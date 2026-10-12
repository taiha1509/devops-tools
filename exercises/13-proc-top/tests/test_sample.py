"""Contract for CPU% and for the vanishing-process rule.

The central claim of this exercise, as a test suite: **CPU% is a property of two
observations, not of a process.** Everything in `TestCpuPercent` follows from
that, including why `ps` and `top` disagree.
"""

from __future__ import annotations

import pytest

from ptop.models import ProcSample, ProcState
from ptop.report import snapshot
from ptop.sample import cpu_percent, cpu_percent_lifetime


def _samples(
    proc_delta: int, system_delta: int, *, pid: int = 1
) -> tuple[ProcSample, ProcSample]:
    first = ProcSample(pid=pid, proc_ticks=225, total_system_ticks=100_000)
    second = ProcSample(
        pid=pid,
        proc_ticks=225 + proc_delta,
        total_system_ticks=100_000 + system_delta,
    )
    return first, second


class TestCpuPercent:
    def test_the_exact_number_from_the_two_fixture_snapshots(self):
        """The acceptance criterion: an **exact** assertion, not a range.

        pid 1 goes 225 -> 325 ticks (delta 100) while the system goes
        100000 -> 101000 (delta 1000). 100/1000 = 10%.
        """
        first, second = _samples(100, 1000)
        assert cpu_percent(first, second) == pytest.approx(10.0)

    def test_one_core_fully_used_is_one_hundred_percent(self):
        """With `cores=1`, a process consuming every tick the system saw is 100%."""
        first, second = _samples(1000, 1000)
        assert cpu_percent(first, second) == pytest.approx(100.0)

    def test_a_four_thread_process_can_exceed_one_hundred_percent(self):
        """380% is not a bug - it is nearly four cores.

        `top` and `htop` both default to this convention, which is why the
        problem statement's 380% needs explaining rather than fixing.
        """
        first, second = _samples(3800, 1000)
        assert cpu_percent(first, second) == pytest.approx(380.0)

    def test_whole_machine_scaling_divides_by_core_count(self):
        """The other convention. Same process, same interval, a number four times
        smaller - which is why the `--help` has to say which one it means."""
        first, second = _samples(3800, 1000)
        assert cpu_percent(first, second, cores=4) == pytest.approx(1520.0)

    def test_an_idle_process_is_zero(self):
        first, second = _samples(0, 1000)
        assert cpu_percent(first, second) == pytest.approx(0.0)

    def test_a_zero_system_delta_does_not_divide_by_zero(self):
        """Two samples inside the same tick. `--interval 0` hits this at once."""
        first, second = _samples(0, 0)
        assert cpu_percent(first, second) == 0.0

    def test_a_negative_process_delta_is_treated_as_a_new_process(self):
        """The PID was reused between samples, so the counters went backwards.

        Return 0.0 rather than a nonsensical negative. `top` cannot get this
        right either, which is worth knowing.
        """
        first, second = _samples(-50, 1000)
        assert cpu_percent(first, second) == 0.0

    def test_mismatched_pids_raise(self):
        """A programming error, not bad data."""
        first = ProcSample(pid=1, proc_ticks=100, total_system_ticks=1000)
        second = ProcSample(pid=2, proc_ticks=200, total_system_ticks=2000)
        with pytest.raises(ValueError):
            cpu_percent(first, second)


class TestLifetimeAverage:
    def test_what_ps_shows(self):
        """A process that used 6000 ticks (60s of CPU) over 600s of wall time
        averaged 10%."""
        assert cpu_percent_lifetime(
            proc_ticks=6000, process_age_seconds=600, clock_ticks=100
        ) == pytest.approx(10.0)

    def test_why_ps_and_top_disagree(self):
        """The answer to the standard screen question, as an assertion.

        A process that burned a full core for 5 minutes and has been idle for a
        day: `ps` still reports ~0.35% because it averages over the whole life;
        `top` reports 0% because nothing happened in the last interval. Neither
        is wrong - they measure different things.
        """
        lifetime = cpu_percent_lifetime(
            proc_ticks=30_000,  # 300s of CPU
            process_age_seconds=86_400,
            clock_ticks=100,
        )
        interval_first, interval_second = _samples(0, 1000)
        assert lifetime == pytest.approx(0.347, abs=0.01)
        assert cpu_percent(interval_first, interval_second) == 0.0

    def test_a_zero_age_does_not_divide_by_zero(self):
        """A process started in the current tick."""
        assert cpu_percent_lifetime(proc_ticks=0, process_age_seconds=0, clock_ticks=100) == 0.0


