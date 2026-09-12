"""Operational git/verification/web lab-tool registration surface."""

from __future__ import annotations

import ipaddress
import socket
import time
import urllib.error
import urllib.parse
import urllib.request
from collections.abc import Callable, MutableMapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .server_hardening import run_subprocess_envelope

JsonObject = MutableMapping[str, Any]
OpsRegistrar = Callable[..., Any]


@dataclass(frozen=True)
class OpsToolDeps:
    error_cls: type[Exception]
    get_project_root: Callable[[str], Path]
    resolve_cwd: Callable[[str, object], Path]
    exec_env: Callable[[JsonObject], dict[str, str]]
    append_reflexion: Callable[[str, JsonObject], object]
    beautiful_soup: Any


VERIFY_MAX_GATES = 32
VERIFY_TIMEOUT_EACH_MAX_SECONDS = 600
VERIFY_OUTPUT_MAX_BYTES = 50000


def _ops_deps(deps: JsonObject) -> OpsToolDeps:
    return OpsToolDeps(
        error_cls=deps["error_cls"],
        get_project_root=deps["get_project_root"],
        resolve_cwd=deps["resolve_cwd"],
        exec_env=deps["exec_env"],
        append_reflexion=deps["append_reflexion"],
        beautiful_soup=deps.get("beautiful_soup"),
    )


def _project_id(payload: JsonObject) -> str:
    return str(payload.get("project_id", "")).strip()


def _repo_path(payload: JsonObject) -> str:
    return str(payload.get("repo_path") or ".").strip() or "."


def _git_envelope(
    root: Path, args: list[str], timeout_seconds: int = 30, stdout_max_bytes: int = 65536
) -> JsonObject:
    return run_subprocess_envelope(
        args,
        cwd=root,
        timeout_seconds=timeout_seconds,
        stdout_max_bytes=stdout_max_bytes,
        stderr_max_bytes=65536,
    )


def _git_stdout(root: Path, args: list[str], dep: OpsToolDeps, *, timeout_seconds: int = 30) -> str:
    result = _git_envelope(root, args, timeout_seconds=timeout_seconds, stdout_max_bytes=65536)
    if not result.get("ok"):
        raise dep.error_cls(
            "GIT_PROBE_FAILED",
            str(result.get("stderr") or result.get("stdout") or "git probe failed"),
            409,
            command=args,
            result=result,
        )
    return str(result.get("stdout") or "").strip()


def _git_repo_probe(
    project_id: str, dep: OpsToolDeps, repo_path: str = "."
) -> tuple[Path, JsonObject | None, JsonObject | None]:
    if not project_id:
        raise dep.error_cls("BAD_REQUEST", "project_id is required", 400)
    project_root = dep.get_project_root(project_id).resolve()
    root = dep.resolve_cwd(project_id, repo_path or ".").resolve()
    if not root.exists() or not root.is_dir():
        return root, None, {
            "ok": False,
            "status": "FAILED",
            "return_code": None,
            "project_id": project_id,
            "project_root": str(project_root),
            "requested_repo_path": repo_path or ".",
            "requested_repo_root": str(root),
            "repo_grounded": False,
            "error_code": "GIT_REPO_INVALID",
            "error": "requested repository path does not exist or is not a directory",
            "stderr": "",
            "stderr_truncated": False,
            "stdout": "",
            "stdout_truncated": False,
        }
    top_probe = _git_envelope(root, ["git", "rev-parse", "--show-toplevel"])
    if not top_probe.get("ok"):
        failure = dict(top_probe)
        failure.update(
            {
                "ok": False,
                "status": "FAILED",
                "project_id": project_id,
                "project_root": str(project_root),
                "requested_repo_path": repo_path or ".",
                "repo_grounded": False,
                "error_code": "GIT_REPO_INVALID",
                "error": str(
                    top_probe.get("stderr")
                    or top_probe.get("stdout")
                    or "not a Git repository"
                ),
                "probe": top_probe,
            }
        )
        return root, None, failure
    try:
        top = Path(str(top_probe.get("stdout") or "").strip()).resolve()
    except OSError as exc:
        return root, None, {
            "ok": False,
            "project_id": project_id,
            "project_root": str(project_root),
            "requested_repo_path": repo_path or ".",
            "repo_grounded": False,
            "error_code": "GIT_REPO_INVALID",
            "error": str(exc),
            "probe": top_probe,
        }
    if top != root:
        return root, None, {
            "ok": False,
            "status": "FAILED",
            "return_code": None,
            "project_id": project_id,
            "repo_grounded": False,
            "error_code": "GIT_REPO_SCOPE_MISMATCH",
            "error": "project root is not the exact Git repository root",
            "project_root": str(project_root),
            "requested_repo_path": repo_path or ".",
            "requested_repo_root": str(root),
            "git_toplevel": str(top),
        }
    head_probe = _git_envelope(root, ["git", "rev-parse", "--verify", "HEAD"])
    head = str(head_probe.get("stdout") or "").strip() if head_probe.get("ok") else None
    branch_probe = _git_envelope(root, ["git", "symbolic-ref", "--quiet", "--short", "HEAD"])
    branch = str(branch_probe.get("stdout") or "").strip() if branch_probe.get("ok") else None
    identity = {
        "project_id": project_id,
        "project_root": str(project_root),
        "repo_path": repo_path or ".",
        "repo_root": str(root),
        "head": head,
        "branch": branch,
        "unborn": head is None,
        "repo_grounded": True,
    }
    return root, identity, None


