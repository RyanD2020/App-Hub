"""The rules every embedded tool follows (docs/ADDING_A_TOOL.md), checked in its code.

Each check is a function over one file's source, run on every .py file of every embedded tool, and also on small
good and bad samples, so a check that stops catching anything fails too.
"""
from __future__ import annotations

import ast
import re
import sys
from pathlib import Path

import pytest

from core import config

ROOT = Path(__file__).resolve().parent.parent
TOOLS = ROOT / "tools"
REQUIREMENTS = ROOT / "requirements.txt"
HUB_PACKAGES = {"tools", "core", "views"}
SESSION_STATE_METHODS = {"get", "setdefault", "pop", "keys", "items", "values", "clear", "update", "to_dict"}
LOCAL_STORES = {"sqlite3", "shelve", "dbm"}  # local databases: lasting data belongs in Delta tables (core/db.py)
CWD_CALLS = {("os", "getcwd"), ("os", "chdir"), ("Path", "cwd"), ("pathlib.Path", "cwd")}
WORKSPACE_VALUES = re.compile(
    r"\.databricksapps\.com|\.cloud\.databricks\.com|/sql/1\.0/warehouses/|\bdbc-[0-9a-f]{8}|\badb-\d{10,}")


# ------------------------------------------------------------------ what to check
def embedded_tools():
    return [t for t in config.load()["tools"] if config.is_embedded(t)]


def tool_folder(tool) -> Path:
    return ROOT.joinpath(*tool["module"].split(".")[:-1])


def tool_files():
    """(tool, file) for every .py file of every embedded tool."""
    return [(t, p) for t in embedded_tools() for p in sorted(tool_folder(t).rglob("*.py"))
            if "__pycache__" not in p.parts]


def hub_code_files():
    """The hub's own code and every tool's: app.py, core/, views/, tools/."""
    files = [ROOT / "app.py"]
    for folder in ("core", "views", "tools"):
        files += [p for p in (ROOT / folder).rglob("*.py") if "__pycache__" not in p.parts]
    return sorted(files)


def name_of(node) -> str:
    """Dotted name of a Name or Attribute chain: st.session_state -> "st.session_state"."""
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        inner = name_of(node.value)
        return f"{inner}.{node.attr}" if inner else ""
    return ""


def is_session_state(node) -> bool:
    return name_of(node).split(".")[-1] == "session_state"


def string_start(node) -> str | None:
    """The fixed start of a string key: "bracket__x" or f"bracket__{n}" -> its text before any {}."""
    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        return node.value
    if isinstance(node, ast.JoinedStr):
        first = node.values[0] if node.values else None
        return first.value if isinstance(first, ast.Constant) else ""
    return None  # a variable: can't be checked here, the doc asks for the prefix anyway


# ------------------------------------------------------------------ the checks (source -> problems)
def page_config_calls(source: str) -> list[int]:
    return sorted(n.lineno for n in ast.walk(ast.parse(source))
                  if isinstance(n, ast.Attribute) and n.attr == "set_page_config")


def unprefixed_keys(source: str, prefix: str) -> list[str]:
    """Widget keys and session_state names that don't start with the tool's prefix ("bracket__"), by line."""
    out: list[tuple[int, str]] = []

    def check(node, text, what):
        if text is not None and not text.startswith(prefix):
            out.append((node.lineno, f"line {node.lineno}: {what} {text!r}"))

    for n in ast.walk(ast.parse(source)):
        if isinstance(n, ast.Call):
            for kw in n.keywords:
                if kw.arg == "key":
                    check(kw.value, string_start(kw.value), "widget key")
            func = n.func
            if (isinstance(func, ast.Attribute) and is_session_state(func.value) and func.attr in {"get", "setdefault", "pop"}
                    and n.args):
                check(n, string_start(n.args[0]), "session_state key")
        elif isinstance(n, ast.Subscript) and is_session_state(n.value):
            check(n, string_start(n.slice), "session_state key")
        elif (isinstance(n, ast.Attribute) and is_session_state(n.value) and n.attr not in SESSION_STATE_METHODS):
            check(n, n.attr, "session_state name")
        elif isinstance(n, ast.Compare) and any(is_session_state(c) for c in n.comparators):
            check(n, string_start(n.left), "session_state key")
    return [text for _, text in sorted(out)]


