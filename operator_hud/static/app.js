const state={tools:[],filtered:[],category:'all',selected:null,status:null,pendingApproval:null,lastDispatch:null,hudToken:null,availabilityChecks:{},cockpitAnnunciation:null,cockpitTrends:{latency:[],failures:[]},lastDiagnostic:null};
const $=id=>document.getElementById(id);
const now=()=>new Date().toLocaleTimeString();

async function api(path,options={}){
  const timeoutMs=options.timeoutMs??5000; const fetchOptions={...options}; delete fetchOptions.timeoutMs;
  const controller=new AbortController(); const timer=setTimeout(()=>controller.abort(),timeoutMs);
  try{
    const headers={'Content-Type':'application/json',...(fetchOptions.headers||{})};
    if((fetchOptions.method||'GET').toUpperCase()!=='GET'&&state.hudToken) headers['X-PCMMAD-HUD-Token']=state.hudToken;
    const res=await fetch(path,{...fetchOptions,headers,cache:'no-store',signal:controller.signal});
    let data; try{data=await res.json();}catch{data={ok:false,error_code:'NON_JSON',message:`HTTP ${res.status}`};}
    data._http_status=res.status; return data;
  }catch(e){return {ok:false,error_code:'HUD_FETCH_FAILED',message:String(e),_http_status:0};}
  finally{clearTimeout(timer);}
}


function showToast(text,ok=true){const t=$('toast');t.textContent=text;t.className=`toast ${ok?'good':'bad'}`;setTimeout(()=>t.classList.add('hidden'),3500);}
function setLamp(id,mode){const el=$(id);el.className=`lamp ${mode}`;}
function fmtTime(ts){if(!ts)return '';return new Date(ts*1000).toLocaleTimeString();}
function escapeHtml(s){return String(s??'').replace(/[&<>'"]/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;',"'":'&#39;','"':'&quot;'}[c]));}
function uid(){return `ui-${Date.now()}-${Math.random().toString(16).slice(2,8)}`;}

function deriveCockpitPicture(data,nowEpochSeconds=Date.now()/1000){
  const h=data.hud||{},r=data.receiver||{},b=data.browser_bridge||{},j=data.journal||{},n=data.ngrok||{},d=data.daemon||{},ready=data.readiness||{};
  const checked=Number(data.checked_at); const age=Number.isFinite(checked)?Math.max(0,nowEpochSeconds-checked):Infinity;
  const stale=!Number.isFinite(checked)||age>15||data.error_code==='HUD_FETCH_FAILED';
  const coreReady=ready.core_ready!==undefined?!!ready.core_ready:!!(h.ok&&r.ok&&j.ok);
  const optionalDegraded=Array.isArray(ready.optional_degraded)?[...ready.optional_degraded]:(!b.ok?['browser_bridge']:[]);
  if(b.ok&&b.armed&&!b.ready_for_browser_automation&&!optionalDegraded.includes('browser_armed_not_ready'))optionalDegraded.push('browser_armed_not_ready');
  let level='normal',label='NORMAL',faultTitle='Required planes nominal',chain='HUD → Receiver → Journal evidence chain is available.',cue='No operator action required.';
  if(stale){
    level='warning';label='WARNING';faultTitle='Status evidence stale or unavailable';
    chain=`Last trustworthy cockpit sample is ${Number.isFinite(age)?Math.round(age)+'s old':'unavailable'}; embedded component state is not sufficient for readiness.`;
    cue='Refresh status and re-establish current evidence before mutation or recovery decisions.';
  }else if(!coreReady){
    level='warning';label='WARNING';
    if(!r.ok){
      faultTitle='Receiver unavailable';
      chain=`HUD ${h.ok?'ONLINE':'DEGRADED'} → transport ${n.ok?'ONLINE':'UNKNOWN/DOWN'} → Receiver DOWN${r.http_status?` (HTTP ${r.http_status})`:''} → native dispatch/readback unavailable.`;
      cue='Inspect supervisor/restart state and correlated Windows / Defender evidence before mutation.';
    }else if(!j.ok){
      faultTitle='Forensic journal degraded';
      chain=`Receiver ONLINE → journal ${j.ok?'READY':'DEGRADED'} → durable consequence/readback evidence is incomplete.`;
      cue='Preserve runtime state; inspect journal load/write evidence before relying on dispatch history.';
    }else{
      faultTitle='Required control-plane evidence degraded';chain='One or more required planes are non-current; isolate the failed plane before acting.';cue='Use the failing plane evidence and recovery state; do not infer readiness from surviving components.';
    }
  }else if(optionalDegraded.length){
    level='caution';label='CAUTION';faultTitle='Core ready; optional degradation isolated';chain=`Required planes nominal → optional ${optionalDegraded.join(', ')} degraded.`;cue='Continue core work; inspect optional plane only if the current task depends on it.';
  }
  const evidence=data.failure_evidence;
  if(evidence?.security_signal_present){cue+=evidence.causation_established?' Security evidence is causally linked.':' Security signal present; causation is NOT established.';}
  return {h,r,b,j,n,d,ready,age,stale,coreReady,optionalDegraded,level,label,faultTitle,chain,cue};
}