def _git_repo_identity(
    project_id: str, dep: OpsToolDeps, repo_path: str = "."
) -> tuple[Path, JsonObject]:
    root, identity, error = _git_repo_probe(project_id, dep, repo_path)
    if identity is not None:
        return root, identity
    assert error is not None
    raise dep.error_cls(
        str(error.get("error_code") or "GIT_REPO_INVALID"),
        str(error.get("error") or "Git repository grounding failed"),
        409,
        **{
            k: v
            for k, v in error.items()
            if k not in {"ok", "status", "error_code", "error"}
        },
    )


def _git_status_snapshot(root: Path) -> JsonObject:
    result = _git_envelope(root, ["git", "status", "--porcelain=v1", "--branch"])
    text = str(result.get("stdout") or "")
    lines = text.splitlines()
    return {
        "ok": bool(result.get("ok")),
        "dirty": any(line and not line.startswith("##") for line in lines),
        "porcelain": text,
        "stdout_truncated": bool(result.get("stdout_truncated")),
    }


GIT_READ_SCHEMA={"type":"object","additionalProperties":False,"required":["project_id"],"properties":{"project_id":{"type":"string","minLength":1},"repo_path":{"type":"string"}}}
GIT_DIFF_SCHEMA={"type":"object","additionalProperties":False,"required":["project_id"],"properties":{"project_id":{"type":"string","minLength":1},"repo_path":{"type":"string"},"cached":{"type":"boolean"}}}
GIT_COMMIT_SCHEMA={"type":"object","additionalProperties":False,"required":["project_id","message"],"properties":{"project_id":{"type":"string","minLength":1},"repo_path":{"type":"string"},"message":{"type":"string","minLength":1}}}
GIT_RESET_SCHEMA={"type":"object","additionalProperties":False,"required":["project_id"],"properties":{"project_id":{"type":"string","minLength":1},"repo_path":{"type":"string"},"target":{"type":"string"}}}
GIT_CLEAN_SCHEMA={"type":"object","additionalProperties":False,"required":["project_id"],"properties":{"project_id":{"type":"string","minLength":1},"repo_path":{"type":"string"},"x":{"type":"boolean"}}}

def _register_git_read_tools(register_tool: OpsRegistrar, dep: OpsToolDeps) -> None:
    @register_tool(
        "git.status",
        "Read git status, branch, and dirty state for a project repo.",
        "medium",
        category="git",
        side_effect_class="read",
        effect_traits=["reads_repo_state", "requires_exact_repo_identity"],
        input_schema=GIT_READ_SCHEMA,
    )
    def tool_git_status(payload: JsonObject) -> JsonObject:
        project_id = _project_id(payload)
        root, identity, error = _git_repo_probe(project_id, dep, _repo_path(payload))
        if error is not None:
            return error
        result = _git_envelope(root, ["git", "status", "--short", "--branch"])
        result["project_id"] = project_id
        result["repo_identity"] = identity
        result["repo_grounded"] = True
        return result

    @register_tool("git.diff", "Read a git diff for a project repo.", "medium", category="git", side_effect_class="read", effect_traits=["reads_repo_state", "requires_exact_repo_identity", "bounded_output"], input_schema=GIT_DIFF_SCHEMA)
    def tool_git_diff(payload: JsonObject) -> JsonObject:
        project_id = _project_id(payload)
        root, identity, error = _git_repo_probe(project_id, dep, _repo_path(payload))
        if error is not None:
            return error
        args = ["git", "diff"]
        if payload.get("cached"):
            args.append("--cached")
        result = _git_envelope(root, args, stdout_max_bytes=262144)
        result["project_id"] = project_id
        result["repo_identity"] = identity
        result["repo_grounded"] = True
        return result


