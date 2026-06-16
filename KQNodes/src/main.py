import sys
from pathlib import Path
import argparse

# Añadir raíz del proyecto al path para que shared_src y KQNodes sean importables
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from shared_src.controllers.manager import Manager
from KQNodes.src.strategies.kqnodes import KQNodes


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--k", type=int, default=3, help="Número de particiones k")
    parser.add_argument(
        "--max-time",
        type=float,
        default=300.0,
        help="Máximo tiempo por iteración de Queyranne en segundos",
    )
    args = parser.parse_args()

    # Fixed configuration requested by user
    estado_inicial = "1000000000"
    condiciones = "1111111111"
    alcance = "1101101101"
    mecanismo = "1111111111"
    k = int(args.k)
    MAX_TIEMPO_SEG = float(args.max_time)

    # Ruta exacta a las muestras indicadas (QNodes/src/.samples)
    sample_path = Path(__file__).resolve().parents[2] / "QNodes" / "src" / ".samples"

    # Cabecera estilizada similar a QNodes CLI
    from datetime import datetime as _dt
    now_ts = _dt.now().strftime("%H:%M")
    print(f"(hfskmip) 😺💬 Meow! What should I do next? ...🏡 QNodes git:(feature/KQNodes)⌚ {now_ts} 😀💬 ~ uv sync")
    print("warning: `VIRTUAL_ENV=...` does not match the project environment path `.venv` and will be ignored; use `--active` to target the active environment instead")
    print("Resolved 0 packages in 0ms")
    print("Checked 0 packages in 0ms")

    gestor = Manager(estado_inicial, ruta_base=sample_path)
    kq = KQNodes(gestor, k=k, refinar=True, verbose=True, max_tiempo_seg=MAX_TIEMPO_SEG)

    # Store alcance/mecanismo for formatted output later
    kq.alcance = alcance
    kq.mecanismo = mecanismo

    # Prepare subsistema with exact masks
    kq.sia_preparar_subsistema(estado_inicial, condiciones, alcance, mecanismo)

    resultado = kq.aplicar_estrategia()
    print(resultado)


if __name__ == "__main__":
    main()
