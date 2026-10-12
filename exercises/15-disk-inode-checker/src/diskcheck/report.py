"""Orchestration: mounts + stats -> usages, ready for `evaluate`.

YOUR JOB: implement `collect_usage`.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from diskcheck.models import MountUsage
    from diskcheck.sources import ProcSource, StatSource


def collect_usage(
    proc: ProcSource,
    stats: StatSource,
    *,
    include_tmpfs: bool = False,
) -> tuple[list[MountUsage], list[str]]:
    """Read mountinfo, filter, and stat each surviving mount.

    Returns `(usages, skipped_mount_points)`. The second value is not decoration:
    a mount you could not stat is a mount you are **not monitoring**, and on the
    day it fills up, "it was in the skipped list all along" is the answer nobody
    wants to discover afterwards.

    Catch `PermissionError` and `OSError` per mount, never around the loop - one
    unreadable `/run/user/1000` must not cost you `/var`.
    """
    raise NotImplementedError


__all__ = ["collect_usage"]
