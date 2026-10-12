"""Seams for the two things that are not files: statvfs, and the fd walk.

`statvfs` results are not files, so there is nothing to capture into a fixture
tree. Hence a Protocol and a value type (`StatvfsResult`) instead of a root path -
same idea as E13's `/proc` seam, different mechanism because the thing being
faked is a syscall rather than a file.

YOUR JOB: implement `LiveStatSource`, `LiveProcSource`, `find_deleted_open`,
and `inode_hogs`.
"""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING, Protocol, runtime_checkable

if TYPE_CHECKING:
    from collections.abc import Iterator

    from diskcheck.models import DeletedOpenFile, StatvfsResult

DELETED_SUFFIX = " (deleted)"
"""How the kernel marks an unlinked-but-open file in `/proc/[pid]/fd/`.

`/var/log/app.log (deleted)` - the suffix is part of the **symlink target
string**, appended by the kernel. It is not a real path, and a file genuinely
named `app.log (deleted)` would be indistinguishable. That ambiguity exists in
`lsof` too; note it in `DECISIONS.md` rather than trying to solve it.
"""


@runtime_checkable
class StatSource(Protocol):
    """Something that can report filesystem statistics."""

    def statvfs(self, path: str) -> StatvfsResult:
        """Stats for the filesystem containing `path`.

        Raises:
            PermissionError: the mount point is not readable. Common for
                `/run/user/1000` as another user - skip and count.
            OSError: the mount went away between listing and statting. A stale
                NFS handle does this routinely, and it blocks rather than
                failing fast, so a timeout is worth thinking about.
        """
        ...


class LiveStatSource:
    """Calls the real `os.statvfs`."""

    def statvfs(self, path: str) -> StatvfsResult:
        raise NotImplementedError


@runtime_checkable
class ProcSource(Protocol):
    """Read-only access to something shaped like `/proc`. As E13 and E14."""

    def read_text(self, relative: str) -> str: ...

    def pids(self) -> Iterator[int]: ...

    def list_fds(self, pid: int) -> Iterator[tuple[int, str]]: ...

    def fd_size(self, pid: int, fd: int) -> int: ...

    def command_for(self, pid: int) -> str: ...


class LiveProcSource:
    """Reads a real `/proc`, or a fixture tree shaped like one."""

    def __init__(self, root: Path = Path("/proc")) -> None:
        self._root = root

    def read_text(self, relative: str) -> str:
        raise NotImplementedError

    def pids(self) -> Iterator[int]:
        raise NotImplementedError

    def list_fds(self, pid: int) -> Iterator[tuple[int, str]]:
        """`(fd, symlink_target)`. The **target**, including any ` (deleted)`."""
        raise NotImplementedError

    def fd_size(self, pid: int, fd: int) -> int:
        """Size of the file behind `/proc/[pid]/fd/<fd>`.

        `os.stat` on the **fd link itself, following it** - that reaches the
        still-open inode and gives you the real size. `os.lstat` would stat the
        symlink; stating the target *path* fails, because the path no longer
        exists. That is the whole trick, and it is why this needs its own method
        rather than being a `Path.stat()` at the call site.
        """
        raise NotImplementedError

    def command_for(self, pid: int) -> str:
        raise NotImplementedError


def find_deleted_open(source: ProcSource) -> tuple[list[DeletedOpenFile], int]:
    """Files unlinked while still open. **Page #2.**

    Walk `/proc/[pid]/fd/*`; a target ending in `DELETED_SUFFIX` is a file `du`
    cannot see and `df` still counts.

    Returns `(findings, inaccessible_process_count)` - same honesty rule as E14:
    without root you cannot see other users' fds, so say how many you missed
    rather than implying the list is complete.

    Sort by size descending. The 50GB one is the answer; the 4KB ones are noise.

    Deduplicate by `(device, inode)` if you can get it: a log file inherited by
    twenty worker processes is **one** 50GB file held open twenty times, not a
    terabyte. Reporting it twenty times makes the output both wrong and
    unreadable - this is the single most common mistake in reimplementations of
    `lsof +L1`.
    """
    raise NotImplementedError


def inode_hogs(root: Path, *, top: int = 10) -> list[tuple[Path, int]]:
    """Directories with the most entries, descending. Answers "what ate the inodes?"

    Count **direct entries** per directory, not recursive totals - you are
    looking for the one directory with 900,000 files in it, and a recursive count
    just reports the root of the tree every time.

    `os.scandir` rather than `os.listdir`: it returns entries without an extra
    `stat` per file, which on a directory with 900,000 entries is the difference
    between seconds and minutes.

    Do not follow symlinks (a loop never terminates), skip `PermissionError`
    silently, and consider staying on one filesystem - crossing into a mounted
    NFS share turns a local scan into a network one.
    """
    raise NotImplementedError


__all__ = [
    "DELETED_SUFFIX",
    "LiveProcSource",
    "LiveStatSource",
    "ProcSource",
    "StatSource",
    "find_deleted_open",
    "inode_hogs",
]
