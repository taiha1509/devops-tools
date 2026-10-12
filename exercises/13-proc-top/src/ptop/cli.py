"""Command-line interface.

YOUR JOB: implement `list_processes`, `top`, and `show`.
"""

from __future__ import annotations

from pathlib import Path
from typing import Annotated

import typer

app = typer.Typer(
    add_completion=False,
    no_args_is_help=True,
    help="Processes, read from /proc. A small ps and top, built from the same files they read.",
)

ROOT_OPTION = typer.Option(
    help="Directory standing in for /proc. Defaults to /proc; tests point it at a fixture tree.",
)


@app.command("list")
def list_processes(
    sort: Annotated[str, typer.Option(help="rss | pid | cpu")] = "rss",
    limit: Annotated[int, typer.Option(help="Rows to show. 0 for all.")] = 15,
    root: Annotated[Path, ROOT_OPTION] = Path("/proc"),
) -> None:
    """One snapshot, like `ps aux`.

    Example:

        ptop list --sort rss --limit 15

    **No CPU% column in this mode**, or a column showing the lifetime average
    clearly labelled as such. A single snapshot cannot produce an interval
    percentage, and this is where most reimplementations quietly lie - they put
    a plausible number under "CPU%" and it means something different from `top`'s.

    Report the skipped counts in a footer when either is non-zero: "41 processes
    (2 vanished, 0 inaccessible)". That footer is the difference between a tool
    you trust and one whose row count you cannot explain.
    """
    raise NotImplementedError


@app.command("top")
def top(
    interval: Annotated[float, typer.Option(help="Seconds between samples.")] = 2.0,
    iterations: Annotated[int, typer.Option(help="Frames to print. 0 for forever.")] = 5,
    per_core: Annotated[
        bool,
        typer.Option("--per-core/--whole-machine", help="100% = one core, or the whole box."),
    ] = True,
    root: Annotated[Path, ROOT_OPTION] = Path("/proc"),
) -> None:
    """CPU% over an interval, like `top -b`.

    Example:

        ptop top --interval 2 --iterations 5

    `--per-core` is the default because **`top` and `htop` both work that way**:
    100% means one core, so a 4-thread process shows nearly 400%. State it in
    this help text explicitly - the brief asks for it, and a user who assumes
    the other convention will read a saturated box as a quarter busy.

    There is **no first frame**. `top` prints one immediately with lifetime
    averages, which is why its first screen is misleading; this tool waits one
    interval and prints a real measurement. If you choose to match `top` instead,
    label that frame.
    """
    raise NotImplementedError


@app.command("show")
def show(
    pid: Annotated[int, typer.Argument(help="Process ID.")],
    root: Annotated[Path, ROOT_OPTION] = Path("/proc"),
) -> None:
    """Everything about one process.

    Example:

        ptop show 1234

    Exit codes: 0 found, 1 no such process, 2 misuse.
    """
    raise NotImplementedError


__all__ = ["app", "list_processes", "show", "top"]
