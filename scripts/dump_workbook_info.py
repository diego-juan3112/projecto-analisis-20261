import zipfile
from xml.etree import ElementTree as ET
p='GeoMIP/results/resultados_Geometric.xlsx'
with zipfile.ZipFile(p) as z:
    files = [n for n in z.namelist() if n.startswith('xl/')]
    print('files count', len(files))
    for n in files:
        print(n)
    wb=ET.fromstring(z.read('xl/workbook.xml'))
    ns='{http://schemas.openxmlformats.org/spreadsheetml/2006/main}'
    for s in wb.findall('.//%ssheet' % ns):
        print('sheet name attrib:', s.attrib)
    if 'xl/_rels/workbook.xml.rels' in z.namelist():
        rels=ET.fromstring(z.read('xl/_rels/workbook.xml.rels'))
        for r in rels.findall('.//{http://schemas.openxmlformats.org/package/2006/relationships}Relationship'):
            print('rel', r.attrib)
