"""Fixtures for the supervisor.

The integration tests here start **real** short-lived children via
`sys.executable -c ...`, and they run fine on macOS - `fork`, `exec`, signals and
exit codes all behave the same way. Only the PID 1 experiment needs a container,
because PID 1 semantics are what the container gives you.
"""

from __future__ import annotations

import signal
import sys
from typing import TYPE_CHECKING

import pytest

from minivisor.models import ProcessSpec, RestartPolicy, SupervisorConfig
from minivisor.signals import ShutdownFlag

if TYPE_CHECKING:
    from collections.abc import Callable, Iterator

# Child programs, as one-liners. Keeping them here rather than as files means the
# tests have no fixture directory to keep in sync.
EXIT_ZERO = "import sys; sys.exit(0)"
EXIT_THREE = "import sys; sys.exit(3)"
SELF_SIGKILL = "import os, signal; os.kill(os.getpid(), signal.SIGKILL)"
SELF_SIGSEGV = "import os, signal; os.kill(os.getpid(), signal.SIGSEGV)"
SLEEP_FOREVER = "import time; time.sleep(3600)"

IGNORES_SIGTERM = (
    "import signal, time; signal.signal(signal.SIGTERM, signal.SIG_IGN); time.sleep(3600)"
)
"""A child that refuses to stop politely.

The SIGKILL-escalation test needs this, and it is not a contrived case: a process
blocked in an uninterruptible syscall behaves the same way, and so does any
runtime with a broken shutdown hook.
"""


@pytest.fixture
def flag() -> ShutdownFlag:
    return ShutdownFlag()


@pytest.fixture(autouse=True)
def restore_signal_handlers() -> Iterator[None]:
    """Autouse, and not optional.

    A test that installs a SIGTERM handler and does not restore it leaks it into
    every later test, and the symptom is an unrelated test hanging. Finding that
    by hand costs an afternoon.
    """
    saved = {sig: signal.getsignal(sig) for sig in (signal.SIGTERM, signal.SIGINT)}
    yield
    for sig, handler in saved.items():
        signal.signal(sig, handler)


@pytest.fixture
def spec() -> Callable[..., ProcessSpec]:
    """Build a ProcessSpec that runs one of the one-liners above."""

    def _spec(
        name: str,
        program: str = SLEEP_FOREVER,
        *,
        restart: RestartPolicy = RestartPolicy.ON_FAILURE,
        max_restarts: int | None = None,
    ) -> ProcessSpec:
        return ProcessSpec(
            name=name,
            cmd=(sys.executable, "-c", program),
            restart=restart,
            max_restarts=max_restarts,
        )

    return _spec


@pytest.fixture
def config() -> Callable[..., SupervisorConfig]:
    def _config(
        *specs: ProcessSpec,
        stop_timeout_seconds: float = 2.0,
    ) -> SupervisorConfig:
        # 2s rather than the brief's 8s: the escalation tests wait this out, and
        # a suite that takes 8 seconds per shutdown test stops being run.
        return SupervisorConfig(processes=specs, stop_timeout_seconds=stop_timeout_seconds)

    return _config
