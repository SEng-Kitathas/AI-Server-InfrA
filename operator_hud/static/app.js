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
  renderSessions(sessions); renderEvents(data.events||[]);
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
  renderCategories();applyToolFilter();return d;
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
  $('rejectApproval').onclick=()=>{const name=state.pendingApproval?.tool?.name;approvalClose();showToast(`Rejected: ${name||'action'}`,false);};
  $('confirmApproval').onclick=()=>{const p=state.pendingApproval;if(!p)return;const cb=p.onApproved;cb();};
  window.addEventListener('keydown',e=>{if(e.key==='Escape'&&!$('approvalModal').classList.contains('hidden')){$('rejectApproval').click();}});
}

async function init(){wire();const meta=await api('/api/meta');state.hudToken=meta.hud_token||null;if(!state.hudToken)showToast('HUD POST capability token unavailable',false);await Promise.all([loadTools(),refreshStatus()]);setInterval(refreshStatus,5000);}
init();
