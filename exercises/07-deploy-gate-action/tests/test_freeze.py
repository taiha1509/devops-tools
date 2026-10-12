"""Contract for the freeze gate, including the boundary minute in two timezones.

The bash gate this replaces was `date +%u` compared to `5`, copy-pasted into nine
repositories and already wrong in three of them because it used runner-local
time. Every test in this file would have caught that.
"""

from __future__ import annotations

from datetime import time

import pytest
from pydantic import ValidationError

from deploy_gate.freeze import evaluate_freeze, in_recurring_window
from deploy_gate.models import RecurringWindow, Weekday
from helpers import BERLIN, FRIDAY, HANOI, SATURDAY, UTC_TZ, at


class TestBoundaryMinute:
    """Boundaries need a decision, not a coin flip. These pin the decision."""

    def test_one_minute_before_the_window_is_allowed(self, friday_afternoon_freeze):
        window = friday_afternoon_freeze.recurring[0]
        assert in_recurring_window(window, at(*FRIDAY, 13, 59)) is False

    def test_the_exact_start_minute_is_frozen(self, friday_afternoon_freeze):
        """Inclusive start. 14:00:00 is inside the freeze."""
        window = friday_afternoon_freeze.recurring[0]
        assert in_recurring_window(window, at(*FRIDAY, 14, 0)) is True

    def test_the_exact_end_minute_is_frozen(self, friday_afternoon_freeze):
        """Inclusive end. 23:59:00 is inside the freeze."""
        window = friday_afternoon_freeze.recurring[0]
        assert in_recurring_window(window, at(*FRIDAY, 23, 59)) is True

    def test_midnight_after_the_window_is_allowed(self, friday_afternoon_freeze):
        window = friday_afternoon_freeze.recurring[0]
        assert in_recurring_window(window, at(*SATURDAY, 0, 0)) is False


class TestTimezones:
    """The actual bug. Same config, same instant, and the weekday disagrees."""

    def test_a_utc_window_is_not_frozen_at_the_same_local_hour_elsewhere(
        self, friday_afternoon_freeze
    ):
        """15:00 in Hanoi on Friday is 08:00 UTC on Friday - before the window.

        An implementation that compares the local wall clock without converting
        freezes here, which is wrong: the window says UTC.
        """
        window = friday_afternoon_freeze.recurring[0]
        assert in_recurring_window(window, at(*FRIDAY, 15, 0, tz=HANOI)) is False

    def test_a_hanoi_window_freezes_at_hanoi_time(self, hanoi_freeze):
        window = hanoi_freeze.recurring[0]
        assert in_recurring_window(window, at(*FRIDAY, 15, 0, tz=HANOI)) is True

    def test_saturday_morning_in_hanoi_is_still_friday_in_utc(self, friday_afternoon_freeze):
        """Saturday 03:00 UTC+7 is Friday 20:00 UTC - **inside** a UTC Friday freeze.

        This is the test that fails for anyone who read the weekday off the local
        clock. It is also the exact scenario that makes a Vietnam-based engineer
        the person most likely to find this bug.
        """
        window = friday_afternoon_freeze.recurring[0]
        assert in_recurring_window(window, at(*SATURDAY, 3, 0, tz=HANOI)) is True

    def test_a_dst_timezone_window_holds_across_the_transition(self):
        """Berlin is UTC+2 in summer and UTC+1 in winter.

        "Friday 14:00 Berlin time" is a different UTC instant in March than in
        November, and `ZoneInfo` handles that only if you convert rather than
        offsetting by a fixed amount. Pick two Fridays either side of the
        transition and assert both.
        """
        raise AssertionError(f"implement: two Fridays either side of {BERLIN}'s DST change")


class TestOneOffWindows:
    def test_inside_the_year_end_freeze(self, year_end_freeze):
        result = evaluate_freeze(
            year_end_freeze, environment="production", now=at(2026, 12, 25, 10)
        )
        assert result.allowed is False

    def test_the_day_after_it_ends(self, year_end_freeze):
        result = evaluate_freeze(year_end_freeze, environment="production", now=at(2027, 1, 3, 10))
        assert result.allowed is True


class TestExemptions:
    def test_an_exempt_environment_deploys_during_a_freeze(self, friday_afternoon_freeze):
        """A freeze that blocks preview environments teaches people to use the
        override, and an override used daily is not an override."""
        config = friday_afternoon_freeze.model_copy(update={"exempt_environments": ("preview",)})
        result = evaluate_freeze(config, environment="preview", now=at(*FRIDAY, 16, 0))
        assert result.allowed is True
        assert "exempt" in result.reason.lower()


class TestReasonQuality:
    def test_a_block_names_the_window_and_when_it_ends(self, friday_afternoon_freeze):
        """ "Blocked by change freeze" starts a conversation. The window's name and
        end time ends one. The reason string is the product here."""
        result = evaluate_freeze(
            friday_afternoon_freeze, environment="production", now=at(*FRIDAY, 16, 0)
        )
        assert result.allowed is False
        assert "Friday afternoon freeze" in result.reason


def test_a_window_without_a_timezone_is_rejected():
    """No default. There is no sensible default timezone for a company-wide freeze,
    and silently choosing UTC reproduces the original bug more quietly.

    `RecurringWindow.timezone` has no default, so pydantic enforces this for free -
    the test exists to stop someone "helpfully" adding `= "UTC"` later.
    """
    with pytest.raises(ValidationError):
        RecurringWindow(days=(Weekday.FRIDAY,), start=time(14, 0), end=time(23, 59))


def test_config_loading_rejects_a_naive_one_off_datetime(tmp_path):
    """`start: "2026-12-20T00:00:00"` with no offset must fail loudly at load time,
    not silently become UTC at comparison time."""
    raise AssertionError(
        f"implement: write a naive-datetime YAML to {tmp_path} and assert load raises"
    )


def test_utc_is_still_spelled_explicitly(friday_afternoon_freeze):
    """Sanity check on the fixtures themselves: even the UTC window declares it."""
    assert friday_afternoon_freeze.recurring[0].timezone == UTC_TZ
