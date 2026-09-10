"""Legacy import alias for :mod:`pcmmad_receiver.context_routes`."""
from importlib import import_module as _import_module
import sys as _sys
_module = _import_module("pcmmad_receiver.context_routes")
_sys.modules[__name__] = _module
