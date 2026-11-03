"""Request validation and the hand-off links (core/request_form.py)."""
from urllib.parse import parse_qs, unquote, urlsplit

import pytest

from core import request_form as rf


def test_task_is_required():
    assert rf.validate("", "Finance").errors == {"task": rf.TASK_REQUIRED}
    assert rf.validate("   \n ", "Finance").errors == {"task": rf.TASK_REQUIRED}
    assert rf.validate(None, "Finance").errors == {"task": rf.TASK_REQUIRED}


def test_valid_request_has_no_errors_and_is_trimmed():
    d = rf.validate("  Match invoices to contracts  ", "Finance", "", "Weekly", " Excel ", 605)
    assert d.errors == {}
    assert (d.task, d.team_category, d.team_name, d.team, d.tools_today, d.est_hours_year) == (
        "Match invoices to contracts", "Finance", "Finance", "Finance", "Excel", 605)


def test_team_name_required_when_other():
    assert rf.validate("A task", "Other", "").errors == {"team_name": rf.TEAM_NAME_REQUIRED}
    assert rf.validate("A task", "Other", "   ").errors == {"team_name": rf.TEAM_NAME_REQUIRED}
    assert rf.validate("A task", "Other", None).errors == {"team_name": rf.TEAM_NAME_REQUIRED}


def test_both_errors_at_once():
    assert set(rf.validate("", "Other", "").errors) == {"task", "team_name"}


def test_other_team_name_is_tidied_and_shown_as_the_team():
    d = rf.validate("A task", "Other", "  Retirement \t plan\n  services ")
    assert d.errors == {}
    assert d.team_category == "Other"
    assert d.team_name == "Retirement plan services"
    assert d.team == "Retirement plan services"


def test_team_name_ignored_unless_other():
    d = rf.validate("A task", "Sales", "Something typed earlier")
    assert d.team_name == "Sales" and d.team == "Sales"


def test_team_name_max_60_characters():
    assert rf.validate("A task", "Other", "x" * 60).errors == {}
    assert rf.validate("A task", "Other", "x" * 61).errors == {"team_name": rf.TEAM_NAME_TOO_LONG}
    # Spaces are collapsed before the length check.
    assert rf.validate("A task", "Other", "a" + " " * 100 + "b").errors == {}


def test_no_estimate_is_none():
    assert rf.validate("A task", "Finance", est_hours_year=0).est_hours_year is None
    assert rf.validate("A task", "Finance", est_hours_year=None).est_hours_year is None


@pytest.mark.parametrize("task, title", [
    ("Monthly client report assembly. The same slides every month.", "Monthly client report assembly"),
    ("First line\nsecond line", "First line"),
    ("word " * 30, ("word " * 13).strip() + "..."),
])
def test_title_of(task, title):
    assert rf.title_of(task) == title
    assert len(rf.title_of(task)) <= rf.TITLE_MAX


def test_mailto_encodes_subject_and_body():
    url = rf.mailto(["Muhammad_Adil@nylim.com", "ryan_e_doswell@newyorklife.com"], "App hub: tool request",
                    "Line one\nTask: R&D 100% done?")
    parts = urlsplit(url)
    assert parts.scheme == "mailto"
    assert parts.path == "Muhammad_Adil@nylim.com,ryan_e_doswell@newyorklife.com"
    assert "%20" in url and "+" not in url  # spaces as %20, which every mail client reads
    q = parse_qs(parts.query)
    assert q["subject"] == ["App hub: tool request"]
    assert q["body"] == ["Line one\nTask: R&D 100% done?"]


def test_teams_chat_link():
    url = rf.teams_chat("madil@newyorklife.com", "Hi, I have a question about the App hub.")
    assert url.startswith("https://teams.microsoft.com/l/chat/0/0?users=madil@newyorklife.com&message=")
    assert unquote(url.split("&message=")[1]) == "Hi, I have a question about the App hub."


def test_fallback_body_holds_the_whole_request():
    d = rf.validate("Match invoices", "Other", "Retirement plan services", "Daily", "Excel, SAP", 605)
    body = rf.fallback_body(d, "analyst@newyorklife.com")
    for text in ("Match invoices", "Retirement plan services", "Daily", "Excel, SAP", "605 hours a year",
                 "analyst@newyorklife.com"):
        assert text in body


def test_contact_body_uses_what_the_form_holds():
    body = rf.contact_body("Match invoices", "Finance", "Weekly", "")
    assert "The task: Match invoices" in body and "Team: Finance" in body and "How often: Weekly" in body
    assert "What we use today" not in body
