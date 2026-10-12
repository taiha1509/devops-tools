"""Contract for the two-sample deltas and for v1 detection.

Same lesson as E13, different file: **a rate is a property of two observations.**
One `cpu.stat` read gives cumulative counters since the cgroup was created, which
is a lifetime average and says nothing about now.
"""

from __future__ import annotations

import pytest

from cgpeek.delta import cpu_usage_cores, throttle_rate
from cgpeek.models import CpuStat
from cgpeek.parse import parse_cpu_stat
from cgpeek.source import CgroupV1Detected, NotACgroup, detect_version, find_cgroup_path


def read(root, name: str) -> str:
    return (root / name).read_text()


class TestThrottleRate:
    def test_the_exact_rate_between_the_two_fixture_snapshots(
        self, limited_root, limited_root_t1
    ):
        """An **exact** assertion, not a range.

        nr_periods 1500 -> 1520 (delta 20), nr_throttled 570 -> 580 (delta 10).
        10/20 = 0.5 exactly.
        """
        first = parse_cpu_stat(read(limited_root, "cpu.stat"))
        second = parse_cpu_stat(read(limited_root_t1, "cpu.stat"))
        assert throttle_rate(first, second) == pytest.approx(0.5)

    def test_the_interval_rate_differs_from_the_lifetime_ratio(
        self, limited_root, limited_root_t1
    ):
        """Why the delta is the right measurement.

        Lifetime: 580/1520 = 38%. This interval: 10/20 = 50%. The container is
        getting *worse*, and the lifetime figure averages that away - which is
        exactly the wrong behaviour during an incident.
        """
        first = parse_cpu_stat(read(limited_root, "cpu.stat"))
        second = parse_cpu_stat(read(limited_root_t1, "cpu.stat"))
        assert throttle_rate(first, second) > second.throttled_fraction

    def test_a_zero_period_delta_does_not_divide_by_zero(self):
        """Samples too close together, or the cpu controller is not enabled so
        `nr_periods` never moves."""
        stat = CpuStat(nr_periods=100, nr_throttled=10)
        assert throttle_rate(stat, stat) == 0.0

    def test_negative_deltas_return_zero(self):
        """The cgroup was recreated between samples - same path, new counters
        starting at zero. A negative rate is nonsense."""
        first = CpuStat(nr_periods=1000, nr_throttled=500)
        second = CpuStat(nr_periods=10, nr_throttled=2)
        assert throttle_rate(first, second) == 0.0

    def test_no_throttling_is_zero(self):
        first = CpuStat(nr_periods=100, nr_throttled=0)
        second = CpuStat(nr_periods=200, nr_throttled=0)
        assert throttle_rate(first, second) == 0.0

    def test_fully_throttled_is_one(self):
        first = CpuStat(nr_periods=100, nr_throttled=100)
        second = CpuStat(nr_periods=200, nr_throttled=200)
        assert throttle_rate(first, second) == pytest.approx(1.0)


class TestCpuUsageCores:
    def test_the_exact_usage_between_the_two_snapshots(
        self, limited_root, limited_root_t1, elapsed
    ):
        """usage_usec +1,000,000 over 2.0s = exactly 0.5 cores."""
        first = parse_cpu_stat(read(limited_root, "cpu.stat"))
        second = parse_cpu_stat(read(limited_root_t1, "cpu.stat"))
        assert cpu_usage_cores(first, second, elapsed_seconds=elapsed) == pytest.approx(0.5)

    def test_low_usage_and_high_throttling_coexist(
        self, limited_root, limited_root_t1, elapsed
    ):
        """**The whole diagnosis, in one assertion.**

        0.5 cores used against a 0.5-core limit, and throttled in 50% of periods.
        It looks contradictory and is completely normal: the app burns its 50ms
        allowance early in each 100ms period and sits frozen for the rest.
        Average usage is low *because* it is throttled.

        This is why `docker stats` showing low CPU on a throttled container sends
        people looking in entirely the wrong place.
        """
        first = parse_cpu_stat(read(limited_root, "cpu.stat"))
        second = parse_cpu_stat(read(limited_root_t1, "cpu.stat"))
        usage = cpu_usage_cores(first, second, elapsed_seconds=elapsed)
        rate = throttle_rate(first, second)
        assert usage <= 0.5
        assert rate >= 0.4

    def test_zero_elapsed_does_not_divide_by_zero(self):
        stat = CpuStat(usage_usec=1000)
        assert cpu_usage_cores(stat, stat, elapsed_seconds=0.0) == 0.0


