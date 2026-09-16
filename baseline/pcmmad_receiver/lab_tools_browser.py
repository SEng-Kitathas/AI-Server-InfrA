"""Browser bridge lab-tool registration surface."""

from __future__ import annotations

import time
from dataclasses import dataclass
from lab_tool_primitives import (
    ToolPayload,
    ToolResult,
    payload_bool,
    payload_optional_int,
    payload_optional_str,
    payload_str,
)
from typing import Any, Callable


@dataclass(frozen=True)
class BrowserFillRequest:
    session_id: str
    selector: str
    text: str
    timeout_seconds: int


@dataclass(frozen=True)
class BrowserPromptCaptureRequest:
    session_id: str
    input_selector: str
    prompt: str
    timeout_seconds: int
    max_wait_seconds: int
    poll_interval_seconds: float
    capture_mode: str
    response_selector: str | None
    page_index: int | None
    submit_selector: str | None
    submit_key: str
    take_screenshot: bool
    screenshot_name: str | None


@dataclass(frozen=True)
class BrowserToolDeps:
    bridge_call: Callable[[str, str, ToolResult | None, int], ToolResult]
    bridge_payload_subset: Callable[[ToolPayload, tuple[str, ...] | list[str]], ToolResult]
    bridge_timeout: Callable[[ToolPayload, int, int], int]
    error_cls: type[Exception]


@dataclass(frozen=True)
class BrowserBridgePostSpec:
    path: str
    fields: tuple[str, ...] | list[str]
    timeout_default: int
    timeout_max: int


@dataclass(frozen=True)
class ProcedureResultSpec:
    request: BrowserPromptCaptureRequest
    captured: ToolResult
    timed_out: bool
    poll_attempts: int
    shot: ToolResult | None
    screenshot_error: str | None


@dataclass(frozen=True)
class BrowserToolSpec:
    name: str
    description: str
    danger_tier: str
    category: str
    path: str
    fields: tuple[str, ...] = ()
    timeout_default: int = 30
    timeout_max: int = 120
    mutating: bool = False
    approval_required: bool = False
    input_schema: JsonObject | None = None


@dataclass(frozen=True)
class BrowserBridgeGetSpec:
    path: str
    timeout_default: int
    timeout_max: int


def _browser_deps(deps: ToolPayload) -> BrowserToolDeps:
    return BrowserToolDeps(
        bridge_call=deps["bridge_call"],
        bridge_payload_subset=deps["bridge_payload_subset"],
        bridge_timeout=deps["bridge_timeout"],
        error_cls=deps["error_cls"],
    )


def _capture_request(payload: ToolPayload, dep: BrowserToolDeps) -> BrowserPromptCaptureRequest:
    session_id = payload_str(payload, "session_id").strip()
    input_selector = payload_str(payload, "input_selector").strip()
    if not session_id or not input_selector:
        raise dep.error_cls("BAD_REQUEST", "session_id and input_selector are required", 400)
    timeout_seconds = dep.bridge_timeout(payload, 30, 120)
    return BrowserPromptCaptureRequest(
        session_id=session_id,
        input_selector=input_selector,
        prompt=payload_str(payload, "prompt"),
        timeout_seconds=timeout_seconds,
        max_wait_seconds=max(
            0, min(int(payload.get("max_wait_seconds", payload.get("wait_seconds", 8))), 300)
        ),
        poll_interval_seconds=max(0.1, min(float(payload.get("poll_interval_seconds", 1.0)), 10.0)),
        capture_mode=payload_str(payload, "capture_mode", "body_text"),
        response_selector=payload_optional_str(payload, "response_selector"),
        page_index=payload_optional_int(payload, "page_index"),
        submit_selector=payload_optional_str(payload, "submit_selector"),
        submit_key=payload_str(payload, "submit_key", "Enter"),
        take_screenshot=payload_bool(payload, "take_screenshot", True),
        screenshot_name=payload_optional_str(payload, "screenshot_name"),
    )


