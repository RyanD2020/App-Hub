"""Savings calculator: hours a tool could give back each year. The maths is in core/calc.py."""
import streamlit as st

from core import calc
from views import ui
from views.ui import esc

with ui.section("sec-calc"):
    ui.section_head("Savings calculator", "Put a number on the task that takes up your week",
                    "Enter a rough estimate. It doesn't need to be exact to show whether a tool is worth building.")

    with st.container(key="grid-calc"):
        with st.container(key="calcin"):
            task = st.text_input("The task", key=ui.remember("calc_task", ""),
                                 placeholder="For example, matching invoices to contracts")
            c1, c2 = st.columns(2)
            hours = c1.number_input("Hours per week, per person", min_value=0.0, max_value=60.0, step=0.5,
                                    key=ui.remember("calc_hours", calc.HOURS_DEFAULT))
            people = c2.number_input("People who do it", min_value=1, max_value=200, step=1,
                                     key=ui.remember("calc_people", calc.PEOPLE_DEFAULT))
            c3, c4 = st.columns(2)
            weeks = c3.number_input("Weeks per year", min_value=1, max_value=calc.WEEKS_MAX, step=1,
                                    key=ui.remember("calc_weeks", calc.WEEKS_DEFAULT))
            errors = c4.selectbox("How error-prone is it today?", calc.ERROR_LEVELS,
                                  key=ui.remember("calc_errors", calc.ERROR_DEFAULT))
            share = st.slider("Share of the work a tool could take over", min_value=calc.SHARE_MIN,
                              max_value=calc.SHARE_MAX, step=calc.SHARE_STEP, format="%d%%",
                              key=ui.remember("calc_share", calc.SHARE_DEFAULT))
            ui.html('<p class="hint">The bracket tool took over 95% of review time. '
                    "Most tools land between 50% and 80%.</p>")

        e = calc.estimate(hours, people, weeks, share)
        # The hours figure and the bars move from the last estimate shown to this one.
        prev = st.session_state.get("_calc_prev", {"saved": e.hours_saved, "now": 100.0 if e.hours_today else 0.0,
                                                    "after": e.after_share * 100})
        now_pct = 100.0 if e.hours_today else 0.0
        after_pct = e.after_share * 100
        st.session_state["_calc_prev"] = {"saved": e.hours_saved, "now": now_pct, "after": after_pct}

        with st.container(key="onblue-calcout"):
            ui.html(
                '<div class="calc-out">'
                "<h3>Hours your team could get back each year</h3>"
                f'<div class="big"><span data-roll-from="{prev["saved"]}" data-roll-to="{e.hours_saved}">'
                f"{calc.fmt(e.hours_saved)}</span></div>"
                f'<div class="sub">{esc(calc.summary_line(e, errors))}</div>'
                '<div class="compare">'
                f'<div class="lab"><span>Today</span><span>{calc.fmt(e.hours_today)} hrs</span></div>'
                f'<div class="track"><div class="fill" style="--from:{prev["now"]:.2f}%;--to:{now_pct:.2f}%"></div></div>'
                f'<div class="lab"><span>With a tool</span><span>{calc.fmt(e.hours_after)} hrs</span></div>'
                f'<div class="track"><div class="fill after" style="--from:{prev["after"]:.2f}%;--to:{after_pct:.2f}%"></div></div>'
                "</div>"
                '<div class="mini">'
                f'<div><span class="n">{calc.fmt(e.working_weeks)}</span>working weeks back</div>'
                f'<div><span class="n">{calc.fmt(e.ftes)}</span>full-time people\'s worth</div>'
                "</div></div>"
            )
            if st.button("Request a tool for this", type="primary", key="calc_to_request"):
                st.session_state["req_estimate"] = e.hours_saved
                if task.strip():
                    ui.prefill(req_task=task.strip())
                ui.go("request")
            ui.html('<p class="calc-hint">Assumes a 37.5-hour week and 1,800 working hours per person per year.</p>')
