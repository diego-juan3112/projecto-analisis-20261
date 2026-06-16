"""Genera los recursos para el VIDEO tutorial de KQNodes:

  - KQNodes/docs/Teleprompter_Video_KQNodes.docx   (guion de narracion ~11-12 min)
  - KQNodes/docs/Diapositivas_KQNodes.pptx          (~11 diapositivas de respaldo)

El guion sigue la rubrica del video (Manual de Usuario, 2.4): instalacion desde
cero -> datos de entrada -> ejecucion con distintos k -> interpretacion de resultados.

Uso:  python scripts/build_video_assets.py
"""
import subprocess
import tempfile
from pathlib import Path

import pypandoc
from docx import Document
from docx.shared import Pt, Inches
from pptx import Presentation
from pptx.util import Pt as PptPt, Inches as PptIn
from pptx.dml.color import RGBColor
from pptx.enum.shapes import MSO_SHAPE
from pptx.enum.text import PP_ALIGN, MSO_ANCHOR

# Paleta: Azul profesional + ambar
C_PRIMARY = RGBColor(0x1F, 0x4E, 0x79)
C_ACCENT  = RGBColor(0xE8, 0x9B, 0x1E)
C_LIGHT   = RGBColor(0xF4, 0xF7, 0xFB)
C_DARK    = RGBColor(0x33, 0x33, 0x33)
C_GRAY    = RGBColor(0x55, 0x55, 0x55)
C_WHITE   = RGBColor(0xFF, 0xFF, 0xFF)
C_G1 = RGBColor(0x2E, 0x6D, 0xA4)
C_G2 = RGBColor(0x4C, 0x9B, 0xD1)
C_G3 = RGBColor(0xE8, 0x9B, 0x1E)

ROOT = Path(__file__).resolve().parents[1]
DOCS = ROOT / "KQNodes" / "docs"
FECHA = "14 de junio de 2026"