def _git_commit_payload(payload: JsonObject, dep: OpsToolDeps) -> JsonObject:
    project_id = _project_id(payload)
    message = str(payload.get("message", "")).strip()
    if not message:
        raise dep.error_cls("BAD_REQUEST", "message is required", 400)
    repo_path = _repo_path(payload)
    root, before = _git_repo_identity(project_id, dep, repo_path)
    status_before = _git_status_snapshot(root)
    add_result = _git_envelope(root, ["git", "add", "."])
    if not add_result.get("ok"):
        raise dep.error_cls(
            "GIT_STAGE_FAILED",
            str(add_result.get("stderr") or add_result.get("stdout") or "git add failed"),
            409,
            project_id=project_id,
            repo_identity=before,
            stage=add_result,
        )
    staged_probe = _git_envelope(root, ["git", "diff", "--cached", "--quiet", "--exit-code"])
    staged_rc = staged_probe.get("return_code")
    if staged_rc == 0:
        raise dep.error_cls(
            "GIT_NOTHING_TO_COMMIT",
            "no staged changes remain after git add",
            409,
            project_id=project_id,
            repo_identity=before,
        )
    if staged_rc not in {1}:
        raise dep.error_cls(
            "GIT_STAGE_VERIFY_FAILED",
            str(staged_probe.get("stderr") or "unable to verify staged changes"),
            409,
            result=staged_probe,
        )
    commit_cmd = ["git", "commit", "-m", message]
    if payload.get("sign"):
        commit_cmd.insert(2, "-S")
    commit_result = _git_envelope(root, commit_cmd, timeout_seconds=60)
    if not commit_result.get("ok"):
        raise dep.error_cls(
            "GIT_COMMIT_FAILED",
            str(commit_result.get("stderr") or commit_result.get("stdout") or "git commit failed"),
            409,
            project_id=project_id,
            repo_identity=before,
            commit=commit_result,
        )
    _, after = _git_repo_identity(project_id, dep, repo_path)
    status_after = _git_status_snapshot(root)
    if str(after.get("head") or "") == str(before.get("head") or ""):
        raise dep.error_cls(
            "GIT_POSTCONDITION_FAILED",
            "git commit returned success but HEAD did not advance",
            500,
            before=before,
            after=after,
        )
    return {
        "ok": True,
        "project_id": project_id,
        "before": before,
        "after": after,
        "status_before": status_before,
        "status_after": status_after,
        "add": add_result,
        "commit": commit_result,
        "verified": True,
    }


def _resolve_commit_target(root: Path, target: str, dep: OpsToolDeps) -> str:
    value = str(target or "HEAD").strip() or "HEAD"
    # --end-of-options prevents a ref-shaped user value from becoming a Git option.
    resolved = _git_stdout(
        root,
        ["git", "rev-parse", "--verify", "--end-of-options", f"{value}^{{commit}}"],
        dep,
    )
    first = resolved.splitlines()[0].strip() if resolved else ""
    if len(first) < 40:
        raise dep.error_cls("GIT_TARGET_INVALID", "target did not resolve to a commit", 409, target=value)
    return first