function deriveDiagnosticPacket(data,picture=deriveCockpitPicture(data)){
  const facts=[],inferences=[],unknowns=[],informedBy=[],nextEvidence=[];
  const addFact=(label,text,source)=>facts.push({truth:'FACT',label,text,source});
  const addInference=(truth,text,basis)=>inferences.push({truth,label:truth==='INFERRED'?'Triangulation':'Inference guard',text,basis});
  const addUnknown=(text,discriminator)=>unknowns.push({truth:'UNKNOWN',text,discriminator});
  const addSource=(name,detail)=>{if(name&&!informedBy.some(x=>x.name===name))informedBy.push({name,detail:detail||''});};
  const h=picture.h||{},r=picture.r||{},n=picture.n||{},d=picture.d||{},j=picture.j||{},b=picture.b||{};
  addSource('HUD /api/status','cockpit aggregation/currentness');
  addFact('Currentness',picture.stale?'STALE / UNTRUSTED':`${Math.round(picture.age)}s old`,'HUD /api/status');
  addFact('HUD',h.ok?'ONLINE':'DEGRADED','HUD self-status');
  addFact('Transport',n.configured?(n.ok?`${n.tunnel_count||1} tunnel(s) online`:'DOWN'):'STANDBY','ngrok /api/tunnels');
  addFact('Receiver',r.ok?'ONLINE':`DOWN${r.http_status?` · HTTP ${r.http_status}`:''}`,'Receiver health probe');
  addFact('Journal',j.ok?'DURABLE':'DEGRADED','HUD journal state');
  addFact('Daemon',d.configured?(d.ok?'ONLINE':'DEGRADED'):'STANDBY','Daemon /status');
  addFact('Browser',!b.ok?'OPTIONAL / DEGRADED':(b.armed?(b.ready_for_browser_automation?'ONLINE · ARMED':'ONLINE · ARMED / NOT READY'):'ONLINE · BLOCKED'),'Browser bridge health + security gate');
  const ha=data.supervisor_budgets||{};const haSummary=ha.summary||{};addFact('HA budget',haSummary.status?`${haSummary.status}${haSummary.remaining===null||haSummary.remaining===undefined?'':` · ${haSummary.remaining}/${haSummary.max_restarts} remaining`}`:'UNKNOWN','Supervisor failure/hold/receipt state');
  if(n.configured)addSource('ngrok /api/tunnels','transport/tunnel evidence');
  addSource('Receiver health probe','body/control-plane evidence');
  addSource('HUD journal','dispatch/consequence evidence');
  if(d.configured)addSource('Daemon /status','resident cognition/currentness');
  if(b.configured!==false)addSource('Browser bridge /health','optional browser evidence');

  if(picture.stale){
    addInference('INFERENCE BLOCKED','Causal triangulation is suspended because the status sample is stale or unavailable.','Currentness boundary');
    addUnknown('Current component state','Refresh /api/status and compare source timestamps before causal reasoning.');
    nextEvidence.push('Refresh HUD /api/status and confirm checked_at currentness.');
  }else{
    if(!r.ok&&n.ok){
      addInference('INFERRED','Transport is alive while Receiver is unavailable; the observed break is downstream of tunnel establishment and upstream of native dispatch/readback.','Transport ONLINE + Receiver DOWN');
      addUnknown('Receiver failure mechanism','Inspect exact Receiver process identity, scheduled task/supervisor state, maintenance hold and restart budget.');
      nextEvidence.push('Inspect Receiver process/task/supervisor identity and restart budget.');
      nextEvidence.push('Query windows.failure_evidence.inspect around the failure window.');
    }else if(!r.ok&&!n.ok){
      addInference('INFERRED','Transport and Receiver are both unavailable; current observations do not establish which failed first.','Transport DOWN + Receiver DOWN');
      addUnknown('Failure ordering','Compare ngrok process/API timestamps with Receiver process/task timestamps.');
      nextEvidence.push('Inspect ngrok and Receiver process creation identities and Windows event timestamps.');
    }
    if(r.ok&&!j.ok){
      addInference('INFERRED','Execution/control may be live while durable consequence evidence is incomplete.','Receiver ONLINE + Journal DEGRADED');
      addUnknown('Journal degradation mechanism','Inspect journal load/write error and storage/permission state.');
      nextEvidence.push('Inspect journal error/readback before trusting dispatch history.');
    }
    if(picture.coreReady&&picture.optionalDegraded.length){
      addInference('INFERRED','Required core remains ready; optional degradation only matters if the active task depends on that plane.','Core ready + optional degraded');
      nextEvidence.push('Inspect the optional plane only if current work depends on it.');
    }
    if(b.ok&&b.armed&&!b.ready_for_browser_automation){
      addUnknown('Browser armed but automation not ready','Verify Playwright package/runtime and configured browser channel before browser actuation.');
      nextEvidence.push('Check browser bridge Playwright readiness and default browser channel.');
    }
    if(d.configured&&!d.ok&&r.ok){
      addInference('INFERRED','Resident intelligence is degraded independently of the Receiver body.','Receiver ONLINE + Daemon DEGRADED');
      addUnknown('Daemon failure mechanism','Inspect Daemon health, host lock, plane audit and last cycle error.');
      nextEvidence.push('Inspect Daemon /health, /status, host lock and plane audit.');
    }
  }

  const evidence=data.failure_evidence;
  if(evidence?.security_signal_present){
    addFact('Security telemetry','Security signal present','Windows / Defender failure evidence');addSource('Windows / Defender failure evidence','security telemetry correlation');
    if(evidence.causation_established)addInference('INFERRED','Security evidence is marked causally linked by the resident evidence packet.','failure_evidence.causation_established=true');
    else{addInference('INFERENCE BLOCKED','A security signal exists, but causation is not established. Do not promote it to root cause.','SECURITY PRODUCT EVENT != CAUSE');addUnknown('Security causal role','Correlate event time/resource/process identity with the failing process transition.');}
  }

  const daemonStatus=d.status||{};
  const surfaces=daemonStatus?.continuity_enforcement?.surfacing_plan?.selected||[];
  for(const item of surfaces.slice(0,8))addSource(`continuity:${item.surface}`,item.reason||item.authority||'surfaced by resident');
  const scars=(data.scar_intelligence?.applicable||[]).slice(0,5);
  for(const scar of scars){if(scar.best_occurrence?.source)addSource(`scar:${scar.best_occurrence.source}`,scar.reason||'applicable scar occurrence');}
  const haWorkloads=data.supervisor_budgets?.workloads||{};
  for(const [key,row] of Object.entries(haWorkloads)){
    if(row.state_status&&row.state_status!=='MISSING')addSource(`ha:${key}`,`${row.state_status} · ${row.restart_events}/${row.max_restarts} restarts in window`);
    if(row.hold?.hold){addUnknown(`${row.name} maintenance hold active`,row.hold.reason||'Inspect supervisor maintenance-hold record.');nextEvidence.push(`Inspect ${row.name} maintenance-hold expiry/reason before expecting automatic recovery.`);}
    if(row.state_status==='CORRUPT_HOLD'){addUnknown(`${row.name} restart budget corrupt-hold`,'Inspect and repair supervisor failure-state provenance; do not reset budget silently.');nextEvidence.push(`Inspect ${row.name} supervisor failure state before restart.`);}
    if(Number(row.remaining)===0&&row.state_status!=='MISSING'&&row.state_status!=='CORRUPT_HOLD'){addUnknown(`${row.name} restart budget exhausted`,'Inspect crash-loop evidence before manual restart or promotion.');}
  }
  const scarDeficits=(data.scar_intelligence?.source_deficits||[]).slice(0,8);
  for(const deficit of scarDeficits){addUnknown('Scar-source coverage incomplete',`${deficit.source_id||'registered source'} · ${deficit.status||'unknown status'}`);addSource(`scar-source:${deficit.source_id||'unknown'}`,deficit.status||'source deficit');}
  if(scarDeficits.length)nextEvidence.push('Materialize/verify registered scar sources before claiming complete scar coverage.');

  const topology={
    nodes:[
      {id:'hud',label:'HUD',state:picture.stale?'unknown':(h.ok?'good':'bad')},
      {id:'transport',label:'TRANSPORT',state:picture.stale||!n.configured?'unknown':(n.ok?'good':'bad')},
      {id:'receiver',label:'RECEIVER',state:picture.stale?'unknown':(r.ok?'good':'bad')},
      {id:'daemon',label:'DAEMON',state:picture.stale||!d.configured?'unknown':(d.ok?'good':'bad')},
      {id:'journal',label:'JOURNAL',state:picture.stale?'unknown':(j.ok?'good':'bad')},
      {id:'browser',label:'BROWSER',state:picture.stale?'unknown':(b.ok?'good':'degraded')},
    ],
    edges:[['hud','transport'],['transport','receiver'],['receiver','daemon'],['daemon','journal'],['journal','browser']],
  };
  return {schema:'pcmmad.hud-diagnostic.v1',severity:picture.label,title:picture.faultTitle,summary:picture.chain,currentness:{stale:picture.stale,age_seconds:picture.age},facts,inferences,unknowns,informedBy,scars,nextEvidence,topology,mutation_authority:false};
}