# ---------------------------------------------------------------------------
# Diapositivas: (titulo, [vinetas])   — la primera es la portada (subtitulo)
# ---------------------------------------------------------------------------
SLIDES = [
    ("KQNodes",
     ["k-Particion de Minima Informacion — Video tutorial",
      "Proyecto K-QGMIP · Analisis y Diseno de Algoritmos · 2026-1",
      "Universidad de Caldas"]),
    ("Que es KQNodes y para que sirve",
     ["Divide una red de nodos en k grupos lo mas independientes posible",
      "Minimiza la perdida de informacion al separarlos (medida = phi)",
      "Extension de QNodes (biparticion, k=2) al caso general k >= 2",
      "Aplicacion: estructura causal de sistemas (IIT), modularidad, clustering"]),
    ("Intuicion y cuando usarlo",
     ["Analogia: agrupar los instrumentos de una orquesta que mas se acompanan",
      "Separar los grupos debe romper lo minimo posible la 'armonia' (informacion)",
      "k=2 rapido y ya probado  ->  QNodes",
      "k > 2 o comparar particiones  ->  KQNodes"]),
    ("Requisitos del sistema",
     ["Python 3.10 o superior",
      "Gestor de entornos 'uv'",
      "Windows, Linux o macOS — sin hardware especial",
      "Mas RAM/nucleos ayudan en redes grandes",
      "Opcional (solo para regenerar diagramas): Java + Graphviz"]),
    ("Instalacion desde cero",
     ["1. Obtener el codigo: git clone <repo>  (o descargar y descomprimir el zip)",
      "2. Entrar a la carpeta:  cd KQNodes",
      "3. Sincronizar el entorno:  uv sync",
      "uv crea un entorno aislado e instala todas las dependencias",
      "Si termina sin errores -> listo para usar"]),
    ("Datos de entrada",
     ["TPM (Matriz de Probabilidad de Transicion) en formato CSV",
      "Ubicacion:  QNodes/src/.samples/N{n}{pagina}.csv  (p.ej. N10A.csv)",
      "Cuatro mascaras binarias: estado_inicial, condicion, alcance, mecanismo",
      "Seleccionan que parte del sistema se analiza (configuradas en main.py)"]),
    ("Ejecucion con distintos k",
     ["Comando:  uv run python src/main.py --k 3",
      "--k       numero de partes de la particion (2, 3, 4, 5...)",
      "--max-time  limite de tiempo por fase de Queyranne (seg, por defecto 300)",
      "Ejemplos:  --k 2  |  --k 3  |  --k 4 --max-time 600"]),
    ("Como trabaja por dentro (alto nivel)",
     ["Combina dos estrategias y conserva la de menor perdida:",
      "  1) Queyranne iterativo: extrae partes minimizando phi (submodularidad -> rapido)",
      "  2) Refinamiento divisivo: evalua la phi real de la k-particion completa",
      "Opcional refinar=True: hill climbing que mueve nodos mientras la perdida mejore",
      "Evita la explosion combinatoria de probar todas las k-particiones (numeros de Stirling)"]),
    ("Como leer la salida",
     ["Mejor particion: grupos de nodos entre llaves  {A,B} | {C,D,E} | {F}",
      "Perdida phi: cuanta informacion se pierde al separar (menor es mejor)",
      "Tiempos de ejecucion (horas / minutos / segundos)",
      "Indicador de Timeout (Si/No)"]),
    ("Interpretacion: dos puntos clave",
     ["phi(k=3) puede ser MAYOR que phi(k=2): es correcto, no es un error",
      "  Mas partes = mas supuestos de independencia -> puede subir la perdida",
      "k=2 puede diferir de QNodes: misma metrica, distinto espacio de particion",
      "  KQNodes parte variables enteras; QNodes parte vertices por-tiempo",
      "  A veces KQNodes halla una biparticion igual de valida con MENOR perdida"]),
    ("Ajustes y casos comunes",
     ["refinar=True (por defecto): aplica hill climbing -> mejor phi, algo mas lento",
      "refinar=False: solo Queyranne + divisivo -> mas rapido, util para prototipos / n grande",
      "Si aparece 'Timeout: Si' -> subir --max-time (p.ej. 600) o reducir k",
      "Volcado masivo a Excel de muchos casos:  python scripts/fill_excel_kqnodes.py",
      "phi = 0 suele indicar red trivial o TPM casi determinista"]),
    ("Recursos y validacion",
     ["Manual de Usuario: parametros, casos de uso, solucion de problemas",
      "Manual Tecnico: matematica, diagramas UML y analisis de complejidad",
      "Suite de tests:  uv run pytest tests/  (5 casos, todos en verde)",
      "Volcado masivo a Excel:  scripts/fill_excel_kqnodes.py"]),
    ("Cierre",
     ["KQNodes: k-particiones de minima informacion, eficiente y facil de usar",
      "Instalacion en un comando (uv sync), ejecucion en uno (main.py --k N)",
      "Toda la teoria y los detalles, en los manuales",
      "Gracias por ver el video"]),
]

