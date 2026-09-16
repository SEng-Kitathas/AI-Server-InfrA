from __future__ import annotations
import sys
from contextlib import nullcontext
from pathlib import Path
from unittest.mock import patch
import pytest
ROOT=Path(__file__).resolve().parents[1]; sys.path.insert(0,str(ROOT/'baseline'))
from pcmmad_receiver import lab_tools
from pcmmad_receiver import lab_tools_execution as lte
from pcmmad_receiver.execution_routes import ExecutionRequestError

def _registry():
    handlers={}; submitted=[]
    def register_tool(name,*args,**kwargs):
        def deco(fn): handlers[name]=fn; return fn
        return deco
    class E(Exception):
        def __init__(self,code,message,status=400): super().__init__(message); self.code=code; self.status=status
    lte.register_execution_tools(register_tool,error_cls=E,request_optional_positive_int=lambda value,default,**kwargs: default if value is None else int(value),resolve_cwd=lambda project_id,cwd:Path.cwd(),exec_env=lambda payload:{},finalize_job=lambda *args:{'project_id':args[0],'job_id':args[1],'status':'COMPLETED'},read_job=lambda project_id,job_id:{'project_id':project_id,'job_id':job_id,'status':'COMPLETED'},tail_text=lambda path,max_bytes:("",False),execution_modes={'one_shot'},max_output_bytes=1024,default_timeout_seconds=10,default_stdout_max_bytes=1024,default_stderr_max_bytes=1024,max_timeout_seconds=60,submit_job=lambda payload:submitted.append(dict(payload)) or {'project_id':payload['project_id'],'job_id':'job-x','status':'QUEUED'},terminate_job=lambda p,j:{'project_id':p,'job_id':j,'status':'TERMINATED'},utc_now=lambda:'now')
    return handlers,submitted,E

def test_async_submit_refuses_compat_no_lease_before_delegate():
    handlers,submitted,E=_registry()
    with patch.object(lte,'current_project_mutation_authority',return_value=None):
        with pytest.raises(E) as exc: handlers['execution.submit']({'project_id':'p','command':['python','-V']})
    assert exc.value.code=='PROJECT_MUTATION_AUTHORITY_REQUIRED' and exc.value.status==423 and submitted==[]

def test_async_submit_with_explicit_authority_still_delegates():
    handlers,submitted,_=_registry(); authority={'project_id':'p','mode':'lease','generation':1,'owner_id':'o','lease_id':'l'}
    with patch.object(lte,'current_project_mutation_authority',return_value=authority), patch.object(lte,'submission_mutation_binding',return_value=nullcontext()):
        result=handlers['execution.submit']({'project_id':'p','command':['python','-V']})
    assert result['job_id']=='job-x' and len(submitted)==1

def test_execution_request_error_maps_to_lab_error():
    err=ExecutionRequestError('IDEMPOTENCY_KEY_CONFLICT','different payload',409,existing_job_id='job-old')
    with patch.object(lab_tools,'submit_execution_job',side_effect=err):
        with pytest.raises(lab_tools.LabToolError) as exc: lab_tools._submit_execution_job_for_lab({'project_id':'p'})
    assert exc.value.error_code=='IDEMPOTENCY_KEY_CONFLICT' and exc.value.status==409 and exc.value.extra['existing_job_id']=='job-old'
