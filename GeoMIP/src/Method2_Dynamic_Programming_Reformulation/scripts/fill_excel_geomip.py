"""
Rellena columnas de resultados GeoMIP (k=2 Geometric) en DatosPruebas2026_1.xlsx.

Uso:
    uv run python uv run python scripts\fill_excel_geomip.py

Configura las constantes de la sección CONFIGURACIÓN antes de ejecutar.
"""

import re
import sys
import traceback
from pathlib import Path

import openpyxl

# ================= CONFIGURACIÓN DE RUTAS Y SOLUCIÓN DE CONFLICTOS =================

SCRIPT_DIR = Path(__file__).resolve().parent
GEOMIP_METHOD = SCRIPT_DIR.parent
TRUE_PROJECT_ROOT = GEOMIP_METHOD.parent.parent.parent

# 1. Inyectar site-packages de GeoMIP
_geomip_sp = GEOMIP_METHOD / ".venv" / "Lib" / "site-packages"
if _geomip_sp.exists():
    sys.path.insert(0, str(_geomip_sp))

# --- PASO A: Importar GeoMIP ---
if str(TRUE_PROJECT_ROOT) in sys.path:
    sys.path.remove(str(TRUE_PROJECT_ROOT))
if str(GEOMIP_METHOD) not in sys.path:
    sys.path.insert(0, str(GEOMIP_METHOD))

from src.models.base.application import aplicacion
from src.controllers.manager import Manager
from src.controllers.strategies.geometric import GeometricSIA

# --- PASO B: Importar QNodes borrando el "src" de memoria ---
if str(GEOMIP_METHOD) in sys.path:
    sys.path.remove(str(GEOMIP_METHOD))
if str(TRUE_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(TRUE_PROJECT_ROOT))

# Forzar a Python a olvidar el 'src' de GeoMIP para que busque el de QNodes
for mod in list(sys.modules.keys()):
    if mod == "src" or mod.startswith("src."):
        del sys.modules[mod]

from QNodes.src.scripts.fill_excel_qnodes import QNODES_SRC

# --- PASO C: Restaurar GeoMIP borrando el "src" de QNodes ---
for mod in list(sys.modules.keys()):
    if mod == "src" or mod.startswith("src."):
        del sys.modules[mod]

if str(GEOMIP_METHOD) not in sys.path:
    sys.path.insert(0, str(GEOMIP_METHOD))
# ========================= CONFIGURACIÓN =========================
EXCEL_PATH   = QNODES_SRC / ".samples" / "DatosPruebas2026_1JSME.xlsx"
SHEET_NAME   = "10A-Elementos"
MAX_TIME_SEG = 3600.0   # referencia informativa; GeoMIP no tiene timeout explícito

# Columna destino en Excel (1-based).
# Estructura por grupo de 3 cols: Partición | Pérdida | Tiempo
#   k=2 QNodes    → cols  4,  5,  6  (D, E, F)
#   k=2 Geometric → cols  7,  8,  9  (G, H, I)  ← activo
#   k=3 QNodes    → cols 10, 11, 12  (J, K, L)
#   k=3 Geometric → cols 13, 14, 15  (M, N, O)
#   k=4 QNodes    → cols 16, 17, 18  (P, Q, R)
#   k=4 Geometric → cols 19, 20, 21  (S, T, U)
#   k=5 QNodes    → cols 22, 23, 24  (V, W, X)
#   k=5 Geometric → cols 25, 26, 27  (Y, Z, AA)
COL_INICIO = 7   # primera columna del grupo (Partición)

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
    """Formatea el tiempo igual que los demás scripts de volcado."""
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
    """Extrae la letra de página del nombre de hoja y la aplica al singleton de GeoMIP."""
    m = re.match(r"\d+([A-Z])", sheet_name)
    if not m:
        raise ValueError(f"No se pudo extraer la página del nombre de hoja: {sheet_name!r}")
    aplicacion.pagina_sample_network = m.group(1)


def main() -> None:
    print(f"Excel  : {EXCEL_PATH}")
    print(f"Hoja   : {SHEET_NAME}")
    print(f"k      : 2  (bipartición GeoMIP Geometric)")
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
    tpm_file = f"N{len(estado_inicial)}{aplicacion.pagina_sample_network}.csv"
    print(f"Cargando TPM: {tpm_file} …")

    # 3 — Crear gestor y cargar TPM una sola vez
    gestor = Manager(estado_inicial)
    geo    = GeometricSIA(gestor)
    tpm    = geo.sia_cargar_tpm()
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

        if caso["row_idx"] in filas_rellenas:
            print("  → ya relleno, omitiendo\n")
            continue

        try:
            # Crear nueva instancia por caso para evitar estado residual en memoria_particiones
            geo = GeometricSIA(gestor)

            resultado = geo.aplicar_estrategia(
                condiciones, alcance_bin, mecanismo_bin, tpm
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
    print(f"Completado. {len(casos)} casos escritos en '{SHEET_NAME}', cols k=2 Geometric.")


if __name__ == "__main__":
    main()
