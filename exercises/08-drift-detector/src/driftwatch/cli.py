"""Command-line interface.

YOUR JOB: implement `analyse`.
"""

from __future__ import annotations

from pathlib import Path
from typing import Annotated

import typer

app = typer.Typer(
    add_completion=False,
    no_args_is_help=True,
    help="Classify a Terraform plan by blast radius and report it where reviewers look.",
)


@app.command()
def analyse(
    plan_json: Annotated[
        Path,
        typer.Argument(
            exists=True,
            dir_okay=False,
            readable=True,
            help="Output of `terraform show -json tf.plan`.",
        ),
    ],
    severity_map: Annotated[
        Path | None,
        typer.Option(exists=True, dir_okay=False, help="YAML overrides for the severity map."),
    ] = None,
    fail_on: Annotated[
        str,
        typer.Option(help="none | changes | destructive. What exits non-zero."),
    ] = "destructive",
    post_comment: Annotated[
        bool,
        typer.Option("--post-comment", help="Upsert the summary onto the PR."),
    ] = False,
    repo: Annotated[
        str | None, typer.Option(help="owner/name. Defaults to $GITHUB_REPOSITORY.")
    ] = None,
    pr_number: Annotated[int | None, typer.Option(help="PR number to comment on.")] = None,
) -> None:
    """Analyse a plan file.

    Exit codes drive the gate:

        0  clean - no changes
        1  changes present, none destructive
        2  destructive changes present **or** misuse

    Note the collision: 2 means both "destructive" and "bad arguments". That is
    E01's exit-code convention running into a three-outcome tool. Decide what to
    do about it - separate the misuse case onto a different code, or document the
    overlap - and write down which, because a CI gate cannot distinguish "you
    passed a bad flag" from "do not deploy this" otherwise.

    `--fail-on` controls which of those is actually non-zero:

        destructive  (default) only replaces and destroys block
        changes      any change blocks - for a repo that should only ever see
                     no-op plans outside a release
        none         report only, never block. The right setting for the first
                     two weeks, while people learn whether to trust the severity
                     map.

    **Must work with no GitHub token present.** `--post-comment` without
    credentials is misuse and should say so; running *without* `--post-comment`
    on a laptop must work completely, because that is how you will debug every
    severity-map argument anyone ever has with you.
    """
    raise NotImplementedError


__all__ = ["analyse", "app"]