def _capture_browser_payload(
    request: BrowserPromptCaptureRequest, dep: BrowserToolDeps
) -> ToolResult:
    if request.capture_mode == "html":
        return dep.bridge_call(
            "POST", "/content", {"session_id": request.session_id}, request.timeout_seconds
        )
    if request.response_selector:
        return dep.bridge_call(
            "POST",
            "/text",
            {"session_id": request.session_id, "selector": request.response_selector},
            request.timeout_seconds,
        )
    return dep.bridge_call(
        "POST",
        "/evaluate",
        {"session_id": request.session_id, "expression": "() => document.body.innerText"},
        request.timeout_seconds,
    )


def _browser_capture_signature(captured: ToolPayload) -> str:
    try:
        return repr(sorted(captured.items()))
    except (TypeError, ValueError):
        return str(captured)


def _browser_capture_has_signal(captured: ToolPayload) -> bool:
    for key in ("text", "content", "raw", "result"):
        value = captured.get(key)
        if isinstance(value, str) and value.strip():
            return True
    return bool(captured)


def _wait_for_browser_capture(
    request: BrowserPromptCaptureRequest, dep: BrowserToolDeps
) -> tuple[ToolResult, bool, int]:
    baseline = _capture_browser_payload(request, dep)
    baseline_signature = _browser_capture_signature(baseline)
    deadline = time.time() + request.max_wait_seconds
    attempts = 0
    latest = baseline
    while time.time() < deadline:
        attempts += 1
        time.sleep(request.poll_interval_seconds)
        latest = _capture_browser_payload(request, dep)
        if _browser_capture_signature(latest) != baseline_signature and _browser_capture_has_signal(
            latest
        ):
            return latest, False, attempts
    return latest, True, attempts


def _bridge_browser_post(
    payload: ToolPayload, spec: BrowserBridgePostSpec, dep: BrowserToolDeps
) -> ToolResult:
    return dep.bridge_call(
        "POST",
        spec.path,
        dep.bridge_payload_subset(payload, spec.fields),
        dep.bridge_timeout(payload, spec.timeout_default, spec.timeout_max),
    )


def _bridge_browser_get(
    payload: ToolPayload, spec: BrowserBridgeGetSpec, dep: BrowserToolDeps
) -> ToolResult:
    return dep.bridge_call(
        "GET", spec.path, None, dep.bridge_timeout(payload, spec.timeout_default, spec.timeout_max)
    )


def _browser_timeout_schema(maximum: int) -> JsonObject:
    return {"timeout_seconds": {"type": "integer", "minimum": 1, "maximum": maximum}}


def _register_bridge_get_tool(
    register_tool: Any, dep: BrowserToolDeps, spec: BrowserToolSpec
) -> None:
    @register_tool(
        spec.name,
        spec.description,
        spec.danger_tier,
        category=spec.category,
        side_effect_class="external_read",
        effect_traits=["network_io", "reads_external_state", "bridge_scoped", "bounded_wait"],
        input_schema={
            "type": "object",
            "properties": _browser_timeout_schema(spec.timeout_max),
            "additionalProperties": False,
        },
    )
    def tool(payload: ToolPayload) -> ToolResult:
        return _bridge_browser_get(
            payload, BrowserBridgeGetSpec(spec.path, spec.timeout_default, spec.timeout_max), dep
        )


def _bridge_payload_schema(
    required: list[str], properties: JsonObject, additional: bool = False
) -> JsonObject:
    schema: JsonObject = {
        "type": "object",
        "properties": properties,
        "additionalProperties": additional,
    }
    if required:
        schema["required"] = required
    return schema


def _register_bridge_post_tool(
    register_tool: Any, dep: BrowserToolDeps, spec: BrowserToolSpec
) -> None:
    @register_tool(
        spec.name,
        spec.description,
        spec.danger_tier,
        category=spec.category,
        mutating=spec.mutating,
        approval_required=spec.approval_required,
        side_effect_class=(
            "external_interaction"
            if spec.name in {"browser.evaluate", "browser.screenshot"}
            else "external_read"
            if not spec.mutating
            else ""
        ),
        effect_traits=(
            ["executes_code", "external_interaction", "may_mutate_external_state", "network_io"]
            if spec.name == "browser.evaluate"
            else ["network_io", "reads_external_state", "captures_visual_state", "may_write_external_artifact", "bridge_scoped", "bounded_wait"]
            if spec.name == "browser.screenshot"
            else ["network_io", "reads_external_state", "bridge_scoped", "bounded_wait"]
            if not spec.mutating
            else []
        ),
        input_schema=spec.input_schema,
    )
    def tool(payload: ToolPayload) -> ToolResult:
        return _bridge_browser_post(
            payload,
            BrowserBridgePostSpec(
                spec.path, tuple(spec.fields), spec.timeout_default, spec.timeout_max
            ),
            dep,
        )


