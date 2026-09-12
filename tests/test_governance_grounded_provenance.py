from __future__ import annotations
import sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'baseline'))
from pcmmad_receiver import governance_provenance as g

def proc(pid,created='20260912',cmd='a'):
 return {'pid':pid,'creation_date':created,'executable_path':'python.exe','command_fingerprint':cmd}
def enrich_process(p,lineage):
 x=g.process_witness(p);x['lineage_id']=lineage;return x
def test_process_identity_is_grounded_from_observed_fields_not_label():
 r=g.process_witness(proc(10));assert r['grounded'] and r['failure_domain'].startswith('process:10:')
def test_pid_reuse_is_distinguished_by_creation_date():
 a=g.process_witness(proc(10,'A'));b=g.process_witness(proc(10,'B'));assert a['failure_domain']!=b['failure_domain']
def test_missing_process_creation_date_is_unknown():
 x=proc(10);x['creation_date']=None;assert g.process_witness(x)['status']=='UNKNOWN'
def test_source_lineage_requires_head_tree_and_root():
 assert g.source_witness({'source_head':'h','source_tree':'t','source_root':'r'})['grounded'];assert g.source_witness({'source_head':'h'})['status']=='UNKNOWN'
def test_contract_lineage_requires_real_digest_shape():
 assert g.contract_witness({'name':'x','contract_digest':'a'*64})['grounded'];assert g.contract_witness({'name':'x','contract_digest':'fake'})['status']=='UNKNOWN'
def test_self_labels_cannot_create_independence_without_both_grounded_dimensions():
 a=g.process_witness(proc(1));b=g.process_witness(proc(2));r=g.compose_independence(a,b);assert r['status']=='UNKNOWN'
def test_distinct_grounded_process_and_lineage_can_earn_independence():
 a=enrich_process(proc(1),'source:A');b=enrich_process(proc(2),'source:B');assert g.compose_independence(a,b)['status']=='INDEPENDENT'
def test_distinct_processes_same_lineage_remain_correlated():
 a=enrich_process(proc(1),'source:A');b=enrich_process(proc(2),'source:A');assert g.compose_independence(a,b)['status']=='CORRELATED'
def test_same_process_claiming_distinct_lineages_remains_correlated():
 a=enrich_process(proc(1),'source:A');b=enrich_process(proc(1),'source:B');assert g.compose_independence(a,b)['status']=='CORRELATED'
