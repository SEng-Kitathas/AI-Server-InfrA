from __future__ import annotations

import hashlib,json,re,time
from collections import Counter,defaultdict
from pathlib import Path
from typing import Any,Iterable

SCHEMA='mvf.scar-intelligence.v1'
_PROV=('LAW','EARNED','OBSERVED','DONOR','PROPOSED')
_TOPIC_RULES={
 'execution':('execution','worker','process','subprocess','job object','timeout','cancel','pid','child','restart'),
 'continuity':('continuity','handoff','shadow','thread','rehydrate','context','commander','intent','surface'),
 'ha_recovery':('recovery','supervisor','restart','hold','crash-loop','ha','availability','recoverable'),
 'authority':('authority','approval','permit','operator','mutation','gate','fence','scope'),
 'evidence':('evidence','verified','claim','proof','observation','epistemic','unknown'),
 'security':('defender','security','antivirus','threat','quarantine','remediation'),
 'promotion':('promotion','rollback','install','deployment','canon','load-bearing','qualified'),
 'interaction':('interaction','local optimum','global','composition','component','system'),
 'daemon':('daemon','resident','cognition','initiative','brain','organism'),
 'hud':('hud','cockpit','dashboard','annunciator','warning','display','operator'),
 'persistence':('sqlite','database','persist','state','checkpoint','biography','ledger','timeline'),
 'routing':('router','routing','tool','capability','dispatch','bridge'),
}

def _sha_text(text:str)->str:return hashlib.sha256(text.encode('utf-8')).hexdigest()
def _tokens(text:str)->set[str]:return set(re.findall(r'[a-z0-9_!=>.-]+',text.casefold()))
def _normalize_expr(expr:str)->str:
    x=expr.strip().strip('`*_ -•\t')
    x=re.sub(r'\s+',' ',x)
    x=re.sub(r'\s*!=\s*',' != ',x)
    return x.strip()
def _identity(expr:str)->str:return _sha_text(_normalize_expr(expr).casefold())
def _heading_before(lines:list[str],idx:int)->str|None:
    for j in range(idx,-1,-1):
        s=lines[j].strip()
        if s.startswith('#'):return s.lstrip('#').strip()[:240]
    return None
def _provenance(lines:list[str],idx:int)->str:
    # Provenance is inherited through the active markdown heading ancestry. A leaf
    # subsection like `### 3.1 Verification` may inherit EARNED from its parent
    # `## §3 EARNED SCARS`, but must never bleed sideways from a previous sibling.
    current=lines[idx].upper()
    for p in _PROV:
        if re.search(r'\b'+p+r'\b',current):return p
    nearest_idx=None;nearest_level=None
    for j in range(idx,-1,-1):
        text=lines[j].strip()
        if text.startswith('#'):
            nearest_idx=j;nearest_level=len(text)-len(text.lstrip('#'));break
    if nearest_idx is None:return 'UNSPECIFIED'
    local=' '.join(lines[max(nearest_idx+1,idx-2):idx+1]).upper()
    for p in _PROV:
        if re.search(r'\b'+p+r'\b',local):return p
    level=nearest_level
    for j in range(nearest_idx,-1,-1):
        text=lines[j].strip()
        if not text.startswith('#'):continue
        hlevel=len(text)-len(text.lstrip('#'))
        if j!=nearest_idx and hlevel>=level:continue
        heading=text.lstrip('#').strip().upper()
        for p in _PROV:
            if re.search(r'\bCLASS\s+'+p+r'\b',heading) or re.search(r'\b'+p+r'\b',heading):return p
        level=hlevel
        if level<=1:break
    return 'UNSPECIFIED'
def _tags(expr:str,heading:str|None,context:str)->list[str]:
    hay=' '.join(x for x in (expr,heading or '',context) if x).casefold();tags=[]
    for tag,words in _TOPIC_RULES.items():
        if any(w in hay for w in words):tags.append(tag)
    return sorted(tags)
def _candidate_exprs(line:str)->list[str]:
    # The scar grammar is deliberately conservative: collect explicit compression forms only.
    clean=line.strip()
    out=[]
    # backticked scars are preferred
    for x in re.findall(r'`([^`]*!=[^`]*)`',clean):out.append(x)
    if '!=' in clean and not out:
        x=re.sub(r'^[-*+>\s]+','',clean)
        x=re.sub(r'^\d+[.)]\s*','',x)
        if len(x)<=500:out.append(x)
    return out

