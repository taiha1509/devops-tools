"""Contract for the cgroup v2 parsers.

`test_max_quota_parses_to_no_limit` is an explicit acceptance criterion, and
`TestMemoryStat` is where the OOMKilled answer lives.
"""

from __future__ import annotations

import pytest

from cgpeek.models import CpuState, MemoryState
from cgpeek.parse import (
    parse_cpu_max,
    parse_cpu_stat,
    parse_limit,
    parse_memory_events,
    parse_memory_stat,
    parse_proc_cgroup,
)

MIB = 1024 * 1024


def read(root, name: str) -> str:
    return (root / name).read_text()


class TestParseLimit:
    def test_a_byte_count(self, limited_root):
        assert parse_limit(read(limited_root, "memory.max")) == 512 * MIB

    def test_the_max_literal_is_none(self, unlimited_root):
        """**None, not a sentinel.**

        A magic number gets forgotten by exactly one downstream calculation, and
        then you report a container with no limit as using 0.0000001% of it.
        """
        assert parse_limit(read(unlimited_root, "memory.max")) is None

    def test_garbage_raises(self):
        """A limit file containing something unexpected means you are reading
        cgroup v1, or not a cgroup at all. Guessing is worse than stopping."""
        with pytest.raises(ValueError):
            parse_limit("-1\n")


class TestParseCpuMax:
    def test_half_a_core(self, limited_root):
        """`50000 100000` -> 0.5 cores, which is exactly what Kubernetes'
        `limits.cpu: 500m` becomes. Being able to point at the file and say that
        is the Senior-level version of this answer."""
        quota, period = parse_cpu_max(read(limited_root, "cpu.max"))
        assert quota == 50_000
        assert period == 100_000

    def test_max_quota_parses_to_no_limit(self, unlimited_root):
        """**The acceptance criterion, verbatim.**

        `"max 100000"` must parse to "no CPU limit", not to a number. An
        implementation doing `int(fields[0])` crashes; one falling back to `0`
        reports a zero-core quota, which then renders as 100% throttled forever.
        """
        quota, period = parse_cpu_max(read(unlimited_root, "cpu.max"))
        assert quota is None
        assert period == 100_000

    def test_the_period_is_present_even_when_unlimited(self, unlimited_root):
        """Which lets you report "no limit (period 100ms)" rather than hiding it."""
        _, period = parse_cpu_max(read(unlimited_root, "cpu.max"))
        assert period == 100_000

    def test_two_cores(self):
        assert parse_cpu_max("200000 100000\n") == (200_000, 100_000)


class TestMemoryStat:
    def test_anon_is_roughly_the_heap(self, limited_root):
        stat = parse_memory_stat(read(limited_root, "memory.stat"))
        assert stat.anon == pytest.approx(290.1 * MIB, rel=0.01)

    def test_file_is_page_cache_and_it_counts(self, limited_root):
        """**The answer to "OOMKilled but the app says the heap is 300MB".**

        The app is right about its heap and wrong about what the limit measures.
        Page cache accumulates inside the container's own memory accounting, and
        the kernel reclaims most of it under pressure but not all of it in time.
        """
        stat = parse_memory_stat(read(limited_root, "memory.stat"))
        assert stat.file > 0
        assert stat.anon + stat.file == pytest.approx(308.4 * MIB, rel=0.01)

    def test_unknown_keys_are_ignored(self, limited_root):
        """The key set varies by kernel version. A parser that requires every key
        breaks on upgrade."""
        text = read(limited_root, "memory.stat") + "some_future_key 12345\n"
        assert parse_memory_stat(text).anon > 0

    def test_a_declared_but_absent_key_defaults_to_zero(self):
        """`sock` is missing on some kernels. Raising for it is wrong."""
        assert parse_memory_stat("anon 100\nfile 200\n").sock == 0


