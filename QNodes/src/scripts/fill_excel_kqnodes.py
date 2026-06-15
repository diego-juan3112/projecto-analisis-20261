"""
Orquestador KQNodes - Resiliencia Multiprocesamiento para Windows 11
"""

import re
import sys
import traceback
from pathlib import Path
import gc
import time
import multiprocessing
import openpyxl

# --- RUTAS DINÁMICAS ABSOLUTAS ---
# Esto resuelve el ModuleNotFoundError independientemente de uv o del entorno virtual
SCRIPT_DIR = Path(__file__).resolve().parent    # src/scripts
SRC_DIR = SCRIPT_DIR.parent                     # src
QNODES_ROOT = SRC_DIR.parent                    # QNodes

# Inyectamos la raíz QNodes al inicio del path para que Python encuentre 'src.strategies...'
sys.path.insert(0, str(QNODES_ROOT))

# Importaciones locales usando la estructura correcta
from src.models.base.application import aplicacion
from src.controllers.manager import Manager
from src.strategies.kqnodes import KQNodes  # <-- IMPORTACIÓN CORREGIDA

# Columna destino en Excel (1-based).
# Estructura por grupo de 3 cols: Partición | Pérdida | Tiempo
#   k=2 QNodes    → cols  4,  5,  6  (D, E, F)   ← activo
#   k=2 Geometric → cols  7,  8,  9  (G, H, I)
#   k=3 QNodes    → cols 10, 11, 12  (J, K, L)
#   k=3 Geometric → cols 13, 14, 15  (M, N, O)
#   k=4 QNodes    → cols 16, 17, 18  (P, Q, R)
#   k=4 Geometric → cols 19, 20, 21  (S, T, U)
#   k=5 QNodes    → cols 22, 23, 24  (V, W, X)
#   k=5 Geometric → cols 25, 26, 27  (Y, Z, AA)

# ========================= CONFIGURACIÓN =========================
EXCEL_PATH   = SRC_DIR / ".samples" / "DatosPruebas2026_1JSME.xlsx"
SHEET_NAME   = "25A-Elementos "
K            = 5
MAX_TIME_SEG = 3000.0      
COL_INICIO   = 22   # primera columna del grupo (Partición)          
# =================================================================

def letras_a_binario(letras, sistema):
    return "".join("1" if c in letras else "0" for c in sistema)

def formatear_tiempo(tiempo_s):
    return f"Horas: {tiempo_s / 3600:.2f} = Minutos: {tiempo_s / 60:.1f} = Segundos: {tiempo_s:.4f}"

def escribir_resultado(excel_path, sheet_name, row_idx, col_inicio, particion, perdida, tiempo):
    wb = openpyxl.load_workbook(excel_path)
    ws = wb[sheet_name]
    ws.cell(row_idx, col_inicio).value = particion
    ws.cell(row_idx, col_inicio + 1).value = str(round(float(perdida), 4)) if isinstance(perdida, (int, float)) else perdida
    ws.cell(row_idx, col_inicio + 2).value = tiempo
    wb.save(excel_path)
    wb.close()

def worker_proceso_calculo(estado_inicial, condiciones, alcance_bin, mecanismo_bin, k_val, max_time, resultado_compartido):
    try:
        gestor = Manager(estado_inicial, ruta_base=SRC_DIR / ".samples")
        kq = KQNodes(gestor, k=k_val, max_tiempo_seg=max_time)
        kq.sia_preparar_subsistema(estado_inicial, condiciones, alcance_bin, mecanismo_bin)
        
        resultado = kq.aplicar_estrategia()
        
        resultado_compartido["particion_str"] = kq._format_partition_letters(resultado.particion)
        resultado_compartido["tiempo_str"]    = formatear_tiempo(resultado.tiempo_ejecucion)
        resultado_compartido["perdida"]       = float(resultado.perdida)
        resultado_compartido["success"]       = True
    except Exception as e:
        resultado_compartido["success"] = False
        resultado_compartido["error_exc"] = f"{type(e).__name__}: {str(e)}"

def main():
    print("=" * 70)
    print(f" ORQUESTADOR KQNodes (K={K}) - ENTORNO AISLADO ")
    print("=" * 70)

    if not EXCEL_PATH.exists():
        print(f"Error: Excel no encontrado en {EXCEL_PATH}")
        sys.exit(1)

    wb_r = openpyxl.load_workbook(EXCEL_PATH, data_only=True)
    ws_r = wb_r[SHEET_NAME]
    estado_inicial = str(ws_r.cell(1, 2).value).strip()
    sistema = str(ws_r.cell(2, 2).value).strip()
    condiciones = "1" * len(estado_inicial)
    
    casos = []
    for row_idx in range(6, ws_r.max_row + 1):
        alc = ws_r.cell(row_idx, 2).value
        mec = ws_r.cell(row_idx, 3).value
        if alc and mec:
            casos.append({"row_idx": row_idx, "alcance_letras": str(alc).strip(), "mecanismo_letras": str(mec).strip()})
    wb_r.close()

    m = re.match(r"\d+([A-Z])", SHEET_NAME)
    if m: aplicacion.set_pagina_red_muestra(m.group(1))

    print(f"Sistema: {sistema} | Casos a procesar: {len(casos)}\n")

    for i, caso in enumerate(casos):
        alcance_bin = letras_a_binario(caso["alcance_letras"], sistema)
        mecanismo_bin = letras_a_binario(caso["mecanismo_letras"], sistema)

        print(f"[{i + 1}/{len(casos)}] Fila={caso['row_idx']} | Alcance={caso['alcance_letras']} | Mecanismo={caso['mecanismo_letras']}")

        manager = multiprocessing.Manager()
        resultado_compartido = manager.dict()
        resultado_compartido["success"] = False

        proceso_calculo = multiprocessing.Process(
            target=worker_proceso_calculo,
            args=(estado_inicial, condiciones, alcance_bin, mecanismo_bin, K, MAX_TIME_SEG, resultado_compartido)
        )

        tiempo_inicio = time.time()
        proceso_calculo.start()
        proceso_calculo.join(timeout=MAX_TIME_SEG)

        if proceso_calculo.is_alive():
            print("  ⚠ Timeout alcanzado. Subproceso interrumpido.")
            proceso_calculo.terminate()
            proceso_calculo.join()
            particion_str, perdida, tiempo_str = "TIMEOUT_ALCANZADO", -1.0, formatear_tiempo(time.time() - tiempo_inicio)
        else:
            if resultado_compartido.get("success"):
                particion_str = resultado_compartido["particion_str"]
                tiempo_str = resultado_compartido["tiempo_str"]
                perdida = resultado_compartido["perdida"]
                print(f"  ✓ Partición: {particion_str} | Pérdida: {perdida:.4f}")
            else:
                err = resultado_compartido.get("error_exc", "Error desconocido")
                print(f"  ✕ Error Interno: {err}")
                particion_str, perdida, tiempo_str = "ERROR_EJECUCION", -2.0, formatear_tiempo(time.time() - tiempo_inicio)

        try:
            escribir_resultado(EXCEL_PATH, SHEET_NAME, caso["row_idx"], COL_INICIO, particion_str, perdida, tiempo_str)
        except Exception as e:
            print(f"  ❌ Error E/S Excel: {e}")

        manager.shutdown()
        del resultado_compartido, proceso_calculo
        gc.collect()

if __name__ == "__main__":
    multiprocessing.freeze_support()
    main()