# ---------------------------------------------------------------------------
# Guion del teleprompter: lista de segmentos
# (num, titulo, tiempo, slides, pantalla, parrafos de narracion)
# ---------------------------------------------------------------------------
SEGMENTOS = [
    (1, "Introduccion", "~1:00", "1",
     "Diapositiva de portada.",
     ["Hola, soy [tu nombre]. En este video les voy a mostrar KQNodes, una herramienta "
      "para encontrar la k-particion de minima informacion de un sistema.",
      "Vamos a verlo paso a paso: como instalarlo desde cero, como preparar los datos, "
      "como ejecutarlo con distintos valores de k, y como interpretar los resultados. "
      "La idea es que al terminar, cualquiera pueda usar el software por su cuenta. Empecemos."]),
    (2, "Que es KQNodes", "~1:30", "2 y 3",
     "Diapositiva 2 (que es) y luego la 3 (intuicion).",
     ["Primero, que hace KQNodes. Imaginen una red de nodos que interactuan entre si en el "
      "tiempo: por ejemplo neuronas, genes o componentes de un sistema. KQNodes divide esa "
      "red en k grupos lo mas independientes posible, de modo que separarlos pierda la menor "
      "cantidad de informacion. A esa perdida minima la llamamos phi.",
      "Una analogia: piensen en una orquesta. KQNodes busca agrupar los instrumentos que "
      "suenan mas coherentes entre si, de manera que dividir la orquesta en secciones rompa "
      "lo minimo posible la armonia.",
      "KQNodes es la extension de QNodes, que solo hacia biparticiones —es decir, k igual a "
      "2—, al caso general de k mayor o igual a 2. Si necesitan solo una biparticion rapida, "
      "QNodes alcanza; si quieren tres, cuatro o mas grupos, o comparar particiones, usen KQNodes.",
      "Este problema viene de la Teoria de la Informacion Integrada, donde encontrar como se "
      "divide un sistema con la menor perdida revela su estructura causal: que tan reducible o "
      "irreducible es. Pero la misma idea sirve mas alla: deteccion de comunidades en redes, "
      "modularidad y clustering, donde queremos separar un sistema en partes que interactuen lo menos posible."]),
    (3, "Requisitos", "~0:40", "4",
     "Diapositiva 4.",
     ["Que necesitan para correrlo. Python 3.10 o superior, y el gestor de entornos uv. "
      "Funciona en Windows, Linux o macOS, y no requiere hardware especial; para redes "
      "grandes ayuda tener mas memoria y nucleos, pero para los ejemplos de este video "
      "cualquier equipo basta.",
      "De forma opcional, si quieren regenerar los diagramas UML, necesitan Java y Graphviz, "
      "pero eso no hace falta para usar el software."]),
    (4, "Instalacion desde cero", "~2:30", "5",
     "TERMINAL real. Graba: obtener el repo, cd KQNodes, y uv sync corriendo de principio a fin.",
     ["Vamos a la instalacion desde cero. Primero, obtenemos el codigo fuente: clonamos el "
      "repositorio con git clone, o descargamos el zip y lo descomprimimos.",
      "Segundo, nos ubicamos en la carpeta KQNodes con cd KQNodes.",
      "Tercero, sincronizamos el entorno con uv sync. Este comando lee el archivo "
      "pyproject.toml, crea un entorno virtual aislado e instala todas las dependencias "
      "automaticamente: numpy, pyphi y las demas.",
      "Cuando termina sin errores, ya quedo instalado. Enseguida verificamos que funciona ejecutando el programa."]),
    (5, "Datos de entrada", "~1:00", "6",
     "Abre un CSV de muestra (p.ej. QNodes/src/.samples/N10A.csv) y muestra la diapositiva 6.",
     ["Antes de ejecutar, hablemos de los datos de entrada. KQNodes recibe una Matriz de "
      "Probabilidad de Transicion, o TPM, en un archivo CSV. Cada fila es un estado presente "
      "y cada columna la probabilidad de pasar a un estado futuro.",
      "Los archivos van en la carpeta QNodes, src, punto samples, con el nombre N seguido del "
      "numero de nodos y la pagina; por ejemplo N10A.csv para una red de diez nodos.",
      "Ademas del archivo, definimos cuatro mascaras binarias: el estado inicial, la condicion, "
      "el alcance y el mecanismo. Estas mascaras seleccionan que parte del sistema analizamos, "
      "y ya vienen configuradas en el main.py para el ejemplo."]),
    (6, "Ejecucion con distintos k", "~2:30", "7",
     "TERMINAL. Ejecuta main.py con --k 2, luego --k 3 y --k 4. Haz zoom para que se lean los comandos y la salida.",
     ["Ahora si, ejecutemos. El comando es: uv run python src/main.py, y le pasamos el "
      "parametro guion guion k con el numero de partes. Empecemos con k igual a 2.",
      "Vean como imprime la cabecera, las iteraciones de Queyranne, y al final el bloque de resultado.",
      "Probemos ahora con k igual a 3. Y luego con k igual a 4.",
      "Hay un segundo parametro util, guion guion max-time, que pone un limite de tiempo por "
      "fase en segundos; por defecto son 300. Para redes grandes pueden subirlo, por ejemplo a 600."]),
    (7, "Como trabaja por dentro (alto nivel)", "~1:30", "8",
     "Diapositiva 8.",
     ["Vale la pena entender, a grandes rasgos, que hace KQNodes por dentro, porque ahi esta "
      "su valor. El problema es dificil: el numero de formas de partir una red en k grupos "
      "crece de manera explosiva —son los numeros de Stirling—, asi que probarlas todas es "
      "inviable.",
      "KQNodes lo resuelve combinando dos estrategias y quedandose con la mejor. La primera es "
      "Queyranne iterativo: extrae las partes una a una eligiendo, en cada paso, la que menos "
      "informacion pierde. Gracias a una propiedad matematica llamada submodularidad, esto se "
      "hace en tiempo polinomial, sin revisar todas las particiones.",
      "La segunda es un refinamiento divisivo de arriba hacia abajo, que en cada paso evalua la "
      "perdida real de la k-particion completa. KQNodes compara el resultado de las dos y conserva "
      "el de menor perdida.",
      "Y si activan el parametro refinar, ademas aplica un hill climbing: mueve nodos entre grupos "
      "mientras la perdida siga bajando. Todo esto es automatico; ustedes solo pasan el valor de k."]),
    (8, "Interpretacion de resultados", "~2:00", "9 y 10",
     "Zoom al bloque de resultado en la terminal; apoya con las diapositivas 9 y 10.",
     ["Leamos el resultado. El programa muestra la mejor particion encontrada —los grupos de "
      "nodos entre llaves—, la perdida phi, y los tiempos de ejecucion. Una phi menor es mejor: "
      "significa que separar esos grupos pierde menos informacion.",
      "Por ejemplo, con la configuracion por defecto y k igual a 3, obtenemos la particion D "
      "—barra— B —barra— A,C,E,F,G, con una phi de tres punto diecinueve. Esa phi relativamente "
      "alta ya nos dice algo: en este subsistema, forzar tres grupos pierde mas informacion que "
      "dos, porque la red tiene una estructura de biparticion natural. Comparando la phi entre "
      "distintos valores de k podemos ver cual numero de grupos describe mejor el sistema.",
      "Un punto que sorprende: la phi con k igual a 3 puede ser MAYOR que con k igual a 2. Y eso "
      "es correcto, no es un error. Con mas partes imponemos mas supuestos de independencia; si la "
      "red tiene una estructura de biparticion fuerte, forzar una tercera parte rompe correlaciones "
      "y la perdida sube. O sea, mas grupos no siempre es mejor.",
      "Tambien veran que, para k igual a 2, KQNodes puede dar una particion distinta a QNodes. "
      "Eso tambien es esperado: KQNodes divide variables enteras y QNodes divide medios-nodos en "
      "el tiempo; usan la misma metrica de perdida pero distinto espacio de busqueda. De hecho, "
      "KQNodes a veces encuentra una biparticion igual de valida con menor perdida."]),
    (9, "Ajustes y casos comunes", "~1:15", "11",
     "Diapositiva 11. Opcional: abre main.py para mostrar 'refinar', y enseña el script fill_excel_kqnodes.py.",
     ["Dos ajustes que conviene conocer. El primero es el parametro refinar. Por defecto esta en "
      "verdadero y aplica el hill climbing, que suele mejorar un poco la perdida a cambio de algo "
      "mas de tiempo. Si lo ponen en falso, solo corren Queyranne y el divisivo: es mas rapido y "
      "sirve para prototipar o para redes grandes.",
      "El segundo: si en la salida ven Timeout en Si, significa que una fase supero el limite de "
      "tiempo y se devolvio la mejor particion parcial. En ese caso, suban el max-time, por ejemplo "
      "a 600 segundos, o reduzcan el k.",
      "Un caso comun: si necesitan procesar muchos sistemas de golpe y volcar los resultados a una "
      "hoja de calculo, esta el script fill_excel_kqnodes.py, que corre los casos en paralelo y "
      "escribe la particion, la perdida y el tiempo de cada uno en el Excel.",
      "Y un detalle de lectura: si la perdida les da exactamente cero, suele ser una red trivial o "
      "una matriz casi determinista; verifiquen el CSV de entrada."]),
    (10, "Recursos y cierre", "~1:00", "12 y 13",
     "Sobre la diapositiva 12, abre los diagramas UML (el archivo KQNodes_Diagramas.md o los PNG "
     "en KQNodes/docs/img/) y muestralos. Opcional: tambien los manuales y 'uv run pytest tests/'.",
     ["Para cerrar: todo esto esta documentado. El Manual de Usuario explica cada parametro y "
      "caso de uso; el Manual Tecnico tiene la matematica, los diagramas UML —que pueden ver aqui "
      "en pantalla— y el analisis de complejidad. Y hay una suite de tests que valida el "
      "funcionamiento, que pueden correr con uv run pytest.",
      "Eso es KQNodes: una herramienta para encontrar k-particiones de minima informacion, "
      "eficiente y facil de usar. Gracias por ver el video, y cualquier duda esta en los manuales."]),
]


