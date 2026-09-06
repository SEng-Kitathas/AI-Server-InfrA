"""Optional local Playwright browser bridge for PCMMAD receiver browser tools."""

from __future__ import annotations

import argparse
import base64
import os
import time
import uuid
from pathlib import Path
from typing import TypedDict

from flask import Flask, jsonify, request
from flask.typing import ResponseReturnValue
from playwright.sync_api import Error as PlaywrightError
from playwright.sync_api import sync_playwright


class JsonPayload(TypedDict, total=False):
    ok: bool


class BrowserSession(TypedDict, total=False):
    session_id: str
    kind: str
    browser: object
    context: object
    profile_name: str | None
    cdp_url: str | None
    page_index: int
    created_at: float


class NewSessionSpec(TypedDict, total=False):
    kind: str
    browser: object
    context: object
    profile_name: str | None
    cdp_url: str | None


BRIDGE_FAILURES = (PlaywrightError, RuntimeError, ValueError, TypeError, OSError)


app = Flask(__name__)
PW = None
SESSIONS: dict[str, BrowserSession] = {}
STARTED_AT = time.time()
SCREENSHOT_DIR = Path(
    os.environ.get("PCMMAD_BROWSER_SCREENSHOT_DIR", str(Path.cwd() / "browser_screenshots"))
)
SCREENSHOT_DIR.mkdir(parents=True, exist_ok=True)


def _json() -> JsonPayload:
    data = request.get_json(silent=True)
    return data if isinstance(data, dict) else {}


def _ok(**extra: object) -> ResponseReturnValue:
    return jsonify({"ok": True, **extra})


def _err(code: str, message: str, status: int = 400, **extra: object) -> ResponseReturnValue:
    return jsonify({"ok": False, "error_code": code, "message": message, **extra}), status


def _session(session_id: str) -> BrowserSession:
    sess = SESSIONS.get(session_id)
    if not sess:
        raise KeyError(session_id)
    return sess


def _pages(sess: BrowserSession) -> list[object]:
    pages = []
    browser = sess.get("browser")
    context = sess.get("context")
    if context is not None:
        pages.extend(context.pages)
    elif browser is not None:
        for ctx in browser.contexts:
            pages.extend(ctx.pages)
    return pages


def _page(sess: BrowserSession) -> object:
    pages = _pages(sess)
    if not pages:
        context = sess.get("context")
        if context is not None:
            return context.new_page()
        browser = sess.get("browser")
        if browser is not None:
            if browser.contexts:
                return browser.contexts[0].new_page()
            return browser.new_context().new_page()
        raise RuntimeError("session has no browser/context")
    idx = max(0, min(int(sess.get("page_index", 0)), len(pages) - 1))
    sess["page_index"] = idx
    return pages[idx]


def _page_card(page: object, index: int) -> JsonPayload:
    try:
        title = page.title()
    except BRIDGE_FAILURES:
        title = None
    try:
        url = page.url
    except BRIDGE_FAILURES:
        url = None
    return {"index": index, "title": title, "url": url, "closed": page.is_closed()}


def _new_session(spec: NewSessionSpec) -> str:
    session_id = f"br-{uuid.uuid4().hex[:12]}"
    SESSIONS[session_id] = {
        "session_id": session_id,
        "kind": str(spec.get("kind", "browser")),
        "browser": spec.get("browser"),
        "context": spec.get("context"),
        "profile_name": spec.get("profile_name"),
        "cdp_url": spec.get("cdp_url"),
        "page_index": 0,
        "created_at": time.time(),
    }
    return session_id


def _browser_channel(name: str | None) -> str | None:
    if not name:
        return None
    normalized_name = name.lower().strip()
    if normalized_name in {"edge", "msedge", "microsoft-edge"}:
        return "msedge"
    if normalized_name in {"chrome", "google-chrome"}:
        return "chrome"
    return None


