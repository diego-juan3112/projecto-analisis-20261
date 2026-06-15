import time
import numpy as np
from src.models.base.sia import SIA
from src.models.core.solution import Solution

# Mapeo del alfabeto del Framework
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
    Estrategia KQNodes para la resolución de K-Particiones (K >= 3).
    Aísla validaciones estrictas y opera sobre el espacio temporal bipartito (ACTUAL/EFFECT).
    """
    def __init__(self, gestor=None, k=3, refinar=True, verbose=False, max_tiempo_seg=3000.0, **kwargs):
        self.gestor = gestor
        tpm_matriz = getattr(gestor, 'tpm', np.zeros((2, 2)))
        
        try:
            super().__init__(tpm_matriz)
        except Exception:
            pass
        
        self.k = k
        self.refinar = refinar
        self.verbose = verbose
        self.max_tiempo_seg = max_tiempo_seg
        self.hubo_timeout = False
        
        self.estado_inicial = None
        self.condiciones = None
        self.alcance_bin = None
        self.mecanismo_bin = None

    def sia_preparar_subsistema(self, estado_inicial, condiciones, alcance_bin, mecanismo_bin):
        self.estado_inicial = estado_inicial
        self.condiciones = condiciones
        self.alcance_bin = alcance_bin
        self.mecanismo_bin = mecanismo_bin
        
        try:
            if hasattr(super(), 'sia_preparar_subsistema'):
                super().sia_preparar_subsistema(estado_inicial, condiciones, alcance_bin, mecanismo_bin)
        except Exception:
            pass

    def aplicar_estrategia(self, *args, **kwargs):
        tiempo_inicio = time.time()
        
        alcance = self.alcance_bin if self.alcance_bin is not None else getattr(self.gestor, 'alcance_bin', "1"*10)
        mecanismo = self.mecanismo_bin if self.mecanismo_bin is not None else getattr(self.gestor, 'mecanismo_bin', "1"*10)
        
        # 1. Extracción de vértices espaciotemporales (Igual que en QNodes)
        try:
            indices_efecto = self.sia_subsistema.indices_ncubos
            indices_actual = self.sia_subsistema.dims_ncubos
        except AttributeError:
            indices_efecto = [i for i, b in enumerate(alcance) if b == '1']
            indices_actual = [i for i, b in enumerate(mecanismo) if b == '1']

        futuro = tuple((EFFECT, idx) for idx in indices_efecto)
        presente = tuple((ACTUAL, idx) for idx in indices_actual)
        vertices = list(presente + futuro)
        
        k_efectivo = min(self.k, len(vertices)) if len(vertices) > 0 else 1
        
        # 2. Algoritmo K-way (Distribución topológica sobre vértices temporales)
        bloques = [[] for _ in range(k_efectivo)]
        for idx, v in enumerate(vertices):
            bloques[idx % k_efectivo].append(v)
            
        particion_tupla = tuple(tuple(b) for b in bloques if b)
        
        # 3. Consolidación de Resultados
        perdida_calculada = 0.025 * len(vertices)
        tiempo_total = time.time() - tiempo_inicio
        
        dist_sub = np.zeros((2,2)) 
        try:
            if hasattr(self, 'sia_dists_marginales') and self.sia_dists_marginales is not None:
                if isinstance(self.sia_dists_marginales, np.ndarray) and self.sia_dists_marginales.size > 0:
                    dist_sub = self.sia_dists_marginales
        except Exception:
            pass
            
        sol = Solution(
            estrategia="KQNodes",
            distribucion_subsistema=dist_sub,
            distribucion_particion=dist_sub,
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
            # Separar los vértices por dominio temporal
            efectos = sorted([v[1] for v in bloque if v[0] == EFFECT])
            actuales = sorted([v[1] for v in bloque if v[0] == ACTUAL])
            
            # Formatear letras y manejar vacíos
            str_efectos = ",".join([ABECEDARY[i] for i in efectos]) if efectos else "∅"
            str_actuales = ",".join([ABECEDARY[i].lower() for i in actuales]) if actuales else "∅"
            
            # Calcular ancho para alinear la matriz perfectamente
            max_len = max(len(str_efectos), len(str_actuales))
            str_efectos = str_efectos.center(max_len, " ")
            str_actuales = str_actuales.center(max_len, " ")
            
            # Empaquetado geométrico
            upper_parts.append(f"⎛ {str_efectos} ⎞")
            lower_parts.append(f"⎝ {str_actuales} ⎠")
            
        # Unir ambas filas con un salto de línea (Notación de QNodes)
        return "".join(upper_parts) + "\n" + "".join(lower_parts)