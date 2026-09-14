"""Authority-neutral resource/consequence conflict relations for job concurrency."""
from __future__ import annotations
from typing import Any,Mapping

def _overlap(a:str,b:str)->bool:
 a=a.rstrip('/\\').lower();b=b.rstrip('/\\').lower();return a==b or a.startswith(b+'\\') or b.startswith(a+'\\') or a.startswith(b+'/') or b.startswith(a+'/')
def claims_conflict(a:Mapping[str,Any],b:Mapping[str,Any])->dict[str,Any]:
 if a.get('project_id')!=b.get('project_id') and a.get('domain')=='project' and b.get('domain')=='project':return {'status':'NON_CONFLICT','conflict':False,'authority':'NONE','reason':'DISTINCT_PROJECT_DOMAINS'}
 da,db=str(a.get('domain') or ''),str(b.get('domain') or '')
 if not da or not db:return {'status':'UNKNOWN','conflict':True,'authority':'NONE','reason':'DOMAIN_UNKNOWN'}
 if da!=db:return {'status':'NON_CONFLICT','conflict':False,'authority':'NONE','reason':'DISTINCT_DOMAINS'}
 ra,rb=str(a.get('resource') or ''),str(b.get('resource') or '')
 if not ra or not rb:return {'status':'UNKNOWN','conflict':True,'authority':'NONE','reason':'RESOURCE_UNKNOWN'}
 if da in {'git_index','git_refs','deployment','migration','artifact_registry','continuity_head','port','process_owner'}:
  same=ra.lower()==rb.lower();return {'status':'CONFLICT' if same else 'NON_CONFLICT','conflict':same,'authority':'NONE','reason':'SHARED_TRANSACTIONAL_RESOURCE' if same else 'DISTINCT_TRANSACTIONAL_RESOURCE'}
 if da=='path':
  overlap=_overlap(ra,rb);writes='WRITE' in {str(a.get('mode','')).upper(),str(b.get('mode','')).upper()};c=overlap and writes;return {'status':'CONFLICT' if c else 'NON_CONFLICT','conflict':c,'authority':'NONE','reason':'PATH_WRITE_OVERLAP' if c else 'PATH_COMPATIBLE'}
 return {'status':'UNKNOWN','conflict':True,'authority':'NONE','reason':'UNQUALIFIED_DOMAIN'}
def jobs_compatible(a:list[Mapping[str,Any]],b:list[Mapping[str,Any]])->dict[str,Any]:
 pairs=[claims_conflict(x,y) for x in a for y in b];bad=[x for x in pairs if x['conflict']];return {'compatible':not bad,'status':'PARALLEL_CANDIDATE' if not bad else ('SERIAL_UNKNOWN' if any(x['status']=='UNKNOWN' for x in bad) else 'SERIAL_CONFLICT'),'authority':'NONE','pairs':pairs}
