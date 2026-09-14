from __future__ import annotations
import sys,tempfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'baseline'));from pcmmad_receiver.project_provisioning import plan,verify_isolation;from pcmmad_receiver.advisory_evidence import gather
def test_project_plan_confined_under_projects_root():
 with tempfile.TemporaryDirectory() as td:
  r=plan(project_id='veya-shard',projects_root=Path(td),source_epoch='abc');assert r['ok'] and Path(r['root']).parent==Path(td).resolve() and r['initial_generation']==0 and not r['writes']
def test_project_id_cannot_smuggle_path():
 with tempfile.TemporaryDirectory() as td:assert not plan(project_id='../escape',projects_root=Path(td))['ok']
def test_existing_project_not_overwritten():
 with tempfile.TemporaryDirectory() as td:
  (Path(td)/'P').mkdir();assert plan(project_id='P',projects_root=Path(td))['status']=='ALREADY_EXISTS'
def test_two_plans_are_independent():
 with tempfile.TemporaryDirectory() as td:assert verify_isolation(plan(project_id='A',projects_root=Path(td)),plan(project_id='B',projects_root=Path(td)))['isolated']
def test_evidence_gatherer_reads_only_known_rollover_surfaces():
 with tempfile.TemporaryDirectory() as td:
  r=Path(td);(r/'LIVE_SHADOW.md').write_text('mutation lease redaction scar');(r/'SECRET.txt').write_text('mutation secret should not be searched');g=gather(handoff_root=r,issue='mutation lease');assert any(x['matches'] for x in g['observations']);assert all(x['surface']!='SECRET.txt' for x in g['observations']);assert g['authority']=='NONE' and not g['may_mutate']
def test_missing_rollover_surface_explicit():
 with tempfile.TemporaryDirectory() as td:assert 'TRACE_MATRIX.md' in gather(handoff_root=Path(td),issue='anything')['missing']
