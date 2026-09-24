"""Command-line interface.

The JSON logging setup below is given to you complete - it is the pattern, not the
exercise. `main` is the stub.

YOUR JOB: implement `main`.
"""

from __future__ import annotations

import json
import logging
import sys
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Annotated, Any

import typer

from logjanitor.models import RetentionPolicy, SweepResult
from logjanitor.policy import select_for_deletion
from logjanitor.store import LocalStore

app = typer.Typer(
    add_completion=False,
    help="Prune build artifacts by age and total size. Dry-run by default.",
)

log = logging.getLogger("logjanitor")


class JsonFormatter(logging.Formatter):
    """One JSON object per line. The log message is the event name."""

    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, Any] = {
            "ts": datetime.fromtimestamp(record.created, tz=UTC).isoformat(),
            "level": record.levelname.lower(),
            "event": record.getMessage(),
        }
        fields = getattr(record, "fields", None)
        if isinstance(fields, dict):
            payload.update(fields)
        return json.dumps(payload, default=str)


def configure_logging() -> None:
    """Send structured logs to stdout.

    stdout, not stderr, and not a file: in a container or a CI runner, stdout is
    the only stream anything reliably collects.
    """
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(JsonFormatter())
    log.handlers = [handler]
    log.setLevel(logging.INFO)
    log.propagate = False


@app.command()
def main(
    root: Annotated[
        Path,
        typer.Option(
            exists=True,
            file_okay=False,
            dir_okay=True,
            readable=True,
            help="Directory to sweep.",
        ),
    ],
    max_age_days: Annotated[
        int | None,
        typer.Option(help="Delete artifacts strictly older than this many days."),
    ] = None,
    max_total_bytes: Annotated[
        int | None,
        typer.Option(help="Keep the retained total at or below this many bytes."),
    ] = None,
    keep_minimum: Annotated[
        int,
        typer.Option(help="Never leave fewer than this many artifacts."),
    ] = 0,
    protect: Annotated[
        list[str] | None,
        typer.Option(help="fnmatch pattern never to delete. Repeatable."),
    ] = None,
    apply: Annotated[
        bool,
        typer.Option("--apply", help="Actually delete. Without this, nothing is removed."),
    ] = False,
) -> None:
    """Sweep ROOT according to the retention rules.

    Exit codes are an API - a CI gate reads them:

        0  swept successfully (including "nothing to do")
        1  expected runtime failure, e.g. the store became unreadable mid-sweep
        2  misuse - typer returns this for bad arguments, and you should too when
           neither --max-age-days nor --max-total-bytes is given. Sweeping with no
           retention rule is not a no-op request, it is a mistake, and silently
           doing nothing hides it.

    Note the asymmetry with `policy.select_for_deletion`, which tolerates an empty
    policy and returns []. The pure function stays permissive; the interface
    refuses. That split is intentional - library code should not decide what
    counts as user error.
    """
    configure_logging()
    # Validate args
    if not max_age_days and not max_total_bytes:
        log.error(
            "sweep.invalid_arguments",
            extra={"fields": {"reason": "need --max-age-days or --max-total-bytes"}},
        )
        sys.exit(2)

    try:
        protect_patterns: tuple[str, ...] = tuple(protect) if protect else ()
        max_age = timedelta(days=max_age_days) if max_age_days is not None else None
        policy = RetentionPolicy(
            protect_patterns=protect_patterns,
            keep_minimum=keep_minimum,
            max_age=max_age,
            max_total_bytes=max_total_bytes,
        )
        artifact_store = LocalStore(root)
        all_artifacts = list(artifact_store.list_artifacts())
        now = datetime.now(tz=UTC)
        deletable_artifacts = list(select_for_deletion(all_artifacts, policy, now=now))

        # `deleted` is the same list either way - a dry run reports exactly what an
        # --apply run would remove. Only the store call below is conditional.
        sweep_rs = SweepResult(len(all_artifacts), dry_run=not apply, deleted=deletable_artifacts)
        for art in sweep_rs.deleted:
            if apply:
                artifact_store.delete(art)
            log.info(
                "artifact.deleted",
                extra={
                    "fields": {
                        "key": art.key,
                        "size_bytes": art.size_bytes,
                        "dry_run": sweep_rs.dry_run,
                    }
                },
            )

        log.info(
            "sweep.summary",
            extra={
                "fields": {
                    "scanned": sweep_rs.scanned,
                    "deleted": len(sweep_rs.deleted),
                    "reclaimed_bytes": sweep_rs.reclaimed_bytes,
                    "dry_run": sweep_rs.dry_run,
                }
            },
        )
    except Exception as exc:
        log.error("sweep.failed", extra={"fields": {"error": str(exc)}})
        sys.exit(1)

    sys.exit(0)


__all__ = ["app", "configure_logging", "main"]
