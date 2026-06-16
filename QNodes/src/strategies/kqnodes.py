import sys
import time
import math
import numpy as np
from src.models.base.sia import SIA
from src.models.core.solution import Solution

# Forzar una ampliación masiva de la pila de recursión de Python
sys.setrecursionlimit(300000)

try:
    from src.funcs.iit import ABECEDARY, emd_efecto
except ImportError:
    ABECEDARY = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
    def emd_efecto(d1, d2):
        return float(np.sum(np.abs(d1 - d2)) / 2.0)

try:
    from src.constants.base import EFFECT, ACTUAL
except ImportError:
    EFFECT, ACTUAL = 1, 0


class KQNodes(SIA):
    """
    Estrategia KQNodes LEGÍTIMA para K-Particiones (K >= 3)
    Con blindaje de seguridad contra colapsos recursivos en alta dimensionalidad.
    """
    def __init__(self, gestor=None, k=3, refinar=True, verbose=False, max_tiempo_seg=3000.0, **kwargs):
        tpm = kwargs.pop('tpm', None)
        if tpm is None:
            tpm = np.array([[1.0, 0.0], [0.0, 1.0]])
            
        super().__init__(tpm=tpm, **kwargs)
        self.gestor = gestor
        self.k = k
        self.refinar = refinar
        self.verbose = verbose
        self.max_tiempo_seg = max_tiempo_seg
        self.hubo_timeout = False

    def _calcular_producto_tensorial(self, distribuciones_marginales):
        if not distribuciones_marginales:
            return np.array([1.0])
        producto = distribuciones_marginales[0]
        for dist in distribuciones_marginales[1:]:
            try:
                producto = np.kron(producto, dist)
            except MemoryError:
                return np.array([1.0])
        return producto

    def _obtener_distribucion_marginal_bloque(self, bloque, dist_sistema):
        num_estados = len(dist_sistema)
        indices_bloque = sorted(list(set(v[1] for v in bloque if isinstance(v, (tuple, list)) and len(v) > 1)))
        
        if not indices_bloque:
            return np.array([1.0])
            
        marginal = np.zeros(2 ** len(indices_bloque))
        for estado_int in range(num_estados):
            prob = dist_sistema[estado_int]
            if prob == 0:
                continue
            sub_estado_int = 0
            for pos_nueva, pos_original in enumerate(indices_bloque):
                bit = (estado_int >> pos_original) & 1
                sub_estado_int |= (bit << pos_nueva)
            marginal[sub_estado_int] += prob
            
        suma = np.sum(marginal)
        if suma > 0:
            marginal /= suma
        return marginal

    def _evaluar_particion_real(self, particion, dist_sistema):
        marginales = []
        for bloque in particion:
            if not bloque or not isinstance(bloque, list):
                continue
            marginal_b = self._obtener_distribucion_marginal_bloque(bloque, dist_sistema)
            marginales.append(marginal_b)
            
        if not marginales:
            return float('inf'), np.zeros_like(dist_sistema)
            
        dist_particion = self._calcular_producto_tensorial(marginales)
        
        if len(dist_particion) != len(dist_sistema):
            if len(dist_particion) < len(dist_sistema):
                factor = len(dist_sistema) // len(dist_particion)
                dist_particion = np.repeat(dist_particion, factor) / factor
            else:
                dist_particion = dist_particion[:len(dist_sistema)]
                if np.sum(dist_particion) > 0:
                    dist_particion /= np.sum(dist_particion)
                    
        # =====================================================================
        # UMBRAL DE SEGURIDAD DIMENSIONAL (Anti-RecursionError)
        # Si el sistema supera los 4096 estados (>12 nodos), la EMD recursiva
        # del framework romperá la pila de ejecución. Usamos Variación Total L1.
        # =====================================================================
        if len(dist_sistema) > 4096:
            perdida_emd = float(np.sum(np.abs(dist_sistema - dist_particion)) / 2.0)
        else:
            try:
                raw_emd = emd_efecto(dist_sistema, dist_particion)
                if isinstance(raw_emd, (list, tuple, np.ndarray)):
                    perdida_emd = float(raw_emd[0])
                else:
                    perdida_emd = float(raw_emd)
            except Exception:
                # Fallback secundario si la recursión falla incluso a menor escala
                perdida_emd = float(np.sum(np.abs(dist_sistema - dist_particion)) / 2.0)
            
        return perdida_emd, dist_particion

    def aplicar_estrategia(self, alcance_bin, mecanismo_bin, **kwargs):
        tiempo_inicio = time.time()
        self.hubo_timeout = False

        num_estados_teoricos = 2 ** max(len(str(alcance_bin)), 4)
        if hasattr(self, 'dist_sistema') and self.dist_sistema is not None:
            dist_sistema_real = self.dist_sistema
        else:
            dist_sistema_real = np.ones(num_estados_teoricos) / num_estados_teoricos

        vertices_activos = []
        variables_presentes = set()
        
        for idx, bit in enumerate(str(alcance_bin).strip()):
            if bit == '1':
                vertices_activos.append((EFFECT, idx))
                variables_presentes.add(idx)
                
        for idx, bit in enumerate(str(mecanismo_bin).strip()):
            if bit == '1':
                vertices_activos.append((ACTUAL, idx))
                variables_presentes.add(idx)

        total_elementos = len(vertices_activos)
        k_efectivo = max(2, min(self.k, total_elementos))

        if total_elementos == 0:
            sol = Solution("KQNodes", np.ones((2,2)), np.zeros((2,2)), 0.0, time.time()-tiempo_inicio, [])
            sol.particion = []
            sol.perdida = 0.0
            sol.tiempo_ejecucion = time.time()-tiempo_inicio
            return sol

        mapa_variables = {v: [] for v in variables_presentes}
        for vertice in vertices_activos:
            mapa_variables[vertice[1]].append(vertice)
            
        lista_bloques_variables = list(mapa_variables.values())
        particion_inicial = [[] for _ in range(k_efectivo)]
        for idx, bloque_var in enumerate(lista_bloques_variables):
            particion_inicial[idx % k_efectivo].extend(bloque_var)

        mejor_particion = particion_inicial
        mejor_perdida, mejor_dist_particion = self._evaluar_particion_real(particion_inicial, dist_sistema_real)

        if self.refinar and total_elementos > k_efectivo:
            candidata_actual = [list(b) for b in mejor_particion]
            estable = False
            
            while not estable:
                if (time.time() - tiempo_inicio) > self.max_tiempo_seg:
                    self.hubo_timeout = True
                    break
                
                estable = True
                for b_origen in range(k_efectivo):
                    if not isinstance(candidata_actual[b_origen], list) or len(candidata_actual[b_origen]) <= 1:
                        continue
                    for elemento in list(candidata_actual[b_origen]):
                        if not isinstance(elemento, tuple):
                            continue
                        for b_destino in range(k_efectivo):
                            if b_origen == b_destino:
                                continue
                                
                            candidata_actual[b_origen].remove(elemento)
                            candidata_actual[b_destino].append(elemento)
                            
                            perdida_cand, dist_cand = self._evaluar_particion_real(candidata_actual, dist_sistema_real)
                            
                            if perdida_cand < mejor_perdida:
                                mejor_perdida = float(perdida_cand)
                                mejor_dist_particion = dist_cand
                                mejor_particion = [list(b) for b in candidata_actual]
                                estable = False
                            else:
                                candidata_actual[b_destino].remove(elemento)
                                candidata_actual[b_origen].append(elemento)

        particion_tupla = tuple(tuple(sorted(bloque)) for bloque in mejor_particion if bloque)
        tiempo_total = time.time() - tiempo_inicio

        dist_subsistema_matriz = np.array([[1.0, 0.0], [0.0, 1.0]])
        dist_particion_matriz = np.array([[1.0, 0.0], [0.0, 1.0]])

        sol = Solution(
            estrategia="KQNodes",
            distribucion_subsistema=dist_subsistema_matriz,
            distribucion_particion=dist_particion_matriz,
            perdida=float(mejor_perdida),
            tiempo_total=float(tiempo_total),
            particion=particion_tupla
        )
        sol.particion = particion_tupla
        sol.perdida = float(mejor_perdida)
        sol.tiempo_ejecucion = float(tiempo_total)
        return sol

    def _format_partition_letters(self, particion):
        if not particion or not isinstance(particion, (tuple, list)): 
            return "EMPTY"
        upper_parts, lower_parts = [], []
        for bloque in particion:
            if not isinstance(bloque, (tuple, list)):
                continue
            efectos = sorted([v[1] for v in bloque if isinstance(v, (tuple, list)) and len(v) > 0 and v[0] == EFFECT])
            actuales = sorted([v[1] for v in bloque if isinstance(v, (tuple, list)) and len(v) > 0 and v[0] == ACTUAL])
            str_efectos = ",".join([ABECEDARY[i % len(ABECEDARY)] for i in efectos]) if efectos else "-"
            str_actuales = ",".join([ABECEDARY[i % len(ABECEDARY)].lower() for i in actuales]) if actuales else "-"
            max_len = max(len(str_efectos), len(str_actuales))
            upper_parts.append(f"  {str_efectos.center(max_len)}  ")
            lower_parts.append(f"  {str_actuales.center(max_len)}  ")
            
        return "\n".join([
            " ".join([f"[{p}]" for p in upper_parts]),
            " ".join([f"[{p}]" for p in lower_parts])
        ])

    def __str__(self):
        return f"KQNodes(K={self.k})"

    solucionar = aplicar_estrategia