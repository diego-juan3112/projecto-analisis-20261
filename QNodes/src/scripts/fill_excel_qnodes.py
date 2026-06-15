"""
Rellena columnas de resultados QNodes (k dinámico: 2, 3, 4, 5) en DatosPruebas2026_1JSME.xlsx.

Uso:
    uv run python QNodes\src\scripts\fill_excel_qnodes.py

Configura las constantes de la sección CONFIGURACIÓN antes de ejecutar.
"""

import re
import sys
import traceback
from pathlib import Path
import gc

import openpyxl

QNODES_ROOT = Path(__file__).resolve().parents[2]
QNODES_SRC   = QNODES_ROOT / "src"
sys.path.insert(0, str(QNODES_ROOT))   # necesario: QNodes usa imports src.*

from src.models.base.application import aplicacion
from src.controllers.manager import Manager
from src.strategies.q_nodes import QNodes

# ========================= CONFIGURACIÓN =========================
EXCEL_PATH   = QNODES_SRC / ".samples" / "DatosPruebas2026_1JSME.xlsx"
SHEET_NAME   = "10A-Elementos"  # Recuerda cambiar a "10A-Elementos" o "15B-Elementos" para pruebas rápidas
MAX_TIME_SEG = 3000.0   # referencia informativa; QNodes no tiene timeout explícito

# --- CONFIGURACIÓN DE PARTICIONES (K) ---
K = 3  # <--- CAMBIA AQUÍ EL VALOR: Puede ser 3, 4 o 5

# Cálculo automático de columna destino (1-based) según el grupo de K:
#   k=2 QNodes    → cols  4,  5,  6  (D, E, F)
#   k=3 QNodes    → cols 10, 11, 12  (J, K, L)
#   k=4 QNodes    → cols 16, 17, 18  (P, Q, R)
#   k=5 QNodes    → cols 22, 23, 24  (V, W, X)
COL_INICIO = 4 + (K - 2) * 6

SAMPLE_PATH     = QNODES_SRC / ".samples"
HEADER_ROW      = 5      # fila de encabezados de columnas en el Excel
SKIP_SI_RELLENO = False  # False = sobreescribir todo; True = saltar filas ya rellenas
# =================================================================


def leer_metadatos_hoja(ws) -> tuple[str, str]:
    """Lee estado_inicial y sistema de las filas de cabecera."""
    estado_inicial = str(ws.cell(1, 2).value).strip()
    sistema        = str(ws.cell(2, 2).value).strip()
    return estado_inicial, sistema


def leer_casos_prueba(ws) -> list[dict]:
    """Devuelve lista de casos {row_idx, alcance_letras, mecanismo_letras}."""
    casos = []
    for row_idx in range(HEADER_ROW + 1, ws.max_row + 1):
        alc = ws.cell(row_idx, 2).value
        mec = ws.cell(row_idx, 3).value
        if alc is None or mec is None:
            continue
        alc_s = str(alc).strip()
        mec_s = str(mec).strip()
        if not alc_s or not mec_s:
            continue
        casos.append({"row_idx": row_idx, "alcance_letras": alc_s, "mecanismo_letras": mec_s})
    return casos


def letras_a_binario(letras: str, sistema: str) -> str:
    """Convierte string de letras a máscara binaria relativa al sistema.

    Ejemplo:
        letras='ACEGI', sistema='ABCDEFGHIJ' → '1010101010'
    """
    return "".join("1" if c in letras else "0" for c in sistema)


def formatear_tiempo(tiempo_s: float) -> str:
    """Formatea el tiempo igual que QNodes."""
    return (
        f"Horas: {tiempo_s / 3600:.2f} = "
        f"Minutos: {tiempo_s / 60:.1f} = "
        f"Segundos: {tiempo_s:.4f}"
    )


def escribir_resultado(
    excel_path: Path,
    sheet_name: str,
    row_idx: int,
    col_inicio: int,
    particion: str,
    perdida: float,
    tiempo: str,
) -> None:
    """Escribe Partición, Pérdida y Tiempo en las celdas correspondientes."""
    wb = openpyxl.load_workbook(excel_path)
    ws = wb[sheet_name]
    ws.cell(row_idx, col_inicio    ).value = particion
    ws.cell(row_idx, col_inicio + 1).value = str(round(float(perdida), 4))
    ws.cell(row_idx, col_inicio + 2).value = tiempo
    wb.save(excel_path)
    wb.close()


def configurar_pagina(sheet_name: str) -> None:
    """Extrae la letra de página del nombre de hoja y la aplica al singleton."""
    m = re.match(r"\d+([A-Z])", sheet_name)
    if not m:
        raise ValueError(f"No se pudo extraer la página del nombre de hoja: {sheet_name!r}")
    aplicacion.set_pagina_red_muestra(m.group(1))


