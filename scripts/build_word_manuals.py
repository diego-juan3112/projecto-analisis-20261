"""Genera versiones Word (.docx) de los manuales KQNodes a partir de los .md.

NO modifica los archivos .md originales: trabaja sobre copias temporales en un
directorio de build. Produce:
  - KQNodes/docs/Manual_Usuario_KQNodes.docx
  - KQNodes/docs/Manual_Tecnico_KQNodes.docx

Requisitos de formato (rúbrica): Word, tamaño carta, fuente Calibri 11,
tabla de contenidos con hipervínculos.

Uso:  python scripts/build_word_manuals.py
"""
import subprocess
import tempfile
from pathlib import Path

import pypandoc
from docx import Document
from docx.shared import Pt, Inches

ROOT = Path(__file__).resolve().parents[1]
DOCS = ROOT / "KQNodes" / "docs"
IMG_DIR = DOCS / "img"
FECHA = "14 de junio de 2026"

# ---------------------------------------------------------------------------
# 1) Reference docx: Calibri 11 + tamaño carta
# ---------------------------------------------------------------------------
def crear_reference_docx(destino: Path) -> Path:
    pandoc = pypandoc.get_pandoc_path()
    with open(destino, "wb") as f:
        subprocess.run(
            [pandoc, "--print-default-data-file", "reference.docx"],
            stdout=f, check=True,
        )
    doc = Document(str(destino))
    normal = doc.styles["Normal"]
    normal.font.name = "Calibri"
    normal.font.size = Pt(11)
    for section in doc.sections:
        section.page_width = Inches(8.5)
        section.page_height = Inches(11)
    doc.save(str(destino))
    return destino


# ---------------------------------------------------------------------------
# 2) Bloques de placeholder (captura / video)
# ---------------------------------------------------------------------------
def captura(titulo, que, comando, archivo):
    return (
        f"\n> **[CAPTURA DE PANTALLA — {titulo}]**\n"
        f">\n"
        f"> **Qué capturar:** {que}\n"
        f">\n"
        f"> **Comando para reproducir la pantalla:** `{comando}`\n"
        f">\n"
        f"> **Guardar la imagen en:** `{archivo}`\n"
        f">\n"
        f"> **Cómo insertarla en Word:** Insertar → Imágenes → seleccionar el archivo "
        f"anterior, y luego borrar este recuadro.\n\n"
    )

VIDEO_BLOCK = (
    "\n> **VIDEO TUTORIAL**\n"
    ">\n"
    "> Enlace al video (8–15 min): _[pegar aquí el enlace de YouTube/Drive cuando esté listo]_\n"
    ">\n"
    "> El video cubre: instalación desde cero en un sistema limpio, configuración del "
    "entorno y una ejecución completa mostrando distintos valores de k e interpretación "
    "de resultados.\n\n"
)

# Inserciones para el manual de USUARIO: (texto_a_insertar, linea_ancla_que_empieza_con)
# El bloque se inserta JUSTO ANTES de la línea ancla (= al final de la sección previa).
INSERCIONES_USUARIO = [
    # Video prominente al inicio (antes de la primera sección)
    (VIDEO_BLOCK, "## 1 ¿Qué es KQNodes"),
    # Captura de instalación: al final de §1.x, antes de §2
    (captura(
        "instalación",
        "la terminal tras ejecutar `uv sync`, mostrando las dependencias instaladas sin errores.",
        "cd KQNodes; uv sync",
        "KQNodes/docs/img/instalacion_uv_sync.png",
    ), "## 2 Cómo Ejecutar KQNodes"),
    # Captura de ejecución: al final de §2.1, antes de §2.2
    (captura(
        "ejecución",
        "la consola ejecutando KQNodes con k=3 (cabecera y progreso de iteraciones).",
        "cd KQNodes; uv run python src/main.py --k 3",
        "KQNodes/docs/img/ejecucion_k3.png",
    ), "### 2.2 Cómo interpretar la salida"),
    # Captura de salida/resultado: al final de §2.2, antes de §2.3
    (captura(
        "resultado",
        "el bloque final de resultado (partición, pérdida φ y tiempos) tras una ejecución.",
        "cd KQNodes; uv run python src/main.py --k 3",
        "KQNodes/docs/img/resultado_k3.png",
    ), "### 2.3 Volcado masivo al Excel"),
]

