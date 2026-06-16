"""Estrategia k-geometrica (KGeoMIP), reescrita en el Sprint 3.

Semantica oficial (decision del Sprint 1): la k-particion se define sobre el
espacio de VERTICES W = {(t, m) : m en mecanismo} U {(t+1, f) : f en alcance},
de modo que el presente y el futuro de una misma variable pueden caer en
grupos distintos, exactamente como en `GeometricSIA`. Dada una particion
{S_1..S_k}, cada cubo futuro f en S_m conserva unicamente las dimensiones
presentes de S_m (las demas se marginalizan); la perdida es la EMD-efecto
entre el vector de marginales reconstruido y el del subsistema original.

Todos los conjuntos se manejan por ETIQUETA global de variable (cube.indice,
cube.dims), nunca por posicion, lo que corrige el bug N1 de la auditoria.

Algoritmo en dos fases:
  - Fase 1 (greedy top-down): k-1 cortes. Cada grupo se corta con el generador
    de candidatos geometrico reformulado del Sprint 2, restringido al
    sub-reticulo de las dimensiones presentes del grupo; cada candidato se
    evalua de forma exacta sobre la particion GLOBAL resultante (sin
    marginalizar de mas: corrige N7). Con k=2 el unico grupo es W y el
    procedimiento es identico a `GeometricSIA` (candidatos, evaluacion y
    desempates), que es la prueba de aceptacion del sprint.
  - Fase 2 (solo k >= 3): refinamiento por reubicacion de vertices con poda:
    (i) cota superior de mejora por movimiento (suma de las perdidas actuales
    de los cubos afectados; si es 0 el movimiento no puede mejorar),
    (ii) aborto temprano de la evaluacion cuando la cota inferior del delta
    ya es no negativa, (iii) sin reinicio: los pares (vertice, destino) solo
    se reevaluan si la composicion de su grupo origen o destino cambio
    (contadores de version por grupo).

Memoizacion: la perdida por particion se cachea bajo clave canonica (tuplas
internas ordenadas y ordenadas entre si); la marginal de cada cubo se cachea
por (cubo, dims conservadas), apoyada ademas en la memoizacion interna de
`NCube.marginalizar`.
"""

import time

import numpy as np

from src.constants.base import ACTUAL, EFECTO, NET_LABEL, TYPE_TAG
from src.constants.models import (
    KGEOMETRIC_ANALYSIS_TAG,
    KGEOMETRIC_LABEL,
    KGEOMETRIC_STRAREGY_TAG,
)
from src.controllers.manager import Manager
from src.funcs.base import emd_efecto, seleccionar_subestado
from src.funcs.format import fmt_biparte_q, fmt_k_particion
from src.middlewares.profile import profile, profiler_manager
from src.middlewares.slogger import SafeLogger
from src.models.base.sia import SIA
from src.models.core.solution import Solution


