"""Sprint 3: mediciones de la nueva KGeometricSIA (curvas vs n y vs k).

Uso: uv run python review/sprint3/bench_kgeo_nuevo.py
"""

import json
import sys
import time
import tracemalloc
from pathlib import Path

METHOD2 = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(METHOD2))

import numpy as np
import pandas as pd

from src.models.base.application import aplicacion

aplicacion.profiler_habilitado = False

from src.controllers.manager import Manager
from src.controllers.strategies.k_geometric import KGeometricSIA

SAMPLES = METHOD2.parents[1] / "data" / "samples"

CASOS = [
    ("N10A.csv", "1000000000", "1" * 10, "1" * 10, "1" * 10, 2),
    ("N10A.csv", "1000000000", "1" * 10, "1" * 10, "1" * 10, 3),
    ("N10A.csv", "1000000000", "1" * 10, "1" * 10, "1" * 10, 4),
    ("N10A.csv", "1000000000", "1" * 10, "1" * 10, "1" * 10, 5),
    ("N10A.csv", "1000000000", "1" * 10, "1" * 10, "1111111110", 3),
    ("N15B.csv", "1" + "0" * 14, "1" * 15, "1" * 15, "1" * 15, 2),
    ("N15B.csv", "1" + "0" * 14, "1" * 15, "1" * 15, "1" * 15, 3),
    ("N15B.csv", "1" + "0" * 14, "1" * 15, "1" * 15, "1" * 15, 4),
    ("N20A.csv", "1" + "0" * 19, "1" * 20, "1" * 20, "1" * 20, 3),
]


def cargar(ruta: Path) -> np.ndarray:
    return pd.read_csv(ruta, header=None, dtype=np.float32).to_numpy()


def main():
    resultados = []
    for red, estado, cond, alc, mec, k in CASOS:
        tpm = cargar(SAMPLES / red)
        kgeo = KGeometricSIA(Manager(estado_inicial=estado))
        medir_mem = red != "N20A.csv"
        if medir_mem:
            tracemalloc.start()
        t0 = time.perf_counter()
        sol = kgeo.aplicar_estrategia(cond, alc, mec, tpm, k_objetivo=k)
        dt = time.perf_counter() - t0
        pico = None
        if medir_mem:
            _, pico = tracemalloc.get_traced_memory()
            tracemalloc.stop()
        registro = {
            "red": red, "mecanismo": mec, "k": k,
            "phi": float(sol.perdida),
            "tiempo_s": round(dt, 4),
            "pico_MB": round(pico / 2**20, 3) if pico else None,
            "poda_fase2": kgeo.estadisticas_poda,
            "particion": sol.particion.replace("\n", " // "),
        }
        print(json.dumps(registro, ensure_ascii=False), flush=True)
        resultados.append(registro)

    salida = Path(__file__).parent / "kgeo_nuevo.json"
    salida.write_text(json.dumps(resultados, ensure_ascii=False, indent=2),
                      encoding="utf-8")
    print(f"Guardado en {salida}", flush=True)


if __name__ == "__main__":
    main()
