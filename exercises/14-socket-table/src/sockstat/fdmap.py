"""Socket -> PID. **A join, not a lookup.** This is the other half of the lesson.

There is no file that says "socket 29123 belongs to pid 1217". What exists is:

    * `/proc/net/tcp` row 29123  -> an inode number
    * `/proc/[pid]/fd/7`         -> a symlink whose target is `socket:[29123]`

So you build the inode -> pid map **once** by walking every process's `fd`
directory, then join. Doing it per socket means re-walking `/proc` for every row,
which on a box with 28,000 `TIME_WAIT` sockets is why your tool appears to hang.

YOUR JOB: implement `build_inode_map` and `attach_pids`.
"""

from __future__ import annotations

import re
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Sequence

    from sockstat.models import Socket
    from sockstat.source import ProcSource

SOCKET_LINK = re.compile(r"^socket:\[(\d+)\]$")
"""The symlink target shape. Given to you complete.

Anchored at both ends deliberately: an unanchored search would also match
`socket:[123]` appearing inside some other path, and a wrong pid attribution is
worse than none - it sends someone to the wrong process during an incident.
"""


def build_inode_map(source: ProcSource) -> tuple[dict[int, tuple[int, str]], int]:
    """Walk every process's fds once. Returns the map and a skip count.

    For each pid, for each entry in `/proc/[pid]/fd/`, read the symlink target.
    Targets matching `SOCKET_LINK` give you `inode -> (pid, command)`.

    The error handling **is** the exercise here:

        * `PermissionError` on another user's process when not root. **Count it
          and report it** - do not silently pretend that process has no sockets.
          `ss -p` has exactly the same limitation and shows nothing for them,
          which is honest; a tool that shows nothing *and* does not say why is
          not.
        * `FileNotFoundError` / `ProcessLookupError`: the process exited
          mid-walk. Skip, and this one does not need counting separately - it is
          E13's "that is Tuesday" case.
        * `OSError` on reading an individual link: skip that fd, keep the
          process. A single weird fd must not lose you the other forty.

    One inode maps to one process in practice, but a socket fd can be
    **inherited by a fork** or passed over a Unix socket, in which case two pids
    hold it. Decide what you report - first wins, lowest pid, or all of them -
    and write it in `DECISIONS.md`. `ss` shows all of them, in `users:(...)`.

    Returns:
        `(inode -> (pid, command), inaccessible_process_count)`
    """
    raise NotImplementedError


def attach_pids(
    sockets: Sequence[Socket],
    inode_map: dict[int, tuple[int, str]],
) -> list[Socket]:
    """Join sockets to owning processes.

    **Inode 0 is never looked up.** Those are `TIME_WAIT` rows belonging to no
    process; a lookup would be a guaranteed miss, and if inode 0 ever *did*
    appear in your map it would attribute every orphan to one unlucky process.

    A socket whose inode is not in the map keeps `pid=None`. That means "we could
    not determine it" and is distinct from `state.is_orphan` meaning "nothing
    owns it". Reporting the first as the second is how a permissions problem
    gets diagnosed as a socket leak.
    """
    raise NotImplementedError


def who_has_port(sockets: Sequence[Socket], port: int) -> list[Socket]:
    """Every socket on `port`, listeners first.

    Answers "address already in use". Order matters: the **listener** is almost
    always what the asker wants, and on a busy box it would otherwise be buried
    under a few hundred `ESTABLISHED` connections to the same port.

    An empty result with `TIME_WAIT` rows present on that port is itself the
    answer to "why can't I bind?" - worth making visible rather than printing
    "nothing found".
    """
    raise NotImplementedError


__all__ = ["SOCKET_LINK", "attach_pids", "build_inode_map", "who_has_port"]