def bare_sibling_imports(source: str, siblings: set[str]) -> list[str]:
    """import report / from report import x, where report is a file next to this one."""
    out = []
    for n in ast.walk(ast.parse(source)):
        if isinstance(n, ast.Import):
            out += [f"line {n.lineno}: import {a.name}" for a in n.names if a.name.split(".")[0] in siblings]
        elif isinstance(n, ast.ImportFrom) and n.level == 0 and n.module and n.module.split(".")[0] in siblings:
            out.append(f"line {n.lineno}: from {n.module} import ...")
    return out


def working_directory_use(source: str) -> list[str]:
    out: list[tuple[int, str]] = []  # ast.walk is breadth-first, so sort by line at the end
    for n in ast.walk(ast.parse(source)):
        if isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute):
            owner = name_of(n.func.value)
            if (owner, n.func.attr) in CWD_CALLS:
                out.append((n.lineno, f"line {n.lineno}: {owner}.{n.func.attr}()"))
    return [text for _, text in sorted(out)]


def local_store_imports(source: str) -> list[str]:
    out = []
    for n in ast.walk(ast.parse(source)):
        names = [a.name for a in n.names] if isinstance(n, ast.Import) else (
            [n.module] if isinstance(n, ast.ImportFrom) and n.module else [])
        out += [f"line {n.lineno}: {m}" for m in names if m.split(".")[0] in LOCAL_STORES]
    return out


def top_level_imports(source: str) -> set[str]:
    found = set()
    for n in ast.walk(ast.parse(source)):
        if isinstance(n, ast.Import):
            found |= {a.name.split(".")[0] for a in n.names}
        elif isinstance(n, ast.ImportFrom) and n.level == 0 and n.module:
            found.add(n.module.split(".")[0])
    return found


def siblings_of(path: Path) -> set[str]:
    return {p.stem for p in path.parent.glob("*.py") if p.stem != "__init__"} | {
        p.name for p in path.parent.iterdir() if p.is_dir() and (p / "__init__.py").is_file()}


def pinned_requirements() -> dict[str, str]:
    pins = {}
    for line in REQUIREMENTS.read_text(encoding="utf-8").splitlines():
        line = line.split("#", 1)[0].strip()
        if line:
            m = re.fullmatch(r"([A-Za-z0-9._-]+)==([A-Za-z0-9.+!-]+)", line)
            assert m, f"requirements.txt: pin an exact version, like name==1.2.3 (got {line!r})"
            pins[re.sub(r"[-_.]+", "-", m.group(1)).lower()] = m.group(2)
    return pins


# ------------------------------------------------------------------ rules, on the real code
def test_only_app_py_calls_set_page_config():
    found = {str(p.relative_to(ROOT)): lines for p in hub_code_files() if p != ROOT / "app.py"
             if (lines := page_config_calls(p.read_text(encoding="utf-8")))}
    assert not found, f"Only app.py calls st.set_page_config. Remove it from: {found}"


def test_no_set_page_config_anywhere_under_tools():
    found = [str(p.relative_to(ROOT)) for p in TOOLS.rglob("*.py") if "set_page_config" in p.read_text(encoding="utf-8")]
    assert not found, f"st.set_page_config under tools/: {found}"


def test_widget_and_session_state_keys_start_with_the_tool_id():
    found = {f"{p.relative_to(ROOT)}": bad for t, p in tool_files()
             if (bad := unprefixed_keys(p.read_text(encoding="utf-8"), f"{t['id']}__"))}
    assert not found, f"Start every key with the tool id and two underscores: {found}"


def test_tools_use_package_imports():
    found = {f"{p.relative_to(ROOT)}": bad for _, p in tool_files()
             if (bad := bare_sibling_imports(p.read_text(encoding="utf-8"), siblings_of(p)))}
    assert not found, f"Import the tool's own files by package path (from tools.<team>.<tool> import x): {found}"


