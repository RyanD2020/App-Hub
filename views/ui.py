"""Branded HTML helpers for the App hub (the prototype's markup) and a few session helpers.

st.html sanitizes everything with DOMPurify (no scripts unless asked, no SVG). Every value that comes from config or a
user is escaped with esc() before it goes into HTML. The styles are in design/hub.css.
"""
from __future__ import annotations

import base64
import html as _html
import json
from functools import lru_cache
from pathlib import Path

import streamlit as st

from core import config, design

ROOT = Path(__file__).resolve().parent.parent
# Shown in the footer so anyone can tell which version is deployed. Bump it with every release.
BUILD = "4"

HUB_CSS = ROOT / "design" / "hub.css"
MOTION_JS = ROOT / "design" / "motion.js"
LOGO = ROOT / "assets" / "nyl_logo.png"

# Page files, relative to app.py, as st.navigation and st.switch_page expect.
PAGES = {
    "home": "views/home.py",
    "tools": "views/tools.py",
    "platform": "views/platform.py",
    "ideas": "views/ideas.py",
    "calc": "views/calculator.py",
    "request": "views/request.py",
}
# Header tabs, in the prototype's order and wording.
TABS = [("home", "Home"), ("tools", "Our tools"), ("platform", "Built on Databricks"),
        ("ideas", "Ideas for your team"), ("calc", "Savings calculator"), ("request", "Request a tool")]

# Status chips (design rules): kind -> CSS classes
CHIP_CLASSES = {
    "live": "chip-match chip-live", "match": "chip-match", "pass": "chip-match", "succeeded": "chip-match",
    "review": "chip-review", "waiting": "chip-review", "placeholder": "chip-review", "high": "chip-review",
    "info": "chip-info", "pilot": "chip-info", "team": "chip-info", "medium": "chip-info",
    "plain": "chip-plain", "low": "chip-plain",
}
FLAG_CHIPS = {"team": ("Team figure", "team"), "placeholder": ("Placeholder", "placeholder")}


def esc(v) -> str:
    return _html.escape("" if v is None else str(v), quote=True)


def cfg() -> dict:
    return config.cached()


# ------------------------------------------------------------------ design and motion
def theme_type() -> str | None:
    """"light" or "dark" as picked in Streamlit's settings menu (the system setting by default), or None if
    Streamlit hasn't reported it yet."""
    try:
        t = getattr(st.context.theme, "type", None)
    except Exception:
        return None
    return t if t in ("light", "dark") else None


@lru_cache(maxsize=1)
def _css_source() -> tuple[str, str, str]:
    raw = HUB_CSS.read_text(encoding="utf-8")
    # Comments are stripped and the result checked: st.html drops a whole <style> whose text looks like markup.
    return design.prepare_css(raw), design.token_block(raw, "light"), design.token_block(raw, "dark")


def css() -> str:
    """design/hub.css, with its colour tokens pinned to the Streamlit theme in use so the branded HTML and
    Streamlit's own widgets always agree. Style-only, so Streamlit puts it where it takes no space."""
    src, light, dark = _css_source()
    pinned = {"light": light, "dark": dark}.get(theme_type())
    extra = f"\n:root:root {{{pinned}}}" if pinned else ""
    return f"<style>{src}{extra}</style>"


@lru_cache(maxsize=1)
def _motion_source() -> str:
    return design.check(MOTION_JS.read_text(encoding="utf-8"), "design/motion.js")


def scripts() -> str:
    """Two scripts for st.html(unsafe_allow_javascript=True):
    1. puts hub.css (with the pinned theme tokens) into a <style id="hub-css"> in the page head. A stylesheet made by
       script never passes through st.html's sanitizer, so the design can't be dropped silently. css() still sends the
       same CSS the ordinary way, so the page is styled even where scripts are blocked.
    2. design/motion.js (count-up, roll, reveal on scroll)."""
    sheet = css()[len("<style>"):-len("</style>")]
    loader = ("(function(){var s=document.getElementById('hub-css');"
              "if(!s){s=document.createElement('style');s.id='hub-css';document.head.appendChild(s);}"
              f"var c={json.dumps(sheet)};if(s.textContent!==c){{s.textContent=c;}}}})();")
    design.check(loader, "the stylesheet loader")
    return f"<script>{loader}</script><script>{_motion_source()}</script>"


@lru_cache(maxsize=1)
def logo_uri() -> str:
    return "data:image/png;base64," + base64.b64encode(LOGO.read_bytes()).decode("ascii")