function renderDiagnosticList(id,rows,emptyText){
  const root=$(id);if(!root)return;root.innerHTML='';
  if(!rows?.length){root.innerHTML=`<div class="diagnostic-empty">${escapeHtml(emptyText)}</div>`;return;}
  for(const row of rows){const div=document.createElement('div');div.className='diagnostic-row';const truth=row.truth?`<span class="truth-tag ${row.truth.toLowerCase().replace(/\s+/g,'-')}">${escapeHtml(row.truth)}</span>`:'';const title=escapeHtml(row.label||row.text||'');const text=row.label&&row.text?`<div>${escapeHtml(row.text)}</div>`:'';const foot=row.source||row.basis||row.discriminator?`<small>${escapeHtml(row.source||row.basis||row.discriminator)}</small>`:'';div.innerHTML=`${truth}<strong>${title}</strong>${text}${foot}`;root.appendChild(div);}
}

function renderDiagnosticTopology(packet){
  const root=$('diagnosticTopology');if(!root)return;root.innerHTML='';
  const map=document.createElement('div');map.className='diagnostic-map';
  packet.topology.nodes.forEach((node,i)=>{const n=document.createElement('span');n.className=`diagnostic-node ${node.state}`;n.textContent=node.label;map.appendChild(n);if(i<packet.topology.nodes.length-1){const edge=document.createElement('span');edge.className='diagnostic-edge';edge.textContent='→';map.appendChild(edge);}});root.appendChild(map);
}

async function toggleBrowserGate(){
  const armed=!!state.status?.browser_bridge?.armed;const desired=armed?'BLOCKED':'ARMED';const result=await api('/api/browser/gate',{method:'POST',body:JSON.stringify({state:desired}),timeoutMs:5000});
  if(!result.ok){showToast(`Browser gate ${desired} failed: ${result.error_code||result.message||'unknown error'}`,false);return;}
  showToast(`Browser actuation ${desired}`);await refreshStatus();
}

function openDiagnostic(){
  const data=state.status||{ok:false,error_code:'HUD_FETCH_FAILED'};const picture=deriveCockpitPicture(data);const packet=deriveDiagnosticPacket(data,picture);state.lastDiagnostic=packet;
  $('diagnosticTitle').textContent=packet.title;$('diagnosticSeverity').textContent=packet.severity;$('diagnosticSeverity').className=`diagnostic-severity ${packet.severity.toLowerCase()}`;$('diagnosticSummary').textContent=packet.summary;renderDiagnosticTopology(packet);
  renderDiagnosticList('diagnosticFacts',packet.facts,'No direct facts available.');renderDiagnosticList('diagnosticInferences',packet.inferences,'No inference needed.');renderDiagnosticList('diagnosticUnknowns',packet.unknowns,'No unresolved discriminator identified.');
  const sources=$('diagnosticSources');sources.innerHTML='';packet.informedBy.forEach(x=>{const chip=document.createElement('span');chip.className='diagnostic-chip';chip.textContent=x.name;chip.title=x.detail||x.name;sources.appendChild(chip);});
  renderDiagnosticList('diagnosticScars',packet.scars.map(x=>({truth:'SCAR',label:x.expression,text:x.reason||'',source:x.best_occurrence?.source||''})),'No applicable routed scar.');renderDiagnosticList('diagnosticNext',packet.nextEvidence.map(x=>({truth:'NEXT',text:x})),'No additional evidence route required.');$('diagnosticModal').classList.remove('hidden');
}

function closeDiagnostic(){$('diagnosticModal').classList.add('hidden');}

function advanceAnnunciation(previous,picture,nowEpochSeconds=Date.now()/1000){
  const identity=`${picture.level}|${picture.faultTitle}`;
  if(!previous)return {identity,level:picture.level,faultTitle:picture.faultTitle,since:nowEpochSeconds,changed:true,cleared:null};
  if(previous.identity===identity)return {...previous,changed:false};
  const cleared=(previous.level==='warning'||previous.level==='caution')&&picture.level==='normal'?{level:previous.level,faultTitle:previous.faultTitle,at:nowEpochSeconds}:null;
  return {identity,level:picture.level,faultTitle:picture.faultTitle,since:nowEpochSeconds,changed:true,cleared};
}

function trendDirection(values,lowerIsBetter=true){
  if(!Array.isArray(values)||values.length<3)return '→';
  const recent=values.slice(-3); const delta=recent[2]-recent[0];
  if(Math.abs(delta)<0.5)return '→';
  const improving=lowerIsBetter?delta<0:delta>0; return improving?'↓':'↑';
}

function pushTrend(values,value,max=12){
  if(Number.isFinite(Number(value)))values.push(Number(value));
  while(values.length>max)values.shift(); return values;
}

function setSynopticNode(id,ok,label,degraded=false,unknown=false){
  const node=$(id); if(!node)return;
  node.className=`synoptic-node ${unknown?'unknown':(ok?(degraded?'degraded':'good'):'bad')}`;
  const value=node.querySelector('strong'); if(value)value.textContent=label;
}

