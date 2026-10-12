"""The `/proc` seam: a Protocol plus a live implementation rooted at a path.

This is E01's `ArtifactStore` again, and it is what lets the whole tool be tested
on a Mac. In production `root` is `/proc`. In tests it is `tmp_path`, populated
with text captured from a real Linux box.

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

    def pids(self) -> Iterator[int]:
        """Every numeric directory entry, ascending.

        Non-numeric entries (`self`, `meminfo`, `net`, ...) are skipped. A
        `int(entry)` without a guard crashes on the first one.
        """
        ...

    def read_text(self, relative: str) -> str:
        """Read a `/proc` file as text. Raises `FileNotFoundError` if gone."""
        ...

    def read_bytes(self, relative: str) -> bytes:
        """Read raw bytes. Needed for `cmdline`, which is NUL-separated."""
        ...


class LiveProcSource:
    """Reads a real `/proc` (or a fixture tree shaped like one)."""

    def __init__(self, root: Path = Path("/proc")) -> None:
        self._root = root

    def pids(self) -> Iterator[int]:
        raise NotImplementedError

    def read_text(self, relative: str) -> str:
        raise NotImplementedError

    def read_bytes(self, relative: str) -> bytes:
        raise NotImplementedError


# --- The vanishing-process rule ---------------------------------------------
#
# A PID returned by `pids()` can be gone before you open its `stat`. **That is
# not an error, it is Tuesday** - on a busy box it happens on most runs.
#
# `FileNotFoundError` and `ProcessLookupError` mean "skip this process". They
# never end the run. Catch them at the *per-process* level in `report.py`, not
# around the whole loop: wrapping the loop means one dying process silently
# truncates your output at that point, which looks like a quiet box.
#
# Count the skips and report them. `ptop` showing 41 processes where `ps` showed
# 43 is a fine outcome *if you can say why*, and that sentence is the deliverable
# for this exercise's DECISIONS.md.
#
# `PermissionError` is different and worth distinguishing: on a real box,
# non-root cannot read other users' `/proc/[pid]/status`. Skipping those silently
# makes the tool appear to work while hiding half the processes - count them
# separately and say so, which is what E14 does for its socket→PID join too.


__all__ = ["LiveProcSource", "ProcSource"]