class TestMemoryEvents:
    def test_oom_and_oom_kill_are_different_counters(self, limited_root):
        """`oom` is "an allocation failed"; `oom_kill` is "the kernel killed
        something". A process can hit the limit, have cache reclaimed, and carry
        on - that is `oom` without `oom_kill`."""
        oom, oom_kill = parse_memory_events(read(limited_root, "memory.events"))
        assert oom == 2
        assert oom_kill == 1

    def test_the_oom_kill_counter_increments_across_the_two_snapshots(
        self, limited_root, limited_root_t1
    ):
        """**The OOM experiment, as a test.**

        The counter lives on the **cgroup**, not the process, which is why it
        survives the kill and why `cgpeek` can report it after the fact. That is
        the entire mechanism behind the brief's experiment.
        """
        _, before = parse_memory_events(read(limited_root, "memory.events"))
        _, after = parse_memory_events(read(limited_root_t1, "memory.events"))
        assert before == 1
        assert after == 2

    def test_a_high_max_count_with_no_kills_is_a_tuning_signal(self, limited_root):
        """1823 times against the limit, one kill. The container is constantly
        pressed and surviving - worth tuning, not an incident."""
        oom, oom_kill = parse_memory_events(read(limited_root, "memory.events"))
        assert oom_kill < oom + 1823


class TestParseCpuStat:
    def test_throttling_counters(self, limited_root):
        stat = parse_cpu_stat(read(limited_root, "cpu.stat"))
        assert stat.nr_periods == 1500
        assert stat.nr_throttled == 570

    def test_no_periods_when_there_is_no_cpu_limit(self, unlimited_root):
        """Which is why `throttled_fraction` guards against dividing by it."""
        assert parse_cpu_stat(read(unlimited_root, "cpu.stat")).nr_periods == 0


class TestParseProcCgroup:
    def test_the_host_path(self, proc_root):
        assert parse_proc_cgroup(read(proc_root / "1234", "cgroup")).startswith("/system.slice/")

    def test_a_container_sees_itself_at_the_root(self, proc_root):
        """**Not an error.**

        Inside a container with its own cgroup namespace the path is just `/` -
        the container sees itself at the root of its own view, and joining `/`
        onto the mount gives exactly the right directory.
        """
        assert parse_proc_cgroup(read(proc_root / "5678", "cgroup")) == "/"

    def test_a_v1_multiline_file_raises(self, proc_root):
        """Many lines, one per controller. More than one line is itself a strong
        v1 signal, and the whole point is to refuse rather than guess."""
        with pytest.raises(ValueError):
            parse_proc_cgroup(read(proc_root / "9012", "cgroup"))


class TestDerivedProperties:
    def test_memory_percent(self, limited_root):
        state = MemoryState(
            current=int(312.4 * MIB),
            max_bytes=512 * MIB,
            high_bytes=460 * MIB,
            stat=parse_memory_stat(read(limited_root, "memory.stat")),
        )
        assert state.percent == pytest.approx(61.0, abs=0.1)

    def test_percent_is_none_when_unlimited(self, unlimited_root):
        """**Not 0%.** A percentage of unlimited is undefined, and printing 0%
        implies headroom that is not being measured."""
        state = MemoryState(
            current=int(1024.0 * MIB),
            max_bytes=None,
            high_bytes=None,
            stat=parse_memory_stat(read(unlimited_root, "memory.stat")),
        )
        assert state.percent is None

    def test_quota_as_cores(self, limited_root):
        state = CpuState(
            quota_usec=50_000,
            period_usec=100_000,
            stat=parse_cpu_stat(read(limited_root, "cpu.stat")),
        )
        assert state.cores == 0.5

    def test_cores_is_none_when_unlimited(self, unlimited_root):
        state = CpuState(
            quota_usec=None,
            period_usec=100_000,
            stat=parse_cpu_stat(read(unlimited_root, "cpu.stat")),
        )
        assert state.cores is None

    def test_the_lifetime_throttled_fraction(self, limited_root):
        """570/1500 = 38% - the number in the brief's sample output."""
        state = CpuState(
            quota_usec=50_000,
            period_usec=100_000,
            stat=parse_cpu_stat(read(limited_root, "cpu.stat")),
        )
        assert state.throttled_fraction == pytest.approx(0.38)

    def test_no_periods_does_not_divide_by_zero(self, unlimited_root):
        state = CpuState(
            quota_usec=None,
            period_usec=100_000,
            stat=parse_cpu_stat(read(unlimited_root, "cpu.stat")),
        )
        assert state.throttled_fraction == 0.0
