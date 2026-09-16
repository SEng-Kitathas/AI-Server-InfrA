# PCMMAD Receiver V27.1 Hotfix Report

## Incident
User reported server startup failure:

- `NameError: name 'ENABLED_SOURCES' is not defined`
- import path: `legacy_routes -> lab_tools`

## Root cause
`lab_tools.py` referenced:
- `ENABLED_SOURCES`
- `ENABLED_HUNT_MODES`
- `PARSER_VERSION`

but did not import them after prior module decomposition.

## Fix
Added:

```python
from research_config import ENABLED_HUNT_MODES, ENABLED_SOURCES, PARSER_VERSION
```

to `lab_tools.py`.

## Scope
This is a targeted startup hotfix, not a broad new refactor pass.

## Verification
- local static source inspection confirms the missing names are now imported
- package rebuilt without stale `__pycache__`
- note: full live-host import proof still requires loading the package on the target host where Flask/runtime deps exist