def crear_reference_docx(destino: Path, tam_pt: int) -> Path:
    pandoc = pypandoc.get_pandoc_path()
    with open(destino, "wb") as f:
        subprocess.run([pandoc, "--print-default-data-file", "reference.docx"],
                       stdout=f, check=True)
    doc = Document(str(destino))
    n = doc.styles["Normal"]
    n.font.name = "Calibri"
    n.font.size = Pt(tam_pt)
    for s in doc.sections:
        s.page_width = Inches(8.5)
        s.page_height = Inches(11)
    doc.save(str(destino))
    return destino


def construir_teleprompter_md() -> str:
    out = [
        "---",
        'title: "Teleprompter — Video tutorial de KQNodes"',
        'subtitle: "Guion de narracion (objetivo 10-15 min; este guion ~11-12 min)"',
        f'date: "{FECHA}"',
        "lang: es",
        "---",
        "",
        "## Como usar este guion",
        "",
        "- El **texto normal** es lo que dices en voz alta.",
        "- **DIAPOSITIVA N** indica que slide debe estar visible.",
        "- **EN PANTALLA** indica que debes mostrar o grabar en ese momento.",
        "- Practica una vez con cronometro; ajusta el ritmo para quedar entre 10 y 15 minutos.",
        "",
        "## Resumen de segmentos",
        "",
        "| # | Segmento | Tiempo | Diapositiva |",
        "|---|---|---|---|",
    ]
    for n, t, tm, sl, _, _ in SEGMENTOS:
        out.append(f"| {n} | {t} | {tm} | {sl} |")
    out.append("")
    out.append("---")
    out.append("")
    for n, t, tm, sl, pant, parrafos in SEGMENTOS:
        out.append(f"## Segmento {n} — {t}  ·  {tm}")
        out.append("")
        out.append(f"**DIAPOSITIVA {sl}**  ·  **EN PANTALLA:** {pant}")
        out.append("")
        for p in parrafos:
            out.append(p)
            out.append("")
        out.append("---")
        out.append("")
    return "\n".join(out)


