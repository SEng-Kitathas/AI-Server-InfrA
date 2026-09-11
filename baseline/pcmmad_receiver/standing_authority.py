"""Operator-owned per-project standing authority profiles."""
from __future__ import annotations
import fnmatch, hashlib
from pathlib import Path
from typing import Any, Mapping
from .shared_core import SYSTEM_ROOT, load_json, save_json_atomic, utc_now
PROFILE_VERSION="1"; MODES={"standing","hitl","custom"}
def _root(): return SYSTEM_ROOT/"lab"/"standing_authority"
def _key(project_id):
 raw=str(project_id or "").strip();
 if not raw: raise ValueError("project_id is required")
 safe="".join(ch if ch.isalnum() or ch in "-_." else "_" for ch in raw)[:80] or "project"; return f"{safe}--{hashlib.sha256(raw.encode()).hexdigest()[:16]}"
def _path(project_id): return _root()/f"{_key(project_id)}.json"
def _patterns(v):
 if v is None:return []
 if isinstance(v,str):v=[x.strip() for x in v.replace("\n",",").split(",")]
 if not isinstance(v,(list,tuple)):raise ValueError("selector lists must be arrays or comma-separated strings")
 out=[]
 for x in v:
  x=str(x or "").strip()
  if x and x not in out:out.append(x)
 return out[:256]
def _selectors(v):
 v=v if isinstance(v,Mapping) else {}; return {k:_patterns(v.get(k)) for k in ("capabilities","categories","effect_traits","danger_tiers")}
def normalize_profile(v):
 project_id=str(v.get("project_id") or "").strip();
 if not project_id:raise ValueError("project_id is required")
 mode=str(v.get("mode") or "standing").lower().strip();
 if mode not in MODES:raise ValueError("mode must be standing, hitl, or custom")
 default=str(v.get("default_action") or ("ask" if mode=="hitl" else "allow")).lower().strip(); default="allow" if mode=="standing" else ("ask" if mode=="hitl" else default)
 if default not in {"allow","ask"}:raise ValueError("default_action must be allow or ask")
 return {"version":PROFILE_VERSION,"project_id":project_id,"mode":mode,"default_action":default,"allow":_selectors(v.get("allow")),"ask":_selectors(v.get("ask")),"deny":_selectors(v.get("deny")),"operator_id":str(v.get("operator_id") or "").strip(),"provenance":str(v.get("provenance") or "").strip(),"updated_at":utc_now()}
def save_profile(v):
 row=normalize_profile(v); p=_path(row["project_id"]); p.parent.mkdir(parents=True,exist_ok=True); save_json_atomic(p,row); return row
def load_profile(project_id):
 p=_path(project_id)
 if not p.exists():return None
 raw=load_json(p,default=None)
 if not isinstance(raw,dict):return None
 row=normalize_profile(raw); row["updated_at"]=raw.get("updated_at"); return row
def delete_profile(project_id):
 p=_path(project_id)
 if not p.exists():return False
 p.unlink(); return True
def _attr(spec,name,default=None): return getattr(spec,name, spec.get(name,default) if isinstance(spec,Mapping) else default)
def _match(patterns,values):
 for p in patterns:
  for v in values:
   if fnmatch.fnmatchcase(str(v).lower(),str(p).lower()):return p
 return None
def _selector_match(sel,spec):
 checks=(("capabilities",[_attr(spec,"name","")]),("categories",[_attr(spec,"category","")]),("effect_traits",list(_attr(spec,"effect_traits",[]) or [])),("danger_tiers",[_attr(spec,"danger_tier","")]))
 for key,vals in checks:
  hit=_match(list(sel.get(key) or []),vals)
  if hit is not None:return {"selector":key,"pattern":hit}
 return None
def project_id_from_payload(payload):
 direct=str(payload.get("project_id") or "").strip()
 if direct:return direct
 target=payload.get("target"); return str(target.get("project_id") or "").strip() if isinstance(target,Mapping) else ""
def resolve(spec,payload):
 project_id=project_id_from_payload(payload)
 if not project_id:return None
 profile=load_profile(project_id)
 if profile is None:return None
 for action in ("deny","ask","allow"):
  hit=_selector_match(profile[action],spec)
  if hit:return {"action":action,"project_id":project_id,"mode":profile["mode"],"matched":hit,"profile":profile}
 return {"action":profile["default_action"],"project_id":project_id,"mode":profile["mode"],"matched":{"selector":"default","pattern":profile["default_action"]},"profile":profile}
