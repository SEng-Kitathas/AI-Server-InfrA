"""Surface-specific grounded provenance composition. No universal attestation authority."""
from __future__ import annotations
from typing import Any,Mapping

def process_witness(info:Mapping[str,Any]|None)->dict[str,Any]:
 if not info:return {'status':'UNKNOWN','grounded':False,'reason':'PROCESS_UNOBSERVABLE'}
 required=('pid','creation_date','executable_path','command_fingerprint')
 if any(not info.get(k) for k in required):return {'status':'UNKNOWN','grounded':False,'reason':'PROCESS_IDENTITY_INCOMPLETE'}
 return {'status':'GROUNDED','grounded':True,'kind':'process','identity':{k:info[k] for k in required},'failure_domain':f"process:{info['pid']}:{info['creation_date']}"}
def source_witness(identity:Mapping[str,Any]|None)->dict[str,Any]:
 if not identity:return {'status':'UNKNOWN','grounded':False,'reason':'SOURCE_UNOBSERVABLE'}
 head=str(identity.get('source_head') or '');tree=str(identity.get('source_tree') or '');root=str(identity.get('source_root') or '')
 if not head or not tree or not root:return {'status':'UNKNOWN','grounded':False,'reason':'SOURCE_IDENTITY_INCOMPLETE'}
 return {'status':'GROUNDED','grounded':True,'kind':'source','identity':{'source_head':head,'source_tree':tree,'source_root':root},'lineage_id':f'git:{head}:{tree}'}
def contract_witness(card:Mapping[str,Any]|None)->dict[str,Any]:
 if not card:return {'status':'UNKNOWN','grounded':False,'reason':'CONTRACT_UNOBSERVABLE'}
 name=str(card.get('name') or '');digest=str(card.get('contract_digest') or '')
 if not name or len(digest)!=64:return {'status':'UNKNOWN','grounded':False,'reason':'CONTRACT_IDENTITY_INCOMPLETE'}
 return {'status':'GROUNDED','grounded':True,'kind':'contract','identity':{'name':name,'contract_digest':digest},'lineage_id':f'contract:{name}:{digest}'}
def compose_independence(left:Mapping[str,Any],right:Mapping[str,Any])->dict[str,Any]:
 if not left.get('grounded') or not right.get('grounded'):return {'status':'UNKNOWN','independent':False,'reason':'UNGROUNDED_WITNESS'}
 ld=left.get('failure_domain');rd=right.get('failure_domain');ll=left.get('lineage_id');rl=right.get('lineage_id')
 # Absence is not evidence of difference. Independence requires positively grounded distinct domains AND lineages.
 if not ld or not rd or not ll or not rl:return {'status':'UNKNOWN','independent':False,'reason':'INDEPENDENCE_DIMENSION_UNGROUNDED'}
 if ld==rd or ll==rl:return {'status':'CORRELATED','independent':False,'reason':'SHARED_LINEAGE_OR_FAILURE_DOMAIN'}
 return {'status':'INDEPENDENT','independent':True,'reason':'DISTINCT_GROUNDED_LINEAGE_AND_FAILURE_DOMAIN'}
