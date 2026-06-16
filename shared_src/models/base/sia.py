from abc import ABC, abstractmethod
import time

import numpy as np
import numpy.typing as NDArray

from shared_src.constants.models import SIA_PREPARATION_TAG
from shared_src.middlewares.slogger import SafeLogger
from shared_src.models.core.system import System

from shared_src.constants.base import (
    COLS_IDX,
    FLOAT_ZERO,
    STR_ZERO,
)
from shared_src.constants.error import (
    ERROR_ESPACIOS_INCOMPATIBLES,
)


class SIA(ABC):
    def __init__(self, tpm: np.ndarray) -> None:
        self.tpm = tpm
        self.sia_logger = SafeLogger(SIA_PREPARATION_TAG)

        self.sia_subsistema: System
        self.sia_dists_marginales: NDArray[np.float32]
        self.sia_tiempo_inicio: float = FLOAT_ZERO

    @abstractmethod
    def aplicar_estrategia(self):
        pass

    def sia_preparar_subsistema(
        self,
        estado_inicial: str,
        condicion: str,
        alcance: str,
        mecanismo: str,
    ):
        if self.chequear_parametros(estado_inicial, condicion, alcance, mecanismo):
            raise Exception(ERROR_ESPACIOS_INCOMPATIBLES)

        dims_condicionadas = np.array(
            [ind for ind, bit in enumerate(condicion) if bit == STR_ZERO], dtype=np.int8
        )
        dims_alcance = np.array(
            [ind for ind, bit in enumerate(alcance) if bit == STR_ZERO], dtype=np.int8
        )
        dims_mecanismo = np.array(
            [ind for ind, bit in enumerate(mecanismo) if bit == STR_ZERO], dtype=np.int8
        )
        dims_estado_inicial = np.array(
            [int(ind) for ind in estado_inicial],
            dtype=np.int8,
        )

        completo = System(self.tpm, dims_estado_inicial)

        candidato = completo.condicionar(dims_condicionadas)
        self.sia_logger.critic("Sisema Candidato creado.")

        subsistema = candidato.substraer(dims_alcance, dims_mecanismo)
        self.sia_logger.critic("Subsistema creado.")

        self.sia_subsistema = subsistema
        self.sia_dists_marginales = subsistema.distribucion_marginal()
        self.sia_tiempo_inicio = time.time()

    def chequear_parametros(
        self, estado_inicial: str, candidato: str, futuro: str, presente: str
    ):
        return not (
            len(self.tpm[COLS_IDX])
            == len(estado_inicial)
            == len(candidato)
            == len(futuro)
            == len(presente)
        )
