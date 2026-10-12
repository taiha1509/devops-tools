"""Fixtures for the cgroup inspector.

Four captured layouts under `fixtures/`, matching the acceptance criteria:

    v2-limited/     512 MiB memory, 0.5 CPU, 38% throttled - the pod from the
                    problem statement
    v2-limited-t1/  the same cgroup one interval later, with deltas chosen to be
                    exact: throttle rate 0.5, usage 0.5 cores over 2.0s, and
                    `oom_kill` 1 -> 2
    v2-unlimited/   `max` for memory, CPU and pids
    v1/             a v1 layout, which must exit 2 rather than be guessed at

macOS has no `/sys/fs/cgroup`, which is why `source.py` takes a root.
"""

from __future__ import annotations

from pathlib import Path

import pytest

FIXTURES = Path(__file__).parent / "fixtures"

MIB = 1024 * 1024

# The interval between the two v2-limited snapshots. Chosen so the derived
# numbers come out exact rather than approximate.
ELAPSED_SECONDS = 2.0


@pytest.fixture
def limited_root() -> Path:
    """A 512 MiB / 0.5 CPU container, throttled in 38% of periods."""
    return FIXTURES / "v2-limited"


@pytest.fixture
def limited_root_t1() -> Path:
    """The same cgroup, one interval later."""
    return FIXTURES / "v2-limited-t1"


@pytest.fixture
def unlimited_root() -> Path:
    """`max` everywhere - the no-limit parse path."""
    return FIXTURES / "v2-unlimited"


@pytest.fixture
def v1_root() -> Path:
    """A v1 layout. No `cgroup.controllers`, different filenames."""
    return FIXTURES / "v1"


@pytest.fixture
def proc_root() -> Path:
    """Stand-in `/proc` with four `cgroup` files: host path, container `/`, and a
    v1 multi-line one."""
    return FIXTURES / "proc"


@pytest.fixture
def elapsed() -> float:
    return ELAPSED_SECONDS
