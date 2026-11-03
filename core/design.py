"""Prepares design/hub.css and design/motion.js for st.html (standard library only, so it can be tested anywhere).

st.html cleans everything with DOMPurify. DOMPurify 3.4 removes a whole <style> or <script> element if its text holds
anything that looks like markup: "<" followed by a letter, digit, "_", "/" or "!". One such comment in hub.css once
dropped the entire stylesheet without any error. So the CSS is sent without its comments, and both files are checked.
"""
from __future__ import annotations

import re

# DOMPurify's ELEMENT_MARKUP_PROBE: /<[/\w!]/
MARKUP_PROBE = re.compile(r"<[/\w!]")
_CSS_COMMENT = re.compile(r"/\*.*?\*/", re.S)


class DesignFileError(RuntimeError):
    """A design file would be dropped by st.html's sanitizer."""


def token_block(css: str, name: str) -> str:
    """The declarations between /* BEGIN <name> tokens */ :root { ... } /* END <name> tokens */."""
    m = re.search(rf"/\* BEGIN {name} tokens \*/\s*:root\s*\{{(.*?)\}}\s*/\* END {name} tokens \*/", css, re.S)
    if not m:
        raise DesignFileError(f"design/hub.css: the {name} token block markers are missing.")
    return m.group(1)


def check(text: str, what: str) -> str:
    m = MARKUP_PROBE.search(text)
    if m:
        line = text.count("\n", 0, m.start()) + 1
        raise DesignFileError(
            f"{what}, line {line}: {text[m.start():m.start() + 20]!r} looks like HTML markup, so st.html would drop "
            "the whole file. Reword it (for example write 'less than' or remove the angle bracket).")
    return text


def prepare_css(raw: str, what: str = "design/hub.css") -> str:
    """A stylesheet (hub.css, or a tool's own) without comments, checked so st.html keeps it."""
    return check(_CSS_COMMENT.sub("", raw), what)
