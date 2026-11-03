"""A team's "Nothing here yet" page: shown in the Team tools menu for a team with no tool to open from the hub."""
from __future__ import annotations

from typing import Any

import streamlit as st

from core import config
from views import ui


def render(cfg: dict[str, Any], team: dict[str, Any]) -> None:
    name = team["name"]
    listed = config.team_tools(cfg, team["id"])  # in hub.yaml, but with no page or link yet
    with ui.section(f"sec-team-{team['id']}"):
        if listed:
            short = [t["short_name"] for t in listed]
            names = short[0] if len(short) == 1 else ", ".join(short[:-1]) + " and " + short[-1]
            text = (f"{names} {'is' if len(listed) == 1 else 'are'} on the way to the hub. You can read how "
                    f"{'it works' if len(listed) == 1 else 'they work'} on Our tools.")
        else:
            text = (f"There are no {name} tools in the hub yet. If a task takes up your team's time, tell us about it "
                    "and we'll look at building one.")
        ui.section_head(name, "Nothing here yet", text)
        with st.container(key=f"team-btns-{team['id']}", horizontal=True):
            if st.button("Request a tool", type="primary", key=f"team-request-{team['id']}"):
                ui.prefill(req_team=name)
                ui.go("request")
            if listed and st.button("See them on Our tools" if len(listed) > 1 else "See it on Our tools",
                                    type="secondary", key=f"team-tools-{team['id']}"):
                ui.go("tools", tool=listed[0]["id"])
