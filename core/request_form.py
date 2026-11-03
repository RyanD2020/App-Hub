"""Tool requests: validation, tidying, and the email and Teams links used when a request is sent by hand.

The requester's email always comes from the Databricks sign-in (core/identity.py), never from the form.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from urllib.parse import quote

from core.calc import fmt

TEAM_OTHER = "Other"
TEAM_NAME_MAX = 60
TITLE_MAX = 70

TASK_REQUIRED = "Describe the task so we know what to look at."
TEAM_NAME_REQUIRED = "Add your team's name so we know who to talk to."
TEAM_NAME_TOO_LONG = f"Keep your team's name to {TEAM_NAME_MAX} characters."


def tidy_team_name(name: str | None) -> str:
    """Trimmed, with runs of spaces, tabs or newlines collapsed to one space."""
    return " ".join((name or "").split())


@dataclass
class Draft:
    """What the request form holds."""
    task: str = ""
    team_category: str = ""
    team_name: str = ""
    frequency: str = ""
    tools_today: str = ""
    est_hours_year: int | None = None
    errors: dict[str, str] = field(default_factory=dict)

    @property
    def team(self) -> str:
        """The team as shown everywhere: the typed name for Other, otherwise the chosen team."""
        return self.team_name if self.team_category == TEAM_OTHER else self.team_category


def validate(task: str | None, team_category: str | None, team_name: str | None = "", frequency: str = "",
             tools_today: str = "", est_hours_year: int | None = None) -> Draft:
    """Clean the form values. Draft.errors maps a field ("task", "team_name") to the message shown under it."""
    d = Draft(
        task=(task or "").strip(),
        team_category=(team_category or "").strip(),
        frequency=(frequency or "").strip(),
        tools_today=(tools_today or "").strip(),
        est_hours_year=est_hours_year if est_hours_year and est_hours_year > 0 else None,
    )
    if not d.task:
        d.errors["task"] = TASK_REQUIRED
    if d.team_category == TEAM_OTHER:
        d.team_name = tidy_team_name(team_name)
        if not d.team_name:
            d.errors["team_name"] = TEAM_NAME_REQUIRED
        elif len(d.team_name) > TEAM_NAME_MAX:
            d.errors["team_name"] = TEAM_NAME_TOO_LONG
    else:
        d.team_name = d.team_category
    return d


def title_of(task: str) -> str:
    """First sentence or line of the task, cut at a word boundary to about 70 characters."""
    text = (task or "").strip()
    first = text.replace("\n", ".").split(".")[0].strip() or text
    if len(first) <= TITLE_MAX:
        return first
    cut = first.rfind(" ", 0, TITLE_MAX - 1)
    return (first[:cut] if cut > 0 else first[:TITLE_MAX - 3]) + "..."


def contact_body(task: str, team: str, frequency: str, tools_today: str) -> str:
    """Body for a contact's Email button: whatever the form holds so far (prototype requestText())."""
    lines = ["Hi,", "", "I'd like to talk about a possible tool for my team."]
    if task.strip():
        lines += ["", "The task: " + task.strip()]
    lines += ["Team: " + (team or "Not given"), "How often: " + (frequency or "Not given")]
    if tools_today.strip():
        lines.append("What we use today: " + tools_today.strip())
    return "\n".join(lines)


def fallback_body(d: Draft, requester_email: str | None) -> str:
    """Body for "Email the team instead" when a request can't be saved: the full request, nothing left out."""
    lines = [
        "Hi,",
        "",
        "I tried to submit this request in the App hub, but it couldn't be saved.",
        "",
        "Task: " + d.task,
        "Team: " + (d.team or "Not given"),
        "How often: " + (d.frequency or "Not given"),
        "What we use today: " + (d.tools_today or "Not given"),
        "Estimate: " + (f"{fmt(d.est_hours_year)} hours a year" if d.est_hours_year else "Not given"),
    ]
    if requester_email:
        lines.append("Signed in as: " + requester_email)
    return "\n".join(lines)


def mailto(to: list[str] | str, subject: str, body: str) -> str:
    """A mailto link with the subject and body percent-encoded (spaces as %20, which every mail client reads)."""
    addresses = [to] if isinstance(to, str) else list(to)
    return (f"mailto:{','.join(quote(a, safe='@') for a in addresses)}"
            f"?subject={quote(subject, safe='')}&body={quote(body, safe='')}")


def teams_chat(address: str, message: str) -> str:
    return (f"https://teams.microsoft.com/l/chat/0/0?users={quote(address, safe='@')}"
            f"&message={quote(message, safe='')}")
