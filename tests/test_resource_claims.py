from __future__ import annotations
import sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'baseline'));from pcmmad_receiver.resource_claims import *
def c(domain,res,mode='READ',project='P'):return {'domain':domain,'resource':res,'mode':mode,'project_id':project}
def test_disjoint_path_writes_candidate_parallel():assert jobs_compatible([c('path',r'a\\x','WRITE')],[c('path',r'b\\y','WRITE')])['compatible']
def test_parent_child_write_serializes():assert not jobs_compatible([c('path',r'a','WRITE')],[c('path',r'a\\x','READ')])['compatible']
def test_read_read_same_path_parallel():assert jobs_compatible([c('path',r'a','READ')],[c('path',r'a','READ')])['compatible']
def test_same_git_index_serializes_despite_different_files():assert not jobs_compatible([c('git_index','worktree-1','WRITE')],[c('git_index','worktree-1','WRITE')])['compatible']
def test_distinct_git_worktrees_candidate_parallel():assert jobs_compatible([c('git_index','w1','WRITE')],[c('git_index','w2','WRITE')])['compatible']
def test_unknown_domain_serializes():assert jobs_compatible([c('mystery','x')],[c('mystery','x')])['status']=='SERIAL_UNKNOWN'
def test_distinct_project_domains_parallel():assert jobs_compatible([c('project','root','WRITE','A')],[c('project','root','WRITE','B')])['compatible']
def test_relation_never_grants_authority():assert claims_conflict(c('path','a','WRITE'),c('path','a','WRITE'))['authority']=='NONE'
