from __future__ import annotations
import sys,tempfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'baseline'));from pcmmad_receiver.advisory_evidence import gather_runtime_source
def test_runtime_source_allowlist_reads_bounded_known_source():
 r=gather_runtime_source(runtime_root=ROOT,relative_path='baseline/pcmmad_receiver/project_mutation_authority.py',max_bytes=64);assert r['status']=='OBSERVED' and r['bytes_read']<=64 and r['authority']=='NONE'
def test_runtime_source_refuses_arbitrary_neighbor():assert gather_runtime_source(runtime_root=ROOT,relative_path='pyproject.toml')['status']=='NOT_ADMITTED'
def test_runtime_source_refuses_traversal():assert gather_runtime_source(runtime_root=ROOT,relative_path='baseline/pcmmad_receiver/../../../outside')['status']!='OBSERVED'
