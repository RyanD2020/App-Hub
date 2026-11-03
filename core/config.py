"""Loads config/hub.yaml and checks it, so a typo shows up as a clear message instead of a broken page."""
from __future__ import annotations

import re
from functools import lru_cache
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
CONFIG_PATH = ROOT / "config" / "hub.yaml"

STATUS_CHIPS = {"live", "match", "review", "info", "plain"}
CHECKS = {"Rules-based code", "AI-assisted"}
STAT_FLAGS = {"team", "placeholder", "measured"}
HERO_FLAGS = {"", "team", "placeholder"}
MATRIX_VALUES = {"yes", "planned"}
TOOL_FIELDS = ("id", "name", "short_name", "team", "mode", "category", "status", "status_chip", "checks", "url", "win",
               "summary", "before", "after", "stats", "steps", "built_with", "chart_hours")

EMBEDDED, EXTERNAL = "embedded", "external"
MODES = {EMBEDDED, EXTERNAL}
TEAM_OTHER = "Other"  # always last in the Request a tool dropdown; not a team of its own
HUB_SECTION = "App hub"  # the navigation section for the hub's own pages; not a team name either
ID_PATTERN = re.compile(r"^[a-z][a-z0-9_]*$")
# An embedded tool's module: tools.<team id>.<folder>.page
MODULE_PATTERN = re.compile(r"^tools\.([a-z][a-z0-9_]*)\.([a-z][a-z0-9_]*)\.page$")
# Page addresses the hub's own pages already use (views/ui.py PAGES, named after their files). A tool's address is its
# id, so no tool id may be one of these.
HUB_PAGE_PATHS = {"home", "tools", "platform", "ideas", "calculator", "request"}


class ConfigError(ValueError):
    """hub.yaml is missing something or has a value the app doesn't recognize."""


def parse(text: str) -> dict[str, Any]:
    import yaml  # PyYAML, installed from requirements.txt

    data = yaml.safe_load(text)
    if not isinstance(data, dict):
        raise ConfigError("config/hub.yaml must be a mapping of settings at the top level.")
    return data