@app.get("/health")
def health() -> ResponseReturnValue:
    return _ok(
        service="pcmmad_browser_bridge",
        uptime_seconds=round(time.time() - STARTED_AT, 3),
        sessions=len(SESSIONS),
        playwright=PW is not None,
        pid=os.getpid(),
        screenshot_dir=str(SCREENSHOT_DIR),
    )


@app.get("/sessions")
def sessions() -> ResponseReturnValue:
    out = []
    for sid, sess in SESSIONS.items():
        pages = _pages(sess)
        out.append(
            {
                "session_id": sid,
                "kind": sess.get("kind"),
                "profile_name": sess.get("profile_name"),
                "cdp_url": sess.get("cdp_url"),
                "page_index": sess.get("page_index", 0),
                "page_count": len(pages),
                "created_at": sess.get("created_at"),
            }
        )
    return _ok(sessions=out)


@app.post("/session/attach")
def session_attach() -> ResponseReturnValue:
    data = _json()
    cdp_url = str(data.get("cdp_url", "")).strip()
    if not cdp_url:
        return _err("BAD_REQUEST", "cdp_url is required")
    try:
        browser = PW.chromium.connect_over_cdp(cdp_url)
        sid = _new_session(
            NewSessionSpec(
                kind="cdp",
                browser=browser,
                profile_name=data.get("profile_name"),
                cdp_url=cdp_url,
            )
        )
        if data.get("url"):
            page = _page(SESSIONS[sid])
            page.goto(str(data["url"]), wait_until="domcontentloaded")
        return _ok(
            session_id=sid,
            cdp_url=cdp_url,
            pages=[_page_card(p, i) for i, p in enumerate(_pages(SESSIONS[sid]))],
        )
    except BRIDGE_FAILURES as exc:
        return _err("CDP_ATTACH_FAILED", str(exc), 502, cdp_url=cdp_url)


def _start_persistent_session(headless: bool, channel: str | None, profile_name: str) -> str:
    profile_dir = Path(os.environ.get("TEMP", str(Path.cwd()))) / profile_name
    context = PW.chromium.launch_persistent_context(
        str(profile_dir), headless=headless, channel=channel
    )
    return _new_session(
        NewSessionSpec(kind="persistent", context=context, profile_name=profile_name)
    )


def _start_launched_session(headless: bool, channel: str | None, profile_name: str) -> str:
    browser = PW.chromium.launch(headless=headless, channel=channel)
    context = browser.new_context()
    return _new_session(
        NewSessionSpec(kind="launched", browser=browser, context=context, profile_name=profile_name)
    )


def _maybe_open_start_url(session_id: str, data: JsonPayload) -> None:
    if data.get("url"):
        page = _page(SESSIONS[session_id])
        page.goto(str(data["url"]), wait_until="domcontentloaded")


@app.post("/session/start")
def session_start() -> ResponseReturnValue:
    data = _json()
    headless = bool(data.get("headless", False))
    persistent = bool(data.get("persistent", False))
    profile_name = str(data.get("profile_name") or "pcmmad-browser")
    browser_name = data.get("browser")
    channel = _browser_channel(browser_name)
    try:
        if persistent:
            sid = _start_persistent_session(headless, channel, profile_name)
        else:
            sid = _start_launched_session(headless, channel, profile_name)
        _maybe_open_start_url(sid, data)
        pages = [_page_card(page, index) for index, page in enumerate(_pages(SESSIONS[sid]))]
        return _ok(session_id=sid, pages=pages)
    except BRIDGE_FAILURES as exc:
        return _err("BROWSER_START_FAILED", str(exc), 502, browser=browser_name, channel=channel)


@app.post("/session/stop")
def session_stop() -> ResponseReturnValue:
    sid = str(_json().get("session_id", ""))
    sess = SESSIONS.pop(sid, None)
    if not sess:
        return _err("NOT_FOUND", "unknown session_id", 404, session_id=sid)
    errors = []
    for obj_name in ("context", "browser"):
        obj = sess.get(obj_name)
        if obj is not None:
            try:
                obj.close()
            except BRIDGE_FAILURES as exc:
                errors.append(f"{obj_name}: {exc}")
    return _ok(session_id=sid, close_errors=errors)


