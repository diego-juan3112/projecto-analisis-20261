import numpy as np
import time
from pathlib import Path

# Adjusting python path to make imports work directly
import sys
method2_path = Path(__file__).resolve().parent
sys.path.append(str(method2_path))

from src.controllers.manager import Manager
from src.controllers.strategies.geometric import GeometricSIA
from src.controllers.strategies.k_geometric import KGeometricSIA


def run_test():
    # Setup for N5A.csv
    estado_inicio = "10000"
    condiciones = "11111"
    alcance = "11111"
    mecanismo = "11111"

    tpm_path = method2_path.parents[1] / "data" / "samples" / "N5A.csv"
    tpm = np.genfromtxt(tpm_path, delimiter=",")

    print("=" * 50)
    print("   COMPARATIVA DE ESTRATEGIAS (N5A.csv)   ")
    print("=" * 50)

    # 1. Prueba con GeometricSIA (K = 2, biparticiones originales)
    gestor_geo = Manager(estado_inicial=estado_inicio)
    analizador_geo = GeometricSIA(gestor_geo)
    try:
        solucion_geo = analizador_geo.aplicar_estrategia(
            condiciones, alcance, mecanismo, tpm
        )
    except Exception as e:  # noqa: BLE001 - script de prueba: reportar y seguir
        solucion_geo = f"Error en GeometricSIA: {e}"

    # 2. Prueba con KGeometricSIA (K = 3)
    gestor_kgeo = Manager(estado_inicial=estado_inicio)
    analizador_kgeo = KGeometricSIA(gestor_kgeo)
    solucion_kgeo = analizador_kgeo.aplicar_estrategia(
        condiciones, alcance, mecanismo, tpm, k_objetivo=3
    )

    # Resultados
    print("\n[RESULTADOS GeometricSIA - K=2]")
    if isinstance(solucion_geo, str):
        print(solucion_geo)
    else:
        print(f"-> Particiones : {solucion_geo.particion}")
        print(f"-> Perdida Phi : {solucion_geo.perdida}")
        print(f"-> T. Ejecucion: {solucion_geo.tiempo_ejecucion:.4f} s")

    print("\n[RESULTADOS KGeometricSIA - K=3]")
    if isinstance(solucion_kgeo, str):
        print(solucion_kgeo)
    else:
        print(f"-> Particiones : {solucion_kgeo.particion}")
        print(f"-> Perdida Phi : {solucion_kgeo.perdida}")
        print(f"-> T. Ejecucion: {solucion_kgeo.tiempo_ejecucion:.4f} s")


if __name__ == "__main__":
    run_test()
