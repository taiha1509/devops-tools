"""Command-line interface.

YOUR JOB: implement `run`.
"""

from __future__ import annotations

from pathlib import Path
from typing import Annotated

import typer

app = typer.Typer(
    add_completion=False,
    no_args_is_help=True,
    help="A tiny process supervisor. Forwards signals, reaps children, decodes exit codes.",
)


@app.command()
def run(
    config: Annotated[
        Path,
        typer.Option(exists=True, dir_okay=False, readable=True, help="procs.yaml"),
    ],
    stop_timeout: Annotated[
        float | None,
        typer.Option(help="Override stop_timeout_seconds."),
    ] = None,
) -> None:
    """Start every process in the config and supervise them.

    Example:

        minivisor run --config procs.yaml

    Exit codes - and this tool's own exit code is read by Docker, so it is an API:

        0  every child exited cleanly
        1  at least one child exited non-zero or was killed
        2  misuse: bad config, unreadable file

    **Install the signal handlers before starting any child.** A SIGTERM
    arriving in the window between the first spawn and the handler install is
    handled by the default disposition - which for PID 1 means *ignored*, so the
    stop request is lost entirely and you wait out the full grace period.

    Same JSON formatter as E01. One event per start, exit, restart and shutdown,
    with the decoded exit code and signal name on the exit events - `{"event":
    "process.exited", "name": "web", "shell_code": 137, "signal": "SIGKILL"}` is
    the log line that answers "why did my container die" without anyone having
    to remember what 137 means.
    """
    raise NotImplementedError


__all__ = ["app", "run"]