def _register_browser_health_tools(register_tool: Any, dep: BrowserToolDeps) -> None:
    _register_bridge_get_tool(
        register_tool,
        dep,
        BrowserToolSpec(
            "browser.health",
            "Check browser automation bridge health.",
            "low",
            "browser",
            "/health",
            timeout_default=10,
            timeout_max=30,
        ),
    )
    _register_bridge_get_tool(
        register_tool,
        dep,
        BrowserToolSpec(
            "browser.sessions.list",
            "List active browser bridge sessions.",
            "low",
            "browser",
            "/sessions",
            timeout_default=10,
            timeout_max=30,
        ),
    )


def _browser_session_attach_spec() -> BrowserToolSpec:
    return BrowserToolSpec(
        "browser.session.attach",
        "Attach to a running debug browser session via the local bridge.",
        "high",
        "browser",
        "/session/attach",
        ("cdp_url", "browser", "profile_name", "url"),
        30,
        120,
        True,
        True,
        _bridge_payload_schema(
            ["cdp_url"],
            {
                "cdp_url": {"type": "string", "minLength": 1},
                "browser": {"type": "string"},
                "profile_name": {"type": "string"},
                "url": {"type": "string"},
                **_browser_timeout_schema(120),
            },
        ),
    )


def _browser_session_start_spec() -> BrowserToolSpec:
    return BrowserToolSpec(
        "browser.session.start",
        "Start a browser session through the local bridge.",
        "high",
        "browser",
        "/session/start",
        ("browser", "headless", "url", "persistent", "profile_name"),
        30,
        120,
        True,
        True,
        _bridge_payload_schema(
            [],
            {
                "browser": {"type": "string"},
                "headless": {"type": "boolean"},
                "url": {"type": "string"},
                "persistent": {"type": "boolean"},
                "profile_name": {"type": "string"},
                **_browser_timeout_schema(120),
            },
        ),
    )


def _browser_session_stop_spec() -> BrowserToolSpec:
    return BrowserToolSpec(
        "browser.session.stop",
        "Stop a browser bridge session.",
        "high",
        "browser",
        "/session/stop",
        ("session_id",),
        30,
        120,
        True,
        True,
        _bridge_payload_schema(
            ["session_id"],
            {"session_id": {"type": "string", "minLength": 1}, **_browser_timeout_schema(120)},
        ),
    )


def _browser_session_specs() -> list[BrowserToolSpec]:
    return [
        _browser_session_attach_spec(),
        _browser_session_start_spec(),
        _browser_session_stop_spec(),
    ]


def _browser_page_list_spec(session: JsonObject) -> BrowserToolSpec:
    return BrowserToolSpec(
        "browser.pages.list",
        "List tabs/pages in a browser bridge session.",
        "low",
        "browser",
        "/pages/list",
        ("session_id",),
        15,
        60,
        False,
        False,
        _bridge_payload_schema(["session_id"], {**session, **_browser_timeout_schema(60)}),
    )


def _browser_page_select_spec(session: JsonObject, index: JsonObject) -> BrowserToolSpec:
    return BrowserToolSpec(
        "browser.pages.select",
        "Select a tab/page in a browser bridge session.",
        "medium",
        "browser",
        "/pages/select",
        ("session_id", "index"),
        15,
        60,
        True,
        False,
        _bridge_payload_schema(
            ["session_id", "index"], {**session, **index, **_browser_timeout_schema(60)}
        ),
    )


def _browser_page_new_spec(session: JsonObject) -> BrowserToolSpec:
    return BrowserToolSpec(
        "browser.pages.new",
        "Open a new tab in a browser bridge session.",
        "medium",
        "browser",
        "/pages/new",
        ("session_id", "url"),
        15,
        60,
        True,
        False,
        _bridge_payload_schema(
            ["session_id"], {**session, "url": {"type": "string"}, **_browser_timeout_schema(60)}
        ),
    )


