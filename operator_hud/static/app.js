const state={tools:[],filtered:[],category:'all',selected:null,status:null,pendingApproval:null,lastDispatch:null,hudToken:null,availabilityChecks:{}};
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
function fmtBytes(value){
  const n=Number(value);if(!Number.isFinite(n)||n<0)return '—';
  const units=['B','KiB','MiB','GiB','TiB'];let x=n,i=0;while(x>=1024&&i<units.length-1){x/=1024;i++;}
  return `${x>=100||i===0?x.toFixed(0):x>=10?x.toFixed(1):x.toFixed(2)} ${units[i]}`;
}
function fmtPercent(value,digits=1){const n=Number(value);return Number.isFinite(n)?`${n.toFixed(digits)}%`:'—';}
function sparkSvg(values){
  const rows=values.map(Number).filter(Number.isFinite);if(rows.length<2)return '<svg viewBox="0 0 100 30" preserveAspectRatio="none"><line class="spark-base" x1="0" y1="15" x2="100" y2="15"/></svg>';
  const min=Math.min(...rows),max=Math.max(...rows),span=max-min||1;
  const points=rows.map((v,i)=>`${(i/(rows.length-1)*100).toFixed(2)},${(27-((v-min)/span)*24).toFixed(2)}`).join(' ');
  return `<svg viewBox="0 0 100 30" preserveAspectRatio="none"><line class="spark-base" x1="0" y1="27" x2="100" y2="27"/><polyline class="spark-path" points="${points}"/></svg>`;
}
function setSpark(id,values,severity='nominal'){const el=$(id);if(!el)return;el.className=`sparkline ${severity}`;el.innerHTML=sparkSvg(values);}

