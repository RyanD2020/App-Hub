"""Runs an embedded tool's page (see docs/ADDING_A_TOOL.md).

A tool's code is imported here, when its page runs, and never when the hub starts: building the navigation only
records the module path from config/hub.yaml. So a tool that is slow to import, or broken, costs nothing on every
other page.
"""
from __future__ import annotations

import importlib
from collections.abc import Callable
from typing import Any


class ToolLoadError(RuntimeError):
    """The tool's module can't be found or has no render() function."""


def load_render(module: str) -> Callable[[], None]:
    """Import the tool's page module and return its render()."""
    mod = importlib.import_module(module)
    render = getattr(mod, "render", None)
    if not callable(render):
        raise ToolLoadError(f"{module} has no render() function.")
    return render


def run(tool: dict[str, Any]) -> None:
    """Import an embedded tool and draw its page."""
    load_render(tool["module"])()
