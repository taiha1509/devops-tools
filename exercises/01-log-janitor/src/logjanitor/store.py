"""Artifact storage backends.

The `ArtifactStore` protocol is the seam that keeps `sweep()` from caring whether
it is pruning a CI runner's disk or an S3 bucket. Defining that seam now is also
the first taste of the platform-engineering habit Phase 5 builds on: design the
interface others consume, then implement behind it.

YOUR JOB: implement `LocalStore`. `S3Store` is the stretch goal.
"""

from __future__ import annotations

import datetime
from os import DirEntry
from pathlib import Path
import os

from typing import TYPE_CHECKING, Protocol, runtime_checkable

from collections.abc import Iterable
from pathlib import Path

from logjanitor.models import Artifact


@runtime_checkable
class ArtifactStore(Protocol):
    """Anything a janitor can sweep."""

    def list_artifacts(self) -> Iterable[Artifact]:
        """Yield every artifact in the store.

        Keys are store-relative and POSIX-style. Implementations should stream
        rather than materialise where the backend allows it - an S3 prefix can
        hold millions of objects.
        """
        ...

    def delete(self, artifact: Artifact) -> None:
        """Remove one artifact.

        Must be idempotent: deleting something already gone is a success, not an
        error. Unattended tools get re-run, and a crash on the second run is how
        a janitor turns into a pager.
        """
        ...


class LocalStore:
    """A directory tree on disk.

    Files only - directories are structure, not artifacts, and are never listed
    or deleted. Keys are relative to `root`, using forward slashes on every
    platform so protect patterns stay portable.
    """

    def __init__(self, root: Path) -> None:
        self._root = root

    def list_artifacts(self) -> Iterable[Artifact]:
        """Walk `root` recursively and yield one Artifact per file.

        `modified_at` comes from the file's mtime and must be timezone-aware UTC.
        (`datetime.fromtimestamp(ts, tz=UTC)` - the naive overload is a trap and
        ruff's DTZ rules will reject it.)
        """
        def scan(entry: Path, relative_dir: str = "") -> Iterable[Artifact]:
            children = list(os.scandir(entry.absolute()))
            for child in children:
                if child.is_dir():
                    relative_dir += f'{child.name}/'
                    yield from scan(Path(child), relative_dir)
                else:
                    artifact = Artifact(modified_at=datetime.datetime.fromtimestamp(Path.stat(Path(child)).st_mtime).astimezone(), key=f'{relative_dir}{child.name}', size_bytes=Path.stat(Path(child)).st_size)
                    yield artifact
        path = self._root.absolute()

        yield from scan(path)

    def delete(self, artifact: Artifact) -> None:
        """Delete the file for `artifact`. A missing file is not an error."""
        # raise NotImplementedError

        abs_path = f'{self._root}/{artifact.key}'
        if not Path.exists(Path(abs_path)):
            print(f'artifact with key {artifact.key} does not exist')
            return
        if not os.path.isfile(abs_path):
            print(f'artifact with key {artifact.key} is not file type')
            return
        Path(abs_path).unlink()

# --- Stretch goal -----------------------------------------------------------
#
# Add an `S3Store(bucket, prefix)` implementing the same protocol, and test it
# with moto. Things worth getting right, all of which recur in Phase 2:
#
#   * list_objects_v2 truncates. Use a paginator, not a single call. Write a test
#     with more than one page - the fixture is the point of the exercise.
#   * ETags and LastModified come back tz-aware already; do not re-localise them.
#   * delete_objects batches up to 1000 keys. One call per object works and is
#     slow and expensive; batching is what you would actually ship.
#   * A delete on a missing key succeeds silently in S3. Your LocalStore must
#     behave the same way, which is why idempotency is in the protocol contract.
