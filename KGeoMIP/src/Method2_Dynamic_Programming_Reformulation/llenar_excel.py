"""Llenado del Excel de entrega: columnas Geometric para k=2..5 (Sprint 4).

Por cada hoja (10A, 15B, 20A, 25A) y cada k, ejecuta KGeometricSIA sobre los
35 casos (Alcance/Mecanismo en letras) y escribe (Partición, Pérdida, Tiempo)
en el bloque correspondiente, con la notación ⎛ ⎞ de la hoja. Localización de
hojas/bloques por contenido (src/funcs/excel_io.py, corrige N11).

Manejo del TPM (P1+P2 mínimos del diagnóstico, habilitados aquí porque la hoja
25A vuelve bloqueante el patrón anterior): el CSV se convierte UNA vez a
.npy float32 (caché junto al CSV) y cada subproceso recibe la RUTA y carga ahí
el .npy completo con np.load(ruta); nunca se serializa el array por
multiprocessing (el padre no lo materializa). El memmap se evaluó y se descartó
porque System consume la TPM por columnas y un memmap fila-mayor degenera en
lecturas dispersas del archivo entero por columna.

Reanudable: las celdas ya ocupadas se saltan; el libro se guarda tras cada
caso. Se crea un respaldo .bak del libro la primera vez.

Uso (desde Method2):
  uv run python llenar_excel.py --hoja 10A --k 2,3,4,5 [--cantidad 35]
                                [--timeout 3600] [--desde 1]
"""

import argparse
import multiprocessing
import os
import shutil
import sys
import time
from pathlib import Path

METHOD2 = Path(__file__).resolve().parent
sys.path.insert(0, str(METHOD2))

import numpy as np
import openpyxl

GEOMIP_ROOT = METHOD2.parents[1]
REPO_ROOT = GEOMIP_ROOT.parent
LIBRO_DEFECTO = REPO_ROOT / "DatosPruebas2026_1.xlsx"
SAMPLES = GEOMIP_ROOT / "data" / "samples"


def ruta_npy(red: str, n_bits: int) -> Path:
    """Devuelve la ruta del caché .npy float32, creándolo desde el CSV si falta."""
    import pandas as pd

    csv = SAMPLES / f"N{n_bits}{red[len(str(n_bits)):]}.csv"
    npy = csv.with_suffix(".npy")
    if not npy.exists():
        if not csv.exists():
            raise FileNotFoundError(f"No existe la muestra {csv}")
        print(f"[conversion unica] {csv.name} -> {npy.name} (float32)...", flush=True)
        bloques = [
            chunk.to_numpy(dtype=np.float32, copy=False)
            for chunk in pd.read_csv(csv, header=None, chunksize=2_000_000,
                                     dtype=np.float32)
        ]
        np.save(npy, np.vstack(bloques) if len(bloques) > 1 else bloques[0])
    return npy


def _trabajador(ruta_tpm, estado, condiciones, alcance, mecanismo, k, cola):
    """Subproceso por caso: carga el TPM por memmap y ejecuta la estrategia."""
    try:
        import sys as _sys
        _sys.path.insert(0, str(Path(__file__).resolve().parent))
        from src.models.base.application import aplicacion

        aplicacion.profiler_habilitado = False
        from src.controllers.manager import Manager
        from src.controllers.strategies.k_geometric import KGeometricSIA

        # Carga COMPLETA secuencial (~3.2 GB / ~10 s en N25): System consume la
        # TPM columna por columna y sobre un memmap fila-mayor eso degenera en
        # lecturas dispersas del archivo entero por columna (timeout observado
        # en la hoja 25A). El memmap queda como alternativa solo si el archivo
        # no cupiera en la RAM del subproceso.
        tpm = np.load(ruta_tpm)
        analizador = KGeometricSIA(Manager(estado_inicial=estado))
        t0 = time.perf_counter()
        sol = analizador.aplicar_estrategia(
            condiciones, alcance, mecanismo, tpm, k_objetivo=k
        )
        duracion = time.perf_counter() - t0
        cola.put({
            "particion": analizador.particion_k_fmt,  # notación ⎛ ⎞ para todo k
            "perdida": float(sol.perdida),
            "tiempo": duracion,
        })
    except Exception as e:  # noqa: BLE001 - el padre registra el fallo
        cola.put({"error": f"{type(e).__name__}: {e}"})


