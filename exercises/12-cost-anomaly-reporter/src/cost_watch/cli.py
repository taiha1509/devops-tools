"""Command-line interface.

YOUR JOB: implement `report` and `backfill`.
"""

from __future__ import annotations

from pathlib import Path
from typing import Annotated

import typer

app = typer.Typer(
    add_completion=False,
    no_args_is_help=True,
    help="Catch spend regressions in days instead of at month close.",
)


@app.command()
def report(
    lookback: Annotated[str, typer.Option(help="Window, e.g. 14d.")] = "14d",
    post: Annotated[str | None, typer.Option(help="Where to post: slack. Omit to print.")] = None,
    accounts: Annotated[
        Path | None,
        typer.Option(exists=True, dir_okay=False, help="Accounts YAML, as in E04."),
    ] = None,
    for_day: Annotated[
        str | None, typer.Option(help="Analyse this day. Defaults to yesterday.")
    ] = None,
    min_delta_usd: Annotated[float, typer.Option(help="Dollar floor for reporting.")] = 50.0,
    cache_dir: Annotated[Path | None, typer.Option(help="Cache historical cost data here.")] = None,
) -> None:
    """Analyse recent spend and report anomalies.

    Example:

        cost-watch report --lookback 14d --post slack

    **Defaults to yesterday, not today.** Today's Cost Explorer data is
    incomplete and revised for up to 24 hours, so analysing it reports a drop
    every single morning - the most embarrassing false positive available here.

    Exit codes:

        0  ran successfully, with or without anomalies. Finding anomalies is the
           job working, not failing - a non-zero exit here would page someone
           every time the tool succeeded.
        1  partial: ran, reported, but some accounts were unreachable. Visible to
           the scheduler without discarding a useful report.
        2  misuse, or the report could not be delivered. Undelivered is misuse of
           the whole exercise: a report nobody received does not exist.

    Emit the heartbeat on **every** path, including failures.
    """
    raise NotImplementedError


@app.command()
def backfill(
    start: Annotated[str, typer.Option(help="First day, YYYY-MM-DD.")],
    end: Annotated[str, typer.Option(help="Last day, YYYY-MM-DD, inclusive.")],
    cache_dir: Annotated[Path | None, typer.Option(help="Cache historical cost data here.")] = None,
) -> None:
    """Re-run the analysis over a historical range.

    Example:

        cost-watch backfill --start 2026-03-01 --end 2026-03-31

    **Idempotent and re-runnable**, which buys two things: a failed scheduled run
    just runs again, and you can answer "when did this actually start?" after the
    fact - which is exactly the question the problem statement could not answer
    about 4 March.

    Note `--end` is inclusive here while Cost Explorer's own `End` is exclusive.
    That mismatch is deliberate - a CLI should take the dates a human means - but
    it has to be converted in exactly one place or every result shifts by a day.
    """
    raise NotImplementedError


__all__ = ["app", "backfill", "report"]