def main() -> None:
    print(f"Excel  : {EXCEL_PATH}")
    print(f"Hoja   : {SHEET_NAME}")
    print(f"k      : {K}  ({K}-partición QNodes)")
    print(f"Cols   : {COL_INICIO}–{COL_INICIO + 2} (Partición, Pérdida, Tiempo)")
    print()

    # 1 — Leer metadatos y casos del Excel
    wb_r = openpyxl.load_workbook(EXCEL_PATH, data_only=True)
    ws_r = wb_r[SHEET_NAME]
    estado_inicial, sistema = leer_metadatos_hoja(ws_r)
    condiciones = "1" * len(estado_inicial)
    casos       = leer_casos_prueba(ws_r)
    filas_rellenas = {
        row_idx
        for row_idx in range(HEADER_ROW + 1, ws_r.max_row + 1)
        if ws_r.cell(row_idx, COL_INICIO).value not in (None, "")
    } if SKIP_SI_RELLENO else set()
    wb_r.close()

    print(f"Estado inicial : {estado_inicial}  (N={len(estado_inicial)})")
    print(f"Sistema        : {sistema}")
    print(f"Condiciones    : {condiciones}  (todo 1s)")
    print(f"Casos de prueba: {len(casos)}")
    print()

    # 2 — Configurar página (10A → 'A', 15B → 'B', …)
    configurar_pagina(SHEET_NAME)
    tpm_file = f"N{len(estado_inicial)}{aplicacion.pagina_red_muestra}.csv"
    print(f"Cargando TPM: {tpm_file} …")

    # 3 — Cargar TPM una sola vez
    gestor = Manager(estado_inicial, ruta_base=SAMPLE_PATH)
    tpm    = gestor.cargar_red().astype('float32')
    print(f"TPM cargada. Shape: {tpm.shape}")
    print("Iniciando ejecución de casos…\n")
    print("-" * 70)

    # 4 — Iterar sobre cada caso de prueba
    for i, caso in enumerate(casos):
        alcance_bin   = letras_a_binario(caso["alcance_letras"],   sistema)
        mecanismo_bin = letras_a_binario(caso["mecanismo_letras"], sistema)

        print(
            f"[{i + 1}/{len(casos)}] fila={caso['row_idx']}  "
            f"Alcance={caso['alcance_letras']}  "
            f"Mecanismo={caso['mecanismo_letras']}"
        )

        # Filtro de seguridad para la hoja de 25 elementos (Evita MemoryError inmediato)
        if len(caso["alcance_letras"]) == 25 and len(caso["mecanismo_letras"]) == 25:
            print(f"  → Saltando fila 6 (25x25) temporalmente por alta demanda de RAM.\n")
            continue

        if caso["row_idx"] in filas_rellenas:
            print("  → ya relleno, omitiendo\n")
            continue

        try:
            # 1. Crear la instancia normal (sin el parámetro k aquí)
            q = QNodes(tpm)

            # 2. Pasar el parámetro k=K directamente al método de la estrategia
            resultado = q.aplicar_estrategia(
                estado_inicial, condiciones, alcance_bin, mecanismo_bin, k=K
            )

            particion_str = str(resultado.particion)
            tiempo_str    = formatear_tiempo(resultado.tiempo_ejecucion)
            perdida       = resultado.perdida

            print(f"  Partición : {particion_str}")
            print(f"  Pérdida   : {perdida:.4f}")
            print(f"  {tiempo_str}")

            escribir_resultado(
                EXCEL_PATH, SHEET_NAME, caso["row_idx"],
                COL_INICIO, particion_str, perdida, tiempo_str,
            )
            print(f"  ✓ Escrito en Excel\n")
            del q
            gc.collect()

        except Exception as e:
            sep = "=" * 70
            print(f"\n{sep}")
            print(f"ERROR en fila {caso['row_idx']} (caso {i + 1}/{len(casos)})")
            print(f"  Alcance  : {caso['alcance_letras']} → {alcance_bin}")
            print(f"  Mecanismo: {caso['mecanismo_letras']} → {mecanismo_bin}")
            print(f"  Excepción: {type(e).__name__}: {e}")
            traceback.print_exc()
            print(sep)
            print("EJECUCIÓN DETENIDA — revisa el error antes de continuar.")
            sys.exit(1)

    print("=" * 70)
    print(f"Completado. {len(casos)} casos escritos en '{SHEET_NAME}', cols k={K} QNodes.")


if __name__ == "__main__":
    main()