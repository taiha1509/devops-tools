"""The supervision loop: start, watch, reap, restart, stop.

YOUR JOB: implement `Supervisor`.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from minivisor.models import ExitInfo, ProcessState, SupervisorConfig
    from minivisor.signals import ShutdownFlag


class Supervisor:
    """Runs every process in the config until told to stop."""

    def __init__(self, config: SupervisorConfig, flag: ShutdownFlag) -> None:
        self._config = config
        self._flag = flag

    def start(self, name: str) -> int:
        """Spawn one process. Returns its pid.

        `subprocess.Popen` with a **list**, never `shell=True`. Then, once it
        works, read how `Popen` is implemented - `fork` + `exec`, or
        `posix_spawn` on platforms that support it - and write one paragraph in
        `DECISIONS.md`. You do not need to call `os.fork` yourself; you need to
        know what `Popen` is doing for you, because that is the question an
        interviewer asks.

        Log a structured `process.started` event with the name and pid.
        """
        raise NotImplementedError

    def reap(self) -> list[tuple[str, ExitInfo]]:
        """Collect everything that has exited since last call. Non-blocking.

        **Two mechanisms, and you need to understand both:**

            `Popen.poll()` per child - simple, and it only sees children you
            spawned. Fine when you are not PID 1.

            `os.waitpid(-1, os.WNOHANG)` in a loop - sees **any** child,
            including **grandchildren reparented to you** when you are PID 1 and
            their real parent died. `Popen.poll()` cannot see those at all, and
            they are exactly the `<defunct>` processes in the problem statement.

        A child that exits and is never waited for becomes a **zombie** - `Z` in
        E13's `ptop`. It holds a slot in the process table forever; enough of
        them exhaust the table and nothing on the box can fork.

        So: `waitpid` for the general case, and map unknown pids (grandchildren)
        to no managed name - reap them and move on. Which you chose and why goes
        in `DECISIONS.md`; this is the single most interview-relevant decision in
        the exercise.
        """
        raise NotImplementedError

    def run(self) -> int:
        """Start everything and supervise until shutdown. Returns the exit code.

        The loop:

            1. start every process
            2. until `flag.requested`:
                 a. `reap()`
                 b. for each exit, consult `policy.should_restart`; if yes, wait
                    `policy.backoff` and restart; if no, record and leave it down
                 c. short sleep - **not a busy-wait**. 100ms is responsive and
                    costs nothing
            3. `stop_all()`

        Exit `0` when every child exited cleanly, non-zero otherwise. Pick the
        convention - last non-zero, or a count of failures - and document it.
        """
        raise NotImplementedError

    def stop_all(self) -> int:
        """Graceful shutdown. The sequence is the exercise.

            1. **Stop restarting.** Anything respawned now will have to be killed
               again, and with `restart: always` you never finish.
            2. `SIGTERM` **every** child. Forwarding matters: the children did
               not get the signal the supervisor got - the kernel sent it to the
               supervisor alone, and a child that is never told is a child that
               never drains. This is the "workers never flush their buffers" half
               of the problem statement.
            3. Wait up to `stop_timeout_seconds`, reaping as they go.
            4. `SIGKILL` the survivors. A child that ignores SIGTERM must still
               die, or `docker stop` hits its own timeout and kills you both.
            5. Reap everything. Exiting with unreaped children is how a PID 1
               leaves zombies behind.

        Note the timeout relationship, which bites in production: your
        `stop_timeout_seconds` must be **less** than Docker's 10s (or the pod's
        `terminationGracePeriodSeconds`). If yours is longer, the runtime kills
        you before your own escalation runs, and your careful shutdown never
        happens.

        Log `process.exited` per child with the decoded code and signal name, and
        one `supervisor.stopped` summary.
        """
        raise NotImplementedError

    def states(self) -> list[ProcessState]:
        """Current state of every managed process, for tests and logging."""
        raise NotImplementedError


__all__ = ["Supervisor"]
