from openpyxl import load_workbook

res_path='GeoMIP/results/resultados_Geometric.xlsx'
pr_path='docs/DatosPruebas2026_1.xlsx'
print('res_path', res_path)
print('pr_path', pr_path)

wb_res = load_workbook(res_path, data_only=True)
# find sheet with Alcance/Mecanismo
ws_res = None
for name in wb_res.sheetnames:
    ws = wb_res[name]
    for r in range(1,6):
        rowvals = [str((ws.cell(row=r, column=c).value or '')).upper() for c in range(1,20)]
        if any('ALCANCE' in v for v in rowvals) and any('MECANISMO' in v for v in rowvals):
            hdr=r
            ws_res=ws
            break
    if ws_res: break
if not ws_res:
    ws_res = wb_res[wb_res.sheetnames[0]]
    hdr=1
print('Using resultados sheet:', ws_res.title, 'header_row=', hdr)
# find columns
col_map={}
for c in range(1, ws_res.max_column+1):
    v=ws_res.cell(row=hdr, column=c).value
    if v:
        col_map[str(v).strip().upper()] = c
print('Res header map sample keys:', list(col_map.keys())[:10])
col_alc = col_map.get('ALCANCE')
col_mec = col_map.get('MECANISMO')
print('col_alc, col_mec=', col_alc, col_mec)
print('\nFirst 10 resultado rows:')
for r in range(hdr+1, min(ws_res.max_row, hdr+10)+1):
    alc = ws_res.cell(row=r, column=col_alc).value if col_alc else None
    mec = ws_res.cell(row=r, column=col_mec).value if col_mec else None
    print(r, 'ALC=', repr(alc), 'MEC=', repr(mec))

wb_pr = load_workbook(pr_path)
if '10A-Elementos' in wb_pr.sheetnames:
    ws_pr = wb_pr['10A-Elementos']
else:
    ws_pr = wb_pr[wb_pr.sheetnames[0]]
print('\nUsing pruebas sheet:', ws_pr.title)
print('First 20 rows B and C:')
for r in range(1, min(21, ws_pr.max_row)+1):
    b = ws_pr.cell(row=r, column=2).value
    c = ws_pr.cell(row=r, column=3).value
    print(r, 'B=', repr(b), 'C=', repr(c))
