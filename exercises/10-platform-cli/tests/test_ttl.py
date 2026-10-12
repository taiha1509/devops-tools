"""Contract for TTL parsing and expiry selection.

E01's `select_for_deletion` in a new costume. If these tests feel familiar, that
is the point - reuse the thinking rather than rediscovering it.
"""

from __future__ import annotations

from datetime import timedelta

import pytest

from plat.ttl import MAX_TTL_HOURS, parse_ttl, select_expired


class TestParseTtl:
    @pytest.mark.parametrize(
        ("given", "expected"),
        [
            ("90s", timedelta(seconds=90)),
            ("30m", timedelta(minutes=30)),
            ("48h", timedelta(hours=48)),
            ("7d", timedelta(days=7)),
        ],
    )
    def test_valid_units(self, given, expected):
        assert parse_ttl(given) == expected

    @pytest.mark.parametrize("given", [None, "", "none", "never"])
    def test_no_ttl_spellings(self, given):
        """Someone will type `none`. An opaque parse error for an obvious intent
        is bad UX, and this costs one line to support."""
        assert parse_ttl(given) is None

    def test_a_bare_number_is_rejected(self):
        """48 seconds and 48 hours are both plausible readings, and the cost of
        guessing wrong is asymmetric. Refuse and show the accepted forms."""
        with pytest.raises(ValueError, match="48h"):
            parse_ttl("48")

    @pytest.mark.parametrize("given", ["0h", "-1h"])
    def test_zero_and_negative_are_rejected(self, given):
        with pytest.raises(ValueError):
            parse_ttl(given)

    def test_over_the_cap_is_rejected(self):
        """`--ttl 8760h` is a permanent environment with extra steps, created by
        someone who only needed a week but did not want to think about it."""
        with pytest.raises(ValueError):
            parse_ttl(f"{MAX_TTL_HOURS + 1}h")

    def test_an_unknown_unit_is_rejected(self):
        with pytest.raises(ValueError):
            parse_ttl("48w")


class TestSelectExpired:
    def test_an_expired_environment_is_selected(self, make_env, now):
        stale = make_env("old", hours_old=72, ttl_hours=48)
        assert select_expired([stale], now=now) == [stale]

    def test_a_live_environment_is_not(self, make_env, now):
        fresh = make_env("fresh", hours_old=1, ttl_hours=48)
        assert select_expired([fresh], now=now) == []

    def test_no_ttl_means_never_expires(self, make_env, now):
        """**Not** "expires immediately".

        Getting this backwards deletes every long-lived environment on first run,
        which is the worst bug available in this exercise - and an easy one to
        write, because `if env.ttl < elapsed` on a `None` is a `TypeError` and
        the obvious fix is to treat `None` as zero.
        """
        forever = make_env("forever", hours_old=10_000, ttl_hours=None)
        assert select_expired([forever], now=now) == []

    def test_the_boundary_is_decided(self, make_env, now):
        """Exactly at expiry. E01 chose "exactly max_age is kept" - match it
        unless you have a reason, and write the reason down."""
        exact = make_env("exact", hours_old=48, ttl_hours=48)
        assert select_expired([exact], now=now) == []

    def test_protection_is_absolute(self, make_env, now):
        """The `DoNotReap` tag again, and it exists for the same reason: someone
        is mid-incident and needs a thing to stay alive."""
        protected = make_env("keep-me", hours_old=10_000, ttl_hours=1)
        assert select_expired([protected], now=now, protected_names=["keep-me"]) == []

    def test_order_is_deterministic_and_oldest_first(self, make_env, now):
        a = make_env("a", hours_old=100, ttl_hours=1)
        b = make_env("b", hours_old=200, ttl_hours=1)
        assert select_expired([a, b], now=now) == [b, a]

    def test_the_plan_does_not_depend_on_whether_you_act_on_it(self, make_env, now):
        """E01's invariant. Calling this twice gives the same answer; the caller
        decides whether to destroy anything."""
        stale = make_env("old", hours_old=72, ttl_hours=48)
        assert select_expired([stale], now=now) == select_expired([stale], now=now)
