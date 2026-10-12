"""Core types. Given to you complete; everything else is a stub.

The modelling decision that carries this exercise: **`max` is `None`, not a magic
number.** `memory.max` contains either a byte count or the literal string `max`.
Representing "no limit" as `sys.maxsize`, or `-1`, or `2**63-1` means every
percentage calculation downstream has to remember to check for it, and one of
them will not - and then you report a container as using 0.0000001% of its memory
limit instead of saying it has none.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class MemoryStat:
    """`memory.stat`, the fields that answer the OOMKilled question.

    `anon` is roughly what the application thinks of as its heap. `file` is the
    **page cache** - and it counts toward the limit.

    That is the whole answer to "OOMKilled but the app says the heap is only
    300MB": the app is right about its heap and wrong about what the limit
    measures. A container that reads a lot of files accumulates page cache inside
    its own memory accounting, and the kernel will reclaim most of it under
    pressure but not all of it in time.
    """

    anon: int = 0
    file: int = 0
    kernel: int = 0
    slab: int = 0
    sock: int = 0


@dataclass(frozen=True, slots=True)
class MemoryState:
    """Memory limits and usage for one cgroup."""

    current: int
    # None means `max` - genuinely unlimited. See the module docstring.
    max_bytes: int | None
    high_bytes: int | None
    stat: MemoryStat
    oom_kills: int = 0
    oom_events: int = 0

    @property
    def percent(self) -> float | None:
        """None when there is no limit, because a percentage of unlimited is not
        0% - it is undefined, and printing 0% implies headroom that is not being
        measured."""
        if self.max_bytes is None or self.max_bytes == 0:
            return None
        return self.current / self.max_bytes * 100


@dataclass(frozen=True, slots=True)
class CpuStat:
    """`cpu.stat`. Two samples of this is what the throttle rate comes from."""

    usage_usec: int = 0
    user_usec: int = 0
    system_usec: int = 0
    nr_periods: int = 0
    nr_throttled: int = 0
    throttled_usec: int = 0


@dataclass(frozen=True, slots=True)
class CpuState:
    """CPU quota and throttling."""

    # `cpu.max` is "<quota> <period>" in microseconds, or "max <period>".
    quota_usec: int | None
    period_usec: int
    stat: CpuStat

    @property
    def cores(self) -> float | None:
        """The quota expressed as cores. None when unlimited.

        `50000 100000` is **0.5 cores** - which is exactly what Kubernetes'
        `limits.cpu: 500m` becomes. Being able to point at the file and say "that
        is what your 500m is" is the Senior-level version of this answer.
        """
        if self.quota_usec is None:
            return None
        return self.quota_usec / self.period_usec

    @property
    def throttled_fraction(self) -> float:
        """Share of periods in which the cgroup was throttled, 0.0-1.0.

        **This is the number that explains the latency.** A multi-threaded app
        with a 0.5-core quota can burn its whole 50ms allowance in the first 10ms
        of each 100ms period and then sit completely frozen for 90ms. Average
        utilisation looks like 40% of the limit; p99 is terrible; and nothing in
        the app's own metrics explains it.
        """
        if self.stat.nr_periods == 0:
            return 0.0
        return self.stat.nr_throttled / self.stat.nr_periods


@dataclass(frozen=True, slots=True)
class PidsState:
    current: int
    max_count: int | None  # None means `max`


@dataclass(frozen=True, slots=True)
class CgroupSnapshot:
    """Everything `cgpeek` reports for one cgroup at one instant."""

    path: str
    memory: MemoryState
    cpu: CpuState
    pids: PidsState
