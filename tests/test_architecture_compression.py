from __future__ import annotations

import hashlib
import json
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import sys
PROJECT_ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(PROJECT_ROOT/"baseline"))

from pcmmad_receiver.architecture_registry import ArtifactRegistryDeps, inspect_artifact
from pcmmad_receiver import migration_engine as migration
from pcmmad_receiver.derived_state import audit_ucm, rebuild_ucm
from pcmmad_receiver.scheduler_effect_profile import _load_witness_registries


class ArchitectureRegistryTests(unittest.TestCase):
    def test_cross_plane_currentness_and_repair_owner(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td); target=root/'continuity'/'x.md'; target.parent.mkdir(parents=True); target.write_text('x\n',encoding='utf-8')
            sha=hashlib.sha256(target.read_bytes()).hexdigest(); ledger=root/'commits.jsonl'
            ledger.write_text(json.dumps({'artifact_class':'state.current','logical_name':'CURRENT_STATE.md','sha256':sha,'generation':3})+'\n',encoding='utf-8')
            deps=ArtifactRegistryDeps(resolve_target=lambda *_:target,commits_ledger_path_for=lambda _p:ledger,sha256_file=lambda p:hashlib.sha256(p.read_bytes()).hexdigest())
            with patch('pcmmad_receiver.architecture_registry.get_project_root',create=True):
                pass
            with patch('pcmmad_receiver.architecture_registry.read_events',return_value=[]), patch('pcmmad_receiver.shared_core.get_project_root',return_value=root):
                row=inspect_artifact('P','state.current','CURRENT_STATE.md',deps)
            self.assertEqual(row['status'],'CURRENT');self.assertTrue(row['lineage']['current']);self.assertEqual(row['repair_capabilities'],[])
            target.write_text('changed\n',encoding='utf-8')
            with patch('pcmmad_receiver.architecture_registry.read_events',return_value=[]), patch('pcmmad_receiver.shared_core.get_project_root',return_value=root):
                stale=inspect_artifact('P','state.current','CURRENT_STATE.md',deps)
            self.assertEqual(stale['status'],'LINEAGE_STALE');self.assertIn('continuity.artifact.adopt',stale['repair_capabilities'])


class MigrationEngineTests(unittest.TestCase):
    def _deps(self,root:Path):
        target=root/'x.md';target.write_text('x\n',encoding='utf-8');sha=hashlib.sha256(target.read_bytes()).hexdigest()
        reg=ArtifactRegistryDeps(resolve_target=lambda *_:target,commits_ledger_path_for=lambda _p:root/'commits.jsonl',sha256_file=lambda p:hashlib.sha256(p.read_bytes()).hexdigest())
        adoption=SimpleNamespace(sha256_file=lambda p:hashlib.sha256(p.read_bytes()).hexdigest())
        return target,sha,migration.MigrationDeps(error_cls=RuntimeError,get_project_root=lambda _p:root,registry=reg,adoption=adoption,utc_now=lambda:'2026-09-11T00:00:00+00:00',save_json_atomic=lambda path,data:(path.parent.mkdir(parents=True,exist_ok=True),path.write_text(json.dumps(data),encoding='utf-8')))
    def test_plan_digest_is_deterministic_and_execute_rejects_tamper(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td);target,sha,deps=self._deps(root)
            with patch('pcmmad_receiver.architecture_registry.read_events',return_value=[]), patch('pcmmad_receiver.shared_core.get_project_root',return_value=root):
                plan=migration.plan_migration({'project_id':'P','kind':'artifact','artifact':{'artifact_class':'x','logical_name':'x.md'}},deps)
            self.assertEqual(plan['plan_sha256'],migration._digest({k:v for k,v in plan.items() if k!='plan_sha256'}))
            bad=dict(plan);bad['expected_sha256']='0'*64
            with self.assertRaises(Exception):
                migration.execute_migration({'project_id':'P','plan':bad,'plan_sha256':plan['plan_sha256']},deps)
    def test_receipt_hash_verification_detects_tamper(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td);_,_,deps=self._deps(root);d=root/'system'/'migrations'/'receipts';d.mkdir(parents=True);body={'schema':'pcmmad.migration-receipt.v1','receipt_id':'r','project_id':'P','kind':'artifact'};body['receipt_sha256']=migration._digest(body);(d/'r.json').write_text(json.dumps(body),encoding='utf-8')
            with patch.object(migration,'inspect_migration',return_value={'ok':True}):
                out=migration.verify_receipt({'project_id':'P','receipt_id':'r'},deps)
            self.assertTrue(out['receipt_hash_valid'])
            doc=json.loads((d/'r.json').read_text());doc['kind']='res';(d/'r.json').write_text(json.dumps(doc),encoding='utf-8')
            with patch.object(migration,'inspect_migration',return_value={'ok':True}):
                out=migration.verify_receipt({'project_id':'P','receipt_id':'r'},deps)
            self.assertFalse(out['receipt_hash_valid'])


