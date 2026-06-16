from pathlib import Path

import numpy as np
import time
from typing import List, Callable
from datetime import datetime

from shared_src.models.base.sia import SIA
from shared_src.models.core.solution import Solution
from shared_src.models.core.system import System
from shared_src.funcs.iit import emd_efecto



class KQNodes(SIA):
    """Estrategia KQNodes para k-partición de mínima información."""

    def __init__(
        self,
        gestor,
        k: int = 2,
        refinar: bool = True,
        verbose: bool = False,
        max_tiempo_seg: float = 300.0,
    ):
        """Inicializa el algoritmo KQNodes.

        Args:
            gestor: Gestor de datos / fuente de TPM.
            k (int): Número de particiones para k-MIP.
            refinar (bool): Si se debe aplicar refinamiento local.
            verbose (bool): Si se imprime información de ejecución.
            max_tiempo_seg (float): Tiempo máximo por fase de Queyranne (segundos).
                Al superarse, la fase aborta y se devuelve la mejor partición
                parcial encontrada; self.hubo_timeout queda en True.
        """
        self.gestor = gestor
        self.k = k
        self.refinar = refinar
        self.verbose = verbose
        # Tiempo máximo por iteración de Queyranne (segundos)
        self.max_tiempo_seg = float(max_tiempo_seg)
        # Indicador si se produjo un timeout durante la ejecución
        self.hubo_timeout: bool = False

        self.tpm: np.ndarray = self.gestor.cargar_red()
        super().__init__(self.tpm)

        self._memo_marginal: dict[tuple, np.ndarray] = {}
        self._memo_perdida_final: dict[tuple, float] = {}

    def aplicar_estrategia(self) -> Solution:
        """Ejecuta la estrategia de k-partición y retorna la solución encontrada.

        Flujo orquestador:
        1. Ejecutar Queyranne iterativo para encontrar k particiones.
        2. Validar que la partición es válida (disjunta, completa, no-vacía).
        3. Si self.refinar=True, aplicar hill climbing de intercambio local.
        4. Retornar Solution con partición, pérdida y tiempo total.

        Retorna:
            Solution: Objeto con partición óptima, pérdida y tiempo de ejecución.

        Lanza:
            ValueError: Si la partición falla validación.
        """
        # Cronómetro de ejecución total
        t0 = time.perf_counter()

        # Invalidar cachés por-caso (dependen del subsistema actual)
        self._memo_marginal = {}
        self._memo_perdida_final = {}

        n_ss = self.sia_dists_marginales.size
        print(f"[KQNodes] Iniciando k={self.k}, n_subsistema={n_ss}, n_tpm={int(self.tpm.shape[1])}, timestamp={datetime.now()}")

        # Paso 1: Ejecutar Queyranne iterativo
        partes_queyranne = self._queyranne_iterativo()

        # Paso 2b: Refinamiento divisivo (top-down, complementario a Queyranne greedy)
        partes_div = self._refinamiento_divisivo()

        # Elegir la partición con menor pérdida entre ambos enfoques
        loss_q = float("inf")
        loss_d = float("inf")
        try:
            loss_q = self._calcular_perdida_final(partes_queyranne)
        except Exception:
            pass
        try:
            loss_d = self._calcular_perdida_final(partes_div)
        except Exception:
            pass

        if loss_d < loss_q:
            partes = partes_div
            if self.verbose:
                print(f"[KQNodes] Divisivo ({loss_d:.4f}) supera Queyranne ({loss_q:.4f}) — usando divisivo")
        else:
            partes = partes_queyranne
            if self.verbose:
                print(f"[KQNodes] Queyranne ({loss_q:.4f}) ≤ Divisivo ({loss_d:.4f}) — usando Queyranne")

        # Paso 3: Validar partición
        self._validar_particion(partes)

        # Paso 4: Refinar si es necesario
        if self.refinar:
            partes = self._intercambio_local(partes)

        # Paso 5: Calcular tiempo total en milisegundos
        tiempo_ms = (time.perf_counter() - t0) * 1000.0

        # Evaluar pérdida final como EMD(global, ⊗ marginals de la k-partición completa)
        perdida_final = float("inf")
        try:
            if partes:
                perdida_final = self._calcular_perdida_final(partes)
        except Exception:
            perdida_final = float("inf")

        # Imprimir bloque final exacto para parsing externo
        horas = tiempo_ms / 1000.0 / 3600.0
        minutos = tiempo_ms / 1000.0 / 60.0
        segundos = tiempo_ms / 1000.0

        # Asegurar que alcance/mecanismo estén disponibles (pueden haber sido seteados en main)
        alcance = getattr(self, "alcance", "")
        mecanismo = getattr(self, "mecanismo", "")

        particion_formateada = self._format_partition_letters(partes)

        print("=== RESULTADO KQNodes ===")
        print(f"k: {self.k}")
        print(f"Alcance: {alcance}")
        print(f"Mecanismo: {mecanismo}")
        print(f"Partición: {particion_formateada}")
        print(f"Pérdida: {perdida_final:.7f}")
        print(f"Tiempo: Horas: {horas:.2f} = Minutos: {minutos:.1f} = Segundos: {segundos:.4f}")
        print(f"Timeout: {'Sí' if self.hubo_timeout else 'No'}")
        print("=== FIN RESULTADO ===")

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

    def _calcular_perdida_final(self, partes: List[frozenset]) -> float:
        """Calcula EMD(global, ⊗_i marginal(P_i)) para la k-partición completa.

        A diferencia de _evaluar_perdida_restringida (que evalúa una extracción
        parcial durante Queyranne), este método recibe la partición definitiva y
        computa la pérdida real comparando la distribución global con el producto
        tensorial de las distribuciones marginales de cada parte.
        """
        # K3: cache por clave de partición — evita recomputar para la misma configuración
        _cache_key = tuple(tuple(sorted(p)) for p in sorted(partes, key=min))
        if _cache_key in self._memo_perdida_final:
            return self._memo_perdida_final[_cache_key]

        distribucion_global = self.sia_dists_marginales
        n = distribucion_global.size
        producto_por_variable = np.empty(n, dtype=np.float32)
        producto_por_variable.fill(np.nan)

        for parte in partes:
            indices_local = np.array(sorted(list(parte)), dtype=np.int8)
            indices_global = self.sia_subsistema.indices_ncubos[indices_local]
            # K1: cache de marginal por conjunto de índices globales
            memo_key = tuple(int(x) for x in indices_global)
            if memo_key not in self._memo_marginal:
                try:
                    subsistema_parte = self.sia_subsistema.substraer(
                        alcance_idx=np.setdiff1d(self.sia_subsistema.indices_ncubos, indices_global),
                        mecanismo_dims=np.setdiff1d(self.sia_subsistema.dims_ncubos, indices_global),
                    )
                    self._memo_marginal[memo_key] = subsistema_parte.distribucion_marginal()
                except Exception:
                    self._memo_marginal[memo_key] = np.ones(len(parte), dtype=np.float32) / len(parte)
            dist_parte = self._memo_marginal[memo_key]

            if dist_parte.size != indices_local.size:
                if self.verbose:
                    print(f"  [calcular_perdida_final] dim mismatch parte {sorted(parte)}")
                self._memo_perdida_final[_cache_key] = float("inf")
                return float("inf")
            producto_por_variable[indices_local] = dist_parte.astype(np.float32, copy=False)  # K5

        if np.isnan(producto_por_variable).any():
            missing = np.where(np.isnan(producto_por_variable))[0]
            if self.verbose:
                print(f"  [calcular_perdida_final] variables sin asignar: {missing.tolist()}")
            self._memo_perdida_final[_cache_key] = float("inf")
            return float("inf")

        resultado = float(emd_efecto(
            u=distribucion_global.astype(np.float32, copy=False),  # K5
            v=producto_por_variable,
        ))
        self._memo_perdida_final[_cache_key] = resultado
        return resultado

    def _queyranne_iterativo(self) -> List[frozenset]:
        """Ejecuta el algoritmo de Queyranne iterativo sobre el subsistema actual.

        Algoritmo:
        1. V_res = frozenset de todos los índices [0..n-1].
        2. Para i in 1..k-1:
           a. define f_i(S) = _evaluar_perdida_restringida(S, V_res, partes_fijas)
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

        # Número de variables = tamaño real del subsistema actual
        n = self.sia_dists_marginales.size

        # Conjunto de variables restantes por particionar
        V_res: frozenset = frozenset(range(n))
        partes_fijas: List[frozenset] = []

        # Función auxiliar: implementación local de Queyranne sobre un dominio V
        def _queyranne_on_set(V: frozenset, f: Callable[[frozenset], float], t_iter_start: float) -> frozenset:
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
                # Comprobar timeout por iteración
                if (time.perf_counter() - t_iter_start) > self.max_tiempo_seg:
                    # Timeout: devolver la mejor solución encontrada hasta ahora
                    if self.verbose:
                        print(f"  [Queyranne] timeout alcanzado tras {self.max_tiempo_seg}s, abortando fase")
                    # Indicar al llamador que hubo timeout
                    nonlocal_timed_out[0] = True
                    return best_set if best_set else (A[0] if A else frozenset())
                # Secuencia greedily construida
                S_sequence: List[frozenset] = []
                S_union: frozenset = frozenset()
                remaining = A.copy()

                # Construir secuencia de pendientes por máximos incrementos
                for _ in range(len(A)):
                    best_a = None
                    best_gain = None
                    val_S_union = f(S_union)  # K2: invariante dentro del loop interno
                    for a in remaining:
                        # Comprobar timeout dentro de la construcción de secuencia
                        if (time.perf_counter() - t_iter_start) > self.max_tiempo_seg:
                            if self.verbose:
                                print(f"  [Queyranne] timeout dentro de construcción de secuencia")
                            nonlocal_timed_out[0] = True
                            return best_set if best_set else (A[0] if A else frozenset())
                        union = frozenset(set(S_union) | set(a))
                        # ganancia marginal: f(S ∪ a) - f(S)
                        gain = f(union) - val_S_union  # K2
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
        # Variable compartida para indicar timeout desde el closure
        nonlocal_timed_out = [False]

        for i in range(1, max(1, self.k)):
            # Print de iteración solicitado
            print(f"[KQNodes] Iteración {i}/{self.k-1}, |V_res|={len(V_res)}")
            # f_i: función objetivo restringida que recibe un subconjunto S
            def f_i(S: frozenset) -> float:
                return self._evaluar_perdida_restringida(S, V_res, partes_fijas)

            # Ejecutar Queyranne sobre V_res con f_i (respetando timeout por iteración)
            t_iter_start = time.perf_counter()
            S_opt = _queyranne_on_set(V_res, f_i, t_iter_start)

            # Si el closure indicó timeout, propagar y salir
            if nonlocal_timed_out[0]:
                self.hubo_timeout = True
                if self.verbose:
                    print(f"[KQNodes] Iteración {i} abortada por timeout. Devolviendo partición parcial.")
                # Añadir la parte extraída si no vacía
                if S_opt:
                    partes_fijas.append(frozenset(S_opt))
                    V_res = frozenset(set(V_res) - set(S_opt))
                break

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

        # Si no alcanzamos k partes, dividir iterativamente las partes más grandes
        # hasta llegar a k (o no poder dividir más).
        # Nueva heurística: priorizar extracción de singletons (elementos individuales)
        # desde la parte más grande, porque suele ser la forma más rápida de
        # aumentar el número de partes y garantizar que se alcance exactamente k.
        while len(partes_fijas) < self.k:
            # seleccionar la parte más grande con tamaño > 1
            sizes = [(idx, len(p)) for idx, p in enumerate(partes_fijas)]
            candidates = [idx for idx, sz in sizes if sz > 1]
            if not candidates:
                # no hay partes divisibles
                break
            # elegir la parte con mayor tamaño
            j = max(candidates, key=lambda i: len(partes_fijas[i]))
            parte_a_dividir = partes_fijas.pop(j)

            V_local = frozenset(parte_a_dividir)
            otras_partes = partes_fijas.copy()

            # Heurística preferida: extraer el singleton que minimice la pérdida
            best_e = None
            best_loss = float("inf")
            for e in sorted(list(V_local)):
                loss = self._evaluar_perdida_restringida(frozenset([e]), V_local, otras_partes)
                if loss < best_loss:
                    best_loss = loss
                    best_e = e

            # Si no se encontró singleton válido (improbable), intentar dividir vía Queyranne
            if best_e is None:
                # intentar dividir vía Queyranne local como último recurso
                def f_local(S: frozenset) -> float:
                    return self._evaluar_perdida_restringida(S, V_local, otras_partes)

                t_split_start = time.perf_counter()
                S_opt = _queyranne_on_set(V_local, f_local, t_split_start)
                if nonlocal_timed_out[0]:
                    self.hubo_timeout = True
                    partes_fijas.append(V_local)
                    break
                S_opt = frozenset(S_opt)
                if not S_opt or S_opt == V_local:
                    partes_fijas.append(V_local)
                    break
                complemento = frozenset(set(V_local) - set(S_opt))
                partes_fijas.append(S_opt)
                partes_fijas.append(complemento)
            else:
                S_opt = frozenset([best_e])
                complemento = frozenset(set(V_local) - set(S_opt))
                partes_fijas.append(S_opt)
                partes_fijas.append(complemento)

        return partes_fijas

    def _evaluar_perdida_restringida(
        self,
        S: frozenset,
        V_res: frozenset,
        partes_fijas: List[frozenset],
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

        Returns:
            float: Pérdida (EMD) asociada a la partición parcial.

        Ejemplo comentado:
            S = frozenset({0})
            V_res = frozenset({0, 1, 2})
            partes_fijas = []

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
            indices_local = np.array(sorted(list(parte)), dtype=np.int8)
            indices_global = self.sia_subsistema.indices_ncubos[indices_local]
            # K1: cache de marginal por conjunto de índices globales
            memo_key = tuple(int(x) for x in indices_global)
            if memo_key not in self._memo_marginal:
                try:
                    subsistema_parte = self.sia_subsistema.substraer(
                        alcance_idx=np.setdiff1d(self.sia_subsistema.indices_ncubos, indices_global),
                        mecanismo_dims=np.setdiff1d(self.sia_subsistema.dims_ncubos, indices_global),
                    )
                    self._memo_marginal[memo_key] = subsistema_parte.distribucion_marginal()
                except Exception:
                    self._memo_marginal[memo_key] = np.ones(len(parte), dtype=np.float32) / len(parte)
            distribuciones_partes.append(self._memo_marginal[memo_key])

        # Construir un vector de probabilidades por variable.
        # Usar el tamaño del subsistema (coincide con sia_dists_marginales.size).
        n = self.sia_dists_marginales.size
        producto_por_variable = np.empty(n, dtype=np.float32)
        producto_por_variable.fill(np.nan)

        # Rellenar las posiciones con las marginals de cada parte
        for parte, dist_parte in zip(partes_a_combinar, distribuciones_partes):
            indices_parte = np.array(sorted(list(parte)), dtype=np.int64)
            if dist_parte.size != indices_parte.size:
                # Falla: caída segura a infinito si las dimensiones no coinciden
                if self.verbose:
                    print(
                        f"  [eval_perdida] dist_parte.size ({dist_parte.size}) != indices_parte.size ({indices_parte.size}) -> inf"
                    )
                return float("inf")
            producto_por_variable[indices_parte] = dist_parte.astype(np.float32)

        # Si quedaron posiciones sin asignar, completar con la distribución global
        # (no ideal, pero evita NaNs). También registra en verbose.
        if np.isnan(producto_por_variable).any():
            if self.verbose:
                missing = np.where(np.isnan(producto_por_variable))[0]
                print(f"  [eval_perdida] faltan variables {missing}, rellenando con global")
            producto_por_variable[np.isnan(producto_por_variable)] = (
                distribucion_global[np.isnan(producto_por_variable)]
            )

        perdida = emd_efecto(
            u=distribucion_global.astype(np.float32, copy=False),  # K5
            v=producto_por_variable,
        )

        if self.verbose:
            print(
                f"  [eval_perdida] S={sorted(list(S))} -> pérdida={perdida:.6f}"
            )

        return float(perdida)

    def _index_to_letter(self, idx: int) -> str:
        if idx < 26:
            return chr(ord("A") + idx)
        else:
            return chr(ord("a") + (idx - 26) % 26)

    def _format_partition_letters(self, partes: List[frozenset]) -> str:
        # Convierte una lista de frozensets en '{A,B} | {C,D}'
        if not partes:
            return "{}"
        grupos = []
        for parte in partes:
            items = sorted(list(parte))
            if not items:
                grupos.append("{}")
                continue
            letras = [self._index_to_letter(int(i)) for i in items]
            grupos.append("{" + ",".join(letras) + "}")
        return " | ".join(grupos)

    def _refinamiento_divisivo(self) -> List[frozenset]:
        """Construye una k-partición de forma divisiva (top-down).

        Algoritmo:
        1. Parte inicial: el conjunto completo de nodos del subsistema como una sola parte.
        2. En cada uno de los k-1 pasos, evalúa extraer cada nodo individual de cada
           parte existente como una nueva parte propia.
        3. Escoge la extracción que produce la menor pérdida total (_calcular_perdida_final).
        4. Repite hasta tener k partes.

        Complejidad: O((k-1) · n_ss · eval_perdida_final).

        Ventaja frente a Queyranne puro: la función objetivo en cada paso es la
        pérdida FINAL de la k-partición completa, no una estimación parcial.
        Esto evita el sesgo greedy de la iteración 1 de Queyranne (que optimiza
        solo la bipartición sin considerar las iteraciones siguientes).
        """
        n_ss = self.sia_dists_marginales.size
        partes: List[frozenset] = [frozenset(range(n_ss))]

        for _ in range(self.k - 1):
            mejor_loss = float("inf")
            mejor_partes: List[frozenset] | None = None

            for idx, parte in enumerate(partes):
                if len(parte) <= 1:
                    continue
                otras = partes[:idx] + partes[idx + 1:]
                for x in sorted(parte):
                    candidato = otras + [frozenset([x]), parte - {x}]
                    try:
                        loss = self._calcular_perdida_final(candidato)
                    except Exception:
                        loss = float("inf")
                    if loss < mejor_loss:
                        mejor_loss = loss
                        mejor_partes = candidato

            if mejor_partes is None:
                break
            partes = mejor_partes

        return partes

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
        perdida_inicial = self._calcular_perdida_final(partes_actuales)

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

                        perdida_candidata = self._calcular_perdida_final(partes_candidatas)

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

        # Validar completitud contra el tamaño real del subsistema
        union_partes = frozenset(elementos_vistos)
        n = self.sia_dists_marginales.size
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
    from shared_src.controllers.manager import Manager

    sample_path = Path(__file__).resolve().parents[2] / "QNodes" / "src" / ".samples"
    gestor = Manager("1000", ruta_base=sample_path)
    tpm = gestor.cargar_red()

    kqnodes = KQNodes(gestor, k=3, refinar=False, verbose=True)
    resultado = kqnodes.aplicar_estrategia()
    print(resultado)
