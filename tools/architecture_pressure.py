#!/usr/bin/env python3
from __future__ import annotations
import concurrent.futures, hashlib, importlib.util, json, sys, time
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'baseline'))
from pcmmad_receiver.artifact_commit_service import commit_artifact
from pcmmad_receiver.architecture_registry import ArtifactRegistryDeps, inspect_artifact
from pcmmad_receiver.lab_tools_continuity import AdoptionDeps
from pcmmad_receiver import migration_engine as migration
from pcmmad_receiver import lab_tools
from pcmmad_receiver import derived_state
from pcmmad_receiver import user_continuity_store as ucm_backend
from pcmmad_receiver.shared_core import (
    append_jsonl, commits_ledger_path_for, get_project_root, load_json, manifest_path_for,
    resolve_target, save_json_atomic, sha256_file, utc_now,
)


def h(value): return hashlib.sha256(json.dumps(value,sort_keys=True,separators=(',',':'),ensure_ascii=False,default=str).encode()).hexdigest()

def file_tree_hash(root: Path):
    rows=[]
    if root.exists():
        for p in sorted(root.rglob('*')):
            if p.is_file(): rows.append((p.relative_to(root).as_posix(),p.stat().st_size,hashlib.sha256(p.read_bytes()).hexdigest()))
    return h(rows)

