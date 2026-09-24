from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Protocol

import pytest

from logjanitor.models import Artifact

# A fixed reference time. Age policies are tested against a value we control, not
# against the wall clock - that is why `now` is a parameter everywhere in this
# codebase rather than something the code reads for itself.
NOW = datetime(2026, 9, 21, 12, 0, tzinfo=UTC)


class MakeArtifact(Protocol):
    def __call__(self, key: str, *, days_old: float = ..., size: int = ...) -> Artifact: ...


@pytest.fixture
def now() -> datetime:
    return NOW


@pytest.fixture
def make_artifact() -> MakeArtifact:
    def _make(key: str, *, days_old: float = 0, size: int = 100) -> Artifact:
        return Artifact(key=key, size_bytes=size, modified_at=NOW - timedelta(days=days_old))

    return _make
