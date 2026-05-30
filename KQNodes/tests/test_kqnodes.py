import sys
import time
import types
from pathlib import Path

import numpy as np
import pytest

# Mock dependencies that no-environment tests may not have installed.
pyttsx3 = types.ModuleType("pyttsx3")
pyttsx3.engine = types.ModuleType("pyttsx3.engine")
pyttsx3.voice = types.ModuleType("pyttsx3.voice")
pyttsx3.engine.Engine = type("Engine", (), {})
pyttsx3.voice.Voice = type("Voice", (), {})
pyttsx3.init = lambda *args, **kwargs: None
sys.modules["pyttsx3"] = pyttsx3
sys.modules["pyttsx3.engine"] = pyttsx3.engine
sys.modules["pyttsx3.voice"] = pyttsx3.voice

pyinstrument = types.ModuleType("pyinstrument")
pyinstrument.Profiler = type("Profiler", (), {})
sys.modules["pyinstrument"] = pyinstrument

pyinstrument_renderers = types.ModuleType("pyinstrument.renderers")
pyinstrument_renderers.HTMLRenderer = type("HTMLRenderer", (), {})
sys.modules["pyinstrument.renderers"] = pyinstrument_renderers

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "QNodes"))
sys.path.insert(0, str(REPO_ROOT))

from KQNodes.src.strategies.kqnodes import KQNodes
from src.strategies.q_nodes import QNodes


@pytest.fixture
def tpm_n3c() -> np.ndarray:
    csv_path = REPO_ROOT / "QNodes" / "src" / ".samples" / "N3C.csv"
    assert csv_path.exists(), f"No se encontró el CSV de prueba en {csv_path}"
    return np.genfromtxt(csv_path, delimiter=",")


@pytest.fixture
def tpm_n10a() -> np.ndarray:
    csv_path = REPO_ROOT / "QNodes" / "src" / ".samples" / "N10A.csv"
    assert csv_path.exists(), f"No se encontró el CSV de prueba en {csv_path}"
    return np.genfromtxt(csv_path, delimiter=",")


class DummyGestor:
    def __init__(self, tpm: np.ndarray):
        self._tpm = tpm

    def cargar_red(self) -> np.ndarray:
        return self._tpm


@pytest.fixture
def gestor_n3c(tpm_n3c) -> DummyGestor:
    return DummyGestor(tpm_n3c)


def test_k2_equivalente_qnodes(gestor_n3c):
    kqnodes = KQNodes(gestor_n3c, k=2, refinar=False, verbose=False)
    sol_kq = kqnodes.aplicar_estrategia()

    qnodes = QNodes(gestor_n3c.cargar_red())
    sol_q = qnodes.aplicar_estrategia("100", "111", "111", "111")

    assert abs(sol_kq.perdida - sol_q.perdida) <= 1e-6, (
        f"KQNodes k=2 debería igualar la pérdida de QNodes, "
        f"obtuvo {sol_kq.perdida} vs {sol_q.perdida}"
    )


def test_k3_perdida_menor_o_igual_k2(gestor_n3c):
    kqnodes_2 = KQNodes(gestor_n3c, k=2, refinar=False, verbose=False)
    sol_k2 = kqnodes_2.aplicar_estrategia()

    kqnodes_3 = KQNodes(gestor_n3c, k=3, refinar=False, verbose=False)
    sol_k3 = kqnodes_3.aplicar_estrategia()

    assert sol_k3.perdida <= sol_k2.perdida + 1e-9, (
        f"KQNodes k=3 debería tener pérdida menor o igual que k=2, "
        f"obtuvo {sol_k3.perdida} vs {sol_k2.perdida}"
    )


def test_particion_valida(gestor_n3c):
    kqnodes = KQNodes(gestor_n3c, k=3, refinar=False, verbose=False)
    sol = kqnodes.aplicar_estrategia()

    partes = sol.particion
    assert partes, "La partición no debe estar vacía"

    union_partes = set().union(*[set(p) for p in partes])
    esperado = set(range(int(gestor_n3c.cargar_red().shape[1])))
    assert union_partes == esperado, (
        f"La unión de las partes debe cubrir todas las variables: espera {esperado}, "
        f"obtuvo {union_partes}"
    )

    for idx, parte in enumerate(partes):
        assert parte, f"La parte {idx} no debe estar vacía"

    for i in range(len(partes)):
        for j in range(i + 1, len(partes)):
            assert set(partes[i]).isdisjoint(set(partes[j])), (
                f"Las partes {i} y {j} deben ser disjuntas, "
                f"pero tienen intersección {set(partes[i]).intersection(set(partes[j]))}"
            )


def test_refinamiento_no_empeora(gestor_n3c):
    kqnodes_no_refine = KQNodes(gestor_n3c, k=3, refinar=False, verbose=False)
    sol_no_refine = kqnodes_no_refine.aplicar_estrategia()

    kqnodes_refine = KQNodes(gestor_n3c, k=3, refinar=True, verbose=False)
    sol_refine = kqnodes_refine.aplicar_estrategia()

    assert sol_refine.perdida <= sol_no_refine.perdida + 1e-9, (
        f"Refinamiento no debe empeorar la pérdida, "
        f"obtuvo refinar=True {sol_refine.perdida} y refinar=False {sol_no_refine.perdida}"
    )


def test_escalabilidad_n10_k4(tpm_n10a):
    gestor = DummyGestor(tpm_n10a)
    kqnodes = KQNodes(gestor, k=4, refinar=True, verbose=False)

    inicio = time.perf_counter()
    sol = kqnodes.aplicar_estrategia()
    duracion = time.perf_counter() - inicio

    assert duracion < 60.0, (
        f"KQNodes k=4 con N10A debe terminar en menos de 60s, "
        f"terminó en {duracion:.2f}s"
    )
    assert sol.perdida >= 0.0, "La pérdida debe ser un número no negativo"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
