"""Volcar resultados de GeoMIP a hoja de pruebas destino.

Uso:
  python KQNodes/scripts/volcar_geomip.py --hoja '10A-Elementos'

Entrada esperada:
  - GeoMIP/results/resultados_Geometric.xlsx
  - docs/DatosPruebas2026_1.xlsx

Para cada fila en resultados_Geometric: convierte `Alcance` y `Mecanismo`
de binario a letras y busca la fila en la hoja destino donde columna B
coincida con Alcance y columna C con Mecanismo. Si encuentra match, escribe
en G,H,I la Partición, Pérdida y Tiempo formateado.
"""
from __future__ import annotations
import argparse
import re
from pathlib import Path
from typing import List, Optional, Tuple

try:
    from openpyxl import load_workbook
except Exception as e:
    raise SystemExit("openpyxl is required: pip install openpyxl")

ABECEDARY = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"


def bin_to_letters(bin_str: str) -> List[str]:
    """Return several textual variants for the letters indicated by bin_str.

    Variants returned (in order):
      - concatenated letters e.g. 'ABC'
      - comma-separated 'A,B,C'
      - comma+space 'A, B, C'
    """
    if bin_str is None:
        return ["", "", ""]
    s = str(bin_str).strip()
    letters = [ABECEDARY[i] for i, ch in enumerate(s) if ch == "1"]
    joined = "".join(letters)
    commas = ",".join(letters)
    commas_sp = ", ".join(letters)
    return [joined, commas, commas_sp]


def normalize_for_compare(s: Optional[str]) -> str:
    if s is None:
        return ""
    s = str(s).strip()
    # remove surrounding pipes, whitespace, and normalize commas/spaces
    s = s.replace("|", "")
    s = s.replace("\u2217", "")
    s = s.replace("∅", "")
    s = s.replace(" ", "")
    s = s.replace(",", "")
    return s.upper()


def parse_float_from_str(s: Optional[str]) -> Optional[float]:
    if s is None:
        return None
    t = str(s).strip()
    # replace comma decimal with dot
    t = t.replace(" ", "")
    t = t.replace(",", ".")
    try:
        return float(t)
    except Exception:
        # try to extract a number with regex
        m = re.search(r"[-+]?[0-9]*\.?[0-9]+", t)
        if m:
            return float(m.group(0))
    return None


def find_header_row(ws) -> int:
    """Try to locate header row by searching for 'Alcance' and 'Mecanismo' cells."""
    for r in range(1, min(15, ws.max_row) + 1):
        vals = [str((ws.cell(row=r, column=c).value or "")).strip() for c in range(1, min(30, ws.max_column) + 1)]
        joined = "|".join(vals)
        if "ALCANCE" in joined.upper() and "MECANISMO" in joined.upper():
            return r
    # fallback to first row
    return 1


