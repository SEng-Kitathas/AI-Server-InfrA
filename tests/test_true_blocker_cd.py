from __future__ import annotations
import sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'baseline'));from pcmmad_receiver.resource_claim_derivation import classify_unmapped_traits;from pcmmad_receiver.agent_advisory import qualify_hypothesis_candidate
def test_unknown_mutating_trait_stays_serial():assert not classify_unmapped_traits(['mutates_magic'])['parallel_admissible']
def test_unknown_unclassified_trait_stays_serial():assert not classify_unmapped_traits(['semantic_foo'])['parallel_admissible']
def test_read_trait_can_be_candidate_nonhazard_but_no_authority():
 r=classify_unmapped_traits(['reads_state']);assert r['parallel_admissible'] and r['authority']=='NONE'
def test_hypothesis_without_discriminator_remains_unqualified():assert qualify_hypothesis_candidate({'hypothesis':'h'},[])['status']=='UNQUALIFIED_CANDIDATE'
def test_discriminated_hypothesis_never_promotes_truth():
 r=qualify_hypothesis_candidate({'hypothesis':'h'},[{'targets':['h'],'outcome':'SUPPORTED'}]);assert r['status']=='DISCRIMINATED_CANDIDATE' and not r['truth_promoted'] and r['authority']=='NONE'
