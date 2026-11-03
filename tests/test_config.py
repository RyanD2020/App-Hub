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


def test_only_project_coach_has_a_url(cfg):
    urls = {t["id"]: t["url"] for t in cfg["tools"]}
    assert urls.pop("coach") == "https://project-coach-3267307435697917.aws.databricksapps.com"
    assert set(urls.values()) == {""}


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
    assert cfg["platform"]["matrix"]["accruals"]["Databricks Apps"] == "planned"
    assert cfg["platform"]["next"][1]["text"].startswith('Type a question like "funded amount')


def test_problems_are_reported_in_plain_words(cfg):
    bad = copy.deepcopy(cfg)
    bad["tools"][0]["status_chip"] = "green"
    bad["tools"][1]["stats"][0]["flag"] = "ph"
    bad["tools"][2]["url"] = "http://not-secure"
    bad["ideas"][0]["proof"] = "nope"
    bad["platform"]["matrix"]["svio"]["Databricks Apps"] = "maybe"
    bad["request_form"]["teams"].remove("Other")
    found = "\n".join(config.problems(bad))
    for text in ("status_chip", "flag must be one of", "https://", "isn't a tool id", "use yes or planned",
                 "keep Other"):
        assert text in found, text
