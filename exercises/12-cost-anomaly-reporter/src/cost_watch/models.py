"""Core types. Given to you complete; everything else is a stub.

The model that carries the exercise is `AnomalyKind`. Week-over-week percentage
change is the obvious starting point and it will drown you in false positives -
weekends differ from weekdays, month-end batch jobs spike, and a service costing
$0.40 that doubles is not news. Each kind below is a false-positive class with a
name, which is the first step to suppressing it on purpose rather than by
fiddling with a threshold until the noise stops.
"""

from __future__ import annotations

from datetime import date
from enum import StrEnum

from pydantic import BaseModel, ConfigDict

UNTAGGED = "__untagged__"
"""Owner for spend with no cost-allocation tag.

Its own line item, reported prominently. "$14,000 of untagged spend" is a
**finding**, not a gap in your tool - it means nobody can be asked about that
money. Burying it in an "other" bucket is the single easiest way to make this
report useless.
"""


class AnomalyKind(StrEnum):
    SPIKE = "spike"  # a real step change
    NEW_SERVICE = "new_service"  # was zero, now is not
    SUSTAINED_TREND = "sustained_trend"  # small daily rises that compound
    DROP = "drop"  # cheaper, and still worth knowing


class Severity(StrEnum):
    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"


class DailyCost(BaseModel):
    """One day, one service, one account, one owner's worth of spend."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    day: date
    service: str
    account_id: str = ""
    owner: str = UNTAGGED
    amount_usd: float = 0.0

    @property
    def is_weekend(self) -> bool:
        """Saturday or Sunday. The simplest seasonality signal there is.

        Deliberately on the model rather than buried in the detector: weekday
        seasonality is the first false-positive class you will hit, on the very
        first Monday the report runs.
        """
        return self.day.weekday() >= 5


class Anomaly(BaseModel):
    """One finding, with everything a reader needs to act on it."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    service: str
    owner: str
    kind: AnomalyKind
    severity: Severity
    day: date
    # Both the absolute and the relative change. Reporting only the percentage is
    # how a $0.40 service doubling outranks a $4,000 one rising 15%.
    baseline_usd: float
    current_usd: float
    delta_usd: float
    delta_pct: float | None = None  # None when the baseline was zero
    detail: str = ""

    def sort_key(self) -> tuple[float, str]:
        """By absolute dollars, descending. Not by percentage.

        Someone skims the first three lines of this report. They have to be the
        three that cost the most money.
        """
        return (-abs(self.delta_usd), self.service)


class Report(BaseModel):
    """The whole report, including what it could not see."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    generated_for: date
    lookback_days: int
    anomalies: tuple[Anomaly, ...] = ()
    total_usd: float = 0.0
    untagged_usd: float = 0.0
    # Accounts whose Cost Explorer was unavailable. E04's lesson, restated: the
    # report covers the rest and is clearly marked partial, rather than failing.
    unavailable_accounts: tuple[str, ...] = ()
    api_requests_made: int = 0

    @property
    def partial(self) -> bool:
        return bool(self.unavailable_accounts)