def _git_reset_payload(payload: JsonObject, dep: OpsToolDeps) -> JsonObject:
    project_id = _project_id(payload)
    target = str(payload.get("target", "HEAD")).strip() or "HEAD"
    repo_path = _repo_path(payload)
    root, before = _git_repo_identity(project_id, dep, repo_path)
    resolved_target = _resolve_commit_target(root, target, dep)
    result = _git_envelope(root, ["git", "reset", "--hard", resolved_target], timeout_seconds=60)
    if not result.get("ok"):
        raise dep.error_cls(
            "GIT_RESET_FAILED",
            str(result.get("stderr") or result.get("stdout") or "git reset --hard failed"),
            409,
            target=target,
            resolved_target=resolved_target,
            result=result,
        )
    _, after = _git_repo_identity(project_id, dep, repo_path)
    tracked_status = _git_envelope(root, ["git", "status", "--porcelain=v1", "--untracked-files=no"])
    verified = (
        bool(tracked_status.get("ok"))
        and str(after.get("head") or "") == resolved_target
        and not str(tracked_status.get("stdout") or "").strip()
    )
    if not verified:
        raise dep.error_cls(
            "GIT_POSTCONDITION_FAILED",
            "reset completed but HEAD/tracked worktree did not converge to requested commit",
            500,
            target=target,
            resolved_target=resolved_target,
            before=before,
            after=after,
            tracked_status=tracked_status,
        )
    return {
        "ok": True,
        "project_id": project_id,
        "target": target,
        "resolved_target": resolved_target,
        "before": before,
        "after": after,
        "reset": result,
        "tracked_status": tracked_status,
        "verified": True,
    }


def _git_clean_payload(payload: JsonObject, dep: OpsToolDeps) -> JsonObject:
    project_id = _project_id(payload)
    repo_path = _repo_path(payload)
    root, identity = _git_repo_identity(project_id, dep, repo_path)
    preview_args = ["git", "clean", "-nd"]
    clean_args = ["git", "clean", "-fd"]
    if payload.get("x"):
        preview_args.append("-x")
        clean_args.append("-x")
    preview_before = _git_envelope(root, preview_args, timeout_seconds=60)
    if not preview_before.get("ok"):
        raise dep.error_cls(
            "GIT_CLEAN_PREVIEW_FAILED",
            str(preview_before.get("stderr") or preview_before.get("stdout") or "git clean preview failed"),
            409,
            repo_identity=identity,
            preview=preview_before,
        )
    result = _git_envelope(root, clean_args, timeout_seconds=60)
    if not result.get("ok"):
        raise dep.error_cls(
            "GIT_CLEAN_FAILED",
            str(result.get("stderr") or result.get("stdout") or "git clean failed"),
            409,
            repo_identity=identity,
            preview=preview_before,
            result=result,
        )
    preview_after = _git_envelope(root, preview_args, timeout_seconds=60)
    verified = bool(preview_after.get("ok")) and not str(preview_after.get("stdout") or "").strip()
    if not verified:
        raise dep.error_cls(
            "GIT_POSTCONDITION_FAILED",
            "git clean returned success but deletable candidates remain",
            500,
            repo_identity=identity,
            preview_before=preview_before,
            preview_after=preview_after,
        )
    return {
        "ok": True,
        "project_id": project_id,
        "repo_identity": identity,
        "include_ignored": bool(payload.get("x")),
        "preview_before": preview_before,
        "clean": result,
        "preview_after": preview_after,
        "verified": True,
    }


def _register_git_commit_tool(register_tool: OpsRegistrar, dep: OpsToolDeps) -> None:
    @register_tool(
        "git.commit",
        "Commit current repo changes with an explicit message.",
        "critical",
        category="git",
        approval_required=True,
        mutating=True,
        side_effect_class="mutation",
        effect_traits=["durable_mutation", "mutates_repo", "creates_commit", "requires_exact_repo_identity", "postcondition_verified", "project_mutation_fenced"],
        input_schema=GIT_COMMIT_SCHEMA,
    )
    def tool_git_commit(payload: JsonObject) -> JsonObject:
        return _git_commit_payload(payload, dep)


def _register_git_reset_tool(register_tool: OpsRegistrar, dep: OpsToolDeps) -> None:
    @register_tool(
        "git.reset_hard",
        "Hard reset repo to a target ref.",
        "critical",
        category="git",
        approval_required=True,
        mutating=True,
        side_effect_class="mutation",
        effect_traits=["durable_mutation", "destructive", "mutates_repo", "requires_exact_repo_identity", "postcondition_verified", "project_mutation_fenced"],
        input_schema=GIT_RESET_SCHEMA,
    )
    def tool_git_reset_hard(payload: JsonObject) -> JsonObject:
        return _git_reset_payload(payload, dep)


