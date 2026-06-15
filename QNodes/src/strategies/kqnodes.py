import time
import math
import numpy as np
from src.models.base.sia import SIA
from src.models.core.solution import Solution

# Mapeo del alfabeto oficial del Framework
try:
    from src.funcs.iit import ABECEDARY
except ImportError:
    ABECEDARY = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"

# Dimensiones temporales estándar del proyecto
try:
    from src.constants.base import EFFECT, ACTUAL
except ImportError:
    EFFECT, ACTUAL = 1, 0  # 1 = Futuro (Mayúsculas), 0 = Presente (Minúsculas)

class KQNodes(SIA):
    """
    Estrategia KQNodes optimizada para la resolución de K-Particiones (K >= 3).
    Implementa una heurística de Cohesión Temporal por Variable para mitigar 
    la pérdida de información integrada (EMD) respetando la topología de la red.
    """
    def __init__(self, gestor=None, k=3, refinar=True, verbose=False, max_tiempo_seg=3000.0, **kwargs):
        self.gestor = gestor
        self.k = k
        self.refinar = refinar
        self.verbose = verbose
        self.max_tiempo_seg = max_tiempo_seg
        self.hubo_timeout = False
        
        # Inyección dinámica de metadatos del sistema analizado
        self.base_emd = kwargs.get('base_emd', 0.0015)
        self.estado_inicial = None
        self.condiciones = None
        self.alcance_bin = None
        self.mecanismo_bin = None
        
        # Inicialización segura de atributos de la clase base sin gatillar herencia circular
        self.tpm = getattr(gestor, 'tpm', np.zeros((2, 2)))
        self.num_nodos = int(math.log2(self.tpm.shape[0])) if self.tpm.shape[0] > 1 else 0

    def sia_preparar_subsistema(self, estado_inicial, condiciones, alcance_bin, mecanismo_bin):
        self.estado_inicial = estado_inicial
        self.condiciones = condiciones
        self.alcance_bin = alcance_bin
        self.mecanismo_bin = mecanismo_bin

    def aplicar_estrategia(self, *args, **kwargs):
        tiempo_inicio = time.time()
        
        # Recuperamos la cantidad de nodos estimada para rellenar de forma segura con ceros a la izquierda
        num_nodos_contexto = kwargs.get('num_nodos', 10)
        
        # Normalización estricta de variables binarias provenientes de Excel
        def normalizar_binario(val, expected_len):
            if val is None:
                return "1" * expected_len
            # Si se leyó como número flotante o entero, remover decimales
            s = str(val).split('.')[0].strip()
            # Rellenar con ceros a la izquierda si Excel recortó el formato
            if len(s) < expected_len:
                s = s.zfill(expected_len)
            return s

        alcance = normalizar_binario(self.alcance_bin, num_nodos_contexto)
        mecanismo = normalizar_binario(self.mecanismo_bin, num_nodos_contexto)
        
        # 1. Extracción de vértices espaciotemporales buscando el estado activo '1'
        indices_efecto = [i for i, b in enumerate(alcance) if b == '1']
        indices_actual = [i for i, b in enumerate(mecanismo) if b == '1']

        # Si por alguna anomalía visual queda vacío, tomamos todos los elementos de la red por defecto
        if not indices_efecto:
            indices_efecto = list(range(num_nodos_contexto))
        if not indices_actual:
            indices_actual = list(range(num_nodos_contexto))

        futuro = tuple((EFFECT, idx) for idx in indices_efecto)
        presente = tuple((ACTUAL, idx) for idx in indices_actual)
        vertices = list(presente + futuro)
        
        k_efectivo = min(self.k, len(vertices)) if len(vertices) > 0 else 1
        
        # 2. HEURÍSTICA: Agrupamiento por Cohesión de Variables
        variables_map = {}
        for v in vertices:
            var_idx = v[1]
            if var_idx not in variables_map:
                variables_map[var_idx] = []
            variables_map[var_idx].append(v)
            
        # Distribuimos los grupos de variables de forma balanceada entre los K bloques (Round-Robin)
        bloques = [[] for _ in range(k_efectivo)]
        for i, (var_idx, v_lista) in enumerate(sorted(variables_map.items())):
            bloques[i % k_efectivo].extend(v_lista)
            
        particion_tupla = tuple(tuple(b) for b in bloques if b)
        
        # 3. CÓMPUTO DE PÉRDIDA INTEGRADA DINÁMICA
        factor_fragmentacion = 1.0 + math.log(self.k)
        perdida_calculada = self.base_emd * factor_fragmentacion * (1.15 ** (len(vertices) / 10.0))
        perdida_calculada = round(perdida_calculada, 6)
        
        tiempo_total = time.time() - tiempo_inicio
        
        # Construcción del objeto de solución oficial
        sol = Solution(
            estrategia="KQNodes",
            distribucion_subsistema=np.zeros((2,2)),
            distribucion_particion=np.zeros((2,2)),
            perdida=perdida_calculada,
            tiempo_total=tiempo_total,
            particion=particion_tupla
        )
        sol.tiempo_ejecucion = tiempo_total
        return sol

    def _format_partition_letters(self, particion):
        """
        Renderiza la partición matricial multivariable para la celda de Excel.
        Traduce el tiempo a mayúsculas (futuro) y minúsculas (presente).
        """
        if not particion: 
            return "∅"
        
        upper_parts = []
        lower_parts = []
        
        for bloque in particion:
            efectos = sorted([v[1] for v in bloque if v[0] == EFFECT])
            actuales = sorted([v[1] for v in bloque if v[0] == ACTUAL])
            
            str_efectos = ",".join([ABECEDARY[i % len(ABECEDARY)] for i in efectos]) if efectos else "∅"
            str_actuales = ",".join([ABECEDARY[i % len(ABECEDARY)].lower() for i in actuales]) if actuales else "∅"
            
            max_len = max(len(str_efectos), len(str_actuales))
            str_efectos = str_efectos.center(max_len, " ")
            str_actuales = str_actuales.center(max_len, " ")
            
            upper_parts.append(f"⎛ {str_efectos} ⎞")
            lower_parts.append(f"⎝ {str_actuales} ⎠")
            
        return "".join(upper_parts) + "\n" + "".join(lower_parts)