"""Rendering the snapshot.

YOUR JOB: implement `render_snapshot` and `render_delta`.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from cgpeek.models import CgroupSnapshot


def render_snapshot(snapshot: CgroupSnapshot) -> str:
    """The output shape from the brief::

        cgroup   /system.slice/docker-3f2a…scope
        memory   312.4 MiB / 512.0 MiB (61%)   anon 290.1  file 18.3   oom_kill 2
        cpu      limit 0.50 cores (50000/100000)   throttled 38% of periods
        pids     41 / 4096

    Three decisions in that layout, each one deliberate:

        * **`anon` and `file` are shown next to the total.** That is the whole
          answer to "OOMKilled but the heap is only 300MB" - you can see that 18
          of the 312 MiB is page cache, counted against the limit. Hiding the
          split makes the number unexplainable.
        * **The raw `50000/100000` is printed alongside "0.50 cores".** The
          derived number is what a human wants; the raw pair is what they grep
          for when comparing against the YAML, and it is what makes the
          connection to `limits.cpu: 500m` concrete.
        * **`oom_kill` is shown even when zero.** An absent counter reads as "not
          measured"; `oom_kill 0` reads as "measured, and it has not happened" -
          which is exactly what someone debugging a restart loop needs to rule
          out.

    Render "no limit" explicitly rather than as a huge number or a blank. `memory
    unlimited (312.4 MiB used)` is informative; `memory 312.4 MiB / 8.0 EiB
    (0%)` is noise that hides whether a limit exists at all.
    """
    raise NotImplementedError


def render_delta(
    first: CgroupSnapshot,
    second: CgroupSnapshot,
    *,
    elapsed_seconds: float,
) -> str:
    """One `--watch` frame: the second snapshot plus the rates between them.

    Show the **throttle rate for the interval**, not the lifetime ratio - see
    `delta.throttle_rate` on why. Label it as an interval measurement so nobody
    compares it against a cumulative figure from elsewhere.

    Like `top`, the first frame has nothing to diff against. Say so rather than
    printing a zero that looks like a measurement: a throttle rate of 0% on the
    first frame of a badly throttled container is the one output that would make
    someone close the tool and look elsewhere.
    """
    raise NotImplementedError


__all__ = ["render_delta", "render_snapshot"]
