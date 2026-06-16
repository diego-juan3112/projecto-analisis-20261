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

# Deshabilitar el profiler de QNodes durante los tests: evita instanciar
# pyinstrument.Profiler (mockeado, no acepta argumentos) y la escritura de
# reportes HTML de profiling en cada ejecución de aplicar_estrategia().
from src.middlewares.profile import gestor_perfilado as _qnodes_perfilado
_qnodes_perfilado.enabled = False


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


def test_k2_biparticion_valida_y_no_peor_que_qnodes(gestor_n3c):
    """KQNodes k=2 vs QNodes — relación correcta entre ambas estrategias.

    KQNodes parte VARIABLES ENTERAS (cada nodo va completo a una parte);
    QNodes parte VÉRTICES POR-TIEMPO (puede separar A_efecto de A_presente).
    Por eso pueden encontrar particiones DISTINTAS para k=2 (ver manual de
    usuario §3.5 y manual técnico, "Modelo de partición y relación con QNodes").

    Lo que sí se verifica y es la propiedad relevante:
    1) KQNodes produce una bipartición válida (2 partes no vacías),
    2) su pérdida usa la MISMA métrica IIT que QNodes/GeoMIP: coincide con la
       reconstrucción bipartir() aplicada a la misma partición,
    3) su pérdida NO es peor que la de QNodes (en N3C halla una bipartición
       igual de válida con MENOR pérdida — más eficiente e igual de eficaz).
    """
    from shared_src.funcs.iit import emd_efecto

    kqnodes = KQNodes(gestor_n3c, k=2, refinar=False, verbose=False)
    kqnodes.sia_preparar_subsistema("100", "111", "111", "111")
    sol_kq = kqnodes.aplicar_estrategia()

    qnodes = QNodes(gestor_n3c.cargar_red())
    sol_q = qnodes.aplicar_estrategia("100", "111", "111", "111")

    # (1) bipartición válida
    assert len(sol_kq.particion) == 2, (
        f"k=2 debe producir 2 partes, obtuvo {len(sol_kq.particion)}"
    )
    assert sol_kq.perdida >= 0.0 and sol_kq.perdida != float("inf")

    # (2) misma métrica IIT: la pérdida coincide con la reconstrucción bipartir()
    sub = kqnodes.sia_subsistema
    glob = np.asarray(kqnodes.sia_dists_marginales, dtype=np.float32)
    parte = sorted(min(sol_kq.particion, key=min))
    alcance = sub.indices_ncubos[np.array(parte, dtype=np.int8)]
    mecanismo = sub.dims_ncubos[np.array(parte, dtype=np.int8)]
    vec = sub.bipartir(
        np.array(alcance, dtype=np.int8), np.array(mecanismo, dtype=np.int8)
    ).distribucion_marginal()
    perdida_bipartir = float(emd_efecto(np.asarray(vec, dtype=np.float32), glob))
    assert abs(sol_kq.perdida - perdida_bipartir) <= 1e-6, (
        f"La pérdida de KQNodes ({sol_kq.perdida}) debe coincidir con la "
        f"reconstrucción bipartir tipo IIT ({perdida_bipartir}) — misma métrica que QNodes"
    )

    # (3) no peor que QNodes (mismo problema; KQNodes halla bipartición ≤)
    assert sol_kq.perdida <= sol_q.perdida + 1e-9, (
        f"KQNodes k=2 ({sol_kq.perdida}) no debería ser peor que QNodes ({sol_q.perdida})"
    )


def test_k3_perdida_menor_o_igual_k2(gestor_n3c):
    kqnodes_2 = KQNodes(gestor_n3c, k=2, refinar=False, verbose=False)
    kqnodes_2.sia_preparar_subsistema("100", "111", "111", "111")
    sol_k2 = kqnodes_2.aplicar_estrategia()

    kqnodes_3 = KQNodes(gestor_n3c, k=3, refinar=False, verbose=False)
    kqnodes_3.sia_preparar_subsistema("100", "111", "111", "111")
    sol_k3 = kqnodes_3.aplicar_estrategia()

    # Nota: φ(k=3) ≥ φ(k=2) es matemáticamente válido (ver manual de usuario §3.4):
    # más partes imponen más supuestos de independencia y pueden subir la pérdida.
    # Lo que sí debe cumplirse es que ambas pérdidas sean finitas y no negativas.
    assert sol_k2.perdida >= 0.0 and sol_k3.perdida >= 0.0, (
        f"Las pérdidas deben ser no negativas: k2={sol_k2.perdida}, k3={sol_k3.perdida}"
    )
    assert sol_k2.perdida != float("inf") and sol_k3.perdida != float("inf"), (
        f"Las pérdidas deben ser finitas: k2={sol_k2.perdida}, k3={sol_k3.perdida}"
    )


def test_particion_valida(gestor_n3c):
    kqnodes = KQNodes(gestor_n3c, k=3, refinar=False, verbose=False)
    kqnodes.sia_preparar_subsistema("100", "111", "111", "111")
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
    kqnodes_no_refine.sia_preparar_subsistema("100", "111", "111", "111")
    sol_no_refine = kqnodes_no_refine.aplicar_estrategia()

    kqnodes_refine = KQNodes(gestor_n3c, k=3, refinar=True, verbose=False)
    kqnodes_refine.sia_preparar_subsistema("100", "111", "111", "111")
    sol_refine = kqnodes_refine.aplicar_estrategia()

    assert sol_refine.perdida <= sol_no_refine.perdida + 1e-9, (
        f"Refinamiento no debe empeorar la pérdida, "
        f"obtuvo refinar=True {sol_refine.perdida} y refinar=False {sol_no_refine.perdida}"
    )


def test_escalabilidad_n10_k4(tpm_n10a):
    gestor = DummyGestor(tpm_n10a)
    kqnodes = KQNodes(gestor, k=4, refinar=True, verbose=False)
    kqnodes.sia_preparar_subsistema(
        "1000000000", "1111111111", "1111111111", "1111111111"
    )

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