def main(out_path: str):
    started=time.perf_counter();report={'schema':'pcmmad.architecture-pressure.v1','failures':[],'workloads':{}}
    # Artifact commit pressure: exact CAS + replay.
    project='PRESSURE-COMMIT';content='seed\n';sha=hashlib.sha256(content.encode()).hexdigest()
    first=commit_artifact({'project_id':project,'artifact_class':'state.current','logical_name':'CURRENT_STATE.md','operation':'create','content':content,'content_sha256':sha,'expected_previous_sha256':None,'session_id':'pressure','commit_id':'c0','idempotency_key':'i0','render_mode':'utf8_exact'})
    current=first['sha256'];replays=0
    t=time.perf_counter()
    for i in range(1,201):
        text=f'value-{i}\n';payload={'project_id':project,'artifact_class':'state.current','logical_name':'CURRENT_STATE.md','operation':'update','content':text,'content_sha256':hashlib.sha256(text.encode()).hexdigest(),'expected_previous_sha256':current,'session_id':'pressure','commit_id':f'c{i}','idempotency_key':f'i{i}','render_mode':'utf8_exact'}
        row=commit_artifact(payload);current=row['sha256'];again=commit_artifact(payload);replays+=int(bool(again['replayed']))
    ledger_lines=len(commits_ledger_path_for(project).read_text(encoding='utf-8').splitlines())
    report['workloads']['artifact_commit']={'updates':200,'replays':replays,'ledger_lines':ledger_lines,'final_sha256':current,'seconds':round(time.perf_counter()-t,4),'pass':replays==200 and ledger_lines==201}
    # Migration execute/receipt pressure on pre-existing exact bytes.
    class E(RuntimeError):
        def __init__(self,error_code,message,status=409,**extra): super().__init__(message);self.error_code=error_code;self.message=message;self.status=status;self.extra=extra
    mproject='PRESSURE-MIGRATION';target=resolve_target(mproject,'state.current','CURRENT_STATE.md');target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(b'migration-source\r\n');before=target.read_bytes()
    adoption=AdoptionDeps(error_cls=E,get_project_root=get_project_root,resolve_target=resolve_target,commits_ledger_path_for=commits_ledger_path_for,manifest_path_for=manifest_path_for,sha256_file=sha256_file,load_json=load_json,save_json_atomic=save_json_atomic,append_jsonl=append_jsonl,utc_now=utc_now)
    reg=ArtifactRegistryDeps(resolve_target=resolve_target,commits_ledger_path_for=commits_ledger_path_for,sha256_file=sha256_file)
    deps=migration.MigrationDeps(error_cls=E,get_project_root=get_project_root,registry=reg,adoption=adoption,utc_now=utc_now,save_json_atomic=save_json_atomic)
    req={'project_id':mproject,'kind':'artifact','artifact':{'artifact_class':'state.current','logical_name':'CURRENT_STATE.md'}};plan=migration.plan_migration(req,deps)
    t=time.perf_counter();valid=0
    for i in range(50):
        out=migration.execute_migration({'project_id':mproject,'plan':plan,'plan_sha256':plan['plan_sha256'],'receipt_id':f'r{i}','session_id':'pressure'},deps)
        check=migration.verify_receipt({'project_id':mproject,'receipt_id':f'r{i}'},deps);valid+=int(bool(out['ok'] and check['receipt_hash_valid']))
    report['workloads']['migration']={'executions':50,'verified_receipts':valid,'bytes_unchanged':target.read_bytes()==before,'seconds':round(time.perf_counter()-t,4),'pass':valid==50 and target.read_bytes()==before}
    # Witnessed read pressure and project-state non-mutation.
    cards={x['name']:x for x in lab_tools.list_tools()};cases=[('protocol.status',{'project_id':mproject}),('protocol.merkle.root',{'project_id':mproject}),('architecture.registry.inspect',{'project_id':mproject,'artifact':{'artifact_class':'state.current','logical_name':'CURRENT_STATE.md'}})]
    before_tree=file_tree_hash(get_project_root(mproject));read_rows={};t=time.perf_counter()
    for name,payload in cases:
        digest=cards[name]['contract_digest']
        def call(_): return lab_tools.dispatch_tool(name,payload,expected_contract_digest=digest)['result']
        with concurrent.futures.ThreadPoolExecutor(max_workers=32) as ex: rows=list(ex.map(call,range(100)))
        hashes={h(x) for x in rows};read_rows[name]={'calls':100,'unique_result_hashes':len(hashes),'pass':len(hashes)==1}
    after_tree=file_tree_hash(get_project_root(mproject));report['workloads']['witnessed_reads']={'cases':read_rows,'project_state_unchanged':before_tree==after_tree,'seconds':round(time.perf_counter()-t,4),'pass':all(x['pass'] for x in read_rows.values()) and before_tree==after_tree}
    # Derived-state orphan cleanup pressure on isolated UCM.
    t=time.perf_counter();cleared=0
    for i in range(100):
        pid=f'orphan-{i}';paths=ucm_backend._paths(pid);paths.snapshots.mkdir(parents=True,exist_ok=True);paths.current.parent.mkdir(parents=True,exist_ok=True);paths.current.write_text('{}',encoding='utf-8');(paths.snapshots/'orphan.json').write_text('{}',encoding='utf-8')
        result=derived_state.rebuild_ucm(pid,0,None);cleared+=int(result['after']['status']=='EMPTY')
    report['workloads']['derived_state']={'cycles':100,'cleared':cleared,'seconds':round(time.perf_counter()-t,4),'pass':cleared==100}
    # Standalone supervisor pressure using injected probes; never touches Windows task scheduler.
    spec=importlib.util.spec_from_file_location('receiver_supervisor',ROOT/'supervisor/receiver_supervisor.py');sup=importlib.util.module_from_spec(spec);spec.loader.exec_module(sup)
    receipts=ROOT/'qualification'/'pressure'/'supervisor';receipts.mkdir(parents=True,exist_ok=True);triggers=[];t=time.perf_counter();healthy_ok=0;recover_ok=0
    for i in range(500):
        r=sup.supervise_once(health_url='x',task_name='receiver',receipt_path=receipts/f'h{i}.json',health_probe=lambda *_:(True,None),trigger=lambda n:(triggers.append(n) or (True,'started')),recovery_seconds=.001,poll_seconds=.0001);healthy_ok+=int(r['healthy_after'] and r['action']=='NONE')
    for i in range(100):
        states=iter([(False,'down'),(True,None)])
        def probe(*_): return next(states,(True,None))
        r=sup.supervise_once(health_url='x',task_name='receiver',receipt_path=receipts/f'r{i}.json',health_probe=probe,trigger=lambda n:(triggers.append(n) or (True,'started')),recovery_seconds=.01,poll_seconds=.0001);recover_ok+=int(r['healthy_after'] and r['triggered'])
    report['workloads']['supervisor']={'healthy_cycles':500,'healthy_ok':healthy_ok,'recovery_cycles':100,'recovery_ok':recover_ok,'triggers':len(triggers),'seconds':round(time.perf_counter()-t,4),'pass':healthy_ok==500 and recover_ok==100 and len(triggers)==100}
    report['pass']=all(v.get('pass') for v in report['workloads'].values());report['seconds']=round(time.perf_counter()-started,4)
    out=Path(out_path);out.parent.mkdir(parents=True,exist_ok=True);out.write_text(json.dumps(report,indent=2,sort_keys=True)+'\n',encoding='utf-8');print(json.dumps(report,sort_keys=True));raise SystemExit(0 if report['pass'] else 2)
if __name__=='__main__': main(sys.argv[1])
