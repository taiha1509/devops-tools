"""The `/proc` seam. Same shape as E13's, plus symlink reading.

YOUR JOB: implement `LiveProcSource`.
"""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING, Protocol, runtime_checkable

if TYPE_CHECKING:
    from collections.abc import Iterator


@runtime_checkable
class ProcSource(Protocol):
    """Read-only access to something shaped like `/proc`."""

    def read_text(self, relative: str) -> str:
        """Read a `/proc` file. Raises `FileNotFoundError` if absent."""
        ...

    def pids(self) -> Iterator[int]:
        """Numeric directory entries, ascending. Non-numeric entries skipped."""
        ...

    def list_fds(self, pid: int) -> Iterator[tuple[int, str]]:
        """Yield `(fd_number, symlink_target)` for one process.

        **The target, not the resolved path.** `Path.readlink()` gives you
        `socket:[29123]`; `Path.resolve()` tries to follow it, fails because it is
        not a real path, and you get nothing useful. This distinction is the
        single easiest way to spend an hour on this exercise.

        Raises:
            PermissionError: another user's process, and you are not root. The
                caller counts these - see `fdmap.build_inode_map`.
        """
        ...

    def command_for(self, pid: int) -> str:
        """The process's command, for display. `comm` is enough here."""
        ...


class LiveProcSource:
    """Reads a real `/proc`, or a fixture tree shaped like one.

    For fixtures, the socket fds are **dangling symlinks** - `os.symlink` to the
    literal string `socket:[29123]`, pointing at nothing. That is fine and is
    exactly what the real ones are: the kernel synthesises those targets, and no
    such path exists on a real box either.
    """

    def __init__(self, root: Path = Path("/proc")) -> None:
        self._root = root

    def read_text(self, relative: str) -> str:
        raise NotImplementedError

    def pids(self) -> Iterator[int]:
        raise NotImplementedError

    def list_fds(self, pid: int) -> Iterator[tuple[int, str]]:
        raise NotImplementedError

    def command_for(self, pid: int) -> str:
        raise NotImplementedError


__all__ = ["LiveProcSource", "ProcSource"]
