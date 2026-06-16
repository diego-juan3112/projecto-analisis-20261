"""
Genera la hoja 'Análisis 10-15-20' dentro de docs/DatosPruebas2026_1.xlsx con:
  - Tablas resumen (φ promedio y tiempo promedio por k y por algoritmo).
  - Gráficos nativos de Excel (barras/líneas) sobre esos resúmenes.
  - Interpretación textual de los resultados.

Lee los valores ya calculados de las hojas 10A/15B/20A-Elementos y NO modifica
ninguna de ellas. Las fórmulas existentes del libro se preservan (se carga con
data_only=False para guardar). Re-ejecutar regenera la hoja de análisis.

Uso:
    uv run python scripts/analizar_resultados.py
"""

import re
import statistics as st
from pathlib import Path

import openpyxl
from openpyxl.chart import BarChart, LineChart, Reference
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.utils import get_column_letter

PROJECT_ROOT = Path(__file__).resolve().parent.parent
EXCEL_PATH   = PROJECT_ROOT / "docs" / "DatosPruebas2026_1.xlsx"
SHEET_OUT    = "Análisis 10-15-20"

# Hojas a analizar y su N (número de elementos).
HOJAS = [("10A-Elementos", 10), ("15B-Elementos", 15), ("20A-Elementos", 20)]

# (k, algoritmo) -> (col Pérdida, col Tiempo)  [1-based]
GRUPOS = {
    ("k2", "QNodes"):    (5, 6),   ("k2", "Geometric"): (8, 9),
    ("k3", "QNodes"):    (11, 12), ("k3", "Geometric"): (14, 15),
    ("k4", "QNodes"):    (17, 18), ("k4", "Geometric"): (20, 21),
    ("k5", "QNodes"):    (23, 24), ("k5", "Geometric"): (26, 27),
}
HEADER_ROW = 5  # los datos empiezan en HEADER_ROW + 1

# ---- Paleta (consistente con las diapositivas: azul profesional + ámbar) ----
C_PRIMARY = "1F4E79"   # azul oscuro
C_ACCENT  = "E89B1E"   # ámbar
C_BLUE2   = "2E75B6"   # azul medio
C_LIGHT   = "DCE6F1"   # azul muy claro (relleno encabezados)
C_WHITE   = "FFFFFF"

THIN = Side(style="thin", color="B7C6DD")
BORDER = Border(left=THIN, right=THIN, top=THIN, bottom=THIN)


# ---------------------------------------------------------------------------
def _secs(v):
    if v is None:
        return None
    m = re.search(r"Segundos:\s*([\d.]+)", str(v))
    return float(m.group(1)) if m else None


def _fval(v):
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


def extraer(wb) -> dict:
    """Devuelve resumen[N][(k,algo)] = {'n','timeout','phi_mean','phi_med','t_mean','t_med'}."""
    resumen: dict = {}
    for hoja, n in HOJAS:
        ws = wb[hoja]
        resumen[n] = {}
        for (k, algo), (cp, ct) in GRUPOS.items():
            phis, times, to = [], [], 0
            for r in range(HEADER_ROW + 1, ws.max_row + 1):
                raw = ws.cell(r, cp).value
                if raw is None or str(raw).strip() == "":
                    continue
                if str(raw).strip().upper() == "TIMEOUT":
                    to += 1
                    continue
                f = _fval(raw)
                s = _secs(ws.cell(r, ct).value)
                if f is not None:
                    phis.append(f)
                if s is not None:
                    times.append(s)
            resumen[n][(k, algo)] = {
                "n": len(phis),
                "timeout": to,
                "phi_mean": st.mean(phis) if phis else None,
                "phi_med":  st.median(phis) if phis else None,
                "t_mean":   st.mean(times) if times else None,
                "t_med":    st.median(times) if times else None,
            }
    return resumen


# ---------------------------------------------------------------------------
# Helpers de formato de celdas
# ---------------------------------------------------------------------------
def _title(ws, cell, text, size=14, color=C_PRIMARY, fill=None):
    c = ws[cell]
    c.value = text
    c.font = Font(bold=True, size=size, color=color)
    if fill:
        c.fill = PatternFill("solid", fgColor=fill)


def _hdr(ws, row, col, text):
    c = ws.cell(row, col, text)
    c.font = Font(bold=True, color=C_WHITE, size=10)
    c.fill = PatternFill("solid", fgColor=C_PRIMARY)
    c.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
    c.border = BORDER
    return c


