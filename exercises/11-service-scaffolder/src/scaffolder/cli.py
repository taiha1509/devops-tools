"""Command-line interface.

Standalone here as `scaffold`; wired into E10 as `plat new service` once both
work. Keeping the engine independently runnable is what lets you finish this
exercise without E10 being done.

YOUR JOB: implement `new_service`, `check`, and `list_templates`.
"""

from __future__ import annotations

from pathlib import Path
from typing import Annotated

import typer

app = typer.Typer(
    add_completion=False,
    no_args_is_help=True,
    help="Generate services that are production-ready on day one.",
)


@app.command("new")
def new_service(
    name: Annotated[str, typer.Argument(help="Service name, e.g. payments-api.")],
    template: Annotated[str, typer.Option(help="Template to use.")] = "python-fastapi",
    team: Annotated[str, typer.Option(help="Owning team. Goes into CODEOWNERS.")] = "",
    target: Annotated[
        Path | None, typer.Option(help="Where to write. Defaults to ./<name>.")
    ] = None,
    dry_run: Annotated[bool, typer.Option("--dry-run", help="Print the file tree only.")] = False,
) -> None:
    """Generate a new service.

    Example:

        scaffold new payments-api --template python-fastapi --team billing

    Order of operations, and it matters:

        1. validate the spec and the target - **all** problems reported at once
        2. render every file in memory
        3. only then write anything

    Exit codes: 0 generated, 1 unexpected failure, 2 validation failed.
    """
    raise NotImplementedError


@app.command("check")
def check(
    service_dir: Annotated[
        Path,
        typer.Argument(exists=True, file_okay=False, help="An existing scaffolded service."),
    ],
    show_all: Annotated[bool, typer.Option("--all", help="Include up-to-date files.")] = False,
) -> None:
    """Report how far an existing service has drifted from its template.

    Example:

        scaffold check services/payments-api

    Exit 1 on drift so this runs in CI on a schedule across every repository.
    That is the difference between a curiosity and fleet management.

    When the stamped version is behind the current template, say so first and
    prominently - "generated from python-fastapi 1.2.0, current is 1.3.0" tells
    the reader that the drift is the template moving on rather than someone
    editing their files, and those need opposite responses.
    """
    raise NotImplementedError


@app.command("templates")
def list_templates() -> None:
    """List available templates and their versions.

    Example:

        scaffold templates
    """
    raise NotImplementedError


__all__ = ["app", "check", "list_templates", "new_service"]
