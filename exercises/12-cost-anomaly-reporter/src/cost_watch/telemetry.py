"""OpenTelemetry for the reporter itself, and the heartbeat.

**This is the phase's real content.** Your own tooling deserves the
observability you would demand of a service - and a scheduled job is harder to
debug than a service, not easier, because nobody is watching it.

YOUR JOB: implement `configure_telemetry`, `emit_heartbeat`, `check_heartbeat`.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from datetime import datetime, timedelta

    from mypy_boto3_cloudwatch import CloudWatchClient
    from opentelemetry.trace import Tracer

SERVICE_NAME = "cost-watch"

HEARTBEAT_METRIC = "CostWatchHeartbeat"
"""The metric whose **absence** is the alert.

A reporter that silently stops running is worse than no reporter, because
everyone assumes silence means no anomalies. This is the asymmetry that makes
scheduled jobs dangerous: a service that stops serving pages someone within
minutes; a cron job that stops running is noticed a quarter later, when somebody
asks why nobody flagged the thing that was flagged.

CloudWatch specifics that matter for alerting on absence:

    * The alarm must treat missing data as **breaching**
      (`TreatMissingData: breaching`). The default is `missing`, which does not
      alarm - so the obvious configuration is precisely the one that does not
      work.
    * Emit the metric even on a failed run, with a separate success/failure
      dimension. "It ran and failed" and "it did not run" are different problems
      and you want to tell them apart from the alarm alone.
"""


def configure_telemetry(*, otlp_endpoint: str | None = None) -> Tracer:
    """Set up tracing and metrics. A no-op exporter when no endpoint is given.

    The no-op path matters: this has to run on a laptop with no collector, and
    an import-time failure on a missing `OTEL_EXPORTER_OTLP_ENDPOINT` makes the
    tool untestable.

    What to instrument, and why these:

        * a span per phase - `collect`, `detect`, `render`, `post`. When the job
          starts taking twenty minutes you want to know which phase grew.
        * a counter for **API requests made**. This is the one that catches the
          day someone refactors `fetch_daily_costs` into a per-service loop and
          turns the reporter into a cost anomaly.
        * a gauge for dollars analysed, so you can spot the run that silently
          analysed one account instead of fourteen - the numbers look plausible
          either way, which is E06's silent-wrongness problem wearing a FinOps
          hat.
        * span attributes for the lookback window and the thresholds used, so a
          trace explains why a given run found what it found.
    """
    raise NotImplementedError


def emit_heartbeat(
    client: CloudWatchClient,
    *,
    now: datetime,
    succeeded: bool = True,
    anomalies_found: int = 0,
) -> None:
    """Record that the reporter ran.

    Emit on **every** run including failures - see the note on `HEARTBEAT_METRIC`
    about distinguishing "ran and failed" from "did not run".
    """
    raise NotImplementedError


def check_heartbeat(
    client: CloudWatchClient,
    *,
    now: datetime,
    max_age: timedelta,
) -> bool:
    """Has the reporter run recently enough? False means alert.

    Exists so the acceptance criterion is testable: *"missing heartbeat triggers
    an alert path - test it by not running it."* That phrasing is the whole
    point. Most monitoring is tested by making it fire; absence-based monitoring
    can only be tested by **not** doing something, which is why almost nobody
    tests it and why it is almost always misconfigured.
    """
    raise NotImplementedError


__all__ = [
    "HEARTBEAT_METRIC",
    "SERVICE_NAME",
    "check_heartbeat",
    "configure_telemetry",
    "emit_heartbeat",
]
