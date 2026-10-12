"""Fixtures for the socket table.

`fixtures/proc/net/tcp` and `tcp6` are captured-shape tables covering every case
the acceptance criteria name. The fd symlinks are built per-test in `tmp_path`,
because a symlink to `socket:[29123]` is a **dangling** link - git will store it
but cloning it across platforms is fragile, and building it in the test is three
lines.

Dangling is correct, by the way: no such path exists on a real box either. The
kernel synthesises those targets.
"""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

import pytest

from sockstat.source import LiveProcSource

if TYPE_CHECKING:
    from collections.abc import Callable

FIXTURES = Path(__file__).parent / "fixtures"

# Inodes present in the tcp fixture, for building matching fd trees.
LISTENER_INODE = 29123  # 127.0.0.1:8080, LISTEN, uid 1000
PG_LISTENER_INODE = 18442  # 0.0.0.0:5432, LISTEN, uid 0
ESTABLISHED_INODE = 29150


@pytest.fixture
def proc_root() -> Path:
    return FIXTURES / "proc"


@pytest.fixture
def net_tcp(proc_root: Path) -> str:
    return (proc_root / "net" / "tcp").read_text()


@pytest.fixture
def net_tcp6(proc_root: Path) -> str:
    return (proc_root / "net" / "tcp6").read_text()


@pytest.fixture
def fd_tree(tmp_path: Path, proc_root: Path) -> Callable[..., Path]:
    """Build a /proc tree with fd symlinks, for the inode join.

    Copies the net tables in and creates `<pid>/fd/<n> -> socket:[<inode>]` for
    each mapping given. `unreadable_pids` creates a process directory whose `fd`
    is mode 000, which is how you reproduce the PermissionError case without
    needing another user.
    """

    def _build(
        mapping: dict[int, list[int]],
        *,
        commands: dict[int, str] | None = None,
        unreadable_pids: list[int] | None = None,
    ) -> Path:
        root = tmp_path / "proc"
        (root / "net").mkdir(parents=True)
        for name in ("tcp", "tcp6"):
            (root / "net" / name).write_text((proc_root / "net" / name).read_text())

        for pid, inodes in mapping.items():
            fd_dir = root / str(pid) / "fd"
            fd_dir.mkdir(parents=True)
            for n, inode in enumerate(inodes):
                (fd_dir / str(n)).symlink_to(f"socket:[{inode}]")
            # A couple of non-socket fds, which must be skipped rather than
            # crashing the walk or being mistaken for sockets.
            (fd_dir / "90").symlink_to("/dev/null")
            (fd_dir / "91").symlink_to("pipe:[12345]")
            name = (commands or {}).get(pid, f"proc{pid}")
            (root / str(pid) / "comm").write_text(f"{name}\n")

        for pid in unreadable_pids or []:
            fd_dir = root / str(pid) / "fd"
            fd_dir.mkdir(parents=True)
            (fd_dir / "0").symlink_to(f"socket:[{LISTENER_INODE}]")
            (root / str(pid) / "comm").write_text(f"secret{pid}\n")
            fd_dir.chmod(0o000)

        return root

    return _build


@pytest.fixture
def source(proc_root: Path) -> LiveProcSource:
    return LiveProcSource(root=proc_root)