def _register_git_clean_tool(register_tool: OpsRegistrar, dep: OpsToolDeps) -> None:
    @register_tool(
        "git.clean",
        "Remove untracked files and directories.",
        "critical",
        category="git",
        approval_required=True,
        mutating=True,
        side_effect_class="mutation",
        effect_traits=["durable_mutation", "destructive", "deletes_files", "requires_exact_repo_identity", "dry_run_preview", "postcondition_verified", "project_mutation_fenced"],
        input_schema=GIT_CLEAN_SCHEMA,
    )
    def tool_git_clean(payload: JsonObject) -> JsonObject:
        return _git_clean_payload(payload, dep)


def _register_git_mutation_tools(register_tool: OpsRegistrar, dep: OpsToolDeps) -> None:
    _register_git_commit_tool(register_tool, dep)
    _register_git_reset_tool(register_tool, dep)
    _register_git_clean_tool(register_tool, dep)


def _gate_command(dep: OpsToolDeps, gate: object) -> tuple[str, list[str]]:
    if not isinstance(gate, dict):
        raise dep.error_cls("BAD_REQUEST", "each gate must be an object", 400)
    name = str(gate.get("name", "gate"))
    command = gate.get("command")
    if (
        not isinstance(command, list)
        or not command
        or not all(isinstance(x, str) and x for x in command)
    ):
        raise dep.error_cls("BAD_REQUEST", f"gate {name} has invalid command", 400)
    return name, command


def _record_gate_failure(
    dep: OpsToolDeps, project_id: str, name: str, envelope: JsonObject
) -> None:
    dep.append_reflexion(
        project_id,
        {
            "title": f"gate_failed:{name}",
            "content": str(
                envelope.get("stderr") or envelope.get("stdout") or envelope.get("error")
            )[-4000:],
            "tags": ["verify", "gate_failure", name],
        },
    )


def _verify_gate_row(command: list[str], cwd: Path, timeout_each: int, name: str) -> JsonObject:
    envelope = run_subprocess_envelope(
        command,
        cwd=cwd,
        timeout_seconds=timeout_each,
        stdout_max_bytes=VERIFY_OUTPUT_MAX_BYTES,
        stderr_max_bytes=VERIFY_OUTPUT_MAX_BYTES,
    )
    return {
        "name": name,
        "command": command,
        "passed": bool(envelope.get("ok")),
        "evidence_scope": "declared_gate_command_exit",
        **envelope,
    }


def _verify_gate_payload(payload: JsonObject, dep: OpsToolDeps) -> JsonObject:
    project_id = _project_id(payload)
    if not project_id:
        raise dep.error_cls("BAD_REQUEST", "project_id is required", 400)
    cwd = dep.resolve_cwd(project_id, payload.get("cwd"))
    gates = payload.get("gates") or []
    if not isinstance(gates, list) or not gates:
        raise dep.error_cls("BAD_REQUEST", "gates must be a non-empty array", 400)
    if len(gates) > VERIFY_MAX_GATES:
        raise dep.error_cls(
            "VERIFY_GATE_LIMIT_EXCEEDED",
            f"gates exceeds maximum of {VERIFY_MAX_GATES}",
            400,
            requested=len(gates),
            maximum=VERIFY_MAX_GATES,
        )
    stop_on_fail = bool(payload.get("stop_on_fail", True))
    timeout_each = max(
        1,
        min(
            int(payload.get("timeout_each", 120)),
            VERIFY_TIMEOUT_EACH_MAX_SECONDS,
        ),
    )
    results: list[JsonObject] = []
    overall = "passed"
    started = time.time()
    for gate in gates:
        name, command = _gate_command(dep, gate)
        row = _verify_gate_row(command, cwd, timeout_each, name)
        results.append(row)
        if not row["passed"]:
            overall = "failed"
            _record_gate_failure(dep, project_id, name, row)
            if stop_on_fail:
                break
    return {
        "project_id": project_id,
        "cwd": str(cwd),
        "overall": overall,
        "evidence_scope": "declared_gate_command_exit_only",
        "semantic_claim_verified": False,
        "requested_gates": len(gates),
        "attempted_gates": len(results),
        "stopped_early": len(results) < len(gates),
        "timeout_each_seconds": timeout_each,
        "duration_ms": int((time.time() - started) * 1000),
        "results": results,
    }


