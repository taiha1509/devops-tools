"""The provisioning seam. Deliberately shallow - the exercise is the interface.

E01's `ArtifactStore` idea again, and by now that should feel like a habit rather
than a trick. `LocalStateBackend` (a JSON file) is enough to build the whole CLI
against; swapping in something real later must not change a single line of
`cli.py`.

YOUR JOB: implement `LocalStateBackend`.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Protocol, runtime_checkable

if TYPE_CHECKING:
    from collections.abc import Iterable, Iterator
    from datetime import datetime, timedelta
    from pathlib import Path

    from plat.models import Environment


@runtime_checkable
class Backend(Protocol):
    """Whatever actually makes environments exist."""

    def create(
        self,
        *,
        name: str,
        template: str,
        owner: str,
        ttl: timedelta | None,
        now: datetime,
    ) -> Environment:
        """Provision one. Raises `EnvironmentExists` if the name is taken."""
        ...

    def list(self, *, owner: str | None = None) -> Iterable[Environment]:
        """Every environment, or just one owner's. Sorted by name for stable output."""
        ...

    def get(self, name: str) -> Environment:
        """One by name. Raises `EnvironmentNotFound`."""
        ...

    def destroy(self, name: str) -> None:
        """Tear one down. **Idempotent** - destroying something already gone is a
        success. E01's rule, and it matters more here: the TTL reaper and a human
        can race, and the reaper must not page anyone for winning."""
        ...

    def logs(self, name: str, *, follow: bool = False) -> Iterator[str]:
        """Stream log lines. A generator so `--follow` does not buffer.

        Returning a list here would make `--follow` meaningless, and that is the
        kind of interface mistake that is expensive to reverse once nine teams
        depend on the output shape.
        """
        ...


class LocalStateBackend:
    """A JSON file on disk. Enough to build the entire CLI against.

    Two things to get right even in a toy backend, because both are interface
    decisions rather than implementation details:

        * **Write atomically.** Write to a temp file in the same directory and
          `Path.replace` it. A half-written state file loses every environment,
          and `plat` crashing mid-write is not a hypothetical.
        * **Store `ttl` as seconds, not as a pretty string.** "48h" is an input
          format; the stored value should be unambiguous. Parsing your own output
          back is a tax you pay forever.
    """

    def __init__(self, state_path: Path) -> None:
        self._state_path = state_path

    def create(
        self,
        *,
        name: str,
        template: str,
        owner: str,
        ttl: timedelta | None,
        now: datetime,
    ) -> Environment:
        raise NotImplementedError

    def list(self, *, owner: str | None = None) -> Iterable[Environment]:
        raise NotImplementedError

    def get(self, name: str) -> Environment:
        raise NotImplementedError

    def destroy(self, name: str) -> None:
        raise NotImplementedError

    def logs(self, name: str, *, follow: bool = False) -> Iterator[str]:
        raise NotImplementedError


__all__ = ["Backend", "LocalStateBackend"]