function renderTelemetry(t){
  const exec=t?.execution||{},g=exec.global||{},proc=t?.process||{},sys=t?.system||{},http=t?.http||{},server=t?.server||{},scheduler=t?.scheduler||{};
  const pill=$('telemetryState');const severity=String(t?.severity||(!t?.ok?'warning':'nominal'));
  if(pill){pill.className=`state-pill ${severity==='critical'?'bad':severity==='warning'?'degraded':t?.ok?'good':'unknown'}`;pill.textContent=t?.ok?(severity==='critical'?'ALERT':severity==='warning'?'ATTENTION':'NOMINAL'):'TELEMETRY DEGRADED';}
  const running=Number(g.running||0),limit=Number(g.global_limit||0),queued=Number(g.queued||0),util=limit>0?running/limit:null;
  $('telemetryWorkers').textContent=limit>0?`${running} / ${limit}`:`${running} / ∞`;
  $('telemetryWorkerSub').textContent=util!==null?`${(util*100).toFixed(0)}% utilized · loaded capacity`:'unbounded loaded capacity';
  $('telemetryQueue').textContent=String(queued);
  const oldest=g.oldest_queued_age_seconds;$('telemetryQueueSub').textContent=oldest==null?'no queued work':`oldest ${Number(oldest).toFixed(1)} s`;
  const p95=http.latency_ms?.p95;$('telemetryP95').textContent=p95==null?'—':`${Number(p95).toFixed(p95>=1000?0:1)} ms`;
  $('telemetryHttpSub').textContent=`${Number(http.request_count||0)} req · ${Number(http.client_error_count||0)} 4xx`;
  $('telemetryRss').textContent=fmtBytes(proc.rss_bytes);$('telemetryRssSub').textContent=`USS ${fmtBytes(proc.uss_bytes)}`;
  $('telemetryCpu').textContent=fmtPercent(proc.cpu_percent);
  $('telemetryHostCpu').textContent=fmtPercent(sys.cpu_percent);
  $('telemetryHostMem').textContent=fmtPercent(sys.memory_percent);
  $('telemetryStorage').textContent=`${fmtBytes(sys.storage?.free_bytes)} free`;
  $('telemetryHandles').textContent=proc.handles??'—';
  $('telemetryThreads').textContent=proc.threads??'—';
  $('telemetryDescriptors').textContent=`${proc.connections??'—'} / ${proc.open_files??'—'}`;
  $('telemetryHttpWorkers').textContent=server.worker_threads!=null?`${server.active_workers??0} / ${server.worker_threads}`:`${server.implementation||'unbound'}`;
  $('telemetryHttpQueuePeak').textContent=server.queue_peak??'—';
  $('telemetryRpm').textContent=Number.isFinite(Number(http.requests_per_minute))?Number(http.requests_per_minute).toFixed(1):'—';
  $('telemetry5xx').textContent=fmtPercent(Number(http.server_error_rate||0)*100,2);
  $('telemetryScheduler').textContent=`${scheduler.thread_alive?'SCHED ✓':'SCHED !'} · ${scheduler.watcher_alive?'WATCH ✓':'WATCH !'}`;
  const alerts=Array.isArray(t?.alerts)?t.alerts:[];
  $('telemetryAlerts').innerHTML=alerts.length?alerts.map(a=>`<span class="telemetry-alert-chip ${escapeHtml(a.severity||'warning')}">${escapeHtml(a.code||'ALERT')} · ${escapeHtml(a.message||'')}</span>`).join(''):'<span class="telemetry-alert-chip nominal">NO ACTIVE INTEGRITY ALARMS</span>';
  const deps=t?.dependencies||{};
  $('telemetryDependencies').textContent=`psutil ${deps.psutil||'—'} · Prometheus ${deps.prometheus_client||'—'} · Waitress ${deps.waitress||'—'} · py-spy ${deps.py_spy_available?(deps.py_spy||'available'):'on-demand unavailable'}`;
  const hist=Array.isArray(t?.history)?t.history:[];
  setSpark('telemetryWorkerSpark',hist.map(x=>Number(x.worker_utilization||0)*100),severity);
  setSpark('telemetryQueueSpark',hist.map(x=>Number(x.queued||0)),queued>0?'warning':'nominal');
  setSpark('telemetryP95Spark',hist.map(x=>x.http_p95_ms).filter(x=>x!=null),p95!=null&&Number(p95)>=2000?'warning':'nominal');
  setSpark('telemetryRssSpark',hist.map(x=>x.rss_bytes).filter(x=>x!=null),'nominal');
}

