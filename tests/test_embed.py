"""The hub's guard around embedded tools (core/embed.py): a failing tool is caught, Streamlit's own control flow isn't."""
import itertools
from datetime import datetime, timezone

import pytest

from core import embed

_names = itertools.count()


@pytest.fixture
def make_tool(tmp_path, monkeypatch):
    """Write a throwaway page module and return a hub.yaml-style tool entry pointing at it."""
    monkeypatch.syspath_prepend(str(tmp_path))

    def make(source):
        name = f"fake_tool_page_{next(_names)}"  # a new name each time, so no cached module is reused
        (tmp_path / f"{name}.py").write_text(source, encoding="utf-8")
        return {"id": "fake", "name": "Fake tool", "module": name}
    return make


def errors_seen():
    seen = []
    return seen, lambda tool, error: seen.append((tool["id"], error))


def test_a_working_tool_runs_and_reports_nothing(make_tool):
    tool = make_tool("drawn = []\ndef render():\n    drawn.append(True)\n")
    seen, on_error = errors_seen()
    assert embed.run(tool, on_error) is True
    assert seen == []


def test_the_wrapper_catches_a_tool_that_raises(make_tool, caplog):
    tool = make_tool("def render():\n    raise ValueError('the contract has no pages')\n")
    seen, on_error = errors_seen()
    assert embed.run(tool, on_error) is False
    assert [(tid, type(e), str(e)) for tid, e in seen] == [("fake", ValueError, "the contract has no pages")]
    assert "Tool 'fake'" in caplog.text and "ValueError" in caplog.text  # the traceback goes to the app's logs


def test_the_wrapper_catches_errors_while_importing(make_tool):
    tool = make_tool("import a_package_that_is_not_installed\ndef render():\n    pass\n")
    seen, on_error = errors_seen()
    assert embed.run(tool, on_error) is False
    assert isinstance(seen[0][1], ModuleNotFoundError)


def test_a_missing_module_or_render_is_reported(make_tool):
    seen, on_error = errors_seen()
    assert embed.run({"id": "fake", "name": "Fake", "module": "no_such_tool_module"}, on_error) is False
    assert embed.run(make_tool("x = 1\n"), on_error) is False
    assert isinstance(seen[0][1], ModuleNotFoundError) and isinstance(seen[1][1], embed.ToolLoadError)


def test_streamlit_control_flow_passes_through(make_tool):
    """st.stop, st.rerun and st.switch_page raise BaseException subclasses; the guard must not swallow them."""
    tool = make_tool("class StopLike(BaseException):\n    pass\ndef render():\n    raise StopLike()\n")
    seen, on_error = errors_seen()
    with pytest.raises(BaseException) as info:
        embed.run(tool, on_error)
    assert type(info.value).__name__ == "StopLike" and seen == []


def test_error_summary_is_one_short_line():
    assert embed.error_summary(ValueError("bad\n  input")) == "ValueError: bad input"
    assert embed.error_summary(KeyError()) == "KeyError"
    long = embed.error_summary(RuntimeError("x" * 1000))
    assert len(long) == len("RuntimeError: ") + embed.ERROR_DETAIL_MAX and long.endswith("...")


def test_error_email_says_what_failed_and_when():
    tool = {"id": "bracket", "name": "Bracket Counter & Spell Check"}
    when = datetime(2026, 11, 3, 15, 4, tzinfo=timezone.utc)
    subject, body = embed.error_email(tool, ValueError("no pages"), "analyst@newyorklife.com", when)
    assert subject == "App hub: Bracket Counter & Spell Check isn't working"
    for text in ("Tool: Bracket Counter & Spell Check (bracket)", "When: 2026-11-03 15:04 UTC",
                 "Error: ValueError: no pages", "Signed in as: analyst@newyorklife.com"):
        assert text in body, text
    assert "Signed in as" not in embed.error_email(tool, ValueError("x"), None, when)[1]
