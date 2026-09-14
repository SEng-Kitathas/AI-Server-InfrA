"""Microseed Variant Framework promotion gate.

MVF composes qualified evidence; it does not create truth or authority. Promotion is
admissible only when every applicable required consumer is current and green.
"""
from __future__ import annotations
from typing import Any,Mapping
def evaluate(*,consumers:list[Mapping[str,Any]],applicable_doctrine:list[str])->dict[str,Any]:
 by={str(x.get('id')):dict(x) for x in consumers};missing=[x for x in applicable_doctrine if x not in by];failed=[];stale=[]
 for x in applicable_doctrine:
  r=by.get(x)
  if not r:continue
  if not bool(r.get('current')):stale.append(x)
  if not bool(r.get('qualified')):failed.append(x)
 ok=not missing and not failed and not stale
 return {'schema':'pcmmad.mvf-promotion.v1','promotion_admissible':ok,'authority':'NONE','missing_consumers':missing,'failed_consumers':failed,'stale_consumers':stale,'law':'DECLARED != BOUND != CONSUMED != CURRENT','claim_ceiling':'admissibility evidence only; does not perform promotion'}


def from_csc(*,declaration_binding:Mapping[str,Any],final_polish:Mapping[str,Any],coverage_graph:Mapping[str,Any])->dict[str,Any]:
 consumers=[{'id':'CSC_DECLARATION_BINDING','current':True,'qualified':bool(declaration_binding.get('qualified'))},{'id':'FINAL_QC','current':True,'qualified':bool(final_polish.get('qualified'))},{'id':'CSC_COVERAGE_GRAPH','current':True,'qualified':bool(coverage_graph.get('declaration_count',0)) and all(v.get('current') for v in coverage_graph.get('consumers',{}).values())}]
 return evaluate(consumers=consumers,applicable_doctrine=['CSC_DECLARATION_BINDING','FINAL_QC','CSC_COVERAGE_GRAPH'])