def _browser_page_close_spec(session: JsonObject, index: JsonObject) -> BrowserToolSpec:
    return BrowserToolSpec(
        "browser.pages.close",
        "Close a tab in a browser bridge session.",
        "high",
        "browser",
        "/pages/close",
        ("session_id", "index"),
        15,
        60,
        True,
        True,
        _bridge_payload_schema(
            ["session_id", "index"], {**session, **index, **_browser_timeout_schema(60)}
        ),
    )


def _browser_page_specs() -> list[BrowserToolSpec]:
    session = {"session_id": {"type": "string", "minLength": 1}}
    index = {"index": {"type": "integer", "minimum": 0}}
    return [
        _browser_page_list_spec(session),
        _browser_page_select_spec(session, index),
        _browser_page_new_spec(session),
        _browser_page_close_spec(session, index),
    ]


def _browser_navigate_spec(session: JsonObject) -> BrowserToolSpec:
    return BrowserToolSpec(
        "browser.navigate",
        "Navigate the current browser bridge page.",
        "medium",
        "browser",
        "/navigate",
        ("session_id", "url"),
        30,
        120,
        True,
        False,
        _bridge_payload_schema(
            ["session_id", "url"],
            {**session, "url": {"type": "string", "minLength": 1}, **_browser_timeout_schema(120)},
        ),
    )


def _browser_click_spec(session: JsonObject, selector: JsonObject) -> BrowserToolSpec:
    return BrowserToolSpec(
        "browser.click",
        "Click a selector in the browser bridge.",
        "medium",
        "browser",
        "/click",
        ("session_id", "selector"),
        30,
        120,
        True,
        False,
        _bridge_payload_schema(
            ["session_id", "selector"], {**session, **selector, **_browser_timeout_schema(120)}
        ),
    )


def _browser_press_spec(session: JsonObject, selector: JsonObject) -> BrowserToolSpec:
    return BrowserToolSpec(
        "browser.press",
        "Press a key on a selector in the browser bridge.",
        "medium",
        "browser",
        "/press",
        ("session_id", "selector", "key"),
        30,
        120,
        True,
        False,
        _bridge_payload_schema(
            ["session_id", "selector", "key"],
            {
                **session,
                **selector,
                "key": {"type": "string", "minLength": 1},
                **_browser_timeout_schema(120),
            },
        ),
    )



def _browser_upload_spec(session: JsonObject, selector: JsonObject) -> BrowserToolSpec:
    return BrowserToolSpec(
        "browser.upload",
        "Set one or more local files on a browser file-input selector.",
        "high",
        "browser",
        "/upload",
        ("session_id", "selector", "paths"),
        30,
        120,
        True,
        True,
        _bridge_payload_schema(
            ["session_id", "selector", "paths"],
            {
                **session,
                **selector,
                "paths": {
                    "type": "array",
                    "minItems": 1,
                    "items": {"type": "string", "minLength": 1},
                },
                **_browser_timeout_schema(120),
            },
        ),
    )


def _browser_action_specs() -> list[BrowserToolSpec]:
    session = {"session_id": {"type": "string", "minLength": 1}}
    selector = {"selector": {"type": "string", "minLength": 1}}
    return [
        _browser_navigate_spec(session),
        _browser_click_spec(session, selector),
        _browser_press_spec(session, selector),
        _browser_upload_spec(session, selector),
    ]


def _browser_content_spec(session: JsonObject) -> BrowserToolSpec:
    return BrowserToolSpec(
        "browser.content",
        "Capture page HTML from the browser bridge.",
        "medium",
        "browser",
        "/content",
        ("session_id",),
        30,
        120,
        False,
        False,
        _bridge_payload_schema(["session_id"], {**session, **_browser_timeout_schema(120)}),
    )


def _browser_evaluate_spec(session: JsonObject) -> BrowserToolSpec:
    return BrowserToolSpec(
        "browser.evaluate",
        "Evaluate JavaScript in the browser bridge.",
        "high",
        "browser",
        "/evaluate",
        ("session_id", "expression"),
        30,
        120,
        False,
        True,
        _bridge_payload_schema(
            ["session_id", "expression"],
            {
                **session,
                "expression": {"type": "string", "minLength": 1},
                **_browser_timeout_schema(120),
            },
        ),
    )