def _cell(ws, row, col, val, *, num="0.0000", bold=False, fill=None):
    c = ws.cell(row, col, val)
    c.border = BORDER
    c.alignment = Alignment(horizontal="center", vertical="center")
    if isinstance(val, (int, float)):
        c.number_format = num
    if bold:
        c.font = Font(bold=True, color=C_PRIMARY)
    if fill:
        c.fill = PatternFill("solid", fgColor=fill)
    return c


# ---------------------------------------------------------------------------
def construir_hoja(wb, resumen):
    if SHEET_OUT in wb.sheetnames:
        del wb[SHEET_OUT]
    ws = wb.create_sheet(SHEET_OUT)
    ws.sheet_view.showGridLines = False
    ws.column_dimensions["A"].width = 18
    for col in "BCDEF":
        ws.column_dimensions[col].width = 13

    _title(ws, "A1", "ANÁLISIS DE RESULTADOS — 10, 15 y 20 ELEMENTOS", size=16)
    ws["A2"] = ("Comparación KQNodes (familia QNodes) vs GeoMIP (Geometric) para "
                "k = 2..5 particiones. φ = pérdida de información mínima; "
                "tiempos en segundos (promedio sobre los casos de prueba).")
    ws["A2"].font = Font(italic=True, size=9, color="555555")
    ws["A2"].alignment = Alignment(wrap_text=True)
    ws.merge_cells("A2:F2")
    ws.row_dimensions[2].height = 30

    Ns = [n for _, n in HOJAS]

    # ===================== TABLA 1: φ KQNodes por k =====================
    r0 = 4
    _title(ws, f"A{r0}", "1) φ promedio — KQNodes por número de particiones (k)", size=12)
    hr = r0 + 1
    _hdr(ws, hr, 1, "N \\ k")
    for j, k in enumerate(["k=2", "k=3", "k=4", "k=5"]):
        _hdr(ws, hr, 2 + j, k)
    for i, n in enumerate(Ns):
        rr = hr + 1 + i
        _cell(ws, rr, 1, f"N={n}", bold=True, fill=C_LIGHT)
        for j, k in enumerate(["k2", "k3", "k4", "k5"]):
            v = resumen[n][(k, "QNodes")]["phi_mean"]
            _cell(ws, rr, 2 + j, round(v, 4) if v is not None else "—")
    t1_last = hr + len(Ns)

    # Chart 1: φ por k (series = N)
    ch1 = BarChart()
    ch1.type = "col"
    ch1.title = "φ promedio vs k (KQNodes)"
    ch1.y_axis.title = "φ (pérdida)"
    ch1.x_axis.title = "número de particiones k"
    ch1.height, ch1.width = 7.5, 13
    data = Reference(ws, min_col=1, min_row=hr + 1, max_col=5, max_row=t1_last)
    ch1.add_data(data, titles_from_data=True, from_rows=True)
    cats = Reference(ws, min_col=2, min_row=hr, max_col=5, max_row=hr)
    ch1.set_categories(cats)
    ws.add_chart(ch1, "H4")

    # ===================== TABLA 2: φ k=2 QNodes vs Geometric =====================
    r0 = t1_last + 3
    _title(ws, f"A{r0}", "2) φ promedio en k=2 — QNodes vs Geometric (consistencia)", size=12)
    hr = r0 + 1
    _hdr(ws, hr, 1, "N")
    _hdr(ws, hr, 2, "QNodes")
    _hdr(ws, hr, 3, "Geometric")
    for i, n in enumerate(Ns):
        rr = hr + 1 + i
        _cell(ws, rr, 1, f"N={n}", bold=True, fill=C_LIGHT)
        for j, algo in enumerate(["QNodes", "Geometric"]):
            v = resumen[n][("k2", algo)]["phi_mean"]
            _cell(ws, rr, 2 + j, round(v, 4) if v is not None else "—")
    t2_last = hr + len(Ns)

    ch2 = BarChart()
    ch2.type = "col"
    ch2.title = "φ k=2: QNodes vs Geometric"
    ch2.y_axis.title = "φ (pérdida)"
    ch2.x_axis.title = "N (elementos)"
    ch2.height, ch2.width = 7.5, 13
    data = Reference(ws, min_col=2, min_row=hr, max_col=3, max_row=t2_last)
    ch2.add_data(data, titles_from_data=True, from_rows=False)
    cats = Reference(ws, min_col=1, min_row=hr + 1, max_col=1, max_row=t2_last)
    ch2.set_categories(cats)
    ws.add_chart(ch2, "H19")

    # ===================== TABLA 3: Tiempo k=2 QNodes vs Geometric =====================
    r0 = t2_last + 3
    _title(ws, f"A{r0}", "3) Tiempo promedio en k=2 (s) — escalabilidad por N", size=12)
    hr = r0 + 1
    _hdr(ws, hr, 1, "N")
    _hdr(ws, hr, 2, "QNodes")
    _hdr(ws, hr, 3, "Geometric")
    for i, n in enumerate(Ns):
        rr = hr + 1 + i
        _cell(ws, rr, 1, f"N={n}", bold=True, fill=C_LIGHT)
        for j, algo in enumerate(["QNodes", "Geometric"]):
            v = resumen[n][("k2", algo)]["t_mean"]
            _cell(ws, rr, 2 + j, round(v, 3) if v is not None else "—", num="0.000")
    t3_last = hr + len(Ns)

    ch3 = BarChart()
    ch3.type = "col"
    ch3.title = "Tiempo k=2 vs N (escalabilidad)"
    ch3.y_axis.title = "segundos (promedio)"
    ch3.x_axis.title = "N (elementos)"
    ch3.height, ch3.width = 7.5, 13
    data = Reference(ws, min_col=2, min_row=hr, max_col=3, max_row=t3_last)
    ch3.add_data(data, titles_from_data=True, from_rows=False)
    cats = Reference(ws, min_col=1, min_row=hr + 1, max_col=1, max_row=t3_last)
    ch3.set_categories(cats)
    ws.add_chart(ch3, "H34")

    # ===================== TABLA 4: Tiempo KQNodes por k =====================
    r0 = t3_last + 3
    _title(ws, f"A{r0}", "4) Tiempo promedio (s) — KQNodes por k", size=12)
    hr = r0 + 1
    _hdr(ws, hr, 1, "N \\ k")
    for j, k in enumerate(["k=2", "k=3", "k=4", "k=5"]):
        _hdr(ws, hr, 2 + j, k)
    for i, n in enumerate(Ns):
        rr = hr + 1 + i
        _cell(ws, rr, 1, f"N={n}", bold=True, fill=C_LIGHT)
        for j, k in enumerate(["k2", "k3", "k4", "k5"]):
            v = resumen[n][(k, "QNodes")]["t_mean"]
            _cell(ws, rr, 2 + j, round(v, 3) if v is not None else "—", num="0.000")
    t4_last = hr + len(Ns)

    ch4 = LineChart()
    ch4.title = "Tiempo vs k (KQNodes)"
    ch4.y_axis.title = "segundos (promedio)"
    ch4.x_axis.title = "número de particiones k"
    ch4.height, ch4.width = 7.5, 13
    data = Reference(ws, min_col=1, min_row=hr + 1, max_col=5, max_row=t4_last)
    ch4.add_data(data, titles_from_data=True, from_rows=True)
    cats = Reference(ws, min_col=2, min_row=hr, max_col=5, max_row=hr)
    ch4.set_categories(cats)
    for s in ch4.series:
        s.smooth = False
    ws.add_chart(ch4, "H49")

    return ws, t4_last


