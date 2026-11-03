"""Savings calculator maths (core/calc.py), checked against the prototype's calc()."""
import pytest

from core import calc


def test_prototype_defaults():
    # 6 hours a week x 3 people x 48 weeks = 864 hours; 70% of that is 604.8, which rounds to 605.
    e = calc.estimate(6, 3, 48, 70)
    assert e.hours_today == 864
    assert e.hours_saved == 605
    assert e.hours_after == 259
    assert e.working_weeks == 16.1   # 605 / 37.5 = 16.13
    assert e.ftes == 0.3             # 605 / 1,800 = 0.336


def test_rounds_half_up_like_math_round():
    # 0.5 x 1 x 10 = 5 hours; half of that is 2.5, which Math.round makes 3 (Python's round() would give 2).
    e = calc.estimate(0.5, 1, 10, 50)
    assert (e.hours_today, e.hours_saved, e.hours_after) == (5, 3, 2)


def test_decimal_hours_do_not_drift():
    # In floats, 7.5 x 2 x 52 x 0.95 is 740.9999...; the answer is exactly 741.
    assert calc.estimate(7.5, 2, 52, 95).hours_saved == 741


def test_working_weeks_and_ftes():
    e = calc.estimate(37.5, 1, 48, 100)
    assert e.hours_saved == 1800
    assert e.working_weeks == 48.0
    assert e.ftes == 1.0


def test_inputs_are_clamped():
    assert calc.estimate(10, 1, 60, 50).hours_today == 520          # weeks capped at 52
    assert calc.estimate(-5, 3, 48, 70).hours_today == 0            # negative hours count as 0
    assert calc.estimate(5, -2, 48, 70).hours_today == 0            # negative people count as 0
    assert calc.estimate(10, 1, 10, 150).hours_saved == 100         # share capped at 100%
    assert calc.estimate(None, None, None, None).hours_today == 0   # empty inputs count as 0


def test_zero_hours_gives_empty_bars():
    e = calc.estimate(0, 3, 48, 70)
    assert (e.hours_today, e.hours_saved, e.hours_after) == (0, 0, 0)
    assert e.after_share == 0.0


def test_after_share_is_the_with_a_tool_bar():
    assert calc.estimate(10, 1, 10, 70).after_share == pytest.approx(0.3)


def test_defaults_match_the_brief():
    assert calc.WEEKS_DEFAULT == 48
    assert (calc.SHARE_MIN, calc.SHARE_MAX, calc.SHARE_DEFAULT) == (20, 95, 70)
    assert calc.HOURS_PER_WORKING_WEEK == 37.5 and calc.HOURS_PER_FTE_YEAR == 1800


@pytest.mark.parametrize("value, shown", [(1008, "1,008"), (16.1, "16.1"), (2.0, "2"), (0, "0"), (0.3, "0.3"),
                                          (1234567, "1,234,567")])
def test_fmt(value, shown):
    assert calc.fmt(value) == shown


def test_summary_line_follows_error_level():
    e = calc.estimate(6, 3, 48, 70)
    assert calc.summary_line(e, "Rarely goes wrong") == "Out of 864 hours spent on it today."
    assert calc.summary_line(e, "Sometimes goes wrong").endswith("catch the errors that slip through today.")
    assert calc.summary_line(e, "Often goes wrong").endswith("catch errors people miss.")


def test_estimate_chip():
    assert calc.estimate_chip(1008) == "Estimated 1,008 hours a year could be saved"