def html(body: str, cls: str = "") -> None:
    st.html(f'<div class="hub {cls}">{body}</div>' if cls else f'<div class="hub">{body}</div>')


# ------------------------------------------------------------------ session helpers
def first_time(flag: str) -> bool:
    """True on the first call in this session, False afterwards. Entrance animations use it so they play once."""
    seen = st.session_state.setdefault("_once", set())
    if flag in seen:
        return False
    seen.add(flag)
    return True


def mark_seen(flag: str) -> None:
    """Treat a first-time moment as already shown (for example the Home intro when the session starts elsewhere)."""
    st.session_state.setdefault("_once", set()).add(flag)


def kept() -> dict:
    """Form values kept across pages. Streamlit drops a widget's value when its page isn't showing."""
    return st.session_state.setdefault("_kept", {})


def remember(key: str, default):
    """Use as a widget key: the widget starts from its kept value (or the default) and save_kept() stores it."""
    if key not in st.session_state:
        st.session_state[key] = kept().get(key, default)
    st.session_state.setdefault("_kept_keys", set()).add(key)
    return key


def save_kept() -> None:
    """Called by app.py after every page run."""
    store = kept()
    for key in st.session_state.get("_kept_keys", ()):
        if key in st.session_state:
            store[key] = st.session_state[key]


def prefill(**values) -> None:
    """Set kept form values for a page that isn't showing yet (for example the request form from Ideas)."""
    store = kept()
    for key, value in values.items():
        store[key] = value
        st.session_state.pop(key, None)


def toast_next(message: str) -> None:
    """Show a toast on the next page, after st.switch_page."""
    st.session_state["_toast"] = message


def show_pending_toast() -> None:
    msg = st.session_state.pop("_toast", None)
    if msg:
        st.toast(msg, duration="long")


def go(page: str, **query) -> None:
    st.switch_page(PAGES[page], query_params=query or None)


# ------------------------------------------------------------------ pieces
def chip(text: str, kind: str = "plain") -> str:
    return f'<span class="chip {CHIP_CLASSES.get(kind, "chip-plain")}">{esc(text)}</span>'


def flag_chip(flag: str | None) -> str:
    label_kind = FLAG_CHIPS.get(flag or "")
    return chip(*label_kind) if label_kind else ""


def status_chip(tool: dict) -> str:
    return chip(tool["status"], tool.get("status_chip", "plain"))


def section(key: str):
    """A full-width section. key starts with "sec-" (page background) or "band-" (Grey band)."""
    assert key.startswith(("sec-", "band-")), key
    return st.container(key=key)


def section_head_html(eyebrow: str | None, title: str, text: str | None = None) -> str:
    parts = ['<div class="section-head">']
    if eyebrow:
        parts.append(f'<div class="eyebrow">{esc(eyebrow)}</div>')
    parts.append(f"<h2>{esc(title)}</h2>")
    if text:
        parts.append(f"<p>{esc(text)}</p>")
    parts.append("</div>")
    return "".join(parts)


def section_head(eyebrow: str | None, title: str, text: str | None = None) -> None:
    html(section_head_html(eyebrow, title, text))


def _number(value: int, prefix: str, suffix: str, count: bool) -> str:
    inner = (f'<span data-count="{int(value)}" data-delay="800">{int(value):,}</span>' if count
             else f"{int(value):,}")
    return f"{esc(prefix)}{inner}{esc(suffix)}"


def hero(h: dict, intro: bool, primary: tuple[str, str], secondary: tuple[str, str]) -> None:
    """Home hero: Dark Blue field cut by the diagonal, "At a glance" on Grey. On the first visit (intro) the field
    sweeps in, the text rises in and the numbers count up. primary and secondary are (label, page)."""
    fig = h["figure"]
    left = (
        f'<div class="hero-left{" intro" if intro else ""}">'
        f'<div class="eyebrow">{esc(h["eyebrow"])}</div>'
        f'<h1>{esc(h["title"])}</h1>'
        f'<div class="hero-figure">{_number(fig["value"], fig.get("prefix", ""), fig.get("suffix", ""), intro)}</div>'
        f'<p>{esc(h["text"])}</p>'
        "</div>"
    )
    rows = "".join(
        f'<li><span class="num">{_number(g["value"], g.get("prefix", ""), g.get("suffix", ""), intro)}</span>'
        f'<span class="lbl">{esc(g["label"])}{flag_chip(g.get("flag"))}</span></li>'
        for g in h["glance"]
    )
    right = f'<div class="hero-right{" intro" if intro else ""}"><h2>At a glance</h2><ul class="glance">{rows}</ul></div>'

    with st.container(key="hero-intro" if intro else "hero"):
        with st.container(key="hero-left"):
            html(left)
            with st.container(key="onblue-hero-btns", horizontal=True):
                if st.button(primary[0], type="primary", key="hero_primary"):
                    go(primary[1])
                if st.button(secondary[0], type="secondary", key="hero_secondary"):
                    go(secondary[1])
        with st.container(key="hero-right"):
            html(right)


