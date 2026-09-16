from __future__ import annotations

import hashlib
import json
import os
import subprocess
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

HUD = "http://127.0.0.1:5090"
BRIDGE = "http://127.0.0.1:4471"
HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
REPORT = ROOT / "state" / "trace_matrix" / "HUD_HOSTILE_SUITE_V2_REPORT_2026-09-01.json"
UPLOAD_PROBE = ROOT / "state" / "trace_matrix" / "HUD_UPLOAD_PROBE_V2.txt"
RECEIVER_DIR = Path(r"C:\Users\ancal\Desktop\PCMMAD_RECEIVER_V29_NATIVE_PROTOCOL_RC1\PCMMAD_receiver\baseline\pcmmad_receiver")
RECEIVER_PY = RECEIVER_DIR / ".venv" / "Scripts" / "python.exe"
BUILD_FILES = [HERE / "server.py", HERE / "static" / "app.js", HERE / "static" / "index.html", HERE / "static" / "style.css"]


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def build_identity() -> dict[str, str]:
    return {str(p.relative_to(HERE)).replace("\\", "/"): sha(p) for p in BUILD_FILES}


def call(method: str, url: str, obj=None, headers=None, timeout=30):
    data = None if obj is None else json.dumps(obj).encode("utf-8")
    h = {"Content-Type": "application/json"} if data else {}
    h.update(headers or {})
    req = urllib.request.Request(url, data=data, headers=h, method=method)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            raw = resp.read().decode("utf-8")
            return resp.status, json.loads(raw) if raw else {}
    except urllib.error.HTTPError as exc:
        raw = exc.read().decode("utf-8")
        try:
            body = json.loads(raw)
        except Exception:
            body = {"raw": raw}
        return exc.code, body


def meta() -> dict:
    return call("GET", HUD + "/api/meta", timeout=5)[1]


def hud_headers() -> dict[str, str]:
    token = meta().get("hud_token")
    if not token:
        raise RuntimeError("HUD token unavailable")
    return {"X-PCMMAD-HUD-Token": token}


def hud_dispatch(tool_name: str, payload: dict, approve=False, headers=None, timeout=35):
    return call(
        "POST",
        HUD + "/api/dispatch",
        {"tool_name": tool_name, "payload": payload, "approve": approve},
        headers or hud_headers(),
        timeout,
    )


def bridge_eval(session_id: str, expression: str):
    status, body = call("POST", BRIDGE + "/evaluate", {"session_id": session_id, "expression": expression}, timeout=20)
    if status != 200 or not body.get("ok"):
        raise RuntimeError(f"evaluate failed {status}: {body}")
    return body.get("result")


def eval_json(session_id: str, expression: str):
    return json.loads(bridge_eval(session_id, f"JSON.stringify({expression})"))


def add(checks, name: str, passed: bool, detail=None):
    checks.append({"name": name, "pass": bool(passed), "detail": detail})


def completed_count() -> int:
    _, d = call("GET", HUD + "/api/events", timeout=5)
    return sum(1 for x in d.get("events", []) if x.get("kind") == "dispatch_completed")


def restart_hud() -> None:
    # Kill only the process currently owning port 5090, then invoke the receiver's
    # idempotent HUD autostart hook from an external process.
    ps = "(Get-NetTCPConnection -State Listen -LocalPort 5090 -ErrorAction SilentlyContinue | Select-Object -First 1).OwningProcess"
    cp = subprocess.run(["powershell.exe", "-NoProfile", "-Command", ps], capture_output=True, text=True, timeout=10)
    pid_text = cp.stdout.strip()
    if pid_text:
        subprocess.run(["taskkill", "/PID", pid_text, "/F"], capture_output=True, timeout=10)
    time.sleep(0.4)
    code = f"import sys,time;sys.path.insert(0,r'{RECEIVER_DIR}');import server;server._autostart_hud();time.sleep(1)"
    subprocess.run([str(RECEIVER_PY), "-c", code], check=True, timeout=10)
    deadline = time.time() + 8
    while time.time() < deadline:
        try:
            if call("GET", HUD + "/api/meta", timeout=0.5)[0] == 200:
                return
        except Exception:
            pass
        time.sleep(0.2)
    raise RuntimeError("HUD failed to restart")