def load_result_rows(result_path: Path) -> List[dict]:
    wb = load_workbook(result_path, data_only=True)
    # try to find sheet that contains Alcance/Mecanismo
    ws_target = None
    for name in wb.sheetnames:
        ws = wb[name]
        header_row = find_header_row(ws)
        hdr_vals = [str((ws.cell(row=header_row, column=c).value or "")).strip().upper() for c in range(1, ws.max_column + 1)]
        if "ALCANCE" in "|".join(hdr_vals) and "MECANISMO" in "|".join(hdr_vals):
            ws_target = ws
            break
    if ws_target is None:
        # default to first sheet
        ws_target = wb[wb.sheetnames[0]]
        header_row = find_header_row(ws_target)
    else:
        header_row = find_header_row(ws_target)

    # build index mapping header name -> column
    header_map = {}
    for c in range(1, ws_target.max_column + 1):
        val = ws_target.cell(row=header_row, column=c).value
        if val is None:
            continue
        header_map[str(val).strip().upper()] = c

    # expected columns
    col_alc = header_map.get("ALCANCE")
    col_mec = header_map.get("MECANISMO")
    col_part = header_map.get("PARTICIÓN") or header_map.get("PARTICION")
    col_perd = header_map.get("PÉRDIDA") or header_map.get("PERDIDA")
    col_time = header_map.get("TIEMPO(S)") or header_map.get("TIEMPO") or header_map.get("TIEMPO DE EJECUCIÓN (S)")

    rows = []
    for r in range(header_row + 1, ws_target.max_row + 1):
        alc = ws_target.cell(row=r, column=col_alc).value if col_alc else None
        mec = ws_target.cell(row=r, column=col_mec).value if col_mec else None
        part = ws_target.cell(row=r, column=col_part).value if col_part else None
        perd = ws_target.cell(row=r, column=col_perd).value if col_perd else None
        tiempo = ws_target.cell(row=r, column=col_time).value if col_time else None
        rows.append({"row": r, "Alcance": alc, "Mecanismo": mec, "Particion": part, "Perdida": perd, "Tiempo": tiempo})
    return rows


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--hoja", required=True, help="Nombre de la hoja destino en docs/DatosPruebas2026_1.xlsx")
    args = p.parse_args()

    base = Path.cwd()
    resultados_path = base / "GeoMIP" / "results" / "resultados_Geometric.xlsx"
    pruebas_path = base / "docs" / "DatosPruebas2026_1.xlsx"

    if not resultados_path.exists():
        raise SystemExit(f"No existe {resultados_path}")
    if not pruebas_path.exists():
        raise SystemExit(f"No existe {pruebas_path}")

    # load resultados
    wb_res = load_workbook(resultados_path, data_only=True)
    # choose sheet that contains Alcance/Mecanismo
    ws_res = None
    for name in wb_res.sheetnames:
        ws = wb_res[name]
        hdr = find_header_row(ws)
        vals = [str((ws.cell(row=hdr, column=c).value or "")).strip().upper() for c in range(1, ws.max_column + 1)]
        if "ALCANCE" in "|".join(vals) and "MECANISMO" in "|".join(vals):
            ws_res = ws
            header_row_res = hdr
            break
    if ws_res is None:
        ws_res = wb_res[wb_res.sheetnames[0]]
        header_row_res = find_header_row(ws_res)

    # map columns in resultados
    hdr_map_res = {}
    for c in range(1, ws_res.max_column + 1):
        v = ws_res.cell(row=header_row_res, column=c).value
        if v is None:
            continue
        hdr_map_res[str(v).strip().upper()] = c

    col_alc_res = hdr_map_res.get("ALCANCE")
    col_mec_res = hdr_map_res.get("MECANISMO")
    col_part_res = hdr_map_res.get("PARTICIÓN") or hdr_map_res.get("PARTICION")
    col_perd_res = hdr_map_res.get("PÉRDIDA") or hdr_map_res.get("PERDIDA")
    col_time_res = hdr_map_res.get("TIEMPO(S)") or hdr_map_res.get("TIEMPO") or hdr_map_res.get("TIEMPO DE EJECUCIÓN (S)")

    if not (col_alc_res and col_mec_res):
        raise SystemExit("No pude identificar columnas 'Alcance' y 'Mecanismo' en resultados_Geometric.xlsx")

    # load pruebas workbook and destination sheet
    wb_pr = load_workbook(pruebas_path)
    if args.hoja not in wb_pr.sheetnames:
        raise SystemExit(f"La hoja '{args.hoja}' no existe en {pruebas_path}")
    ws_dest = wb_pr[args.hoja]

    # Build a lookup of destination rows by normalized (B,C)
    dest_map = {}
    for r in range(1, ws_dest.max_row + 1):
        val_b = ws_dest.cell(row=r, column=2).value
        val_c = ws_dest.cell(row=r, column=3).value
        key = (normalize_for_compare(val_b), normalize_for_compare(val_c))
        # store first occurrence only
        if key not in dest_map:
            dest_map[key] = r

    matched = 0
    not_found = 0

    # iterate resultados rows
    for r in range(header_row_res + 1, ws_res.max_row + 1):
        alc_bin = ws_res.cell(row=r, column=col_alc_res).value
        mec_bin = ws_res.cell(row=r, column=col_mec_res).value
        part = ws_res.cell(row=r, column=col_part_res).value if col_part_res else None
        perd = ws_res.cell(row=r, column=col_perd_res).value if col_perd_res else None
        tiempo = ws_res.cell(row=r, column=col_time_res).value if col_time_res else None

        # convert
        alc_variants = bin_to_letters(alc_bin)
        mec_variants = bin_to_letters(mec_bin)

        found_row = None
        for a in alc_variants:
            for m in mec_variants:
                key = (normalize_for_compare(a), normalize_for_compare(m))
                if key in dest_map:
                    found_row = dest_map[key]
                    break
            if found_row:
                break

        if not found_row:
            not_found += 1
            continue

        # write into dest: cols G(7), H(8), I(9)
        # Partición as-is
        ws_dest.cell(row=found_row, column=7).value = part
        # Pérdida: try to parse to float then write dot-decimal string
        fperd = parse_float_from_str(perd)
        ws_dest.cell(row=found_row, column=8).value = fperd
        # Tiempo: format as 'Segundos: {tiempo:.4f}'
        ftime = parse_float_from_str(tiempo)
        if ftime is not None:
            ws_dest.cell(row=found_row, column=9).value = f"Segundos: {ftime:.4f}"
        else:
            ws_dest.cell(row=found_row, column=9).value = None

        matched += 1

    wb_pr.save(pruebas_path)

    print(f"Filas emparejadas: {matched}")
    print(f"Filas sin match: {not_found}")


if __name__ == "__main__":
    main()
