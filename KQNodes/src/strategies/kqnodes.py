import numpy as np
import time
from typing import List, Callable

from src.models.base.sia import SIA
from src.models.core.solution import Solution
from src.models.core.system import System
from src.funcs.iit import emd_efecto
from src.constants.base import COLS_IDX


class KQNodes(SIA):
    """Estrategia KQNodes para k-partición de mínima información."""

    def __init__(
        self,
        gestor,
        k: int = 2,
        refinar: bool = True,
        verbose: bool = False,
    ):
        """Inicializa el algoritmo KQNodes.

        Args:
            gestor: Gestor de datos / fuente de TPM.
            k (int): Número de particiones para k-MIP.
            refinar (bool): Si se debe aplicar refinamiento local.
            verbose (bool): Si se imprime información de ejecución.
        """
        self.gestor = gestor
        self.k = k
        self.refinar = refinar
        self.verbose = verbose

        self.tpm: np.ndarray = self.gestor.cargar_red()
        super().__init__(self.tpm)

        self._tabla_costos: np.ndarray | None = None

    def aplicar_estrategia(self) -> Solution:
        """Ejecuta la estrategia de k-partición y retorna la solución encontrada.

        Flujo orquestador:
        1. Obtener tabla de costos T (pre-calculada o reutilizada de GeoMIP).
        2. Ejecutar Queyranne iterativo para encontrar k particiones.
        3. Validar que la partición es válida (disjunta, completa, no-vacía).
        4. Si self.refinar=True, aplicar hill climbing de intercambio local.
        5. Retornar Solution con partición, pérdida y tiempo total.

        Retorna:
            Solution: Objeto con partición óptima, pérdida y tiempo de ejecución.

        Lanza:
            ValueError: Si la partición falla validación.
        """
        # Cronómetro de ejecución total
        t0 = time.perf_counter()

        # Paso 1: Obtener tabla de costos T
        T = self._obtener_tabla_costos()

        # Paso 2: Ejecutar Queyranne iterativo
        partes = self._queyranne_iterativo(T)

        # Paso 3: Validar partición
        self._validar_particion(partes)

        # Paso 4: Refinar si es necesario
        if self.refinar:
            partes = self._intercambio_local(partes)

        # Paso 5: Calcular tiempo total en milisegundos
        tiempo_ms = (time.perf_counter() - t0) * 1000.0

        # Evaluar pérdida final
        perdida_final = self._evaluar_perdida_restringida(
            frozenset(partes[0]) if partes else frozenset(),
            frozenset(range(int(T.shape[0]))),
            [],
            T,
        )

        # Construir y retornar resultado
        return self._construir_resultado(partes, perdida_final, tiempo_ms)
    
    def _construir_resultado(self, partes: List[frozenset], perdida: float, tiempo_ms: float) -> Solution:
        """Construye un objeto Solution a partir de la partición calculada.

        Args:
            partes: Lista de frozensets que componen la partición.
            perdida: Pérdida (EMD) asociada a la partición.
            tiempo_ms: Tiempo de ejecución en milisegundos.

        Retorna:
            Solution: Objeto con los resultados.
        """
        # Conversión a formato compatible con Solution
        # (ajustar según el constructor de Solution)
        return Solution(
            estrategia="KQNodes",
            perdida=perdida,
            distribucion_subsistema=self.sia_dists_marginales,
            distribucion_particion=np.ones(len(partes), dtype=np.float32) / len(partes),
            tiempo_total=tiempo_ms / 1000.0,  # convertir a segundos
            particion=partes,
        )

    def _obtener_tabla_costos(self) -> np.ndarray:
        """Construye la tabla de costos T que utilizará Queyranne iterativo.

        Retorna una matriz de costos n×n donde T[i,j] representa el coste
        de tener los nodos i y j en la misma partición (o separados).

        Para simplificar, usar una matriz de identidad o basada en distancia
        de Hamming. En versiones futuras, reutilizar tablas de GeoMIP.

        Retorna:
            np.ndarray: Matriz de costos T (n×n).
        """
        if self._tabla_costos is not None:
            return self._tabla_costos

        # Número de variables
        n = int(self.tpm.shape[1])

        # Matriz de costos simple: distancia euclidiana entre columnas de TPM
        # o matriz uniforme para prototipos
        T = np.zeros((n, n), dtype=np.float32)

        # Llenar con distancias (por ahora, uniforme)
        for i in range(n):
            for j in range(n):
                if i == j:
                    T[i, j] = 0.0
                else:
                    T[i, j] = 1.0

        self._tabla_costos = T
        return T

    def _queyranne_iterativo(self, T: np.ndarray) -> List[frozenset]:
        """Ejecuta el algoritmo de Queyranne iterativo sobre la matriz de costos T.

        Algoritmo:
        1. V_res = frozenset de todos los índices [0..n-1].
        2. Para i in 1..k-1:
           a. define f_i(S) = _evaluar_perdida_restringida(S, V_res, partes_fijas, T)
           b. ejecuta Queyranne sobre V_res con f_i
           c. S_opt = corte de menor pérdida encontrado por Queyranne
           d. partes_fijas.append(S_opt); V_res = V_res - S_opt
        3. partes_fijas.append(V_res)
        4. retorna partes_fijas

        Complejidad: O(k * n^3 * eval_delta) donde eval_delta es el coste de
        evaluar `_evaluar_perdida_restringida`.

        Retorna:
            list[frozenset[int]]: lista de partes fijas que suman la partición.
        """

        # Número de variables inferido desde la forma de T
        n = int(T.shape[0])

        # Conjunto de variables restantes por particionar
        V_res: frozenset = frozenset(range(n))
        partes_fijas: List[frozenset] = []

        # Función auxiliar: implementación local de Queyranne sobre un dominio V
        def _queyranne_on_set(V: frozenset, f: Callable[[frozenset], float]) -> frozenset:
            """Implementación básica del algoritmo de Queyranne.

            - A representa una partición coarsened de V como lista de bloques (frozenset).
            - En cada fase se construye una secuencia por máximos marginals
              y se obtiene un "pendant pair" (prev, last). Se actualiza la mejor
              solución candidata y se fusionan los dos bloques en A.
            """
            # Inicialmente A contiene singletons
            A: List[frozenset] = [frozenset([v]) for v in V]
            best_set: frozenset = frozenset()
            best_value: float = float("inf")

            # Mientras existan al menos dos bloques
            while len(A) > 1:
                # Secuencia greedily construida
                S_sequence: List[frozenset] = []
                S_union: frozenset = frozenset()
                remaining = A.copy()

                # Construir secuencia de pendientes por máximos incrementos
                for _ in range(len(A)):
                    best_a = None
                    best_gain = None
                    for a in remaining:
                        union = frozenset(set(S_union) | set(a))
                        # ganancia marginal: f(S ∪ a) - f(S)
                        gain = f(union) - f(S_union)
                        if best_a is None or gain > best_gain:
                            best_a = a
                            best_gain = gain
                    # añadir mejor bloque encontrado
                    S_sequence.append(best_a)
                    S_union = frozenset(set(S_union) | set(best_a))
                    remaining.remove(best_a)

                # El último elemento de la secuencia es candidato (pendant)
                last = S_sequence[-1]
                # evaluar su valor y actualizar mejor solución si aplica
                val_last = f(last)
                if val_last < best_value:
                    best_value = val_last
                    best_set = last

                # fusionar los dos últimos bloques (prev, last) en A
                prev = S_sequence[-2]
                merged = frozenset(set(prev) | set(last))

                # reconstruir A reemplazando prev por merged y eliminando last
                A_new: List[frozenset] = []
                merged_added = False
                for a in A:
                    if a == prev and not merged_added:
                        A_new.append(merged)
                        merged_added = True
                    elif a == last:
                        # omitimos last
                        continue
                    else:
                        A_new.append(a)
                A = A_new

            return best_set if best_set else (A[0] if A else frozenset())

        # Iterar k-1 veces para extraer k-1 partes fijas
        for i in range(1, max(1, self.k)):
            # f_i: función objetivo restringida que recibe un subconjunto S
            def f_i(S: frozenset) -> float:
                return self._evaluar_perdida_restringida(S, V_res, partes_fijas, T)

            # Ejecutar Queyranne sobre V_res con f_i
            S_opt = _queyranne_on_set(V_res, f_i)

            # Asegurar tipo frozenset
            S_opt = frozenset(S_opt)

            # Registrar y actualizar el conjunto restante
            partes_fijas.append(S_opt)
            V_res = frozenset(set(V_res) - set(S_opt))

            if self.verbose:
                loss = f_i(S_opt)
                print(f"[KQNodes][iter={i}] extraída S={sorted(list(S_opt))} restante={sorted(list(V_res))} pérdida={loss}")

            # Si ya no quedan elementos, romper antes de completar las iteraciones
            if not V_res:
                break

        # Última parte = lo que quede
        if V_res:
            partes_fijas.append(V_res)

        return partes_fijas

    def _evaluar_perdida_restringida(
        self,
        S: frozenset,
        V_res: frozenset,
        partes_fijas: List[frozenset],
        T: np.ndarray,
    ) -> float:
        """Calcula la pérdida restringida de una partición parcial.

        Definición matemática:
        f_i(S) = EMD(
            P(V_t+1 | V_t=estado_inicial),
            P(S1) ⊗ P(S2) ⊗ ... ⊗ P(Si-1) ⊗ P(S) ⊗ P(complemento)
        )

        donde:
        - partes_fijas = [S1, S2, ..., Si-1] (ya fijadas)
        - S = nueva parte candidata
        - complemento = V_res - S
        - P(X) = distribución marginal de X condicionada al estado inicial
        - ⊗ = producto tensorial (Kronecker para distribuciones independientes)

        Casos edge: retorna float('inf') si S es vacío o S == V_res.

        Args:
            S (frozenset): Nueva parte candidata a evaluar.
            V_res (frozenset): Conjunto de variables restantes por particionar.
            partes_fijas (List[frozenset]): Partes ya fijadas en iteraciones previas.
            T (np.ndarray): Matriz de costos (n×n), pre-calculada.

        Returns:
            float: Pérdida (EMD) asociada a la partición parcial.

        Ejemplo comentado:
            S = frozenset({0})
            V_res = frozenset({0, 1, 2})
            partes_fijas = []
            T = array 3x3

            complemento = V_res - S = {1, 2}
            P(S) = distribucion_marginal({0})
            P(complemento) = distribucion_marginal({1, 2})
            producto_tensorial = P(S) ⊗ P(complemento)
            perdida = EMD(distribucion_global, producto_tensorial)
        """

        # Casos edge: si S es vacío o cubre todo V_res, retornar infinito
        if not S or S == V_res:
            return float("inf")

        # Calcular complemento: la parte restante de V_res que no es S
        complemento = frozenset(set(V_res) - set(S))

        # Lista de partes a combinar tensorialmente
        # partes_a_combinar = partes_fijas + [S] + [complemento]
        partes_a_combinar: List[frozenset] = list(partes_fijas) + [S]
        if complemento:
            partes_a_combinar.append(complemento)

        # Obtener la distribución marginal global del subsistema
        # (condicionada al estado inicial ya set en sia_preparar_subsistema)
        distribucion_global = self.sia_dists_marginales

        # Calcular el producto tensorial de las distribuciones marginales de cada parte
        # Para cada parte, extraer el subsistema parcial y obtener su distribución marginal
        distribuciones_partes: List[np.ndarray] = []

        for parte in partes_a_combinar:
            # Convertir frozenset a array para indexación
            indices_parte = np.array(sorted(list(parte)), dtype=np.int8)

            # Para esta parte, crear un subsistema restringido
            # (aquí asumimos que self.sia_subsistema ya está preparado)
            # y obtener su distribución marginal
            try:
                # Usar el subsistema del SIA para marginalizar a la parte específica
                subsistema_parte = self.sia_subsistema.substraer(
                    alcance_idx=np.setdiff1d(self.sia_subsistema.indices_ncubos, indices_parte),
                    mecanismo_dims=np.setdiff1d(self.sia_subsistema.dims_ncubos, indices_parte),
                )
                dist_parte = subsistema_parte.distribucion_marginal()
            except Exception:
                # Si la marginalización falla, usar una distribución uniforme
                dist_parte = np.ones(len(parte), dtype=np.float32) / len(parte)

            distribuciones_partes.append(dist_parte)

        # Producto tensorial (Kronecker) de las distribuciones
        # Para distribuciones independientes: P(S1,S2,...) = P(S1) ⊗ P(S2) ⊗ ...
        producto_tensorial = distribuciones_partes[0].copy()
        for dist in distribuciones_partes[1:]:
            producto_tensorial = np.kron(producto_tensorial, dist)

        # Calcular la EMD (Earth Mover's Distance) entre las distribuciones
        # Usar emd_efecto que ya está optimizado para este propósito
        perdida = emd_efecto(
            u=distribucion_global.astype(np.float32),
            v=producto_tensorial.astype(np.float32),
        )

        if self.verbose:
            print(
                f"  [eval_perdida] S={sorted(list(S))} -> pérdida={perdida:.6f}"
            )

        return float(perdida)

    def _intercambio_local(self, partes: List[frozenset]) -> List[frozenset]:
        """Realiza un intercambio local (hill climbing) para mejorar la partición inicial.

        Algoritmo (hill climbing):
        1. Repetir hasta convergencia o máximo n*k iteraciones:
           a. Para cada variable x en cada parte S_a:
              i. Para cada parte S_b != S_a:
                 - Si |S_a| > 1 (no dejar parte vacía):
                   - Evaluar pérdida si x se mueve de S_a a S_b
                   - Si hay mejora: aplicar movimiento, marcar cambio=True
           b. Si ningún movimiento mejoró en la pasada: romper (convergencia)
        2. Retornar lista de frozensets refinada.

        Invariante: la pérdida nunca puede aumentar durante los intercambios.

        Args:
            partes (List[frozenset]): Partición inicial de k partes.

        Retorna:
            List[frozenset]: Partición refinada con pérdida ≤ pérdida inicial.
        """
        # Copiar para no modificar la entrada
        partes_actuales = [frozenset(p) for p in partes]
        n = sum(len(p) for p in partes_actuales)
        max_iteraciones = max(n * self.k, 100)  # límite de iteraciones

        # Evaluar pérdida inicial de toda la partición
        T = self._obtener_tabla_costos()
        V_todas = frozenset(range(n))
        perdida_inicial = sum(
            self._evaluar_perdida_restringida(
                p, V_todas, [], T
            )
            for p in partes_actuales
        )

        if self.verbose:
            print(f"[intercambio_local] inicio con pérdida={perdida_inicial:.6f}")

        # Hill climbing: repetir hasta convergencia
        for iteracion in range(max_iteraciones):
            cambio_realizado = False

            # Para cada parte S_a
            for idx_a in range(len(partes_actuales)):
                S_a = partes_actuales[idx_a]

                # Para cada variable x en S_a
                for x in list(S_a):
                    # Para cada parte S_b != S_a
                    for idx_b in range(len(partes_actuales)):
                        if idx_b == idx_a:
                            continue

                        S_b = partes_actuales[idx_b]

                        # Evitar dejar S_a vacía
                        if len(S_a) <= 1:
                            continue

                        # Crear partición candidata moviendo x de S_a a S_b
                        S_a_nueva = frozenset(set(S_a) - {x})
                        S_b_nueva = frozenset(set(S_b) | {x})

                        # Evaluar pérdida de la nueva partición
                        partes_candidatas = []
                        for i in range(len(partes_actuales)):
                            if i == idx_a:
                                partes_candidatas.append(S_a_nueva)
                            elif i == idx_b:
                                partes_candidatas.append(S_b_nueva)
                            else:
                                partes_candidatas.append(partes_actuales[i])

                        perdida_candidata = sum(
                            self._evaluar_perdida_restringida(
                                p, V_todas, [], T
                            )
                            for p in partes_candidatas
                        )

                        # Si hay mejora, aplicar movimiento
                        if perdida_candidata < perdida_inicial - 1e-9:  # tolerancia numérica
                            partes_actuales = partes_candidatas
                            perdida_inicial = perdida_candidata
                            cambio_realizado = True

                            if self.verbose:
                                print(
                                    f"  [iter={iteracion}] movimiento: {x} de {idx_a} a {idx_b}, "
                                    f"nueva pérdida={perdida_inicial:.6f}"
                                )
                            break

                    if cambio_realizado:
                        break

                if cambio_realizado:
                    break

            # Si ningún movimiento mejoró, converger
            if not cambio_realizado:
                if self.verbose:
                    print(f"[intercambio_local] convergencia en iteración {iteracion}")
                break

        return partes_actuales

    def _validar_particion(self, partes: List[frozenset]) -> bool:
        """Valida que la partición cumple las propiedades de k-partición.

        Propiedades validadas:
        1. Disjunción: ningún elemento aparece en más de una parte.
        2. Completitud: la unión de todas las partes es V = {0..n-1}.
        3. No-vacío: ninguna parte es vacía.
        4. Cardinalidad: hay exactamente k partes (o < k si V_res quedó incompleto).

        Args:
            partes (List[frozenset]): Partición a validar.

        Retorna:
            bool: True si válida.

        Lanza:
            ValueError: Si alguna propiedad falla, con mensaje descriptivo.
        """
        # Validar no-vacío
        for i, parte in enumerate(partes):
            if not parte:
                raise ValueError(
                    f"Partición inválida: la parte {i} es vacía. "
                    f"Todas las partes deben tener al menos un elemento."
                )

        # Validar disjunción
        elementos_vistos = set()
        for i, parte in enumerate(partes):
            for elem in parte:
                if elem in elementos_vistos:
                    raise ValueError(
                        f"Partición inválida: el elemento {elem} aparece en múltiples partes. "
                        f"Todas las partes deben ser disjuntas."
                    )
                elementos_vistos.add(elem)

        # Validar completitud
        union_partes = frozenset(elementos_vistos)
        n = int(self.tpm.shape[COLS_IDX])
        esperados = frozenset(range(n))
        if union_partes != esperados:
            faltantes = esperados - union_partes
            sobrantes = union_partes - esperados
            msg = f"Partición inválida: cobertura incompleta. "
            if faltantes:
                msg += f"Faltantes: {sorted(list(faltantes))}. "
            if sobrantes:
                msg += f"Sobrantes: {sorted(list(sobrantes))}. "
            raise ValueError(msg)

        # Validar cardinalidad
        if len(partes) > self.k:
            raise ValueError(
                f"Partición inválida: tiene {len(partes)} partes pero k={self.k}. "
                f"No debe haber más partes que k."
            )

        if self.verbose:
            print(
                f"[validar_particion] ✓ Partición válida: "
                f"{len(partes)} partes, {len(elementos_vistos)} elementos, disjunta y completa."
            )

        return True


if __name__ == "__main__":
    from pathlib import Path
    from src.controllers.manager import Manager

    sample_path = Path(__file__).resolve().parents[2] / "QNodes" / "src" / ".samples"
    gestor = Manager("1000", ruta_base=sample_path)
    tpm = gestor.cargar_red()

    kqnodes = KQNodes(gestor, k=3, refinar=False, verbose=True)
    resultado = kqnodes.aplicar_estrategia()
    print(resultado)
