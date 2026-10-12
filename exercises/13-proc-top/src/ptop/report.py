"""Orchestration: read, parse, compute, return. The impure glue.

YOUR JOB: implement `snapshot`, `sample_cpu`, and `describe_process`.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from datetime import datetime

    from ptop.models import Process, SystemInfo
    from ptop.source import ProcSource


@dataclass(frozen=True, slots=True)
class Snapshot:
    """One pass over `/proc`, plus an honest account of what was skipped.

    `vanished` and `inaccessible` are separate on purpose. They explain the two
    different reasons your row count differs from `ps`, and "my tool shows 41,
    `ps` shows 43, and here is why" is the sentence this exercise is for.
    """

    processes: list[Process] = field(default_factory=list)
    system: SystemInfo | None = None
    vanished: int = 0
    inaccessible: int = 0


def snapshot(
    source: ProcSource,
    *,
    now: datetime,
    clock_ticks: int,
    uid_names: dict[int, str] | None = None,
) -> Snapshot:
    """One pass over every PID.

    Per process: read `stat`, `status` and `cmdline`; parse; resolve units.
    `cpu_percent` stays **None** - a single pass cannot produce an interval
    percentage, and filling it with a lifetime average under a column called
    "CPU%" is the confusion this whole exercise exists to clear up.

    Catch `FileNotFoundError` / `ProcessLookupError` **per process** and count
    them in `vanished`. Catch `PermissionError` separately into `inaccessible`.
    Wrapping the whole loop instead means one dying process truncates the output
    at that point, which looks like a quiet machine.

    `uid_names` maps UID to username. Passed in rather than read from `pwd`
    because `/etc/passwd` is not in `/proc`, so a fixture tree cannot provide it -
    and because inside a container the names differ from the host's anyway. Fall
    back to the numeric UID as a string, which is what `ps` does.
    """
    raise NotImplementedError


def sample_cpu(
    source: ProcSource,
    *,
    interval_seconds: float,
    cores: int = 1,
) -> list[Process]:
    """Two passes separated by `interval_seconds`, with CPU% computed.

    The sequence that matters:

        1. read `/proc/stat` total, then every process's ticks
        2. sleep
        3. read `/proc/stat` total, then every process's ticks again
        4. for each pid present in **both**, compute the percentage

    Read the system total **adjacent to** the process reads in each pass, not
    once at the start. The gap between them is error in every percentage, and on
    a loaded box reading a thousand `/proc/[pid]/stat` files is not instant.

    A pid in only the second pass is new: report it with `cpu_percent=None`
    rather than 0.0. "Started during the interval" and "used no CPU" are
    different facts, and 0.0 claims the second.
    """
    raise NotImplementedError


def describe_process(
    source: ProcSource,
    pid: int,
    *,
    now: datetime,
    clock_ticks: int,
) -> Process:
    """Everything about one process, for `ptop show <pid>`.

    Raises:
        ProcessLookupError: no such process. Let it propagate - here the user
            named a specific pid, so its absence is the answer rather than
            something to skip over.
    """
    raise NotImplementedError


__all__ = ["Snapshot", "describe_process", "sample_cpu", "snapshot"]