def problems(cfg: dict[str, Any]) -> list[str]:
    """Every problem found in a parsed hub.yaml, in plain words. An empty list means it's fine."""
    out: list[str] = []

    teams = cfg.get("teams") or []
    if not teams:
        out.append("teams: add at least one team.")
    team_ids: list[str] = []
    for i, team in enumerate(teams):
        where = f"teams[{i}] ({team.get('id', '?')})"
        tid, name, order = team.get("id"), team.get("name"), team.get("nav_order")
        if not isinstance(tid, str) or not ID_PATTERN.match(tid):
            out.append(f"{where}: id must be lowercase letters, digits and underscores, starting with a letter.")
        team_ids.append(tid)
        if not isinstance(name, str) or not name.strip():
            out.append(f"{where}: add a name.")
        elif name.strip().casefold() in {TEAM_OTHER.casefold(), HUB_SECTION.casefold()}:
            out.append(f"{where}: {name!r} is used by the hub itself; pick another team name.")
        if not isinstance(order, int) or isinstance(order, bool):
            out.append(f"{where}: nav_order must be a whole number.")
    if len(set(team_ids)) != len(team_ids):
        out.append("teams: every id must be different.")
    if len({t.get("name") for t in teams}) != len(teams):
        out.append("teams: every name must be different.")
    if len({t.get("nav_order") for t in teams}) != len(teams):
        out.append("teams: every nav_order must be different.")

    tools = cfg.get("tools") or []
    if not tools:
        out.append("tools: add at least one tool.")
    ids: list[str] = []
    for i, t in enumerate(tools):
        where = f"tools[{i}] ({t.get('id', '?')})"
        for f in TOOL_FIELDS:
            if f not in t:
                out.append(f"{where}: missing {f}.")
        ids.append(t.get("id", ""))
        if not isinstance(t.get("id"), str) or not ID_PATTERN.match(t["id"]):
            out.append(f"{where}: id must be lowercase letters, digits and underscores, starting with a letter.")
        elif t["id"] in HUB_PAGE_PATHS:
            out.append(f"{where}: id {t['id']!r} is the address of one of the hub's own pages; pick another.")
        if t.get("team") not in team_ids:
            out.append(f"{where}: team must be one of the team ids in teams.")
        mode = t.get("mode")
        if mode not in MODES:
            out.append(f"{where}: mode must be embedded or external.")
        elif mode == EMBEDDED:
            m = MODULE_PATTERN.match(t.get("module") or "")
            if not m:
                out.append(f"{where}: an embedded tool needs module, the dotted path of its page.py, "
                           "like tools.<team>.<folder>.page.")
            elif m.group(1) != t.get("team"):
                out.append(f"{where}: module must be in its team's folder, tools.{t.get('team')}.")
            if t.get("url"):
                out.append(f"{where}: an embedded tool runs inside the hub; leave url blank.")
        elif "module" in t:
            out.append(f"{where}: module is only for embedded tools; remove it or set mode to embedded.")
        if t.get("status_chip") not in STATUS_CHIPS:
            out.append(f"{where}: status_chip must be one of {sorted(STATUS_CHIPS)}.")
        if t.get("checks") not in CHECKS:
            out.append(f"{where}: checks must be one of {sorted(CHECKS)}.")
        url = t.get("url") or ""
        if url and not url.startswith("https://"):
            out.append(f"{where}: url must start with https:// or be blank.")
        for s in t.get("stats") or []:
            if s.get("flag") not in STAT_FLAGS:
                out.append(f"{where}: stat {s.get('value')!r} flag must be one of {sorted(STAT_FLAGS)}.")
            if not isinstance(s.get("value"), str) or not s.get("label"):
                out.append(f"{where}: each stat needs a quoted value and a label.")
        hours = t.get("chart_hours")
        if not (isinstance(hours, list) and len(hours) == 2 and all(isinstance(h, (int, float)) and h >= 0 for h in hours)):
            out.append(f"{where}: chart_hours must be [before, after], two numbers of 0 or more.")
    if len(set(ids)) != len(ids):
        out.append("tools: every id must be different.")

    hero = cfg.get("hero") or {}
    for f in ("eyebrow", "title", "figure", "text", "glance"):
        if f not in hero:
            out.append(f"hero: missing {f}.")
    for g in [hero.get("figure") or {}] + list(hero.get("glance") or []):
        if not isinstance(g.get("value"), int) or g.get("value", 0) < 0:
            out.append(f"hero: {g.get('label', 'figure')} value must be a whole number of 0 or more.")
        if g.get("flag", "") not in HERO_FLAGS:
            out.append(f"hero: {g.get('label')} flag must be team, placeholder or blank.")

    for i, idea in enumerate(cfg.get("ideas") or []):
        for f in ("team", "task", "today", "tool_could"):
            if not idea.get(f):
                out.append(f"ideas[{i}]: missing {f}.")
        if idea.get("team") and idea["team"] not in team_ids:
            out.append(f"ideas[{i}]: team {idea['team']!r} isn't a team id.")
        if idea.get("proof") and idea["proof"] not in ids:
            out.append(f"ideas[{i}]: proof {idea['proof']!r} isn't a tool id.")

    plat = cfg.get("platform") or {}
    features = plat.get("features") or []
    for tool_id, row in (plat.get("matrix") or {}).items():
        if tool_id not in ids:
            out.append(f"platform.matrix: {tool_id!r} isn't a tool id.")
        for feat, val in (row or {}).items():
            if feat not in features:
                out.append(f"platform.matrix.{tool_id}: {feat!r} isn't in platform.features.")
            if val not in MATRIX_VALUES:
                out.append(f"platform.matrix.{tool_id}.{feat}: use yes or planned, or leave it out.")
    for layer in plat.get("layers") or []:
        if layer.get("feature") not in features:
            out.append(f"platform.layers: {layer.get('title')!r} feature isn't in platform.features.")

    form = cfg.get("request_form") or {}
    if "teams" in form:
        out.append("request_form.teams: remove it. The dropdown lists the teams list, then Other.")
    if form.get("default_frequency") not in (form.get("frequencies") or []):
        out.append("request_form.default_frequency must be one of request_form.frequencies.")

    admins = cfg.get("admins") or []
    if not admins:
        out.append("admins: add at least one admin.")
    for a in admins:
        for f in ("name", "short_name", "email", "teams"):
            if not a.get(f):
                out.append(f"admins: {a.get('name', '?')} is missing {f}.")
        for f in ("email", "teams"):
            if a.get(f) and "@" not in a[f]:
                out.append(f"admins: {a.get('name')} {f} isn't an email address.")
    for c in cfg.get("contacts") or []:
        for f in ("name", "email", "teams"):
            if not c.get(f):
                out.append(f"contacts: {c.get('name', '?')} is missing {f}.")

    if "escalation_backup" not in cfg:
        out.append("escalation_backup: keep the key, blank until it's supplied.")
    return out


def load(path: Path = CONFIG_PATH) -> dict[str, Any]:
    cfg = parse(path.read_text(encoding="utf-8"))
    found = problems(cfg)
    if found:
        raise ConfigError("config/hub.yaml needs fixing:\n- " + "\n- ".join(found))
    return cfg


@lru_cache(maxsize=1)
def cached() -> dict[str, Any]:
    """The checked config, read once per app process. Redeploy (or restart the app) after editing hub.yaml."""
    return load()


def tool(cfg: dict[str, Any], tool_id: str) -> dict[str, Any] | None:
    return next((t for t in cfg["tools"] if t["id"] == tool_id), None)


def teams(cfg: dict[str, Any]) -> list[dict[str, Any]]:
    """The teams in navigation order."""
    return sorted(cfg["teams"], key=lambda t: t["nav_order"])


def team_names(cfg: dict[str, Any]) -> dict[str, str]:
    """Team id to display name."""
    return {t["id"]: t["name"] for t in cfg["teams"]}


def team_tools(cfg: dict[str, Any], team_id: str) -> list[dict[str, Any]]:
    """A team's tools, in hub.yaml order."""
    return [t for t in cfg["tools"] if t["team"] == team_id]


def request_teams(cfg: dict[str, Any]) -> list[str]:
    """The Request a tool dropdown: every team in navigation order, then Other."""
    return [t["name"] for t in teams(cfg)] + [TEAM_OTHER]


def is_embedded(t: dict[str, Any]) -> bool:
    return t.get("mode") == EMBEDDED


def opens_in_hub(t: dict[str, Any]) -> bool:
    """True if the hub has something to open for this tool: its own page, or an external link."""
    return is_embedded(t) or bool(t.get("url"))