function renderCockpitStatus(data){
  const h=data.hud||{},r=data.receiver||{},b=data.browser_bridge||{},j=data.journal||{},ready=data.readiness||{};
  const coreReady=ready.core_ready!==undefined?!!ready.core_ready:!!(h.ok&&r.ok&&j.ok);
  const optionalDegraded=Array.isArray(ready.optional_degraded)?ready.optional_degraded:(!b.ok?['browser_bridge']:[]);
  const assurance=$('cockpitAssurance');
  if(assurance){
    assurance.textContent=coreReady?(optionalDegraded.length?'Core ready; optional degradation isolated':'Core ready; required planes nominal'):'Required control-plane evidence is degraded';
  }
  const optional=$('cockpitOptional');if(optional)optional.textContent=optionalDegraded.length?`${optionalDegraded.length} DEGRADED`:'NOMINAL';
  const sessions=data.browser_sessions||[];
  const sessionSummary=$('cockpitSessionSummary');
  if(sessionSummary){
    sessionSummary.innerHTML=sessions.length
      ? `<strong>${sessions.length}</strong> active session${sessions.length===1?'':'s'}<br>${sessions.slice(0,3).map(x=>escapeHtml(x.session_id||x.id||'session')).join('<br>')}`
      : `${b.ok?'Bridge online; no active sessions.':'Optional browser bridge unavailable.'}`;
  }
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
  const h=data.hud||{},r=data.receiver||{},b=data.browser_bridge||{},j=data.journal||{},ready=data.readiness||{};
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
  renderCockpitStatus(data); renderTelemetry(data.telemetry||{}); renderSessions(sessions); renderEvents(data.events||[]);
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
  const rows=completed.slice(0,10);
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
async function sendDispatch(t,payload,authority=null){
  const request_id=uid(); state.lastDispatch=request_id;
  const body={tool_name:t.name,payload,request_id};if(authority&&Object.keys(authority).length)body.authority=authority;
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
    if(!challenge?.handle){dispatchResult(t,d);showToast(`Approval challenge missing for ${t.name}`,false);return d;}
    const backendRiskTool={...t,effective_approval_required:true,danger_tier:d.danger_tier||t.danger_tier};
    dispatchResult(t,d);
    const approvedSend=async()=>{
      approvalBusy(true);
      const authority={approval_handle:challenge.handle,permit:true,operator_id:'local-hud-operator',provenance:`pcmmad-local-hud:${d.request_id||state.lastDispatch||'unknown'}`};
      const confirmed=await sendDispatch(t,payload,authority);
      approvalClose();dispatchResult(t,confirmed);return confirmed;
    };
    approvalOpen(backendRiskTool,payload,challenge,approvedSend);
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

function wire(){
  document.querySelectorAll('.tab').forEach(b=>b.onclick=()=>activateTab(b.dataset.tab));
  document.querySelectorAll('[data-preset]').forEach(b=>b.onclick=()=>presetAction(b.dataset.preset));
  $('refreshAll').onclick=async()=>{await Promise.all([refreshStatus(),loadTools()]);showToast('State refreshed');};
  $('browserRefresh').onclick=refreshStatus;$('activityRefresh').onclick=refreshStatus;$('launchBrowser').onclick=launchBrowser;$('requestUpload').onclick=requestBrowserUpload;$('closeData').onclick=()=>$('dataModal').classList.add('hidden');
  $('toolSearch').oninput=applyToolFilter;$('syncFormBtn').onclick=()=>{try{syncFormToJson();}catch(e){showToast(String(e),false);}};$('dispatchBtn').onclick=rawToolDispatch;$('checkAvailabilityBtn').onclick=checkSelectedAvailability;
  $('openToolExplorer').onclick=()=>activateTab('tools');$('openRawTools').onclick=()=>activateTab('tools');$('openBrowserView').onclick=()=>activateTab('browser');$('openActivityView').onclick=()=>activateTab('activity');
  $('runCockpitCommand').onclick=runCockpitCommand;$('cockpitCommand').addEventListener('keydown',e=>{if(e.key==='Enter'){e.preventDefault();runCockpitCommand();}});
  $('uiTier').onchange=e=>setUiTier(e.target.value);
  $('rejectApproval').onclick=()=>{const name=state.pendingApproval?.tool?.name;approvalClose();showToast(`Rejected: ${name||'action'}`,false);};
  $('confirmApproval').onclick=()=>{const p=state.pendingApproval;if(!p)return;const cb=p.onApproved;cb();};
  window.addEventListener('keydown',e=>{
    if(e.key==='Escape'&&!$('approvalModal').classList.contains('hidden')){$('rejectApproval').click();return;}
    const target=e.target;const editing=target&&(['INPUT','TEXTAREA','SELECT'].includes(target.tagName)||target.isContentEditable);
    if((e.ctrlKey||e.metaKey)&&e.key.toLowerCase()==='k'){e.preventDefault();focusCockpitCommand();return;}
    if(e.altKey&&['1','2','3','4'].includes(e.key)){e.preventDefault();activateTab(['ops','browser','activity','tools'][Number(e.key)-1]);return;}
    if(!editing&&e.key==='/'){e.preventDefault();focusCockpitCommand();}
  });
}

async function init(){wire();restoreUiTier();const meta=await api('/api/meta');state.hudToken=meta.hud_token||null;if(!state.hudToken)showToast('HUD POST capability token unavailable',false);await Promise.all([loadTools(),refreshStatus()]);setInterval(refreshStatus,5000);}
init();