function renderCockpitStatus(data){
  const picture=deriveCockpitPicture(data); const {h,r,b,j,n,d,coreReady,optionalDegraded,level,label,faultTitle,chain,cue,stale}=picture;
  const ann=advanceAnnunciation(state.cockpitAnnunciation,picture);state.cockpitAnnunciation=ann;
  const assurance=$('cockpitAssurance'),modeDetail=$('cockpitModeDetail'),master=$('masterAnnunciator'),masterLabel=$('masterAnnunciatorLabel');
  if(master)master.className=`master-annunciator ${level}`;
  if(masterLabel)masterLabel.textContent=label;
  const masterMeta=$('masterAnnunciatorMeta');if(masterMeta){const age=Math.max(0,Math.round(Date.now()/1000-ann.since));masterMeta.textContent=ann.cleared?`cleared ${ann.cleared.level.toUpperCase()} · monitoring`:`${ann.changed?'new':'active'} · ${age}s`;}
  if(assurance)assurance.textContent=stale?'STATUS STALE · CURRENTNESS REQUIRED':coreReady?(optionalDegraded.length?'CORE READY · OPTIONAL DEGRADED':'CORE READY · REQUIRED PLANES NOMINAL'):'CORE DEGRADED · REQUIRED EVIDENCE LOST';
  if(modeDetail)modeDetail.textContent=stale?'do not trust embedded green states':coreReady?(optionalDegraded.length?`${optionalDegraded.length} optional plane${optionalDegraded.length===1?'':'s'} isolated`:'machine-truth path available'):'recovery / fault isolation mode';
  const optional=$('cockpitOptional');if(optional)optional.textContent=optionalDegraded.length?`${optionalDegraded.length} DEGRADED`:'NOMINAL';
  setSynopticNode('synHud',!!h.ok,h.ok?'ONLINE':'DOWN',false,stale);
  setSynopticNode('synNgrok',!!n.ok,n.ok?`${n.tunnel_count||1} TUNNEL${(n.tunnel_count||1)===1?'':'S'}`:(n.configured?'DOWN':'STANDBY'),false,!n.configured||stale);
  setSynopticNode('synReceiver',!!r.ok,r.ok?'ONLINE':'DOWN',false,stale);
  setSynopticNode('synDaemon',!!d.ok,d.configured?(d.ok?'ONLINE':'DEGRADED'):'STANDBY',d.configured&&!d.ok,!d.configured||stale);
  setSynopticNode('synJournal',!!j.ok,j.ok?'DURABLE':'DEGRADED',!j.ok,stale);
  const browserLabel=!b.ok?'OPTIONAL':(b.armed?(b.ready_for_browser_automation?'ARMED':'ARMED / NOT READY'):'BLOCKED');
  setSynopticNode('synBrowser',!!b.ok,browserLabel,!!(b.ok&&b.armed&&!b.ready_for_browser_automation),!b.ok&&stale);
  const synBrowser=$('synBrowser');if(synBrowser&&b.ok&&!b.armed)synBrowser.className='synoptic-node blocked diagnostic-trigger';
  const ft=$('cockpitFaultTitle');if(ft)ft.textContent=faultTitle; const cc=$('cockpitCausalChain');if(cc)cc.textContent=chain; const rc=$('cockpitRecoveryCue');if(rc)rc.textContent=cue;
  const completed=(data.events||[]).filter(e=>e.kind==='dispatch_completed');const failureCount=completed.filter(e=>!e.ok).length;
  pushTrend(state.cockpitTrends.latency,data.latency_ms);pushTrend(state.cockpitTrends.failures,failureCount);
  const tsa=$('trendStatusAge');if(tsa)tsa.textContent=Number.isFinite(picture.age)?`${Math.round(picture.age)}s`:'--';
  const tl=$('trendLatency');if(tl)tl.textContent=Number.isFinite(Number(data.latency_ms))?`${Math.round(Number(data.latency_ms))}ms`:'--';
  const tld=$('trendLatencyDir');if(tld)tld.textContent=trendDirection(state.cockpitTrends.latency,true);
  const tf=$('trendFailures');if(tf)tf.textContent=String(failureCount);const tfd=$('trendFailuresDir');if(tfd)tfd.textContent=trendDirection(state.cockpitTrends.failures,true);
  const tt=$('trendTransport');if(tt)tt.textContent=n.ok?`${n.tunnel_count||1} UP`:(n.configured?'DOWN':'STANDBY');
  const tb=$('trendBrowser');if(tb)tb.textContent=!b.ok?'DOWN':(b.armed?(b.ready_for_browser_automation?'ARMED':'ARMED !READY'):'BLOCKED');
  const hb=data.supervisor_budgets?.summary||{};const thb=$('trendHaBudget');if(thb)thb.textContent=hb.status==='AVAILABLE'?`${hb.remaining}/${hb.max_restarts}`:(hb.status||'STANDBY');
  const td=$('trendDaemon');if(td)td.textContent=d.configured?(d.ok?`${d.status?.cycle_count??'--'} CYCLES`:'DEGRADED'):'STANDBY';

  const scarPacket=data.scar_intelligence||data.daemon?.scar_intelligence||data.resident?.scar_intelligence; const routed=Array.isArray(scarPacket?.applicable)?scarPacket.applicable:[];
  const scarBox=$('cockpitScar'),scarText=$('cockpitScarText'),scarReason=$('cockpitScarReason');
  if(scarBox&&routed.length){const scar=routed[0];scarBox.hidden=false;if(scarText)scarText.textContent=scar.expression||'Applicable scar';if(scarReason)scarReason.textContent=scar.reason||`routed from ${scar.occurrence_count||1} source occurrence${scar.occurrence_count===1?'':'s'}`;}else if(scarBox){scarBox.hidden=true;}
  const sessions=data.browser_sessions||[];const sessionSummary=$('cockpitSessionSummary');if(sessionSummary){sessionSummary.innerHTML=!b.ok?'Optional browser bridge unavailable.':(!b.armed?`<strong>BLOCKED</strong> · bridge online · actuation disabled`:(!b.ready_for_browser_automation?`<strong>ARMED</strong> · automation runtime not ready`:(sessions.length?`<strong>${sessions.length}</strong> active session${sessions.length===1?'':'s'}<br>${sessions.slice(0,3).map(x=>escapeHtml(x.session_id||x.id||'session')).join('<br>')}`:`<strong>ARMED</strong> · automation ready · no active sessions`)));}
  const gateState=$('browserGateState');if(gateState)gateState.textContent=b.armed?'ARMED':'BLOCKED';const gateBtn=$('browserGateToggle');if(gateBtn){gateBtn.textContent=b.armed?'BLOCK':'ARM';gateBtn.className=`gate-control ${b.armed?'armed':'blocked'}`;gateBtn.title=b.armed?'Block browser actuation immediately':'Explicitly arm browser actuation';}
}

function renderCockpitTools(){
  const toolCount=$('cockpitToolCount'),familyCount=$('cockpitFamilyCount'),summary=$('cockpitCapabilitySummary');
  if(!toolCount||!familyCount||!summary)return;
  const families=new Set(state.tools.map(t=>t.category||'other'));
  const mutating=state.tools.filter(t=>t.mutating).length;
  const approvals=state.tools.filter(toolNeedsApproval).length;
  const dynamic=state.tools.filter(t=>t.availability?.mode==='dynamic').length;
  const unavailable=state.tools.filter(t=>String(t.availability?.status||'').toLowerCase()==='unavailable').length;
  toolCount.textContent=String(state.tools.length);
  familyCount.textContent=String(families.size);
  summary.innerHTML=`<strong>${state.tools.length}</strong> native tools<br><strong>${mutating}</strong> mutating · <strong>${approvals}</strong> approval-gated<br><strong>${dynamic}</strong> dynamic availability${unavailable?` · <strong>${unavailable}</strong> unavailable`:''}`;
}