def _browser_screenshot_spec(session: JsonObject) -> BrowserToolSpec:
    return BrowserToolSpec(
        "browser.screenshot",
        "Capture a screenshot through the browser bridge.",
        "medium",
        "browser",
        "/screenshot",
        ("session_id", "name"),
        30,
        120,
        False,
        False,
        _bridge_payload_schema(
            ["session_id"], {**session, "name": {"type": "string"}, **_browser_timeout_schema(120)}
        ),
    )


def _browser_capture_specs() -> list[BrowserToolSpec]:
    session = {"session_id": {"type": "string", "minLength": 1}}
    return [
        _browser_content_spec(session),
        _browser_evaluate_spec(session),
        _browser_screenshot_spec(session),
    ]


def _register_browser_session_tools(register_tool: Any, dep: BrowserToolDeps) -> None:
    for spec in _browser_session_specs():
        _register_bridge_post_tool(register_tool, dep, spec)


def _browser_fill_payload(payload: ToolPayload, dep: BrowserToolDeps) -> ToolResult:
    request = BrowserFillRequest(
        session_id=payload_str(payload, "session_id").strip(),
        selector=payload_str(payload, "selector").strip(),
        text=payload_str(payload, "text"),
        timeout_seconds=dep.bridge_timeout(payload, 30, 120),
    )
    return dep.bridge_call(
        "POST",
        "/fill",
        {"session_id": request.session_id, "selector": request.selector, "text": request.text},
        request.timeout_seconds,
    )


def _register_browser_page_tools(register_tool: Any, dep: BrowserToolDeps) -> None:
    for spec in _browser_page_specs():
        _register_bridge_post_tool(register_tool, dep, spec)


def _register_browser_action_tools(register_tool: Any, dep: BrowserToolDeps) -> None:
    for spec in _browser_action_specs():
        _register_bridge_post_tool(register_tool, dep, spec)

    @register_tool(
        "browser.fill",
        "Fill a selector in the browser bridge.",
        "medium",
        category="browser",
        mutating=True,
        input_schema=_bridge_payload_schema(
            ["session_id", "selector", "text"],
            {
                "session_id": {"type": "string", "minLength": 1},
                "selector": {"type": "string", "minLength": 1},
                "text": {"type": "string"},
                **_browser_timeout_schema(120),
            },
        ),
    )
    def tool_browser_fill(payload: ToolPayload) -> ToolResult:
        return _browser_fill_payload(payload, dep)


def _register_browser_capture_tools(register_tool: Any, dep: BrowserToolDeps) -> None:
    for spec in _browser_capture_specs():
        _register_bridge_post_tool(register_tool, dep, spec)


def _procedure_select_page(request: BrowserPromptCaptureRequest, dep: BrowserToolDeps) -> None:
    if request.page_index is not None:
        dep.bridge_call(
            "POST",
            "/pages/select",
            {"session_id": request.session_id, "index": request.page_index},
            request.timeout_seconds,
        )


def _procedure_submit_prompt(request: BrowserPromptCaptureRequest, dep: BrowserToolDeps) -> None:
    dep.bridge_call(
        "POST",
        "/fill",
        {
            "session_id": request.session_id,
            "selector": request.input_selector,
            "text": request.prompt,
        },
        request.timeout_seconds,
    )
    if request.submit_selector:
        dep.bridge_call(
            "POST",
            "/click",
            {"session_id": request.session_id, "selector": request.submit_selector},
            request.timeout_seconds,
        )
    else:
        dep.bridge_call(
            "POST",
            "/press",
            {
                "session_id": request.session_id,
                "selector": request.input_selector,
                "key": request.submit_key,
            },
            request.timeout_seconds,
        )


def _procedure_screenshot(
    request: BrowserPromptCaptureRequest, dep: BrowserToolDeps
) -> tuple[ToolResult | None, str | None]:
    if not request.take_screenshot:
        return None, None
    try:
        return (
            dep.bridge_call(
                "POST",
                "/screenshot",
                {"session_id": request.session_id, "name": request.screenshot_name},
                request.timeout_seconds,
            ),
            None,
        )
    except (OSError, RuntimeError, ValueError, TypeError) as exc:
        return None, str(exc)


