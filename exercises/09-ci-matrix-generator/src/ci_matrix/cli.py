"""Command-line interface.

YOUR JOB: implement `plan`.
"""

from __future__ import annotations

from pathlib import Path
from typing import Annotated

import typer

app = typer.Typer(
    add_completion=False,
    no_args_is_help=True,
    help="Compute the minimum set of CI jobs a change requires.",
)


@app.command()
def plan(
    base: Annotated[
        str,
        typer.Option(help="Base ref or SHA to diff against, e.g. the PR's base.sha."),
    ],
    repo_root: Annotated[
        Path,
        typer.Option(exists=True, file_okay=False, help="Repo root."),
    ] = Path(),
    head: Annotated[str, typer.Option(help="Head ref.")] = "HEAD",
    explain_output: Annotated[
        bool,
        typer.Option("--explain", help="Print why each service was included or excluded."),
    ] = False,
    job_limit: Annotated[
        int,
        typer.Option(help="Max matrix jobs before degrading."),
    ] = 256,
    github_output: Annotated[
        Path | None,
        typer.Option(help="Append matrix=<json> here. Defaults to $GITHUB_OUTPUT."),
    ] = None,
) -> None:
    """Emit the matrix JSON on stdout, and `matrix=<json>` to $GITHUB_OUTPUT.

    **stdout carries the payload and nothing else.** Diagnostics go to stderr or
    the log; a stray print lands inside what `fromJson` has to parse, and the
    error GitHub gives you for that is unhelpful. `--explain` writes to stderr for
    the same reason.

    Exit codes:

        0  a plan was produced (including the empty plan - a docs-only PR is a
           success, not a failure)
        1  the graph is unusable: a dependency cycle, or an unknown dependency
        2  misuse - bad refs, missing base, unreadable repo root

    On exit 1, **do not emit a matrix**. A cyclic graph means every closure
    computed from it is suspect, and emitting build-all would hide a real repo
    problem behind a slow CI run forever.

    `git` failures are the exception: those degrade to build-all with
    `degraded=true`, because the safe direction when you cannot tell what changed
    is to build everything. That asymmetry is the subject of the brief's safety
    question and belongs in `DECISIONS.md`.
    """
    raise NotImplementedError


__all__ = ["app", "plan"]
