from __future__ import annotations

import json,re,subprocess
from dataclasses import dataclass,asdict
from pathlib import Path
from typing import Any
from .surfaces import audit_continuity_surfaces

@dataclass(frozen=True)
class SurfaceSpec:
    name:str;authority:str;priority:int;topics:tuple[str,...];always_for:tuple[str,...]=()

SURFACE_REGISTRY=(
    SurfaceSpec('COMMANDERS_INTENT_CURRENT.md','operator_intent',100,('commander','intent','goal','scope','defer','campaign','priority','authority'),('mutation','handoff','recovery','promotion')),
    SurfaceSpec('LIVE_SHADOW.md','live_operational_state',95,('live','runtime','pid','port','head','current','failure','recovery','daemon','receiver','ngrok'),('mutation','handoff','recovery')),
    SurfaceSpec('CURRENT_STATE.md','materialized_project_state',90,('current','state','implemented','qualified','blocker','runtime','campaign'),('mutation','handoff','recovery')),
    SurfaceSpec('NEXT_STEPS.md','continuation_plan',85,('next','step','campaign','priority','p0','blocker','plan'),('handoff','recovery')),
    SurfaceSpec('TRACE_MATRIX.md','claim_evidence_reopen',80,('evidence','verified','claim','reopen','trace','qualification','test','hash'),('audit','promotion')),
    SurfaceSpec('REVISIT_LEDGER.md','open_seams_debt',75,('revisit','open','debt','blocker','deferred','risk','seam'),('handoff','audit')),
    SurfaceSpec('DESIGN_THREAD_STREAM.md','chronological_design_lineage',65,('design','architecture','why','history','decision','convergence','lineage'),()),
    SurfaceSpec('SERVER_THREAD_HANDOFF_CURRENT.md','server_recovery_handoff',85,('server','handoff','recovery','runtime','thread'),('handoff','recovery')),
    SurfaceSpec('NEW_THREAD_HANDOFF_PROMPT_CURRENT.md','fresh_thread_ingress',85,('new thread','fresh thread','rehydrate','handoff','ingress'),('handoff','recovery')),
    SurfaceSpec('THREAD_CONTINUITY_CHECKPOINT_2026-09-15.md','thread_checkpoint',80,('checkpoint','thread','recovery','campaign','continuity'),('handoff','recovery')),
    SurfaceSpec('DOCTRINE_SNAPSHOT.md','governing_distinctions',70,('doctrine','law','rule','scar','distinction','authority','heat','interaction'),('audit','promotion')),
)

def _text(path:Path)->str:return path.read_text(encoding='utf-8',errors='ignore')
def _tokens(s:str)->set[str]:return set(re.findall(r'[a-z0-9_!=>.-]+',s.casefold()))
def _campaign_labels(handoff:Path)->dict[str,str]:
    out={}
    patterns=[r'active parent campaign\s*:\s*([^\n]+)',r'parent\s*:\s*([^\n]+)',r'active parent campaign remains the \*\*([^*]+)\*\*']
    for name in ('COMMANDERS_INTENT_CURRENT.md','LIVE_SHADOW.md','CURRENT_STATE.md'):
        p=handoff/name
        if not p.exists():continue
        txt=_text(p)
        for pat in patterns:
            m=re.search(pat,txt,re.I)
            if m:out[name]=m.group(1).strip(' .*`');break
    return out

