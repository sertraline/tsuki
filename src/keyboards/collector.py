import src.keyboards as keyboards
import pkgutil
from inspect import getmembers, isfunction


class KeyboardCollector:
    def __init__(self):
        for _loader, _module_name, _ in pkgutil.walk_packages(keyboards.__path__):
            _module = _loader.find_module(_module_name).load_module(_module_name)
            functions = getmembers(_module, isfunction)
            for f in functions:
                setattr(self, f[0], f[1])