def _guardar_atomico(libro, destino: Path) -> None:
    """Guarda a un temporal y reemplaza: un lector concurrente o un corte a
    mitad de escritura nunca ven un .xlsx truncado."""
    temporal = destino.with_suffix(destino.suffix + ".tmp")
    libro.save(temporal)
    os.replace(temporal, destino)


def llenar_hoja(libro_path: Path, red: str, ks: list[int], desde: int,
                cantidad: int, timeout: int) -> None:
    from src.funcs.excel_io import (
        celda_ocupada, escribir_resultado, leer_casos, leer_contexto,
        letras_a_binario, localizar_hoja,
    )

    # Un solo escritor a la vez: dos procesos concurrentes se pisarian las
    # celdas (cada uno guarda su copia completa del libro en memoria).
    candado = libro_path.with_suffix(libro_path.suffix + ".lock")
    try:
        descriptor = os.open(candado, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
        os.close(descriptor)
    except FileExistsError:
        raise SystemExit(
            f"Otro llenado esta en curso ({candado}). Si es un residuo de un "
            f"proceso muerto, borre el archivo .lock y reintente."
        )

    respaldo = libro_path.with_suffix(libro_path.suffix + ".bak")
    if not respaldo.exists():
        shutil.copy2(libro_path, respaldo)
        print(f"Respaldo creado: {respaldo.name}", flush=True)

    libro = openpyxl.load_workbook(libro_path)
    hoja = localizar_hoja(libro, red)
    ctx = leer_contexto(hoja)
    print(f"Hoja '{hoja.title}': estado={ctx.estado_inicial} "
          f"condiciones={ctx.condiciones} bloques k={sorted(ctx.columnas_geometric)}",
          flush=True)

    tpm_path = ruta_npy(red, len(ctx.estado_inicial))
    casos = list(leer_casos(hoja, ctx))[desde - 1 : desde - 1 + cantidad]

    for k in ks:
        if k not in ctx.columnas_geometric:
            print(f"[k={k}] sin bloque Geometric en la hoja; se omite", flush=True)
            continue
        col = ctx.columnas_geometric[k]
        for numero, (fila, alc_letras, mec_letras) in enumerate(casos, start=desde):
            if celda_ocupada(hoja, fila, col):
                continue
            alcance = letras_a_binario(alc_letras, ctx.sistema)
            mecanismo = letras_a_binario(mec_letras, ctx.sistema)
            print(f"[{red} k={k} caso {numero}] alc={alc_letras} mec={mec_letras}",
                  flush=True)

            cola = multiprocessing.Queue()
            proceso = multiprocessing.Process(
                target=_trabajador,
                args=(str(tpm_path), ctx.estado_inicial, ctx.condiciones,
                      alcance, mecanismo, k, cola),
            )
            proceso.start()
            proceso.join(timeout=timeout)
            if proceso.is_alive():
                proceso.terminate()
                proceso.join()
                resultado = {"error": f"timeout {timeout}s"}
            else:
                resultado = cola.get() if not cola.empty() else {"error": "sin resultado"}

            if "error" in resultado:
                print(f"  -> ERROR: {resultado['error']}", flush=True)
                continue
            escribir_resultado(hoja, fila, col, resultado["particion"],
                               resultado["perdida"], resultado["tiempo"])
            _guardar_atomico(libro, libro_path)
            print(f"  -> phi={resultado['perdida']:.4f} "
                  f"t={resultado['tiempo']:.2f}s", flush=True)

    try:
        _guardar_atomico(libro, libro_path)
        print(f"Hoja {red} completada para k={ks}.", flush=True)
    finally:
        candado.unlink(missing_ok=True)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--hoja", required=True, help="ej. 10A, 15B, 20A, 25A")
    parser.add_argument("--k", default="2,3,4,5")
    parser.add_argument("--desde", type=int, default=1)
    # default holgado: leer_casos se detiene solo en la primera fila vacia
    parser.add_argument("--cantidad", type=int, default=500)
    parser.add_argument("--timeout", type=int, default=3600)
    parser.add_argument("--libro", default=str(LIBRO_DEFECTO))
    args = parser.parse_args()
    ks = [int(x) for x in args.k.split(",")]
    llenar_hoja(Path(args.libro), args.hoja, ks, args.desde, args.cantidad,
                args.timeout)


if __name__ == "__main__":
    main()