def plan_surface_use(handoff_dir:Path,context:str,*,mode:str='discussion',limit:int=5)->dict[str,Any]:
    handoff_dir=handoff_dir.resolve();mode=mode.casefold();limit=max(1,min(int(limit),len(SURFACE_REGISTRY)));ctx=context.casefold();ctx_tokens=_tokens(ctx);ranked=[]
    for spec in SURFACE_REGISTRY:
        p=handoff_dir/spec.name
        if not p.exists():continue
        score=spec.priority if mode in spec.always_for else 0;hits=[]
        for topic in spec.topics:
            if topic in ctx or (len(topic)>3 and topic in ctx_tokens):score+=30;hits.append(topic)
        # Generic low-value availability: every governed surface can surface, but only after direct relevance/mandatory ones.
        if score==0:score=max(1,spec.priority//20)
        ranked.append({'surface':spec.name,'authority':spec.authority,'score':score,'mandatory_for_mode':mode in spec.always_for,'matched_topics':hits,'reason':('mandatory '+mode if mode in spec.always_for else ('matched: '+', '.join(hits) if hits else 'available low-priority context'))})
    ranked.sort(key=lambda x:(x['score'],x['surface']),reverse=True)
    selected=ranked[:limit]
    return {'schema':'mvf.continuity-surfacing-plan.v1','mode':mode,'context':context[:2000],'selected':selected,'considered_count':len(ranked),'ritual_dump_avoided':len(selected)<len(ranked),'mutation_authority':False}

def _normalize_campaign_identity(value:str)->str:
    text=re.sub(r'\([^)]*\)',' ',str(value).casefold())
    text=re.sub(r'[`*_>#:-]+',' ',text)
    text=re.sub(r'\s+',' ',text).strip()
    return text

def handoff_gate(handoff_dir:Path,*,repo_root:Path|None=None)->dict[str,Any]:
    handoff_dir=handoff_dir.resolve();audit=audit_continuity_surfaces(handoff_dir).to_dict();failures=[];warnings=[]
    if audit['status']!='CURRENT':failures.append('ACTIVE_SURFACES_NOT_CURRENT')
    for name in ('COMMANDERS_INTENT_CURRENT.md','LIVE_SHADOW.md','CURRENT_STATE.md','NEXT_STEPS.md','REVISIT_LEDGER.md','TRACE_MATRIX.md'):
        if not (handoff_dir/name).is_file():failures.append('REQUIRED_HANDOFF_SURFACE_MISSING:'+name)
    labels=_campaign_labels(handoff_dir);norm={_normalize_campaign_identity(v) for v in labels.values() if v}
    if len(norm)>1:failures.append('ACTIVE_CAMPAIGN_CONFLICT')
    if len(labels)<2:warnings.append('ACTIVE_CAMPAIGN_WEAKLY_REPLICATED')
    git={'head':None,'status':[]}
    if repo_root is not None:
        try:
            git['head']=subprocess.check_output(['git','-C',str(repo_root),'rev-parse','HEAD'],text=True,timeout=5).strip()
            raw=subprocess.check_output(['git','-C',str(repo_root),'status','--short'],text=True,timeout=5)
            git['status']=[x for x in raw.splitlines() if x.strip()]
        except Exception as exc:failures.append('GIT_STATE_UNAVAILABLE:'+type(exc).__name__)
        if git['status']:
            corpus='\n'.join(_text(handoff_dir/n) for n in ('LIVE_SHADOW.md','CURRENT_STATE.md','NEW_THREAD_HANDOFF_PROMPT_CURRENT.md') if (handoff_dir/n).exists()).casefold()
            if 'uncommitted' not in corpus and 'working tree' not in corpus:failures.append('UNCOMMITTED_WORK_NOT_DECLARED_IN_HANDOFF')
    return {'schema':'mvf.handoff-gate.v1','ready':not failures,'failures':failures,'warnings':warnings,'surface_audit':audit,'campaign_labels':labels,'git':git,'mutation_authority':False}

def rehydrate_packet(handoff_dir:Path,*,repo_root:Path|None=None,context:str='fresh thread recovery',limit:int=7)->dict[str,Any]:
    gate=handoff_gate(handoff_dir,repo_root=repo_root);plan=plan_surface_use(handoff_dir,context,mode='recovery',limit=limit);packet=[]
    for item in plan['selected']:
        p=handoff_dir/item['surface'];txt=_text(p);packet.append({'surface':item['surface'],'authority':item['authority'],'reason':item['reason'],'sha256':__import__('hashlib').sha256(p.read_bytes()).hexdigest(),'tail':txt[-6000:]})
    return {'schema':'mvf.rehydrate-packet.v1','ready':gate['ready'],'gate':gate,'surfacing_plan':plan,'surfaces':packet,'mutation_authority':False}