def seccion_diagramas() -> str:
    """Sección 'Diagramas UML' con las 4 imágenes PlantUML (rutas absolutas
    para que pandoc las incruste en el .docx). Se inserta antes de '## 2'."""
    def img(nombre, cap):
        ruta = (IMG_DIR / nombre).resolve().as_posix()
        return f"![{cap}]({ruta}){{ width=6.3in }}\n\n"

    return (
        "## Diagramas UML\n\n"
        "Los siguientes diagramas describen la arquitectura y el flujo de KQNodes. "
        "La fuente PlantUML está en `KQNodes/docs/diagramas/*.puml` y se regenera con "
        "`python scripts/render_diagramas.py`.\n\n"
        "### Diagrama de paquetes\n\n"
        + img("paquetes.png", "Diagrama de paquetes de KQNodes")
        + "### Diagrama de clases\n\n"
        + img("clases.png", "Diagrama de clases de KQNodes")
        + "### Diagrama de secuencia\n\n"
        + img("secuencia.png", "Diagrama de secuencia de aplicar_estrategia()")
        + "### Diagrama de estados\n\n"
        + img("estados.png", "Diagrama de estados (ciclo de vida) de KQNodes")
    )


def insertar_bloques(texto: str, inserciones) -> str:
    lineas = texto.splitlines(keepends=True)
    salida = []
    for ln in lineas:
        for bloque, ancla in inserciones:
            if ln.startswith(ancla):
                salida.append(bloque)
        salida.append(ln)
    return "".join(salida)


def yaml_front_matter(titulo: str, subtitulo: str) -> str:
    return (
        f"---\n"
        f'title: "{titulo}"\n'
        f'subtitle: "{subtitulo}"\n'
        f'author: "Equipo KQNodes — Universidad de Caldas"\n'
        f'date: "{FECHA}"\n'
        f"lang: es\n"
        f"---\n\n"
    )


# ---------------------------------------------------------------------------
# 3) Conversión
# ---------------------------------------------------------------------------
def convertir(md_src: Path, salida_docx: Path, titulo: str, subtitulo: str,
              ref_docx: Path, inserciones=None, nota_inicial: str = ""):
    texto = md_src.read_text(encoding="utf-8")
    if inserciones:
        texto = insertar_bloques(texto, inserciones)
    cuerpo = nota_inicial + texto
    contenido = yaml_front_matter(titulo, subtitulo) + cuerpo

    with tempfile.NamedTemporaryFile(
        "w", suffix=".md", delete=False, encoding="utf-8"
    ) as tmp:
        tmp.write(contenido)
        tmp_path = Path(tmp.name)

    pypandoc.convert_file(
        str(tmp_path),
        "docx",
        format="markdown",
        outputfile=str(salida_docx),
        extra_args=[
            "--toc",
            "--toc-depth=3",
            "--standalone",
            f"--reference-doc={ref_docx}",
        ],
    )
    tmp_path.unlink(missing_ok=True)
    print(f"  OK -> {salida_docx.relative_to(ROOT)}")


def main():
    IMG_DIR.mkdir(parents=True, exist_ok=True)
    (IMG_DIR / ".gitkeep").write_text("", encoding="utf-8")

    with tempfile.TemporaryDirectory() as td:
        ref = crear_reference_docx(Path(td) / "reference.docx")
        print("reference.docx (Calibri 11, carta) generado")

        print("Generando Manual de Usuario...")
        convertir(
            DOCS / "manual_usuario.md",
            DOCS / "Manual_Usuario_KQNodes.docx",
            "Manual de Usuario — KQNodes",
            "Proyecto K-QGMIP · Análisis y Diseño de Algoritmos · 2026-1",
            ref,
            inserciones=INSERCIONES_USUARIO,
        )

        print("Generando Manual Técnico...")
        convertir(
            DOCS / "manual_tecnico.md",
            DOCS / "Manual_Tecnico_KQNodes.docx",
            "Manual Técnico — KQNodes",
            "Proyecto K-QGMIP · Análisis y Diseño de Algoritmos · 2026-1",
            ref,
            inserciones=[(seccion_diagramas(), "## 2 Algoritmo Central")],
        )

    print("Listo. Los .md NO fueron modificados.")


if __name__ == "__main__":
    main()
