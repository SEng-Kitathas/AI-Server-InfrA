from __future__ import annotations
import sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'baseline'));from pcmmad_receiver.cross_arm_recursion import *
def test_new_arm_fact_reopens_prior_blocker():
 r=reopen_scan(arm_results={'A':{'earned_facts':['authenticated_operator_principal']}},blockers=[{'arm':'B','id':'external-adopt','reopen_requires':['authenticated_operator_principal']}]);assert r['reopened'][0]['id']=='external-adopt'
def test_partial_requirements_stay_blocked_with_missing_explicit():
 r=reopen_scan(arm_results={'C':{'earned_facts':['resource_claims']}},blockers=[{'arm':'B','id':'commit','reopen_requires':['resource_claims','registry_transaction']}]);assert r['still_blocked'][0]['missing']==['registry_transaction']
def test_projection_never_grants_authority():assert project_result({'arm':'D','earned_facts':['x']},['A','B'])['authority']=='NONE'