def _register_verify_tools(register_tool: OpsRegistrar, dep: OpsToolDeps) -> None:
    @register_tool(
        "verify.gates",
        "Run ordered verification gates like lint, test, and custom commands.",
        "high",
        category="verify",
        approval_required=True,
        mutating=True,
        side_effect_class="execution",
        effect_traits=["project_mutation_fenced",
            "executes_code",
            "spawns_process",
            "arbitrary_process_side_effects",
            "may_write_project_state",
            "records_failure_reflexion",
            "project_scope_enforced",
            "bounded_output",
            "bounded_gate_count",
            "command_exit_evidence_only",
        ],
        input_schema={
            "type": "object",
            "properties": {
                "project_id": {"type": "string", "minLength": 1},
                "cwd": {"type": "string"},
                "gates": {
                    "type": "array",
                    "minItems": 1,
                    "maxItems": VERIFY_MAX_GATES,
                    "items": {
                        "type": "object",
                        "properties": {
                            "name": {"type": "string"},
                            "command": {
                                "type": "array",
                                "minItems": 1,
                                "items": {"type": "string", "minLength": 1},
                            },
                        },
                        "required": ["command"],
                    },
                },
                "stop_on_fail": {"type": "boolean"},
                "timeout_each": {
                    "type": "integer",
                    "minimum": 1,
                    "maximum": VERIFY_TIMEOUT_EACH_MAX_SECONDS,
                },
            },
            "required": ["project_id", "gates"],
        },
        output_schema={
            "type": "object",
            "properties": {
                "project_id": {"type": "string"},
                "cwd": {"type": "string"},
                "overall": {"type": "string", "enum": ["passed", "failed"]},
                "evidence_scope": {"type": "string"},
                "semantic_claim_verified": {"type": "boolean"},
                "requested_gates": {"type": "integer"},
                "attempted_gates": {"type": "integer"},
                "stopped_early": {"type": "boolean"},
                "timeout_each_seconds": {"type": "integer"},
                "duration_ms": {"type": "integer"},
                "results": {"type": "array"},
            },
            "required": [
                "project_id",
                "cwd",
                "overall",
                "evidence_scope",
                "semantic_claim_verified",
                "results",
            ],
        },
    )
    def tool_verify_gates(payload: JsonObject) -> JsonObject:
        return _verify_gate_payload(payload, dep)


WEB_MAX_URL_CHARS = 8192
WEB_MAX_USER_AGENT_CHARS = 512
WEB_MAX_REDIRECTS = 5
WEB_TIMEOUT_MAX_SECONDS = 60
WEB_BODY_MAX_BYTES = 1_000_000
WEB_TEXT_MAX_CHARS = 200_000


def _contains_control_chars(value: str) -> bool:
    return any(ord(ch) < 32 or ord(ch) == 127 for ch in value)


def _html_to_text(dep: OpsToolDeps, text: str) -> tuple[str, str | None, list[str]]:
    if dep.beautiful_soup is None:
        lower = text.lower()
        t0 = lower.find("<title>")
        t1 = lower.find("</title>")
        title = text[t0 + 7 : t1].strip() if t0 != -1 and t1 != -1 and t1 > t0 else None
        return text, title, []
    soup = dep.beautiful_soup(text, "html.parser")
    for tag in soup(["script", "style", "nav"]):
        tag.decompose()
    title = soup.title.string.strip() if soup.title and soup.title.string else None
    links = [a.get("href") for a in soup.find_all("a", href=True)[:100]]
    body_text = "\n".join(line.strip() for line in soup.get_text("\n").splitlines() if line.strip())
    return body_text, title, links


def _blocked_web_ip(address: str) -> bool:
    try:
        ip = ipaddress.ip_address(address.split("%", 1)[0])
    except ValueError:
        return True
    return not ip.is_global