@app.post("/pages/list")
def pages_list() -> ResponseReturnValue:
    try:
        sess = _session(str(_json().get("session_id", "")))
        return _ok(
            page_index=sess.get("page_index", 0),
            pages=[_page_card(p, i) for i, p in enumerate(_pages(sess))],
        )
    except KeyError as exc:
        return _err("NOT_FOUND", "unknown session_id", 404, session_id=str(exc))


@app.post("/pages/select")
def pages_select() -> ResponseReturnValue:
    data = _json()
    try:
        sess = _session(str(data.get("session_id", "")))
        pages = _pages(sess)
        idx = int(data.get("index", 0))
        if idx < 0 or idx >= len(pages):
            return _err("BAD_REQUEST", "page index out of range", index=idx, page_count=len(pages))
        sess["page_index"] = idx
        return _ok(page_index=idx, page=_page_card(pages[idx], idx))
    except KeyError as exc:
        return _err("NOT_FOUND", "unknown session_id", 404, session_id=str(exc))


@app.post("/pages/new")
def pages_new() -> ResponseReturnValue:
    data = _json()
    try:
        sess = _session(str(data.get("session_id", "")))
        context = sess.get("context")
        browser = sess.get("browser")
        if context is None:
            context = browser.contexts[0] if browser and browser.contexts else browser.new_context()
        page = context.new_page()
        if data.get("url"):
            page.goto(str(data["url"]), wait_until="domcontentloaded")
        pages = _pages(sess)
        sess["page_index"] = max(0, len(pages) - 1)
        return _ok(page_index=sess["page_index"], page=_page_card(page, sess["page_index"]))
    except KeyError as exc:
        return _err("NOT_FOUND", "unknown session_id", 404, session_id=str(exc))
    except BRIDGE_FAILURES as exc:
        return _err("PAGE_NEW_FAILED", str(exc), 502)


@app.post("/pages/close")
def pages_close() -> ResponseReturnValue:
    data = _json()
    try:
        sess = _session(str(data.get("session_id", "")))
        pages = _pages(sess)
        idx = int(data.get("index", sess.get("page_index", 0)))
        if idx < 0 or idx >= len(pages):
            return _err("BAD_REQUEST", "page index out of range", index=idx, page_count=len(pages))
        pages[idx].close()
        sess["page_index"] = max(0, min(idx, len(_pages(sess)) - 1))
        return _ok(page_index=sess["page_index"], page_count=len(_pages(sess)))
    except KeyError as exc:
        return _err("NOT_FOUND", "unknown session_id", 404, session_id=str(exc))


@app.post("/navigate")
def navigate() -> ResponseReturnValue:
    data = _json()
    try:
        page = _page(_session(str(data.get("session_id", ""))))
        page.goto(str(data.get("url", "")), wait_until="domcontentloaded")
        return _ok(url=page.url, title=page.title())
    except KeyError as exc:
        return _err("NOT_FOUND", "unknown session_id", 404, session_id=str(exc))
    except BRIDGE_FAILURES as exc:
        return _err("NAVIGATE_FAILED", str(exc), 502)


@app.post("/fill")
def fill() -> ResponseReturnValue:
    data = _json()
    try:
        page = _page(_session(str(data.get("session_id", ""))))
        page.fill(str(data.get("selector", "")), str(data.get("text", "")))
        return _ok()
    except KeyError as exc:
        return _err("NOT_FOUND", "unknown session_id", 404, session_id=str(exc))
    except BRIDGE_FAILURES as exc:
        return _err("FILL_FAILED", str(exc), 502)


@app.post("/click")
def click() -> ResponseReturnValue:
    data = _json()
    try:
        page = _page(_session(str(data.get("session_id", ""))))
        page.click(str(data.get("selector", "")))
        return _ok()
    except KeyError as exc:
        return _err("NOT_FOUND", "unknown session_id", 404, session_id=str(exc))
    except BRIDGE_FAILURES as exc:
        return _err("CLICK_FAILED", str(exc), 502)


