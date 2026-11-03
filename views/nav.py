"""The hub's navigation, built from config/hub.yaml: an "App hub" section for the hub's own pages, then one section per
team in nav_order.

A team's section holds a page for each embedded tool (it runs inside the hub) and each external tool with a url (it
opens in a new tab). A team with nothing to open yet gets one "Nothing here yet" page instead (views/team.py).

Streamlit identifies a page by its url_path, so tool_page() can be called anywhere, for example by st.switch_page on
Our tools, and it matches the page registered here. Building a page imports nothing from tools/: an embedded tool's
code is imported only when its page runs (core/embed.py). render_tool() guards it: an error shows a short message
and an Email the team link on that tool's page only.
"""
from __future__ import annotations

from typing import Any

import streamlit as st

from core import config, embed, identity
from core import request_form as rf
from views import ui
from views.ui import esc

HUB_SECTION = config.HUB_SECTION
EMPTY_TEAM_TITLE = "Nothing here yet"


def hub_pages() -> dict[str, st.Page]:
    """The hub's own pages, keyed as in views/ui.py PAGES."""
    return {key: st.Page(ui.PAGES[key], title=title, default=(key == "home")) for key, title in ui.TABS}


def render_tool(tool: dict[str, Any]) -> None:
    """Draw an embedded tool inside the hub's page. If it fails, the message appears here, after whatever the tool
    drew before failing; the header, the footer and every other page are unaffected."""
    with ui.section(f"sec-tool-{tool['id']}"):
        embed.run(tool, on_error=show_tool_error)


def show_tool_error(tool: dict[str, Any], error: Exception) -> None:
    """The short message shown in place of a tool that failed, with an email to the admins ready to send."""
    subject, body = embed.error_email(tool, error, identity.signed_in_email())
    link = rf.mailto([a["email"] for a in ui.cfg()["admins"]], subject, body)
    ui.html('<div class="notice tool-error">'
            f'<p><b>{esc(tool["name"])} ran into a problem.</b> The rest of the App hub is working. Try again, or '
            "email the team and we'll look into it.</p>"
            f'<a class="btn btn-ghost btn-sm" href="{esc(link)}">Email the team</a></div>')


def tool_page(tool: dict[str, Any]) -> st.Page:
    """An embedded tool's page, or an external tool's link page. Its address is the tool id."""
    if config.is_embedded(tool):
        def run_tool() -> None:
            render_tool(tool)
        return st.Page(run_tool, title=tool["name"], url_path=tool["id"])
    return st.Page(tool["url"], title=tool["name"], url_path=tool["id"])


def team_page(cfg: dict[str, Any], team: dict[str, Any]) -> st.Page:
    """The "Nothing here yet" page for a team with nothing to open."""
    def run_team() -> None:
        from views import team as team_view

        team_view.render(cfg, team)
    return st.Page(run_team, title=EMPTY_TEAM_TITLE, url_path=f"team-{team['id']}")


def team_sections(cfg: dict[str, Any]) -> dict[str, list[st.Page]]:
    """Team name to its pages, in nav_order."""
    out: dict[str, list[st.Page]] = {}
    for team in config.teams(cfg):
        pages = [tool_page(t) for t in config.team_tools(cfg, team["id"]) if config.opens_in_hub(t)]
        out[team["name"]] = pages or [team_page(cfg, team)]
    return out
