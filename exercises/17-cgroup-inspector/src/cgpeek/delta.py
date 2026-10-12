"""Deltas between two samples. Pure - same idea as E13's CPU percentage.

A rate is a property of two observations. One `cpu.stat` read gives you
cumulative counters since the cgroup was created, which is an average over its
whole lifetime and tells you nothing about now.

YOUR JOB: implement `throttle_rate` and `cpu_usage_cores`.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from cgpeek.models import CpuStat


def throttle_rate(first: CpuStat, second: CpuStat) -> float:
    """Fraction of periods throttled **between two samples**, 0.0-1.0.

        (second.nr_throttled - first.nr_throttled)
        ------------------------------------------
        (second.nr_periods - first.nr_periods)

    Why the delta rather than the absolute ratio: a container that was badly
    throttled at startup and is fine now shows a high lifetime ratio forever.
    During an incident you need "is it throttled **right now**", and that is only
    answerable with two samples - which is exactly E13's lesson about `ps` versus
    `top`, in a different file.

    Edge cases, both of which occur:

        * **Zero period delta.** The samples were too close together, or the cpu
          controller is not enabled so `nr_periods` never moves. Return 0.0; do
          not divide by zero.
        * **Negative deltas.** The cgroup was recreated between samples - same
          path, new counters starting at zero. Return 0.0 rather than a negative
          rate.
    """
    raise NotImplementedError


def cpu_usage_cores(first: CpuStat, second: CpuStat, *, elapsed_seconds: float) -> float:
    """Cores actually used between two samples.

    `usage_usec` delta divided by elapsed wall time, both in microseconds. So 0.5
    means half a core.

    Report this **next to the quota**, because the pair is the diagnosis the
    problem statement needs: "0.2 cores used against a 0.5-core limit, and
    throttled in 38% of periods" is contradictory-looking and completely normal.

    The resolution: the app burns its whole 50ms allowance in the first 10ms of
    each 100ms period, then sits frozen for 90ms. Average usage is low *because*
    it is throttled. Either number alone misleads - which is why `docker stats`
    showing low CPU on a throttled container sends people looking in the wrong
    place entirely.
    """
    raise NotImplementedError


__all__ = ["cpu_usage_cores", "throttle_rate"]