function renderStatus(data){
  state.status=data;
  const h=data.hud||{},r=data.receiver||{},b=data.browser_bridge||{},j=data.journal||{},n=data.ngrok||{},ready=data.readiness||{};
  setLamp('hudLamp',h.ok?'good':'bad');$('hudState').textContent=h.ok?'ONLINE':'DOWN';$('hudDetail').textContent=h.ok?`${h.host}:${h.port}`:'HUD unavailable';
  setLamp('receiverLamp',r.ok?'good':'bad');$('receiverState').textContent=r.ok?'ONLINE':'DOWN';$('receiverDetail').textContent=r.ok?`${r.tool_count??'?'} live tools · HTTP ${r.http_status}`:`HTTP ${r.http_status??'?'}`;
  setLamp('bridgeLamp',b.ok?'good':'bad');$('bridgeState').textContent=b.ok?'ONLINE':'DOWN';$('bridgeDetail').textContent=b.ok?`PID ${b.detail?.pid??'?'} · ${b.detail?.sessions??0} sessions`:(b.detail?.error||'bridge unavailable');
  setLamp('journalLamp',j.ok?'good':'bad');$('journalState').textContent=j.ok?'DURABLE':'DEGRADED';$('journalDetail').textContent=j.ok?`${j.memory_rows??0} recent rows · ${j.malformed_rows_skipped??0} malformed skipped`:(j.load_error||j.write_error||`journal degraded · ${j.malformed_rows_skipped??0} malformed skipped`);
  const sessions=data.browser_sessions||[];$('sessionCount').textContent=String(sessions.length);setLamp('sessionLamp',b.ok?'good':'bad');
  const coreReady=ready.core_ready!==undefined?!!ready.core_ready:!!(h.ok&&r.ok&&j.ok);
  const optionalDegraded=Array.isArray(ready.optional_degraded)?ready.optional_degraded:(!b.ok?['browser_bridge']:[]);
  const corePartiallyAlive=!!(h.ok&&(r.ok||j.ok));
  const g=$('globalState');
  if(coreReady&&optionalDegraded.length){g.className='state-pill degraded';g.textContent='CORE READY · OPTIONAL DEGRADED';}
  else if(coreReady){g.className='state-pill good';g.textContent='CORE READY';}
  else if(corePartiallyAlive){g.className='state-pill degraded';g.textContent='CORE DEGRADED';}
  else{g.className='state-pill bad';g.textContent='CONTROL PLANE DOWN';}
  $('lastRefresh').textContent=`checked ${now()} · ${data.latency_ms??'?'} ms`;
  renderCockpitStatus(data); renderSessions(sessions); renderEvents(data.events||[]);
}

async function refreshStatus(){
  const d=await api('/api/status',{timeoutMs:5000}); renderStatus(d);
  const liveCount=d.receiver?.tool_count;
  if(d.receiver?.ok && Number.isInteger(liveCount) && state.tools.length && liveCount!==state.tools.length){
    $('toolCount').textContent=`catalog stale: ${state.tools.length} cached / ${liveCount} live`;
    await loadTools();
  }else if(!d.receiver?.ok && state.tools.length){
    $('toolCount').textContent=`${state.tools.length} cached tools · receiver down`;
  }
  return d;
}

function renderSessions(rows){
  const box=$('sessionList'); const sel=$('uploadSession'); if(sel){sel.innerHTML='<option value="">Select session</option>'+rows.map(r=>`<option value="${escapeHtml(r.session_id||r.id||'')}">${escapeHtml(r.session_id||r.id||'')}</option>`).join('');}
  if(!rows.length){box.innerHTML='<div class="empty-note">No active browser sessions.</div>';return;}
  box.innerHTML=rows.map(s=>`<div class="session-row"><div><div class="session-title">${escapeHtml(s.session_id||s.id||'session')}</div><div class="session-meta">${escapeHtml(s.url||s.current_url||'')} ${s.profile_name?`· ${escapeHtml(s.profile_name)}`:''}</div></div><button class="secondary" data-stop-session="${escapeHtml(s.session_id||s.id||'')}">Stop…</button></div>`).join('');
  box.querySelectorAll('[data-stop-session]').forEach(btn=>btn.onclick=()=>{const t=state.tools.find(x=>x.name==='browser.session.stop'); if(!t)return showToast('browser.session.stop unavailable',false); dispatchTool(t,{session_id:btn.dataset.stopSession,timeout_seconds:20});});
}

function renderEvents(events){
  const completed=events.filter(e=>e.kind==='dispatch_completed');
  const failures=completed.filter(e=>!e.ok);
  $('failureCount').textContent=String(failures.length);
  $('failures').className=failures.length?'stack':'stack empty-note';
  $('failures').innerHTML=failures.length?failures.slice(0,6).map(e=>`<div class="failure-row"><strong>${escapeHtml(e.tool_name)}</strong><div class="session-meta">${fmtTime(e.ts)} · HTTP ${e.http_status} · ${escapeHtml(e.error_code||'unspecified failure')}</div></div>`).join(''):'No HUD dispatch failures recorded.';
  const rows=completed.slice(0,4);
  $('recentActivity').innerHTML=rows.length?rows.map(eventRow).join(''):'<div class="empty-note">No HUD dispatches yet.</div>';
  $('activityTable').innerHTML=completed.length?completed.map(eventRow).join(''):'<div class="empty-note">No HUD dispatch history yet.</div>';
}

function eventRow(e){const ids=[e.request_id,e.dispatch_id?`dispatch ${e.dispatch_id.slice(0,12)}`:null].filter(Boolean).join(' · ');return `<div class="event-row"><span>${fmtTime(e.ts)}</span><span><span class="event-kind">${escapeHtml(e.tool_name)}</span><br><span class="muted">${escapeHtml(ids)}</span></span><span class="${e.ok?'event-ok':'event-bad'}">${e.ok?'SUCCESS':'FAILED'}</span><span>${e.elapsed_ms??'?'} ms</span></div>`;}

