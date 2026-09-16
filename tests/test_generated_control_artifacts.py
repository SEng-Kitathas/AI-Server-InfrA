from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[1]
BASE=ROOT/"baseline"/"pcmmad_receiver"
if str(BASE) not in sys.path: sys.path.insert(0,str(BASE))
import generated_control_artifacts as g

def test_checked_scheduler_effect_profile_matches_current_catalog():
    assert g.scheduler_effect_profile_is_current(), "run scripts/refresh_generated_control_artifacts.py --write"
