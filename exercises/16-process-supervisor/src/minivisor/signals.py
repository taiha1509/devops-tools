"""Signal handling. The handler sets a flag; the main loop does the work.

**Do no work in a signal handler.** Python runs handlers between bytecodes, so
I/O or locking inside one is a re-entrancy bug waiting for load - and the symptom
is a deadlock during shutdown, which is the worst time to debug one.

YOUR JOB: implement `ShutdownFlag` and `install_handlers`.
"""

from __future__ import annotations

import signal
from types import FrameType
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Iterator

STOP_SIGNALS = (signal.SIGTERM, signal.SIGINT)
"""The two that mean "stop".

`SIGTERM` is what `docker stop` and the kubelet send. `SIGINT` is Ctrl-C. Both
should produce the same graceful shutdown - a tool that drains on one and dies on
the other behaves differently in development than in production, which is how you
ship a shutdown bug you never saw.

Deliberately absent: `SIGKILL` cannot be caught (that is the point of it), and
`SIGHUP` conventionally means "reload config", not "stop" - mapping it to
shutdown surprises anyone who sends it expecting a reload.
"""


class ShutdownFlag:
    """A flag the handler sets and the loop reads.

    Two designs, and the choice is worth making deliberately:

        **a plain flag** (this one). Simple. The main loop notices on its next
        pass, so responsiveness is bounded by the poll interval - with a 100ms
        poll, shutdown starts within 100ms. Fine here.

        **a self-pipe.** The handler writes one byte to a pipe the main loop
        `select`s on, so the loop wakes **immediately** rather than on its next
        tick. The standard trick for a loop that blocks on I/O with no timeout,
        because a plain flag is never noticed there at all.

    If you use `signal.set_wakeup_fd`, Python does the self-pipe write for you.
    Record which you picked and why in `DECISIONS.md`.
    """

    def __init__(self) -> None:
        self._requested = False
        self._signal: int | None = None

    @property
    def requested(self) -> bool:
        raise NotImplementedError

    @property
    def signal_number(self) -> int | None:
        """Which signal arrived. Worth keeping for the log line - "shut down
        because SIGTERM" and "because Ctrl-C" are different stories."""
        raise NotImplementedError

    def set(self, signum: int, _frame: FrameType | None = None) -> None:
        """The handler body. Assignment only - **no logging**, no I/O, no locks.

        Tempting to log here, and it is exactly the re-entrancy bug: the handler
        can fire while the main thread is mid-`logging` call and holding its
        lock, and then you deadlock on shutdown.
        """
        raise NotImplementedError


def install_handlers(flag: ShutdownFlag) -> None:
    """Point `STOP_SIGNALS` at `flag.set`.

    **The PID 1 problem, which is the heart of the experiment in the brief:**
    the kernel does not apply *default* signal actions to PID 1. A normal process
    with no SIGTERM handler is killed by the kernel; PID 1 with no handler simply
    **ignores** SIGTERM. So a container whose entrypoint installs no handler sits
    there until `docker stop`'s 10-second grace period expires and SIGKILL
    arrives - which is the ten-second stop, every time, and why `tini` exists.

    Installing a handler is therefore not a nicety when you are PID 1. It is the
    difference between a 0.1-second stop and a 10-second one.
    """
    raise NotImplementedError


def reset_handlers() -> Iterator[None]:
    """Restore the default dispositions. For tests, so one test's handler does
    not leak into the next - a leaked SIGTERM handler makes an unrelated test
    hang, and finding that costs an afternoon."""
    raise NotImplementedError


__all__ = ["STOP_SIGNALS", "ShutdownFlag", "install_handlers", "reset_handlers"]
