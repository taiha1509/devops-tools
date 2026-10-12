"""Command-line interface: `inventory collect` and `inventory query`.

Two subcommands rather than one, because collection is slow and querying is not -
you collect once and then ask the dataset five different questions. Baking the
query into the collect run would mean a ten-minute sweep per question.

YOUR JOB: implement `collect_cmd` and `query_cmd`.
"""

from __future__ import annotations

from pathlib import Path
from typing import Annotated

import typer

app = typer.Typer(
    add_completion=False,
    no_args_is_help=True,
    help="Sweep every AWS account and region into one queryable dataset.",
)


@app.command("collect")
def collect_cmd(
    accounts: Annotated[
        Path,
        typer.Option(exists=True, dir_okay=False, readable=True, help="Accounts YAML."),
    ],
    output: Annotated[
        Path,
        typer.Option(help="Where to write the inventory JSON."),
    ],
    max_workers: Annotated[
        int,
        typer.Option(help="Concurrent account-region sweeps."),
    ] = 8,
    region: Annotated[
        list[str] | None,
        typer.Option(help="Override the configured regions. Repeatable."),
    ] = None,
) -> None:
    """Sweep the estate and write the dataset.

    Exit codes are an API - a scheduled job reads them:

        0  complete sweep, every account-region reached
        1  **partial** sweep - the dataset was written and some of the estate was
           unreachable. Not 0, because "we looked everywhere" is a different
           claim from "we looked where we could", and a monitoring system needs
           to tell them apart. Not 2, because the output is still useful.
        2  misuse - unreadable config, no accounts configured, unwritable output

    Write the JSON with `model_dump_json(indent=2)` plus a trailing newline, and
    **sort nothing here** - `collect()` already returned sorted data. Sorting in
    two places is how the two sorts eventually disagree.

    Log a final `collect.summary` event with `accounts_requested`,
    `accounts_reached`, `resources`, `failures`, and `partial`.
    """
    raise NotImplementedError


@app.command("query")
def query_cmd(
    dataset: Annotated[
        Path,
        typer.Argument(exists=True, dir_okay=False, readable=True, help="Inventory JSON."),
    ],
    resource_type: Annotated[
        list[str] | None,
        typer.Option(help="Filter by type, e.g. ec2:instance. Repeatable."),
    ] = None,
    account: Annotated[list[str] | None, typer.Option(help="Filter by account ID.")] = None,
    public_ip: Annotated[
        bool | None,
        typer.Option("--public-ip/--no-public-ip", help="Only resources with/without a public IP."),
    ] = None,
    has_tag: Annotated[list[str] | None, typer.Option(help="Tag that must be present.")] = None,
    missing_tag: Annotated[list[str] | None, typer.Option(help="Tag that must be absent.")] = None,
    output_json: Annotated[bool, typer.Option("--json", help="Emit JSON, not a table.")] = False,
) -> None:
    """Ask the dataset a question.

    The brief's motivating query is::

        inventory query inventory.json --public-ip --missing-tag Owner

    **Warn when the dataset is partial.** If the file you are querying was
    written by a run with failures, a count from it is a lower bound, not an
    answer. Say so on stderr before printing results - "0 matching resources"
    from a sweep that could not reach three accounts is the exact shape of a
    misleading security finding.

    Exit codes: 0 results found, 1 no results (so shell `if` works), 2 misuse.
    """
    raise NotImplementedError


__all__ = ["app", "collect_cmd", "query_cmd"]
