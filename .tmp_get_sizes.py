import os
p20='QNodes/src/.samples/N20A.csv'
p22='QNodes/src/.samples/N22A.csv'
print('N20 size bytes:', os.path.getsize(p20) if os.path.exists(p20) else 'missing')
print('N22 size bytes:', os.path.getsize(p22) if os.path.exists(p22) else 'missing')
