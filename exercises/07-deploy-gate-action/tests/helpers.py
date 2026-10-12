"""Shared constants and builders for the gate tests.

Separate from `conftest.py` because these are values tests import, not fixtures
pytest injects. (No `__init__.py` in `tests/` - pytest puts this directory on
`sys.path`, so `from helpers import ...` works.)
"""

from __future__ import annotations

from datetime import datetime
from zoneinfo import ZoneInfo

# Three timezones, used throughout. Every freeze test runs in at least two,
# because the bug being fixed is a timezone bug - a suite that only tested UTC
# would not have caught the bash gate this replaces either.
UTC_TZ = "UTC"
HANOI = "Asia/Ho_Chi_Minh"  # UTC+7, no DST - the user's own timezone
BERLIN = "Europe/Berlin"  # UTC+1/+2 - has DST, which is where it gets interesting

# 2026-09-25 is a Friday. 2026-09-26 is a Saturday.
FRIDAY = (2026, 9, 25)
SATURDAY = (2026, 9, 26)


def at(
    year: int,
    month: int,
    day: int,
    hour: int,
    minute: int = 0,
    *,
    tz: str = UTC_TZ,
) -> datetime:
    """A tz-aware instant. There is deliberately no naive-datetime helper here."""
    return datetime(year, month, day, hour, minute, tzinfo=ZoneInfo(tz))


__all__ = ["BERLIN", "FRIDAY", "HANOI", "SATURDAY", "UTC_TZ", "at"]
