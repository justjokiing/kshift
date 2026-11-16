"""Oracle tests for the daily schedule selector.

``_select_current_theme`` is the decision every catch-up run makes. The
fixture-based tests in ``test_theme_recovery.py`` cover the reported cases;
these tests compare the selector against an independent computation over
randomized schedules, so the minute and rollover logic cannot regress silently
for a combination nobody wrote a fixture for.
"""
import random
from datetime import datetime, timedelta
from types import SimpleNamespace

import pytest

HOURS = (0, 1, 6, 8, 12, 18, 20, 23)
MINUTES = (0, 5, 30, 59)


def _conf(times):
    """A theme config whose ``time`` entries are datetimes, like Config."""
    return SimpleNamespace(
        time=[datetime(2000, 1, 1, hour, minute) for hour, minute in times])


def _latest_occurrence(times, now):
    """The latest daily occurrence at or before ``now``.

    Computed independently of the selector: only the wall-clock minute
    matters, and an occurrence may come from today or yesterday.
    """
    now_minute = now.replace(second=0, microsecond=0)
    latest = None
    for hour, minute in times:
        for days_back in (0, 1):
            event = (now_minute - timedelta(days=days_back)).replace(
                hour=hour, minute=minute)
            if event <= now_minute and (latest is None or event > latest):
                latest = event
    return latest


@pytest.mark.parametrize("seed", range(50))
def test_selector_matches_the_latest_occurrence(main_module, seed):
    rng = random.Random(seed)
    themes = {}
    for index in range(rng.randint(1, 4)):
        count = rng.randint(0, 3)
        themes[f"theme{index}"] = _conf([
            (rng.choice(HOURS), rng.choice(MINUTES)) for _ in range(count)
        ])
    now = datetime(2026, 11, 5, rng.choice(HOURS), rng.choice(MINUTES),
                   rng.randint(0, 59))

    selected = main_module._select_current_theme(themes, now)

    latest = {
        name: _latest_occurrence([(t.hour, t.minute) for t in conf.time], now)
        for name, conf in themes.items()
    }
    occurrences = [when for when in latest.values() if when is not None]
    if not occurrences:
        assert selected is None
        return

    assert selected is not None
    assert latest[selected] == max(occurrences)


def test_selector_ignores_future_only_schedules(main_module):
    themes = {"future": _conf([(23, 59)]), "past": _conf([(0, 0)])}

    assert main_module._select_current_theme(themes,
                                             datetime(2026, 11, 5, 12,
                                                      0)) == "past"


def test_selector_is_independent_of_config_order(main_module):
    now = datetime(2026, 11, 5, 12, 0)

    first = main_module._select_current_theme(
        {
            "alpha": _conf([(8, 0)]),
            "beta": _conf([(8, 0)])
        }, now)
    second = main_module._select_current_theme(
        {
            "beta": _conf([(8, 0)]),
            "alpha": _conf([(8, 0)])
        }, now)

    assert first == second


def test_logged_activation_wins_a_same_minute_tie(main_module):
    themes = {"scheduled": _conf([(8, 0)]), "logged": _conf([])}

    selected = main_module._select_current_theme(
        themes,
        datetime(2026, 11, 5, 9, 0),
        last_log_theme=("logged", datetime(2026, 11, 5, 8, 0)))

    assert selected == "logged"


def test_stale_log_does_not_override_a_later_schedule(main_module):
    themes = {"day": _conf([(8, 0)]), "night": _conf([(20, 0)])}

    selected = main_module._select_current_theme(
        themes,
        datetime(2026, 11, 5, 21, 0),
        last_log_theme=("day", datetime(2026, 11, 5, 8, 0)))

    assert selected == "night"


@pytest.mark.parametrize(("times", "expected"), [
    ([], True),
    ([datetime(2000, 1, 1, 8, 0)], True),
    (["Mon..Fri *-*-* 08:00:00"], False),
    ([datetime(2000, 1, 1, 8, 0), "Mon..Fri *-*-* 08:00:00"], False),
])
def test_daily_schedules_policy(main_module, times, expected):
    assert main_module._daily_schedules({"day": SimpleNamespace(time=times)
                                         }) is expected


def test_daily_schedules_ignores_themes_without_a_time(main_module):
    themes = {"disabled": _conf([]), "daily": _conf([(8, 0)])}

    assert main_module._daily_schedules(themes) is True
    assert main_module._daily_schedules({}) is True
