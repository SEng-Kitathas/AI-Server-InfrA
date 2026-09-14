"""Reseal handoff/current manifest after canonical rollover members change."""
from __future__ import annotations
import hashlib,json
from datetime import datetime,timezone
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];HANDOFF=ROOT/'handoff'/'current';MANIFEST=HANDOFF/'SNAPSHOT_MANIFEST_SHA256.json'
def reseal()->dict:
 d=json.loads(MANIFEST.read_text(encoding='utf-8'))
 for name,row in d['files'].items():
  p=HANDOFF/name
  if not p.is_file():raise FileNotFoundError(name)
  row['bytes']=p.stat().st_size;row['sha256']=hashlib.sha256(p.read_bytes()).hexdigest()
 d['created_at']=datetime.now(timezone.utc).isoformat();MANIFEST.write_text(json.dumps(d,indent=2,sort_keys=True)+'\n',encoding='utf-8');return d
if __name__=='__main__':reseal()
