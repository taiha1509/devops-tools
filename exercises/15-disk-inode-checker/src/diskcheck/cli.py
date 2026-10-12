"""Command-line interface.

YOUR JOB: implement `usage`, `deleted_open`, and `inode_hogs_cmd`.
"""

from __future__ import annotations

from pathlib import Path
from typing import Annotated

import typer

app = typer.Typer(
    add_completion=False,
    no_args_is_help=True,
    help="Disk, inodes, and the space that isn't there. Tells the three 'disk full' pages apart.",
)

ROOT_OPTION = typer.Option(help="Directory standing in for /proc. Defaults to /proc.")


@app.command()
def usage(
    warn: Annotated[float, typer.Option(help="Warn above this percent.")] = 80.0,
    crit: Annotated[float, typer.Option(help="Exit 1 above this percent.")] = 90.0,
    include_tmpfs: Annotated[bool, typer.Option("--tmpfs", help="Include tmpfs mounts.")] = False,
    root: Annotated[Path, ROOT_OPTION] = Path("/proc"),
) -> None:
    """Per-mount usage, bytes and inodes - like `df -h` and `df -i` together.

    Examples:

        diskcheck usage
        diskcheck usage --warn 80 --crit 90

    Show **both budgets in one table**. Having to run two commands is why nobody
    checks inodes, and page #1 (`No space left on device` at 40% full) is
    entirely an inode problem.

    Show both free numbers when they differ: available-to-users and
    free-including-root's-reserve. That column is page #3, and the whole value of
    this tool over `df` is printing it.

    Exit codes: 0 clear, 1 a **crit** crossed, 2 misuse. A warn is information,
    not a page - see `evaluate.exit_code_for`.
    """
    raise NotImplementedError


@app.command("deleted-open")
def deleted_open(
    root: Annotated[Path, ROOT_OPTION] = Path("/proc"),
) -> None:
    """Files deleted but still held open, with PID and size. **Page #2.**

    Example:

        diskcheck deleted-open

    This is the answer to "`df` says 100%, `du` says half that". Almost always a
    log rotated without `copytruncate`: the directory entry is gone so `du`
    cannot see it, the process still holds the fd so the blocks are not freed,
    and it grows forever.

    Print the **fix** alongside the finding, because the fix is not obvious and
    deleting something is not it: the space comes back when the fd closes, which
    means restarting (or `HUP`-ing) the holding process. `truncate -s 0
    /proc/<pid>/fd/<n>` also works and is the one people do not know.

    Say how many processes you could not inspect. Without root this list is a
    lower bound, and presenting a lower bound as an answer is how the real 50GB
    file stays hidden.
    """
    raise NotImplementedError


@app.command("inode-hogs")
def inode_hogs_cmd(
    path: Annotated[Path, typer.Argument(exists=True, file_okay=False, help="Where to scan.")],
    top: Annotated[int, typer.Option(help="How many to show.")] = 10,
) -> None:
    """Directories with the most entries. Answers "what ate the inodes?"

    Example:

        diskcheck inode-hogs /var --top 10

    Direct entries per directory, not recursive totals - you are hunting the one
    directory with 900,000 files in it, and a recursive count just reports the
    root of the tree every time.

    This one **walks the filesystem**, so it is slow and it is the only command
    here that is. Say so if it is taking a while rather than looking hung.
    """
    raise NotImplementedError


__all__ = ["app", "deleted_open", "inode_hogs_cmd", "usage"]
