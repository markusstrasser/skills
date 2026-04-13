"""Importable wrapper around `session-shape.py`.

The CLI entrypoint stays hyphenated for compatibility with existing shell
invocations. This adapter gives tests and future code a stable module name.
"""

from __future__ import annotations

from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path
from types import ModuleType

_IMPL_PATH = Path(__file__).with_name("session-shape.py")
_SPEC = spec_from_file_location("observe_session_shape_impl", _IMPL_PATH)
assert _SPEC and _SPEC.loader
_IMPL = module_from_spec(_SPEC)
_SPEC.loader.exec_module(_IMPL)

for _name in dir(_IMPL):
    if _name.startswith("__"):
        continue
    _value = getattr(_IMPL, _name)
    if isinstance(_value, ModuleType):
        continue
    globals()[_name] = _value
