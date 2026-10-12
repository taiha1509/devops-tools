"""Core data types. Given to you complete; everything else is a stub.

`MountUsage` is where the whole exercise lives. Three block counts, not one, and
the difference between them is the answer to two of the three pages.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum


class Finding(StrEnum):
    BYTES_WARN = "bytes_warn"
    BYTES_CRIT = "bytes_crit"
    INODES_WARN = "inodes_warn"
    INODES_CRIT = "inodes_crit"


@dataclass(frozen=True, slots=True)
class Mount:
    """One line of `/proc/self/mountinfo`."""

    mount_id: int
    device: str
    mount_point: str
    fs_type: str
    options: str


@dataclass(frozen=True, slots=True)
class StatvfsResult:
    """The `os.statvfs` fields this tool uses. A plain value, so it can be a fixture.

    `statvfs` results are not files, so there is nothing to capture into a
    fixture tree - hence a `StatSource` protocol and this shape instead. Same
    seam idea as E13's `/proc` root, different mechanism.

    **The three block counts are the exercise:**

        f_blocks  total blocks
        f_bfree   free blocks, **including root's reserve**
        f_bavail  free blocks available to an ordinary user

    ext4 reserves 5% for root by default. That gap between `f_bfree` and
    `f_bavail` is page #3: an engineer frees 5%, root processes keep writing
    happily, and the app user still gets `ENOSPC` at what `df` reports as 95%.
    """

    f_bsize: int
    f_frsize: int
    f_blocks: int
    f_bfree: int
    f_bavail: int
    f_files: int
    f_ffree: int
    f_favail: int


@dataclass(frozen=True, slots=True)
class MountUsage:
    """Usage for one mount, bytes and inodes, computed the way `df` computes it."""

    mount: Mount
    stat: StatvfsResult

    @property
    def total_bytes(self) -> int:
        return self.stat.f_blocks * self.stat.f_frsize

    @property
    def available_bytes(self) -> int:
        """What an ordinary user can still write. `f_bavail`, not `f_bfree`."""
        return self.stat.f_bavail * self.stat.f_frsize

    @property
    def free_bytes_including_reserve(self) -> int:
        """What root can still write. The difference from `available_bytes` is
        the reserve, and reporting only this number is page #3."""
        return self.stat.f_bfree * self.stat.f_frsize

    @property
    def used_bytes(self) -> int:
        """Total minus free-including-reserve. This is what is actually consumed."""
        return (self.stat.f_blocks - self.stat.f_bfree) * self.stat.f_frsize

    @property
    def used_percent(self) -> float:
        """**`used / (used + avail)`, which is how `df` computes it.**

        Not `used / total`. The two differ by exactly the root reserve, so on a
        default ext4 filesystem your number is a couple of points off `df`'s
        forever, and you will not know which of you is wrong.

        Worked example - 100 blocks total, 90 used, 5 reserved for root:
            df's way:     90 / (90 + 5)  = 94.7%
            the naive way: 90 / 100      = 90.0%
        `df` says 95%. Match it, because `df` is what the alert and the human
        are both looking at.
        """
        used = self.stat.f_blocks - self.stat.f_bfree
        avail = self.stat.f_bavail
        denominator = used + avail
        return 0.0 if denominator == 0 else used / denominator * 100

    @property
    def inode_used_percent(self) -> float:
        """Inodes are a **separate budget** and this is page #1.

        A million 1-byte cache files exhaust `f_files` while bytes are barely
        touched. `No space left on device` with `df -h` showing 40% used is
        always this.
        """
        used = self.stat.f_files - self.stat.f_ffree
        denominator = used + self.stat.f_favail
        return 0.0 if denominator == 0 else used / denominator * 100


@dataclass(frozen=True, slots=True)
class DeletedOpenFile:
    """A file unlinked while still held open. Page #2.

    `du` cannot see it - there is no directory entry any more. `df` still counts
    it, because the inode and its blocks survive until the last fd closes. The
    usual cause is a log rotated without `copytruncate`: the old file is gone
    from the directory and the process is still writing to it, forever.
    """

    pid: int
    command: str
    fd: int
    path: str
    size_bytes: int