class KGeometricSIA(SIA):
    """k-particion de minima perdida sobre el espacio de vertices presente/futuro."""

    def __init__(self, gestor: Manager):
        super().__init__(gestor)
        profiler_manager.start_session(
            f"{NET_LABEL}{len(gestor.estado_inicial)}{gestor.pagina}"
        )
        self.logger = SafeLogger(KGEOMETRIC_STRAREGY_TAG)
        # (phi, dist) por particion en clave canonica
        self.memoria_particiones: dict[tuple, tuple[np.floating, np.ndarray]] = {}
        # marginal escalar por (etiqueta de cubo, dims presentes conservadas)
        self._cache_v: dict[tuple, np.floating] = {}
        self.estadisticas_poda: dict[str, int] = {}

    # ------------------------------------------------------------------
    # Interfaz principal
    # ------------------------------------------------------------------

    @profile(context={TYPE_TAG: KGEOMETRIC_ANALYSIS_TAG})
    def aplicar_estrategia(
        self,
        condicion: str,
        alcance: str,
        mecanismo: str,
        tpm: np.ndarray,
        k_objetivo: int = 2,
    ) -> Solution:
        self.sia_preparar_subsistema(condicion, alcance, mecanismo, tpm)
        self._preparar_contexto()

        total_vertices = len(self._dims) + len(self._idx)
        if k_objetivo < 2 or k_objetivo > total_vertices:
            raise ValueError(
                f"k debe estar en [2, {total_vertices}] (vertices del subsistema)"
            )

        self.logger.critic(f"KGeoMIP k={k_objetivo} sobre {total_vertices} vertices")

        grupos, ultimo_corte = self._fase1_greedy(k_objetivo)

        if k_objetivo > 2:
            grupos = self._fase2_refinar(grupos)

        phi, dist = self._medir_perdida(grupos)
        # composicion final en forma canonica (consumida por las validaciones)
        self.grupos_finales = tuple(sorted(tuple(sorted(g)) for g in grupos))
        return Solution(
            estrategia=KGEOMETRIC_LABEL,
            perdida=phi,
            distribucion_subsistema=self.sia_dists_marginales,
            distribucion_particion=dist,
            tiempo_total=time.time() - self.sia_tiempo_inicio,
            particion=self._formatear(grupos, ultimo_corte, k_objetivo),
        )

    # ------------------------------------------------------------------
    # Contexto del subsistema
    # ------------------------------------------------------------------

    def _preparar_contexto(self):
        sub = self.sia_subsistema
        self._dims = [int(d) for d in sub.dims_ncubos]  # etiquetas presentes
        self._idx = [int(f) for f in sub.indices_ncubos]  # etiquetas futuras
        self._pos_de_dim = {d: p for p, d in enumerate(self._dims)}
        self._estado = sub.estado_inicial[sub.dims_ncubos]
        self._flats = {
            int(cubo.indice): np.ascontiguousarray(
                cubo.data.ravel().astype(np.float32, copy=False)
            )
            for cubo in sub.ncubos
        }
        i_int = 0
        for p, _ in enumerate(self._dims):
            i_int |= int(self._estado[p]) << p
        self._i_int = i_int

    # ------------------------------------------------------------------
    # Fase 1: greedy top-down con el corte geometrico restringido
    # ------------------------------------------------------------------

    def _fase1_greedy(self, k: int):
        """Aplica k-1 cortes; cada candidato se evalua sobre la particion global."""
        w_total = frozenset(
            [(ACTUAL, d) for d in self._dims] + [(EFECTO, f) for f in self._idx]
        )
        grupos: list[frozenset] = [w_total]
        ultimo_corte = None

        while len(grupos) < k:
            mejor = None  # (phi, gi, G1, G2)
            for gi, grupo in enumerate(grupos):
                if len(grupo) < 2:
                    continue
                for g1, g2 in self._candidatos_corte(grupo):
                    nueva = grupos[:gi] + [g1, g2] + grupos[gi + 1 :]
                    phi, _ = self._medir_perdida(nueva)
                    if mejor is None or phi < mejor[0]:
                        mejor = (phi, gi, g1, g2)
            if mejor is None:
                raise RuntimeError("No hay grupo divisible y len(grupos) < k")
            _, gi, g1, g2 = mejor
            grupos = grupos[:gi] + [g1, g2] + grupos[gi + 1 :]
            ultimo_corte = (g1, g2)
            self.logger.info(f"Corte {len(grupos)-1}: phi={mejor[0]}")

        return grupos, ultimo_corte

    def _candidatos_corte(self, grupo: frozenset):
        """Candidatos de biparticion del grupo, en el orden de `GeometricSIA`.

        1. Cortes unitarios de futuro (etiqueta de cubo ascendente): {f} contra
           el resto del grupo.
        2. Un candidato por nivel del sub-reticulo de Hamming de las
           dimensiones presentes del grupo (barrido reformulado del Sprint 2).
        El primer elemento de cada par es el lado 'clave' (equivalente al key
        de GeometricSIA: presentes conservados + futuros elegidos).
        """
        presentes = sorted(d for t, d in grupo if t == ACTUAL)
        futuros = sorted(f for t, f in grupo if t == EFECTO)
        candidatos: list[tuple[frozenset, frozenset]] = []

        for f in futuros:
            g2 = frozenset([(EFECTO, f)])
            candidatos.append((grupo - g2, g2))

        if len(presentes) >= 2 and futuros:
            for pres_match, futs_elegidos in self._barrido_restringido(
                presentes, futuros
            ):
                g1 = frozenset(
                    [(ACTUAL, d) for d in pres_match]
                    + [(EFECTO, f) for f in futs_elegidos]
                )
                g2 = grupo - g1
                if g1 and g2:
                    candidatos.append((g1, g2))

        if not candidatos:
            # grupo sin futuros (o degenerado): corte trivial phi-neutral
            ordenado = sorted(grupo)
            candidatos.append((frozenset(ordenado[1:]), frozenset(ordenado[:1])))
        return candidatos

    # ------------------------------------------------------------------
    # Barrido geometrico restringido (reusa la reformulacion del Sprint 2)
    # ------------------------------------------------------------------

    def _barrido_restringido(self, presentes: list[int], futuros: list[int]):
        """DP por niveles en streaming sobre el sub-reticulo de `presentes`.

        Identico a `GeometricSIA._candidatos_por_niveles` cuando el grupo es W
        completo (mismo orden de niveles, de estados y de desempates); para
        subgrupos, el bit b del estado y corresponde a la etiqueta
        `presentes[b]` y los costos se calculan solo para los cubos `futuros`.
        Devuelve [(etiquetas presentes conservadas, etiquetas futuras elegidas)]
        por nivel barrido, en orden de nivel.
        """
        p = len(presentes)
        total_niveles = p + 1
        es_par = total_niveles % 2 == 0
        mitad = total_niveles // 2 if es_par else total_niveles // 2 + 1
        if mitad <= 1:
            return []

        posiciones = np.array(
            [self._pos_de_dim[d] for d in presentes], dtype=np.int64
        )
        flats = [self._flats[f] for f in futuros]
        x_inicial = np.array(
            [flat[self._i_int] for flat in flats], dtype=np.float32
        )
        mascara_total = np.uint32((1 << p) - 1)

        y_prev = np.zeros(1, dtype=np.uint32)
        t_prev = np.zeros((1, len(futuros)), dtype=np.float32)
        niveles_bajos: dict[int, tuple[np.ndarray, np.ndarray]] = {}
        ganadores: dict[int, tuple[list[int], list[int]]] = {}

        for nivel in range(1, p):
            y_cur = self._generar_nivel(y_prev, p)
            t_cur = self._costos_nivel(
                y_cur, y_prev, t_prev, flats, x_inicial, posiciones, nivel, p
            )
            if nivel <= mitad - 1:
                niveles_bajos[nivel] = (y_cur, t_cur)
            comp = p - nivel
            if comp in niveles_bajos and comp <= mitad - 1 and nivel >= comp:
                y_bajo, t_bajo = niveles_bajos.pop(comp)
                ganadores[comp] = self._barrido_nivel(
                    y_bajo, t_bajo, y_cur, t_cur, mascara_total, presentes, futuros
                )
            y_prev, t_prev = y_cur, t_cur

        return [ganadores[nivel] for nivel in sorted(ganadores)]

    @staticmethod
    def _generar_nivel(y_prev: np.ndarray, n: int) -> np.ndarray:
        """Nivel siguiente del reticulo en el orden de enumeracion del oraculo."""
        bits = (np.uint32(1) << np.arange(n, dtype=np.uint32))[None, :]
        cand = y_prev[:, None] | bits
        validos = (y_prev[:, None] & bits) == 0
        plano = cand[validos]
        _, primera_aparicion = np.unique(plano, return_index=True)
        return plano[np.sort(primera_aparicion)]

    def _costos_nivel(
        self,
        y_cur: np.ndarray,
        y_prev: np.ndarray,
        t_prev: np.ndarray,
        flats: list[np.ndarray],
        x_inicial: np.ndarray,
        posiciones: np.ndarray,
        nivel: int,
        p: int,
    ) -> np.ndarray:
        """Recursion t = 2^{-nivel}(D + suma de predecesores) sobre el sub-reticulo."""
        mascara_global = np.zeros(y_cur.size, dtype=np.int64)
        for b in range(p):
            bit_global = np.int64(1) << posiciones[b]
            mascara_global |= ((y_cur >> b) & 1).astype(np.int64) * bit_global
        j_idx = np.int64(self._i_int) ^ mascara_global

        t_cur = np.empty((y_cur.size, len(flats)), dtype=np.float32)
        for c, flat in enumerate(flats):
            np.abs(flat[j_idx] - x_inicial[c], out=t_cur[:, c])

        if nivel > 1:
            orden_prev = np.argsort(y_prev)
            y_prev_ord = y_prev[orden_prev]
            suma_pred = np.zeros_like(t_cur)
            for b in range(p):
                bit = np.uint32(1 << b)
                mascara = (y_cur & bit) != 0
                if not mascara.any():
                    continue
                pred = y_cur[mascara] ^ bit
                filas = orden_prev[np.searchsorted(y_prev_ord, pred)]
                suma_pred[mascara] += t_prev[filas]
            t_cur += suma_pred

        t_cur *= np.float32(2.0 ** (-nivel))
        return t_cur

    @staticmethod
    def _barrido_nivel(
        y_bajo: np.ndarray,
        t_bajo: np.ndarray,
        y_alto: np.ndarray,
        t_alto: np.ndarray,
        mascara_total: np.uint32,
        presentes: list[int],
        futuros: list[int],
    ) -> tuple[list[int], list[int]]:
        """Ganador del nivel contra su complementario (semantica del oraculo)."""
        y_comp = y_bajo ^ mascara_total
        orden_alto = np.argsort(y_alto)
        y_alto_ord = y_alto[orden_alto]
        filas_comp = orden_alto[np.searchsorted(y_alto_ord, y_comp)]
        t_comp = t_alto[filas_comp]

        eleccion_futuro = t_bajo <= t_comp
        costos = np.where(eleccion_futuro, t_bajo, t_comp).sum(
            axis=1, dtype=np.float64
        )
        ganador = int(np.argmin(costos))

        y_g = int(y_bajo[ganador])
        pres_match = [presentes[b] for b in range(len(presentes)) if not (y_g >> b) & 1]
        futs = [futuros[c] for c in np.nonzero(eleccion_futuro[ganador])[0]]
        return pres_match, futs

    # ------------------------------------------------------------------
    # Medicion de perdida (exacta, memoizada a nivel de cubo y de particion)
    # ------------------------------------------------------------------

    @staticmethod
    def _clave_canonica(grupos: list[frozenset]) -> tuple:
        return tuple(sorted(tuple(sorted(g)) for g in grupos))

    def _v_cubo(self, cubo, conservadas: tuple[int, ...]) -> np.floating:
        """Marginal escalar (estado OFF) del cubo conservando solo `conservadas`."""
        clave = (int(cubo.indice), conservadas)
        if clave not in self._cache_v:
            ejes = np.setdiff1d(
                cubo.dims, np.array(conservadas, dtype=np.int8)
            )
            reducido = cubo.marginalizar(ejes)
            probabilidad = reducido.data
            if reducido.dims.size:
                sub_estado = tuple(
                    self.sia_subsistema.estado_inicial[j] for j in reducido.dims
                )
                probabilidad = reducido.data[seleccionar_subestado(sub_estado)]
            self._cache_v[clave] = np.float32(1) - probabilidad
        return self._cache_v[clave]

    def _conservadas_por_grupo(self, grupos: list[frozenset]) -> list[tuple[int, ...]]:
        return [tuple(sorted(d for t, d in g if t == ACTUAL)) for g in grupos]

    def _medir_perdida(self, grupos: list[frozenset]):
        """phi y distribucion reconstruida de la particion global (semantica 1.4)."""
        clave = self._clave_canonica(grupos)
        if clave in self.memoria_particiones:
            return self.memoria_particiones[clave]

        conservadas = self._conservadas_por_grupo(grupos)
        grupo_de_futuro = {}
        for gi, g in enumerate(grupos):
            for t, etiqueta in g:
                if t == EFECTO:
                    grupo_de_futuro[etiqueta] = gi

        dist = np.empty(len(self.sia_subsistema.ncubos), dtype=np.float32)
        for i, cubo in enumerate(self.sia_subsistema.ncubos):
            gi = grupo_de_futuro[int(cubo.indice)]
            dist[i] = self._v_cubo(cubo, conservadas[gi])
        phi = emd_efecto(dist, self.sia_dists_marginales)

        self.memoria_particiones[clave] = (phi, dist)
        return phi, dist

    # ------------------------------------------------------------------
    # Fase 2: refinamiento por reubicacion con poda (solo k >= 3)
    # ------------------------------------------------------------------

    def _fase2_refinar(self, grupos: list[frozenset]) -> list[frozenset]:
        """Busqueda local first-improvement sin reinicio, con poda segura.

        Movimiento: reubicar un vertice w (presente o futuro) a otro grupo.
        Cota superior de mejora del movimiento: la suma de las perdidas
        actuales |v_f - v_orig_f| de los cubos afectados (cada delta nuevo es
        >= 0, luego ninguna mejora puede exceder esa suma); si la cota es 0 o
        la cota inferior parcial del delta deja de ser negativa, se poda. Los
        pares (vertice, destino) ya descartados no se reevaluan mientras no
        cambie la version de su grupo origen ni la del destino.
        """
        k = len(grupos)
        v_orig = self.sia_dists_marginales
        phi_actual, dist_actual = self._medir_perdida(grupos)
        delta_actual = np.abs(dist_actual - v_orig).astype(np.float64)
        pos_cubo = {f: i for i, f in enumerate(self._idx)}

        version = [0] * k
        revisado: dict[tuple, tuple[int, int]] = {}
        stats = {"evaluados": 0, "poda_cota_cero": 0, "poda_parcial": 0,
                 "poda_version": 0, "movimientos": 0, "pasadas": 0}

        vertices = sorted(
            [(ACTUAL, d) for d in self._dims] + [(EFECTO, f) for f in self._idx]
        )

        def cubos_afectados(w, gi_src, gi_dst):
            if w[0] == EFECTO:
                return [w[1]]
            afectados = [f for t, f in grupos[gi_src] if t == EFECTO]
            afectados += [f for t, f in grupos[gi_dst] if t == EFECTO]
            return afectados

        mejora = True
        while mejora:
            mejora = False
            stats["pasadas"] += 1
            for w in vertices:
                gi_src = next(gi for gi, g in enumerate(grupos) if w in g)
                if len(grupos[gi_src]) == 1:
                    continue  # vaciar el grupo rompería el objetivo k
                conservadas = self._conservadas_por_grupo(grupos)
                for gi_dst in range(k):
                    if gi_dst == gi_src:
                        continue
                    marca = (version[gi_src], version[gi_dst])
                    if revisado.get((w, gi_dst)) == marca:
                        stats["poda_version"] += 1
                        continue

                    afectados = cubos_afectados(w, gi_src, gi_dst)
                    cota_mejora = sum(delta_actual[pos_cubo[f]] for f in afectados)
                    if cota_mejora <= 0.0:
                        stats["poda_cota_cero"] += 1
                        revisado[(w, gi_dst)] = marca
                        continue

                    # composicion tras el movimiento
                    if w[0] == ACTUAL:
                        cons_src = tuple(x for x in conservadas[gi_src] if x != w[1])
                        cons_dst = tuple(sorted(conservadas[gi_dst] + (w[1],)))
                    else:
                        cons_src, cons_dst = conservadas[gi_src], conservadas[gi_dst]

                    delta_total = 0.0
                    restante = cota_mejora
                    podado = False
                    stats["evaluados"] += 1
                    for f in afectados:
                        i = pos_cubo[f]
                        restante -= delta_actual[i]
                        if w[0] == EFECTO:
                            cons_nueva = cons_dst
                        else:
                            en_src = (EFECTO, f) in grupos[gi_src]
                            cons_nueva = cons_src if en_src else cons_dst
                        cubo = self.sia_subsistema.ncubos[i]
                        v_nuevo = float(self._v_cubo(cubo, cons_nueva))
                        delta_total += abs(v_nuevo - float(v_orig[i])) - delta_actual[i]
                        if delta_total - restante >= 0.0:
                            stats["poda_parcial"] += 1
                            podado = True
                            break
                    if podado or delta_total >= 0.0:
                        revisado[(w, gi_dst)] = marca
                        continue

                    # aplicar movimiento (mejora estricta)
                    grupos[gi_src] = grupos[gi_src] - {w}
                    grupos[gi_dst] = grupos[gi_dst] | {w}
                    version[gi_src] += 1
                    version[gi_dst] += 1
                    phi_actual, dist_actual = self._medir_perdida(grupos)
                    delta_actual = np.abs(dist_actual - v_orig).astype(np.float64)
                    stats["movimientos"] += 1
                    mejora = True
                    self.logger.info(
                        f"Refinado: {w} -> grupo {gi_dst}, phi={phi_actual}"
                    )
                    break  # siguiente vertice (sin reinicio global)

        self.estadisticas_poda = stats
        self.logger.critic(f"Fase 2: {stats}")
        return grupos

    # ------------------------------------------------------------------
    # Formato de salida
    # ------------------------------------------------------------------

    def _formatear(self, grupos, ultimo_corte, k: int) -> str:
        """k=2 conserva fmt_biparte_q (identidad bit a bit con GeometricSIA);
        k>=3 usa la notación de paréntesis grandes del Excel de pruebas.
        `particion_k_fmt` expone la notación ⎛ ⎞ para cualquier k (la usa el
        llenador del Excel, donde también las biparticiones van con ⎛ ⎞)."""
        self.particion_k_fmt = fmt_k_particion([list(g) for g in grupos])
        if k == 2 and ultimo_corte is not None:
            g1, g2 = ultimo_corte
            return fmt_biparte_q(list(g1), list(g2))
        return self.particion_k_fmt
