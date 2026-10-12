"""TTL parsing and expiry selection. Pure.

This is E01's `select_for_deletion` in a new costume, and you should reuse the
thinking rather than rediscovering it: a reference `now` passed in, protection
rules that are absolute, and a plan that does not depend on whether you are
actually going to act on it.

YOUR JOB: implement `parse_ttl` and `select_expired`.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Iterable, Sequence
    from datetime import datetime, timedelta

    from plat.models import Environment

MAX_TTL_HOURS = 24 * 14
"""Two weeks. A cap, not a default.

Without a cap, `--ttl 8760h` is a permanent environment with extra steps -
and it will be created by someone who genuinely only needed a week but did not
want to think about it again.
"""


def parse_ttl(value: str | None) -> timedelta | None:
    """Parse `48h`, `30m`, `7d`, `90s` into a `timedelta`.

    `None` and `""` mean no TTL. `"none"` and `"never"` should too - someone will
    type them, and an opaque parse error for an obvious intent is bad UX.

    Reject, with a message that shows the accepted forms:

        * a bare number (`48`) - ambiguous, and the ambiguity is expensive:
          48 seconds and 48 hours are both plausible readings
        * zero or negative
        * anything over `MAX_TTL_HOURS`
        * unknown units (`48w`) - unless you add weeks, in which case say so

    Raises:
        ValueError: unparseable or out of range.
    """
    raise NotImplementedError


def select_expired(
    environments: Iterable[Environment],
    *,
    now: datetime,
    protected_names: Sequence[str] = (),
) -> list[Environment]:
    """Which environments the reaper should destroy. Oldest first.

    Deliberately the same shape as E01's `select_for_deletion`, including:

        * **Protection is absolute.** A protected name is never selected, no
          matter how long expired. This is the `DoNotReap` tag again, and it
          exists for the same reason: someone is mid-incident and needs a thing
          to stay alive.
        * **No TTL means never expires.** Not "expires immediately". Getting this
          backwards deletes every long-lived environment on first run, which is
          the single worst bug available in this exercise.
        * **Deterministic order.** Sort by `(expires_at, name)` so the same
          estate always produces the same plan.
        * Returns the plan. Whether anything is destroyed is the caller's
          decision, and `--dry-run` must produce an identical list.
    """
    raise NotImplementedError


__all__ = ["MAX_TTL_HOURS", "parse_ttl", "select_expired"]
