"""Sprint 3: validacion de la nueva KGeometricSIA.

A. Prueba de aceptacion k=2 (no negociable): KGeometricSIA(k=2) debe
   reproducir EXACTAMENTE a GeometricSIA (misma particion, mismo phi) en la
   bateria de 15 casos del Sprint 2, con mascaras triviales y no triviales.
B. Calidad de la heuristica: k=3 (y k=4 donde es barato) contra fuerza bruta
   exacta sobre el espacio de particiones de vertices, en n pequeno.

Uso: uv run python review/sprint3/validar_kgeo.py
"""

import json
import sys
import time
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

CASOS_K2 = [
    ("N3A.csv", "100", "111", "111", "111"),
    ("N4A.csv", "1000", "1111", "1111", "1111"),
    ("N4B.csv", "1000", "1111", "0111", "1111"),
    ("N5A.csv", "10000", "11111", "11111", "11111"),
    ("N5B.csv", "10000", "11111", "11111", "01111"),
    ("N6A.csv", "100000", "111111", "101011", "111111"),
    ("N6A.csv", "100000", "111111", "111111", "111111"),
    ("N8A.csv", "10000000", "11111111", "11111111", "11111111"),
    ("N8A.csv", "10000000", "11111111", "11011011", "10101010"),
    ("N10A.csv", "1000000000", "1111111111", "1111111111", "1111111111"),
    ("N10A.csv", "1000000000", "1111111111", "1111111111", "1111111110"),
    ("N10A.csv", "1000000000", "1111111111", "0101010101", "1111111111"),
    ("N10A.csv", "1000000000", "1111111111", "1111111111", "1010101010"),
    ("N15B.csv", "1" + "0" * 14, "1" * 15, "1" * 15, "111111111111000"),
    ("N15B.csv", "1" + "0" * 14, "1" * 15, "110110110110110", "101010101010101"),
]

# (red, estado, cond, alcance, mecanismo, k) para fuerza bruta
CASOS_BF = [
    ("N3A.csv", "100", "111", "111", "111", 3),
    ("N4A.csv", "1000", "1111", "1111", "1111", 3),
    ("N4B.csv", "1000", "1111", "0111", "1111", 3),
    ("N5A.csv", "10000", "11111", "11111", "11111", 3),
    ("N5B.csv", "10000", "11111", "11111", "01111", 3),
    ("N6A.csv", "100000", "111111", "111111", "111111", 3),
    ("N5A.csv", "10000", "11111", "11111", "11111", 4),
    ("N6A.csv", "100000", "111111", "101011", "111111", 3),
    ("N10A.csv", "1000000000", "1111111111", "1110000000", "1100000000", 3),
]


def particiones_k(elementos: list, k: int):
    """Genera todas las particiones de `elementos` en exactamente k partes no vacias."""
    n = len(elementos)

    def rec(i, partes):
        if i == n:
            if len(partes) == k:
                yield [frozenset(p) for p in partes]
            return
        # poda: si ni metiendo cada resto en partes nuevas se llega a k
        if len(partes) + (n - i) < k:
            return
        for p in partes:
            p.append(elementos[i])
            yield from rec(i + 1, partes)
            p.pop()
        if len(partes) < k:
            partes.append([elementos[i]])
            yield from rec(i + 1, partes)
            partes.pop()

    yield from rec(0, [])


