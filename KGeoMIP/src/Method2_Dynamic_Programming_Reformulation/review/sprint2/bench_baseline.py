"""Sprint 2: mediciones baseline de GeometricSIA ANTES de optimizar.

Ejecuta casos pequenos y medianos con el codigo actual, midiendo tiempo de pared,
pico de memoria (tracemalloc) y el resultado (particion, phi) que luego sirve de
referencia para la validacion contra el oraculo.

Uso: uv run python review/sprint2/bench_baseline.py [etiqueta_salida]
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

aplicacion.profiler_habilitado = False  # tiempos limpios; perfiles pyinstrument se generan aparte

from src.controllers.manager import Manager

SAMPLES = METHOD2.parents[1] / "data" / "samples"

# (red, estado_inicial, condicion, alcance, mecanismo, descripcion)
CASOS = [
    ("N5A.csv", "10000", "11111", "11111", "11111", "n=5 completo"),
    ("N10A.csv", "1000000000", "1111111111", "1111111111", "1111111110", "n=9 (mecanismo reducido)"),
    ("N10A.csv", "1000000000", "1111111111", "1111111111", "1111111111", "n=10 completo"),
    ("N15B.csv", "100000000000000", "1" * 15, "1" * 15, "111111111111000", "n=12 (mecanismo reducido)"),
    ("N15B.csv", "100000000000000", "1" * 15, "1" * 15, "1" * 15, "n=15 completo"),
]


def cargar_estrategia():
    from src.controllers.strategies.geometric import GeometricSIA

    return GeometricSIA


def correr_caso(red, estado, cond, alc, mec, medir_memoria):
    tpm = np.genfromtxt(SAMPLES / red, delimiter=",")
    Estrategia = cargar_estrategia()
    analizador = Estrategia(Manager(estado_inicial=estado))

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
        "pico_memoria_MB": (pico / 1024 / 1024) if pico is not None else None,
        "n_estados_tabla": len(analizador.tabla_transiciones),
    }


def main():
    etiqueta = sys.argv[1] if len(sys.argv) > 1 else "baseline"
    resultados = []
    for red, estado, cond, alc, mec, desc in CASOS:
        print(f"--- {red} {desc} ---", flush=True)
        try:
            r_tiempo = correr_caso(red, estado, cond, alc, mec, medir_memoria=False)
            r_mem = correr_caso(red, estado, cond, alc, mec, medir_memoria=True)
            registro = {
                "red": red,
                "descripcion": desc,
                "condicion": cond,
                "alcance": alc,
                "mecanismo": mec,
                **r_tiempo,
                "pico_memoria_MB": r_mem["pico_memoria_MB"],
                "tiempo_con_tracemalloc_s": r_mem["tiempo_s"],
            }
        except MemoryError:
            registro = {"red": red, "descripcion": desc, "error": "MemoryError"}
        except Exception as e:  # noqa: BLE001 - registrar y seguir
            registro = {"red": red, "descripcion": desc, "error": f"{type(e).__name__}: {e}"}
        print(json.dumps(registro, ensure_ascii=False, indent=2), flush=True)
        resultados.append(registro)

    salida = Path(__file__).parent / f"{etiqueta}.json"
    salida.write_text(json.dumps(resultados, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Guardado en {salida}", flush=True)


if __name__ == "__main__":
    main()