def test_tools_find_their_files_from_their_own_folder():
    found = {f"{p.relative_to(ROOT)}": bad for _, p in tool_files()
             if (bad := working_directory_use(p.read_text(encoding="utf-8")))}
    assert not found, f"Use Path(__file__).parent, not the working directory: {found}"


def test_tools_keep_no_local_database():
    found = {f"{p.relative_to(ROOT)}": bad for _, p in tool_files()
             if (bad := local_store_imports(p.read_text(encoding="utf-8")))}
    assert not found, f"The app's disk can be wiped on any restart; keep lasting data in Delta tables: {found}"


def test_no_workspace_values_in_code():
    """Warehouse IDs, workspace and app URLs live in app.yaml or config/hub.yaml, so a redeploy can move the hub."""
    found = {str(p.relative_to(ROOT)): m.group(0) for p in hub_code_files()
             if (m := WORKSPACE_VALUES.search(p.read_text(encoding="utf-8")))}
    assert not found, f"Move these to app.yaml or config/hub.yaml: {found}"


def test_requirements_are_pinned_exactly_and_once():
    lines = [ln.split("#", 1)[0].strip() for ln in REQUIREMENTS.read_text(encoding="utf-8").splitlines()]
    names = [re.sub(r"[-_.]+", "-", ln.split("==")[0]).lower() for ln in lines if ln]
    assert len(names) == len(set(names)), "a package is listed twice in requirements.txt"
    assert pinned_requirements()


def test_every_package_a_tool_imports_is_in_requirements():
    """Runs where requirements.txt is installed (tests/run_tests.py): maps each import to its installed package."""
    from importlib.metadata import packages_distributions

    dists = packages_distributions()
    pins = pinned_requirements()
    missing = {}
    for _, p in tool_files():
        for name in top_level_imports(p.read_text(encoding="utf-8")) - HUB_PACKAGES - set(sys.stdlib_module_names):
            if name in siblings_of(p):
                continue
            owners = {re.sub(r"[-_.]+", "-", d).lower() for d in dists.get(name, [])}
            if not owners & set(pins):
                missing.setdefault(str(p.relative_to(ROOT)), set()).add(name)
    assert not missing, f"Add these to requirements.txt with an exact version: {missing}"


# ------------------------------------------------------------------ the checks catch what they should
BAD = '''
import streamlit as st
import report
from bracket_checker import analyze
import sqlite3, os
from pathlib import Path
st.set_page_config(page_title="x")
st.text_input("Label", key="label_a")
st.file_uploader("File", key=f"file_{1}")
st.session_state["docs"] = None
st.session_state.analyzed = True
if "comparison" in st.session_state:
    st.session_state.get("allow")
words = open(os.path.join(os.getcwd(), "words.txt"))
here = Path.cwd()
'''

GOOD = '''
from pathlib import Path
import streamlit as st
from tools.underwriting.bracket_spell_check import report
st.text_input("Label", key="bracket__label_a")
st.file_uploader("File", key=f"bracket__file_{1}")
st.session_state["bracket__docs"] = None
st.session_state.bracket__analyzed = True
if "bracket__comparison" in st.session_state:
    st.session_state.get("bracket__allow")
words = (Path(__file__).parent / "words.txt").read_text()
'''


def test_the_checks_catch_a_tool_that_breaks_every_rule():
    assert page_config_calls(BAD) == [7]
    assert len(unprefixed_keys(BAD, "bracket__")) == 6
    assert bare_sibling_imports(BAD, {"report", "bracket_checker"}) == ["line 3: import report",
                                                                         "line 4: from bracket_checker import ..."]
    assert working_directory_use(BAD) == ["line 14: os.getcwd()", "line 15: Path.cwd()"]
    assert local_store_imports(BAD) == ["line 5: sqlite3"]
    assert WORKSPACE_VALUES.search('URL = "https://bracket-app-1.aws.databricksapps.com"')
    assert WORKSPACE_VALUES.search('HTTP_PATH = "/sql/1.0/warehouses/abc123"')