@app.post("/press")
def press() -> ResponseReturnValue:
    data = _json()
    try:
        page = _page(_session(str(data.get("session_id", ""))))
        page.press(str(data.get("selector", "body")), str(data.get("key", "Enter")))
        return _ok()
    except KeyError as exc:
        return _err("NOT_FOUND", "unknown session_id", 404, session_id=str(exc))
    except BRIDGE_FAILURES as exc:
        return _err("PRESS_FAILED", str(exc), 502)


@app.post("/content")
def content() -> ResponseReturnValue:
    try:
        page = _page(_session(str(_json().get("session_id", ""))))
        return _ok(html=page.content(), url=page.url, title=page.title())
    except KeyError as exc:
        return _err("NOT_FOUND", "unknown session_id", 404, session_id=str(exc))
    except BRIDGE_FAILURES as exc:
        return _err("CONTENT_FAILED", str(exc), 502)


@app.post("/text")
def text() -> ResponseReturnValue:
    data = _json()
    try:
        page = _page(_session(str(data.get("session_id", ""))))
        selector = data.get("selector")
        value = (
            page.locator(str(selector)).inner_text()
            if selector
            else page.locator("body").inner_text()
        )
        return _ok(text=value, url=page.url, title=page.title())
    except KeyError as exc:
        return _err("NOT_FOUND", "unknown session_id", 404, session_id=str(exc))
    except BRIDGE_FAILURES as exc:
        return _err("TEXT_FAILED", str(exc), 502)


@app.post("/evaluate")
def evaluate() -> ResponseReturnValue:
    data = _json()
    try:
        page = _page(_session(str(data.get("session_id", ""))))
        result = page.evaluate(str(data.get("expression", "() => null")))
        return _ok(result=result)
    except KeyError as exc:
        return _err("NOT_FOUND", "unknown session_id", 404, session_id=str(exc))
    except BRIDGE_FAILURES as exc:
        return _err("EVALUATE_FAILED", str(exc), 502)


@app.post("/screenshot")
def screenshot() -> ResponseReturnValue:
    data = _json()
    try:
        page = _page(_session(str(data.get("session_id", ""))))
        name = str(data.get("name") or f"shot-{uuid.uuid4().hex[:10]}.png")
        safe = (
            "".join(ch for ch in name if ch.isalnum() or ch in ("-", "_", ".")).strip()
            or "screenshot.png"
        )
        if not safe.lower().endswith(".png"):
            safe += ".png"
        path = SCREENSHOT_DIR / safe
        raw = page.screenshot(path=str(path), full_page=True)
        return _ok(path=str(path), bytes=len(raw), base64=base64.b64encode(raw).decode("ascii"))
    except KeyError as exc:
        return _err("NOT_FOUND", "unknown session_id", 404, session_id=str(exc))
    except BRIDGE_FAILURES as exc:
        return _err("SCREENSHOT_FAILED", str(exc), 502)


def main() -> None:
    global PW
    parser = argparse.ArgumentParser()
    parser.add_argument("--host", default=os.environ.get("PCMMAD_BROWSER_BRIDGE_HOST", "127.0.0.1"))
    parser.add_argument(
        "--port", type=int, default=int(os.environ.get("PCMMAD_BROWSER_BRIDGE_PORT", "4471"))
    )
    args = parser.parse_args()
    PW = sync_playwright().start()
    try:
        app.run(host=args.host, port=args.port, debug=False, use_reloader=False, threaded=False)
    finally:
        cleanup_errors = []
        for sid in list(SESSIONS):
            try:
                sess = SESSIONS.pop(sid)
                if sess.get("context") is not None:
                    sess["context"].close()
                if sess.get("browser") is not None:
                    sess["browser"].close()
            except BRIDGE_FAILURES as exc:
                cleanup_errors.append(f"{sid}: {exc}")
        if cleanup_errors:
            app.logger.warning("browser bridge cleanup errors: %s", cleanup_errors)
        PW.stop()


if __name__ == "__main__":
    main()
