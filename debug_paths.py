from pathlib import Path
p = Path('KQNodes/src/main.py').resolve().parents[2]
print('repo_root=', p)
print('QNodes/src exists=', (p / 'QNodes' / 'src').exists())
print('KQNodes/src exists=', (p / 'KQNodes' / 'src').exists())
print('QNodes/src listing:')
for child in sorted((p / 'QNodes' / 'src').iterdir()):
    print(' -', child.name)
