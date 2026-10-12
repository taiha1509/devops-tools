"""CPU percentage: the arithmetic, pure.

The one idea in this module, and the reason the exercise exists:

    **CPU% is a delta of (utime + stime) over an interval, divided by the
    system's total tick delta.**

One snapshot cannot produce it. That is why `top`'s first frame is garbage - it
has nothing to subtract from - and why `ps` shows a different number from `top`:
`ps` reports a lifetime average over the process's whole existence.

YOUR JOB: implement `cpu_percent` and `cpu_percent_lifetime`.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ptop.models import ProcSample


def cpu_percent(
    first: ProcSample,
    second: ProcSample,
    *,
    cores: int = 1,
) -> float:
    """Percentage CPU between two samples of the same process.

        (second.proc_ticks - first.proc_ticks)
        --------------------------------------  * 100 * cores
        (second.total_system_ticks - first.total_system_ticks)

    `cores` is the scaling decision, and it needs stating in `--help` because
    users will otherwise mis-read every number:

        cores=1  100% means one core fully used. **`top` and `htop` both default
                 to this**, which is why a 4-thread process shows 380%.
        cores=N  100% means the whole machine. Nothing shows this by default,
                 and a reader who assumes it will think a saturated box is idle.

    Match `top`, i.e. default to 1, so the live comparison in the acceptance
    criteria lines up.

    Edge cases, all of which occur:

        * **Zero system-tick delta.** Two samples taken in the same tick. Return
          0.0, do not divide by zero. A tight `--interval 0` loop hits this
          immediately.
        * **Negative process delta.** The PID was reused by a new process
          between samples, so its counters went backwards. Return 0.0 and treat
          it as a new process rather than reporting a nonsensical negative - and
          note that this is the one thing `top` genuinely cannot get right
          either.
        * The two samples must be the same `pid`. Raise `ValueError` if not; it
          is a programming error, not bad data.
    """
    raise NotImplementedError


def cpu_percent_lifetime(
    *,
    proc_ticks: int,
    process_age_seconds: float,
    clock_ticks: int,
) -> float:
    """What `ps` shows: average CPU over the process's entire life.

    `(proc_ticks / clock_ticks) / process_age_seconds * 100`

    Worth implementing even though `top` mode does not use it, because being able
    to produce **both** numbers and explain why they differ is precisely the
    interview answer this exercise is for. A process that burned a core for five
    minutes and has since been idle for a day shows ~0.3% here and 0% in `top`,
    and neither is wrong.

    Return 0.0 for a zero or negative age rather than dividing by zero - a
    process started in the current tick has an age of 0.
    """
    raise NotImplementedError


__all__ = ["cpu_percent", "cpu_percent_lifetime"]
