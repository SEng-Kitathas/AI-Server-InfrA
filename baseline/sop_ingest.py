"""Legacy import alias for :mod:`pcmmad_receiver.sop_ingest`."""
from importlib import import_module as _import_module
import sys as _sys
_module = _import_module("pcmmad_receiver.sop_ingest")
_sys.modules[__name__] = _module
