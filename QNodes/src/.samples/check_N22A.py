import os
p='QNodes/src/.samples/N22A.csv'
print('EXISTS', os.path.exists(p))
if os.path.exists(p):
    print('SIZE', os.path.getsize(p))
    with open(p,'r', encoding='utf-8', errors='ignore') as f:
        first = f.readline().strip()
        print('COLS', len(first.split(',')))
    count = 0
    with open(p,'rb') as f:
        for chunk in iter(lambda: f.read(1<<20), b''):
            count += chunk.count(b'\n')
    print('LINES', count)
