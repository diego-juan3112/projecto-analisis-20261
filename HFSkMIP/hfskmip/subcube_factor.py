"""
Heurística Subcubo-Factor (HFS): costos de transición locales en caras k-dimensionales
del hipercubo del subsistema, agregados para rankear biparticiones; la pérdida final
se calcula con la misma EMD-efecto que GeoMIP sobre la partición elegida.
"""

from __future__ import annotations

import itertools
import random
import time
from typing import Dict, List, Sequence, Tuple

import numpy as np

from src.constants.base import ACTUAL, EFECTO
from src.funcs.base import emd_efecto
from src.funcs.format import fmt_biparte_q
from src.models.base.sia import SIA
from src.models.core.solution import Solution
from src.controllers.manager import Manager

STRATEGY_LABEL = "SubcubeFactor"


def _hamming(a: Sequence[int], b: Sequence[int]) -> int:
    return sum(x != y for x, y in zip(a, b))


class SubcubeFactorSIA(SIA):
    """
    Heurística SubCube-Factor alineada en espíritu con `SubCubeFactor_Formalizacion.docx`:

    - `decomposition_mode="index_partition"`: cubierta disjunta del hipercubo con
      corte por índice (doc §4.2.2): dimensiones libres ``0..d-1``, fijas ``d..n-1``;
      para cada patrón de bits en las fijas se integra un subcubo de 2^d vértices y
      se calcula el costo local inicial→final dentro de ese subcubo (BFS restringido,
      misma recurrencia que GeoMIP).
    - `decomposition_mode="sample_faces"`: variante experimental que muestrea
      conjuntos de `k` dimensiones activas (no recorre toda 𝒞(d)).

    La agregación en código promedia vectores de costo por variable futura (Fase 2
    completa del doc: matriz de afinidad y clustering espectral queda como extensión
    futura; ver `docs/Alineacion_formalizacion_e_implementacion.md`).
    """

    def __init__(
        self,
        gestor: Manager,
        subcube_dim: int | None = None,
        max_subcubes: int = 64,
        top_k_candidates: int = 5,
        seed: int = 42,
        decomposition_mode: str = "index_partition",
    ) -> None:
        super().__init__(gestor)
        self.subcube_dim = subcube_dim
        self.max_subcubes = max_subcubes
        self.top_k_candidates = max(1, top_k_candidates)
        if decomposition_mode not in ("index_partition", "sample_faces"):
            raise ValueError(
                "decomposition_mode debe ser 'index_partition' o 'sample_faces'"
            )
        self.decomposition_mode = decomposition_mode
        self._rng = random.Random(seed)
        self._flat_data: list[np.ndarray] = []
        self.vertices: set[tuple[int, int]] = set()

    def aplicar_estrategia(
        self,
        condicion: str,
        alcance: str,
        mecanismo: str,
        tpm: np.ndarray,
    ) -> Solution:
        self.sia_preparar_subsistema(condicion, alcance, mecanismo, tpm)

        futuro = tuple((EFECTO, efecto) for efecto in self.sia_subsistema.indices_ncubos)
        presente = tuple((ACTUAL, actual) for actual in self.sia_subsistema.dims_ncubos)
        self.vertices = set(presente + futuro)

        self._flat_data = [ncubo.data.ravel() for ncubo in self.sia_subsistema.ncubos]

        dims = self.sia_subsistema.dims_ncubos
        estado_inicial = self.sia_subsistema.estado_inicial[dims]
        estado_final = 1 - estado_inicial
        self._estado_inicial = np.array(estado_inicial, dtype=np.int8)
        self._estado_final = np.array(estado_final, dtype=np.int8)

        n = int(self._estado_inicial.size)
        # Doc §8.1: d = ⌊n/2⌋ como valor por defecto; acotamos a [1, n].
        k = self.subcube_dim if self.subcube_dim is not None else max(1, n // 2)
        k = max(1, min(k, n))

        costos_aprox = self._aggregate_subcube_costs(n, k)
        mip = self._select_partition(costos_aprox, n)
        presentes = self.sia_subsistema.dims_ncubos[list(mip[0])]
        futuros = self.sia_subsistema.indices_ncubos[list(mip[1])]
        dist = self.sia_subsistema.bipartir(futuros, presentes).distribucion_marginal()
        emd = emd_efecto(dist, self.sia_dists_marginales)

        key = [(0, int(nodo)) for nodo in presentes]
        key.extend([(1, int(nodo)) for nodo in futuros])
        fmt_mip = fmt_biparte_q(list(key), self._nodes_complement(key))

        return Solution(
            estrategia=STRATEGY_LABEL,
            perdida=emd,
            distribucion_subsistema=self.sia_dists_marginales,
            distribucion_particion=dist,
            tiempo_total=time.time() - self.sia_tiempo_inicio,
            particion=fmt_mip,
        )

    def _nodes_complement(self, nodes: list[tuple[int, int]]) -> list[tuple[int, int]]:
        return list(self.vertices - set(nodes))

    def _subcube_choices(self, n: int, k: int) -> List[Tuple[int, ...]]:
        combs = list(itertools.combinations(range(n), k))
        if len(combs) <= self.max_subcubes:
            return combs
        return self._rng.sample(combs, self.max_subcubes)

    def _iter_index_partition_subcubes(
        self, n: int, d: int
    ) -> List[Tuple[List[int], List[int]]]:
        """
        Corte por índice (doc §4.2.2, 0-based): libres 0..d-1, fijas d..n-1.
        Cada elemento es (s0, s1) vértices en el mismo C(F,b).
        """
        if d >= n:
            s0 = self._estado_inicial.tolist()
            s1 = self._estado_final.tolist()
            return [(s0, s1)]
        free = tuple(range(d))
        fixed = list(range(d, n))
        patterns = list(itertools.product((0, 1), repeat=len(fixed)))
        if len(patterns) > self.max_subcubes:
            patterns = self._rng.sample(patterns, self.max_subcubes)
        out: List[Tuple[List[int], List[int]]] = []
        ei = self._estado_inicial.tolist()
        ef = self._estado_final.tolist()
        for bits in patterns:
            s0 = [0] * n
            s1 = [0] * n
            for j, idx in enumerate(fixed):
                b = int(bits[j])
                s0[idx] = b
                s1[idx] = b
            for i in free:
                s0[i] = int(ei[i])
                s1[i] = int(ef[i])
            out.append((s0, s1))
        return out

    def _aggregate_subcube_costs(self, n: int, k: int) -> np.ndarray:
        sumvec = np.zeros(n, dtype=np.float64)
        count = 0
        if self.decomposition_mode == "index_partition":
            for s0, s1 in self._iter_index_partition_subcubes(n, k):
                v = self._edge_costs_on_face(s0, s1, tuple(range(k)) if k < n else tuple(range(n)))
                sumvec += v
                count += 1
        else:
            for dims_active in self._subcube_choices(n, k):
                estado_inicial = self._estado_inicial.tolist()
                estado_final_face = estado_inicial.copy()
                for i in dims_active:
                    estado_final_face[i] = int(self._estado_final[i])
                v = self._edge_costs_on_face(
                    estado_inicial, estado_final_face, dims_active
                )
                sumvec += v
                count += 1
        if count == 0:
            return np.zeros(n, dtype=np.float64)
        return sumvec / count

    def _edge_costs_on_face(
        self,
        estado_inicial: List[int],
        estado_final_face: List[int],
        dims_active: Tuple[int, ...],
    ) -> np.ndarray:
        """Costo por variable futura en la arista estado_inicial → estado_final_face restringida a dims_active."""
        tabla: Dict[Tuple[Tuple[int, ...], Tuple[int, ...]], List[float]] = {}
        caminos: Dict[int, List[List[int]]] = {0: [estado_inicial]}
        max_level = len(dims_active)

        for nivel in range(1, max_level + 1):
            caminos[nivel] = []
            visitados: set[tuple] = set()
            for estado_anterior in caminos[nivel - 1]:
                estado_actual = np.array(estado_anterior, dtype=np.int8)
                for i in dims_active:
                    if estado_actual[i] != estado_final_face[i]:
                        nuevo = estado_actual.copy()
                        nuevo[i] = estado_final_face[i]
                        t = tuple(int(x) for x in nuevo)
                        if t not in visitados:
                            caminos[nivel].append(nuevo.tolist())
                            self._calcular_costo(
                                estado_inicial,
                                nuevo.tolist(),
                                tabla,
                            )
                            visitados.add(t)

        key = (tuple(estado_inicial), tuple(estado_final_face))
        if key not in tabla:
            self._calcular_costo(estado_inicial, estado_final_face, tabla)
        vec = tabla[key]
        return np.array(vec, dtype=np.float64)

    def _calcular_costo(
        self,
        estado_inicial: List[int],
        estado_final: List[int],
        tabla: Dict[Tuple[Tuple[int, ...], Tuple[int, ...]], List[float]],
    ) -> None:
        """Misma lógica que GeometricSIA.calcular_costo, sobre tabla local."""
        key = (tuple(estado_inicial), tuple(estado_final))
        if key not in tabla:
            tabla[key] = [None] * len(self._flat_data)

        distancia_hamming = _hamming(estado_inicial, estado_final)
        factor = 1.0 / (2**distancia_hamming)

        estado_ini_int = int("".join(map(str, estado_inicial[::-1])), 2)
        estado_fin_int = int("".join(map(str, estado_final[::-1])), 2)

        diffs = np.abs(
            np.array([flat[estado_ini_int] for flat in self._flat_data])
            - np.array([flat[estado_fin_int] for flat in self._flat_data])
        )
        tabla[key] = diffs.tolist()

        if distancia_hamming > 1:
            for i in range(len(estado_inicial)):
                if estado_inicial[i] != estado_final[i]:
                    nuevo_estado = list(estado_final)
                    nuevo_estado[i] = estado_inicial[i]
                    nuevo_tuple = tuple(nuevo_estado)
                    temp_key = (tuple(estado_inicial), nuevo_tuple)
                    for n in range(len(self._flat_data)):
                        tabla[key][n] = tabla[key][n] + tabla[temp_key][n]

        tmp: List[float] = []
        for n in tabla[key]:
            if n is not None:
                tmp.append(factor * float(n))
            else:
                tmp.append(float("nan"))
        tabla[key] = tmp

    def _select_partition(
        self,
        costos_aprox: np.ndarray,
        n: int,
    ) -> Tuple[List[int], List[int]]:
        """
        Candidatos tipo GeoMIP (primer bloque): futuros = todos menos idx.
        Rankeamos idx por costo agregado local (menor → más «barato» en cara).
        Evaluamos EMD real para los top_k y devolvemos el de menor pérdida.
        """
        order = np.argsort(costos_aprox)
        idxs = [int(order[i]) for i in range(min(self.top_k_candidates, n))]

        best: Tuple[float, Tuple[List[int], List[int]]] | None = None
        for idx in idxs:
            presentes = [i for i in range(n)]
            futuros = [i for i in range(n) if i != idx]
            presentes_nodes = self.sia_subsistema.dims_ncubos[presentes]
            futuros_nodes = self.sia_subsistema.indices_ncubos[futuros]
            dist = (
                self.sia_subsistema.bipartir(futuros_nodes, presentes_nodes)
                .distribucion_marginal()
            )
            emd = float(emd_efecto(dist, self.sia_dists_marginales))
            cand = (presentes, futuros)
            if best is None or emd < best[0]:
                best = (emd, cand)
        assert best is not None
        return best[1]