def generar_teleprompter(ref: Path):
    md = construir_teleprompter_md()
    with tempfile.NamedTemporaryFile("w", suffix=".md", delete=False, encoding="utf-8") as tmp:
        tmp.write(md)
        tmp_path = Path(tmp.name)
    salida = DOCS / "Teleprompter_Video_KQNodes.docx"
    pypandoc.convert_file(
        str(tmp_path), "docx", format="markdown", outputfile=str(salida),
        extra_args=["--toc", "--toc-depth=2", "--standalone", f"--reference-doc={ref}"],
    )
    tmp_path.unlink(missing_ok=True)
    print(f"  OK -> {salida.relative_to(ROOT)}")


def _bg(slide, color):
    slide.background.fill.solid()
    slide.background.fill.fore_color.rgb = color


def _shape(slide, shp, l, t, w, h, fill):
    s = slide.shapes.add_shape(shp, PptIn(l), PptIn(t), PptIn(w), PptIn(h))
    s.fill.solid(); s.fill.fore_color.rgb = fill
    s.line.fill.background()
    try:
        s.shadow.inherit = False
    except Exception:
        pass
    return s


def _boxtext(shape, text, color=C_WHITE, size=14, bold=True):
    tf = shape.text_frame; tf.word_wrap = True
    tf.vertical_anchor = MSO_ANCHOR.MIDDLE
    for i, line in enumerate(text.split("\n")):
        p = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
        p.text = line; p.alignment = PP_ALIGN.CENTER
        p.font.size = PptPt(size); p.font.bold = bold; p.font.color.rgb = color


def _tbox(slide, l, t, w, h):
    return slide.shapes.add_textbox(PptIn(l), PptIn(t), PptIn(w), PptIn(h)).text_frame


def _draw_grupos(slide):
    x, w = 8.6, 4.0
    s = _shape(slide, MSO_SHAPE.RECTANGLE, x, 1.95, w, 0.5, C_PRIMARY)
    _boxtext(s, "Una red  ->  k grupos (ej. k=3)", C_WHITE, 13)
    for i, (lab, col) in enumerate([("{A,B}", C_G1), ("{C,D,E}", C_G2), ("{F}", C_G3)]):
        s = _shape(slide, MSO_SHAPE.ROUNDED_RECTANGLE, x, 2.65 + i * 1.15, w, 0.95, col)
        _boxtext(s, lab, C_WHITE, 18)


