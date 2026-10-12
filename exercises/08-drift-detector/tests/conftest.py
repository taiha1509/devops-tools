from __future__ import annotations

import json
from pathlib import Path
from typing import TYPE_CHECKING, Any

import httpx
import pytest

if TYPE_CHECKING:
    from collections.abc import Callable

FIXTURES = Path(__file__).parent / "fixtures" / "plans"


@pytest.fixture
def plan() -> Callable[[str], dict[str, Any]]:
    """Load a committed plan fixture by stem, e.g. `plan("replace")`.

    See `fixtures/plans/README.md` for what each one covers and how to capture
    real output to replace them.
    """

    def _plan(name: str) -> dict[str, Any]:
        path = FIXTURES / f"{name}.json"
        if not path.exists():
            available = sorted(p.stem for p in FIXTURES.glob("*.json"))
            msg = f"no fixture {name!r}; have {available}"
            raise FileNotFoundError(msg)
        return json.loads(path.read_text())  # type: ignore[no-any-return]

    return _plan


@pytest.fixture
def plan_path() -> Callable[[str], Path]:
    """The path to a fixture, for the CLI tests."""

    def _path(name: str) -> Path:
        return FIXTURES / f"{name}.json"

    return _path


@pytest.fixture
def client() -> httpx.Client:
    """Stubbed at the transport layer by respx. No GitHub token, no network."""
    return httpx.Client(timeout=5.0)
