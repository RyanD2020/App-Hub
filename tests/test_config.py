"""config/hub.yaml parses, passes its own checks, and holds the content the brief asks for.

This is the hub.yaml check: PyYAML isn't installed on the team's laptops, so it runs in Databricks (tests/run_tests.py).
"""
import copy

import pytest

from core import config


@pytest.fixture(scope="module")
def cfg():
    return config.load()  # parses with PyYAML and raises ConfigError listing every problem


def test_no_problems(cfg):
    assert config.problems(cfg) == []


def test_tools_and_statuses(cfg):
    status = {t["name"]: t["status"] for t in cfg["tools"]}
    assert status == {
        "Bracket Counter & Spell Check": "Live",
        "Citi Accruals": "Live",
        "Cadency to SAP reconciliation": "Phase 3 in build",
        "SVIO plan database": "Pilot",
        "Project Coach": "Final edits",
    }


TEAMS = [
    ("all_ia", "All of IA"), ("underwriting", "Underwriting"), ("svio", "SVIO"), ("accounting", "Accounting"),
    ("structured_settlements", "Structured Settlements"), ("stable_value_investments", "Stable Value Investments"),
    ("par", "PAR"), ("guaranteed_products", "Guaranteed Products"), ("prt", "PRT"), ("service", "Service"),
]


def test_teams_in_nav_order(cfg):
    assert [(t["id"], t["name"]) for t in config.teams(cfg)] == TEAMS


def test_request_dropdown_is_the_teams_then_other(cfg):
    assert config.request_teams(cfg) == [name for _, name in TEAMS] + ["Other"]


def test_every_tool_has_a_team_and_a_mode(cfg):
    assert {t["id"]: t["team"] for t in cfg["tools"]} == {
        "bracket": "underwriting", "accruals": "underwriting", "cadency": "accounting", "svio": "svio",
        "coach": "all_ia",
    }
    assert all(t["mode"] in config.MODES for t in cfg["tools"])


def test_embedded_tools_point_into_their_team_folder(cfg):
    for t in cfg["tools"]:
        if config.is_embedded(t):
            assert t["module"].startswith(f"tools.{t['team']}.") and t["module"].endswith(".page"), t["id"]
            assert not t["url"], t["id"]


def test_ideas_use_team_ids(cfg):
    ids = {t["id"] for t in cfg["teams"]}
    assert all(i["team"] in ids for i in cfg["ideas"])


def test_external_tools_link_to_their_current_apps(cfg):
    """Until a tool moves into the hub, Our tools and Team tools link to its own Databricks App."""
    assert {t["id"]: t["url"] for t in cfg["tools"] if not config.is_embedded(t)} == {
        "bracket": "https://bracket-app-3267307435697917.aws.databricksapps.com",
        "accruals": "https://citiaccruals-3267307435697917.aws.databricksapps.com",
        "cadency": "https://fastreconciler-3267307435697917.aws.databricksapps.com",
        "svio": "https://svio-coda-app-3267307435697917.aws.databricksapps.com",
        "coach": "https://project-coach-3267307435697917.aws.databricksapps.com",
    }


def test_teams_with_tools_list_them_instead_of_nothing_here_yet(cfg):
    """views/nav.py gives a team the "Nothing here yet" page only when none of its tools can be opened."""
    for team in ("all_ia", "underwriting", "accounting", "svio"):
        assert any(config.opens_in_hub(t) for t in config.team_tools(cfg, team)), team
    for team in ("structured_settlements", "stable_value_investments", "par", "guaranteed_products", "prt",
                 "service"):
        assert config.team_tools(cfg, team) == [], team


def test_every_tool_has_full_content(cfg):
    for t in cfg["tools"]:
        assert t["win"] and t["summary"] and t["before"] and t["after"]
        assert len(t["steps"]) == 5 and t["built_with"] and len(t["stats"]) >= 3
        assert t["checks"] in config.CHECKS
        assert all(isinstance(s["value"], str) for s in t["stats"])


