"""The design files survive st.html's sanitizer (core/design.py).

DOMPurify drops a whole <style> or <script> whose text looks like markup; that once removed all of hub.css silently.
"""
from pathlib import Path

import pytest

from core import design

ROOT = Path(__file__).resolve().parent.parent
CSS = (ROOT / "design" / "hub.css").read_text(encoding="utf-8")
JS = (ROOT / "design" / "motion.js").read_text(encoding="utf-8")


def test_hub_css_as_sent_has_nothing_that_looks_like_markup():
    sent = design.prepare_css(CSS)
    assert not design.MARKUP_PROBE.search(sent)
    assert "/*" not in sent  # comments stay in the file, not in the page
    for selector in (".hub .chip", "div.st-key-hero", "div[class*=\"st-key-tile-\"]", "@keyframes hubFieldIn"):
        assert selector in sent, selector


def test_motion_js_has_nothing_that_looks_like_markup():
    assert design.check(JS, "design/motion.js") == JS


@pytest.mark.parametrize("bad", ["/* see the <style> block */ a{}", "a{} </style>", "a{content:'<!--'}",
                                 "a{} /* key tile-<id> */"[:-3] + "<b"])
def test_markup_is_caught(bad):
    with pytest.raises(design.DesignFileError):
        design.check(bad, "test")


def test_page_scripts_pass_the_sanitizer():
    """views/ui.py scripts(): the stylesheet loader and motion.js, as sent to st.html. Needs Streamlit installed."""
    pytest.importorskip("streamlit")
    import re

    from views import ui

    html = ui.scripts()
    bodies = re.findall(r"<script>(.*?)</script>", html, re.S)
    assert len(bodies) == 2
    for body in bodies:
        assert not design.MARKUP_PROBE.search(body)
    assert "hub-css" in bodies[0] and ".hub .chip" in bodies[0]


def test_comments_with_angle_brackets_are_fine_once_stripped():
    assert design.prepare_css("/* key tile-<id> */ .a { color: red; }").strip() == ".a { color: red; }"


def test_token_blocks():
    light, dark = design.token_block(CSS, "light"), design.token_block(CSS, "dark")
    assert "--h-bg: #FFFFFF" in light and "--h-bg: #000A62" in dark
    with pytest.raises(design.DesignFileError):
        design.token_block(".a{}", "light")


def test_tool_css_is_sent_without_comments_and_checked(tmp_path):
    """views/ui.py tool_css(): a tool's own stylesheet gets the same treatment as hub.css. Needs Streamlit installed."""
    pytest.importorskip("streamlit")
    from views import ui

    good = tmp_path / "style.css"
    good.write_text("/* scoped to <the tool> */ div.st-key-sec-tool-x p { color: var(--h-text); }", encoding="utf-8")
    ui.tool_css(good)  # outside a running app st.html does nothing, so this only checks it doesn't raise
    bad = tmp_path / "bad.css"
    bad.write_text('div.st-key-sec-tool-x p::after { content: "</p>"; }', encoding="utf-8")
    with pytest.raises(design.DesignFileError, match="bad.css"):
        ui.tool_css(bad)
