"""Sprint 2: validacion de la reformulacion contra el oraculo O(2^n).

1. Equivalencia de marginalizacion: NCube._mean_axis_flat vs np.mean clasico
   en cubos 3D y 4D, todos los ejes y combinaciones (validacion seccion 9.5).
2. Equivalencia de endianness: indice plano = int(bits invertidos) (seccion 9.6).
3. Oraculo vs optimizado: misma particion (cadena exacta) y mismo phi
   (|delta| <= 1e-5) en una bateria de casos con n <= 12.

Uso: uv run python review/sprint2/validar_oraculo.py
"""

import itertools
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
from src.models.core.ncube import NCube

SAMPLES = METHOD2.parents[1] / "data" / "samples"
TOL_PHI = 1e-5


def test_marginalizacion_equivalente() -> list[str]:
    """_mean_axis_flat == reshape((2,)*n).mean(eje) para n=3,4, todos los ejes."""
    fallos = []
    rng = np.random.default_rng(73)
    for n in (3, 4):
        datos = rng.random(2**n).astype(np.float32)
        for pos in range(n):  # posicion local de la variable
            eje_local = n - 1 - pos
            esperado = (
                datos.reshape((2,) * n)
                .mean(axis=n - 1 - pos)  # eje numpy de la variable en posicion pos
                .ravel()
                .astype(np.float32)
            )
            obtenido = NCube._mean_axis_flat(datos, n, eje_local)
            if not np.allclose(esperado, obtenido, atol=1e-6):
                fallos.append(f"_mean_axis_flat n={n} pos={pos}")
        # combinaciones de dos ejes (conmutatividad)
        for p1, p2 in itertools.combinations(range(n), 2):
            esperado = (
                datos.reshape((2,) * n)
                .mean(axis=(n - 1 - p1, n - 1 - p2))
                .ravel()
                .astype(np.float32)
            )
            paso1 = NCube._mean_axis_flat(datos, n, n - 1 - p2)  # quita pos p2
            # tras quitar p2 (p2 > p1), la posicion de p1 no cambia
            paso2 = NCube._mean_axis_flat(paso1, n - 1, (n - 1) - 1 - p1)
            if not np.allclose(esperado, paso2, atol=1e-6):
                fallos.append(f"composicion n={n} ejes=({p1},{p2})")
    return fallos


def test_endianness() -> list[str]:
    """El indice plano del estado s es sum_p s_p 2^p (little-endian)."""
    fallos = []
    for n in (3, 4, 5):
        col = np.arange(2**n, dtype=np.float32)  # flat[r] = r si el mapeo es identidad
        cubo = col.reshape((2,) * n)
        for r in range(2**n):
            estado = [(r >> p) & 1 for p in range(n)]  # posicion p = bit p
            # indexacion por ejes: eje a <-> variable n-1-a
            idx_ejes = tuple(estado[n - 1 - a] for a in range(n))
            if cubo[idx_ejes] != r:
                fallos.append(f"endianness n={n} r={r}")
                break
    return fallos


CASOS = [
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


def correr(Estrategia, red, estado, cond, alc, mec):
    tpm = np.genfromtxt(SAMPLES / red, delimiter=",")
    analizador = Estrategia(Manager(estado_inicial=estado))
    t0 = time.perf_counter()
    sol = analizador.aplicar_estrategia(cond, alc, mec, tpm)
    dt = time.perf_counter() - t0
    return sol.particion, float(sol.perdida), dt


def main():
    fallos_marg = test_marginalizacion_equivalente()
    fallos_endian = test_endianness()
    print(f"[marginalizacion] {'OK' if not fallos_marg else fallos_marg}")
    print(f"[endianness]      {'OK' if not fallos_endian else fallos_endian}")

    from src.controllers.strategies.geometric import GeometricSIA as Optimizada
    from src.controllers.strategies.geometric_oracle import GeometricSIA as Oraculo

    resultados = []
    fallas = 0
    for red, estado, cond, alc, mec in CASOS:
        part_o, phi_o, t_o = correr(Oraculo, red, estado, cond, alc, mec)
        part_n, phi_n, t_n = correr(Optimizada, red, estado, cond, alc, mec)
        igual_part = part_o == part_n
        igual_phi = abs(phi_o - phi_n) <= TOL_PHI
        estatus = "OK" if (igual_part and igual_phi) else "FALLA"
        if estatus == "FALLA":
            fallas += 1
        registro = {
            "red": red,
            "alcance": alc,
            "mecanismo": mec,
            "estatus": estatus,
            "phi_oraculo": phi_o,
            "phi_optimizada": phi_n,
            "t_oraculo_s": round(t_o, 4),
            "t_optimizada_s": round(t_n, 4),
            "particion_igual": igual_part,
        }
        if not igual_part:
            registro["particion_oraculo"] = part_o
            registro["particion_optimizada"] = part_n
        print(
            f"{estatus} {red} mec={mec} phi_o={phi_o:.6f} phi_n={phi_n:.6f} "
            f"t_o={t_o:.3f}s t_n={t_n:.3f}s part_igual={igual_part}",
            flush=True,
        )
        resultados.append(registro)

    salida = Path(__file__).parent / "validacion_oraculo.json"
    salida.write_text(
        json.dumps(
            {
                "marginalizacion": fallos_marg or "OK",
                "endianness": fallos_endian or "OK",
                "casos": resultados,
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    print(f"\nTotal casos: {len(resultados)}, fallas: {fallas}. Guardado en {salida}")
    sys.exit(1 if (fallas or fallos_marg or fallos_endian) else 0)


if __name__ == "__main__":
    main()