def kpi_cards_html(cards: list[tuple[str, str, str]]) -> str:
    """Stat or KPI cards: (value, label, chip HTML or "")."""
    return '<div class="stats">' + "".join(
        f'<div class="stat"><div class="v">{esc(v)}</div><div class="l">{esc(label)}</div>{chip_html}</div>'
        for v, label, chip_html in cards
    ) + "</div>"


def kpi_cards(cards: list[tuple[str, str, str]]) -> None:
    html(kpi_cards_html(cards))


def steps_html(items: list[tuple[str, str]], reveal: str | None = None) -> str:
    """Four chevrons (Dark Blue, Blue, Green, Light Green). reveal names them so they fill in left to right the
    first time they scroll into view in this session."""
    attr = f' data-reveal="{esc(reveal)}"' if reveal else ""
    return f'<div class="steps"{attr}>' + "".join(
        f'<div class="step s{i}"><h4>{esc(t)}</h4>{f"<p>{esc(p)}</p>" if p else ""}</div>'
        for i, (t, p) in enumerate(items, start=1)
    ) + "</div>"


def steps(items: list[tuple[str, str]], reveal: str | None = None) -> None:
    html(steps_html(items, reveal))


def tile(key: str, category: str, title: str, text: str, chip_html: str, link_label: str) -> bool:
    """A Home tool tile. The whole tile is one click target; returns True when clicked."""
    with st.container(key=f"tile-{key}"):
        html(f'<div class="tile"><span class="cat">{esc(category)}</span><h3>{esc(title)}</h3>'
             f'<span class="win">{esc(text)}</span>{chip_html}</div>')
        return st.button(link_label, key=f"gotile-{key}", type="tertiary")


def html_table_html(headers: list[str], rows: list[list[str]], center: set[int] = frozenset(),
                    cls: str = "") -> str:
    """A flat table with Dark Blue headers. Cells are HTML: escape text with esc() first."""
    def c(i):
        return ' class="c"' if i in center else ""
    head = "".join(f"<th{c(i)}>{esc(h)}</th>" for i, h in enumerate(headers))
    body = "".join("<tr>" + "".join(f"<td{c(i)}>{v}</td>" for i, v in enumerate(r)) + "</tr>" for r in rows)
    return f'<div class="table-scroll"><table class="{esc(cls)}"><thead><tr>{head}</tr></thead><tbody>{body}</tbody></table></div>'


def html_table(headers: list[str], rows: list[list[str]], center: set[int] = frozenset(), cls: str = "") -> None:
    html(html_table_html(headers, rows, center, cls))


def header(current: str) -> None:
    """The prototype's header: logo and "App hub" (back to Home), then one tab per page with the current one solid.
    Streamlit's own top bar is hidden (design/hub.css) and st.navigation runs with position="hidden"."""
    with st.container(key="hub-header", horizontal=True, vertical_alignment="center"):
        with st.container(key="hub-brand", horizontal=True, vertical_alignment="center", width="content"):
            st.html(f'<img class="hub-brand-logo" src="{logo_uri()}" alt="New York Life">', width="content")
            if st.button("App hub", key="nav-brand", type="tertiary"):
                go("home")
        with st.container(key="hub-tabs", horizontal=True, wrap=False, vertical_alignment="center"):
            for page, title in TABS:
                if st.button(title, key=f"nav-{page}", type="primary" if page == current else "tertiary"):
                    go(page)


def footer() -> None:
    st.html(f'<footer class="hub site-footer"><div class="foot-inner"><img src="{logo_uri()}" alt="New York Life">'
            "<span>New York Life Insurance Company. For internal use only.</span>"
            f'<span class="right">Build {esc(BUILD)}</span></div></footer>')
