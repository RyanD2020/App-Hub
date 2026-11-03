"""Runs an embedded tool's page (see docs/ADDING_A_TOOL.md).

A tool's code is imported here, when its page runs, and never when the hub starts: building the navigation only
records the module path from config/hub.yaml. So a tool that is slow to import, or broken, costs nothing on every
other page.

run() is the hub's guard around a tool: any error while importing or drawing the tool is caught, logged with its
traceback, and handed to on_error, which shows a short message on that tool's page only. The rest of the hub (header,
footer, every other page) keeps working. Streamlit's own st.stop, st.rerun and st.switch_page are not errors: they
derive from BaseException, so they pass straight through.

Standard library only, so it can be tested without Streamlit.
"""
from __future__ import annotations

import importlib
import logging
from collections.abc import Callable
from datetime import datetime, timezone
from typing import Any

_LOG = logging.getLogger("app_hub.tools")
ERROR_DETAIL_MAX = 300  # characters of the error message carried into the email


class ToolLoadError(RuntimeError):
    """The tool's module can't be found or has no render() function."""


def load_render(module: str) -> Callable[[], None]:
    """Import the tool's page module and return its render()."""
    mod = importlib.import_module(module)
    render = getattr(mod, "render", None)
    if not callable(render):
        raise ToolLoadError(f"{module} has no render() function.")
    return render


def run(tool: dict[str, Any], on_error: Callable[[dict[str, Any], Exception], None]) -> bool:
    """Import an embedded tool and draw its page. Returns False if it failed (on_error has then been called)."""
    try:
        load_render(tool["module"])()
    except Exception as error:  # noqa: BLE001  (any tool error stays on the tool's page)
        _LOG.exception("Tool %r (%s) failed", tool.get("id"), tool.get("module"))
        on_error(tool, error)
        return False
    return True


def error_summary(error: BaseException) -> str:
    """One line for people: the error's type and the start of its message."""
    text = " ".join(str(error).split())
    if len(text) > ERROR_DETAIL_MAX:
        text = text[:ERROR_DETAIL_MAX - 3] + "..."
    return f"{type(error).__name__}: {text}" if text else type(error).__name__


def error_email(tool: dict[str, Any], error: BaseException, user: str | None = None,
                when: datetime | None = None) -> tuple[str, str]:
    """Subject and body for the Email the team link shown when a tool fails."""
    when = when or datetime.now(timezone.utc)
    subject = f"App hub: {tool['name']} isn't working"
    lines = [
        "Hi,",
        "",
        f"{tool['name']} showed an error in the App hub.",
        "",
        f"Tool: {tool['name']} ({tool['id']})",
        f"When: {when.astimezone(timezone.utc):%Y-%m-%d %H:%M} UTC",
        f"Error: {error_summary(error)}",
    ]
    if user:
        lines.append(f"Signed in as: {user}")
    lines += ["", "What I was doing:", ""]
    return subject, "\n".join(lines)
