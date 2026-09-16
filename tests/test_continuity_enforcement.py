from __future__ import annotations
import hashlib,json,tempfile,subprocess,sys
from pathlib import Path
import pytest
from mvf_resident.continuity_enforcement import plan_surface_use,handoff_gate,rehydrate_packet,SURFACE_REGISTRY
from mvf_resident.surfaces import REQUIRED_ACTIVE_SURFACES

ROOT=Path(__file__).resolve().parents[1]
RUNTIME=ROOT/"baseline"/"pcmmad_receiver"
if str(RUNTIME) not in sys.path: sys.path.insert(0,str(RUNTIME))
from lab_tools_ops import _resolve_git_executable

def _git():
    executable,error=_resolve_git_executable()
    if executable is None or error is not None: raise RuntimeError(error or "GIT_EXECUTABLE_NOT_FOUND")
    return executable

def _handoff(root:Path):
    files={}
    for n in REQUIRED_ACTIVE_SURFACES:
        p=root/n;p.write_text(n,encoding='utf-8');b=p.read_bytes();files[n]={'bytes':len(b),'sha256':hashlib.sha256(b).hexdigest()}
    # campaign replication
    (root/'COMMANDERS_INTENT_CURRENT.md').write_text('Active parent campaign: GLOBAL INTERACTION WAR CAMPAIGN\ncommander intent authority',encoding='utf-8')
    (root/'LIVE_SHADOW.md').write_text('Parent: GLOBAL INTERACTION WAR CAMPAIGN\nlive receiver daemon ngrok',encoding='utf-8')
    (root/'CURRENT_STATE.md').write_text('Active parent campaign: GLOBAL INTERACTION WAR CAMPAIGN\ncurrent state uncommitted working tree',encoding='utf-8')
    for n in ('COMMANDERS_INTENT_CURRENT.md','LIVE_SHADOW.md','CURRENT_STATE.md'):
        b=(root/n).read_bytes();files[n]={'bytes':len(b),'sha256':hashlib.sha256(b).hexdigest()}
    cp=files['THREAD_CONTINUITY_CHECKPOINT_2026-09-15.md']['sha256']
    (root/'SNAPSHOT_MANIFEST_SHA256.json').write_text(json.dumps({'updated_at':'2026-09-15T00:00:00+00:00','continuity_checkpoint_sha256':cp,'files':files}),encoding='utf-8')

def test_recovery_plan_prioritizes_intent_live_state_and_avoids_ritual_dump():
    with tempfile.TemporaryDirectory() as td:
        h=Path(td);_handoff(h);p=plan_surface_use(h,'Receiver failure recovery and current campaign',mode='recovery',limit=5);names=[x['surface'] for x in p['selected']]
        assert 'COMMANDERS_INTENT_CURRENT.md' in names and 'LIVE_SHADOW.md' in names and 'CURRENT_STATE.md' in names
        assert p['ritual_dump_avoided'] is True and len(names)==5

def test_directly_relevant_low_priority_surface_can_outrank_generic_high_priority_surface():
    with tempfile.TemporaryDirectory() as td:
        h=Path(td);_handoff(h);p=plan_surface_use(h,'why architecture design history lineage decision',mode='discussion',limit=3);names=[x['surface'] for x in p['selected']]
        assert 'DESIGN_THREAD_STREAM.md' in names

def test_handoff_gate_blocks_stale_surface_and_campaign_conflict():
    with tempfile.TemporaryDirectory() as td:
        h=Path(td);_handoff(h);assert handoff_gate(h)['ready'] is True
        (h/'LIVE_SHADOW.md').write_text('Parent: DIFFERENT CAMPAIGN',encoding='utf-8')
        g=handoff_gate(h);assert g['ready'] is False;assert 'ACTIVE_SURFACES_NOT_CURRENT' in g['failures'];assert 'ACTIVE_CAMPAIGN_CONFLICT' in g['failures']

def test_uncommitted_repo_requires_handoff_declaration():
    with tempfile.TemporaryDirectory() as td:
        b=Path(td);h=b/'h';h.mkdir();_handoff(h);repo=b/'repo';repo.mkdir();subprocess.run([_git(),'init'],cwd=repo,capture_output=True,check=True);subprocess.run([_git(),'config','user.email','a@b.c'],cwd=repo,check=True);subprocess.run([_git(),'config','user.name','x'],cwd=repo,check=True);(repo/'x').write_text('1');subprocess.run([_git(),'add','.'],cwd=repo,check=True);subprocess.run([_git(),'commit','-m','x'],cwd=repo,capture_output=True,check=True);(repo/'x').write_text('2')
        # current synthetic Current State declares uncommitted, so ready
        assert handoff_gate(h,repo_root=repo)['ready'] is True
        (h/'CURRENT_STATE.md').write_text('Active parent campaign: GLOBAL INTERACTION WAR CAMPAIGN\nclean claim',encoding='utf-8');files=json.loads((h/'SNAPSHOT_MANIFEST_SHA256.json').read_text());data=(h/'CURRENT_STATE.md').read_bytes();files['files']['CURRENT_STATE.md']={'bytes':len(data),'sha256':hashlib.sha256(data).hexdigest()};(h/'SNAPSHOT_MANIFEST_SHA256.json').write_text(json.dumps(files),encoding='utf-8')
        g=handoff_gate(h,repo_root=repo);assert g['ready'] is False;assert 'UNCOMMITTED_WORK_NOT_DECLARED_IN_HANDOFF' in g['failures']

def test_rehydrate_packet_is_bounded_hashed_and_gate_bearing():
    with tempfile.TemporaryDirectory() as td:
        h=Path(td);_handoff(h);p=rehydrate_packet(h,context='fresh thread recovery receiver failure',limit=4);assert p['ready'] is True;assert len(p['surfaces'])==4
        for row in p['surfaces']:assert len(row['sha256'])==64 and len(row['tail'])<=6000

def test_registry_covers_every_required_active_surface():
    names={x.name for x in SURFACE_REGISTRY}
    assert set(REQUIRED_ACTIVE_SURFACES).issubset(names)


def test_campaign_identity_ignores_descriptive_parenthetical_but_rejects_different_campaign():
    from mvf_resident.continuity_enforcement import _normalize_campaign_identity
    assert _normalize_campaign_identity('GLOBAL INTERACTION WAR CAMPAIGN (fully embodied clone -> pre-live organism beat-down)') == _normalize_campaign_identity('GLOBAL INTERACTION WAR CAMPAIGN')
    assert _normalize_campaign_identity('HUD COCKPIT WAR CAMPAIGN') != _normalize_campaign_identity('GLOBAL INTERACTION WAR CAMPAIGN')


def test_campaign_label_uses_latest_explicit_declaration_not_historical_first_match():
    with tempfile.TemporaryDirectory() as td:
        h=Path(td);_handoff(h)
        for name in ('COMMANDERS_INTENT_CURRENT.md','LIVE_SHADOW.md','CURRENT_STATE.md'):
            p=h/name;p.write_text(p.read_text()+"\nActive parent campaign: HUD COCKPIT WAR CAMPAIGN\n",encoding='utf-8')
            manifest=json.loads((h/'SNAPSHOT_MANIFEST_SHA256.json').read_text());data=p.read_bytes();manifest['files'][name]={'bytes':len(data),'sha256':hashlib.sha256(data).hexdigest()};(h/'SNAPSHOT_MANIFEST_SHA256.json').write_text(json.dumps(manifest),encoding='utf-8')
        g=handoff_gate(h)
        assert g['ready'] is True
        assert set(g['campaign_labels'].values())=={'HUD COCKPIT WAR CAMPAIGN'}
