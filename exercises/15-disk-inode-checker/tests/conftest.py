"""Pytest fixtures for the disk checker.

The statvfs builders and the three pages-as-numbers live in `statfixtures.py`
next door - tests import those directly. This file holds only what pytest
injects.
"""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

import pytest

from statfixtures import FakeStatSource

if TYPE_CHECKING:
    from collections.abc import Callable

    from diskcheck.models import StatvfsResult

FIXTURES = Path(__file__).parent / "fixtures"


@pytest.fixture
def mountinfo_text() -> str:
    """The captured mountinfo, including a mount point with a space in it and a
    line with two optional fields before the `-` separator."""
    return (FIXTURES / "mountinfo").read_text()


@pytest.fixture
def stat_source() -> Callable[..., FakeStatSource]:
    def _make(
        by_mount: dict[str, StatvfsResult],
        *,
        unreadable: set[str] | None = None,
    ) -> FakeStatSource:
        return FakeStatSource(by_mount, unreadable=unreadable)

    return _make
