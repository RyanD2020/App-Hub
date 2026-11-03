"""Ideas for your team: common manual tasks, what a tool could do, and which of our tools already works that way."""
import streamlit as st

from core.request_form import TEAM_OTHER
from views import ui
from views.ui import chip, esc

cfg = ui.cfg()
ideas = cfg["ideas"]
names = {t["id"]: t["short_name"] for t in cfg["tools"]}
form_teams = cfg["request_form"]["teams"]

ALL = "All teams"
teams = [ALL] + list(dict.fromkeys(i["team"] for i in ideas))

with ui.section("sec-ideas"):
    ui.section_head("Ideas for your team", "Does any of this sound like your week?",
                    "These are common manual tasks and what a tool could do about them. Each one points to "
                    "something we've already built that works the same way.")
    team = st.pills("Filter by team", teams, key=ui.remember("ideas_team", ALL), required=True,
                    label_visibility="collapsed")
    shown = [(n, i) for n, i in enumerate(ideas) if team in (None, ALL) or i["team"] == team]

    with st.container(key="grid3-ideas"):
        for n, idea in shown:
            with st.container(key=f"idea-{n}"):
                ui.html(
                    '<div class="idea">'
                    f'<div class="eyebrow">{esc(idea["team"])}</div><h3>{esc(idea["task"])}</h3>'
                    f'<div class="row"><b>Today</b>{esc(idea["today"])}</div>'
                    f'<div class="row"><b>A tool could</b>{esc(idea["tool_could"])}</div>'
                    "</div>"
                )
                with st.container(key=f"ideafoot-{n}", horizontal=True):
                    proof = idea.get("proof")
                    ui.html(chip(f"Works like {names[proof]}", "match") if proof else chip("New for us", "info"))
                    if st.button("This sounds like us", key=f"sm-idea-{n}", type="secondary"):
                        known = idea["team"] in form_teams
                        ui.prefill(req_task=f'{idea["task"]}. {idea["today"]}',
                                   req_team=idea["team"] if known else TEAM_OTHER,
                                   req_team_name="" if known else idea["team"])
                        ui.toast_next("We've started a request for you. Add your details and submit.")
                        ui.go("request")
