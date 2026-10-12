"""Fixtures for the cost reporter.

Everything here builds `DailyCost` series from a compact spec, because the five
cases the brief demands are all *shapes over time* rather than single values:

    a genuine anomaly, a weekend dip, a month-end spike, a brand-new service,
    and a tiny-but-doubled service

The last three are the false-positive classes. Your detector has to report the
first one and stay quiet about the others, and the false-positive rate you
document is measured against exactly this data.
"""

from __future__ import annotations

from datetime import date, timedelta
from typing import TYPE_CHECKING

import pytest

from cost_watch.models import UNTAGGED, DailyCost

if TYPE_CHECKING:
    from collections.abc import Callable

# A Monday, so weekday arithmetic in the tests is readable.
TARGET_DAY = date(2026, 9, 21)
ACCOUNT = "111111111111"


@pytest.fixture
def target_day() -> date:
    return TARGET_DAY


@pytest.fixture
def series() -> Callable[..., list[DailyCost]]:
    """Build a daily series for one service, ending at `TARGET_DAY`.

    `amounts[-1]` is the target day. `weekend_factor` scales Saturdays and
    Sundays, which is how the weekend-dip fixture is built without hand-writing
    fourteen values.
    """

    def _series(
        service: str,
        amounts: list[float],
        *,
        owner: str = "billing",
        weekend_factor: float = 1.0,
        end: date = TARGET_DAY,
    ) -> list[DailyCost]:
        out: list[DailyCost] = []
        for offset, amount in enumerate(reversed(amounts)):
            day = end - timedelta(days=offset)
            scaled = amount * (weekend_factor if day.weekday() >= 5 else 1.0)
            out.append(
                DailyCost(
                    day=day,
                    service=service,
                    account_id=ACCOUNT,
                    owner=owner,
                    amount_usd=round(scaled, 2),
                )
            )
        return list(reversed(out))

    return _series


@pytest.fixture
def genuine_anomaly(series) -> list[DailyCost]:
    """The case that must be reported.

    Steady at ~$400/day, then $2,800 - a log-retention misconfiguration writing
    400GB/day. Large in dollars and in percentage, on a weekday.
    """
    return series("AmazonCloudWatch", [400] * 20 + [2800])


@pytest.fixture
def weekend_dip(series) -> list[DailyCost]:
    """False positive #1, and the first one you will hit - on the first Monday.

    Spend is 40% lower at weekends. Compared against "yesterday", every Monday
    looks like a +150% spike and every Saturday like a -60% drop. A same-weekday
    baseline removes both.
    """
    return series("AmazonEC2", [1000] * 21, weekend_factor=0.4)


@pytest.fixture
def month_end_spike(series) -> list[DailyCost]:
    """False positive #2, and the one a same-weekday baseline does not fix.

    A batch job on the last day of the month. The target day here is the 30th, so
    the spike lands on it - which is the hard case, not the convenient one.
    """
    return series("AmazonAthena", [100] * 29 + [1800], end=date(2026, 9, 30))


@pytest.fixture
def brand_new_service(series) -> list[DailyCost]:
    """False positive #3 - or rather, the case that must be reported *differently*.

    Zero for twenty days, then $600. The percentage change is infinite, and a
    naive implementation either crashes on the division or reports it as the
    biggest anomaly in history every day forever. `NEW_SERVICE` with
    `delta_pct=None` is the answer.
    """
    return series("AmazonBedrock", [0] * 20 + [600])


@pytest.fixture
def tiny_but_doubled(series) -> list[DailyCost]:
    """False positive #4. $0.40 to $0.85 - a 112% increase that is not news.

    Small services have the most volatile percentages, which is why a
    percentage-only detector reports mostly rounding errors. The dollar floor
    kills this whole class in one line.
    """
    return series("AmazonRoute53", [0.40] * 20 + [0.85])


@pytest.fixture
def sustained_trend(series) -> list[DailyCost]:
    """The case the problem statement actually describes.

    Each day ~8% above the last. No single day trips a spike threshold; two
    months later the bill is 30% up and nobody can say when it started.
    """
    amounts = [500.0]
    for _ in range(20):
        amounts.append(round(amounts[-1] * 1.08, 2))
    return series("AmazonS3", amounts)


@pytest.fixture
def untagged_spend(series) -> list[DailyCost]:
    """Spend nobody can be asked about. A finding, not a gap in the tool."""
    return series("AmazonEC2", [700] * 21, owner=UNTAGGED)


@pytest.fixture
def all_fixtures(
    genuine_anomaly,
    weekend_dip,
    month_end_spike,
    brand_new_service,
    tiny_but_doubled,
    sustained_trend,
    untagged_spend,
) -> list[DailyCost]:
    """Everything at once - the set the documented false-positive rate is measured
    against. Exactly two of these seven should be reported on the target day."""
    return [
        *genuine_anomaly,
        *weekend_dip,
        *month_end_spike,
        *brand_new_service,
        *tiny_but_doubled,
        *sustained_trend,
        *untagged_spend,
    ]
