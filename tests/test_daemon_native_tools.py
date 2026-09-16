from __future__ import annotations
import sys
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'baseline'/'pcmmad_receiver'))

def test_daemon_native_tools_are_registered_read_only():
    import lab_tools
    for name in ('daemon.health','daemon.status','daemon.events'):
        spec=lab_tools._TOOL_REGISTRY[name]
        assert spec.category=='daemon'
        assert spec.danger_tier=='low'
        assert spec.mutating is False
        assert spec.side_effect_class=='read'
        assert 'does_not_grant_mutation_authority' in spec.effect_traits
