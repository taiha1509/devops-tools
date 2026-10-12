"""Fixtures for the /proc parsers.

Everything here runs on your Mac, against the captured trees under
`fixtures/proc` and `fixtures/proc-t1`. macOS has no `/proc`, which is exactly
why `source.py` takes a `root`.

The two trees are one process-table snapshot each, taken a notional interval
apart, with **arithmetically clean deltas** so the CPU% test can assert an exact
number instead of a range:

    pid 1 ticks:  225 -> 325      delta   100
    system ticks: 100000 -> 101000  delta 1000

    100 / 1000 * 100 * 1 core = exactly 10.0%
"""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
from typing import TYPE_CHECKING

import pytest

from ptop.source import LiveProcSource

if TYPE_CHECKING:
    from collections.abc import Callable

FIXTURES = Path(__file__).parent / "fixtures"

# Linux's SC_CLK_TCK is 100 on essentially every distro. Passed as a parameter
# everywhere anyway - "almost always" is how you ship a tool that is quietly 4x
# off on an unusual kernel.
CLOCK_TICKS = 100

NOW = datetime(2026, 9, 21, 12, 0, tzinfo=UTC)

# From the fixture's /proc/stat cpu line: 10000 + 0 + 5000 + 80000 + 3000 + 500 + 1500
TOTAL_TICKS_T0 = 100_000
TOTAL_TICKS_T1 = 101_000


@pytest.fixture
def now() -> datetime:
    return NOW


@pytest.fixture
def clock_ticks() -> int:
    return CLOCK_TICKS


@pytest.fixture
def proc_root() -> Path:
    return FIXTURES / "proc"


@pytest.fixture
def proc_root_t1() -> Path:
    return FIXTURES / "proc-t1"


@pytest.fixture
def source(proc_root: Path) -> LiveProcSource:
    return LiveProcSource(root=proc_root)


@pytest.fixture
def source_t1(proc_root_t1: Path) -> LiveProcSource:
    return LiveProcSource(root=proc_root_t1)


@pytest.fixture
def read_fixture(proc_root: Path) -> Callable[[str], str]:
    """Read a file out of the t0 tree, for the pure parser tests."""

    def _read(relative: str) -> str:
        return (proc_root / relative).read_text()

    return _read


@pytest.fixture
def read_fixture_bytes(proc_root: Path) -> Callable[[str], bytes]:
    def _read(relative: str) -> bytes:
        return (proc_root / relative).read_bytes()

    return _read
