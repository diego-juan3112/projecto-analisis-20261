from itertools import product
from typing import Callable

import numpy as np
from numpy.typing import NDArray

from shared_src.constants.base import (
    ABC_START,
    # EMPTY_STR may be absent in minimal copy; use WHITESPACE as fallback where needed
    INT_ZERO,
    STR_ZERO as STR_ONE,
    # VOID_STR and EMPTY_STR are not present in minimal constants; define locally if needed
)
from shared_src.models.base.application import aplicacion
from shared_src.models.enums.distance import MetricDistance
from shared_src.models.enums.notation import Notation
from shared_src.models.enums.temporal_emd import TimeEMD


def get_labels(n: int) -> tuple[str, ...]:
    def get_excel_column(n: int) -> str:
        if n <= 0:
            return ""
        return get_excel_column((n - 1) // 26) + chr((n - 1) % 26 + ord(ABC_START))

    return tuple([get_excel_column(i) for i in range(1, n + 1)])


ABECEDARY = get_labels(40)
LOWER_ABECEDARY = [letter.lower() for letter in ABECEDARY]


def hamming_distance(a: int, b: int) -> int:
    return count_bits(a ^ b)


def count_bits(n: int) -> int:
    return bin(n).count("1")


def reindexar(n: int) -> np.ndarray:
    notaciones = {
        Notation.BIG_ENDIAN.value: big_endian(n),
        Notation.LIL_ENDIAN.value: lil_endian(n),
    }
    notacion = (
        aplicacion.notacion_indexado.value
        if isinstance(aplicacion.notacion_indexado, Notation)
        else str(aplicacion.notacion_indexado)
    )
    if notacion not in notaciones:
        opciones = ", ".join(sorted(notaciones.keys()))
        raise ValueError(
            f"Notación de indexado no soportada: '{notacion}'. Opciones disponibles: {opciones}"
        )
    return notaciones[notacion]


def seleccionar_estado(subestado: np.ndarray) -> np.ndarray:
    notaciones = {
        Notation.BIG_ENDIAN.value: subestado,
        Notation.LIL_ENDIAN.value: subestado[::-1],
    }
    notacion = (
        aplicacion.notacion_indexado.value
        if isinstance(aplicacion.notacion_indexado, Notation)
        else str(aplicacion.notacion_indexado)
    )
    if notacion not in notaciones:
        opciones = ", ".join(sorted(notaciones.keys()))
        raise ValueError(
            f"Notación de estado no soportada: '{notacion}'. Opciones disponibles: {opciones}"
        )
    return notaciones[notacion]


def big_endian(n: int) -> np.ndarray:
    return np.array(range(n), dtype=np.uint32)


def lil_endian(n: int) -> np.ndarray:
    if n <= 0:
        return np.array([0], dtype=np.uint32)

    size = 1 << n
    result = np.zeros(size, dtype=np.uint32)
    block_bits = max(12, min(16, 28 - int(np.log2(n))))
    block_size = 1 << block_bits
    shifts = np.array([n - i - 1 for i in range(n)], dtype=np.uint32)
    block_result = np.zeros(block_size, dtype=np.uint32)
    bit_group_size = 6 if n > 24 else 4

    for start in range(0, size, block_size):
        end = min(start + block_size, size)
        current_size = end - start
        block_result[:current_size] = 0
        block_indices = np.arange(start, end, dtype=np.uint32)
        for base_bit in range(0, n, bit_group_size):
            bits_remaining = min(bit_group_size, n - base_bit)
            if bits_remaining <= 0:
                break
            group_mask = np.uint32((1 << bits_remaining) - 1)
            group_values = (block_indices >> base_bit) & group_mask
            for j in range(bits_remaining):
                shift = shifts[base_bit + j]
                bit_value = (group_values >> j) & np.uint32(1)
                block_result[:current_size] |= bit_value << shift
        result[start:end] = block_result[:current_size]

    return result


def emd_efecto(u: NDArray[np.float32], v: NDArray[np.float32]) -> float:
    return np.sum(np.abs(u - v))