function toolNeedsApproval(t){if(t?.effective_approval_required!==undefined)return !!t.effective_approval_required;return !!t?.approval_required||!!t?.mutating||['high','critical'].includes(String(t?.danger_tier||'').toLowerCase());}
function availabilityClass(a){const status=String(a?.status||'unknown').toLowerCase();return ['available','unavailable','degraded'].includes(status)?`availability-${status}`:'availability-unknown';}
function availabilityLabel(t){const a=t?.availability||{};if(!a.mode)return 'availability unspecified';return `${a.mode} · ${a.status||'unknown'}`;}
function badgeMarkup(t){const a=t?.availability||{};return `<span class="badge ${t.mutating?'mutate':'read'}">${t.mutating?'mutating':'read'}</span><span class="badge ${toolNeedsApproval(t)?'approve':'read'}">${toolNeedsApproval(t)?'approval':'no approval'}</span><span class="badge ${String(t.danger_tier).toLowerCase()==='critical'?'critical':'read'}">${escapeHtml(t.danger_tier||'unknown')}</span><span class="badge ${availabilityClass(a)}">${escapeHtml(availabilityLabel(t))}</span>`;}

function currentAvailabilityCheck(t){
  const checked=state.availabilityChecks[t?.name]||null;if(!checked)return null;
  const cardDigest=String(t?.contract_digest||''),checkedDigest=String(checked?.contract_digest||'');
  if(!cardDigest||!checkedDigest||cardDigest!==checkedDigest){delete state.availabilityChecks[t?.name];return null;}
  return checked;
}
function renderAvailability(t){
  const a=t?.availability||{}; const checked=currentAvailabilityCheck(t);
  const mode=a.mode||'unspecified', staticStatus=a.status||'unknown';
  $('toolAvailabilityState').textContent=`${mode} · ${staticStatus}`;
  let detail=`Runtime card basis: ${a.basis||'unspecified'}`;
  if(a.scope)detail+=` · scope: ${a.scope}`;
  if(checked){
    detail=`Current Runtime check: ${checked.status||'unknown'} · basis: ${checked.basis||'unspecified'} · ${checked.checked_at||'time unavailable'}`;
    if(Array.isArray(checked.blockers)&&checked.blockers.length)detail+=` · blockers: ${checked.blockers.join(', ')}`;
  }
  $('toolAvailabilityDetail').textContent=detail;
  const btn=$('checkAvailabilityBtn');
  const checkable=!!(t&&a.mode==='dynamic'&&a.probe_supported);
  btn.classList.toggle('hidden',!checkable);btn.disabled=false;btn.textContent='Check current availability';
}

async function checkSelectedAvailability(){
  const t=state.selected;if(!t)return;
  const a=t.availability||{};if(a.mode!=='dynamic'||!a.probe_supported)return showToast(`${t.name}: no dynamic provider probe`,false);
  const btn=$('checkAvailabilityBtn');btn.disabled=true;btn.textContent='Checking…';
  const body={tool_name:'lab.capabilities.availability',payload:{tool_names:[t.name]},request_id:uid()};
  const data=await api('/api/dispatch',{method:'POST',body:JSON.stringify(body),timeoutMs:10000});
  const row=data?.result?.rows?.[0];
  if(data.ok&&row){state.availabilityChecks[t.name]=row;renderAvailability(t);showToast(`${t.name}: ${row.status||'unknown'}`,row.available!==false);}
  else{btn.disabled=false;btn.textContent='Check current availability';showToast(`${t.name}: availability check failed`,false);}
  return data;
}

async function loadTools(){
  const d=await api('/api/tools',{timeoutMs:5000});
  if(!d.ok){state.tools=[];$('toolCount').textContent='catalog unavailable';return d;}
  const selectedName=state.selected?.name||null;
  state.tools=(d.tools||[]).sort((a,b)=>String(a.category).localeCompare(String(b.category))||a.name.localeCompare(b.name));
  if(selectedName){
    const fresh=state.tools.find(t=>t.name===selectedName)||null;
    if(fresh){state.selected=fresh;$('toolCategory').textContent=fresh.category||'tool';$('toolName').textContent=fresh.name;$('toolDescription').textContent=fresh.description||'';$('toolBadges').innerHTML=badgeMarkup(fresh);renderAvailability(fresh);}
    else{state.selected=null;$('toolDetail').classList.add('hidden');$('toolEmpty').classList.remove('hidden');delete state.availabilityChecks[selectedName];}
  }
  renderCategories();applyToolFilter();renderCockpitTools();return d;
}

function renderCategories(){
  const cats=['all',...new Set(state.tools.map(t=>t.category||'other'))];const box=$('categories');box.innerHTML='';
  cats.forEach(c=>{const b=document.createElement('button');b.textContent=`${c} (${c==='all'?state.tools.length:state.tools.filter(t=>(t.category||'other')===c).length})`;if(c===state.category)b.classList.add('active');b.onclick=()=>{state.category=c;renderCategories();applyToolFilter();};box.appendChild(b);});
}
function applyToolFilter(){const q=$('toolSearch').value.trim().toLowerCase();state.filtered=state.tools.filter(t=>(state.category==='all'||(t.category||'other')===state.category)&&(!q||`${t.name} ${t.description||''}`.toLowerCase().includes(q)));$('toolCount').textContent=`${state.filtered.length} / ${state.tools.length} tools`;renderToolList();}
function renderToolList(){const box=$('toolList');box.innerHTML='';state.filtered.forEach(t=>{const el=document.createElement('div');el.className=`tool-item${state.selected?.name===t.name?' active':''}`;el.innerHTML=`<div class="tool-title">${escapeHtml(t.name)}</div><div class="tool-desc">${escapeHtml(t.description||'')}</div><div>${badgeMarkup(t)}</div>`;el.onclick=()=>selectTool(t);box.appendChild(el);});}

function defaultFor(p){if(Object.prototype.hasOwnProperty.call(p,'default'))return p.default;if(p.type==='object')return {};if(p.type==='array')return [];if(p.type==='boolean')return false;return '';}
function buildForm(schema){const box=$('schemaForm');box.innerHTML='';const props=schema?.properties||{},req=new Set(schema?.required||[]);if(!Object.keys(props).length){box.innerHTML='<div class="schema-warning">Opaque object schema: use Raw JSON. The HUD will not invent arguments.</div>';}
  for(const [name,p] of Object.entries(props)){if(name==='approval')continue;const row=document.createElement('div');row.className='field';const lab=document.createElement('label');lab.textContent=name+(req.has(name)?' *':'');row.appendChild(lab);let input;
    if(p.type==='boolean'){input=document.createElement('input');input.type='checkbox';input.checked=!!defaultFor(p);}else if(p.enum){input=document.createElement('select');p.enum.forEach(v=>{const o=document.createElement('option');o.value=String(v);o.textContent=String(v);input.appendChild(o);});if(p.default!==undefined)input.value=String(p.default);}else if(p.type==='integer'||p.type==='number'){input=document.createElement('input');input.type='number';if(p.minimum!==undefined)input.min=p.minimum;if(p.maximum!==undefined)input.max=p.maximum;if(p.default!==undefined)input.value=p.default;}else if(p.type==='object'||p.type==='array'){input=document.createElement('textarea');input.value=JSON.stringify(defaultFor(p),null,2);}else{input=document.createElement('input');input.value=p.default??'';}
    input.dataset.field=name;input.dataset.type=p.type||'string';row.appendChild(input);if(p.description){const h=document.createElement('div');h.className='hint';h.textContent=p.description;row.appendChild(h);}box.appendChild(row);
  } syncFormToJson();}