def test_the_checks_pass_a_tool_that_follows_them():
    assert page_config_calls(GOOD) == []
    assert unprefixed_keys(GOOD, "bracket__") == []
    assert bare_sibling_imports(GOOD, {"report", "bracket_checker"}) == []
    assert working_directory_use(GOOD) == []
    assert local_store_imports(GOOD) == []
    assert not WORKSPACE_VALUES.search(GOOD)


@pytest.mark.parametrize("source, start", [('"bracket__x"', "bracket__x"), ('f"bracket__{n}"', "bracket__"),
                                           ('f"{n}_x"', ""), ("name", None)])
def test_string_start(source, start):
    assert string_start(ast.parse(source, mode="eval").body) == start


# ------------------------------------------------------------------ the hub draws the frame; tools style only themselves
FRAME_CALLS = {"st.sidebar", "streamlit.sidebar", "st.logo", "streamlit.logo"}
COLOUR_LITERAL = re.compile(r"#[0-9a-fA-F]{3,8}\b|\b(?:rgba?|hsla?)\(|(?<![\w-])(?:white|black)(?![\w-])", re.I)


def frame_use(source: str) -> list[str]:
    """st.sidebar and st.logo: the hub hides the bar that reopens a sidebar, and it draws the logo itself."""
    out = []
    for n in ast.walk(ast.parse(source)):
        if isinstance(n, ast.Attribute) and name_of(n) in FRAME_CALLS:
            out.append((n.lineno, f"line {n.lineno}: {name_of(n)}"))
        elif isinstance(n, ast.ImportFrom) and n.module == "streamlit":
            out += [(n.lineno, f"line {n.lineno}: from streamlit import {a.name}") for a in n.names
                    if a.name in {"sidebar", "logo"}]
    return [text for _, text in sorted(out)]


def css_rules(css: str) -> list[tuple[str, str]]:
    """(selectors, declarations) of every style rule, including those inside @media and @supports. @keyframes and
    other at-rules are skipped."""
    css = re.sub(r"/\*.*?\*/", "", css, flags=re.S)
    rules: list[tuple[str, str]] = []

    def block_end(s, start):
        depth = 0
        for j in range(start, len(s)):
            depth += {"{": 1, "}": -1}.get(s[j], 0)
            if depth == 0:
                return j
        raise AssertionError("the CSS has an unclosed {")

    def walk(s):
        pos = 0
        while (k := s.find("{", pos)) >= 0:
            prelude = s[pos:k].rsplit(";", 1)[-1].strip()
            end = block_end(s, k)
            if prelude.startswith(("@media", "@supports", "@container")):
                walk(s[k + 1:end])
            elif not prelude.startswith("@"):
                rules.append((prelude, s[k + 1:end]))
            pos = end + 1

    walk(css)
    return rules


def unscoped_selectors(css: str, tool_id: str) -> list[str]:
    scope = re.compile(rf"^(?:div)?\.st-key-sec-tool-{re.escape(tool_id)}(?![\w-])")
    return [sel.strip() for selectors, _ in css_rules(css) for sel in selectors.split(",")
            if not scope.match(sel.strip())]


def colour_literals(css: str) -> list[str]:
    return [m.group(0) for _, body in css_rules(css) for m in COLOUR_LITERAL.finditer(body)]


def design_breaks(css: str) -> list[str]:
    """The hub's design rules (as tests/test_rules.py checks for hub.css): square, flat, no forced capitals."""
    out = []
    for _, body in css_rules(css):
        if "gradient" in body:
            out.append("a gradient")
        if re.search(r"box-shadow:(?!\s*none\b)", body):
            out.append("a shadow")
        out += [f"border-radius: {m.group(1).strip()}" for m in re.finditer(r"border-radius:\s*([^;]+)", body)
                if m.group(1).strip() not in {"0", "2px", "50%"}]
        if re.search(r"text-transform:\s*uppercase", body):
            out.append("text-transform: uppercase")
    return out


def tool_css_files():
    return [(t, p) for t in embedded_tools() for p in sorted(tool_folder(t).rglob("*.css"))]


def test_tools_use_no_sidebar_or_logo():
    found = {f"{p.relative_to(ROOT)}": bad for _, p in tool_files() if (bad := frame_use(p.read_text(encoding="utf-8")))}
    assert not found, f"Put settings on the page (an st.expander), not st.sidebar; the hub draws the logo: {found}"


