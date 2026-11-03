"""App hub: the front door to the team's tools (Databricks App, Streamlit 1.66.1)."""
import os

import streamlit as st

HERE = os.path.dirname(os.path.abspath(__file__))
LOGO = os.path.join(HERE, "assets", "nyl_logo.png")
st.set_page_config(page_title="App hub", page_icon=LOGO, layout="wide")

from core import config, design  # noqa: E402  (after set_page_config)
from views import nav as hub_nav  # noqa: E402
from views import ui  # noqa: E402

try:
    st.html(ui.css())  # style-only, so it takes no space on the page
    st.html(ui.scripts(), unsafe_allow_javascript=True)  # our own files; no user input reaches them
except design.DesignFileError as e:
    st.error(f"The App hub's design files need fixing.\n\n{e}")
    st.stop()

try:
    ui.cfg()
except (config.ConfigError, OSError) as e:
    st.error(f"The App hub can't start because of its settings file.\n\n{e}")
    st.stop()

# Streamlit handles the routing; the header is the prototype's own (ui.header), so Streamlit draws no navigation.
# Sections come from hub.yaml: the hub's own pages, then one per team (views/nav.py). A tool's code is imported only
# when its page runs.
pages = hub_nav.hub_pages()
teams = hub_nav.team_sections(ui.cfg())
nav = st.navigation({hub_nav.HUB_SECTION: list(pages.values()), **teams}, position="hidden")
current = next((k for k, p in pages.items() if p.url_path == nav.url_path), None)  # None on a team's page

# The Home intro is the session's opening moment: it plays only if Home is the first page opened.
if ui.first_time("session-start") and current != "home":
    ui.mark_seen("home-intro")

ui.header(current, teams)
ui.show_pending_toast()

try:
    nav.run()
finally:
    ui.save_kept()  # also after a page calls st.switch_page or st.stop
    ui.footer()
