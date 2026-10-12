"""Contract for the pure parsers. These are the specification.

The `comm` tests are the ones that matter. Splitting `/proc/[pid]/stat` on
whitespace is the classic bug in every hand-rolled parser, and it does not fail
loudly - it shifts every subsequent field by one, so you get a plausible state
and a wildly wrong RSS, and nothing tells you.
"""

from __future__ import annotations

from datetime import UTC, datetime

import pytest

from ptop.models import ProcState
from ptop.parse import (
    build_system_info,
    parse_cmdline,
    parse_loadavg,
    parse_meminfo,
    parse_stat,
    parse_status_rss_kb,
    parse_status_uid,
    parse_total_cpu_ticks,
    parse_uptime,
    start_time_to_datetime,
)


class TestParseStatNormalCase:
    def test_pid_and_comm(self, read_fixture):
        stat = parse_stat(read_fixture("1/stat"))
        assert stat.pid == 1
        assert stat.comm == "systemd"

    def test_state(self, read_fixture):
        assert parse_stat(read_fixture("1/stat")).state is ProcState.SLEEPING

    def test_ppid(self, read_fixture):
        assert parse_stat(read_fixture("1/stat")).ppid == 0

    def test_cpu_ticks(self, read_fixture):
        """utime is field 14, stime field 15. Off by one here and every CPU
        percentage in the tool is wrong by a plausible-looking amount."""
        stat = parse_stat(read_fixture("1/stat"))
        assert stat.utime == 150
        assert stat.stime == 75
        assert stat.total_ticks == 225

    def test_num_threads_and_starttime(self, read_fixture):
        stat = parse_stat(read_fixture("1/stat"))
        assert stat.num_threads == 1
        assert stat.starttime == 15

    def test_rss_is_in_pages(self, read_fixture):
        """Field 24, in **pages**. `VmRSS` in `status` is in kB. Mixing the two
        gives an RSS that is wrong by a factor of 4 on a 4KiB-page kernel."""
        assert parse_stat(read_fixture("1/stat")).rss_pages == 2500


class TestParseStatAwkwardComm:
    """The whole reason this parser needs writing rather than one-lining."""

    def test_a_comm_containing_a_space_and_a_paren(self, read_fixture):
        """The fixture line is `1217 (my proc)) S 1 ...`.

        The process is named `my proc)`, so the line has a `)` *inside* the
        parentheses. Split on the **last** `)`, not the first, and not on
        whitespace.
        """
        stat = parse_stat(read_fixture("1217/stat"))
        assert stat.comm == "my proc)"

    def test_fields_after_an_awkward_comm_are_still_correct(self, read_fixture):
        """The real test. A parser that gets `comm` wrong usually still returns
        *something* for these, and that something is shifted by one field."""
        stat = parse_stat(read_fixture("1217/stat"))
        assert stat.state is ProcState.SLEEPING
        assert stat.ppid == 1
        assert stat.utime == 300
        assert stat.stime == 120
        assert stat.num_threads == 4
        assert stat.rss_pages == 51200

    def test_comm_is_truncated_to_fifteen_characters(self, read_fixture):
        """The kernel truncates `comm`. The process is really called
        `my-very-long-process-name`; `/proc` says `my-very-long-pr`.

        Cheap test, and it stops you trying to match processes by `comm` later.
        """
        assert parse_stat(read_fixture("1301/stat")).comm == "my-very-long-pr"

    def test_a_zombie_is_parsed_not_skipped(self, read_fixture):
        """A zombie has valid `stat` content and zero everything else. It is a
        real row - E16 is entirely about why it is there."""
        stat = parse_stat(read_fixture("4242/stat"))
        assert stat.state is ProcState.ZOMBIE
        assert stat.total_ticks == 0

    def test_malformed_input_raises(self):
        """Do not return a partial model. A silently wrong RSS is worse than a
        crash, because the crash gets fixed."""
        with pytest.raises(ValueError):
            parse_stat("this is not a stat line\n")