def _procedure_result(spec: ProcedureResultSpec) -> ToolResult:
    return {
        "session_id": spec.request.session_id,
        "capture_mode": spec.request.capture_mode,
        "captured": spec.captured,
        "timed_out": spec.timed_out,
        "poll_attempts": spec.poll_attempts,
        "max_wait_seconds": spec.request.max_wait_seconds,
        "poll_interval_seconds": spec.request.poll_interval_seconds,
        "response_selector": spec.request.response_selector,
        "screenshot": spec.shot,
        "screenshot_error": spec.screenshot_error,
    }


def _procedure_prompt_capture_payload(payload: ToolPayload, dep: BrowserToolDeps) -> ToolResult:
    request = _capture_request(payload, dep)
    _procedure_select_page(request, dep)
    _procedure_submit_prompt(request, dep)
    captured, timed_out, poll_attempts = _wait_for_browser_capture(request, dep)
    shot, screenshot_error = _procedure_screenshot(request, dep)
    return _procedure_result(
        ProcedureResultSpec(request, captured, timed_out, poll_attempts, shot, screenshot_error)
    )


def _prompt_capture_schema() -> JsonObject:
    return _bridge_payload_schema(
        ["session_id", "input_selector", "prompt"],
        {
            "session_id": {"type": "string", "minLength": 1},
            "input_selector": {"type": "string", "minLength": 1},
            "prompt": {"type": "string"},
            "max_wait_seconds": {"type": "integer", "minimum": 0, "maximum": 300},
            "wait_seconds": {"type": "integer", "minimum": 0, "maximum": 300},
            "poll_interval_seconds": {"type": "number", "minimum": 0.1, "maximum": 10.0},
            "capture_mode": {"type": "string"},
            "response_selector": {"type": "string"},
            "page_index": {"type": "integer", "minimum": 0},
            "submit_selector": {"type": "string"},
            "submit_key": {"type": "string"},
            "take_screenshot": {"type": "boolean"},
            "screenshot_name": {"type": "string"},
            **_browser_timeout_schema(120),
        },
    )


def _register_browser_procedure_tools(register_tool: Any, dep: BrowserToolDeps) -> None:
    @register_tool(
        "procedure.browser.prompt_capture",
        "Server-side browser prompt, submit, wait, and capture procedure.",
        "high",
        category="procedure",
        mutating=True,
        approval_required=True,
        input_schema=_prompt_capture_schema(),
    )
    def tool_procedure_browser_prompt_capture(payload: ToolPayload) -> ToolResult:
        return _procedure_prompt_capture_payload(payload, dep)


def _browser_bridge_availability(dep: BrowserToolDeps) -> ToolResult:
    try:
        result = dep.bridge_call("GET", "/health", None, 5)
        ok = bool(result.get("ok", True)) if isinstance(result, dict) else True
        return {
            "status": "available" if ok else "degraded",
            "available": True if ok else None,
            "blockers": [] if ok else ["browser_bridge_health_degraded"],
            "basis": "browser_bridge_health",
        }
    except Exception as exc:
        return {
            "status": "unavailable",
            "available": False,
            "blockers": ["browser_bridge_unavailable"],
            "basis": "browser_bridge_health",
            "error": str(exc)[:500],
        }


def register_browser_tools(
    register_tool: Callable[
        ..., Callable[[Callable[[ToolPayload], ToolResult]], Callable[[ToolPayload], ToolResult]]
    ],
    **deps: Any,
) -> None:
    dep = _browser_deps(deps)
    availability_provider = lambda: _browser_bridge_availability(dep)

    def browser_register_tool(*args: Any, **metadata: Any) -> Any:
        metadata.setdefault("availability_mode", "dynamic")
        metadata.setdefault("availability_scope", "browser_bridge")
        metadata.setdefault("availability_provider_id", "browser_bridge")
        metadata.setdefault("availability_provider", availability_provider)
        return register_tool(*args, **metadata)

    _register_browser_health_tools(browser_register_tool, dep)
    _register_browser_session_tools(browser_register_tool, dep)
    _register_browser_page_tools(browser_register_tool, dep)
    _register_browser_action_tools(browser_register_tool, dep)
    _register_browser_capture_tools(browser_register_tool, dep)
    _register_browser_procedure_tools(browser_register_tool, dep)
