import pkgutil
import inspect
import glob
import re
import sys
from os.path import (
    join,
    dirname
)

# Deal with it.
modules = glob.glob(join(dirname(__file__), '*'))
modules = [i if re.findall(r'^.+$(?<!\.py)', i) else None for i in modules]
modules = [i for i in modules if i]
for _loader, _module_name, _ in pkgutil.walk_packages(path=modules):
    _module = _loader.find_module(_module_name).load_module(_module_name)
    fromlist = []
    for name, obj in inspect.getmembers(sys.modules[_module_name]):
        if inspect.isclass(obj):
            print('Import', obj.__name__)
            globals()[obj.__name__] = obj
