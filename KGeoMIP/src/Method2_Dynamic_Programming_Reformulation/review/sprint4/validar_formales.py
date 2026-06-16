"""Sprint 4: validaciones matemáticas formales pendientes del plan.

1. Monotonía causal: phi_2 <= phi_3 <= phi_4 <= phi_5 sobre un set de control.
2. Invariancia dimensional: permutar el orden de las variables no altera la
   composición de las particiones (módulo la permutación) ni el phi.

Uso: uv run python review/sprint4/validar_formales.py
"""

import json
import sys
from pathlib import Path

METHOD2 = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(METHOD2))

import numpy as np

from src.models.base.application import aplicacion

aplicacion.profiler_habilitado = False

from src.controllers.manager import Manager
from src.controllers.strategies.k_geometric import KGeometricSIA

SAMPLES = METHOD2.parents[1] / "data" / "samples"

CONTROL_MONOTONIA = [
    ("N5A.csv", "10000", "11111", "11111", "11111"),
    ("N5B.csv", "10000", "11111", "11111", "01111"),
    ("N6A.csv", "100000", "111111", "111111", "111111"),
    ("N6A.csv", "100000", "111111", "101011", "111111"),
    ("N8A.csv", "10000000", "11111111", "11111111", "11111111"),
    ("N10A.csv", "1000000000", "1111111111", "1111111111", "1111111111"),
    ("N10A.csv", "1000000000", "1111111111", "1111111111", "1010101010"),
    ("N15B.csv", "1" + "0" * 14, "1" * 15, "1" * 15, "1" * 15),
    ("N15B.csv", "1" + "0" * 14, "1" * 15, "110110110110110", "101010101010101"),
]

CASOS_INVARIANCIA = [
    ("N5A.csv", "10000", "11111", "11111", "11111", 2),
    ("N5A.csv", "10000", "11111", "11111", "11111", 3),
    ("N6A.csv", "100000", "111111", "111111", "111111", 2),
    ("N6A.csv", "100000", "111111", "101011", "111111", 3),
    ("N10A.csv", "1000000000", "1111111111", "1111111111", "1111111110", 2),
]


def correr(red, estado, cond, alc, mec, k, tpm=None):
    if tpm is None:
        tpm = np.genfromtxt(SAMPLES / red, delimiter=",")
    a = KGeometricSIA(Manager(estado_inicial=estado))
    sol = a.aplicar_estrategia(cond, alc, mec, tpm, k_objetivo=k)
    return float(sol.perdida), a.grupos_finales


def permutar_tpm(tpm: np.ndarray, pi: list[int]) -> np.ndarray:
    """TPM del sistema con variables renombradas: la variable j' nueva es pi[j'] vieja."""
    n = len(pi)
    filas = 1 << n
    nueva = np.empty_like(tpm)
    r_nuevo = np.arange(filas)
    r_viejo = np.zeros(filas, dtype=np.int64)
    for jp in range(n):
        r_viejo |= ((r_nuevo >> jp) & 1) << pi[jp]
    for jp in range(n):
        nueva[:, jp] = tpm[r_viejo, pi[jp]]
    return nueva


def permutar_cadena(cadena: str, pi: list[int]) -> str:
    return "".join(cadena[pi[jp]] for jp in range(len(pi)))


def main():
    informe = {"monotonia": [], "invariancia": []}
    fallas = 0

    print("=== 1. Monotonia phi_2 <= phi_3 <= phi_4 <= phi_5 ===", flush=True)
    for red, estado, cond, alc, mec in CONTROL_MONOTONIA:
        tpm = np.genfromtxt(SAMPLES / red, delimiter=",")
        phis = []
        for k in (2, 3, 4, 5):
            phi, _ = correr(red, estado, cond, alc, mec, k, tpm)
            phis.append(round(phi, 9))
        monotono = all(phis[i] <= phis[i + 1] + 1e-9 for i in range(3))
        if not monotono:
            fallas += 1
        print(f"{'OK ' if monotono else 'FALLA'} {red} mec={mec}: {phis}", flush=True)
        informe["monotonia"].append(
            {"red": red, "alcance": alc, "mecanismo": mec,
             "phi_2_5": phis, "monotono": bool(monotono)}
        )

    print("\n=== 2. Invariancia dimensional (permutacion de variables) ===", flush=True)
    rng = np.random.default_rng(73)
    for red, estado, cond, alc, mec, k in CASOS_INVARIANCIA:
        tpm = np.genfromtxt(SAMPLES / red, delimiter=",")
        n = len(estado)
        phi_base, grupos_base = correr(red, estado, cond, alc, mec, k, tpm)

        resultados_perm = []
        for permutacion in (list(range(n))[::-1], list(rng.permutation(n))):
            pi = [int(x) for x in permutacion]
            tpm_p = permutar_tpm(tpm, pi)
            phi_p, grupos_p = correr(
                red, permutar_cadena(estado, pi), permutar_cadena(cond, pi),
                permutar_cadena(alc, pi), permutar_cadena(mec, pi), k, tpm_p,
            )
            # mapear las etiquetas permutadas de vuelta: j' -> pi[j']
            grupos_mapeados = tuple(sorted(
                tuple(sorted((t, pi[j]) for t, j in g)) for g in grupos_p
            ))
            misma_phi = abs(phi_p - phi_base) <= 1e-6
            misma_comp = grupos_mapeados == grupos_base
            resultados_perm.append({
                "pi": pi, "phi": phi_p,
                "misma_phi": bool(misma_phi),
                "misma_composicion": bool(misma_comp),
            })
            if not misma_phi:
                fallas += 1
        estado_str = all(r["misma_phi"] for r in resultados_perm)
        comp_str = all(r["misma_composicion"] for r in resultados_perm)
        print(f"{'OK ' if estado_str else 'FALLA'} {red} k={k}: phi invariante={estado_str}, "
              f"composicion invariante={comp_str}", flush=True)
        informe["invariancia"].append({
            "red": red, "mecanismo": mec, "k": k, "phi_base": phi_base,
            "permutaciones": resultados_perm,
        })

    salida = Path(__file__).parent / "validacion_formales.json"
    salida.write_text(json.dumps(informe, ensure_ascii=False, indent=2),
                      encoding="utf-8")
    print(f"\nFallas duras (phi): {fallas}. Guardado en {salida}", flush=True)
    sys.exit(1 if fallas else 0)


if __name__ == "__main__":
    main()
