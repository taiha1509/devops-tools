"""Core data types. Given to you complete; everything else is a stub.

`ProcSample` is the model that makes the exercise's central point: a process's
CPU percentage is **not a property of a process**, it is a property of two
observations of a process. One snapshot can only give you a lifetime average -
which is what `ps` shows, and why `ps` and `top` disagree.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum


class ProcState(StrEnum):
    """The single-letter state from field 3 of `/proc/[pid]/stat`."""

    RUNNING = "R"
    SLEEPING = "S"
    DISK_SLEEP = "D"  # uninterruptible. A box full of these is an I/O problem.
    ZOMBIE = "Z"  # exited, not yet reaped. E16 is about why.
    STOPPED = "T"
    TRACING_STOP = "t"
    DEAD = "X"
    IDLE = "I"  # kernel idle thread


@dataclass(frozen=True, slots=True)
class ProcStat:
    """The fields of `/proc/[pid]/stat` this tool uses.

    `utime` and `stime` are in **clock ticks**, not seconds, and not
    milliseconds. Converting them needs `os.sysconf("SC_CLK_TCK")` - which is
    almost always 100, and hard-coding it is still wrong, because "almost always"
    is how you get a tool that is quietly 4x off on an unusual kernel.

    `starttime` is ticks **since boot**, so turning it into a wall-clock time
    needs `/proc/uptime` as well. Two files for one timestamp.
    """

    pid: int
    comm: str
    state: ProcState
    ppid: int
    utime: int
    stime: int
    starttime: int
    num_threads: int
    rss_pages: int

    @property
    def total_ticks(self) -> int:
        """User plus system time. The numerator of every CPU percentage."""
        return self.utime + self.stime


@dataclass(frozen=True, slots=True)
class Process:
    """One process as this tool reports it, units already resolved."""

    pid: int
    ppid: int
    state: ProcState
    user: str
    command: str
    rss_bytes: int
    started_at: datetime
    # None in `list` mode: a single snapshot cannot produce an interval
    # percentage, and reporting a lifetime average in a column labelled "CPU%"
    # is exactly the confusion this exercise exists to clear up.
    cpu_percent: float | None = None

    def sort_key_rss(self) -> tuple[int, int]:
        return (-self.rss_bytes, self.pid)


@dataclass(frozen=True, slots=True)
class ProcSample:
    """One observation of one process's CPU counters, with the system total.

    Both halves are needed. A process using 100 ticks tells you nothing until you
    know whether 200 or 20,000 ticks passed system-wide in the same interval.
    """

    pid: int
    proc_ticks: int
    total_system_ticks: int


@dataclass(frozen=True, slots=True)
class SystemInfo:
    """The `top` header line."""

    load_1: float
    load_5: float
    load_15: float
    mem_total_bytes: int
    mem_available_bytes: int
    uptime_seconds: float
    boot_time: datetime

    @property
    def mem_used_bytes(self) -> int:
        """`MemTotal - MemAvailable`, not `MemTotal - MemFree`.

        `MemFree` excludes the page cache, which Linux fills with reclaimable
        data by design - so a healthy box looks 95% full by that measure. Nearly
        every "we are out of memory" false alarm traces back to reading `MemFree`.
        `MemAvailable` is the kernel's own estimate of what a new allocation
        could actually get.
        """
        return self.mem_total_bytes - self.mem_available_bytes
