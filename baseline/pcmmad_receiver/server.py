"""PCMMAD receiver process entrypoint."""

from __future__ import annotations

from app_factory import create_app
from runtime_config import SERVER_CONFIG
from operator_plane import ensure_hud_running

app = create_app()


if __name__ == "__main__":
    try:
        hud = ensure_hud_running()
        print(f"[PCMMAD] operator HUD {hud.get('action')} on {hud.get('host')}:{hud.get('port')}", flush=True)
    except Exception as exc:
        print(f"[PCMMAD] operator HUD degraded: {type(exc).__name__}: {exc}", flush=True)
    app.run(
        host=SERVER_CONFIG.host,
        port=SERVER_CONFIG.port,
        debug=False,
        threaded=True,
        use_reloader=False,
    )