function inputValue(i){const t=i.dataset.type;if(t==='boolean')return i.checked;if(t==='integer')return i.value===''?undefined:parseInt(i.value,10);if(t==='number')return i.value===''?undefined:parseFloat(i.value);if(t==='object'||t==='array')return i.value.trim()?JSON.parse(i.value):(t==='object'?{}:[]);return i.value===''?undefined:i.value;}
function syncFormToJson(){const o={};document.querySelectorAll('#schemaForm [data-field]').forEach(i=>{const v=inputValue(i);if(v!==undefined)o[i.dataset.field]=v;});$('rawPayload').value=JSON.stringify(o,null,2);}
function selectTool(t,preset=null){state.selected=t;$('toolEmpty').classList.add('hidden');$('toolDetail').classList.remove('hidden');$('toolCategory').textContent=t.category||'tool';$('toolName').textContent=t.name;$('toolDescription').textContent=t.description||'';$('toolBadges').innerHTML=badgeMarkup(t);renderAvailability(t);buildForm(t.input_schema||{});if(preset)$('rawPayload').value=JSON.stringify(preset,null,2);$('resultBox').textContent='No dispatch yet.';$('resultBox').className='result';renderToolList();}
function openToolPreset(name,payload={}){const t=state.tools.find(x=>x.name===name);if(!t){showToast(`Tool unavailable: ${name}`,false);return;}activateTab('tools');selectTool(t,payload);}

function approvalOpen(t,payload,challenge,onApproved){state.pendingApproval={tool:t,payload,challenge,onApproved};$('approvalTool').textContent=t.name;$('approvalTier').textContent=String(t.danger_tier||'unknown').toUpperCase();$('approvalDescription').textContent=t.description||'';$('approvalPayload').textContent=JSON.stringify({payload,approval_challenge:challenge},null,2);$('approvalModal').classList.remove('hidden');}
function approvalBusy(on){$('confirmApproval').disabled=on;$('rejectApproval').disabled=on;$('confirmApproval').textContent=on?'Dispatching...':'Approve exact challenge';}
function approvalClose(){approvalBusy(false);state.pendingApproval=null;$('approvalModal').classList.add('hidden');}
async function sendDispatch(t,payload,authority=null,expectedContractDigest=null){
  const request_id=uid(); state.lastDispatch=request_id;
  const body={tool_name:t.name,payload,request_id};if(authority&&Object.keys(authority).length)body.authority=authority;if(expectedContractDigest)body.expected_contract_digest=expectedContractDigest;
  const data=await api('/api/dispatch',{method:'POST',body:JSON.stringify(body),timeoutMs:35000});
  if(data.error_code==='HUD_TOKEN_REQUIRED'){
    const meta=await api('/api/meta',{timeoutMs:3000});
    if(meta.hud_token) state.hudToken=meta.hud_token;
    data.hud_notice='HUD process token refreshed. This dispatch was NOT retried; explicit operator action is required again.';
    showToast('HUD restarted: token refreshed; action NOT retried',false);
  }
  await refreshStatus(); return data;
}
async function dispatchTool(t,payload){
  // Catalog metadata is advisory for display. Runtime policy alone issues authority.
  const d=await sendDispatch(t,payload,null);
  if(d.error_code==='APPROVAL_REQUIRED'){
    const challenge=d.approval_challenge||null;
    const continuation=d.continuation||null;
    if(!challenge?.handle||!continuation||continuation.kind!=='resubmit_exact_tool_call'||!continuation.tool||!continuation.arguments||!continuation.expected_contract_digest||!continuation.authority_template){dispatchResult(t,d);showToast(`Approval continuation missing for ${t.name}`,false);return d;}
    const backendRiskTool={...t,effective_approval_required:true,danger_tier:d.danger_tier||t.danger_tier};
    dispatchResult(t,d);
    const approvedSend=async()=>{
      approvalBusy(true);
      const authority={...continuation.authority_template,permit:true,operator_id:'local-hud-operator',provenance:`pcmmad-local-hud:${d.request_id||state.lastDispatch||'unknown'}`};
      const continuationTool={...t,name:continuation.tool};
      const confirmed=await sendDispatch(continuationTool,continuation.arguments,authority,continuation.expected_contract_digest);
      approvalClose();dispatchResult(t,confirmed);return confirmed;
    };
    approvalOpen(backendRiskTool,continuation.arguments,challenge,approvedSend);
    showToast(`Runtime issued ${String(backendRiskTool.danger_tier||'approval').toUpperCase()} challenge: ${t.name}`,false);
    return d;
  }
  dispatchResult(t,d);return d;
}

function dispatchResult(t,d){
  if(state.selected?.name===t.name){$('resultBox').textContent=JSON.stringify(d,null,2);$('resultBox').className=`result ${d.ok?'ok-result':'bad-result'}`;}
  if(d.error_code==='HUD_TOKEN_REQUIRED') showToast('HUD restarted: token refreshed; action NOT retried',false);
  else showToast(`${t.name}: ${d.ok?'success':'failed'}`,!!d.ok);
}

async function rawToolDispatch(){if(!state.selected)return;let payload;try{payload=JSON.parse($('rawPayload').value||'{}');}catch(e){$('resultBox').textContent=`Invalid JSON: ${e}`;$('resultBox').className='result bad-result';return;}await dispatchTool(state.selected,payload);}

async function presetAction(name){
  if(name==='sessions'){await refreshStatus();activateTab('browser');return;}
  if(name==='mounts'){const d=await api('/api/mounts');showData('Mounted roots',d);showToast(d.ok?'Mounts loaded':'Mounts failed',!!d.ok);return;}
  if(name==='duckai'){const t=state.tools.find(x=>x.name==='browser.session.start');if(!t)return showToast('browser.session.start unavailable',false);return dispatchTool(t,{browser:'chrome',headless:false,persistent:false,profile_name:'da001_duckai_operator',url:'https://duck.ai/',timeout_seconds:60});}
  if(name==='upload'){openToolPreset('browser.upload',{session_id:'',selector:'input[type=file]',paths:[],timeout_seconds:60});}
}

