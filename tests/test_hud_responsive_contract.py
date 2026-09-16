from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def test_hud_responsive_contract():
    css=(ROOT/"operator_hud/static/style.css").read_text(encoding="utf-8")
    js=(ROOT/"operator_hud/static/app.js").read_text(encoding="utf-8")
    html=(ROOT/"operator_hud/static/index.html").read_text(encoding="utf-8")
    assert "--topbar-h:" in css
    assert "top: var(--topbar-h)" in css
    assert "@container right-wing" in css
    assert "@container center-wing" in css
    assert "syncStickyOffsets" in js
    assert "ops-hud-20260916-responsive-v3" in html