def test_hero_figures(cfg):
    h = cfg["hero"]
    assert (h["figure"]["value"], h["figure"]["suffix"]) == (95, "%")
    glance = {g["label"]: g for g in h["glance"]}
    assert (glance["Tools built by our team"]["value"], glance["Tools built by our team"]["suffix"]) == (10, "+")
    assert glance["Contract errors caught"]["value"] == 100
    assert (glance["Added software cost"]["prefix"], glance["Added software cost"]["value"]) == ("$", 0)
    assert glance["Hours saved per year"]["flag"] == "placeholder"


def test_admins_and_contacts(cfg):
    assert [(a["name"], a["email"], a["teams"]) for a in cfg["admins"]] == [
        ("Muhammad F. Adil", "Muhammad_Adil@nylim.com", "madil@newyorklife.com"),
        ("Ryan E. Doswell", "ryan_e_doswell@newyorklife.com", "rdoswell@newyorklife.com"),
    ]
    assert [c["email"] for c in cfg["contacts"]] == [a["email"] for a in cfg["admins"]]
    assert cfg["email_subject"] == "App hub: tool request"
    assert cfg["escalation_backup"] == ""


def test_ideas_and_matrix(cfg):
    assert len(cfg["ideas"]) == 12
    # Citi Accruals runs as the citiaccruals Databricks App and keeps its data in Delta tables (its core/db.py).
    assert cfg["platform"]["matrix"]["accruals"]["Databricks Apps"] == "yes"
    assert cfg["platform"]["matrix"]["accruals"]["Delta tables"] == "yes"
    assert cfg["platform"]["next"][1]["text"].startswith('Type a question like "funded amount')


def test_problems_are_reported_in_plain_words(cfg):
    bad = copy.deepcopy(cfg)
    bad["tools"][0]["status_chip"] = "green"
    bad["tools"][1]["stats"][0]["flag"] = "ph"
    bad["tools"][2]["url"] = "http://not-secure"
    bad["ideas"][0]["proof"] = "nope"
    bad["platform"]["matrix"]["svio"]["Databricks Apps"] = "maybe"
    bad["request_form"]["teams"] = ["Finance", "Other"]
    found = "\n".join(config.problems(bad))
    for text in ("status_chip", "flag must be one of", "https://", "isn't a tool id", "use yes or planned",
                 "request_form.teams: remove it"):
        assert text in found, text


def test_team_and_mode_problems_are_reported(cfg):
    bad = copy.deepcopy(cfg)
    bad["teams"].append({"id": "Bad Id", "name": "Other", "nav_order": 1})
    bad["tools"][0]["team"] = "nope"
    bad["tools"][1]["mode"] = "iframe"
    bad["tools"][2].update(mode="embedded", module="tools.underwriting.cadency.page")  # cadency is accounting
    bad["tools"][3].update(mode="embedded")  # no module
    bad["tools"][4]["module"] = "tools.all_ia.coach.page"  # external, but has a module
    bad["ideas"][0]["team"] = "Finance"
    found = "\n".join(config.problems(bad))
    for text in ("id must be lowercase", "used by the hub itself", "every nav_order must be different",
                 "team must be one of the team ids", "mode must be embedded or external",
                 "module must be in its team's folder, tools.accounting", "an embedded tool needs module",
                 "module is only for embedded tools", "team 'Finance' isn't a team id"):
        assert text in found, text


def test_tool_ids_cant_take_a_hub_page_address(cfg):
    bad = copy.deepcopy(cfg)
    bad["tools"][0]["id"] = "request"
    assert any("address of one of the hub's own pages" in p for p in config.problems(bad))


def test_hub_page_addresses_match_the_page_files():
    """config.HUB_PAGE_PATHS must list every hub page's address (its file name), or a tool id could take one."""
    pytest.importorskip("streamlit")
    from pathlib import Path

    from views import ui

    assert config.HUB_PAGE_PATHS == {Path(p).stem for p in ui.PAGES.values()}
