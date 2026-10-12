"""Hex address decoding. Pure, tiny, and the entire lesson of the exercise.

**Byte order is the point.** The port and the address in `/proc/net/tcp` are
printed in *different* orders, and the reason is that one is a network-order
value the kernel formats as a number while the other is a raw in-memory `u32`
dumped as hex.

YOUR JOB: implement every function.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from sockstat.models import TcpState


def decode_port(hex_port: str) -> int:
    """`"1F90"` -> `8080`.

    Plain big-endian hex. `int(hex_port, 16)` and you are done - the port is the
    easy half, and it being easy is what makes the address surprising.
    """
    raise NotImplementedError


def decode_ipv4(hex_addr: str) -> str:
    """`"0100007F"` -> `"127.0.0.1"`.

    **Not `1.0.0.127`.** This is the test the brief insists on, and it is the
    whole exercise in one line.

    What is happening: the kernel prints the address as the raw `u32` sitting in
    memory, formatted as hex. On x86 and ARM - little-endian - the bytes of
    `127.0.0.1` are stored `7F 00 00 01` reversed, i.e. `01 00 00 7F`, which
    prints as `0100007F`.

    So: take the bytes, **reverse them**, then format. `socket.inet_ntop` after
    reordering, or `bytes.fromhex(h)[::-1]`, or `struct.unpack("<I", ...)`.
    Whichever you pick, the test is the same.

    Worth knowing: this is endianness of the *host*, not of the protocol. On a
    big-endian machine `/proc/net/tcp` would print `7F000001` for the same
    address. You will never meet one, and knowing why the caveat exists is the
    difference between understanding this and memorising it.
    """
    raise NotImplementedError


def decode_ipv6(hex_addr: str) -> str:
    """32 hex chars -> an IPv6 string.

    `"00000000000000000000000001000000"` -> `"::1"`.

    The format is **four 32-bit words, each in host byte order** - so you reverse
    within each 4-byte group, not across the whole 16 bytes. Reversing all
    sixteen gives a plausible-looking address that is completely wrong, which is
    the worst kind of bug to have in a tool you are using to diagnose something
    else.

    Two cases that must both work, and are in the acceptance criteria:

        `::1`                 loopback
        `::ffff:10.0.0.5`     an **IPv4-mapped** address. This is how a
                              dual-stack listener on 0.0.0.0 shows up in
                              `/proc/net/tcp6`, and if you do not handle it you
                              will conclude a service is not listening when it
                              is. `socket.inet_ntop(AF_INET6, ...)` renders the
                              mapped form for you once the bytes are right.
    """
    raise NotImplementedError


def decode_address(hex_pair: str, *, ipv6: bool = False) -> tuple[str, int]:
    """Split `"0100007F:1F90"` into `("127.0.0.1", 8080)`.

    One function so callers never have to remember which half needs reversing.
    """
    raise NotImplementedError


def decode_state(hex_state: str) -> TcpState:
    """`"0A"` -> `TcpState.LISTEN`.

    Raises:
        ValueError: an unknown state value. Loudly, with the raw value in the
            message. A silent `"UNKNOWN"` string would be counted in
            `sockstat summary` as if it were a real state, and then your totals
            disagree with `ss -s` for no visible reason.
    """
    raise NotImplementedError


__all__ = ["decode_address", "decode_ipv4", "decode_ipv6", "decode_port", "decode_state"]