def spawn_isolated_hud(port: int, receiver_base: str, bridge_base: str):
    env = os.environ.copy()
    env["PCMMAD_HUD_PORT"] = str(port)
    env["PCMMAD_RECEIVER_BASE"] = receiver_base
    env["PCMMAD_BROWSER_BRIDGE_BASE"] = bridge_base
    proc = subprocess.Popen(
        [sys.executable, str(HERE / "server.py")],
        cwd=str(HERE), env=env,
        stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
    )
    deadline = time.time() + 5
    while time.time() < deadline:
        try:
            if call("GET", f"http://127.0.0.1:{port}/api/meta", timeout=0.3)[0] == 200:
                return proc
        except Exception:
            pass
        time.sleep(0.1)
    proc.terminate()
    raise RuntimeError(f"isolated HUD {port} failed")


def main() -> int:
    checks = []
    created_sessions: list[str] = []
    isolated = []
    before_build = build_identity()

    # Live health and catalog.
    s, status = call("GET", HUD + "/api/status", timeout=5)
    add(checks, "live_status_http_200", s == 200, status)
    add(checks, "live_all_components_green", all(status.get(k, {}).get("ok") for k in ["hud", "receiver", "browser_bridge"]), status)
    s, tools = call("GET", HUD + "/api/tools", timeout=5)
    catalog = tools.get("tools", [])
    add(checks, "live_catalog_available", s == 200 and len(catalog) > 0, {"count": len(catalog)})
    live_count = len(catalog)

    # Anti-CSRF / approval broker boundary.
    start_payload = {"browser": "chrome", "headless": True, "persistent": False, "profile_name": "suite_v2_csrf", "url": "about:blank", "timeout_seconds": 15}
    body = {"tool_name": "browser.session.start", "payload": start_payload, "approve": True}
    s, d = call("POST", HUD + "/api/dispatch", body, headers={}, timeout=10)
    add(checks, "csrf_no_token_rejected", s == 403 and d.get("error_code") == "HUD_TOKEN_REQUIRED", d)
    s, d = call("POST", HUD + "/api/dispatch", body, headers={"X-PCMMAD-HUD-Token": "wrong"}, timeout=10)
    add(checks, "csrf_wrong_token_rejected", s == 403 and d.get("error_code") == "HUD_TOKEN_REQUIRED", d)
    token_headers = hud_headers()
    smuggle = {**start_payload, "approval": {"permit": True, "source": "smuggle"}}
    s, d = hud_dispatch("browser.session.start", smuggle, approve=False, headers=token_headers)
    add(checks, "raw_receiver_approval_smuggle_rejected", s == 403 and d.get("error_code") == "APPROVAL_REQUIRED", d)

    # Start browser-rendered HUD under explicit approval.
    s, d = hud_dispatch("browser.session.start", {**start_payload, "profile_name": "suite_v2_hud", "url": HUD + "/"}, approve=True, headers=token_headers)
    hud_sid = d.get("result", {}).get("session_id")
    add(checks, "rendered_hud_session_started", s == 200 and bool(hud_sid), d)
    if not hud_sid:
        raise RuntimeError("HUD browser session unavailable")
    created_sessions.append(hud_sid)
    time.sleep(0.8)

    visible = eval_json(hud_sid, "({global:globalState.textContent,hud:hudState.textContent,receiver:receiverState.textContent,bridge:bridgeState.textContent,count:toolCount.textContent,tokenVisible:document.body.innerText.includes(state.hudToken)})")
    add(checks, "visible_nominal_topology", visible["global"] == "ALL SYSTEMS NOMINAL" and visible["hud"] == visible["receiver"] == visible["bridge"] == "ONLINE", visible)
    add(checks, "hud_token_not_rendered_in_body", visible["tokenVisible"] is False, visible)
    add(checks, "visible_catalog_count_current", str(live_count) in visible["count"], visible)

    # All live tools render; opaque schemas are honest.
    sweep = json.loads(bridge_eval(hud_sid, r'''(()=>{const failures=[],opaque=[];for(const item of [...document.querySelectorAll('.tool-item')]){const name=item.querySelector('.tool-title')?.textContent||'?';try{item.click();JSON.parse(rawPayload.value||'{}');const fields=[...schemaForm.querySelectorAll('[data-field]')];if(!fields.length)opaque.push({name,warning:schemaForm.textContent});}catch(e){failures.push({name,error:String(e)})}}return JSON.stringify({count:document.querySelectorAll('.tool-item').length,failures,opaque});})()'''))
    add(checks, "all_tools_render", sweep["count"] == live_count and not sweep["failures"], sweep)
    add(checks, "opaque_schemas_labeled", all("Opaque object schema" in x["warning"] for x in sweep["opaque"]), {"opaque_count": len(sweep["opaque"])})

    # XSS pressure against tool rendering and approval payload rendering.
    xss = eval_json(hud_sid, r'''(()=>{window.__hud_xss=false;const fake={name:'<img src=x onerror="window.__hud_xss=true">',description:'<script>window.__hud_xss=true</script>',category:'x',mutating:false,approval_required:false,danger_tier:'<svg onload="window.__hud_xss=true">',input_schema:{type:'object',properties:{}}};state.tools.push(fake);state.filtered=[fake];renderToolList();const html=toolList.innerHTML;selectTool(fake);approvalOpen({...fake,approval_required:true,danger_tier:'HIGH'},{payload:'</pre><script>window.__hud_xss=true</script>'},()=>{});const out={executed:window.__hud_xss,imgs:toolList.querySelectorAll('img,script,svg').length,payloadScripts:approvalPayload.querySelectorAll('script').length,payloadText:approvalPayload.textContent};approvalClose();location.reload();return out})()''')
    add(checks, "tool_metadata_xss_not_executed", xss["executed"] is False and xss["imgs"] == 0, xss)
    add(checks, "approval_payload_xss_not_interpreted", xss["payloadScripts"] == 0 and "<script>" in xss["payloadText"], xss)
    time.sleep(0.8)

    # Approval modal: exact payload, reject and Escape no dispatch, double confirm exactly one.
    before = completed_count()
    open_expr = r'''(()=>{activateTab('tools');const t=state.tools.find(x=>x.name==='browser.session.start');selectTool(t);rawPayload.value=JSON.stringify({browser:'chrome',headless:true,persistent:false,profile_name:'suite_modal_target',url:'about:blank',timeout_seconds:15});dispatchBtn.click();return {hidden:approvalModal.classList.contains('hidden'),tier:approvalTier.textContent,tool:approvalTool.textContent,payload:approvalPayload.textContent}})()'''
    modal = eval_json(hud_sid, open_expr)
    add(checks, "high_tool_opens_explicit_modal", modal["hidden"] is False and modal["tier"] == "HIGH" and modal["tool"] == "browser.session.start", modal)
    bridge_eval(hud_sid, "rejectApproval.click();'rejected'")
    time.sleep(0.15)
    add(checks, "reject_creates_no_dispatch", completed_count() == before, {"before": before, "after": completed_count()})
    bridge_eval(hud_sid, "dispatchBtn.click();'opened'")
    before_escape = completed_count(); bridge_eval(hud_sid, "window.dispatchEvent(new KeyboardEvent('keydown',{key:'Escape'}));'escape'"); time.sleep(0.15)
    add(checks, "escape_creates_no_dispatch", completed_count() == before_escape, {"before": before_escape, "after": completed_count()})
    bridge_eval(hud_sid, "dispatchBtn.click();confirmApproval.click();confirmApproval.click();'double'")
    time.sleep(0.8)
    after_double = completed_count()
    state_after = eval_json(hud_sid, "({modalHidden:approvalModal.classList.contains('hidden'),result:resultBox.textContent,cls:resultBox.className})")
    add(checks, "double_confirm_single_dispatch", after_double - before_escape == 1, {"before": before_escape, "after": after_double})
    add(checks, "approved_success_visibly_green", "ok-result" in state_after["cls"] and '"ok": true' in state_after["result"], state_after)

    # Record newly created target session for cleanup.
    _, ls = hud_dispatch("browser.sessions.list", {}, approve=False, headers=hud_headers())
    for row in ls.get("result", {}).get("sessions", []):
        if row.get("profile_name") == "suite_modal_target": created_sessions.append(row.get("session_id"))

    # Malformed JSON blocks before backend.
    before_badjson = completed_count()
    badjson = eval_json(hud_sid, "(()=>{rawPayload.value='{bad json';dispatchBtn.click();return {text:resultBox.textContent,cls:resultBox.className}})()")
    time.sleep(0.1)
    add(checks, "malformed_json_blocked_locally", badjson["text"].startswith("Invalid JSON:") and "bad-result" in badjson["cls"] and completed_count() == before_badjson, badjson)

    # Backend approval escalation must override stale LOW metadata with HIGH.
    bridge_eval(hud_sid, "location.reload();'reload'"); time.sleep(0.8)
    bridge_eval(hud_sid, r'''(()=>{activateTab('tools');const t=state.tools.find(x=>x.name==='browser.session.start');t.approval_required=false;t.danger_tier='low';selectTool(t);rawPayload.value=JSON.stringify({browser:'chrome',headless:true,persistent:false,profile_name:'suite_backend_escalation',url:'about:blank',timeout_seconds:15});dispatchBtn.click();return true})()''')
    time.sleep(0.6)
    escalated = eval_json(hud_sid, "({hidden:approvalModal.classList.contains('hidden'),tier:approvalTier.textContent,toast:toast.textContent,result:resultBox.textContent})")
    add(checks, "backend_approval_escalates_modal", escalated["hidden"] is False and escalated["tier"] == "HIGH" and "Backend requires HIGH approval" in escalated["toast"], escalated)
    bridge_eval(hud_sid, "rejectApproval.click();location.reload();'reset'"); time.sleep(0.8)

    # Catalog currentness: corrupt local cache count; status refresh must reload.
    # Playwright page.evaluate awaits returned promises, but the bridge wrapper may
    # serialize a promise result differently across versions. Store the result
    # in page state and poll for completion rather than assuming direct shape.
    bridge_eval(hud_sid, "window.__catalogProbe=null;(async()=>{state.tools.pop();const before=state.tools.length;await refreshStatus();window.__catalogProbe={before,after:state.tools.length,text:toolCount.textContent};})()")
    deadline=time.time()+4
    currentness=None
    while time.time()<deadline:
        raw=bridge_eval(hud_sid, "JSON.stringify(window.__catalogProbe)")
        if raw and raw!='null':
            currentness=json.loads(raw);break
        time.sleep(0.1)
    add(checks, "catalog_count_drift_self_repairs", bool(currentness) and currentness.get("before") == live_count - 1 and currentness.get("after") == live_count, currentness)

    # Mounts quick action must show actual data, not toast-only success.
    bridge_eval(hud_sid, "presetAction('mounts');'triggered'")
    deadline=time.time()+4
    mounts=None
    while time.time()<deadline:
        mounts=eval_json(hud_sid, "({hidden:dataModal.classList.contains('hidden'),title:dataTitle.textContent,body:dataBody.textContent,toast:toast.textContent})")
        if mounts.get("hidden") is False and mounts.get("title") == "Mounted roots": break
        time.sleep(0.1)
    add(checks, "mounts_quick_action_surfaces_data", bool(mounts) and mounts.get("hidden") is False and mounts.get("title") == "Mounted roots" and len(mounts.get("body", "")) > 20, mounts)
    bridge_eval(hud_sid, "closeData.click();'closed'")

    # Upload through dedicated browser-tab controls.
    UPLOAD_PROBE.write_text("pcmmad hostile HUD V2 upload probe\n", encoding="utf-8", newline="\n")
    s, d = hud_dispatch("browser.session.start", {"browser": "chrome", "headless": True, "persistent": False, "profile_name": "suite_upload_target", "url": "about:blank", "timeout_seconds": 15}, approve=True, headers=hud_headers())
    target_sid = d.get("result", {}).get("session_id")
    add(checks, "upload_target_started", s == 200 and bool(target_sid), d)
    if target_sid:
        created_sessions.append(target_sid)
        bridge_eval(target_sid, "document.body.innerHTML='<input id=\"u\" type=\"file\">';'ready'")
        bridge_eval(hud_sid, "refreshStatus();'refresh'"); time.sleep(0.4)
        upload_open = eval_json(hud_sid, f'''(()=>{{activateTab('browser');uploadSession.value={json.dumps(target_sid)};uploadSelector.value='#u';uploadPaths.value={json.dumps(str(UPLOAD_PROBE.resolve()))};requestUpload.click();return {{hidden:approvalModal.classList.contains('hidden'),tool:approvalTool.textContent,tier:approvalTier.textContent,payload:approvalPayload.textContent}}}})()''')
        add(checks, "dedicated_upload_opens_approval", upload_open["hidden"] is False and upload_open["tool"] == "browser.upload" and upload_open["tier"] == "HIGH", upload_open)
        bridge_eval(hud_sid, "confirmApproval.click();'approved'"); time.sleep(0.7)
        files = json.loads(bridge_eval(target_sid, "JSON.stringify([...document.querySelector('#u').files].map(f=>({name:f.name,size:f.size})))"))
        add(checks, "dedicated_upload_reaches_file_input", len(files) == 1 and files[0]["name"] == UPLOAD_PROBE.name, files)

    # Degraded-state isolated HUDs, using real bridge to inspect them.
    for port, receiver_base, bridge_base, label, expected in [
        (5091, "http://127.0.0.1:59991", BRIDGE, "receiver_down", {"global": "DEGRADED", "hud": "ONLINE", "receiver": "DOWN", "bridge": "ONLINE"}),
        (5092, "http://127.0.0.1:5000", "http://127.0.0.1:59992", "bridge_down", {"global": "DEGRADED", "hud": "ONLINE", "receiver": "ONLINE", "bridge": "DOWN"}),
    ]:
        proc = spawn_isolated_hud(port, receiver_base, bridge_base); isolated.append(proc)
        s, d = hud_dispatch("browser.session.start", {"browser": "chrome", "headless": True, "persistent": False, "profile_name": f"suite_{label}_visual", "url": f"http://127.0.0.1:{port}/", "timeout_seconds": 20}, approve=True, headers=hud_headers())
        iso_sid = d.get("result", {}).get("session_id"); created_sessions.append(iso_sid)
        time.sleep(2.6)
        topo = eval_json(iso_sid, "({global:globalState.textContent,hud:hudState.textContent,receiver:receiverState.textContent,bridge:bridgeState.textContent,count:toolCount.textContent})")
        add(checks, f"visible_{label}_topology", all(topo[k] == v for k, v in expected.items()), topo)
        if label == "receiver_down": add(checks, "receiver_down_catalog_not_claimed_live", "unavailable" in topo["count"], topo)
        proc.terminate();
        try: proc.wait(timeout=2)
        except Exception: proc.kill()
        isolated.remove(proc)

    # HUD token rotation across an open approval modal: no auto retry.
    bridge_eval(hud_sid, "location.href='http://127.0.0.1:5090/';'reload'"); time.sleep(0.8)
    bridge_eval(hud_sid, r'''(()=>{activateTab('tools');const t=state.tools.find(x=>x.name==='browser.session.start');selectTool(t);rawPayload.value=JSON.stringify({browser:'chrome',headless:true,persistent:false,profile_name:'suite_token_rotation',url:'about:blank',timeout_seconds:15});dispatchBtn.click();return true})()''')
    old_page_token_hash = hashlib.sha256(str(bridge_eval(hud_sid, "state.hudToken")).encode()).hexdigest()
    restart_hud()
    new_token_hash = hashlib.sha256(meta()["hud_token"].encode()).hexdigest()
    add(checks, "hud_restart_rotates_token", old_page_token_hash != new_token_hash, None)
    before_token = completed_count()
    bridge_eval(hud_sid, "confirmApproval.click();'stale-confirm'"); time.sleep(0.7)
    stale = eval_json(hud_sid, "({result:resultBox.textContent,cls:resultBox.className,toast:toast.textContent,modalHidden:approvalModal.classList.contains('hidden')})")
    after_token = completed_count()
    add(checks, "stale_token_not_auto_retried", "HUD_TOKEN_REQUIRED" in stale["result"] and "NOT retried" in stale["result"] and after_token == before_token, stale)
    add(checks, "stale_token_failure_visible", "bad-result" in stale["cls"] and "NOT retried" in stale["toast"], stale)
    bridge_eval(hud_sid, "dispatchBtn.click();confirmApproval.click();'retry'"); time.sleep(0.8)
    retry = eval_json(hud_sid, "({result:resultBox.textContent,cls:resultBox.className,toast:toast.textContent})")
    add(checks, "fresh_explicit_retry_succeeds_once", '"ok": true' in retry["result"] and "ok-result" in retry["cls"] and completed_count() == before_token + 1, retry)
    _, ls = hud_dispatch("browser.sessions.list", {}, approve=False, headers=hud_headers())
    for row in ls.get("result", {}).get("sessions", []):
        if row.get("profile_name") == "suite_token_rotation": created_sessions.append(row.get("session_id"))

    # Cleanup only sessions created by the suite, with current token.
    cleanup = []
    for session_id in reversed(list(dict.fromkeys(x for x in created_sessions if x))):
        s, d = hud_dispatch("browser.session.stop", {"session_id": session_id, "timeout_seconds": 15}, approve=True, headers=hud_headers(), timeout=20)
        cleanup.append({"session_id": session_id, "http": s, "ok": d.get("ok"), "error": d.get("error_code")})
    add(checks, "suite_targeted_cleanup", all(x["ok"] for x in cleanup), cleanup)

    # Build identity must not move underneath the suite.
    after_build = build_identity()
    add(checks, "build_identity_stable_during_suite", before_build == after_build, {"before": before_build, "after": after_build})

    report = {
        "schema": "pcmmad.hud-hostile-suite.v2",
        "build_identity": before_build,
        "ui_version": meta().get("ui_version"),
        "live_tool_count": live_count,
        "pass": all(x["pass"] for x in checks),
        "summary": {"passed": sum(1 for x in checks if x["pass"]), "failed": sum(1 for x in checks if not x["pass"])},
        "checks": checks,
    }
    REPORT.parent.mkdir(parents=True, exist_ok=True)
    REPORT.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8", newline="\n")
    print(json.dumps({**report["summary"], "pass": report["pass"], "report": str(REPORT)}, indent=2))
    for item in checks:
        if not item["pass"]:
            print("FAIL", item["name"], json.dumps(item["detail"], indent=2)[:6000])
    return 0 if report["pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
