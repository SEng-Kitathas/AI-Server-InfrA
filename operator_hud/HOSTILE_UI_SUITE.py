from __future__ import annotations

import json
import time
import urllib.error
import urllib.request
from pathlib import Path

HUD = "http://127.0.0.1:5090"
BRIDGE = "http://127.0.0.1:4471"
ROOT = Path(__file__).resolve().parents[1]
REPORT = ROOT / "state" / "trace_matrix" / "HUD_HOSTILE_SUITE_REPORT_2026-09-01.json"
UPLOAD_PROBE = ROOT / "state" / "trace_matrix" / "HUD_UPLOAD_PROBE.txt"


def call(url: str, obj=None, timeout: float = 30):
    data = None if obj is None else json.dumps(obj).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=data,
        headers={"Content-Type": "application/json"} if data else {},
        method="POST" if data else "GET",
    )
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


def hud_dispatch(tool_name: str, payload: dict, approve: bool = False, timeout: float = 30):
    return call(
        HUD + "/api/dispatch",
        {"tool_name": tool_name, "payload": payload, "approve": approve},
        timeout,
    )


def bridge_eval(session_id: str, expression: str):
    status, body = call(BRIDGE + "/evaluate", {"session_id": session_id, "expression": expression}, 20)
    if status != 200 or not body.get("ok"):
        raise RuntimeError(f"bridge evaluate failed: {status} {body}")
    return body.get("result")


def parse_eval_json(session_id: str, expression: str):
    raw = bridge_eval(session_id, f"JSON.stringify({expression})")
    return json.loads(raw)


def assert_check(checks, name: str, condition: bool, detail=None):
    checks.append({"name": name, "pass": bool(condition), "detail": detail})


