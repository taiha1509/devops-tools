"""Loading `procs.yaml`.

YOUR JOB: implement `load_config`.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pathlib import Path

    from minivisor.models import SupervisorConfig


def load_config(path: Path) -> SupervisorConfig:
    """Parse the config.

    Expected shape::

        processes:
          - name: web
            cmd: ["python3", "-m", "http.server", "8080"]
            restart: always          # always | on-failure | never
          - name: worker
            cmd: ["python3", "worker.py"]
            restart: on-failure
            max_restarts: 5
        stop_timeout_seconds: 8

    Validate, and reject with a message naming the offending process:

        * **`cmd` must be a list.** A string is the mistake that matters: it
          implies `shell=True`, which puts a shell between you and the process
          and breaks signal forwarding - the exact bug this exercise is about.
          Reject it rather than helpfully splitting it.
        * `name` must be unique and non-empty. Duplicate names make the logs
          unreadable and the state dict silently lose a process.
        * `max_restarts` only means something with `restart: on-failure` or
          `always`. With `never` it is a contradiction - warn rather than fail.
        * `stop_timeout_seconds` must be positive, and **warn if it is >= 10**:
          Docker's default grace period is 10s, so a longer timeout means the
          runtime SIGKILLs you before your own escalation runs and your shutdown
          logic never executes. That is a silent misconfiguration worth catching
          at load time.
    """
    raise NotImplementedError


__all__ = ["load_config"]
