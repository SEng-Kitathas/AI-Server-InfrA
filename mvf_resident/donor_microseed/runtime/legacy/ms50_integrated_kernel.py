from __future__ import annotations
from pathlib import Path
import sys,sqlite3,hashlib,json,time
PROJECT=Path(__file__).resolve().parents[3]
PKG=PROJECT/'embodiment/e09_specialist_packaging_v0_1'
sys.path.insert(0,str(PKG))
import packaging_core as pc
MODELS=PKG/'models'
TASKS=('circle','cross','xor')
PRIMARY={'circle':'TQ2','cross':'INT8','xor':'TQ2'}
QUALIFIED={('TQ2','circle'):True,('TQ2','cross'):False,('TQ2','xor'):True,('INT8','circle'):True,('INT8','cross'):True,('INT8','xor'):True}
FILES={('TQ2',t):MODELS/f'tq2_bias_{t}.bin' for t in TASKS}|{('INT8',t):MODELS/f'int8_{t}.bin' for t in TASKS}
HASHES={k:hashlib.sha256(v.read_bytes()).hexdigest() for k,v in FILES.items()}

def in_regime(x,y): return x and y and -12<=x<=12 and -12<=y<=12
class Kernel:
    def __init__(self,db=':memory:'):
        self.conn=sqlite3.connect(db)
        self.conn.execute('create table if not exists memory(k text, value text, valid_from int, recorded_at int, source text)')
        self.conn.execute('create table if not exists effects(effect_key text primary key,target text,value text,at int)')
        self.materialized={('TQ2','circle'),('INT8','cross'),('TQ2','xor')}
        self.qualified=dict(QUALIFIED)
        self.tool_registry={}
    def _artifact_ok(self,key):
        p=FILES[key]
        return p.exists() and hashlib.sha256(p.read_bytes()).hexdigest()==HASHES[key]
    def route(self,task,x,y,allow_cold=True):
        if task not in TASKS or not in_regime(x,y): return {'status':'UNKNOWN_OUT_OF_REGIME','authority':'NONE','evidence':[]}
        candidates=[]
        for model in ('TQ2','INT8'):
            k=(model,task)
            if self.qualified.get(k) and self._artifact_ok(k):
                candidates.append((FILES[k].stat().st_size,model,k))
        candidates.sort()
        if not candidates:return {'status':'UNKNOWN_NO_QUALIFIED_SPECIALIST','authority':'NONE','evidence':[]}
        _,model,k=candidates[0]
        if k not in self.materialized:
            if not allow_cold:return {'status':'UNAVAILABLE_NOT_MATERIALIZED','authority':'NONE','evidence':[f'QUALIFIED:{model}:{task}']}
            self.materialized.add(k)
        if model=='TQ2': label,score=pc.infer_tq2_slice(task,x,y)
        else: label,score=pc.infer_int8_slice(task,x,y)
        return {'status':'MODEL_OUTPUT','authority':'MODEL_OUTPUT_ONLY','model':model,'task':task,'label':label,'score':score,'evidence':[f'QUALIFIED:{model}:{task}',f'ARTIFACT:{HASHES[k]}']}
    def revoke(self,model,task): self.qualified[(model,task)]=False
    def qualify(self,model,task): self.qualified[(model,task)]=True
    def remember(self,k,value,valid_from,recorded_at,source):
        self.conn.execute('insert into memory values(?,?,?,?,?)',(k,json.dumps(value,sort_keys=True),valid_from,recorded_at,source));self.conn.commit()
    def read(self,k,now,max_age):
        row=self.conn.execute('select value,valid_from,recorded_at,source from memory where k=? order by recorded_at desc limit 1',(k,)).fetchone()
        if not row:return {'status':'UNKNOWN_NO_RECORD'}
        status='CURRENT' if now-row[2]<=max_age else 'RETAINED_NOT_CURRENT'
        return {'status':status,'value':json.loads(row[0]),'valid_from':row[1],'recorded_at':row[2],'source':row[3]}
    def qualify_tool(self,name,path):
        p=Path(path); self.tool_registry[name]={'path':str(p),'sha256':hashlib.sha256(p.read_bytes()).hexdigest()}
    def tool_current(self,name):
        d=self.tool_registry.get(name)
        if not d:return False
        p=Path(d['path']);return p.exists() and hashlib.sha256(p.read_bytes()).hexdigest()==d['sha256']
    def set_file(self,target,value,effect_key,authorized=True):
        if not authorized:return {'status':'DENY_AUTHORITY'}
        prior=self.conn.execute('select effect_key from effects where effect_key=?',(effect_key,)).fetchone()
        if prior:return {'status':'DUPLICATE_SUPPRESSED','effect_key':effect_key}
        Path(target).write_text(value)
        self.conn.execute('insert into effects values(?,?,?,?)',(effect_key,str(target),value,int(time.time())));self.conn.commit()
        return {'status':'EFFECT_APPLIED','effect_key':effect_key,'observed':Path(target).read_text()==value}

def self_test(tmp):
    k=Kernel(str(Path(tmp)/'k.db')); rows=[]
    rows.append(k.route('circle',9,1)['model']=='TQ2')
    rows.append(k.route('cross',9,9)['model']=='INT8')
    rows.append(k.route('circle',13,1)['status']=='UNKNOWN_OUT_OF_REGIME')
    k.revoke('TQ2','circle'); rows.append(k.route('circle',9,1)['model']=='INT8')
    k.revoke('INT8','circle'); rows.append(k.route('circle',9,1)['status']=='UNKNOWN_NO_QUALIFIED_SPECIALIST')
    k.remember('x',{'v':1},10,10,'S');rows.append(k.read('x',100,20)['status']=='RETAINED_NOT_CURRENT')
    p=Path(tmp)/'target';a=k.set_file(p,'on','E1');b=k.set_file(p,'on','E1');rows.append(a['status']=='EFFECT_APPLIED' and b['status']=='DUPLICATE_SUPPRESSED')
    return {'passed':sum(rows),'total':len(rows),'all_pass':all(rows)}
