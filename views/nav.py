"""The hub's navigation, built from config/hub.yaml: an "App hub" section for the hub's own pages, then one section per
team in nav_order.

A team's section holds a page for each embedded tool (it runs inside the hub) and each external tool with a url (it
opens in a new tab). A team with nothing to open yet gets one "Nothing here yet" page instead (views/team.py).

Streamlit identifies a page by its url_path, so tool_page() can be called anywhere, for example by st.switch_page on
Our tools, and it matches the page registered here. Building a page imports nothing from tools/: an embedded tool's
code is imported only when its page runs (core/embed.py).
"""
from __future__ import annotations

from typing import Any

import streamlit as st

from core import config, embed
from views import ui

HUB_SECTION = config.HUB_SECTION
EMPTY_TEAM_TITLE = "Nothing here yet"


def hub_pages() -> dict[str, st.Page]:
    """The hub's own pages, keyed as in views/ui.py PAGES."""
    return {key: st.Page(ui.PAGES[key], title=title, default=(key == "home")) for key, title in ui.TABS}


def tool_page(tool: dict[str, Any]) -> st.Page:
    """An embedded tool's page, or an external tool's link page. Its address is the tool id."""
    if config.is_embedded(tool):
        def run_tool() -> None:
            with ui.section(f"sec-tool-{tool['id']}"):
                embed.run(tool)
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