class TestVersionDetection:
    def test_v2_is_detected(self, limited_root):
        """One `exists()` on `cgroup.controllers`, rather than parsing
        `/proc/filesystems` or `/proc/mounts`."""
        assert detect_version(limited_root) == 2

    def test_v1_raises_rather_than_being_guessed_at(self, v1_root):
        """**The acceptance criterion: a v1 layout must exit 2.**

        v1 splits controllers across hierarchies with different filenames
        (`memory.limit_in_bytes`, `cpu.cfs_quota_us`) and different semantics. A
        tool that half-works on v1 produces numbers that look right and are not,
        which is strictly worse than refusing.
        """
        with pytest.raises(CgroupV1Detected):
            detect_version(v1_root)

    def test_no_cgroup_filesystem_at_all(self, tmp_path):
        """A Mac, or a stripped container. Exits 2 locally, and that is correct."""
        with pytest.raises(NotACgroup):
            detect_version(tmp_path / "does-not-exist")


class TestFindCgroupPath:
    def test_the_current_process(self, proc_root):
        assert find_cgroup_path(None, proc_root=proc_root).startswith("/")

    def test_another_process(self, proc_root):
        assert find_cgroup_path(1234, proc_root=proc_root) == "/system.slice/docker-3f2a9c1b.scope"

    def test_a_containerised_process_at_the_namespace_root(self, proc_root):
        assert find_cgroup_path(5678, proc_root=proc_root) == "/"

    def test_no_such_pid(self, proc_root):
        with pytest.raises(ProcessLookupError):
            find_cgroup_path(424242, proc_root=proc_root)

    def test_joining_a_leading_slash_path_onto_the_mount(self, limited_root):
        """The most common five-minute bug in this exercise.

        `Path("/sys/fs/cgroup") / "/system.slice/x.scope"` is
        `/system.slice/x.scope` - a leading-slash operand **replaces** the whole
        path rather than appending. Strip it first.
        """
        from cgpeek.source import LiveCgroupSource

        source = LiveCgroupSource(limited_root, cgroup_path="/")
        assert source.directory == limited_root


def test_the_throttling_experiment():
    """A procedure, and the exercise's deliverable. Delete once recorded.

        docker run --rm -it --memory=128m --memory-swap=128m --cpus=0.5 \\
          -v "$PWD":/work -w /work -e UV_PROJECT_ENVIRONMENT=/tmp/venv \\
          ghcr.io/astral-sh/uv:python3.12-bookworm-slim bash
        uv sync
        # OOM: expect exit 137, and oom_kill goes 0 -> 1
        python3 -c 'x = bytearray(200 * 1024 * 1024)' ; echo "exit $?"
        uv run cgpeek
        # throttling: 4 busy threads against half a core
        python3 -c 'import threading
    def spin():
        while True: pass
    [threading.Thread(target=spin, daemon=True).start() for _ in range(4)]
    import time; time.sleep(30)' &
        uv run cgpeek --watch 2

    Then compare against `docker stats` from the Mac and record in
    `DECISIONS.md`:

      * does `docker stats` memory include page cache? The answer **differs
        between Docker versions**, which is exactly why reading the kernel
        directly is worth knowing how to do.
      * `docker stats` shows no throttling figure at all. A container at 40% of
        its CPU limit with terrible p99 looks healthy there and is not.
    """
    raise AssertionError("implement: run the experiments, record them, delete this test")
