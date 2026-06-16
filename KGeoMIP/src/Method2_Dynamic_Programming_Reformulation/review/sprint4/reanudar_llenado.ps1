# Respaldo nocturno: reanuda el llenado del Excel de entrega donde haya quedado.
# Es un no-op si todas las celdas ya estan ocupadas. Limpia un lock huerfano si existe.
$env:PYTHONIOENCODING = 'utf-8'
Set-Location 'c:\uCaldasTasks\projecto-analisis-20261\GeoMIP\src\Method2_Dynamic_Programming_Reformulation'
# Si un llenado sigue vivo, NO tocar su lock ni lanzar un segundo escritor.
$vivo = Get-CimInstance Win32_Process -ErrorAction SilentlyContinue |
    Where-Object { $_.CommandLine -match 'llenar_excel' }
if ($vivo) { exit 0 }
Remove-Item 'c:\uCaldasTasks\projecto-analisis-20261\DatosPruebas2026_1.xlsx.lock' -Force -ErrorAction SilentlyContinue
foreach ($h in '10A', '15B', '20A', '22A', '25A') {
    uv run python llenar_excel.py --hoja $h --k 2,3,4,5 --timeout 1500 *>> review\sprint4\llenado_respaldo.log
}
