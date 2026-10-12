"""Core types. Given to you complete; everything else is a stub.

`ExitInfo` is the one that matters. "What does exit code 137 mean?" comes up in
almost every DevOps and SRE loop, and the answer is in `from_returncode` below.
"""

from __future__ import annotations

import signal
from dataclasses import dataclass
from enum import StrEnum


class RestartPolicy(StrEnum):
    ALWAYS = "always"
    ON_FAILURE = "on-failure"
    NEVER = "never"


@dataclass(frozen=True, slots=True)
class ProcessSpec:
    """One managed process, from `procs.yaml`.

    `cmd` is a **list**, never a string. `shell=True` with a string means a shell
    sits between the supervisor and the process, which breaks signal forwarding
    in exactly the way this exercise is about - and is how the ten-second
    `docker stop` in the problem statement happens.
    """

    name: str
    cmd: tuple[str, ...]
    restart: RestartPolicy = RestartPolicy.ON_FAILURE
    max_restarts: int | None = None


@dataclass(frozen=True, slots=True)
class SupervisorConfig:
    processes: tuple[ProcessSpec, ...]
    stop_timeout_seconds: float = 8.0


@dataclass(frozen=True, slots=True)
class ExitInfo:
    """A decoded process exit. **Exit codes are an API.**

    The mapping everyone needs and few can recite:

        `Popen.returncode`  `N` for a normal exit, `-N` when killed by signal N.
                            Python's convention, and it is **not** what anything
                            else reports.
        shells, Docker,     `128 + N` for a signal death. Same event, different
        Kubernetes          number.

    So the famous ones:

        **137** = 128 + 9  = SIGKILL. Usually the OOM killer (see E17) or a stop
                             timeout expiring. Almost never a crash in the
                             application's own code, which is why "the app is
                             crashing with 137" is a misdiagnosis.
        **143** = 128 + 15 = SIGTERM. A *graceful* stop request. A pod exiting 143
                             during a deploy is normal, and alerting on it is a
                             classic noisy-alert mistake.
        **139** = 128 + 11 = SIGSEGV. That one really is a crash.
        **130** = 128 + 2  = SIGINT, i.e. somebody pressed Ctrl-C.
    """

    code: int | None  # None when killed by a signal
    signal_number: int | None  # None on a normal exit
    shell_code: int  # what a shell / Docker / Kubernetes reports

    @property
    def signal_name(self) -> str | None:
        """`"SIGKILL"` rather than `9`, for the log line."""
        if self.signal_number is None:
            return None
        return signal.Signals(self.signal_number).name

    @property
    def succeeded(self) -> bool:
        """Only a clean exit 0. A signal death is never a success - including
        SIGTERM, which is a *requested* stop but still not "the work finished"."""
        return self.code == 0

    @classmethod
    def from_returncode(cls, returncode: int) -> ExitInfo:
        """Decode `Popen.returncode`. Pure, table-testable, and the exercise's core.

        Negative means killed by `-returncode`. Positive is a normal exit status.
        """
        if returncode < 0:
            sig = -returncode
            return cls(code=None, signal_number=sig, shell_code=128 + sig)
        return cls(code=returncode, signal_number=None, shell_code=returncode)


@dataclass(frozen=True, slots=True)
class ProcessState:
    """Live state for one managed process."""

    name: str
    pid: int | None = None
    restarts: int = 0
    last_exit: ExitInfo | None = None
    running: bool = False
    give_up: bool = False
