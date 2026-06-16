from pathlib import Path
import sys

repo_root = Path(__file__).resolve().parents[0]
# Insert parent folders so that 'src' packages inside them are importable as 'src'
# Prefer QNodes parent first so shared packages (models, constants, funcs) are found there
sys.path.insert(0, str(repo_root / "QNodes"))
sys.path.insert(1, str(repo_root / "KQNodes"))
print('sys.path[0:5]=', sys.path[0:5])
from pathlib import Path as _P
print('QNodes/src exists=', (_P(repo_root) / 'QNodes' / 'src').exists())
print('KQNodes/src exists=', (_P(repo_root) / 'KQNodes' / 'src').exists())

# Load Manager directly from file to avoid package-name conflicts
from importlib.util import spec_from_file_location, module_from_spec

mgr_path = repo_root / 'QNodes' / 'src' / 'controllers' / 'manager.py'
spec = spec_from_file_location('q_manager', str(mgr_path))
mod_mgr = module_from_spec(spec)
spec.loader.exec_module(mod_mgr)
Manager = getattr(mod_mgr, 'Manager')

# Load KQNodes strategy module from file (it contains its own sys.path hack)
kq_path = repo_root / 'KQNodes' / 'src' / 'strategies' / 'kqnodes.py'
spec2 = spec_from_file_location('kqnodes_mod', str(kq_path))
kq_mod = module_from_spec(spec2)
spec2.loader.exec_module(kq_mod)
KQNodes = getattr(kq_mod, 'KQNodes')

if __name__ == '__main__':
    estado = '1000'
    sample_path = repo_root / 'QNodes' / 'src' / '.samples'
    gestor = Manager(estado, ruta_base=sample_path)
    kq = KQNodes(gestor, k=3, refinar=False, verbose=True)
    resultado = kq.aplicar_estrategia()
    print(resultado)
