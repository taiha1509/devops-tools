"""Stat fixtures: builders, the three pages as numbers, and a fake StatSource.

Separate from `conftest.py` because these are values tests import, not fixtures
pytest injects. (No `__init__.py` in `tests/` - pytest puts this directory on
`sys.path`, so `from statfixtures import ...` works.)

`statvfs` results are not files, so there is nothing to capture - the
`FakeStatSource` below plays that part, keyed by mount point. That is why
`sources.py` defines a `StatSource` protocol rather than a root path: the thing
being faked is a syscall, not a file.

The three pages from the brief each get a fixture, with numbers chosen so the
assertions are exact rather than approximate.
"""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

from diskcheck.models import StatvfsResult

if TYPE_CHECKING:
    pass

FIXTURES = Path(__file__).parent / "fixtures"

BLOCK = 4096  # 4 KiB, the ext4 default


def statvfs(
    *,
    blocks: int,
    bfree: int,
    bavail: int,
    files: int = 1_000_000,
    ffree: int = 900_000,
    favail: int | None = None,
) -> StatvfsResult:
    """Build a StatvfsResult with sane defaults for the fields a test ignores."""
    return StatvfsResult(
        f_bsize=BLOCK,
        f_frsize=BLOCK,
        f_blocks=blocks,
        f_bfree=bfree,
        f_bavail=bavail,
        f_files=files,
        f_ffree=ffree,
        f_favail=ffree if favail is None else favail,
    )


# --- The three pages, as numbers ---------------------------------------------

HEALTHY = statvfs(blocks=1_000_000, bfree=600_000, bavail=550_000)
"""40% used, inodes fine. The boring case, and the one that must stay quiet."""

INODES_EXHAUSTED = statvfs(
    blocks=1_000_000,
    bfree=700_000,
    bavail=650_000,
    files=250_000,
    ffree=2_500,
)
"""**Page #1.** Bytes at ~31%, inodes at 99%.

`No space left on device` while `df -h` says the volume is a third full. A
million 1-byte cache files. A tool that only looks at bytes calls this healthy.
"""

ROOT_RESERVE = statvfs(blocks=100, bfree=10, bavail=5)
"""**Page #3**, with numbers small enough to check by hand.

100 blocks, 90 used, 10 free to root, **5 free to everyone else** - the ext4 5%
reserve. `df` reports 95%; `used / total` reports 90%. The app user has 5 blocks
and root has 10, which is why freeing "5%" does not help the app.

    df's way:      90 / (90 + 5) = 94.7% -> rounds to 95%
    the naive way: 90 / 100       = 90.0%
"""

FULL = statvfs(blocks=1_000_000, bfree=0, bavail=0)
"""Genuinely full. Both formulas agree at 100%, which is why this case proves
nothing on its own - it is here so a passing suite is not just the easy case."""

EMPTY_PSEUDO = statvfs(blocks=0, bfree=0, bavail=0, files=0, ffree=0)
"""A pseudo-filesystem that got past the filter. `0/0` is where the
division-by-zero crash lives, and it must be skipped rather than reported."""


class FakeStatSource:
    """A `StatSource` backed by a dict. Raises for mounts it does not know."""

    def __init__(
        self,
        by_mount: dict[str, StatvfsResult],
        *,
        unreadable: set[str] | None = None,
    ) -> None:
        self._by_mount = by_mount
        self._unreadable = unreadable or set()

    def statvfs(self, path: str) -> StatvfsResult:
        if path in self._unreadable:
            msg = f"[Errno 13] Permission denied: {path!r}"
            raise PermissionError(msg)
        if path not in self._by_mount:
            msg = f"[Errno 2] No such file or directory: {path!r}"
            raise OSError(msg)
        return self._by_mount[path]
