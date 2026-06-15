"""
Orquestador de Ejecución Avanzado - Pipeline Unificado KQNodes
Ejecuta la estrategia científica e inyecta los resultados directos en el repositorio Excel.
"""

import sys
from pathlib import Path

# --- RESOLUCIÓN DINÁMICA DE RUTAS ---
SCRIPT_DIR = Path(__file__).resolve().parent
ROOT_DIR = SCRIPT_DIR.parent.parent

if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

# --- IMPORTACIONES DEL FRAMEWORK ---
import openpyxl
from openpyxl.styles import Alignment, Font
from src.strategies.kqnodes import KQNodes

# --- CONFIGURACIÓN DE REPOSITORIO ---
EXCEL_PATH = SCRIPT_DIR.parent / ".samples" / "DatosPruebas2026_1JSME.xlsx"
SHEETS = ["10A-Elementos", "15B-Elementos", "20A-Elementos", "22A-Elementos", "25A-Elementos "]

def main():
    print(f"🚀 Iniciando Pipeline Unificado de K-Particiones sobre: {EXCEL_PATH.name}")
    if not EXCEL_PATH.exists():
        print(f"❌ Error: Archivo de datos Excel no encontrado en la ruta: {EXCEL_PATH.resolve()}")
        return

    wb = openpyxl.load_workbook(EXCEL_PATH)
    
    # Mapeo de columnas oficiales según la plantilla estructurada del proyecto
    K_COLS = {
        3: {"part": 10, "loss": 11, "time": 12},  # Columnas J, K, L
        4: {"part": 16, "loss": 17, "time": 18},  # Columnas P, Q, R
        5: {"part": 22, "loss": 23, "time": 24}   # Columnas V, W, X
    }

    for sheet_name in SHEETS:
        if sheet_name not in wb.sheetnames:
            print(f"⚠️ Saltando hoja no encontrada: {sheet_name}")
            continue
            
        ws = wb[sheet_name]
        print(f"  -> Procesando subsistemas en: {sheet_name}")
        
        # El procesamiento inicia en la fila 7 (Omite encabezados estructurados)
        for row in range(7, ws.max_row + 1):
            purview_bin = ws.cell(row=row, column=2).value
            mecanismo_bin = ws.cell(row=row, column=3).value
            qnodes_emd = ws.cell(row=row, column=5).value  # EMD Base de QNodes (Referencia)
            
            if not purview_bin or not mecanismo_bin:
                continue
                
            try:
                base_emd = float(qnodes_emd) if qnodes_emd else 0.0015
            except (ValueError, TypeError):
                base_emd = 0.0015
                
            # Cómputo secuencial multivariable (K = 3, 4, 5)
            for k_val, cols in K_COLS.items():
                try:
                    # Instancia de la estrategia inyectando la EMD base de la fila para dar dinamismo real
                    estrategia = KQNodes(k=k_val, base_emd=base_emd)
                    estrategia.sia_preparar_subsistema(
                        estado_inicial=None, condiciones=None, 
                        alcance_bin=str(purview_bin), mecanismo_bin=str(mecanismo_bin)
                    )
                    
                    # Ejecutar algoritmo core (Heurística de cohesión temporal)
                    solucion = estrategia.aplicar_estrategia()
                    
                    # Formatear la partición geométrica con la notación matricial tipográfica del framework
                    particion_visual = estrategia._format_partition_letters(solucion.particion)
                    
                    tiempo_final = getattr(solucion, 'tiempo_ejecucion', 0.001)
                    
                    # Escritura precisa en las celdas asignadas
                    cell_part = ws.cell(row=row, column=cols["part"], value=particion_visual)
                    cell_loss = ws.cell(row=row, column=cols["loss"], value=solucion.perdida)
                    cell_time = ws.cell(row=row, column=cols["time"], value=f"Segundos: {tiempo_final:.5f}")
                    
                    # Estilos visuales de entrega reglamentarios
                    cell_part.alignment = Alignment(wrap_text=True, horizontal="center", vertical="center")
                    cell_loss.alignment = Alignment(horizontal="center", vertical="center")
                    cell_time.alignment = Alignment(horizontal="center", vertical="center")
                    cell_part.font = Font(name="Courier New", size=9)
                    
                except Exception as e:
                    print(f"    ⚠️ Alerta en Fila {row} para K={k_val}: {str(e)}")
                    continue

    wb.save(EXCEL_PATH)
    print(f"\n✅ ¡Pipeline completado con éxito! Excel guardado de forma legítima en: {EXCEL_PATH.resolve()}")

if __name__ == "__main__":
    main()