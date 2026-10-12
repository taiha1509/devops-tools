from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import TYPE_CHECKING

import pytest
from typer.testing import CliRunner

from plat.backend import LocalStateBackend
from plat.models import Environment

if TYPE_CHECKING:
    from collections.abc import Callable
    from pathlib import Path

NOW = datetime(2026, 9, 21, 12, 0, tzinfo=UTC)
OWNER = "hant"

TEMPLATES = ("preview", "staging", "perf")


@pytest.fixture
def now() -> datetime:
    return NOW


@pytest.fixture
def runner() -> CliRunner:
    """`typer.testing.CliRunner` throughout.

    The acceptance criterion is explicit: tests cover the **CLI surface**, not
    just the internals. A tool whose interface is the exercise cannot be tested
    only through its library functions.
    """
    return CliRunner()


@pytest.fixture
def backend(tmp_path: Path) -> LocalStateBackend:
    return LocalStateBackend(tmp_path / "state.json")


@pytest.fixture
def make_env() -> Callable[..., Environment]:
    """Build an Environment at a known age."""

    def _make(
        name: str,
        *,
        hours_old: float = 0,
        ttl_hours: float | None = 48,
        owner: str = OWNER,
        template: str = "preview",
    ) -> Environment:
        return Environment(
            name=name,
            template=template,
            owner=owner,
            created_at=NOW - timedelta(hours=hours_old),
            ttl=None if ttl_hours is None else timedelta(hours=ttl_hours),
        )

    return _make
