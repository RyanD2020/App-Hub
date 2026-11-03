"""Home: hero, tool tiles, before/after hours chart, how we work with you, and the call to action."""
import math

import altair as alt
import pandas as pd
import streamlit as st

from views import ui

cfg = ui.cfg()
tools = cfg["tools"]

ui.hero(cfg["hero"], intro=ui.first_time("home-intro"),
        primary=("See our tools", "tools"), secondary=("Estimate your savings", "calc"))

# ------------------------------------------------------------------ tool tiles (3 x 2)
with ui.section("sec-home-tools"):
    ui.section_head("Our tools", "Tools that replace work people used to do by hand")
    with st.container(key="grid3-tiles"):
        for t in tools:
            if ui.tile(t["id"], t["category"], t["short_name"], t["win"], ui.status_chip(t), "See how it works"):
                ui.go("tools", tool=t["id"])
        more = cfg["more_tools_tile"]
        if ui.tile("more", more["category"], more["title"], more["text"], ui.chip(more["chip"], "info"), more["link"]):
            ui.go("request")

# ------------------------------------------------------------------ before / after chart
dark = ui.theme_type() == "dark"
before_colour, after_colour = ("#80BAFF", "#A5EFBF") if dark else ("#000A62", "#0468FF")
text_colour, axis_colour = ("#FFFFFF", "#8C96C8") if dark else ("#000000", "#888888")
series = ["Before", "With the tool"]
order = [t["short_name"] for t in tools]
data = pd.DataFrame([
    {"tool": t["short_name"], "series": s, "hours": h}
    for t in tools for s, h in zip(series, t["chart_hours"])
])
top = max(20, int(math.ceil(max(max(t["chart_hours"]) for t in tools) / 10.0)) * 10)
step = 10 if top <= 60 else int(math.ceil(top / 60.0)) * 10

base = alt.Chart(data).encode(
    x=alt.X("tool:N", sort=order, title=None, scale=alt.Scale(paddingInner=0.35, paddingOuter=0.2),
            axis=alt.Axis(labelAngle=0, labelColor=text_colour, labelFontSize=13, labelLimit=180, labelPadding=10,
                          domainColor=axis_colour, ticks=False)),
    xOffset=alt.XOffset("series:N", sort=series, scale=alt.Scale(paddingInner=0.12)),
    y=alt.Y("hours:Q", title=None, scale=alt.Scale(domain=[0, top], nice=False),
            axis=alt.Axis(values=list(range(0, top + 1, step)), grid=False, ticks=False, labelColor=text_colour,
                          labelFontSize=13, labelPadding=8, domainColor=axis_colour)),
)
bars = base.mark_bar().encode(
    color=alt.Color("series:N", scale=alt.Scale(domain=series, range=[before_colour, after_colour]), legend=None),
    tooltip=[alt.Tooltip("tool:N", title="Tool"), alt.Tooltip("series:N", title=" "),
             alt.Tooltip("hours:Q", title="Hours per month")],
)
labels = base.mark_text(dy=-6, baseline="bottom", fontSize=13, color=text_colour).encode(text="hours:Q")
chart = ((bars + labels)
         .properties(height=320, background="transparent", padding={"left": 4, "right": 4, "top": 18, "bottom": 4})
         .configure(font="Arial")
         .configure_view(strokeWidth=0))

with ui.section("band-home-chart"):
    with st.container(key="chartcard"):
        note = cfg.get("chart_note") or ""
        ui.html(
            '<div class="chart-top"><div><div class="eyebrow">Time saved</div>'
            "<h3>Hours per month, before and after each tool</h3></div>"
            '<div class="chart-right"><div class="legend">'
            f'<span><i style="background:{before_colour}"></i>Before</span>'
            f'<span><i style="background:{after_colour}"></i>With the tool</span></div>'
            f'{ui.chip(note, "placeholder") if note else ""}</div></div>'
        )
        st.altair_chart(chart, theme=None, width="stretch",
                        alt="Hours per month before and after each tool." + (f" {note}." if note else ""))

# ------------------------------------------------------------------ how we work with you
with ui.section("sec-home-how"):
    ui.section_head("How we work with you", "From a task that eats your week to a tool that does it for you")
    ui.steps([
        ("Tell us the task", "Describe what takes the time and who does it."),
        ("Scope it together", "We agree what the tool checks and what stays with people."),
        ("We build it", "On Databricks, with your real files and your sign-off."),
        ("Your team saves time", "Open it from this hub, and we track the hours saved."),
    ], reveal="home-steps")

# ------------------------------------------------------------------ call to action
with st.container(key="cta"):
    text_col, button_col = st.columns([3, 2], vertical_alignment="center")
    with text_col:
        ui.html('<div class="cta"><h2>Could we save your team time too?</h2>'
                "<p>Browse ideas from other teams, or put a number on the task that takes up your week.</p></div>")
    with button_col:
        with st.container(key="onblue-cta-btns", horizontal=True, horizontal_alignment="right"):
            if st.button("Browse ideas", type="primary", key="cta_ideas"):
                ui.go("ideas")
            if st.button("Request a tool", type="secondary", key="cta_request"):
                ui.go("request")
