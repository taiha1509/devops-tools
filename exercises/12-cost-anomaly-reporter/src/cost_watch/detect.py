"""Anomaly detection. Pure, and the actual engineering problem in this exercise.

Week-over-week percentage change is the starting point and it will drown you in
false positives. **Getting the false-positive rate low enough that people keep
reading the report is the work** - a report that cries wolf is muted within two
weeks, and a muted report is worth less than no report, because everyone assumes
silence means no anomalies.

The acceptance criterion is a **number**: your false-positive rate against the
fixture set, documented. Not an adjective.

YOUR JOB: implement everything below.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Iterable, Sequence
    from datetime import date

    from cost_watch.models import Anomaly, DailyCost


@dataclass(frozen=True, slots=True)
class Thresholds:
    """Tuning knobs, all in one place so the write-up can quote them.

    Given to you complete. The values are a starting point, not an answer - the
    whole point of the exercise is to move them against real fixture data and
    record what happened.
    """

    # The dollar floor. A service costing $0.40 that doubles is not news, and it
    # is the single biggest source of noise in a naive implementation: small
    # services have the most volatile percentages.
    min_delta_usd: float = 50.0
    # Relative change needed to report at all.
    min_delta_pct: float = 25.0
    # Consecutive days of smaller rises that together mean something. Three days
    # of +8% matters more than one day of +20% - it is a trend rather than a
    # blip, and it is what the 30%-in-March case actually looked like day to day.
    trend_days: int = 3
    trend_min_pct: float = 5.0
    critical_delta_usd: float = 1000.0


def baseline_for(
    history: Sequence[DailyCost],
    day: date,
    *,
    thresholds: Thresholds,
) -> float:
    """The expected cost for `day`, given history.

    **Compare like with like.** The naive baseline is "yesterday", and it is
    wrong twice a week: Monday against Sunday shows a spike every single Monday,
    and Saturday against Friday shows a drop every single Saturday.

    The cheap fix that removes most of the noise: compare against **the same
    weekday**, averaged over the previous N weeks. Monday against the last three
    Mondays. It needs more history than week-over-week, which is why `--lookback`
    defaults generously.

    Month-end is the harder case and a same-weekday baseline does not fix it: a
    batch job that runs on the last day of the month spikes against any weekday
    baseline. Options are to suppress the last/first N days, to compare against
    the previous month-end, or to accept it and label it. Pick one, and record
    which in `DECISIONS.md` along with what it cost you in missed real anomalies.

    Returns:
        The expected amount. `0.0` when there is no comparable history, which the
        caller must treat as "new service", **not** as "expected zero" - those
        differ, and conflating them makes every genuinely new service a critical
        anomaly forever.
    """
    raise NotImplementedError


def classify(
    current: DailyCost,
    baseline: float,
    *,
    thresholds: Thresholds,
) -> Anomaly | None:
    """Is this day anomalous for this service? None when it is not.

    The order of the checks is the design, because each one suppresses a
    false-positive class:

        1. **New service** (baseline zero, current above the floor). Report as
           `NEW_SERVICE`, never as an infinite percentage increase. `delta_pct`
           is `None` here - that is why the field is optional, and why dividing
           by the baseline without checking is the first bug everyone writes.
        2. **Dollar floor.** Below `min_delta_usd`, stop. Kills the
           tiny-but-doubled class entirely.
        3. **Percentage floor.** Below `min_delta_pct`, stop.
        4. Otherwise `SPIKE` or `DROP` by sign. Report drops too: a service
           costing nothing suddenly is as likely to mean "it broke" as "we
           optimised it".

    Severity from absolute dollars, not percentage. See `Anomaly.sort_key`.
    """
    raise NotImplementedError


def detect_trends(
    history: Sequence[DailyCost],
    *,
    thresholds: Thresholds,
) -> list[Anomaly]:
    """Find sustained small rises that no single-day check would catch.

    This is the one that would have caught the problem statement. A log-retention
    misconfiguration shipped on 4 March does not spike - it adds a constant daily
    cost that grows as data accumulates, each day a few percent above the last.
    Every single-day check passes. Two months later the bill is 30% up and
    nobody can say when it started.

    `trend_days` consecutive days each at least `trend_min_pct` above the
    previous is the simplest useful signal. Report the **whole run** as one
    `SUSTAINED_TREND` anomaly with the cumulative delta, not as three separate
    findings - three findings for one cause is how a report becomes noise.
    """
    raise NotImplementedError


def detect(
    costs: Iterable[DailyCost],
    *,
    target_day: date,
    thresholds: Thresholds | None = None,
) -> list[Anomaly]:
    """Full detection pass over one day, plus trends over the whole window.

    Group by `(service, account_id)` before comparing. Comparing a total across
    services hides a $2,000 rise in one behind a $2,000 fall in another, and
    those are two findings, not zero.

    Returns:
        Anomalies sorted by `Anomaly.sort_key()` - biggest dollar impact first.
        Deduplicated: a service caught by both the single-day and trend checks
        appears once, as the more informative of the two.
    """
    raise NotImplementedError


__all__ = ["Thresholds", "baseline_for", "classify", "detect", "detect_trends"]
