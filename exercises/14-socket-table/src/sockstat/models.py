"""Core data types. Given to you complete; everything else is a stub."""

from __future__ import annotations

from dataclasses import dataclass
from enum import IntEnum


class TcpState(IntEnum):
    """The `st` column of `/proc/net/tcp`, as hex values.

    An `Enum`, not a dict of strings - the brief is explicit about this, and the
    reason is that these are a closed set defined by the kernel. An unknown value
    should be an error you can see, not a `KeyError` in the middle of a loop or a
    silent `"UNKNOWN"` string that gets counted in your summary.
    """

    ESTABLISHED = 0x01
    SYN_SENT = 0x02
    SYN_RECV = 0x03
    FIN_WAIT1 = 0x04
    FIN_WAIT2 = 0x05
    TIME_WAIT = 0x06
    CLOSE = 0x07
    CLOSE_WAIT = 0x08
    LAST_ACK = 0x09
    LISTEN = 0x0A
    CLOSING = 0x0B

    @property
    def is_orphan(self) -> bool:
        """True for states where the socket belongs to no process any more.

        `TIME_WAIT` sockets have **inode 0**: the process is long gone and the
        kernel is holding the tuple for 2*MSL (60s on Linux) so a late duplicate
        packet cannot be mistaken for part of a new connection. This is why
        `ss -p` shows nothing for them, and why 28,000 of them is not necessarily
        a leak - but *is* a problem if you are near ephemeral port exhaustion.
        """
        return self in {TcpState.TIME_WAIT, TcpState.CLOSE}


@dataclass(frozen=True, slots=True)
class Socket:
    """One row of `/proc/net/tcp` or `/proc/net/tcp6`, decoded."""

    local_address: str
    local_port: int
    remote_address: str
    remote_port: int
    state: TcpState
    uid: int
    inode: int
    # Filled in by the fd join, which is a separate pass. None means "we could
    # not determine it", which is **different** from "no process owns it" -
    # the latter is `state.is_orphan`. Conflating them is how you report a
    # permission problem as an orphaned socket.
    pid: int | None = None
    command: str | None = None

    @property
    def is_listening(self) -> bool:
        return self.state is TcpState.LISTEN

    def sort_key(self) -> tuple[int, int, str]:
        return (int(self.state), self.local_port, self.local_address)


@dataclass(frozen=True, slots=True)
class SocketTable:
    """Every socket, plus an honest account of what could not be seen.

    `inaccessible_pids` is the field that keeps this tool honest. Running as
    non-root, you cannot read other users' `/proc/[pid]/fd/`, so their sockets
    appear with `pid=None`. Silently pretending those processes have no sockets
    is the failure mode; `ss -p` has the same limitation and shows nothing for
    them, so matching that behaviour **and saying so** is the goal.
    """

    sockets: tuple[Socket, ...] = ()
    inaccessible_pids: int = 0

    def counts_by_state(self) -> dict[TcpState, int]:
        """For `sockstat summary`, like `ss -s`."""
        out: dict[TcpState, int] = {}
        for sock in self.sockets:
            out[sock.state] = out.get(sock.state, 0) + 1
        return out