def main() -> int:
    checks = []
    created_sessions: list[str] = []

    # Baseline component health.
    status, health = call(HUD + "/api/health", timeout=5)
    assert_check(checks, "hud_health_http_200", status == 200, health)
    assert_check(checks, "receiver_visible_online", health.get("receiver", {}).get("ok") is True, health)
    assert_check(checks, "bridge_visible_online", health.get("browser_bridge", {}).get("ok") is True, health)
    assert_check(checks, "api_key_not_exposed", health.get("hud", {}).get("api_key_exposed_to_browser") is False, health)

    status, tools = call(HUD + "/api/tools", timeout=5)
    catalog = tools.get("tools", [])
    assert_check(checks, "tool_catalog_available", status == 200 and len(catalog) >= 1, {"count": len(catalog)})
    live_count = len(catalog)

    # Raw approval smuggling must fail if the explicit HUD approve bit is false.
    smuggle_payload = {
        "browser": "chrome",
        "headless": True,
        "persistent": False,
        "profile_name": "hud_raw_approval_smuggle_probe",
        "url": "about:blank",
        "timeout_seconds": 15,
        "approval": {"permit": True, "source": "raw-json-smuggle"},
    }
    status, body = hud_dispatch("browser.session.start", smuggle_payload, approve=False)
    assert_check(
        checks,
        "raw_json_cannot_smuggle_approval",
        status == 403 and body.get("error_code") == "APPROVAL_REQUIRED",
        body,
    )

    # Start a fresh browser session displaying the current HUD.
    status, body = hud_dispatch(
        "browser.session.start",
        {
            "browser": "chrome",
            "headless": True,
            "persistent": False,
            "profile_name": "hud_hostile_suite",
            "url": HUD + "/",
            "timeout_seconds": 30,
        },
        approve=True,
        timeout=45,
    )
    hud_sid = body.get("result", {}).get("session_id")
    assert_check(checks, "hud_browser_session_start", status == 200 and bool(hud_sid), body)
    if not hud_sid:
        raise RuntimeError("cannot continue without HUD browser session")
    created_sessions.append(hud_sid)
    time.sleep(0.8)

    visible = parse_eval_json(
        hud_sid,
        "({hud:[hudStatus.textContent,hudStatus.className],recv:[receiverStatus.textContent,receiverStatus.className],bridge:[bridgeStatus.textContent,bridgeStatus.className],placeholder:toolSearch.placeholder,count:toolCount.textContent})",
    )
    assert_check(checks, "hud_status_visible", visible["hud"][0] == "HUD online" and "ok" in visible["hud"][1], visible)
    assert_check(checks, "receiver_status_visible", visible["recv"][0] == "receiver online" and "ok" in visible["recv"][1], visible)
    assert_check(checks, "bridge_status_visible", visible["bridge"][0] == "browser bridge online" and "ok" in visible["bridge"][1], visible)
    assert_check(checks, "tool_count_not_stale", str(live_count) in visible["placeholder"] and str(live_count) in visible["count"], visible)

    # Sweep all currently rendered tools.
    sweep_raw = bridge_eval(
        hud_sid,
        r'''(()=>{
 const failures=[]; const opaque=[]; const observations=[];
 const tools=[...document.querySelectorAll('.tool-item')];
 for(const item of tools){
   const name=item.querySelector('.tool-title')?.textContent||'?';
   try{
     item.click();
     const hidden=approvalBox.classList.contains('hidden');
     const approved=approveToggle.checked;
     let jsonOk=true; try{JSON.parse(rawPayload.value||'{}')}catch(e){jsonOk=false}
     const badges=[...toolBadges.querySelectorAll('.badge')].map(x=>x.textContent);
     const needs=badges.includes('approval');
     const fields=[...schemaForm.querySelectorAll('[data-field]')].map(x=>x.dataset.field);
     const warning=schemaForm.querySelector('.schema-warning')?.textContent||'';
     if(hidden===needs) failures.push({name,kind:'approval_visibility',hidden,needs,badges});
     if(needs && approved) failures.push({name,kind:'approval_default_checked'});
     if(!jsonOk) failures.push({name,kind:'generated_json_invalid',raw:rawPayload.value});
     if(fields.length===0) opaque.push({name,warning});
     observations.push({name,needs,fields});
   }catch(e){failures.push({name,kind:'render_exception',error:String(e)})}
 }
 return JSON.stringify({toolCount:tools.length,failures,opaque,approvalTools:observations.filter(x=>x.needs).length});
})()''',
    )
    sweep = json.loads(sweep_raw)
    assert_check(checks, "all_live_tools_rendered", sweep["toolCount"] == live_count, sweep)
    assert_check(checks, "all_tool_renders_exception_free", not sweep["failures"], sweep["failures"])
    assert_check(
        checks,
        "opaque_schemas_are_explicitly_labeled",
        all("opaque object schema" in row.get("warning", "") for row in sweep["opaque"]),
        {"opaque_count": len(sweep["opaque"]), "bad": [x for x in sweep["opaque"] if "opaque object schema" not in x.get("warning", "")]},
    )

    # Critical action must visibly require approval and default to unchecked.
    critical = parse_eval_json(
        hud_sid,
        '''(()=>{const x=[...document.querySelectorAll('.tool-item')].find(e=>e.querySelector('.tool-title')?.textContent==='execution.terminate');x.click();return {badges:[...toolBadges.querySelectorAll('.badge')].map(e=>e.textContent),approvalHidden:approvalBox.classList.contains('hidden'),checked:approveToggle.checked}})()''',
    )
    assert_check(checks, "critical_tool_labeled_critical", "critical" in critical["badges"], critical)
    assert_check(checks, "critical_tool_approval_visible", critical["approvalHidden"] is False and critical["checked"] is False, critical)

    # Unchecked UI dispatch must block locally.
    unchecked = bridge_eval(
        hud_sid,
        '''(()=>{const x=[...document.querySelectorAll('.tool-item')].find(e=>e.querySelector('.tool-title')?.textContent==='browser.session.start');x.click();rawPayload.value=JSON.stringify({browser:'chrome',headless:true,persistent:false,profile_name:'ui_unchecked_suite',url:'about:blank',timeout_seconds:15});dispatchBtn.click();return resultBox.textContent})()''',
    )
    assert_check(checks, "unchecked_approval_blocks_locally", unchecked.startswith("Approval required."), unchecked)

    # Double click must not duplicate a dispatch and approval must reset after success.
    _, before = hud_dispatch("browser.sessions.list", {})
    before_count = len(before.get("result", {}).get("sessions", []))
    bridge_eval(
        hud_sid,
        '''(()=>{rawPayload.value=JSON.stringify({browser:'chrome',headless:true,persistent:false,profile_name:'ui_double_suite',url:'about:blank',timeout_seconds:15});approveToggle.checked=true;dispatchBtn.click();dispatchBtn.click();return true})()''',
    )
    time.sleep(1.1)
    _, after = hud_dispatch("browser.sessions.list", {})
    sessions_after = after.get("result", {}).get("sessions", [])
    after_count = len(sessions_after)
    new_ids = [row.get("session_id") for row in sessions_after if row.get("session_id") not in {x.get("session_id") for x in before.get("result", {}).get("sessions", [])}]
    created_sessions.extend([x for x in new_ids if x])
    dispatch_state = parse_eval_json(hud_sid, "({checked:approveToggle.checked,disabled:dispatchBtn.disabled,result:resultBox.textContent,resultClass:resultBox.className})")
    assert_check(checks, "double_click_single_dispatch", after_count - before_count == 1, {"before": before_count, "after": after_count, "new": new_ids})
    assert_check(checks, "approval_resets_after_dispatch", dispatch_state["checked"] is False, dispatch_state)
    assert_check(checks, "successful_result_visibly_marked", "ok-result" in dispatch_state["resultClass"], dispatch_state)

    # Malformed JSON should never hit backend.
    malformed = bridge_eval(hud_sid, "rawPayload.value='{bad json';dispatchBtn.click();JSON.stringify({text:resultBox.textContent,cls:resultBox.className})")
    malformed = json.loads(malformed)
    assert_check(checks, "malformed_json_blocked_locally", malformed["text"].startswith("Invalid JSON:") and "bad-result" in malformed["cls"], malformed)

    # Upload: create a target browser session and a native file input.
    UPLOAD_PROBE.parent.mkdir(parents=True, exist_ok=True)
    UPLOAD_PROBE.write_text("pcmmad hostile upload probe\n", encoding="utf-8", newline="\n")
    status, body = hud_dispatch(
        "browser.session.start",
        {"browser": "chrome", "headless": True, "persistent": False, "profile_name": "hud_upload_suite_target", "url": "about:blank", "timeout_seconds": 15},
        approve=True,
    )
    target_sid = body.get("result", {}).get("session_id")
    assert_check(checks, "upload_target_session_start", status == 200 and bool(target_sid), body)
    if target_sid:
        created_sessions.append(target_sid)
        bridge_eval(target_sid, "document.body.innerHTML='<input id=\"u\" type=\"file\">';'ready'")
        bridge_eval(
            hud_sid,
            f'''(()=>{{const x=[...document.querySelectorAll('.tool-item')].find(e=>e.querySelector('.tool-title')?.textContent==='browser.upload');x.click();rawPayload.value={json.dumps(json.dumps({'session_id': target_sid, 'selector': '#u', 'paths': [str(UPLOAD_PROBE.resolve())], 'timeout_seconds': 30}))};approveToggle.checked=true;dispatchBtn.click();return true}})()''',
        )
        time.sleep(0.7)
        uploaded = json.loads(bridge_eval(target_sid, "JSON.stringify([...document.querySelector('#u').files].map(f=>({name:f.name,size:f.size})))"))
        up_state = parse_eval_json(hud_sid, "({checked:approveToggle.checked,result:resultBox.textContent,resultClass:resultBox.className})")
        assert_check(checks, "upload_reaches_target_file_input", len(uploaded) == 1 and uploaded[0]["name"] == UPLOAD_PROBE.name, uploaded)
        assert_check(checks, "upload_approval_resets", up_state["checked"] is False, up_state)
        assert_check(checks, "upload_success_visibly_marked", "ok-result" in up_state["resultClass"], up_state)

    # Cleanup only sessions created by this suite.
    cleanup = []
    for session_id in reversed(list(dict.fromkeys(created_sessions))):
        status, body = hud_dispatch("browser.session.stop", {"session_id": session_id, "timeout_seconds": 20}, approve=True)
        cleanup.append({"session_id": session_id, "status": status, "body": body})
    assert_check(checks, "suite_session_cleanup", all(x["status"] == 200 and x["body"].get("ok") for x in cleanup), cleanup)

    report = {
        "schema": "pcmmad.hud-hostile-suite.v1",
        "live_tool_count": live_count,
        "pass": all(x["pass"] for x in checks),
        "checks": checks,
        "summary": {"passed": sum(1 for x in checks if x["pass"]), "failed": sum(1 for x in checks if not x["pass"])},
    }
    REPORT.parent.mkdir(parents=True, exist_ok=True)
    REPORT.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8", newline="\n")
    print(json.dumps(report["summary"] | {"pass": report["pass"], "report": str(REPORT)}, indent=2))
    if not report["pass"]:
        for item in checks:
            if not item["pass"]:
                print("FAIL", item["name"], json.dumps(item["detail"], indent=2)[:5000])
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
