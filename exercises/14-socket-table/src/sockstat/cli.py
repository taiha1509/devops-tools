"""Command-line interface.

YOUR JOB: implement `list_sockets`, `summary`, and `who_has`.
"""

from __future__ import annotations

from pathlib import Path
from typing import Annotated

import typer

app = typer.Typer(
    add_completion=False,
    no_args_is_help=True,
    help="Sockets, read from /proc/net. A small ss, built from the files ss reads.",
)

ROOT_OPTION = typer.Option(help="Directory standing in for /proc. Defaults to /proc.")


@app.command("list")
def list_sockets(
    state: Annotated[str | None, typer.Option(help="Filter by state, e.g. listen.")] = None,
    port: Annotated[int | None, typer.Option(help="Only sockets touching this port.")] = None,
    ipv6: Annotated[bool, typer.Option("--ipv6/--no-ipv6", help="Include tcp6.")] = True,
    root: Annotated[Path, ROOT_OPTION] = Path("/proc"),
) -> None:
    """List sockets, like `ss -tanp`.

    Examples:

        sockstat list --state listen
        sockstat list --port 5432

    **Report inaccessible processes in a footer** when the count is non-zero:
    "412 sockets (18 processes not readable - run as root to see their owners)".
    Without that line, a non-root run looks like a complete picture with some
    mysteriously unowned sockets, and the reader draws the wrong conclusion
    during an incident.
    """
    raise NotImplementedError


@app.command("summary")
def summary(
    root: Annotated[Path, ROOT_OPTION] = Path("/proc"),
) -> None:
    """Counts per TCP state, like `ss -s`.

    Example:

        sockstat summary

    Skips the fd walk - it is the expensive part and this command does not need
    owners.

    `TIME_WAIT` is the number people came for. Half the team thinks 28,000 of
    them is the bug and half thinks it is normal; both are right depending on the
    ephemeral port range, so print that range alongside if you did the stretch
    goal.
    """
    raise NotImplementedError


@app.command("who-has")
def who_has(
    port: Annotated[int, typer.Argument(help="Port number.")],
    root: Annotated[Path, ROOT_OPTION] = Path("/proc"),
) -> None:
    """Which process holds this port.

    Example:

        sockstat who-has 8080

    Answers "address already in use". Three distinct outcomes, and they need
    different messages:

        * a **listener** found -> the pid and command. Exit 0.
        * only `TIME_WAIT` rows on that port -> "nothing is listening; N sockets
          in TIME_WAIT, which will clear in up to 60s". **This is the answer** to
          a bind failure with nothing listening, and printing "not found" instead
          sends the reader looking for a process that does not exist.
        * nothing at all -> exit 1.

    If the owner is unreadable, say *that* rather than "not found": "port 8080 is
    held by a process owned by another user (run as root)".
    """
    raise NotImplementedError


__all__ = ["app", "list_sockets", "summary", "who_has"]
