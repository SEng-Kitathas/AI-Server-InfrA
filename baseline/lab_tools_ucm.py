"""Legacy import alias for :mod:`pcmmad_receiver.lab_tools_ucm`."""
from importlib import import_module as _import_module
import sys as _sys
_module = _import_module("pcmmad_receiver.lab_tools_ucm")
_sys.modules[__name__] = _module
