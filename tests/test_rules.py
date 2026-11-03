"""House rules checked across every file: who may be named, and the design rules that can be checked in code."""
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
# The approved prototype is a design reference, not part of the app; it keeps its own example address.
SKIP = {ROOT / "docs" / "App_Hub_Prototype.html"}
TEXT = {".py", ".yaml", ".yml", ".toml", ".css", ".js", ".md", ".sql", ".txt", ".json", ".html"}

ALLOWED_EMAILS = {
    "muhammad_adil@nylim.com", "madil@newyorklife.com",
    "ryan_e_doswell@newyorklife.com", "rdoswell@newyorklife.com",
    "analyst@newyorklife.com", "reviewer@newyorklife.com",  # example requesters
}
EMAIL = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9-]+(?:\.[A-Za-z0-9-]+)+")
FORBIDDEN_UI = ("·", "→", "←", "➔", "➤", "&rarr;", "&middot;")  # middle dot, arrows


def files():
    for p in ROOT.rglob("*"):
        if p.is_file() and p.suffix in TEXT and p not in SKIP and not {".git", "__pycache__"} & set(p.parts):
            yield p


def test_only_the_two_admins_and_example_requesters_are_named():
    found = {}
    for p in files():
        for m in EMAIL.findall(p.read_text(encoding="utf-8", errors="ignore")):
            if m.lower() not in ALLOWED_EMAILS:
                found.setdefault(str(p.relative_to(ROOT)), set()).add(m)
    assert not found, f"Addresses that aren't the admins or the example requesters: {found}"


def test_no_gradients_shadows_or_rounded_controls_in_the_design():
    css = (ROOT / "design" / "hub.css").read_text(encoding="utf-8")
    assert "gradient" not in css
    assert not re.search(r"box-shadow:(?!\s*none\b)", css), "shadows are off"
    for m in re.finditer(r"border-radius:\s*([^;]+);", css):
        assert m.group(1).strip() in {"0", "2px", "50%"}, m.group(0)  # 2px chips; 50% only for the live dot
    assert "uppercase" not in css


def test_no_middle_dots_or_arrows_in_ui_text():
    for p in list((ROOT / "views").glob("*.py")) + [ROOT / "app.py", ROOT / "config" / "hub.yaml"]:
        text = p.read_text(encoding="utf-8")
        for bad in FORBIDDEN_UI:
            assert bad not in text, f"{p.name} contains {bad!r}"


def test_hub_css_keeps_its_token_markers():
    css = (ROOT / "design" / "hub.css").read_text(encoding="utf-8")
    for marker in ("/* BEGIN light tokens */", "/* END light tokens */", "/* BEGIN dark tokens */",
                   "/* END dark tokens */"):
        assert css.count(marker) == 1, marker


def test_logo_is_the_supplied_png():
    data = (ROOT / "assets" / "nyl_logo.png").read_bytes()
    assert data[:8] == b"\x89PNG\r\n\x1a\n" and len(data) == 6518