class TestSnapshot:
    def test_every_pid_directory_is_found(self, source, now, clock_ticks):
        """Five readable processes in the fixture: 1, 2, 1217, 1301, 4242."""
        result = snapshot(source, now=now, clock_ticks=clock_ticks)
        assert {p.pid for p in result.processes} == {1, 2, 1217, 1301, 4242}

    def test_non_numeric_entries_are_skipped(self, source, now, clock_ticks):
        """The fixture has `self/` and `net/`. A bare `int(entry)` over every
        dirent crashes on the first one."""
        result = snapshot(source, now=now, clock_ticks=clock_ticks)
        assert all(isinstance(p.pid, int) for p in result.processes)

    def test_a_vanished_process_is_counted_not_fatal(self, source, now, clock_ticks):
        """Fixture pid 9999 is a directory with no `stat` - a process that exited
        between the listdir and the open. **That is not an error, it is Tuesday.**

        It must be counted, though. "41 processes, 2 vanished" is a tool you can
        trust; "41 processes" when `ps` says 43 is one you cannot.
        """
        result = snapshot(source, now=now, clock_ticks=clock_ticks)
        assert result.vanished == 1
        assert 9999 not in {p.pid for p in result.processes}

    def test_a_single_snapshot_has_no_cpu_percent(self, source, now, clock_ticks):
        """**None, not 0.0.** One snapshot cannot produce an interval percentage,
        and putting a lifetime average under a column called "CPU%" is the exact
        confusion this exercise exists to clear up."""
        result = snapshot(source, now=now, clock_ticks=clock_ticks)
        assert all(p.cpu_percent is None for p in result.processes)

    def test_a_kernel_thread_is_shown_in_brackets(self, source, now, clock_ticks):
        """`[kthreadd]`, matching `ps`. An empty command makes the row blank."""
        result = snapshot(source, now=now, clock_ticks=clock_ticks)
        kthreadd = next(p for p in result.processes if p.pid == 2)
        assert kthreadd.command.startswith("[")

    def test_a_zombie_appears_with_state_z(self, source, now, clock_ticks):
        result = snapshot(source, now=now, clock_ticks=clock_ticks)
        zombie = next(p for p in result.processes if p.pid == 4242)
        assert zombie.state is ProcState.ZOMBIE

    def test_an_unknown_uid_falls_back_to_the_number(self, source, now, clock_ticks):
        """`/etc/passwd` is not in `/proc`, so a fixture tree cannot supply names -
        and inside a container the names differ from the host's anyway. `ps` falls
        back to the numeric UID; do the same."""
        result = snapshot(source, now=now, clock_ticks=clock_ticks, uid_names={})
        assert any(p.user == "1000" for p in result.processes)

    def test_rss_is_reported_in_bytes(self, source, now, clock_ticks):
        """Whichever source you chose, the model is in bytes. pid 1217 has
        204800 kB in `status` and 51200 pages in `stat` - which agree at a 4KiB
        page size, deliberately, so this test passes either way."""
        result = snapshot(source, now=now, clock_ticks=clock_ticks)
        proc = next(p for p in result.processes if p.pid == 1217)
        assert proc.rss_bytes == 204800 * 1024

    def test_the_live_comparison(self, source, now, clock_ticks):
        """Not an assertion - a procedure, and the exercise's real deliverable.

        Run `ptop list` and `ps -eo pid,ppid,stat,rss,comm` side by side in the
        container and explain **every** difference in `DECISIONS.md`:

            "Mine says 41 processes, ps says 43 - the two extra were ps itself
            and the shell that ran it"

        That sentence is what the exercise is for. Delete this test once written.
        """
        raise AssertionError("implement: run the live comparison, record it, delete this test")