def extract_scars_from_file(path:Path,*,source_root:Path|None=None)->list[dict[str,Any]]:
    text=path.read_text(encoding='utf-8',errors='ignore');lines=text.splitlines();out=[];rel=path.name if source_root is None else path.resolve().relative_to(source_root.resolve()).as_posix()
    for i,line in enumerate(lines):
        for raw in _candidate_exprs(line):
            expr=_normalize_expr(raw)
            if not expr or '!=' not in expr:continue
            heading=_heading_before(lines,i);context=' | '.join(x.strip() for x in lines[max(0,i-2):min(len(lines),i+3)] if x.strip())[:1600]
            out.append({'scar_id':_identity(expr),'expression':expr,'source':rel,'line':i+1,'heading':heading,'source_sha256':hashlib.sha256(path.read_bytes()).hexdigest(),'provenance':_provenance(lines,i),'tags':_tags(expr,heading,context),'context':context})
    return out

def _source_roots(source_dirs:Path|Iterable[Path])->list[Path]:
    if isinstance(source_dirs,(str,Path)):
        roots=[Path(source_dirs)]
    else:
        roots=[Path(x) for x in source_dirs]
    out=[];seen=set()
    for root in roots:
        rr=root.resolve()
        if rr in seen or not rr.exists() or not rr.is_dir():continue
        seen.add(rr);out.append(rr)
    return out

def _registry_status(root:Path)->dict[str,Any]|None:
    path=root/'SOURCE_REGISTRY.json'
    if not path.exists():return None
    try:obj=json.loads(path.read_text(encoding='utf-8-sig'))
    except Exception as exc:return {'path':str(path),'schema':None,'ok':False,'error':f'{type(exc).__name__}: {exc}','sources':[]}
    rows=[]
    for src in obj.get('sources',[]) if isinstance(obj,dict) else []:
        if not isinstance(src,dict):continue
        filename=str(src.get('filename') or '')
        candidate=(root/filename).resolve() if filename else None
        materialized=bool(candidate and candidate.is_file())
        actual_sha=hashlib.sha256(candidate.read_bytes()).hexdigest() if materialized else None
        expected=str(src.get('sha256') or '').casefold() or None
        hash_ok=bool(materialized and expected and actual_sha==expected)
        status='MATERIALIZED_VERIFIED' if hash_ok else ('MATERIALIZED_HASH_MISMATCH' if materialized else str(src.get('status') or 'REGISTERED_PENDING'))
        rows.append({
            'source_id':src.get('source_id'),'filename':filename,'source_class':src.get('source_class'),'authority':src.get('authority'),
            'evidence_ceiling':src.get('evidence_ceiling') or [],'provenance_classes':src.get('provenance_classes') or [],
            'expected_sha256':expected,'actual_sha256':actual_sha,'materialized':materialized,'hash_ok':hash_ok,'status':status,
        })
    return {'path':str(path),'schema':obj.get('schema') if isinstance(obj,dict) else None,'ok':True,'sources':rows}

def collect_scars(source_dir:Path|Iterable[Path],*,include_globs:Iterable[str]=('*.md',))->dict[str,Any]:
    roots=_source_roots(source_dir);occ=[];files=[];registries=[]
    for root_index,root in enumerate(roots):
        plane='active_handoff' if root_index==0 else root.name
        registry=_registry_status(root)
        if registry:registries.append({'source_plane':plane,**registry})
        for glob in include_globs:
            for path in sorted(root.glob(glob)):
                if not path.is_file():continue
                rows=extract_scars_from_file(path,source_root=root)
                for row in rows:
                    row['source_plane']=plane;row['source']=f"{plane}:{row['source']}"
                if rows:files.append({'source_plane':plane,'path':path.name,'sha256':hashlib.sha256(path.read_bytes()).hexdigest(),'count':len(rows)})
                occ.extend(rows)
    grouped:dict[str,list[dict[str,Any]]]=defaultdict(list)
    for row in occ:grouped[row['scar_id']].append(row)
    scars=[]
    for sid,rows in grouped.items():
        tag_counts=Counter(t for r in rows for t in r['tags']);prov_counts=Counter(r['provenance'] for r in rows);plane_counts=Counter(r.get('source_plane','unknown') for r in rows)
        scars.append({'scar_id':sid,'expression':rows[0]['expression'],'tags':[t for t,_ in tag_counts.most_common()],'provenance_observations':dict(prov_counts),'source_plane_observations':dict(plane_counts),'authority':'DERIVED_INDEX_ONLY','occurrence_count':len(rows),'occurrences':rows})
    scars.sort(key=lambda r:(-r['occurrence_count'],r['expression'].casefold()))
    digest_subject={'files':files,'registries':registries}
    source_digest=_sha_text(json.dumps(digest_subject,sort_keys=True,separators=(',',':')))
    source_deficits=[]
    for reg in registries:
        for row in reg.get('sources',[]):
            if row.get('status')!='MATERIALIZED_VERIFIED':source_deficits.append({'source_plane':reg.get('source_plane'),'source_id':row.get('source_id'),'status':row.get('status'),'expected_sha256':row.get('expected_sha256'),'actual_sha256':row.get('actual_sha256')})
    return {'schema':SCHEMA,'generated_at_epoch':time.time(),'source_dirs':[str(x) for x in roots],'source_digest':source_digest,'file_count':len(files),'source_registries':registries,'source_deficits':source_deficits,'scar_count':len(scars),'occurrence_count':len(occ),'scars':scars,'authority':'DERIVED_INDEX_ONLY','mutation_authority':False}

