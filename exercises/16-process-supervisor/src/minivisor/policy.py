"""Restart policy and backoff. Pure - no sleeping, no processes.

The loop that sleeps and spawns lives in `supervisor.py`. Keeping the decision
here means you can test "should this restart?" as a table, with no subprocesses
and no waiting.

YOUR JOB: implement `should_restart` and `backoff`.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from minivisor.models import ExitInfo, RestartPolicy

MAX_BACKOFF_SECONDS = 30.0
"""Cap on the exponential backoff.

Uncapped doubling reaches an hour by restart 12, at which point a process that
would have recovered is simply down. The cap is what makes `restart: always`
mean "keep trying" rather than "try for a while and then effectively give up".
"""


def should_restart(
    policy: RestartPolicy,
    exit_info: ExitInfo,
    restarts_so_far: int,
    *,
    max_restarts: int | None = None,
    shutting_down: bool = False,
) -> bool:
    """Should this process be restarted?

    The rules, in order:

        1. **`shutting_down` wins over everything.** Once SIGTERM has arrived, no
           process is restarted, including `restart: always` ones. Without this,
           a supervisor with an `always` process can never shut down - it keeps
           respawning the children it is trying to stop, and `docker stop`
           reaches its timeout every time.
        2. `max_restarts` reached -> False, and the caller should log loudly.
           Silently giving up is worse than crashing: the container stays
           "healthy" with nothing running inside it.
        3. `NEVER` -> False.
        4. `ALWAYS` -> True, even on a clean exit 0.
        5. `ON_FAILURE` -> True only when the exit was not a success.

    The interesting question in rule 5: **is a SIGTERM death a failure?** If the
    supervisor sent it, no. If something else did, the process was killed and
    `on-failure` should restart it. `ExitInfo.succeeded` says no-it-is-not-a-
    success, and rule 1 covers the case where we are the ones shutting down -
    which is why these two rules are enough. Say so in `DECISIONS.md` because a
    reviewer will ask.
    """
    raise NotImplementedError


def backoff(restarts_so_far: int, *, cap: float = MAX_BACKOFF_SECONDS) -> float:
    """Seconds to wait before the next restart. Exponential, capped.

    `2 ** restarts_so_far`, capped at `cap`. So 1, 2, 4, 8, 16, 30, 30, ...

    `restarts_so_far == 0` must return a **small** value, not zero: a process
    that fails instantly in a zero-backoff `always` loop is a busy-wait that
    pins a core and floods the logs. 1 second is fine.

    Consider jitter if you run many replicas - without it, every replica of a
    service that lost its database retries in lockstep and hammers it the moment
    it comes back. Not required here; worth a line in `DECISIONS.md`.
    """
    raise NotImplementedError


__all__ = ["MAX_BACKOFF_SECONDS", "backoff", "should_restart"]
