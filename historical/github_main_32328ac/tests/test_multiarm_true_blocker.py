from __future__ import annotations
import os,sys,tempfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'baseline'));from pcmmad_receiver.app_factory import create_app;from pcmmad_receiver.resource_claim_derivation import derive
def test_real_flask_request_context_derives_remote_agent_not_claimed_operator(monkeypatch):
 monkeypatch.setenv('GITHOME_API_KEY','agent');monkeypatch.setenv('PCMMAD_OPERATOR_API_KEY','operator');monkeypatch.setenv('PCMMAD_OPERATOR_EPOCH','9');app=create_app()
 @app.get('/_warfort_principal')
 def p():
  from flask import g;return g.pcmmad_principal
 c=app.test_client();r=c.get('/_warfort_principal',headers={'X-GitHome-Key':'agent','X-Claimed-Principal':'OPERATOR'});j=r.get_json();assert j['principal_class']=='REMOTE_AGENT' and j['max_scope']=='PROJECT'
def test_real_flask_request_context_derives_operator(monkeypatch):
 monkeypatch.setenv('GITHOME_API_KEY','agent');monkeypatch.setenv('PCMMAD_OPERATOR_API_KEY','operator');monkeypatch.setenv('PCMMAD_OPERATOR_EPOCH','9');app=create_app()
 @app.get('/_warfort_principal2')
 def p():
  from flask import g;return g.pcmmad_principal
 j=app.test_client().get('/_warfort_principal2',headers={'X-PCMMAD-Operator-Key':'operator'}).get_json();assert j['principal_class']=='OPERATOR' and j['max_scope']=='MACHINE' and j['principal_epoch']==9
def test_registry_mutation_claim_is_global_and_server_derived():
 r=derive({'name':'project.provision','effect_traits':['durable_mutation','project_registry_mutation']},{'project_id':'NEW','claims':[]});assert any(x['domain']=='project_registry' and x['resource']=='GLOBAL_PROJECT_REGISTRY' for x in r['claims'])
