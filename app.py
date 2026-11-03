"""App hub: the front door to the team's tools (Databricks App, Streamlit 1.66.1)."""
import os

import streamlit as st

HERE = os.path.dirname(os.path.abspath(__file__))
LOGO = os.path.join(HERE, "assets", "nyl_logo.png")
st.set_page_config(page_title="App hub", page_icon=LOGO, layout="wide")

from core import config, design  # noqa: E402  (after set_page_config)
from views import ui  # noqa: E402

try:
    st.html(ui.css())  # style-only, so it takes no space on the page
    st.html(ui.motion_script(), unsafe_allow_javascript=True)  # our own file; no user input reaches it
except design.DesignFileError as e:
    st.error(f"The App hub's design files need fixing.\n\n{e}")
    st.stop()
st.logo(LOGO, size="large")

try:
    ui.cfg()
except (config.ConfigError, OSError) as e:
    st.error(f"The App hub can't start because of its settings file.\n\n{e}")
    st.stop()

pages = [
    st.Page(ui.PAGES["home"], title="Home", default=True),
    st.Page(ui.PAGES["tools"], title="Our tools"),
    st.Page(ui.PAGES["platform"], title="Built on Databricks"),
    st.Page(ui.PAGES["ideas"], title="Ideas for your team"),
    st.Page(ui.PAGES["calc"], title="Savings calculator"),
    st.Page(ui.PAGES["request"], title="Request a tool"),
]
nav = st.navigation(pages, position="top")
# The Home intro is the session's opening moment: it plays only if Home is the first page opened.
if ui.first_time("session-start") and nav.title != "Home":
    ui.mark_seen("home-intro")
ui.show_pending_toast()

try:
    nav.run()
finally:
    ui.save_kept()  # also after a page calls st.switch_page or st.stop
    ui.footer()
