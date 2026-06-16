"""Renderiza los diagramas PlantUML de KQNodes a PNG.

Fuente:   KQNodes/docs/diagramas/*.puml
Salida:   KQNodes/docs/img/*.png

Requiere: Java + Graphviz (dot) instalados, y plantuml.jar.
Por defecto busca el jar en .tools/plantuml.jar; se puede sobrescribir con la
variable de entorno PLANTUML_JAR.

Uso:  python scripts/render_diagramas.py
"""
import os
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PUML_DIR = ROOT / "KQNodes" / "docs" / "diagramas"
IMG_DIR = ROOT / "KQNodes" / "docs" / "img"
JAR = Path(os.environ.get("PLANTUML_JAR", ROOT / ".tools" / "plantuml.jar"))


def main():
    if not JAR.exists():
        raise SystemExit(
            f"No se encontró plantuml.jar en {JAR}. Descárgalo (Maven Central: "
            "net.sourceforge.plantuml:plantuml) o define PLANTUML_JAR."
        )
    IMG_DIR.mkdir(parents=True, exist_ok=True)
    pumls = sorted(PUML_DIR.glob("*.puml"))
    if not pumls:
        raise SystemExit(f"No hay .puml en {PUML_DIR}")
    cmd = [
        "java", "-DPLANTUML_LIMIT_SIZE=16384", "-jar", str(JAR),
        "-tpng", "-SdpiSize=150", "-o", str(IMG_DIR),
        *[str(p) for p in pumls],
    ]
    subprocess.run(cmd, check=True)
    print("PNG generados en", IMG_DIR.relative_to(ROOT))
    for png in sorted(IMG_DIR.glob("*.png")):
        print("  -", png.name)


if __name__ == "__main__":
    main()