class TestParseStatus:
    def test_uid_takes_the_first_of_four(self, read_fixture):
        """`Uid:` has real, effective, saved and filesystem UIDs. `ps` shows the
        real one, so match it or the live comparison will not line up."""
        assert parse_status_uid(read_fixture("1217/status")) == 1000

    def test_rss_kb(self, read_fixture):
        assert parse_status_rss_kb(read_fixture("1217/status")) == 204800

    def test_a_kernel_thread_has_no_vmrss_at_all(self, read_fixture):
        """**None, not 0.** A kernel thread has no user address space, so the
        `VmRSS` line is absent rather than zero.

        Defaulting it to 0 makes two dozen kernel threads look like real
        processes using no memory, and then your row count differs from `ps`
        and you cannot say why.
        """
        assert parse_status_rss_kb(read_fixture("2/status")) is None


class TestParseCmdline:
    def test_arguments_are_nul_separated(self, read_fixture_bytes):
        """Not space-separated. Splitting on spaces yields one argument."""
        assert parse_cmdline(read_fixture_bytes("1/cmdline")) == "/sbin/init splash"

    def test_an_argument_containing_a_space_survives(self, read_fixture_bytes):
        """`/tmp/my proc)` is one argument containing a space - which is only
        recoverable *because* the separator is NUL."""
        assert parse_cmdline(read_fixture_bytes("1217/cmdline")).startswith("/tmp/my proc)")

    def test_an_empty_cmdline_is_a_kernel_thread(self, read_fixture_bytes):
        """Convention, which `ps` follows: show `comm` in brackets. Returning ""
        makes the busiest rows in your output blank."""
        assert parse_cmdline(read_fixture_bytes("2/cmdline")) == ""


class TestParseSystemFiles:
    def test_total_cpu_ticks_sums_the_aggregate_line(self, read_fixture):
        """Including idle and iowait - this is the **denominator**, so it has to be
        total elapsed CPU time. Omitting idle gives percentages always near 100."""
        assert parse_total_cpu_ticks(read_fixture("stat")) == 100_000

    def test_per_core_lines_are_not_double_counted(self, read_fixture):
        """The fixture's `cpu0` and `cpu1` lines sum to the same total as `cpu `.
        Summing all three halves every percentage."""
        assert parse_total_cpu_ticks(read_fixture("stat")) == 100_000

    def test_loadavg(self, read_fixture):
        assert parse_loadavg(read_fixture("loadavg")) == (0.52, 0.38, 0.29)

    def test_meminfo_returns_bytes_not_kb(self, read_fixture):
        total, available = parse_meminfo(read_fixture("meminfo"))
        assert total == 8039084 * 1024
        assert available == 5123456 * 1024

    def test_uptime_takes_the_first_float(self, read_fixture):
        assert parse_uptime(read_fixture("uptime")) == pytest.approx(226255.63)

    def test_memory_used_excludes_the_page_cache(self, read_fixture):
        """`MemTotal - MemAvailable`, never `MemTotal - MemFree`.

        The fixture has MemFree at 245MB and MemAvailable at 5.1GB. Reading
        MemFree says the box is 97% full; MemAvailable says 36%. Nearly every
        "we are out of memory" false alarm is this mistake.
        """
        info = build_system_info(
            loadavg_text=read_fixture("loadavg"),
            meminfo_text=read_fixture("meminfo"),
            uptime_text=read_fixture("uptime"),
            now=datetime(2026, 9, 21, 12, 0, tzinfo=UTC),
        )
        assert info.mem_used_bytes == (8039084 - 5123456) * 1024


class TestStartTime:
    def test_ticks_since_boot_become_a_wall_clock_time(self):
        """starttime is ticks since **boot**, so this needs /proc/uptime too.
        Two files for one timestamp."""
        boot = datetime(2026, 9, 1, 0, 0, tzinfo=UTC)
        started = start_time_to_datetime(170_000, boot_time=boot, clock_ticks=100)
        assert started == datetime(2026, 9, 1, 0, 28, 20, tzinfo=UTC)

    def test_the_result_is_timezone_aware(self):
        boot = datetime(2026, 9, 1, 0, 0, tzinfo=UTC)
        assert start_time_to_datetime(15, boot_time=boot, clock_ticks=100).tzinfo is not None
