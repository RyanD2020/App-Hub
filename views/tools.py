"""Our tools: a tool picker and each tool's before and after, stats, how it works and what it's built with."""
import streamlit as st

from views import ui
from views.ui import chip, esc, flag_chip, status_chip

cfg = ui.cfg()
tools = cfg["tools"]
ids = [t["id"] for t in tools]

# The chosen tool lives in the URL (?tool=bracket), so a Home tile can open it and the page can be bookmarked.
# Coming back through the top navigation (no ?tool=) shows the last tool picked in this session.
chosen = st.query_params.get("tool") or st.session_state.get("_tool")
if chosen not in ids:
    chosen = ids[0]
st.session_state["_tool"] = chosen
st.query_params["tool"] = chosen


def pick(tool_id: str) -> None:
    st.query_params["tool"] = tool_id
    st.session_state["_tool"] = tool_id


tool = next(t for t in tools if t["id"] == chosen)

with ui.section("sec-tools"):
    ui.section_head("Our tools", "Before and after, tool by tool",
                    "Pick a tool to see the old process, the new one, and what changed.")
    with st.container(key="grid-tools"):
        with st.container(key="toollist"):
            for t in tools:
                with st.container(key=("picked-" if t["id"] == chosen else "pick-") + t["id"]):
                    st.button(t["short_name"], key=f"pickbtn-{t['id']}", type="tertiary", on_click=pick,
                              args=(t["id"],))
                    ui.html(f'<span class="tc">{esc(t["category"])}, {esc(t["status"].lower())}</span>')

        with st.container(key="tooldetail"):
            checks_kind = "info" if tool["checks"] == "AI-assisted" else "plain"
            stats = "".join(
                f'<div class="stat"><div class="v">{esc(s["value"])}</div><div class="l">{esc(s["label"])}</div>'
                f'{flag_chip(s.get("flag"))}</div>'
                for s in tool["stats"]
            )
            ui.html(
                '<div class="tool-detail">'
                f'<div class="eyebrow">{esc(tool["category"])}</div><h2>{esc(tool["name"])}</h2>'
                f'<div class="meta">{status_chip(tool)}{chip(tool["checks"], checks_kind)}</div>'
                f'<p class="summary">{esc(tool["summary"])}</p>'
                '<div class="ba">'
                f'<div class="ba-card"><h3>Before</h3><p>{esc(tool["before"])}</p></div>'
                f'<div class="ba-card after"><h3>With the tool</h3><p>{esc(tool["after"])}</p></div>'
                "</div>"
                f'<div class="stats">{stats}</div>'
                "</div>"
            )
            with st.container(key="grid-how"):
                ui.html('<div class="how"><h3>How it works</h3><ol>'
                        + "".join(f"<li>{esc(s)}</li>" for s in tool["steps"]) + "</ol></div>")
                with st.container(key="howright"):
                    ui.html('<div class="how"><h3>Built with</h3><div class="built">'
                            + "".join(chip(b, "plain") for b in tool["built_with"]) + "</div></div>")
                    if tool.get("url"):
                        st.link_button(f"Open {tool['short_name']}", tool["url"], type="primary",
                                       key=f"open-{tool['id']}")
                    else:
                        ui.html(chip("Link coming soon", "plain"))
            any_placeholder = any(s.get("flag") == "placeholder" for s in tool["stats"])
            notes = cfg.get("tool_notes") or {}
            note = notes.get("placeholder") if any_placeholder else notes.get("team")
            if note:
                ui.html(f'<p class="note">{esc(note)}</p>')