def _resolve_public_web_target(url: str, dep: OpsToolDeps) -> JsonObject:
    if len(url) > WEB_MAX_URL_CHARS:
        raise dep.error_cls(
            "WEB_URL_TOO_LONG",
            f"url exceeds maximum of {WEB_MAX_URL_CHARS} characters",
            400,
            maximum=WEB_MAX_URL_CHARS,
            requested=len(url),
        )
    if _contains_control_chars(url):
        raise dep.error_cls("WEB_TARGET_INVALID", "url contains control characters", 400)
    parsed = urllib.parse.urlparse(url)
    if parsed.scheme not in {"http", "https"}:
        raise dep.error_cls("BAD_REQUEST", "url must be http or https", 400)
    if not parsed.hostname:
        raise dep.error_cls("WEB_TARGET_INVALID", "url hostname is required", 400)
    if parsed.username is not None or parsed.password is not None:
        raise dep.error_cls(
            "WEB_CREDENTIALS_FORBIDDEN",
            "web.fetch is a public read capability and does not accept URL userinfo/credentials",
            403,
            hostname=parsed.hostname,
        )
    try:
        port = parsed.port or (443 if parsed.scheme == "https" else 80)
    except ValueError as exc:
        raise dep.error_cls("WEB_TARGET_INVALID", f"invalid URL port: {exc}", 400) from exc
    try:
        infos = socket.getaddrinfo(
            parsed.hostname,
            port,
            type=socket.SOCK_STREAM,
        )
    except socket.gaierror as exc:
        raise dep.error_cls(
            "WEB_TARGET_RESOLUTION_FAILED",
            f"unable to resolve web target: {exc}",
            502,
            hostname=parsed.hostname,
        ) from exc
    addresses = sorted({str(info[4][0]) for info in infos if info and info[4]})
    if not addresses:
        raise dep.error_cls(
            "WEB_TARGET_RESOLUTION_FAILED",
            "web target resolved to no usable addresses",
            502,
            hostname=parsed.hostname,
        )
    blocked = [address for address in addresses if _blocked_web_ip(address)]
    if blocked:
        raise dep.error_cls(
            "WEB_TARGET_FORBIDDEN",
            "web.fetch is public-network-only; target resolves to non-public address",
            403,
            hostname=parsed.hostname,
            resolved_addresses=addresses,
            blocked_addresses=blocked,
        )
    return {
        "scheme": parsed.scheme,
        "hostname": parsed.hostname,
        "port": port,
        "resolved_addresses": addresses,
        "scope": "public_network",
        "validated_at_unix_ms": int(time.time() * 1000),
    }


class _PublicOnlyRedirectHandler(urllib.request.HTTPRedirectHandler):
    max_redirections = WEB_MAX_REDIRECTS

    def __init__(self, dep: OpsToolDeps) -> None:
        super().__init__()
        self.dep = dep
        self.redirect_targets: list[JsonObject] = []

    def redirect_request(self, req, fp, code, msg, headers, newurl):
        target = _resolve_public_web_target(str(newurl), self.dep)
        self.redirect_targets.append({"url": str(newurl), **target})
        return super().redirect_request(req, fp, code, msg, headers, newurl)


def _web_request(
    payload: JsonObject, dep: OpsToolDeps
) -> tuple[str, urllib.request.Request, int, int, JsonObject]:
    url = str(payload.get("url", "")).strip()
    if not url:
        raise dep.error_cls("BAD_REQUEST", "url is required", 400)
    target = _resolve_public_web_target(url, dep)
    user_agent = str(payload.get("user_agent", "Mozilla/5.0 PCMMAD-Lab/1.0"))
    if not user_agent or len(user_agent) > WEB_MAX_USER_AGENT_CHARS:
        raise dep.error_cls(
            "WEB_USER_AGENT_INVALID",
            f"user_agent must be 1..{WEB_MAX_USER_AGENT_CHARS} characters",
            400,
        )
    if _contains_control_chars(user_agent):
        raise dep.error_cls(
            "WEB_USER_AGENT_INVALID",
            "user_agent contains control characters",
            400,
        )
    request = urllib.request.Request(url, headers={"User-Agent": user_agent})
    timeout_seconds = max(
        1, min(int(payload.get("timeout_seconds", 30)), WEB_TIMEOUT_MAX_SECONDS)
    )
    max_bytes = max(
        1024, min(int(payload.get("max_bytes", 500000)), WEB_BODY_MAX_BYTES)
    )
    return url, request, timeout_seconds, max_bytes, target


