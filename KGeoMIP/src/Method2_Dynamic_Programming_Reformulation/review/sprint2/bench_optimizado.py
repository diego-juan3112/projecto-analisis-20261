"""Sprint 2: mediciones de la version optimizada (mismos casos del baseline + escalado).

Uso: uv run python review/sprint2/bench_optimizado.py [--n25]
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
from src.controllers.strategies.geometric import GeometricSIA

SAMPLES = METHOD2.parents[1] / "data" / "samples"

CASOS = [
    ("N5A.csv", "10000", "11111", "11111", "11111", "n=5 completo"),
    ("N10A.csv", "1000000000", "1111111111", "1111111111", "1111111110", "n=9 (mecanismo reducido)"),
    ("N10A.csv", "1000000000", "1111111111", "1111111111", "1111111111", "n=10 completo"),
    ("N15B.csv", "100000000000000", "1" * 15, "1" * 15, "111111111111000", "n=12 (mecanismo reducido)"),
    ("N15B.csv", "100000000000000", "1" * 15, "1" * 15, "1" * 15, "n=15 completo"),
    ("N20A.csv", "1" + "0" * 19, "1" * 20, "1" * 20, "1" * 20, "n=20 completo"),
]

CASO_N25 = ("N25A.csv", "1" + "0" * 24, "1" * 25, "1" * 25, "1" * 25, "n=25 completo")


def cargar_tpm_float32(ruta: Path) -> np.ndarray:
    """Carga por chunks directamente en float32 (evita el float64 de genfromtxt)."""
    chunks = [
        chunk.to_numpy(dtype=np.float32, copy=False)
        for chunk in pd.read_csv(ruta, header=None, chunksize=2_000_000, dtype=np.float32)
    ]
    return np.vstack(chunks) if len(chunks) > 1 else chunks[0]


def correr_caso(red, estado, cond, alc, mec, medir_memoria):
    t_carga0 = time.perf_counter()
    tpm = cargar_tpm_float32(SAMPLES / red)
    t_carga = time.perf_counter() - t_carga0

    analizador = GeometricSIA(Manager(estado_inicial=estado))
    if medir_memoria:
        tracemalloc.start()
    t0 = time.perf_counter()
    sol = analizador.aplicar_estrategia(cond, alc, mec, tpm)
    t1 = time.perf_counter()
    pico = None
    if medir_memoria:
        _, pico = tracemalloc.get_traced_memory()
        tracemalloc.stop()
    return {
        "particion": sol.particion,
        "perdida": float(sol.perdida),
        "tiempo_s": t1 - t0,
        "tiempo_carga_tpm_s": t_carga,
        "pico_memoria_MB": (pico / 1024 / 1024) if pico is not None else None,
    }


def main():
    casos = list(CASOS)
    etiqueta = "optimizado"
    if "--n25" in sys.argv:
        casos = [CASO_N25]
        etiqueta = "optimizado_n25"

    resultados = []
    for red, estado, cond, alc, mec, desc in casos:
        print(f"--- {red} {desc} ---", flush=True)
        try:
            medir_mem = "N25" not in red and "N20" not in red
            r = correr_caso(red, estado, cond, alc, mec, medir_memoria=False)
            registro = {"red": red, "descripcion": desc, "mecanismo": mec, **r}
            if medir_mem:
                r2 = correr_caso(red, estado, cond, alc, mec, medir_memoria=True)
                registro["pico_memoria_MB"] = r2["pico_memoria_MB"]
            else:
                # para casos grandes: una sola corrida con tracemalloc seria 2x;
                # se repite con tracemalloc solo si el tiempo base fue < 60 s
                if r["tiempo_s"] < 60:
                    r2 = correr_caso(red, estado, cond, alc, mec, medir_memoria=True)
                    registro["pico_memoria_MB"] = r2["pico_memoria_MB"]
        except MemoryError:
            registro = {"red": red, "descripcion": desc, "error": "MemoryError"}
        except Exception as e:  # noqa: BLE001
            registro = {"red": red, "descripcion": desc, "error": f"{type(e).__name__}: {e}"}
        print(json.dumps(registro, ensure_ascii=False, indent=2), flush=True)
        resultados.append(registro)

    salida = Path(__file__).parent / f"{etiqueta}.json"
    salida.write_text(json.dumps(resultados, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Guardado en {salida}", flush=True)


if __name__ == "__main__":
    main()
