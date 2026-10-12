"""Contract for mountinfo parsing and the `df` arithmetic.

`test_the_df_percentage_formula_*` pair is the heart of this file. The brief is
explicit: *the number must match `df`, not your intuition.*
"""

from __future__ import annotations

import pytest

from diskcheck.models import MountUsage
from diskcheck.mountinfo import is_real_filesystem, parse_mountinfo, unescape_octal
from statfixtures import FULL, HEALTHY, INODES_EXHAUSTED, ROOT_RESERVE


class TestUnescapeOctal:
    def test_a_space_in_a_mount_point(self):
        """`\\040` is the one you will actually hit - external drives are full of
        mount points with spaces."""
        assert unescape_octal(r"/mnt/my\040backup") == "/mnt/my backup"

    @pytest.mark.parametrize(
        ("escaped", "expected"),
        [(r"a\011b", "a\tb"), (r"a\012b", "a\nb"), (r"a\134b", "a\\b")],
    )
    def test_the_other_three_escapes(self, escaped, expected):
        assert unescape_octal(escaped) == expected

    def test_a_backslash_escape_is_decoded_last(self):
        r"""`\134040` is a literal backslash followed by `040`, **not** a space.

        Decoding `\134` first turns it into `\040` and then a second pass turns
        that into a space - so order matters, and getting it wrong produces a
        path that looks fine and is wrong.
        """
        assert unescape_octal(r"\134040") == r"\040"

    def test_plain_paths_are_untouched(self):
        assert unescape_octal("/var/lib/docker") == "/var/lib/docker"

    def test_utf8_in_paths_survives(self):
        """Why not `codecs.decode(text, "unicode_escape")`: it mangles real UTF-8,
        because a path is bytes, not latin-1."""
        assert unescape_octal("/mnt/dữ liệu") == "/mnt/dữ liệu"


class TestParseMountinfo:
    def test_every_line_is_parsed(self, mountinfo_text):
        assert len(parse_mountinfo(mountinfo_text)) == 14

    def test_the_root_filesystem(self, mountinfo_text):
        mounts = parse_mountinfo(mountinfo_text)
        root = next(m for m in mounts if m.mount_point == "/")
        assert root.mount_id == 25
        assert root.fs_type == "ext4"
        assert root.device == "/dev/mapper/vg-root"

    def test_a_mount_point_containing_a_space(self, mountinfo_text):
        """The reason the fixture has this line. A parser that does not decode
        the escape reports a mount point that does not exist."""
        mounts = parse_mountinfo(mountinfo_text)
        assert any(m.mount_point == "/mnt/my backup" for m in mounts)

    def test_variable_optional_fields_before_the_separator(self, mountinfo_text):
        """**The structural trap.**

        Line 50 has *two* optional fields (`master:1 propagate_from:25`) where
        most lines have one or none. Split on the standalone `-`; indexing past
        field 5 from the left, or from the right, works on your laptop and breaks
        on every Kubernetes node.
        """
        mounts = parse_mountinfo(mountinfo_text)
        bind = next(m for m in mounts if m.mount_point == "/mnt/bind")
        assert bind.fs_type == "ext4"
        assert bind.device == "/dev/sdc1"

    def test_a_line_with_no_optional_fields(self, mountinfo_text):
        """The overlay lines have none at all - the other end of the same trap."""
        mounts = parse_mountinfo(mountinfo_text)
        overlay = next(m for m in mounts if "overlay2" in m.mount_point)
        assert overlay.fs_type == "overlay"

    def test_file_order_is_preserved(self, mountinfo_text):
        """Later mounts shadow earlier ones at the same point, and file order is
        what tells you which is on top."""
        mounts = parse_mountinfo(mountinfo_text)
        assert mounts[0].mount_point == "/proc"