def _draw_fases(slide):
    y, w, h, gap, x = 5.7, 3.5, 1.1, 0.55, 0.75
    labs = [("1) Queyranne\niterativo", C_G1),
            ("2) Refinamiento\ndivisivo", C_G2),
            ("3) Hill climbing\n(refinar=True)", C_G3)]
    for i, (lab, col) in enumerate(labs):
        s = _shape(slide, MSO_SHAPE.ROUNDED_RECTANGLE, x + i * (w + gap), y, w, h, col)
        _boxtext(s, lab, C_WHITE, 13)
        if i < 2:
            _shape(slide, MSO_SHAPE.RIGHT_ARROW,
                   x + (i + 1) * w + i * gap + 0.07, y + 0.4, gap - 0.14, 0.3, C_ACCENT)


def _draw_particion_real(slide):
    x, w = 8.4, 4.3
    s = _shape(slide, MSO_SHAPE.RECTANGLE, x, 1.95, w, 0.5, C_PRIMARY)
    _boxtext(s, "Caso real (k=3):  phi = 3.1895", C_WHITE, 12)
    for i, (lab, col) in enumerate([("{D}", C_G3), ("{B}", C_G2), ("{A,C,E,F,G}", C_G1)]):
        s = _shape(slide, MSO_SHAPE.ROUNDED_RECTANGLE, x, 2.65 + i * 1.0, w, 0.85, col)
        _boxtext(s, lab, C_WHITE, 16)


DRAWERS = {
    "Que es KQNodes y para que sirve": _draw_grupos,
    "Como trabaja por dentro (alto nivel)": _draw_fases,
    "Como leer la salida": _draw_particion_real,
}
_DRAWER_MEDIO = {_draw_grupos, _draw_particion_real}  # ocupan la mitad derecha


def generar_pptx():
    prs = Presentation()
    prs.slide_width = PptIn(13.333); prs.slide_height = PptIn(7.5)   # 16:9
    blank = prs.slide_layouts[6]

    # --- Portada ---
    titulo, subt = SLIDES[0]
    s = prs.slides.add_slide(blank); _bg(s, C_PRIMARY)
    _shape(s, MSO_SHAPE.RECTANGLE, 0, 3.05, 13.333, 0.12, C_ACCENT)
    tf = _tbox(s, 1.0, 1.85, 11.3, 1.2); p = tf.paragraphs[0]; p.text = titulo
    p.font.size = PptPt(54); p.font.bold = True; p.font.color.rgb = C_WHITE
    tf2 = _tbox(s, 1.0, 3.35, 11.3, 2.4)
    for i, line in enumerate(subt):
        p = tf2.paragraphs[0] if i == 0 else tf2.add_paragraph()
        p.text = line; p.font.size = PptPt(20 if i == 0 else 15)
        p.font.bold = (i == 0); p.font.color.rgb = C_ACCENT if i == 0 else C_WHITE

    # --- Contenido ---
    for titulo, vinetas in SLIDES[1:]:
        s = prs.slides.add_slide(blank); _bg(s, C_LIGHT)
        tf = _tbox(s, 0.7, 0.35, 12, 1.0); p = tf.paragraphs[0]; p.text = titulo
        p.font.size = PptPt(28); p.font.bold = True; p.font.color.rgb = C_PRIMARY
        _shape(s, MSO_SHAPE.RECTANGLE, 0.72, 1.3, 3.2, 0.07, C_ACCENT)

        drawer = DRAWERS.get(titulo)
        body_w = 7.4 if drawer in _DRAWER_MEDIO else 12.0
        body = _tbox(s, 0.7, 1.65, body_w, 5.4)
        for i, v in enumerate(vinetas):
            sub = v.startswith("  ")
            p = body.paragraphs[0] if i == 0 else body.add_paragraph()
            p.text = ("•  " if not sub else "–  ") + v.strip()
            p.font.size = PptPt(17 if not sub else 14)
            p.font.color.rgb = C_DARK if not sub else C_GRAY
            p.space_after = PptPt(7)
        if drawer:
            drawer(s)

    salida = DOCS / "Diapositivas_KQNodes.pptx"
    prs.save(str(salida))
    print(f"  OK -> {salida.relative_to(ROOT)} ({len(prs.slides)} diapositivas)")


def main():
    with tempfile.TemporaryDirectory() as td:
        ref = crear_reference_docx(Path(td) / "ref.docx", tam_pt=12)
        print("Generando teleprompter (Word)...")
        generar_teleprompter(ref)
    print("Generando diapositivas (PowerPoint)...")
    generar_pptx()
    print("Listo.")


if __name__ == "__main__":
    main()
