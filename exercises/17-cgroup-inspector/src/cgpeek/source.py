"""Finding and reading the cgroup. The impure part.

YOUR JOB: implement `detect_version`, `find_cgroup_path`, and `LiveCgroupSource`.
"""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING, Protocol, runtime_checkable

if TYPE_CHECKING:
    from cgpeek.models import CgroupSnapshot

CGROUP_MOUNT = Path("/sys/fs/cgroup")
V2_MARKER = "cgroup.controllers"
"""Presence of this file at the mount root means cgroup **v2**.

Its absence means v1 (or not a cgroup mount at all). This is the detection the
brief asks for, and it is one `exists()` call rather than parsing
`/proc/filesystems` or `/proc/mounts`.
"""


class CgroupV1Detected(Exception):
    """This is a v1 layout. **Exit 2 with a clear message rather than guessing.**

    v1 splits controllers across separate hierarchies with different filenames
    (`memory.limit_in_bytes`, `cpu.cfs_quota_us`) and different semantics. A tool
    that half-works on v1 produces numbers that look right and are not, which is
    strictly worse than refusing - and modern Docker, containerd and Kubernetes
    nodes are all v2, so refusing costs almost nothing.
    """


class NotACgroup(Exception):
    """No cgroup filesystem at all - a Mac, or a stripped container. Exit 2."""


@runtime_checkable
class CgroupSource(Protocol):
    """Read-only access to something shaped like `/sys/fs/cgroup`."""

    def read_text(self, relative: str) -> str:
        """Read a cgroup file. Raises `FileNotFoundError` if absent.

        Absence is **normal and meaningful**, not exceptional: `memory.max` does
        not exist in the root cgroup, and `cpu.max` is absent when the cpu
        controller is not enabled for that cgroup. The caller treats a missing
        limit file as "no limit", which is correct.
        """
        ...

    def snapshot(self) -> CgroupSnapshot:
        """Read everything once. One pass, so the numbers are consistent.

        Reading memory and CPU in separate passes means `--watch` can show a
        memory figure from before a spike and a CPU figure from after it.
        """
        ...


def detect_version(mount: Path = CGROUP_MOUNT) -> int:
    """2 for cgroup v2. Raises for anything else.

    Raises:
        CgroupV1Detected: the mount exists but has no `cgroup.controllers`.
        NotACgroup: no mount at all.
    """
    raise NotImplementedError


def find_cgroup_path(
    pid: int | None = None,
    *,
    proc_root: Path = Path("/proc"),
) -> str:
    """The cgroup path for `pid` (or the current process when None).

    Read `/proc/[pid]/cgroup`, which under v2 is one line: `0::/some/path`.

    **Inside a container with its own cgroup namespace the path is often just
    `/`** - the container sees itself at the root of its own view. That is not an
    error and not a failure to find anything; it means "my cgroup is the root of
    what I can see", and joining `/` onto the mount gives exactly the right
    directory.

    Raises:
        ProcessLookupError: no such pid.
    """
    raise NotImplementedError


class LiveCgroupSource:
    """Reads a real `/sys/fs/cgroup`, or a fixture tree shaped like one."""

    def __init__(self, root: Path, *, cgroup_path: str = "/") -> None:
        self._root = root
        self._cgroup_path = cgroup_path

    @property
    def directory(self) -> Path:
        """The mount joined with the cgroup path.

        Careful: `Path("/sys/fs/cgroup") / "/system.slice/x.scope"` gives
        `/system.slice/x.scope` - a leading-slash operand **replaces** the whole
        path rather than appending. Strip the leading slash first. This is the
        most common five-minute bug in this exercise.
        """
        raise NotImplementedError

    def read_text(self, relative: str) -> str:
        raise NotImplementedError

    def snapshot(self) -> CgroupSnapshot:
        raise NotImplementedError


__all__ = [
    "CGROUP_MOUNT",
    "V2_MARKER",
    "CgroupSource",
    "CgroupV1Detected",
    "LiveCgroupSource",
    "NotACgroup",
    "detect_version",
    "find_cgroup_path",
]
