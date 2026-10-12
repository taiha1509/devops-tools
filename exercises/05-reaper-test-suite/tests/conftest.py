"""Fixtures for the reaper suite, plus the one seam everything else hangs off.

## The adapter seam

Twenty tests that each reach into E03's internals is twenty tests you rewrite
when E03's internals change. Instead, `reap` below is the **single** place this
suite knows E03's API. Wire it once; every test calls through it.

That is not just convenience - it is the design lesson. If you cannot express
"run the reaper with this policy against this account and tell me what it did"
as one function, E03's API is harder to use than it needs to be, and the test
suite finding that out is the suite doing its job.

## Scoping

Every moto mock is function-scoped. A test that passes alone and fails in a suite
is a scoping bug; `pytest-randomly` is installed to surface it now rather than in
CI at 2am.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any

import boto3
import pytest
from moto import mock_aws

if TYPE_CHECKING:
    from collections.abc import Callable, Iterator

    from mypy_boto3_ec2 import EC2Client

NOW = datetime(2026, 9, 21, 12, 0, tzinfo=UTC)
REGION = "ap-southeast-1"
OTHER_REGION = "eu-west-1"


@dataclass
class ReapOutcome:
    """What a run did, in this suite's vocabulary rather than E03's.

    `deleted_ids` is the **plan** - what the reaper selected. `api_deletes` is
    what actually reached AWS. Keeping them separate is what makes the dry-run
    invariant testable at all: a dry run has a non-empty plan and zero API
    deletes, and asserting on the return value alone would never catch a reaper
    that deletes during a dry run.
    """

    deleted_ids: list[str] = field(default_factory=list)
    api_deletes: list[str] = field(default_factory=list)
    failures: list[dict[str, Any]] = field(default_factory=list)
    exit_code: int = 0
    cost_estimate: float | None = None


@pytest.fixture
def aws() -> Iterator[None]:
    """moto, function-scoped. Nothing in this suite touches a real account."""
    with mock_aws():
        yield


@pytest.fixture
def now() -> datetime:
    return NOW


@pytest.fixture
def ec2(aws: None) -> EC2Client:
    return boto3.client("ec2", region_name=REGION)


@pytest.fixture
def reap() -> Callable[..., ReapOutcome]:
    """THE SEAM. Wire this to E03 and the rest of the suite works.

    Implement it to:

        1. build whatever policy object E03 takes, from the kwargs here
        2. run the reaper
        3. return a `ReapOutcome`

    Import `reaper` **inside** the function, not at module scope. E03 is a work
    in progress; a module-level import makes this whole suite fail to collect
    while E03 is mid-refactor, and a suite you cannot run is a suite you stop
    running.

    For `api_deletes`, count deletions at the boundary rather than trusting the
    return value - a `botocore` event hook on `before-call.ec2.DeleteVolume`, or
    a `Stubber`, or monkeypatching the client. Whichever you pick, write down in
    `TESTING.md` why, because "I asserted on the thing under test's own report of
    itself" is the hole the dry-run invariant is supposed to close.
    """

    def _reap(
        *,
        older_than_days: int = 30,
        apply: bool = False,
        exclude_tags: dict[str, str] | None = None,
        regions: tuple[str, ...] = (REGION,),
        now: datetime = NOW,
    ) -> ReapOutcome:
        raise NotImplementedError("wire this to E03's reaper - see the docstring")

    return _reap


@pytest.fixture
def unattached_volume(ec2: EC2Client) -> Callable[..., str]:
    """Create an `available` (orphaned) EBS volume and return its ID."""

    def _make(*, tags: dict[str, str] | None = None, size: int = 8) -> str:
        kwargs: dict[str, Any] = {"AvailabilityZone": f"{REGION}a", "Size": size}
        if tags:
            kwargs["TagSpecifications"] = [
                {
                    "ResourceType": "volume",
                    "Tags": [{"Key": k, "Value": v} for k, v in tags.items()],
                }
            ]
        return str(ec2.create_volume(**kwargs)["VolumeId"])

    return _make


@pytest.fixture
def throttle_after() -> Callable[..., None]:
    """Inject `ThrottlingException` into EC2 calls.

    `after=0` throttles every call - that is the "fails loudly" test. `after=2`
    throttles the first two and then succeeds, which is the "survives transient
    throttling" test. Both matter and they assert opposite things.

    Implement with a `botocore` `before-call` event hook that raises
    `ClientError` with code `ThrottlingException`, or with `Stubber`. If you
    cannot inject a throttle without monkeypatching something private in E03,
    **that is a design signal about E03** - note it in `TESTING.md`.
    """

    def _throttle(*, after: int = 0, operations: tuple[str, ...] = ()) -> None:
        raise NotImplementedError

    return _throttle
