from shared_src.models.enums.temporal_emd import TimeEMD
from shared_src.constants.base import ABC_START, ACTIVE, INACTIVE
from shared_src.models.enums.distance import MetricDistance
from shared_src.models.enums.notation import Notation


class Application:
    def __init__(self) -> None:
        self.semilla_numpy = 73
        self.pagina_red_muestra: str = ABC_START
        self.distancia_metrica: str = MetricDistance.HAMMING.value
        self.indexado_llegada: str = Notation.LIL_ENDIAN.value
        self.notacion_indexado: str = Notation.LIL_ENDIAN.value
        self.tiempo_emd: str = TimeEMD.EMD_EFECTO.value
        self.modo_estados: bool = ACTIVE
        self.profiler_habilitado: bool = True

    def set_pagina_red_muestra(self, pagina: str):
        self.pagina_red_muestra = pagina

    def set_notacion(self, tipo: Notation):
        self.notacion_indexado = tipo.value if isinstance(tipo, Notation) else str(tipo)

    def set_distancia(self, tipo: MetricDistance):
        self.distancia_metrica = (
            tipo.value if isinstance(tipo, MetricDistance) else str(tipo)
        )

    def set_estados_activos(self):
        self.modo_estados = ACTIVE

    def set_estados_inactivos(self):
        self.modo_estados = INACTIVE

    def set_tiempo_emd(self, tipo: TimeEMD):
        self.tiempo_emd = tipo.value if isinstance(tipo, TimeEMD) else str(tipo)

    def set_distancia_metrica(self, tipo: MetricDistance):
        self.distancia_metrica = (
            tipo.value if isinstance(tipo, MetricDistance) else str(tipo)
        )

    def activar_profiling(self) -> None:
        self.profiler_habilitado = True

    def desactivar_profiling(self) -> None:
        self.profiler_habilitado = False


aplicacion = Application()
