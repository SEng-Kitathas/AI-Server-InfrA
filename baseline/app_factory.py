"""Legacy import alias for :mod:`pcmmad_receiver.app_factory`."""
from importlib import import_module as _import_module
import sys as _sys
_module = _import_module("pcmmad_receiver.app_factory")
_sys.modules[__name__] = _module
