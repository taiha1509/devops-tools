"""The freeze-window gate. Pure: config and an instant in, a verdict out.

No clock, no network, no GitHub. `now` is a parameter, which is what lets you
test the boundary minute in two timezones without waiting for Friday.

YOUR JOB: implement `load_freeze_config`, `in_recurring_window`,
`in_one_off_window`, and `evaluate_freeze`.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from datetime import datetime
    from pathlib import Path

    from deploy_gate.models import FreezeConfig, GateResult, OneOffWindow, RecurringWindow


def load_freeze_config(path: Path) -> FreezeConfig:
    """Parse `.github/freeze.yaml`.

    Expected shape::

        recurring:
          - days: [friday]
            start: "14:00"
            end: "23:59"
            timezone: "UTC"
            label: "Friday afternoon freeze"
        one_off:
          - start: "2026-12-20T00:00:00+00:00"
            end: "2027-01-02T23:59:59+00:00"
            label: "End-of-year change freeze"
        exempt_environments: [preview, staging]

    **Reject a window with no timezone and reject naive one-off datetimes**, with
    a message that names the window. Defaulting to UTC here would be the same
    class of bug as the bash gate's runner-local time, just quieter - the config
    would look correct and behave wrongly for whoever wrote it in Hanoi.

    Raises:
        ValueError: unreadable, or any window that fails validation.
    """
    raise NotImplementedError


def in_recurring_window(window: RecurringWindow, now: datetime) -> bool:
    """Is `now` inside this recurring window?

    Convert `now` into the window's timezone **first**, then compare the weekday
    and the time. Converting in the other order, or comparing the weekday in UTC,
    is the bug this function exists to prevent: at 15:00 UTC+7 on Saturday it is
    still Friday 08:00 UTC, and the two answers differ.

    Boundaries, which need a decision rather than a coin flip:

        * `start` is **inclusive** - 14:00:00 is frozen
        * `end` is **inclusive** - 23:59:00 is frozen

    Both are tested at the exact minute. Pick these, document them in the
    `--help`, and if you prefer the other convention, change the tests
    deliberately rather than letting the implementation decide.

    A window where `end < start` (22:00 to 02:00) wraps past midnight. Decide
    whether you support that and say so - either is defensible, silently getting
    it wrong is not.
    """
    raise NotImplementedError


def in_one_off_window(window: OneOffWindow, now: datetime) -> bool:
    """Is `now` inside this one-off window? Both bounds inclusive."""
    raise NotImplementedError


def evaluate_freeze(config: FreezeConfig, *, environment: str, now: datetime) -> GateResult:
    """Combine every window into one verdict.

    Exempt environments short-circuit to allowed, with a reason that says so -
    "preview is exempt from the change freeze" rather than a bare pass, so the
    log explains itself when someone asks why their deploy went through.

    When blocked, `reason` must name **which** window matched and when it ends.
    "Blocked by change freeze" starts a conversation; "Blocked by 'Friday
    afternoon freeze' until 2026-09-25 23:59 UTC" ends one.
    """
    raise NotImplementedError


__all__ = [
    "evaluate_freeze",
    "in_one_off_window",
    "in_recurring_window",
    "load_freeze_config",
]