def escribir_interpretacion(ws, resumen, fila_inicio):
    r = fila_inicio + 3
    _title(ws, f"A{r}", "INTERPRETACIÓN DE RESULTADOS", size=14)
    r += 1

    def bloque(titulo, parrafos):
        nonlocal r
        c = ws.cell(r, 1, titulo)
        c.font = Font(bold=True, size=11, color=C_PRIMARY)
        r += 1
        for p in parrafos:
            cc = ws.cell(r, 1, p)
            cc.alignment = Alignment(wrap_text=True, vertical="top")
            cc.font = Font(size=10)
            ws.merge_cells(start_row=r, start_column=1, end_row=r, end_column=6)
            ws.row_dimensions[r].height = max(15, 15 * (1 + len(p) // 95))
            r += 1
        r += 1

    # Cálculos para el texto
    g = lambda n, k, a, key: resumen[n][(k, a)][key]
    sp20 = (g(20, "k2", "Geometric", "t_mean") / g(20, "k2", "QNodes", "t_mean")
            if g(20, "k2", "QNodes", "t_mean") else float("nan"))
    salto = (g(20, "k2", "QNodes", "t_mean") / g(15, "k2", "QNodes", "t_mean")
             if g(15, "k2", "QNodes", "t_mean") else float("nan"))

    bloque("1. La pérdida φ crece de forma monótona con k.", [
        "En las tres redes, al exigir más particiones (k mayor) la pérdida de información φ "
        "aumenta: cada corte adicional rompe más dependencias del sistema, por lo que una "
        "k-partición nunca puede perder menos que la mejor bipartición. "
        f"Ej. N=20: φ pasa de {g(20,'k2','QNodes','phi_mean'):.4f} (k=2) a "
        f"{g(20,'k5','QNodes','phi_mean'):.4f} (k=5). Esto valida que k es un parámetro de "
        "granularidad: más partes ⇒ más información sacrificada.",
    ])

    bloque("2. QNodes y Geometric coinciden en k=2 (validación cruzada).", [
        "Para la bipartición (k=2) ambos algoritmos resuelven el mismo problema (MIP), y sus "
        "valores de φ son prácticamente iguales en las tres redes "
        f"(N=10: {g(10,'k2','QNodes','phi_mean'):.4f} vs {g(10,'k2','Geometric','phi_mean'):.4f}; "
        f"N=15: {g(15,'k2','QNodes','phi_mean'):.4f} vs {g(15,'k2','Geometric','phi_mean'):.4f}; "
        f"N=20: {g(20,'k2','QNodes','phi_mean'):.4f} vs {g(20,'k2','Geometric','phi_mean'):.4f}). "
        "Geometric tiende a encontrar un φ ligeramente menor o igual, lo que confirma que ambas "
        "implementaciones hallan la misma partición de mínima información.",
    ])

    bloque("3. El tiempo explota con N (coste exponencial).", [
        "El número de elementos domina el costo: para k=2 (QNodes) el tiempo promedio salta de "
        f"~{g(10,'k2','QNodes','t_mean'):.2f}s (N=10) y ~{g(15,'k2','QNodes','t_mean'):.2f}s (N=15) "
        f"a ~{g(20,'k2','QNodes','t_mean'):.1f}s (N=20): un factor de ~{salto:.0f}× al pasar de 15 a "
        "20 elementos. Esto refleja el crecimiento exponencial del espacio de estados (2^N) y "
        "marca el límite práctico de los métodos exactos en este hardware.",
    ])

    bloque("4. QNodes vs Geometric en tiempo: depende de la red.", [
        "No hay un ganador único en velocidad. En N=10 Geometric es más rápido, pero en N=15 y "
        f"N=20 QNodes resulta más eficiente (N=20: QNodes ~{g(20,'k2','QNodes','t_mean'):.0f}s vs "
        f"Geometric ~{g(20,'k2','Geometric','t_mean'):.0f}s, es decir Geometric tarda ~{sp20:.1f}× más). "
        "El método geométrico (programación dinámica) paga un sobrecosto que solo compensa en "
        "redes pequeñas o con cierta estructura.",
    ])

    bloque("5. KQNodes (k≥3) es competitivo en tiempo.", [
        "En N=20, las particiones k=3..5 de KQNodes se resuelven en ~134–154s, por debajo de los "
        "~235s de la bipartición exhaustiva QNodes. La minimización submodular de Queyranne más el "
        "refinamiento divisivo escala mejor que explorar todas las biparticiones, a costa de ser "
        "heurístico. Se registró 1 timeout (k=4, N=20), señal de que cerca del límite algunos "
        "casos superan la cota de 1 hora.",
    ])

    bloque("6. La magnitud de φ depende de la estructura de cada red.", [
        "Los φ no son comparables entre redes distintas: N=15 (red B) es casi reducible "
        f"(φ≈{g(15,'k2','QNodes','phi_mean'):.4f}, sin información integrada relevante), mientras que "
        f"N=10 (red A) muestra φ altos en k≥3 (hasta ~{g(10,'k5','QNodes','phi_mean'):.2f}). Esto "
        "describe la red, no el algoritmo: φ mide cuánta integración real tiene cada sistema.",
    ])


def main():
    wb_vals = openpyxl.load_workbook(EXCEL_PATH, data_only=True)
    resumen = extraer(wb_vals)
    wb_vals.close()

    wb = openpyxl.load_workbook(EXCEL_PATH, data_only=False)  # preserva fórmulas
    ws, last = construir_hoja(wb, resumen)
    escribir_interpretacion(ws, resumen, last)
    wb.save(EXCEL_PATH)
    print(f"OK — hoja '{SHEET_OUT}' creada/actualizada en {EXCEL_PATH.name}")
    print("Tablas: φ por k | φ k=2 QN vs Geo | tiempo k=2 | tiempo por k. 4 gráficos + interpretación.")


if __name__ == "__main__":
    main()