class TestFiltering:
    def test_pseudo_filesystems_are_excluded(self, mountinfo_text):
        mounts = [m for m in parse_mountinfo(mountinfo_text) if is_real_filesystem(m)]
        assert not any(m.fs_type in {"proc", "sysfs", "cgroup2", "devpts"} for m in mounts)

    def test_real_filesystems_survive(self, mountinfo_text):
        mounts = [m for m in parse_mountinfo(mountinfo_text) if is_real_filesystem(m)]
        points = {m.mount_point for m in mounts}
        assert {"/", "/var", "/boot"} <= points

    def test_tmpfs_is_excluded_by_default(self, mountinfo_text):
        """A systemd box has a dozen tiny tmpfs mounts. Reporting all of them is
        noise - but `/dev/shm` filling up is a real page, hence the flag."""
        mounts = [m for m in parse_mountinfo(mountinfo_text) if is_real_filesystem(m)]
        assert not any(m.fs_type == "tmpfs" for m in mounts)

    def test_tmpfs_can_be_included(self, mountinfo_text):
        mounts = [
            m for m in parse_mountinfo(mountinfo_text) if is_real_filesystem(m, include_tmpfs=True)
        ]
        assert any(m.mount_point == "/dev/shm" for m in mounts)

    def test_overlay_is_reported_only_once(self, mountinfo_text):
        """The fixture has two. On a box running containers there are dozens, the
        lower layers are read-only, and their "usage" is meaningless."""
        mounts = [m for m in parse_mountinfo(mountinfo_text) if is_real_filesystem(m)]
        assert len([m for m in mounts if m.fs_type == "overlay"]) <= 1


class TestDfArithmetic:
    """**The acceptance criterion: the number must match `df`, not your intuition.**"""

    def _usage(self, mountinfo_text, stat) -> MountUsage:
        mount = parse_mountinfo(mountinfo_text)[4]  # the root ext4 mount
        return MountUsage(mount=mount, stat=stat)

    def test_the_df_percentage_formula_with_a_nonzero_reserve(self, mountinfo_text):
        """100 blocks, 90 used, 10 free to root, 5 free to users.

            df's way:      90 / (90 + 5) = 94.7%
            the naive way: 90 / 100       = 90.0%

        `df` rounds to 95%. Use `used / (used + avail)` or your tool disagrees
        with `df` by a couple of points forever on every default ext4 filesystem,
        and nobody will be able to say which of you is right.
        """
        usage = self._usage(mountinfo_text, ROOT_RESERVE)
        assert usage.used_percent == pytest.approx(94.7, abs=0.1)

    def test_the_naive_formula_would_give_a_different_answer(self, mountinfo_text):
        """Stated as a test so the difference is recorded, not just asserted away."""
        usage = self._usage(mountinfo_text, ROOT_RESERVE)
        naive = usage.used_bytes / usage.total_bytes * 100
        assert naive == pytest.approx(90.0)
        assert usage.used_percent != pytest.approx(naive)

    def test_the_reserve_is_visible_as_two_different_free_numbers(self, mountinfo_text):
        """Page #3 in one assertion: root has twice the headroom the app user has.

        An engineer frees "5%", root processes keep writing, and the app still
        gets ENOSPC. Printing both numbers is the whole value of this tool
        over `df`.
        """
        usage = self._usage(mountinfo_text, ROOT_RESERVE)
        assert usage.available_bytes < usage.free_bytes_including_reserve

    def test_a_full_filesystem_is_one_hundred_percent(self, mountinfo_text):
        assert self._usage(mountinfo_text, FULL).used_percent == pytest.approx(100.0)

    def test_a_healthy_filesystem(self, mountinfo_text):
        usage = self._usage(mountinfo_text, HEALTHY)
        assert 40.0 < usage.used_percent < 45.0


class TestInodeArithmetic:
    def test_inodes_are_a_separate_budget(self, mountinfo_text):
        """**Page #1.** Bytes at ~31%, inodes at 99%.

        `No space left on device` while `df -h` says the volume is a third full.
        A tool that only looks at bytes calls this box healthy.
        """
        mount = parse_mountinfo(mountinfo_text)[4]
        usage = MountUsage(mount=mount, stat=INODES_EXHAUSTED)
        assert usage.used_percent < 40.0
        assert usage.inode_used_percent > 98.0
