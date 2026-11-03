"""Ideas for your team: common manual tasks, what a tool could do, and which of our tools already works that way."""
import streamlit as st

from core import config
from views import ui
from views.ui import chip, esc

cfg = ui.cfg()
ideas = cfg["ideas"]
names = {t["id"]: t["short_name"] for t in cfg["tools"]}
team_names = config.team_names(cfg)

ALL = "All teams"
# The filter lists the teams that have ideas, in the teams list's order.
with_ideas = {i["team"] for i in ideas}
teams = [ALL] + [t["name"] for t in config.teams(cfg) if t["id"] in with_ideas]

with ui.section("sec-ideas"):
    ui.section_head("Ideas for your team", "Does any of this sound like your week?",
                    "These are common manual tasks and what a tool could do about them. Each one points to "
                    "something we've already built that works the same way.")
    team = st.pills("Filter by team", teams, key=ui.remember("ideas_team", ALL), required=True,
                    label_visibility="collapsed")
    shown = [(n, i) for n, i in enumerate(ideas) if team in (None, ALL) or team_names[i["team"]] == team]

    with st.container(key="grid3-ideas"):
        for n, idea in shown:
            with st.container(key=f"idea-{n}"):
                ui.html(
                    '<div class="idea">'
                    f'<div class="eyebrow">{esc(team_names[idea["team"]])}</div><h3>{esc(idea["task"])}</h3>'
                    f'<div class="row"><b>Today</b>{esc(idea["today"])}</div>'
                    f'<div class="row"><b>A tool could</b>{esc(idea["tool_could"])}</div>'
                    "</div>"
                )
                with st.container(key=f"ideafoot-{n}"):  # chip, then the button under it, on every card
                    proof = idea.get("proof")
                    ui.html(chip(f"Works like {names[proof]}", "match") if proof else chip("New for us", "info"))
                    if st.button("This sounds like us", key=f"sm-idea-{n}", type="secondary"):
                        ui.prefill(req_task=f'{idea["task"]}. {idea["today"]}',
                                   req_team=team_names[idea["team"]], req_team_name="")
                        ui.toast_next("We've started a request for you. Add your details and submit.")
                        ui.go("request")
