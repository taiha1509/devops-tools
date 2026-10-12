"""The CLI, which is also the Action's entrypoint. One code path, both contexts.

YOUR JOB: implement `check`.
"""

from __future__ import annotations

from pathlib import Path
from typing import Annotated

import typer

app = typer.Typer(
    add_completion=False,
    no_args_is_help=True,
    help="Decide whether a deploy is allowed. Runs identically locally and in CI.",
)


@app.command()
def check(
    environment: Annotated[
        str,
        typer.Option(help="Target environment, e.g. production."),
    ],
    freeze_windows: Annotated[
        Path | None,
        typer.Option(exists=True, dir_okay=False, help="Freeze config YAML."),
    ] = None,
    error_budget_threshold: Annotated[
        float | None,
        typer.Option(help="Block when remaining error budget is below this fraction (0.0-1.0)."),
    ] = None,
    metrics_endpoint: Annotated[
        str | None,
        typer.Option(help="URL returning the remaining error budget."),
    ] = None,
    incidents_endpoint: Annotated[
        str | None,
        typer.Option(help="URL returning open incidents."),
    ] = None,
    override: Annotated[
        bool,
        typer.Option("--override", help="Bypass the gates. Always audited."),
    ] = False,
    override_reason: Annotated[
        str | None,
        typer.Option(help="Required with --override."),
    ] = None,
    actor: Annotated[
        str | None,
        typer.Option(help="Who is deploying. Defaults to $GITHUB_ACTOR."),
    ] = None,
) -> None:
    """Run every configured gate and report whether the deploy may proceed.

    Exit codes - a deploy job reads these, so they are an API:

        0  allowed (including allowed-by-override)
        1  blocked by at least one gate
        2  misuse: --override without --override-reason, a threshold outside
           0.0-1.0, an unreadable freeze file, or --error-budget-threshold with
           no --metrics-endpoint to read

    **Gates are opt-in.** A gate with no configuration does not run and does not
    block - otherwise adopting this Action in a repo with no incident API would
    be impossible. But say so in the output: "error_budget: not configured" is
    information, a silent omission is not. Someone will eventually believe they
    are protected by a gate they never configured.

    Behaviour differences between local and CI should be limited to **where
    output goes**, never to what the decision is. `$GITHUB_OUTPUT` and
    `$GITHUB_ACTOR` being absent means "running locally", not "degraded".
    """
    raise NotImplementedError


__all__ = ["app", "check"]
