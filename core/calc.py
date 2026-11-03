"""Savings calculator maths, the same as the prototype's calc().

hours today = hours per week per person x people x weeks per year
hours saved = hours today x share a tool could take over, rounded to whole hours
working weeks back = hours saved / 37.5, and full-time people = hours saved / 1,800, both to one decimal

Rounding is half-up, as in JavaScript's Math.round, and uses Decimal so 0.7 x 864 is exactly 604.8.
"""
from __future__ import annotations

from dataclasses import dataclass
from decimal import ROUND_HALF_UP, Decimal

HOURS_PER_WORKING_WEEK = Decimal("37.5")
HOURS_PER_FTE_YEAR = Decimal("1800")

WEEKS_DEFAULT, WEEKS_MAX = 48, 52
SHARE_MIN, SHARE_MAX, SHARE_DEFAULT, SHARE_STEP = 20, 95, 70, 5
HOURS_DEFAULT, PEOPLE_DEFAULT = 6.0, 3

ERROR_LEVELS = ("Rarely goes wrong", "Sometimes goes wrong", "Often goes wrong")
ERROR_DEFAULT = "Sometimes goes wrong"
_ERROR_NOTES = {
    "Often goes wrong": " It often goes wrong today, so a tool would also catch errors people miss.",
    "Sometimes goes wrong": " A tool would also catch the errors that slip through today.",
}


@dataclass(frozen=True)
class Estimate:
    hours_today: int
    hours_saved: int
    hours_after: int
    working_weeks: float
    ftes: float

    @property
    def after_share(self) -> float:
        """Width of the "with a tool" bar, as a fraction of today's."""
        return self.hours_after / self.hours_today if self.hours_today else 0.0


def _d(x) -> Decimal:
    try:
        return Decimal(str(x if x is not None else 0))
    except Exception:
        return Decimal(0)


def _round(x: Decimal, places: int = 0) -> Decimal:
    return x.quantize(Decimal(1).scaleb(-places), rounding=ROUND_HALF_UP)


def estimate(hours_per_week, people, weeks_per_year=WEEKS_DEFAULT, share_pct=SHARE_DEFAULT) -> Estimate:
    """Hours a tool could give back each year. Negative inputs count as 0; weeks are capped at 52 and the
    share at 0 to 100%."""
    hours = max(_d(hours_per_week), Decimal(0))
    ppl = max(_d(people), Decimal(0))
    weeks = min(max(_d(weeks_per_year), Decimal(0)), Decimal(WEEKS_MAX))
    share = min(max(_d(share_pct), Decimal(0)), Decimal(100)) / 100

    today = hours * ppl * weeks
    saved = _round(today * share)
    after = _round(today - saved)
    return Estimate(
        hours_today=int(_round(today)),
        hours_saved=int(saved),
        hours_after=int(after),
        working_weeks=float(_round(saved / HOURS_PER_WORKING_WEEK, 1)),
        ftes=float(_round(saved / HOURS_PER_FTE_YEAR, 1)),
    )


def summary_line(e: Estimate, error_level: str) -> str:
    return f"Out of {fmt(e.hours_today)} hours spent on it today." + _ERROR_NOTES.get(error_level, "")


def estimate_chip(hours_saved: int) -> str:
    """The chip that travels with a request made from the calculator."""
    return f"Estimated {fmt(hours_saved)} hours a year could be saved"


def fmt(x) -> str:
    """1008 -> "1,008", 16.1 -> "16.1", 2.0 -> "2" (like toLocaleString in the prototype)."""
    d = _d(x)
    if d == d.to_integral_value():
        return f"{int(d):,}"
    return f"{float(d):,.1f}"
