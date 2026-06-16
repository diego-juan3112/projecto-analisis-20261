"""Sprint 2: diagnostico cuantitativo del ciclo de vida del TPM (solo medicion).

Mide, para redes existentes, el costo real de cada etapa del ciclo:
(a) formato de almacenamiento: CSV texto vs .npy binario (tamano, carga),
(b) parsing: np.genfromtxt vs pandas.read_csv float32,
(c) paso por multiprocessing: costo de serializar el array (pickle),
(d) representacion interna: tamanos por dtype.

No modifica el pipeline; los .npy de prueba se crean en un directorio temporal.

Uso: uv run python review/sprint2/diag_tpm.py
"""

import json
import pickle
import sys
import tempfile
import time
from pathlib import Path

METHOD2 = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(METHOD2))

import numpy as np
import pandas as pd

SAMPLES = METHOD2.parents[1] / "data" / "samples"
REDES = ["N15B.csv", "N20A.csv"]


def medir(funcion):
    t0 = time.perf_counter()
    resultado = funcion()
    return resultado, time.perf_counter() - t0


def main():
    informe = {}
    tmp = Path(tempfile.mkdtemp(prefix="diag_tpm_"))

    for red in REDES:
        ruta = SAMPLES / red
        n = int(red[1:-5])
        registro = {"csv_bytes": ruta.stat().st_size, "n": n}

        # (b) parsing CSV
        tpm64, t_gen = medir(lambda r=ruta: np.genfromtxt(r, delimiter=","))
        registro["genfromtxt_s"] = round(t_gen, 3)
        registro["array_float64_MB"] = round(tpm64.nbytes / 2**20, 1)

        tpm32, t_pd = medir(
            lambda r=ruta: pd.read_csv(r, header=None, dtype=np.float32).to_numpy()
        )
        registro["read_csv_float32_s"] = round(t_pd, 3)
        registro["array_float32_MB"] = round(tpm32.nbytes / 2**20, 1)

        # (a) binario .npy
        npy = tmp / (red + ".npy")
        _, t_save = medir(lambda: np.save(npy, tpm32))
        registro["npy_save_s"] = round(t_save, 3)
        registro["npy_bytes"] = npy.stat().st_size

        _, t_load = medir(lambda: np.load(npy))
        registro["npy_load_s"] = round(t_load, 4)
        mm, t_mmap = medir(lambda: np.load(npy, mmap_mode="r"))
        registro["npy_mmap_open_s"] = round(t_mmap, 5)
        # primer acceso completo via memmap (paginado real desde disco)
        _, t_touch = medir(lambda: float(np.asarray(mm).sum()))
        registro["npy_mmap_lectura_total_s"] = round(t_touch, 3)
        del mm

        # int8 si la red es determinista (todos los valores en {0,1})
        es_binaria = bool(((tpm32 == 0) | (tpm32 == 1)).all())
        registro["es_binaria"] = es_binaria
        if es_binaria:
            registro["array_int8_MB"] = round(tpm32.astype(np.int8).nbytes / 2**20, 1)
            registro["packbits_MB"] = round(
                np.packbits(tpm32.astype(np.uint8), axis=0).nbytes / 2**20, 2
            )

        # (c) costo de pickling (lo que paga multiprocessing por subproceso)
        _, t_pkl64 = medir(lambda: len(pickle.dumps(tpm64, protocol=5)))
        _, t_pkl32 = medir(lambda: len(pickle.dumps(tpm32, protocol=5)))
        registro["pickle_float64_s"] = round(t_pkl64, 3)
        registro["pickle_float32_s"] = round(t_pkl32, 3)

        informe[red] = registro
        print(json.dumps({red: registro}, ensure_ascii=False, indent=2), flush=True)
        del tpm64, tpm32

    # Proyeccion analitica N25 (medirlo con genfromtxt es inviable en esta RAM)
    n, filas = 25, 1 << 25
    informe["N25A_proyeccion"] = {
        "csv_bytes": (SAMPLES / "N25A.csv").stat().st_size,
        "array_float64_MB": round(filas * n * 8 / 2**20, 0),
        "array_float32_MB": round(filas * n * 4 / 2**20, 0),
        "array_int8_MB": round(filas * n / 2**20, 0),
        "packbits_MB": round(filas * n / 8 / 2**20, 0),
        "nota": "float64 via genfromtxt + copia pickle a subproceso = 2 x 6.7 GB; inviable en 16 GB",
    }

    salida = Path(__file__).parent / "diag_tpm.json"
    salida.write_text(json.dumps(informe, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Guardado en {salida}", flush=True)

    for archivo in tmp.glob("*"):
        archivo.unlink()
    tmp.rmdir()


if __name__ == "__main__":
    main()
