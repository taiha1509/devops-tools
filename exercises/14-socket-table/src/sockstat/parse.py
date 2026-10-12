"""Parsing `/proc/net/tcp` and `/proc/net/tcp6`. Pure.

YOUR JOB: implement `parse_net_tcp`.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from sockstat.models import Socket


def parse_net_tcp(text: str, *, ipv6: bool = False) -> list[Socket]:
    """Parse the socket table.

    The format, which has a header line you must skip (wrapped here to fit; it
    is one line per socket in the file)::

          sl  local_address rem_address   st tx_queue rx_queue tr tm->when
                 retrnsmt   uid  timeout inode
           0: 0100007F:1F90 00000000:0000 0A 00000000:00000000 00:00000000
                 00000000  1000        0 29123 1 ...

    Columns by index after `.split()`, with the header skipped:

        0  sl             the row number, with a trailing colon. Not useful.
        1  local_address  hex IP:PORT
        2  rem_address    hex IP:PORT
        3  st             hex state
        7  uid
        9  inode          the join key for the fd map

    Things that will catch you:

        * **Column 0 has a trailing colon** (`0:`). Harmless if you ignore it,
          an `int()` crash if you do not.
        * The columns after `inode` vary between kernels. Index from the **left**
          and never use a negative index - `fields[-1]` is a different thing on
          different machines.
        * A **blank trailing line** is normal. Skip empty lines rather than
          letting `fields[1]` raise.
        * `inode` is `0` for `TIME_WAIT` rows. Not a parse error - the socket
          genuinely belongs to no process. Keep the row; `state.is_orphan`
          explains it.
        * `ipv6=True` only changes how the address half decodes. The column
          layout is identical, so this should be one parameter threaded to
          `decode_address`, not a second parser.

    Returns:
        Sockets in file order. `pid` and `command` are None - the fd join is a
        separate pass, because it costs a walk of every process and the caller
        may not need it.
    """
    raise NotImplementedError


__all__ = ["parse_net_tcp"]
