"""Cost Explorer access. The one module that costs money to run.

**Cost Explorer charges per API request** - $0.01 each at time of writing, which
sounds like nothing until a naive implementation queries per-service-per-day
across fourteen accounts and makes 20,000 requests a month. A cost reporter that
is itself a cost anomaly is a genuinely funny way to fail and an easy one.

YOUR JOB: implement `fetch_daily_costs` and the cache.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from datetime import date
    from pathlib import Path

    from mypy_boto3_ce import CostExplorerClient

    from cost_watch.models import DailyCost

MAX_GROUP_BY = 2
"""`get_cost_and_usage` accepts at most two GroupBy dimensions.

This constrains the whole design and it is worth knowing before you plan the
queries rather than after. You want service, account **and** owner tag - that is
three - so you need either two passes or a choice. Note which you picked and why.
"""


class CostExplorerUnavailable(Exception):
    """One account's Cost Explorer could not be read.

    E04's lesson again: the report covers the rest and is marked partial. A
    monthly cost report that fails entirely because one account is unreachable
    will be unread for a month.
    """


def fetch_daily_costs(
    client: CostExplorerClient,
    *,
    start: date,
    end: date,
    owner_tag_key: str = "Owner",
    request_counter: list[int] | None = None,
) -> list[DailyCost]:
    """One batched query per window, not one per service per day.

    The call that does it in a single request:

        get_cost_and_usage(
            TimePeriod={"Start": ..., "End": ...},   # inclusive / EXCLUSIVE
            Granularity="DAILY",
            Metrics=["UnblendedCost"],
            GroupBy=[{"Type": "DIMENSION", "Key": "SERVICE"},
                     {"Type": "TAG", "Key": owner_tag_key}],
        )

    Things that will cost you an afternoon each:

        * **`End` is exclusive.** Asking for the 1st to the 7th gives you six
          days. Off-by-one here silently shifts every baseline.
        * **It paginates** via `NextPageToken`, not `NextToken`, and not through
          a botocore paginator in older versions. Check whether
          `client.get_paginator("get_cost_and_usage")` exists in your boto3
          version before assuming it does.
        * **A resource with no owner tag** comes back with the tag key present
          and an empty value, not absent. Map that to `UNTAGGED` rather than to
          an empty-string owner, or your biggest line item is called "".
        * **`UnblendedCost` vs `AmortizedCost`.** Unblended is what you were
          charged that day; amortized spreads reserved-instance and savings-plan
          costs. They tell different stories and a spike in one can be flat in
          the other. Pick deliberately and say which in the report itself -
          otherwise nobody can reconcile your numbers against the console.
        * Today's data is **incomplete and revised for up to 24 hours**. A
          reporter that flags yesterday's partial figure as a drop every morning
          is the most embarrassing false positive available here.

    `request_counter`, if given, is appended to once per API call. That is the
    metric `telemetry.py` exports, and it is how you notice the day someone
    "improves" this into 20,000 requests.

    Raises:
        CostExplorerUnavailable: for this account. Never ends the whole run.
    """
    raise NotImplementedError


def cached_fetch(
    client: CostExplorerClient,
    *,
    start: date,
    end: date,
    cache_dir: Path,
    owner_tag_key: str = "Owner",
) -> list[DailyCost]:
    """`fetch_daily_costs` with a disk cache.

    **Historical cost data is immutable** once a day is more than ~48 hours old,
    which makes it ideal to cache and is what makes backfilling cheap. Cache by
    `(account, start, end, granularity, group_by)`.

    The one rule that matters: **never cache a window that includes the last two
    days.** Those are still being revised, and a cached partial figure becomes a
    permanently wrong baseline that quietly poisons every future comparison.
    """
    raise NotImplementedError


def to_daily_costs(
    response: dict[str, Any],
    *,
    account_id: str,
    owner_tag_key: str,
) -> list[DailyCost]:
    """Normalise one `get_cost_and_usage` response. Pure, so it is testable.

    Keeping this separate from the client call is what lets the whole detection
    pipeline be tested against committed fixtures with no AWS at all - which
    matters here more than anywhere else in the track, because moto does not
    meaningfully model Cost Explorer.
    """
    raise NotImplementedError


__all__ = [
    "MAX_GROUP_BY",
    "CostExplorerUnavailable",
    "cached_fetch",
    "fetch_daily_costs",
    "to_daily_costs",
]
