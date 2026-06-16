"""Sprint 3: baseline del KGeometricSIA original ANTES de reescribirlo.

Captura tiempo, memoria, phi y particion para k=2 y k=3, y contrasta el k=2
contra GeometricSIA (se espera discrepancia: espacios de busqueda distintos).

Uso: uv run python review/sprint3/bench_kgeo_viejo.py
"""

import json
import sys
import time
import tracemalloc
from pathlib import Path

METHOD2 = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(METHOD2))

import numpy as np

from src.models.base.application import aplicacion

aplicacion.profiler_habilitado = False

from src.controllers.manager import Manager
from src.controllers.strategies.geometric import GeometricSIA
from src.controllers.strategies.k_geometric import KGeometricSIA

SAMPLES = METHOD2.parents[1] / "data" / "samples"

CASOS = [
    ("N5A.csv", "10000", "11111", "11111", "11111", 2),
    ("N5A.csv", "10000", "11111", "11111", "11111", 3),
    ("N10A.csv", "1000000000", "1111111111", "1111111111", "1111111111", 2),
    ("N10A.csv", "1000000000", "1111111111", "1111111111", "1111111111", 3),
    # mascara no trivial: el bug N1 produce resultado silenciosamente erroneo
    ("N10A.csv", "1000000000", "1111111111", "1111111111", "1111111110", 3),
]


def main():
    resultados = []
    for red, estado, cond, alc, mec, k in CASOS:
        tpm = np.genfromtxt(SAMPLES / red, delimiter=",")
        kgeo = KGeometricSIA(Manager(estado_inicial=estado))
        tracemalloc.start()
        t0 = time.perf_counter()
        try:
            sol = kgeo.aplicar_estrategia(cond, alc, mec, tpm, k_objetivo=k)
            dt = time.perf_counter() - t0
            _, pico = tracemalloc.get_traced_memory()
            registro = {
                "red": red, "mecanismo": mec, "k": k,
                "particion": str(sol.particion),
                "phi": float(sol.perdida),
                "tiempo_s": round(dt, 4),
                "pico_MB": round(pico / 2**20, 3),
            }
        except Exception as e:  # noqa: BLE001
            registro = {"red": red, "mecanismo": mec, "k": k,
                        "error": f"{type(e).__name__}: {e}"}
        finally:
            tracemalloc.stop()

        if k == 2 and "phi" in registro:
            geo = GeometricSIA(Manager(estado_inicial=estado))
            sol_g = geo.aplicar_estrategia(cond, alc, mec, tpm)
            registro["phi_geometric"] = float(sol_g.perdida)
            registro["particion_geometric"] = sol_g.particion
            registro["k2_coincide_phi"] = bool(
                abs(registro["phi"] - float(sol_g.perdida)) <= 1e-9
            )

        print(json.dumps(registro, ensure_ascii=False), flush=True)
        resultados.append(registro)

    salida = Path(__file__).parent / "kgeo_viejo.json"
    salida.write_text(json.dumps(resultados, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Guardado en {salida}", flush=True)


if __name__ == "__main__":
    main()
