#!/usr/bin/env python3
"""
Genera N15A2.csv y N15B2.csv con 0/1 (no sobrescribe si ya existen).
Usa semillas fijas para reproducibilidad (42, 43).
"""
from pathlib import Path
import numpy as np

OUT_DIR = Path(__file__).resolve().parent.parent / "src" / ".samples"
OUT_DIR.mkdir(parents=True, exist_ok=True)

def gen_binary(out_path: Path, seed: int, N: int = 15):
    if out_path.exists():
        print(f"Skipping existing file: {out_path}")
        return
    rng = np.random.RandomState(seed)
    states = rng.randint(0, 2, size=(2 ** N, N), dtype=np.int8)
    np.savetxt(out_path, states, delimiter=",", fmt="%d")
    print(f"Wrote {out_path} ({states.shape[0]}x{states.shape[1]})")

if __name__ == "__main__":
    gen_binary(OUT_DIR / "N15A2.csv", seed=42)
    gen_binary(OUT_DIR / "N15B2.csv", seed=43)