function setUiTier(value){
  const tier=['full','balanced','minimal'].includes(String(value))?String(value):'balanced';
  document.body.dataset.uiTier=tier;
  if($('uiTier'))$('uiTier').value=tier;
  try{localStorage.setItem('pcmmad-hud-tier',tier);}catch{}
}
function restoreUiTier(){
  let tier='balanced';try{tier=localStorage.getItem('pcmmad-hud-tier')||'balanced';}catch{}
  setUiTier(tier);
}
function runCockpitCommand(){
  const input=$('cockpitCommand');if(!input)return;const raw=input.value.trim();const q=raw.toLowerCase();if(!q)return;
  const views={ops:'ops',cockpit:'ops',browser:'browser',sessions:'browser',activity:'activity',journal:'activity',tools:'tools','tool explorer':'tools'};
  if(views[q]){activateTab(views[q]);input.value='';return;}
  const exact=state.tools.find(t=>t.name.toLowerCase()===q);
  const prefix=state.tools.find(t=>t.name.toLowerCase().startsWith(q));
  const contains=state.tools.find(t=>`${t.name} ${t.description||''}`.toLowerCase().includes(q));
  const tool=exact||prefix||contains;
  if(tool){activateTab('tools');selectTool(tool,{});input.value='';$('rawPayload')?.focus();return;}
  showToast(`No live tool/view match: ${raw}`,false);
}
function focusCockpitCommand(){activateTab('ops');const input=$('cockpitCommand');if(input){input.focus();input.select();}}
function activateTab(name){document.querySelectorAll('.tab').forEach(b=>b.classList.toggle('active',b.dataset.tab===name));document.querySelectorAll('.tabpage').forEach(p=>p.classList.toggle('active',p.id===`tab-${name}`));}
function showData(title,data){$('dataTitle').textContent=title;$('dataBody').textContent=typeof data==='string'?data:JSON.stringify(data,null,2);$('dataModal').classList.remove('hidden');}

async function launchBrowser(){const t=state.tools.find(x=>x.name==='browser.session.start');if(!t)return showToast('browser.session.start unavailable',false);const payload={browser:'chrome',headless:$('launchHeadless').checked,persistent:$('launchPersistent').checked,profile_name:$('launchProfile').value.trim()||'pcmmad_operator',url:$('launchUrl').value.trim()||'about:blank',timeout_seconds:60};await dispatchTool(t,payload);}
async function requestBrowserUpload(){const t=state.tools.find(x=>x.name==='browser.upload');if(!t)return showToast('browser.upload unavailable',false);const session_id=$('uploadSession').value;const selector=$('uploadSelector').value.trim();const paths=$('uploadPaths').value.split(/\r?\n/).map(x=>x.trim()).filter(Boolean);if(!session_id||!selector||!paths.length)return showToast('Session, selector, and at least one local path are required',false);await dispatchTool(t,{session_id,selector,paths,timeout_seconds:60});}


let topbarResizeObserver=null;
function syncStickyOffsets(){
  const topbar=document.querySelector('.topbar');
  if(!topbar)return;
  const update=()=>{
    const h=Math.ceil(topbar.getBoundingClientRect().height||0);
    if(h>0)document.documentElement.style.setProperty('--topbar-h',`${h}px`);
  };
  update();
  if('ResizeObserver' in window){
    topbarResizeObserver?.disconnect?.();
    topbarResizeObserver=new ResizeObserver(update);
    topbarResizeObserver.observe(topbar);
  }else{
    window.addEventListener('resize',update,{passive:true});
  }
}

function wire(){
  syncStickyOffsets();
  document.querySelectorAll('.tab').forEach(b=>b.onclick=()=>activateTab(b.dataset.tab));
  document.querySelectorAll('[data-preset]').forEach(b=>b.onclick=()=>presetAction(b.dataset.preset));
  $('refreshAll').onclick=async()=>{await Promise.all([refreshStatus(),loadTools()]);showToast('State refreshed');};
  $('browserRefresh').onclick=refreshStatus;$('activityRefresh').onclick=refreshStatus;$('launchBrowser').onclick=launchBrowser;$('requestUpload').onclick=requestBrowserUpload;$('closeData').onclick=()=>$('dataModal').classList.add('hidden');
  $('toolSearch').oninput=applyToolFilter;$('syncFormBtn').onclick=()=>{try{syncFormToJson();}catch(e){showToast(String(e),false);}};$('dispatchBtn').onclick=rawToolDispatch;$('checkAvailabilityBtn').onclick=checkSelectedAvailability;
  $('openToolExplorer').onclick=()=>activateTab('tools');$('openRawTools').onclick=()=>activateTab('tools');$('openBrowserView').onclick=()=>activateTab('browser');$('openActivityView').onclick=()=>activateTab('activity');
  $('runCockpitCommand').onclick=runCockpitCommand;$('cockpitCommand').addEventListener('keydown',e=>{if(e.key==='Enter'){e.preventDefault();runCockpitCommand();}});
  const diagnosticIds=['masterAnnunciator','synHud','synNgrok','synReceiver','synDaemon','synJournal','synBrowser','cockpitDiagnosticBtn'];diagnosticIds.forEach(id=>{const el=$(id);if(!el)return;el.onclick=openDiagnostic;el.addEventListener('keydown',e=>{if(e.key==='Enter'||e.key===' '){e.preventDefault();openDiagnostic();}});});$('closeDiagnostic').onclick=closeDiagnostic;
  $('browserGateToggle').onclick=toggleBrowserGate;
  $('uiTier').onchange=e=>setUiTier(e.target.value);
  $('rejectApproval').onclick=()=>{const name=state.pendingApproval?.tool?.name;approvalClose();showToast(`Rejected: ${name||'action'}`,false);};
  $('confirmApproval').onclick=()=>{const p=state.pendingApproval;if(!p)return;const cb=p.onApproved;cb();};
  window.addEventListener('keydown',e=>{
    if(e.key==='Escape'&&!$('approvalModal').classList.contains('hidden')){$('rejectApproval').click();return;}
    if(e.key==='Escape'&&!$('diagnosticModal').classList.contains('hidden')){closeDiagnostic();return;}
    const target=e.target;const editing=target&&(['INPUT','TEXTAREA','SELECT'].includes(target.tagName)||target.isContentEditable);
    if((e.ctrlKey||e.metaKey)&&e.key.toLowerCase()==='k'){e.preventDefault();focusCockpitCommand();return;}
    if(e.altKey&&['1','2','3','4'].includes(e.key)){e.preventDefault();activateTab(['ops','browser','activity','tools'][Number(e.key)-1]);return;}
    if(!editing&&e.key==='/'){e.preventDefault();focusCockpitCommand();}
  });
}

async function init(){wire();restoreUiTier();const meta=await api('/api/meta');state.hudToken=meta.hud_token||null;if(!state.hudToken)showToast('HUD POST capability token unavailable',false);await Promise.all([loadTools(),refreshStatus()]);setInterval(refreshStatus,5000);}
init();
