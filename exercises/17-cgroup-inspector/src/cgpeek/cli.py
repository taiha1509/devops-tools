"""Command-line interface.

YOUR JOB: implement `main`.
"""

from __future__ import annotations

from pathlib import Path
from typing import Annotated

import typer

app = typer.Typer(
    add_completion=False,
    help="What a container limit actually is: cgroup v2 memory, CPU quota and throttling.",
)


@app.command()
def main(
    pid: Annotated[int | None, typer.Option(help="Inspect this process's cgroup.")] = None,
    watch: Annotated[
        float | None,
        typer.Option(help="Re-sample every N seconds and show deltas."),
    ] = None,
    iterations: Annotated[int, typer.Option(help="Frames in --watch mode. 0 for forever.")] = 0,
    cgroup_root: Annotated[
        Path,
        typer.Option(help="Directory standing in for /sys/fs/cgroup."),
    ] = Path("/sys/fs/cgroup"),
    proc_root: Annotated[
        Path,
        typer.Option(help="Directory standing in for /proc."),
    ] = Path("/proc"),
) -> None:
    """Inspect a cgroup's limits, usage and pressure.

    Examples:

        cgpeek                    # the current process's cgroup
        cgpeek --pid 1234         # another process's cgroup
        cgpeek --watch 2          # re-sample every 2s and show deltas

    Exit codes:

        0  reported successfully
        1  no such process, or the cgroup directory is unreadable
        2  **cgroup v1 detected**, or no cgroup filesystem at all, or misuse

    v1 gets its own clear message rather than a guess. v1 splits controllers
    across hierarchies with different filenames and different semantics
    (`memory.limit_in_bytes`, `cpu.cfs_quota_us`), so a tool that half-works on
    it produces numbers that look right and are not - strictly worse than
    refusing. Modern Docker, containerd and Kubernetes nodes are all v2.

    On a Mac there is no cgroup filesystem at all, so this exits 2 locally and
    that is correct. The tests run against fixture trees; the live runs happen in
    a Linux container, per `LINUX.md`.
    """
    raise NotImplementedError


__all__ = ["app", "main"]
