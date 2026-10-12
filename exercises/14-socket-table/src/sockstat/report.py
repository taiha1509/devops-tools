"""Orchestration: read both tables, join to pids, assemble.

YOUR JOB: implement `build_table` and `summarise`.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from sockstat.models import SocketTable, TcpState
    from sockstat.source import ProcSource


def build_table(
    source: ProcSource,
    *,
    include_ipv6: bool = True,
    resolve_pids: bool = True,
) -> SocketTable:
    """Read `/proc/net/tcp` (+ `tcp6`), optionally join to owning processes.

    `resolve_pids=False` skips the fd walk entirely. Worth having: the walk is
    the expensive part, and `sockstat summary` does not need it. On a box with
    2,000 processes the difference is immediate-versus-noticeable.

    `/proc/net/tcp6` may be **absent** on an IPv6-disabled kernel. That is not an
    error - skip it. Raising would make the tool useless on exactly the hosts
    where it is simplest.

    Read both tables **before** walking the fds. The socket tables are a snapshot
    each; interleaving the reads widens the window in which a socket closes and
    disappears from one source but not the other.
    """
    raise NotImplementedError


def summarise(table: SocketTable) -> dict[TcpState, int]:
    """Counts per state, like `ss -s`.

    Include states with a count of **zero**? Decide and be consistent. Showing
    `FIN_WAIT2: 0` is noise most of the time; omitting it means a reader cannot
    tell "none" from "this tool does not track that state". `ss -s` omits them.

    The number people come here for is `TIME_WAIT`. Alongside it, report how
    close you are to **ephemeral port exhaustion** if you did the stretch goal -
    28,000 `TIME_WAIT` sockets is fine with a 28,232-port range and a disaster
    with a 4,000-port one, and the raw count alone cannot tell you which.
    """
    raise NotImplementedError


__all__ = ["build_table", "summarise"]
