"""The whole hub runs headless with Streamlit's AppTest: every page of its own, a team's empty page, and no tool's code
is imported until its page is opened."""
import sys
from pathlib import Path

import pytest

pytest.importorskip("streamlit")
from streamlit.testing.v1 import AppTest  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
TIMEOUT = 60  # the first run imports pandas and Altair


def tool_modules():
    """Modules of individual tools (tools.<team>.<tool>...), as opposed to the empty tools and team packages."""
    return sorted(m for m in sys.modules if m.startswith("tools.") and m.count(".") >= 2)


def hub_pages():
    from views import ui

    return list(ui.PAGES.values())


def test_home_runs_without_importing_any_tool():
    for m in tool_modules():
        del sys.modules[m]
    at = AppTest.from_file(str(ROOT / "app.py"), default_timeout=TIMEOUT).run()
    assert not at.exception, [e.value for e in at.exception]
    assert not at.error, [e.value for e in at.error]
    assert tool_modules() == [], "building the navigation imported a tool"


@pytest.mark.parametrize("page", hub_pages())
def test_every_hub_page_runs(page):
    at = AppTest.from_file(str(ROOT / "app.py"), default_timeout=TIMEOUT).run()
    at.switch_page(page).run()
    assert not at.exception, [e.value for e in at.exception]
    assert not at.error, [e.value for e in at.error]


def _team_page(team_id, without_links=False):
    import copy

    from views import team, ui

    cfg = copy.deepcopy(ui.cfg())
    if without_links:  # as if the team's tools had no link yet
        for t in cfg["tools"]:
            t["url"] = ""
    team.render(cfg, next(t for t in cfg["teams"] if t["id"] == team_id))


def test_a_team_with_no_tools_gets_a_request_button():
    at = AppTest.from_function(_team_page, args=("par",), default_timeout=TIMEOUT).run()
    assert not at.exception, [e.value for e in at.exception]
    assert at.button(key="team-request-par").label == "Request a tool"
    assert "team-tools-par" not in [b.key for b in at.button]  # nothing to point to on Our tools


def test_a_team_with_tools_not_yet_open_points_to_our_tools():
    at = AppTest.from_function(_team_page, args=("underwriting", True), default_timeout=TIMEOUT).run()
    assert not at.exception, [e.value for e in at.exception]
    assert at.button(key="team-tools-underwriting").label == "See them on Our tools"
