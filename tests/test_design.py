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


def test_comments_with_angle_brackets_are_fine_once_stripped():
    assert design.prepare_css("/* key tile-<id> */ .a { color: red; }").strip() == ".a { color: red; }"


def test_token_blocks():
    light, dark = design.token_block(CSS, "light"), design.token_block(CSS, "dark")
    assert "--h-bg: #FFFFFF" in light and "--h-bg: #000A62" in dark
    with pytest.raises(design.DesignFileError):
        design.token_block(".a{}", "light")
