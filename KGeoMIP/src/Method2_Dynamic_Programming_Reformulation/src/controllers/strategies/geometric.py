"""Estrategia geometrica de biparticion (version reformulada, Sprint 2).

Reformulacion exacta del calculo de costos sobre el reticulo de Hamming:
en lugar de materializar `tabla_transiciones` (diccionario con 2^n claves,
listas de floats de Python) y `caminos` (todos los estados por nivel como
listas), la recursion

    t_c(i,j) = 2^{-d}( |X_c[i] - X_c[j]| + sum_{p in Pred(j)} t_c(i,p) )

se evalua nivel por nivel en arreglos numpy float32 contiguos de forma
(estados_del_nivel x n_cubos), conservando en memoria unicamente:
  - el nivel anterior (necesario para la recursion),
  - los niveles bajos (1..mitad-1) hasta que llega su nivel complementario,
    momento en el que se ejecuta el barrido de candidatos y se liberan.

La semantica es identica a la version original (conservada verbatim en
`geometric_oracle.py` como oraculo de correctitud): mismos costos, mismos
candidatos, mismo orden de enumeracion de estados (y por tanto los mismos
desempates), misma evaluacion exacta de candidatos via `System.bipartir` +
`emd_efecto`. Cambia la representacion: enteros con bits (popcount/XOR) en
lugar de tuplas y cadenas, float32 en lugar de float64, y streaming en lugar
del reticulo completo.
"""

import time

import numpy as np

from src.constants.base import NET_LABEL
from src.funcs.base import ABECEDARY, emd_efecto
from src.middlewares.slogger import SafeLogger
from src.models.base.sia import SIA
from src.constants.base import (
    ACTUAL,
    EFECTO,
    TYPE_TAG,
)
from src.constants.models import (
    GEOMETRIC_ANALYSIS_TAG,
    GEOMETRIC_LABEL,
    GEOMETRIC_STRAREGY_TAG,
)
from src.controllers.manager import Manager
from src.funcs.format import fmt_biparte_q
from src.middlewares.profile import profiler_manager, profile
from src.models.core.solution import Solution


