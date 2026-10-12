"""Threshold logic. Pure - this is E01's `policy.py` in a new costume.

Mount stats and thresholds in, findings out. No `statvfs`, no `/proc`, no clock.

YOUR JOB: implement `evaluate` and `exit_code_for`.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Sequence

    from diskcheck.models import Finding, MountUsage


@dataclass(frozen=True, slots=True)
class Thresholds:
    """Warn and crit levels, bytes and inodes separately. Given to you complete.

    Inodes get their own thresholds because the two budgets behave differently:
    byte usage creeps up, inode usage is usually flat and then suddenly is not -
    a cache directory starts writing a million small files and you go from 2% to
    100% inside an hour. A single shared threshold tuned for bytes is always
    wrong for inodes.
    """

    bytes_warn: float = 80.0
    bytes_crit: float = 90.0
    inodes_warn: float = 80.0
    inodes_crit: float = 90.0


@dataclass(frozen=True, slots=True)
class Problem:
    """One threshold crossing."""

    mount_point: str
    finding: Finding
    percent: float
    threshold: float
    detail: str = ""


def evaluate(
    usages: Sequence[MountUsage],
    thresholds: Thresholds,
) -> list[Problem]:
    """Check every mount against the thresholds.

    Rules:

        * Report bytes and inodes **independently**. A mount at 30% bytes and
          99% inodes has one problem, and it is the inode one - that is page #1,
          and a tool that only looks at bytes reports the box as healthy while
          writes are failing.
        * Only the **highest** severity per axis: a mount over crit produces one
          `*_CRIT`, not a crit and a warn. Two findings for one condition doubles
          every alert.
        * A mount with zero total blocks or zero inodes is **skipped**, not
          reported at 0% or 100%. That is a pseudo-filesystem that got past the
          filter, and `0/0` is where a division-by-zero crash lives.
        * Order deterministically by `(mount_point, finding)` so two runs over an
          unchanged box produce identical output.

    Mention the root reserve in `detail` when `f_bfree` and `f_bavail` differ
    materially. "95% used (5% reserved for root - the app user has 0 bytes
    available)" is page #3 solved in one line of output, and it is the single
    most useful sentence this tool can print.
    """
    raise NotImplementedError


def exit_code_for(problems: Sequence[Problem]) -> int:
    """0 all clear, 1 a crit threshold was crossed, 2 misuse.

    **A warn does not exit non-zero.** It is information for a human reading the
    output, not a page. Making warnings fail the check is how a monitoring
    integration ends up permanently red and therefore permanently ignored - and
    the brief's exit codes say 1 is specifically "a crit threshold was crossed".
    """
    raise NotImplementedError


__all__ = ["Problem", "Thresholds", "evaluate", "exit_code_for"]