def test_tools_draw_no_logo_of_their_own():
    found = [str(p.relative_to(ROOT)) for t in embedded_tools() for p in tool_folder(t).rglob("*")
             if p.suffix in {".py", ".css", ".html"} and "<svg" in p.read_text(encoding="utf-8").lower()]
    assert not found, f"The hub's header and footer show the supplied logo; tools draw no SVG logos or banners: {found}"


def test_tool_css_lives_in_css_files():
    found = [f"{p.relative_to(ROOT)}" for _, p in tool_files() if "<style" in p.read_text(encoding="utf-8").lower()]
    assert not found, f"Move the CSS to a .css file in the tool's folder and load it with ui.tool_css(): {found}"


def test_tool_css_is_scoped_to_the_tool():
    found = {f"{p.relative_to(ROOT)}": bad for t, p in tool_css_files()
             if (bad := unscoped_selectors(p.read_text(encoding="utf-8"), t["id"]))}
    assert not found, f"Start every selector with div.st-key-sec-tool-<tool id>: {found}"


def test_tool_css_uses_the_hubs_colour_tokens_and_design():
    found = {f"{p.relative_to(ROOT)}": bad for _, p in tool_css_files()
             if (bad := colour_literals(p.read_text(encoding="utf-8")) + design_breaks(p.read_text(encoding="utf-8")))}
    assert not found, f"Use var(--h-...) colours (they follow light and dark mode) and the hub's design rules: {found}"


def test_tool_css_survives_the_sanitizer():
    from core import design

    for _, p in tool_css_files():
        design.prepare_css(p.read_text(encoding="utf-8"), str(p.relative_to(ROOT)))  # raises with the line to fix


BAD_FRAME = '''
import streamlit as st
from streamlit import sidebar
with st.sidebar:
    st.header("Settings")
st.logo("logo.png")
'''

BAD_CSS = '''
:root { --nyl-dark-blue: #000A62; }
.stApp h1 { color: #000A62; }
.nyl-eyebrow { text-transform: uppercase; color: rgba(0, 0, 0, .5); }
@media (max-width: 640px) { .nyl-metrics { box-shadow: 0 1px 2px black; border-radius: 6px; } }
@keyframes spin { from { opacity: 0; } to { opacity: 1; } }
'''

GOOD_CSS = '''
/* Bracket tool styles: scoped to its page section, hub tokens only. */
div.st-key-sec-tool-bracket { --b-fail-tint: color-mix(in srgb, var(--h-err) 12%, var(--h-surface)); }
div.st-key-sec-tool-bracket .nyl-verdict.fail, .st-key-sec-tool-bracket .nyl-verdict .head {
  background: var(--b-fail-tint); color: var(--h-head); border-radius: 0;
}
@media (max-width: 640px) { div.st-key-sec-tool-bracket .nyl-metrics { grid-template-columns: 1fr; } }
@keyframes bracketFade { from { opacity: 0; } to { opacity: 1; } }
'''


def test_the_frame_and_css_checks_catch_a_tool_that_breaks_them():
    assert frame_use(BAD_FRAME) == ["line 3: from streamlit import sidebar", "line 4: st.sidebar", "line 6: st.logo"]
    assert unscoped_selectors(BAD_CSS, "bracket") == [":root", ".stApp h1", ".nyl-eyebrow", ".nyl-metrics"]
    assert colour_literals(BAD_CSS) == ["#000A62", "#000A62", "rgba(", "black"]
    assert set(design_breaks(BAD_CSS)) == {"text-transform: uppercase", "a shadow", "border-radius: 6px"}
    assert unscoped_selectors(".st-key-sec-tool-bracketx p { color: var(--h-text); }", "bracket")


def test_the_frame_and_css_checks_pass_a_tool_that_follows_them():
    assert frame_use(GOOD) == []
    assert unscoped_selectors(GOOD_CSS, "bracket") == []
    assert colour_literals(GOOD_CSS) == [] and design_breaks(GOOD_CSS) == []