class GeometricSIA(SIA):
    """Biparticion geometrica con costos por niveles en streaming (sin reticulo materializado)."""

    def __init__(self, gestor: Manager):
        super().__init__(gestor)
        profiler_manager.start_session(
            f"{NET_LABEL}{len(gestor.estado_inicial)}{gestor.pagina}"
        )
        self.etiquetas = [tuple(s.lower() for s in ABECEDARY), ABECEDARY]
        self.logger = SafeLogger(GEOMETRIC_STRAREGY_TAG)
        self.vertices: set[tuple]
        self.memoria_particiones: dict[tuple, tuple[float, np.ndarray]] = {}
        # Conservado por compatibilidad de interfaz; la version reformulada no
        # construye el reticulo (ver docstring del modulo).
        self.tabla_transiciones: dict = {}

    @profile(context={TYPE_TAG: GEOMETRIC_ANALYSIS_TAG})
    def aplicar_estrategia(
        self,
        condicion: str,
        alcance: str,
        mecanismo: str,
        tpm: np.ndarray,
    ):
        """Prepara el subsistema y busca la biparticion de minima perdida.

        Identica interfaz y semantica que la version original; la busqueda de
        candidatos se realiza con la reformulacion por niveles (ver `find_mip`).
        """
        self.sia_preparar_subsistema(condicion, alcance, mecanismo, tpm)

        futuro = tuple(
            (EFECTO, efecto) for efecto in self.sia_subsistema.indices_ncubos
        )
        presente = tuple(
            (ACTUAL, actual) for actual in self.sia_subsistema.dims_ncubos
        )
        self.vertices = set(presente + futuro)

        # Vista plana float32 de cada n-cubo del subsistema (sin copia: la data
        # ya es contigua tras la construccion float32 del System).
        self._flat_data = [
            np.ascontiguousarray(ncubo.data.ravel().astype(np.float32, copy=False))
            for ncubo in self.sia_subsistema.ncubos
        ]

        dims = self.sia_subsistema.dims_ncubos
        self.estado_inicial = self.sia_subsistema.estado_inicial[dims]
        self.estado_final = 1 - self.estado_inicial

        mip = self.find_mip()
        fmt_mip = fmt_biparte_q(list(mip), self.nodes_complement(mip))

        return Solution(
            estrategia=GEOMETRIC_LABEL,
            perdida=self.memoria_particiones[mip][0],
            distribucion_subsistema=self.sia_dists_marginales,
            distribucion_particion=self.memoria_particiones[mip][1],
            tiempo_total=time.time() - self.sia_tiempo_inicio,
            particion=fmt_mip,
        )

    def nodes_complement(self, nodes: list[tuple[int, int]]):
        return list(set(self.vertices) - set(nodes))

    # ------------------------------------------------------------------
    # Nucleo reformulado
    # ------------------------------------------------------------------

    def find_mip(self):
        """Busca la biparticion optima dentro del conjunto de candidatos.

        Genera los mismos candidatos que la version original:
          1. |F| cortes unitarios de futuro (cada cubo solo contra el resto).
          2. Un candidato por nivel 1..mitad-1 del reticulo, elegido por el
             barrido de costos contra el nivel complementario.
        Cada candidato se evalua de forma exacta con bipartir + emd_efecto.
        """
        self.sia_logger.critic("empieza.")
        n = int(self.estado_inicial.size)
        n_vars = int(self.sia_subsistema.indices_ncubos.size)

        # Codificacion entera little-endian del estado inicial restringido:
        # la posicion p aporta 2^p, coherente con el indice plano del n-cubo.
        i_int = 0
        for p in range(n):
            i_int |= int(self.estado_inicial[p]) << p

        # Candidatos iniciales: cortes unitarios de futuro (orden por indice).
        candidatos: list[list[list[int]]] = []
        for idx in range(n_vars):
            presentes = list(range(n))
            futuros = [i for i in range(n_vars) if i != idx]
            candidatos.append([presentes, futuros])

        # mitad replica el calculo original sobre len(caminos) = n + 1 niveles.
        total_niveles = n + 1
        es_par = total_niveles % 2 == 0
        mitad = total_niveles // 2 if es_par else total_niveles // 2 + 1

        candidatos.extend(self._candidatos_por_niveles(n, n_vars, i_int, mitad))

        # Evaluacion exacta de cada candidato (identica al original).
        for presentes, futuros in candidatos:
            presentes_dims = self.sia_subsistema.dims_ncubos[presentes]
            futuros_idx = self.sia_subsistema.indices_ncubos[futuros]
            dist = self.sia_subsistema.bipartir(
                futuros_idx, presentes_dims
            ).distribucion_marginal()
            emd = emd_efecto(dist, self.sia_dists_marginales)
            key = [(0, nodo) for nodo in presentes_dims]
            key.extend([(1, nodo) for nodo in futuros_idx])
            self.memoria_particiones[tuple(key)] = (emd, dist)

        return min(
            self.memoria_particiones, key=lambda k: self.memoria_particiones[k][0]
        )

    def _candidatos_por_niveles(self, n: int, n_vars: int, i_int: int, mitad: int):
        """DP por niveles en streaming y barrido contra niveles complementarios.

        Mantiene T_nivel como matriz float32 (estados x n_cubos). Los niveles
        bajos (1..mitad-1) se retienen hasta que el avance del DP alcanza su
        complemento n-nivel; alli se ejecuta el barrido y se liberan.
        Devuelve un candidato por nivel barrido, en orden de nivel.
        """
        if mitad <= 1 or n < 2:
            return []

        mascara_total = np.uint32((1 << n) - 1)
        flats = self._flat_data
        x_inicial = np.array([flat[i_int] for flat in flats], dtype=np.float32)

        # Nivel 0: unico estado y = 0 con costo nulo.
        y_prev = np.zeros(1, dtype=np.uint32)
        t_prev = np.zeros((1, n_vars), dtype=np.float32)

        niveles_bajos: dict[int, tuple[np.ndarray, np.ndarray]] = {}
        ganadores: dict[int, list[list[int]]] = {}

        nivel_max = n - 1  # el complemento del nivel 1; el nivel n no se necesita
        for nivel in range(1, nivel_max + 1):
            y_cur = self._generar_nivel(y_prev, n)
            t_cur = self._costos_nivel(
                y_cur, y_prev, t_prev, flats, x_inicial, i_int, nivel, n
            )

            if nivel <= mitad - 1:
                niveles_bajos[nivel] = (y_cur, t_cur)

            comp = n - nivel
            if comp in niveles_bajos and comp <= mitad - 1 and nivel >= comp:
                y_bajo, t_bajo = niveles_bajos.pop(comp)
                ganadores[comp] = self._barrido_nivel(
                    y_bajo, t_bajo, y_cur, t_cur, mascara_total, n
                )

            y_prev, t_prev = y_cur, t_cur

        return [ganadores[nivel] for nivel in sorted(ganadores)]

    @staticmethod
    def _generar_nivel(y_prev: np.ndarray, n: int) -> np.ndarray:
        """Genera el nivel siguiente replicando el orden de la version original.

        El original recorre los estados del nivel anterior en orden y, por cada
        uno, los bits ascendentes aun no volteados, descartando repetidos
        (primera aparicion gana). Aqui: producto fila-mayor + dedupe por primera
        aparicion (np.unique con return_index entrega la primera ocurrencia).
        """
        bits = (np.uint32(1) << np.arange(n, dtype=np.uint32))[None, :]
        cand = y_prev[:, None] | bits
        validos = (y_prev[:, None] & bits) == 0
        plano = cand[validos]  # orden fila-mayor: estado-mayor, bit-menor
        _, primera_aparicion = np.unique(plano, return_index=True)
        return plano[np.sort(primera_aparicion)]

    @staticmethod
    def _costos_nivel(
        y_cur: np.ndarray,
        y_prev: np.ndarray,
        t_prev: np.ndarray,
        flats: list[np.ndarray],
        x_inicial: np.ndarray,
        i_int: int,
        nivel: int,
        n: int,
    ) -> np.ndarray:
        """Aplica la recursion t = 2^{-nivel} (D + suma de predecesores), vectorizada.

        Los predecesores de y (un bit menos cerca del inicial) se localizan por
        busqueda binaria sobre el nivel anterior; la agregacion se hace bit por
        bit: para un bit fijo, el mapeo y -> y sin ese bit es inyectivo, asi que
        la suma indexada no tiene colisiones.
        """
        n_vars = t_prev.shape[1]
        j_idx = (np.uint32(i_int) ^ y_cur).astype(np.int64)

        t_cur = np.empty((y_cur.size, n_vars), dtype=np.float32)
        for c, flat in enumerate(flats):
            np.abs(flat[j_idx] - x_inicial[c], out=t_cur[:, c])

        if nivel > 1:
            orden_prev = np.argsort(y_prev)
            y_prev_ord = y_prev[orden_prev]
            suma_pred = np.zeros_like(t_cur)
            for b in range(n):
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
        n: int,
    ) -> list[list[int]]:
        """Barrido de un nivel contra su complementario (semantica original exacta).

        Para cada estado j del nivel bajo: cada cubo va al lado 'futuros' si
        t(j) <= t(complemento(j)) (empate favorece futuros, como el original);
        el costo del estado es la suma de los minimos elegidos. Gana el primer
        estado con costo estrictamente menor (argmin = primera ocurrencia,
        identico al recorrido original). 'presentes' son las posiciones no
        volteadas respecto del estado inicial.
        """
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
        presentes = [p for p in range(n) if not (y_g >> p) & 1]
        futuros = [int(c) for c in np.nonzero(eleccion_futuro[ganador])[0]]
        return [presentes, futuros]
