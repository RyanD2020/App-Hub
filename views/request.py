"""Request a tool: what happens when you submit, the form, and ways to get help.

Part 1 builds the page and checks the form. Saving to the hub_requests Delta table, the request board and My requests
come in Part 2; until then a valid request offers "Email the team instead", prefilled with everything, so nothing is lost.
"""
import streamlit as st

from core import calc, config, identity
from core import request_form as rf
from views import ui
from views.ui import chip, esc

cfg = ui.cfg()
admins = cfg["admins"]
form = cfg["request_form"]
teams = config.request_teams(cfg)  # the teams list in nav order, then Other
subject = cfg["email_subject"]
coach_url = next((t.get("url") for t in cfg["tools"] if t["id"] == "coach"), "")
admin_names = " and ".join(a["short_name"] for a in admins)


def submit() -> None:
    """Runs before the page redraws, so errors show under their fields straight away."""
    s = st.session_state
    draft = rf.validate(s.get("req_task"), s.get("req_team"), s.get("req_team_name"), s.get("req_freq"),
                        s.get("req_tools"), s.get("req_estimate"))
    s["req_errors"] = draft.errors
    s["req_outcome"] = None
    if draft.errors:
        return
    # Part 2 inserts the request here and only reports success once the insert has committed.
    s["req_outcome"] = {"saved": False}


with ui.section("sec-request"):
    ui.section_head("Request a tool", "Tell us what takes up your team's time",
                    "Every request is reviewed. You can follow its progress on the board below.")
    ui.steps([
        ("Saved", "Your request is stored securely on Databricks."),
        ("Team notified", f"Within minutes, {admin_names} get an email and a Teams message, with reminders until "
                          "one of them picks it up."),
        ("Reviewed", "We look at it within a week and get in touch."),
        ("Kept updated", "Follow its status on the request board below."),
    ], reveal="request-steps")

    errors = st.session_state.get("req_errors") or {}
    with st.container(key="grid-req"):
        with st.container(key="reqform"):
            task = st.text_area("What task takes the time?", key=ui.remember("req_task", ""), height=110,
                                placeholder="What you do, step by step, and where it goes wrong")
            if errors.get("task") and not task.strip():
                ui.html(f'<p class="err">{esc(errors["task"])}</p>')
            c1, c2 = st.columns(2)
            team = c1.selectbox("Your team", teams, key=ui.remember("req_team", teams[0]))
            freq = c2.selectbox("How often it happens", form["frequencies"],
                                key=ui.remember("req_freq", form["default_frequency"]))
            team_name = ""
            if team == rf.TEAM_OTHER:
                team_name = st.text_input("Your team's name", max_chars=rf.TEAM_NAME_MAX,
                                          key=ui.remember("req_team_name", ""),
                                          placeholder="For example, Retirement plan services")
                if errors.get("team_name") and not rf.tidy_team_name(team_name):
                    ui.html(f'<p class="err">{esc(errors["team_name"])}</p>')
            tools_today = st.text_input("What you use today", key=ui.remember("req_tools", ""),
                                        placeholder="For example, Excel, email, SAP, PDFs")
            estimate = st.session_state.get("req_estimate")
            if estimate:
                ui.html(chip(calc.estimate_chip(estimate), "match"))
            ui.html('<p class="hint">You\'re submitting as your Databricks login, so there\'s no need to add your '
                    "email. Updates go to that address. If a request can't be saved, you'll see an error and a "
                    "ready-to-send email to the team instead, so nothing gets lost.</p>")
            st.button("Submit request", type="primary", key="req_submit", on_click=submit)

            outcome = st.session_state.get("req_outcome")
            draft = rf.validate(task, team, team_name, freq, tools_today, estimate)
            if outcome and not outcome["saved"] and not draft.errors:
                fallback = rf.mailto([a["email"] for a in admins], subject,
                                     rf.fallback_body(draft, identity.signed_in_email()))
                ui.html('<div class="notice"><p><b>Your request hasn\'t been saved.</b> Saving requests to Databricks '
                        "is switched on in the next release of the hub. Email the team instead: the email below "
                        "already holds everything you entered.</p>"
                        f'<a class="btn btn-ghost btn-sm" href="{esc(fallback)}">Email the team instead</a>'
                        "</div>")

        with st.container(key="reqside"):
            with st.container(key="side-coach"):
                ui.html('<div class="eyebrow">Not sure what you need?</div><h3>Talk it through with Project Coach</h3>'
                        "<p>Describe the problem in your own words. The coach asks questions and helps turn it into a "
                        "clear request you can paste here.</p>")
                if coach_url:
                    st.link_button("Open Project Coach", coach_url, type="primary", key="sm-coach")

            team_shown = rf.tidy_team_name(team_name) if team == rf.TEAM_OTHER else team
            body = rf.contact_body(task, team_shown, freq, tools_today)
            contacts = "".join(
                '<div class="contact">'
                f'<span class="cn">{esc(c["name"])}</span><span class="cd">{esc(c.get("title", ""))}</span>'
                '<div class="btn-row">'
                f'<a class="btn btn-ghost btn-sm" href="{esc(rf.mailto(c["email"], subject, body))}">Email</a>'
                f'<a class="btn btn-ghost btn-sm" href="{esc(rf.teams_chat(c["teams"], cfg["teams_message"]))}" '
                'target="_blank">Message on Teams</a>'
                "</div></div>"
                for c in cfg["contacts"]
            )
            with st.container(key="side-contact"):
                ui.html(f'<div class="eyebrow">Rather talk first?</div><h3>Get in touch</h3><div>{contacts}</div>')

            with st.container(key="side-calc"):
                ui.html('<div class="eyebrow">Want a number first?</div><h3>Start with the calculator</h3>'
                        "<p>A rough hours estimate helps us prioritize, and it attaches to your request "
                        "automatically.</p>")
                if st.button("Open the calculator", type="secondary", key="sm-opencalc"):
                    ui.go("calc")
