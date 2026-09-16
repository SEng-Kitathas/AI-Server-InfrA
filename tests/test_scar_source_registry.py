from __future__ import annotations
import json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
REG=ROOT/'scar_sources'/'SOURCE_REGISTRY.json'

def test_uploaded_global_scar_ledger_identity_is_registered_without_authority_promotion():
    obj=json.loads(REG.read_text(encoding='utf-8-sig'));assert obj['schema']=='pcmmad.scar-source-registry.v1';src=obj['sources'][0]
    assert src['source_id']=='rahl-engineering-consolidated-doctrine-scar-ledger-2026-09-13'
    assert src['sha256']=='7643b0faa7841205f374a0ce2cfecee970a807cba3ea322f8b4c1e93dd298696'
    assert src['bytes']==20318;assert src['source_class']=='GATHERING';assert src['authority']=='NONE_FROM_COMPILATION'
    assert src['evidence_ceiling']==['CONSOLIDATION != CANON','COMPILED_BY_ASSISTANT != OPERATOR_RATIFIED','GATHERED != RE_EARNED']
    assert src['status']=='MATERIALIZED_VERIFIED';assert src['materialized_path']=='scar_sources/RAHL ENGINEERING CONSOLIDATED DOCTRINE AND SCAR LEDGER 2026-09-13.md'
    materialized=ROOT/src['materialized_path'];assert materialized.is_file();assert materialized.stat().st_size==20318
    import hashlib;assert hashlib.sha256(materialized.read_bytes()).hexdigest()==src['sha256']


def test_materialized_global_ledger_enters_derived_index_without_source_deficit():
    import sys
    sys.path.insert(0,str(ROOT))
    from mvf_resident.scar_intelligence import collect_scars
    idx=collect_scars([ROOT/'handoff'/'current',ROOT/'scar_sources'])
    assert idx['source_deficits']==[]
    external=[o for scar in idx['scars'] for o in scar.get('occurrences',[]) if o.get('source_plane')=='scar_sources']
    assert len(external)>=100
    assert any(o.get('provenance')=='EARNED' for o in external)
    assert any(o.get('provenance')=='DONOR' for o in external)
    assert any(str(o.get('source','')).endswith('RAHL ENGINEERING CONSOLIDATED DOCTRINE AND SCAR LEDGER 2026-09-13.md') for o in external)
