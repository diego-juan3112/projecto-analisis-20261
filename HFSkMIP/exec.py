"""
Ejecuta HFSkMIP: añade al path el paquete `src` de Method2 (GeoMIP) y este proyecto.
"""

from pathlib import Path
import sys

_ROOT = Path(__file__).resolve().parent
_REPO = _ROOT.parent
_METHOD2 = (
    _REPO
    / "GeoMIP"
    / "src"
    / "Method2_Dynamic_Programming_Reformulation"
)
sys.path[:0] = [str(_METHOD2), str(_ROOT)]

from hfskmip.main import iniciar  # noqa: E402


def main() -> None:
    iniciar()


if __name__ == "__main__":
    main()