def write_index(index:dict[str,Any],path:Path)->None:
    path.parent.mkdir(parents=True,exist_ok=True);tmp=path.with_suffix(path.suffix+'.tmp');tmp.write_text(json.dumps(index,indent=2,sort_keys=True)+'\n',encoding='utf-8');tmp.replace(path)
def load_index(path:Path)->dict[str,Any]|None:
    if not path.exists():return None
    try:return json.loads(path.read_text(encoding='utf-8'))
    except Exception:return None

def refresh_index(source_dir:Path|Iterable[Path],index_path:Path)->dict[str,Any]:
    fresh=collect_scars(source_dir);old=load_index(index_path)
    changed=not old or old.get('source_digest')!=fresh.get('source_digest')
    if changed:write_index(fresh,index_path)
    fresh['changed']=changed
    return fresh

def route_scars(index:dict[str,Any],context:str,*,limit:int=7)->dict[str,Any]:
    limit=max(1,min(int(limit),25));ctx=context.casefold();ctx_tokens=_tokens(ctx);ranked=[]
    stop={'that','this','with','from','into','must','shall','when','where','what','have','does','only','state','system'}
    for scar in index.get('scars',[]):
        expr=scar['expression'];expr_tokens={x for x in _tokens(expr) if len(x)>3 and x not in stop}
        expr_overlap=sorted(expr_tokens & ctx_tokens)
        score=len(expr_overlap)*12;reasons=[]
        if expr_overlap:reasons.append('expression:'+','.join(expr_overlap[:8]))
        # Tags are occurrence-local evidence. A tag inherited from an unrelated occurrence
        # must not make the entire semantic scar globally relevant.
        best_occ=None;best_occ_score=0;best_occ_reasons=[]
        for occ in scar.get('occurrences',[]):
            occ_score=0;occ_reasons=[]
            local_tags=[]
            for tag in occ.get('tags',[]):
                if tag in ctx_tokens or tag.replace('_',' ') in ctx:
                    occ_score+=20;local_tags.append(tag)
            if local_tags:occ_reasons.append('local-tags:'+','.join(sorted(local_tags)))
            local_tokens={x for x in _tokens((occ.get('heading') or '')+' '+(occ.get('context') or '')) if len(x)>4 and x not in stop}
            local_overlap=sorted(local_tokens & ctx_tokens)
            if local_overlap:
                occ_score+=min(20,len(local_overlap)*3);occ_reasons.append('local-context:'+','.join(local_overlap[:6]))
            if occ_score>best_occ_score:
                best_occ_score=occ_score;best_occ=occ;best_occ_reasons=occ_reasons
        score+=best_occ_score;reasons.extend(best_occ_reasons)
        prov=scar.get('provenance_observations',{})
        if prov.get('EARNED'):score+=8;reasons.append('earned-source')
        if prov.get('LAW'):score+=5;reasons.append('law-source')
        if score>0:
            ranked.append({'scar_id':scar['scar_id'],'expression':expr,'score':score,'tags':scar.get('tags',[]),'authority':scar.get('authority'),'provenance_observations':prov,'occurrence_count':int(scar.get('occurrence_count',1)),'best_occurrence':({'source':best_occ.get('source'),'line':best_occ.get('line'),'heading':best_occ.get('heading')} if best_occ else None),'reason':'; '.join(reasons)})
    ranked.sort(key=lambda x:(x['score'],len(_tokens(x['expression'])),x['expression']),reverse=True)
    selected=ranked[:limit]
    return {'schema':'mvf.scar-routing.v1','context':context[:3000],'selected':selected,'candidate_count':len(ranked),'scar_count':int(index.get('scar_count',0)),'ritual_dump_avoided':len(selected)<int(index.get('scar_count',0)),'authority':'DERIVED_ROUTING_ONLY','mutation_authority':False}
