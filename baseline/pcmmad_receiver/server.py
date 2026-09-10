"""PCMMAD receiver process entrypoint."""

from __future__ import annotations

if __package__ in (None, ""):
    import sys as _sys
    from pathlib import Path as _BootstrapPath

    _sys.path.insert(0, str(_BootstrapPath(__file__).resolve().parents[1]))
    __package__ = "pcmmad_receiver"


from .app_factory import create_app
from .runtime_config import SERVER_CONFIG
from .operator_plane import ensure_hud_running

app = create_app()


def _serve() -> None:
    try:
        from waitress import create_server
        from .observability import bind_waitress_server
    except ImportError as exc:
        print(
            f"[PCMMAD] Waitress unavailable; falling back to Flask development server: {exc}",
            flush=True,
        )
        app.run(
            host=SERVER_CONFIG.host,
            port=SERVER_CONFIG.port,
            debug=False,
            threaded=True,
            use_reloader=False,
        )
        return

    server = create_server(
        app,
        host=SERVER_CONFIG.host,
        port=SERVER_CONFIG.port,
        threads=SERVER_CONFIG.http_threads,
        channel_timeout=120,
        cleanup_interval=10,
        asyncore_use_poll=True,
    )
    bind_waitress_server(server)
    print(
        f"[PCMMAD] HTTP server waitress threads={SERVER_CONFIG.http_threads} "
        f"bind={SERVER_CONFIG.host}:{SERVER_CONFIG.port}",
        flush=True,
    )
    server.run()


if __name__ == "__main__":
    try:
        hud = ensure_hud_running()
        print(f"[PCMMAD] operator HUD {hud.get('action')} on {hud.get('host')}:{hud.get('port')}", flush=True)
    except Exception as exc:
        print(f"[PCMMAD] operator HUD degraded: {type(exc).__name__}: {exc}", flush=True)
    _serve()
