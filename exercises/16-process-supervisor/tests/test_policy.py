"""Contract for exit-code decoding and the restart policy.

**No processes are started in this file.** Both modules are pure, so these are
the fast, table-driven tests - and `TestExitCodeDecoding` is the one worth being
able to recite, because "what does exit code 137 mean?" comes up in almost every
DevOps and SRE loop.
"""

from __future__ import annotations

import signal

import pytest

from minivisor.models import ExitInfo, RestartPolicy
from minivisor.policy import MAX_BACKOFF_SECONDS, backoff, should_restart


class TestExitCodeDecoding:
    @pytest.mark.parametrize(
        ("returncode", "shell_code", "signal_name"),
        [
            (0, 0, None),
            (1, 1, None),
            (3, 3, None),
            (-signal.SIGKILL, 137, "SIGKILL"),
            (-signal.SIGTERM, 143, "SIGTERM"),
            (-signal.SIGSEGV, 139, "SIGSEGV"),
            (-signal.SIGINT, 130, "SIGINT"),
        ],
    )
    def test_the_table(self, returncode, shell_code, signal_name):
        """`Popen.returncode` -> what a shell, Docker and Kubernetes report.

        Python says `-9`. Everything else says `137`. Same event, two numbers,
        and the translation is this one function.
        """
        info = ExitInfo.from_returncode(returncode)
        assert info.shell_code == shell_code
        assert info.signal_name == signal_name

    def test_137_is_sigkill_not_an_application_crash(self):
        """The misdiagnosis this test exists to prevent.

        137 means something killed the process from outside - usually the OOM
        killer (E17 covers why) or a stop timeout expiring. "The app is crashing
        with 137" is almost always wrong: the app did not crash, it was executed.
        """
        info = ExitInfo.from_returncode(-signal.SIGKILL)
        assert info.signal_name == "SIGKILL"
        assert info.code is None
        assert info.succeeded is False

    def test_143_is_a_graceful_stop_request(self):
        """A pod exiting 143 during a deploy is **normal**. Alerting on it is a
        classic noisy-alert mistake - it means the orchestrator asked it to stop
        and it did."""
        assert ExitInfo.from_returncode(-signal.SIGTERM).shell_code == 143

    def test_a_signal_death_is_never_a_success(self):
        """Including SIGTERM. It was a *requested* stop, which is not the same as
        "the work finished"."""
        assert ExitInfo.from_returncode(-signal.SIGTERM).succeeded is False

    def test_only_zero_succeeds(self):
        assert ExitInfo.from_returncode(0).succeeded is True
        assert ExitInfo.from_returncode(1).succeeded is False


class TestShouldRestart:
    def test_shutting_down_beats_restart_always(self):
        """**The rule that makes shutdown possible at all.**

        Without it, a supervisor with an `always` process keeps respawning the
        children it is trying to kill, `stop_all` never converges, and
        `docker stop` hits its timeout every single time.
        """
        info = ExitInfo.from_returncode(-signal.SIGTERM)
        assert should_restart(RestartPolicy.ALWAYS, info, 0, shutting_down=True) is False

    def test_always_restarts_even_a_clean_exit(self):
        """A `restart: always` process that exits 0 has still stopped running,
        and the point of `always` is that something must be running."""
        assert should_restart(RestartPolicy.ALWAYS, ExitInfo.from_returncode(0), 0) is True

    def test_never_does_not_restart_even_a_failure(self):
        assert should_restart(RestartPolicy.NEVER, ExitInfo.from_returncode(1), 0) is False

    def test_on_failure_restarts_a_failure(self):
        assert should_restart(RestartPolicy.ON_FAILURE, ExitInfo.from_returncode(3), 0) is True

    def test_on_failure_leaves_a_clean_exit_alone(self):
        """A one-shot job that succeeded. Restarting it is how a migration runs
        forty times."""
        assert should_restart(RestartPolicy.ON_FAILURE, ExitInfo.from_returncode(0), 0) is False

    def test_on_failure_restarts_a_killed_process(self):
        """Killed by something else - OOM, or an operator. The process did not
        choose to stop, so `on-failure` should bring it back."""
        info = ExitInfo.from_returncode(-signal.SIGKILL)
        assert should_restart(RestartPolicy.ON_FAILURE, info, 0) is True

    def test_max_restarts_is_respected(self):
        info = ExitInfo.from_returncode(1)
        assert should_restart(RestartPolicy.ON_FAILURE, info, 5, max_restarts=5) is False

    def test_below_max_restarts_still_restarts(self):
        info = ExitInfo.from_returncode(1)
        assert should_restart(RestartPolicy.ON_FAILURE, info, 4, max_restarts=5) is True

    def test_none_max_restarts_means_unlimited(self):
        info = ExitInfo.from_returncode(1)
        assert should_restart(RestartPolicy.ALWAYS, info, 9999, max_restarts=None) is True


class TestBackoff:
    def test_it_is_exponential(self):
        assert backoff(0) < backoff(1) < backoff(2) < backoff(3)

    def test_the_first_backoff_is_not_zero(self):
        """A process that fails instantly in a zero-backoff `always` loop is a
        busy-wait that pins a core and floods the logs."""
        assert backoff(0) > 0

    def test_it_is_capped(self):
        """Uncapped doubling reaches an hour by restart 12, at which point a
        process that would have recovered is simply down."""
        assert backoff(100) <= MAX_BACKOFF_SECONDS

    def test_the_cap_is_configurable(self):
        assert backoff(100, cap=5.0) == 5.0
