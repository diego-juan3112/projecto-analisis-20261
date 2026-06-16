import zipfile
import xml.etree.ElementTree as ET
from collections import defaultdict

p='GeoMIP/results/resultados_Geometric.xlsx'
with zipfile.ZipFile(p) as z:
    # load shared strings
    strings = []
    if 'xl/sharedStrings.xml' in z.namelist():
        root = ET.fromstring(z.read('xl/sharedStrings.xml'))
        for si in root.findall('.//{http://schemas.openxmlformats.org/spreadsheetml/2006/main}t'):
            strings.append(si.text)
    # find first sheet
    sheets = [n for n in z.namelist() if n.startswith('xl/worksheets/sheet')]
    if not sheets:
        print('No sheets')
        raise SystemExit(1)
    sheet = sheets[0]
    data = []
    root = ET.fromstring(z.read(sheet))
    ns='{http://schemas.openxmlformats.org/spreadsheetml/2006/main}'
    for row in root.findall('.//%srow' % ns):
        row_vals = {}
        for c in row.findall('%sc' % ns):
            r = c.attrib.get('r')
            t = c.attrib.get('t')
            v = c.find('%sv' % ns)
            if v is None:
                continue
            if t == 's':
                val = strings[int(v.text)] if v.text and v.text.isdigit() else v.text
            else:
                val = v.text
            row_vals[r] = val
        data.append(row_vals)
    # print header (first row) mapping col letters to names
    if not data:
        print('empty')
    else:
        header = data[0]
        # map column letter
        def col_letter(cell_ref):
            import re
            return re.sub(r"[0-9]+","",cell_ref)
        hdr = {}
        for ref, val in header.items():
            hdr[col_letter(ref)] = val
        print('HEADER', hdr)
        # find columns for Alcance and Mecanismo
        col_let = {v:k for k,v in hdr.items()}
        for key in ('Alcance','Mecanismo'):
            print(key, '->', col_let.get(key))
        # sample few rows for those columns
        rows_sample = []
        for i, row in enumerate(data[1:1+20], start=2):
            row_map = {}
            for ref,val in row.items():
                row_map[col_letter(ref)] = val
            rows_sample.append(row_map)
        print('SAMPLES (first 10 rows):')
        for r in rows_sample[:10]:
            a = r.get(col_let.get('Alcance'))
            m = r.get(col_let.get('Mecanismo'))
            print(a, '|', m)
