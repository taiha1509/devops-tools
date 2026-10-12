"""Integration tests: real children, real signals. These run fine on macOS.

`fork`, `exec`, signals and exit codes behave the same on Darwin as on Linux -
only PID 1 semantics differ, and that is the one thing the container experiment
is for.
"""

from __future__ import annotations

import signal
import time

import pytest

from conftest import (
    EXIT_THREE,
    EXIT_ZERO,
    IGNORES_SIGTERM,
    SELF_SIGKILL,
    SLEEP_FOREVER,
)
from minivisor.models import RestartPolicy
from minivisor.supervisor import Supervisor


class TestRealChildren:
    def test_a_child_that_exits_zero(self, spec, config, flag):
        sup = Supervisor(config(spec("ok", EXIT_ZERO, restart=RestartPolicy.NEVER)), flag)
        sup.start("ok")
        time.sleep(0.5)
        exits = sup.reap()
        assert exits[0][1].code == 0

    def test_a_child_that_exits_three(self, spec, config, flag):
        sup = Supervisor(config(spec("bad", EXIT_THREE, restart=RestartPolicy.NEVER)), flag)
        sup.start("bad")
        time.sleep(0.5)
        exits = sup.reap()
        assert exits[0][1].shell_code == 3

    def test_a_child_that_kills_itself(self, spec, config, flag):
        """`SIGKILL` from inside. `Popen.returncode` is -9; the decoded shell code
        is 137 - the number anyone reading Docker logs will actually see."""
        sup = Supervisor(config(spec("killed", SELF_SIGKILL, restart=RestartPolicy.NEVER)), flag)
        sup.start("killed")
        time.sleep(0.5)
        exits = sup.reap()
        assert exits[0][1].signal_name == "SIGKILL"
        assert exits[0][1].shell_code == 137

    def test_reap_is_non_blocking(self, spec, config, flag):
        """A long-running child must not make `reap()` wait. The whole loop
        depends on this - a blocking reap means the supervisor stops noticing
        shutdown requests."""
        sup = Supervisor(config(spec("sleeper", SLEEP_FOREVER)), flag)
        sup.start("sleeper")
        started = time.monotonic()
        sup.reap()
        assert time.monotonic() - started < 0.5
        sup.stop_all()

    def test_no_zombies_are_left_behind(self, spec, config, flag):
        """A child that exits and is never waited for becomes a zombie - `Z` in
        E13's `ptop`. It holds a process-table slot forever, and enough of them
        mean nothing on the box can fork.

        Assert the pid is genuinely gone: `os.kill(pid, 0)` on a zombie
        **succeeds**, because the entry still exists. That is the trap - checking
        for liveness that way reports zombies as healthy processes.
        """
        raise AssertionError("implement: start, exit, reap, assert the pid is not a zombie")


class TestGracefulShutdown:
    def test_sigterm_is_forwarded_to_children(self, spec, config, flag):
        """The children did not get the signal the supervisor got.

        The kernel sent SIGTERM to the supervisor **alone**. A child that is never
        told is a child that never drains - that is the "workers never flush
        their buffers" half of the problem statement.
        """
        raise AssertionError("implement: run in a thread, set the flag, assert children got TERM")

    def test_a_child_ignoring_sigterm_is_sigkilled_after_the_timeout(self, spec, config, flag):
        """**The acceptance criterion.**

        A process blocked in an uninterruptible syscall behaves the same way as
        this deliberate `SIG_IGN`, so this is not a contrived case. It must still
        die, or `docker stop` hits its own timeout and kills you both.
        """
        sup = Supervisor(
            config(spec("stubborn", IGNORES_SIGTERM), stop_timeout_seconds=1.0),
            flag,
        )
        sup.start("stubborn")
        time.sleep(0.3)
        started = time.monotonic()
        sup.stop_all()
        elapsed = time.monotonic() - started
        assert 0.9 < elapsed < 3.0
        assert all(not s.running for s in sup.states())

    def test_a_cooperative_child_stops_well_before_the_timeout(self, spec, config, flag):
        """The other half: escalation must not be the *normal* path. If every
        shutdown takes the full timeout, you have not implemented graceful stop,
        you have implemented a delay before SIGKILL."""
        sup = Supervisor(config(spec("polite", SLEEP_FOREVER), stop_timeout_seconds=5.0), flag)
        sup.start("polite")
        time.sleep(0.3)
        started = time.monotonic()
        sup.stop_all()
        assert time.monotonic() - started < 2.0

    def test_shutdown_stops_restarting_an_always_process(self, spec, config, flag):
        """Rule 1 of `should_restart`, end to end. Without it `stop_all` never
        converges."""
        raise AssertionError("implement: always-restart child, shut down, assert it stays dead")

    def test_the_exit_code_reflects_the_children(self, spec, config, flag):
        """0 when every child exited cleanly, non-zero otherwise. Docker reads
        this, so it is an API."""
        raise AssertionError("implement: one child exits 3, assert run() returns non-zero")


class TestSignalHandling:
    def test_the_handler_only_sets_a_flag(self, flag):
        """No I/O, no logging, no locks in a handler.

        Python runs handlers between bytecodes, so a handler that logs can fire
        while the main thread holds the logging lock - and then you deadlock
        during shutdown, which is the worst possible time.
        """
        flag.set(signal.SIGTERM)
        assert flag.requested is True
        assert flag.signal_number == signal.SIGTERM

    def test_both_stop_signals_are_handled(self, flag):
        """SIGTERM is `docker stop`; SIGINT is Ctrl-C. A tool that drains on one
        and dies on the other behaves differently in development than in
        production, which is how you ship a shutdown bug you never saw."""
        raise AssertionError("implement: install handlers, raise each signal, assert both set it")

    def test_handlers_are_installed_before_any_child_starts(self):
        """A SIGTERM arriving between the first spawn and the handler install is
        handled by the **default** disposition - which for PID 1 means *ignored*,
        so the stop request is lost and you wait out the full grace period."""
        raise AssertionError("implement: assert ordering in cli.run, or make it structural")


@pytest.mark.skip(reason="Run by hand in a container; record the four timings in DECISIONS.md")
def test_the_pid_1_experiment():
    """**The experiment, and the point of the whole exercise.**

        docker run --rm --name mv -v "$PWD":/work -w /work \\
          -e UV_PROJECT_ENVIRONMENT=/tmp/venv \\
          ghcr.io/astral-sh/uv:python3.12-bookworm-slim \\
          uv run minivisor run --config procs.yaml
        # other terminal:
        time docker stop mv

    Four runs, four timings to record:

        1. your supervisor as PID 1, **with** the SIGTERM handler
        2. the same, with `--init` (Docker injects `tini` as PID 1)
        3. your supervisor as PID 1, handler **removed**
        4. the same with `--init`

    Run 3 should take the full ten seconds. The explanation is the deliverable:
    **the kernel does not apply default signal actions to PID 1.** A normal
    process with no handler is killed by the kernel; PID 1 with no handler simply
    *ignores* SIGTERM. So `docker stop` waits out its grace period and SIGKILLs.

    That is the ten-second `docker stop` in the problem statement, and it is why
    `tini` exists - run 4 is fast because tini has a handler and forwards.

    This test is skipped rather than deleted: it is the exercise's most
    interview-relevant content, and a skip in the output is a reminder.
    """