def main():
    resultados = {"k2": [], "fuerza_bruta": []}
    fallas_k2 = 0

    print("=== A. Aceptacion k=2 vs GeometricSIA ===", flush=True)
    for red, estado, cond, alc, mec in CASOS_K2:
        tpm = np.genfromtxt(SAMPLES / red, delimiter=",")

        geo = GeometricSIA(Manager(estado_inicial=estado))
        t0 = time.perf_counter()
        sol_g = geo.aplicar_estrategia(cond, alc, mec, tpm)
        t_g = time.perf_counter() - t0

        kgeo = KGeometricSIA(Manager(estado_inicial=estado))
        t0 = time.perf_counter()
        sol_k = kgeo.aplicar_estrategia(cond, alc, mec, tpm, k_objetivo=2)
        t_k = time.perf_counter() - t0

        igual_part = sol_g.particion == sol_k.particion
        igual_phi = float(sol_g.perdida) == float(sol_k.perdida)
        ok = igual_part and igual_phi
        if not ok:
            fallas_k2 += 1
        registro = {
            "red": red, "alcance": alc, "mecanismo": mec,
            "estatus": "OK" if ok else "FALLA",
            "phi_geometric": float(sol_g.perdida),
            "phi_kgeo": float(sol_k.perdida),
            "t_geometric_s": round(t_g, 4), "t_kgeo_s": round(t_k, 4),
        }
        if not igual_part:
            registro["particion_geometric"] = sol_g.particion
            registro["particion_kgeo"] = sol_k.particion
        print(f"{registro['estatus']} {red} alc={alc} mec={mec} "
              f"phi_g={registro['phi_geometric']:.6f} phi_k={registro['phi_kgeo']:.6f}",
              flush=True)
        resultados["k2"].append(registro)

    print("\n=== B. k>=3 vs fuerza bruta ===", flush=True)
    for red, estado, cond, alc, mec, k in CASOS_BF:
        tpm = np.genfromtxt(SAMPLES / red, delimiter=",")
        kgeo = KGeometricSIA(Manager(estado_inicial=estado))
        t0 = time.perf_counter()
        sol = kgeo.aplicar_estrategia(cond, alc, mec, tpm, k_objetivo=k)
        t_greedy = time.perf_counter() - t0

        # fuerza bruta sobre el MISMO espacio y la MISMA funcion de perdida
        vertices = sorted(
            [(0, int(d)) for d in kgeo.sia_subsistema.dims_ncubos]
            + [(1, int(f)) for f in kgeo.sia_subsistema.indices_ncubos]
        )
        mejor_phi, mejor_part, evaluadas = None, None, 0
        t0 = time.perf_counter()
        for particion in particiones_k(vertices, k):
            phi, _ = kgeo._medir_perdida(particion)
            evaluadas += 1
            if mejor_phi is None or phi < mejor_phi:
                mejor_phi, mejor_part = phi, particion
        t_bf = time.perf_counter() - t0

        gap = float(sol.perdida) - float(mejor_phi)
        registro = {
            "red": red, "alcance": alc, "mecanismo": mec, "k": k,
            "phi_greedy": float(sol.perdida),
            "phi_optimo_bf": float(mejor_phi),
            "gap_absoluto": round(gap, 9),
            "optimo_alcanzado": bool(abs(gap) <= 1e-9),
            "particiones_evaluadas_bf": evaluadas,
            "t_greedy_s": round(t_greedy, 4),
            "t_bf_s": round(t_bf, 4),
            "poda_fase2": kgeo.estadisticas_poda,
        }
        print(f"{red} k={k}: greedy={registro['phi_greedy']:.6f} "
              f"bf={registro['phi_optimo_bf']:.6f} gap={registro['gap_absoluto']} "
              f"(bf evaluo {evaluadas} particiones en {t_bf:.2f}s)", flush=True)
        resultados["fuerza_bruta"].append(registro)

    salida = Path(__file__).parent / "validacion_kgeo.json"
    salida.write_text(json.dumps(resultados, ensure_ascii=False, indent=2),
                      encoding="utf-8")
    n_opt = sum(r["optimo_alcanzado"] for r in resultados["fuerza_bruta"])
    print(f"\nk=2: {len(CASOS_K2) - fallas_k2}/{len(CASOS_K2)} OK; "
          f"fuerza bruta: optimo alcanzado en {n_opt}/{len(CASOS_BF)}. "
          f"Guardado en {salida}", flush=True)
    sys.exit(1 if fallas_k2 else 0)


if __name__ == "__main__":
    main()
