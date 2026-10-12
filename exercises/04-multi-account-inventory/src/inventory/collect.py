"""Sweep the estate: assume, paginate, normalise, survive.

This is the orchestration layer, and the lesson of the exercise lives here:
**partial failure is the normal case.** Fourteen accounts times four regions is
fifty-six independent chances to fail, and the run must complete regardless,
collecting everything it can and reporting precisely what it could not.

YOUR JOB: implement `Collector` implementations, `collect_one`, and `collect`.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Protocol, runtime_checkable

if TYPE_CHECKING:
    from collections.abc import Sequence
    from datetime import datetime

    import boto3

    from inventory.accounts import AccountConfig
    from inventory.models import CollectionFailure, Inventory, Resource, ResourceType


@runtime_checkable
class Collector(Protocol):
    """One resource type, in one region, through one session.

    Same seam idea as E01's `ArtifactStore`: `collect()` below does not know
    whether it is sweeping EC2 or Lambda, which is what lets you add a fifth
    resource type without touching the orchestration.
    """

    @property
    def resource_type(self) -> ResourceType:
        """Which type this collector produces."""
        ...

    def collect(self, session: boto3.Session, *, account_id: str, region: str) -> list[Resource]:
        """Return every resource of this type in this account-region.

        **Use a paginator, never a bare `describe_*` call.** `DescribeInstances`
        truncates, `ListFunctions` truncates, everything truncates. The
        first-page-only bug is the entire subject of E06 and the reason this
        contract says so in capitals.
        """
        ...


class Ec2InstanceCollector:
    """`DescribeInstances` - note the Reservations nesting, which is the bit
    everyone forgets: instances live at `Reservations[*].Instances[*]`, so a
    naive `page["Instances"]` finds nothing and reports success."""


class EbsVolumeCollector:
    """`DescribeVolumes`."""


class RdsInstanceCollector:
    """`DescribeDBInstances`."""


class LambdaFunctionCollector:
    """`ListFunctions`. See `normalise_lambda_function` on the tags problem."""


def collect_one(
    account: AccountConfig,
    region: str,
    collectors: Sequence[Collector],
    *,
    session_name: str,
) -> tuple[list[Resource], list[CollectionFailure]]:
    """Sweep one account-region pair. **Never raises.**

    Everything that can go wrong becomes a `CollectionFailure`:

        * `AssumeRoleDenied`                -> `assume_role_denied`, region None,
                                               and the whole account is skipped
        * `InvalidClientTokenId` / opt-in   -> `region_unavailable`
          region errors (`AuthFailure`,
          `UnrecognizedClientException`)
        * `ThrottlingException` surviving   -> `throttled_out`
          botocore's own retries
        * `ExpiredToken`                    -> `credentials_expired`
        * anything else                     -> `unknown`, with the exception text
                                               in `detail` so it is debuggable

    Note the asymmetry worth getting right: a throttle that botocore retries into
    success is not a failure and must not appear here. A throttle that exhausts
    the retry budget is, and silently returning `[]` for it would be the worst
    outcome in this whole exercise - a confidently empty answer.

    Returns:
        Whatever was collected, and whatever failed. Both may be non-empty: three
        of four collectors succeeding is a normal result.
    """
    raise NotImplementedError


def collect(
    accounts: Sequence[AccountConfig],
    collectors: Sequence[Collector],
    *,
    now: datetime,
    max_workers: int = 8,
    session_name: str = "inventory",
) -> Inventory:
    """Sweep every account-region pair and assemble the `Inventory`.

    **Concurrency.** Serial across fifty-six pairs is a coffee break.
    `concurrent.futures.ThreadPoolExecutor` is the right first tool - these are
    I/O-bound HTTP calls, so the GIL is not the constraint. Build one Session per
    worker (see `creds.assume_role_session` on why) and submit one task per
    account-region pair.

    **Determinism.** Threads complete in arbitrary order, so sort before
    returning: `resources` by `Resource.sort_key()`, `failures` by
    `CollectionFailure.sort_key()`. Two runs over an unchanged estate must
    produce byte-identical JSON. There is a test for this and it is the acceptance
    criterion most likely to catch a thread-ordering bug.

    `accounts_reached` counts accounts that produced at least one successful
    collector call - not accounts that returned resources. An account genuinely
    running nothing was still reached.

    `now` is passed in rather than read from the clock, for the usual reason.
    """
    raise NotImplementedError


__all__ = [
    "Collector",
    "EbsVolumeCollector",
    "Ec2InstanceCollector",
    "LambdaFunctionCollector",
    "RdsInstanceCollector",
    "collect",
    "collect_one",
]