def _web_fetch_payload(payload: JsonObject, dep: OpsToolDeps) -> JsonObject:
    url, request, timeout_seconds, max_bytes, initial_target = _web_request(payload, dep)
    redirect_handler = _PublicOnlyRedirectHandler(dep)
    opener = urllib.request.build_opener(redirect_handler)
    with opener.open(request, timeout=timeout_seconds) as resp:
        final_url = str(resp.geturl() or url)
        final_target = _resolve_public_web_target(final_url, dep)
        raw_probe = resp.read(max_bytes + 1)
        content_type = resp.headers.get("Content-Type", "")
        status_code = getattr(resp, "status", None)
        if status_code is None and hasattr(resp, "getcode"):
            status_code = resp.getcode()
    truncated = len(raw_probe) > max_bytes
    raw = raw_probe[:max_bytes]
    text = raw.decode("utf-8", errors="replace")
    title = None
    links: list[str] = []
    if "html" in content_type.lower():
        text, title, links = _html_to_text(dep, text)
    text_truncated = len(text) > WEB_TEXT_MAX_CHARS
    text = text[:WEB_TEXT_MAX_CHARS]
    return {
        "url": url,
        "final_url": final_url,
        "network_scope": "public_network",
        "initial_target": initial_target,
        "final_target": final_target,
        "redirects": redirect_handler.redirect_targets,
        "http_status": status_code,
        "content_type": content_type,
        "bytes": len(raw),
        "truncated": truncated,
        "max_bytes": max_bytes,
        "text_truncated": text_truncated,
        "text_max_chars": WEB_TEXT_MAX_CHARS,
        "title": title,
        "text": text,
        "links": links[:100],
        "redirect_count": len(redirect_handler.redirect_targets),
        "redirect_limit": WEB_MAX_REDIRECTS,
        "dns_rebinding_residual": (
            "DNS targets are validated before request/redirect and after response; "
            "stdlib urllib still performs its own connection-time resolution."
        ),
    }


def _register_web_tools(register_tool: OpsRegistrar, dep: OpsToolDeps) -> None:
    @register_tool(
        "web.fetch",
        "Fetch a URL and distill rendered text/link metadata.",
        "medium",
        category="web",
        side_effect_class="external_read",
        effect_traits=[
            "network_io",
            "reads_external_state",
            "public_network_only",
            "redirects_revalidated",
            "bounded_output",
            "bounded_redirects",
            "url_credentials_rejected",
            "header_controls_rejected",
            "dns_validation_evidence",
            "dns_rebinding_residual_disclosed",
        ],
        input_schema={
            "type": "object",
            "properties": {
                "url": {"type": "string", "minLength": 1, "maxLength": WEB_MAX_URL_CHARS},
                "user_agent": {"type": "string", "minLength": 1, "maxLength": WEB_MAX_USER_AGENT_CHARS},
                "timeout_seconds": {"type": "integer", "minimum": 1, "maximum": WEB_TIMEOUT_MAX_SECONDS},
                "max_bytes": {"type": "integer", "minimum": 1024, "maximum": WEB_BODY_MAX_BYTES},
            },
            "required": ["url"],
            "additionalProperties": False,
        },
        output_schema={
            "type": "object",
            "properties": {
                "url": {"type": "string"},
                "final_url": {"type": "string"},
                "network_scope": {"type": "string"},
                "initial_target": {"type": "object"},
                "final_target": {"type": "object"},
                "redirects": {"type": "array"},
                "redirect_count": {"type": "integer"},
                "redirect_limit": {"type": "integer"},
                "http_status": {},
                "content_type": {"type": "string"},
                "bytes": {"type": "integer"},
                "truncated": {"type": "boolean"},
                "max_bytes": {"type": "integer"},
                "text_truncated": {"type": "boolean"},
                "text_max_chars": {"type": "integer"},
                "title": {},
                "text": {"type": "string"},
                "links": {"type": "array"},
                "dns_rebinding_residual": {"type": "string"},
            },
            "required": [
                "url", "final_url", "network_scope", "initial_target", "final_target",
                "redirects", "redirect_count", "redirect_limit", "bytes", "truncated",
                "max_bytes", "text_truncated", "text_max_chars", "text", "links",
                "dns_rebinding_residual"
            ],
        },
    )
    def tool_web_fetch(payload: JsonObject) -> JsonObject:
        return _web_fetch_payload(payload, dep)


def register_ops_tools(register_tool: OpsRegistrar, **deps: Any) -> None:
    dep = _ops_deps(deps)
    _register_git_read_tools(register_tool, dep)
    _register_git_mutation_tools(register_tool, dep)
    _register_verify_tools(register_tool, dep)
    _register_web_tools(register_tool, dep)
