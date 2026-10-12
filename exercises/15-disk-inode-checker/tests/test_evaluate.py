"""Contract for the threshold logic and the deleted-but-open walk.

`test_thirty_percent_bytes_and_ninety_nine_percent_inodes_exits_one` is the
brief's acceptance criterion verbatim, and it is the test that proves the tool
looks at both budgets rather than just the one `df -h` shows.
"""

from __future__ import annotations

from diskcheck.evaluate import Problem, Thresholds, evaluate, exit_code_for
from diskcheck.models import Finding, Mount, MountUsage
from diskcheck.sources import DELETED_SUFFIX
from statfixtures import EMPTY_PSEUDO, FULL, HEALTHY, INODES_EXHAUSTED, ROOT_RESERVE

ROOT_MOUNT = Mount(
    mount_id=25,
    device="/dev/mapper/vg-root",
    mount_point="/",
    fs_type="ext4",
    options="rw,relatime",
)
VAR_MOUNT = Mount(
    mount_id=30,
    device="/dev/mapper/vg-var",
    mount_point="/var",
    fs_type="ext4",
    options="rw,relatime",
)


def _usage(stat, mount=ROOT_MOUNT) -> MountUsage:
    return MountUsage(mount=mount, stat=stat)


class TestThresholds:
    def test_a_healthy_mount_produces_nothing(self):
        assert evaluate([_usage(HEALTHY)], Thresholds()) == []

    def test_a_full_mount_produces_a_crit(self):
        problems = evaluate([_usage(FULL)], Thresholds())
        assert any(p.finding is Finding.BYTES_CRIT for p in problems)

    def test_crit_does_not_also_produce_a_warn(self):
        """One condition, one finding. Two findings for one condition doubles
        every alert and halves how much anyone reads."""
        problems = evaluate([_usage(FULL)], Thresholds())
        byte_findings = [p for p in problems if p.finding.value.startswith("bytes")]
        assert len(byte_findings) == 1

    def test_the_boundary(self):
        """Exactly at crit. Decide and pin it - E01's rule, and the convention
        there was "exactly at the threshold is not over it"."""
        at_ninety = _usage(
            type(HEALTHY)(
                f_bsize=4096,
                f_frsize=4096,
                f_blocks=100,
                f_bfree=10,
                f_bavail=10,
                f_files=1000,
                f_ffree=900,
                f_favail=900,
            )
        )
        problems = evaluate([at_ninety], Thresholds(bytes_crit=90.0))
        assert not any(p.finding is Finding.BYTES_CRIT for p in problems)


class TestBothBudgetsIndependently:
    def test_thirty_percent_bytes_and_ninety_nine_percent_inodes_exits_one(self):
        """**The brief's acceptance criterion, verbatim.**

        Bytes at ~31%, inodes at 99%, `--crit 90` exits 1. A tool that only looks
        at bytes calls this box healthy while writes are already failing with
        `No space left on device`.
        """
        problems = evaluate([_usage(INODES_EXHAUSTED)], Thresholds(inodes_crit=90.0))
        assert any(p.finding is Finding.INODES_CRIT for p in problems)
        assert exit_code_for(problems) == 1

    def test_the_byte_axis_stays_quiet_in_that_case(self):
        """The other half: no spurious byte finding on an inode problem, or the
        reader cannot tell which budget is actually exhausted."""
        problems = evaluate([_usage(INODES_EXHAUSTED)], Thresholds())
        assert not any(p.finding.value.startswith("bytes") for p in problems)

    def test_the_two_axes_have_separate_thresholds(self):
        """Byte usage creeps up; inode usage is flat and then suddenly is not. A
        single threshold tuned for bytes is always wrong for inodes."""
        problems = evaluate([_usage(INODES_EXHAUSTED)], Thresholds(inodes_crit=99.9))
        assert not any(p.finding is Finding.INODES_CRIT for p in problems)