class ArtifactCommitServiceTests(unittest.TestCase):
    def payload(self, project_id: str, *, operation: str, content: str, commit_id: str, idem: str, expected=None):
        import hashlib
        return {
            "project_id": project_id,
            "artifact_class": "state.current",
            "logical_name": "CURRENT_STATE.md",
            "operation": operation,
            "content": content,
            "content_sha256": hashlib.sha256(content.encode("utf-8")).hexdigest(),
            "expected_previous_sha256": expected,
            "session_id": "test-session",
            "commit_id": commit_id,
            "idempotency_key": idem,
            "render_mode": "utf8_exact",
        }

    def test_create_update_exact_cas_and_idempotent_replay(self):
        from pcmmad_receiver.artifact_commit_service import commit_artifact, ArtifactCommitError
        from pcmmad_receiver.shared_core import resolve_target
        project="ARCH-COMMIT-A"
        first=commit_artifact(self.payload(project,operation="create",content="one\n",commit_id="c1",idem="i1"))
        self.assertFalse(first["replayed"])
        again=commit_artifact(self.payload(project,operation="create",content="one\n",commit_id="c1",idem="i1"))
        self.assertTrue(again["replayed"]);self.assertEqual(first["sha256"],again["sha256"])
        second=commit_artifact(self.payload(project,operation="update",content="two\n",commit_id="c2",idem="i2",expected=first["sha256"]))
        self.assertNotEqual(first["sha256"],second["sha256"])
        target=resolve_target(project,"state.current","CURRENT_STATE.md")
        self.assertEqual(target.read_bytes(),b"two\n")
        with self.assertRaises(ArtifactCommitError) as ctx:
            commit_artifact(self.payload(project,operation="update",content="three\n",commit_id="c3",idem="i3",expected=first["sha256"]))
        self.assertEqual(ctx.exception.error_code,"HASH_MISMATCH")

    def test_content_hash_idempotency_and_commit_id_conflicts_fail_closed(self):
        from pcmmad_receiver.artifact_commit_service import commit_artifact, ArtifactCommitError
        project="ARCH-COMMIT-B";payload=self.payload(project,operation="create",content="alpha\n",commit_id="c1",idem="i1")
        bad=dict(payload);bad["content_sha256"]="0"*64
        with self.assertRaises(ArtifactCommitError) as ctx: commit_artifact(bad)
        self.assertEqual(ctx.exception.error_code,"CONTENT_HASH_INVALID")
        first=commit_artifact(payload)
        conflict=self.payload(project,operation="update",content="beta\n",commit_id="c2",idem="i1",expected=first["sha256"])
        with self.assertRaises(ArtifactCommitError) as ctx: commit_artifact(conflict)
        self.assertEqual(ctx.exception.error_code,"IDEMPOTENCY_KEY_CONFLICT")
        other=self.payload(project,operation="update",content="beta\n",commit_id="c1",idem="i2",expected=first["sha256"])
        with self.assertRaises(ArtifactCommitError) as ctx: commit_artifact(other)
        self.assertEqual(ctx.exception.error_code,"COMMIT_ID_CONFLICT")


class DerivedStateTests(unittest.TestCase):
    def test_orphan_derived_zero_head_is_cleared(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td);sn=root/'snapshots';sn.mkdir();(sn/'x.json').write_text('{}');cur=root/'current.json';cur.write_text('{}')
            paths=SimpleNamespace(root=root,ledger=root/'events.jsonl',current=cur,snapshots=sn)
            with patch('pcmmad_receiver.derived_state.ucm.head',return_value={'ledger_head_seq':0,'ledger_head_hash':None,'snapshot_from_seq':0,'snapshot_current':False}),patch('pcmmad_receiver.derived_state.backend._paths',return_value=paths):
                before=audit_ucm('p');self.assertEqual(before['status'],'ORPHAN_DERIVED')
                with patch.object(__import__('pcmmad_receiver.derived_state',fromlist=['backend']).backend,'_CACHE_GUARD',__import__('threading').RLock()),patch.object(__import__('pcmmad_receiver.derived_state',fromlist=['backend']).backend,'_STATE_CACHE',{}):
                    out=rebuild_ucm('p',0,None)
            self.assertEqual(out['action'],'ORPHAN_DERIVED_CLEARED');self.assertFalse(cur.exists());self.assertEqual(list(sn.glob('*.json')),[])


class WitnessLoaderTests(unittest.TestCase):
    def test_missing_invalid_and_valid_witness_file_fail_closed(self):
        with tempfile.TemporaryDirectory() as td:
            p=Path(td)/'w.json';self.assertEqual(_load_witness_registries(p),({},{},{}));p.write_text('{}');self.assertEqual(_load_witness_registries(p),({},{},{}));d='a'*64;p.write_text(json.dumps({'schema':'pcmmad.scheduler-effect-witnesses.v1','effect_truth':{'x':{'contract_digest':d,'effect_kind':'READ_LOCAL'}},'parallel':{},'resume_replay':{}}));truth,parallel,replay=_load_witness_registries(p);self.assertEqual(truth['x']['contract_digest'],d);self.assertEqual(parallel,{});self.assertEqual(replay,{})


class HudProjectionTests(unittest.TestCase):
    def test_hud_contains_architecture_projection_not_duplicate_authority_engine(self):
        root=Path(__file__).resolve().parents[1];html=(root/'operator_hud/static/index.html').read_text(encoding='utf-8');js=(root/'operator_hud/static/app.js').read_text(encoding='utf-8');server=(root/'operator_hud/server.py').read_text(encoding='utf-8')
        self.assertIn('ARCHITECTURE · CURRENTNESS',html);self.assertIn('loadArchitecture',js);self.assertIn('/api/architecture',server);self.assertIn('architecture.runtime.status',server)


if __name__=='__main__': unittest.main()
