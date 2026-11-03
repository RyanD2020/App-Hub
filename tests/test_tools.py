"""The tools/ folder matches config/hub.yaml, and every embedded tool follows the rules in docs/ADDING_A_TOOL.md.

Layout: tools/<team id>/<tool folder>/ with __init__.py and page.py, and page.py defines render().
"""
import ast
import importlib
import importlib.util
from pathlib import Path

import pytest

from core import config

ROOT = Path(__file__).resolve().parent.parent
TOOLS = ROOT / "tools"


@pytest.fixture(scope="module")
def cfg():
    return config.load()


def team_folders():
    return sorted(p for p in TOOLS.iterdir() if p.is_dir() and p.name != "__pycache__")


def tool_folders():
    return sorted(p for team in team_folders() for p in team.iterdir() if p.is_dir() and p.name != "__pycache__")


def embedded(cfg):
    return [t for t in cfg["tools"] if config.is_embedded(t)]


def test_every_team_folder_is_in_the_teams_list(cfg):
    ids = {t["id"] for t in cfg["teams"]}
    unknown = [p.name for p in team_folders() if p.name not in ids]
    assert not unknown, f"Folders under tools/ that aren't a team id in hub.yaml: {unknown}"


def test_tools_and_team_folders_are_packages():
    assert (TOOLS / "__init__.py").is_file()
    for p in team_folders() + tool_folders():
        assert (p / "__init__.py").is_file(), f"{p.relative_to(ROOT)} needs an __init__.py"


def test_every_tool_folder_has_a_page_with_render():
    for p in tool_folders():
        page = p / "page.py"
        assert page.is_file(), f"{p.relative_to(ROOT)} needs a page.py"
        tree = ast.parse(page.read_text(encoding="utf-8"))
        assert any(isinstance(n, ast.FunctionDef) and n.name == "render" for n in tree.body), \
            f"{page.relative_to(ROOT)} needs a top-level render() function"


def test_every_tool_folder_is_an_embedded_tool_in_hub_yaml(cfg):
    used = {t["module"].rsplit(".", 1)[0] for t in embedded(cfg)}
    for p in tool_folders():
        module = ".".join(p.relative_to(ROOT).parts)
        assert module in used, f"{module} isn't the module of any embedded tool in hub.yaml"


def test_every_embedded_tools_module_exists_and_has_render(cfg):
    for t in embedded(cfg):
        assert importlib.util.find_spec(t["module"]) is not None, f"{t['id']}: {t['module']} not found"
    pytest.importorskip("streamlit")  # importing a tool imports Streamlit
    from core import embed

    for t in embedded(cfg):
        assert callable(embed.load_render(t["module"])), t["id"]


def test_team_packages_import_nothing():
    """Importing tools or a team package must not pull in any tool (tools load only when their page runs)."""
    for p in [TOOLS] + team_folders():
        tree = ast.parse((p / "__init__.py").read_text(encoding="utf-8"))
        assert not any(isinstance(n, (ast.Import, ast.ImportFrom)) for n in ast.walk(tree)), p.relative_to(ROOT)


def test_load_render_reports_a_module_without_render(tmp_path, monkeypatch):
    from core import embed

    (tmp_path / "no_render_here.py").write_text("x = 1\n", encoding="utf-8")
    monkeypatch.syspath_prepend(str(tmp_path))
    importlib.invalidate_caches()
    with pytest.raises(embed.ToolLoadError):
        embed.load_render("no_render_here")