class TestEdgeCases:
    def test_a_zero_block_filesystem_is_skipped_not_reported(self):
        """A pseudo-filesystem that got past the filter. `0/0` is where the
        division-by-zero crash lives, and reporting it at 0% or 100% is also
        wrong - it has no usage to report."""
        assert evaluate([_usage(EMPTY_PSEUDO)], Thresholds()) == []

    def test_the_root_reserve_is_mentioned_in_the_detail(self):
        """The single most useful sentence this tool can print:

            "95% used (5% reserved for root - the app user has 0 bytes available)"

        Page #3 solved in one line of output.
        """
        problems = evaluate([_usage(ROOT_RESERVE)], Thresholds(bytes_crit=90.0))
        assert any("reserv" in p.detail.lower() for p in problems)

    def test_output_order_is_deterministic(self):
        """Two runs over an unchanged box produce identical output, so a diff
        means something changed."""
        usages = [_usage(FULL, VAR_MOUNT), _usage(INODES_EXHAUSTED, ROOT_MOUNT)]
        first = evaluate(usages, Thresholds())
        second = evaluate(list(reversed(usages)), Thresholds())
        assert [(p.mount_point, p.finding) for p in first] == [
            (p.mount_point, p.finding) for p in second
        ]


class TestExitCodes:
    def test_all_clear_is_zero(self):
        assert exit_code_for([]) == 0

    def test_a_crit_is_one(self):
        problem = Problem(
            mount_point="/",
            finding=Finding.BYTES_CRIT,
            percent=95.0,
            threshold=90.0,
        )
        assert exit_code_for([problem]) == 1

    def test_a_warn_alone_is_zero(self):
        """**A warn is information, not a page.**

        Making warnings fail the check is how a monitoring integration ends up
        permanently red and therefore permanently ignored. The brief's exit codes
        say 1 is specifically "a crit threshold was crossed".
        """
        problem = Problem(
            mount_point="/",
            finding=Finding.BYTES_WARN,
            percent=85.0,
            threshold=80.0,
        )
        assert exit_code_for([problem]) == 0


class TestDeletedOpenFiles:
    def test_the_deleted_suffix_is_the_marker(self):
        """`/var/log/app.log (deleted)` - the suffix is part of the symlink
        **target string**, appended by the kernel.

        It is not a real path, and a file genuinely named `app.log (deleted)`
        would be indistinguishable. `lsof` has the same ambiguity.
        """
        assert DELETED_SUFFIX == " (deleted)"

    def test_a_rotated_log_held_open_is_found(self, tmp_path):
        """**Page #2**, and the fix is the part worth printing.

        A log rotated without `copytruncate`: the directory entry is gone so `du`
        cannot see it, the process still holds the fd so the blocks are not
        freed, and it grows forever. The space comes back when the fd closes -
        restart the process, or `truncate -s 0 /proc/<pid>/fd/<n>`.
        """
        raise AssertionError("implement: fd tree with a ' (deleted)' target, assert it is found")

    def test_one_file_held_by_twenty_workers_is_reported_once(self, tmp_path):
        """The most common mistake in reimplementations of `lsof +L1`.

        A log inherited by twenty workers is **one** 50GB file held open twenty
        times, not a terabyte. Deduplicate by `(device, inode)`.
        """
        raise AssertionError("implement: same inode across 20 pids, assert one finding")

    def test_findings_are_sorted_largest_first(self, tmp_path):
        """The 50GB one is the answer; the 4KB ones are noise."""
        raise AssertionError("implement: three deleted files of different sizes")

    def test_inaccessible_processes_are_counted(self, tmp_path):
        """Without root this list is a **lower bound**. Presenting a lower bound
        as an answer is how the real 50GB file stays hidden."""
        raise AssertionError("implement: mode-000 fd dir, assert the count")


def test_the_live_comparison():
    """A procedure, and the exercise's deliverable. Delete once written up.

    In the container, compare against `df -h`, `df -i` and `lsof +L1`. The
    reproductions from the brief:

        # page 1: inode exhaustion on a tiny filesystem (needs --privileged)
        mkdir /tmp/tiny && mount -t tmpfs -o size=10M,nr_inodes=200 tmpfs /tmp/tiny
        for i in $(seq 1 300); do touch /tmp/tiny/f$i; done

        # page 2: deleted but open
        python3 -c 'import os,time; f=open("/tmp/big","wb"); f.write(b"0"*50_000_000); \\
            f.flush(); os.remove("/tmp/big"); time.sleep(600)' &

    Record every difference from the real tools in `DECISIONS.md`.
    """
    raise AssertionError("implement: run the live comparison, record it, delete this test")
