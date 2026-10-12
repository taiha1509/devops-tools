"""Shared fixtures.

Must be named `conftest.py` - pytest only auto-discovers fixtures from this filename.
A module called `fixtures.py` is just a module; nothing imports it, so its fixtures
are invisible and every test using them errors with "fixture not found".
"""

from __future__ import annotations

import boto3
import pytest
from botocore.config import Config as BotoConfig

REGION = "ap-southeast-1"

# Retry mode set deliberately, per the README: standard mode already handles
# Throttling / ThrottlingException / RequestThrottledException / 429 / 5xx with
# exponential backoff. Nothing here should add a retry decorator on top of it.
BOTO_CONFIG = BotoConfig(
    region_name=REGION,
    retries={"max_attempts": 3, "mode": "standard"},
)


@pytest.fixture
def region() -> str:
    return REGION


@pytest.fixture
def init_ec2_client():
    """Return a *factory*, not a client.

    Fixture setup runs before `@mock_aws` activates, so a fixture that built the
    client itself would be talking to real AWS. Building it inside the test body
    keeps it under the mock.

    Note the `**kwargs` sits on `_make`, not on the fixture: a fixture's own
    parameters are requests for *other fixtures*, so `def init_ec2_client(**kwargs)`
    would just be called with nothing.
    """

    def _make(**kwargs):
        # `config=` by keyword. boto3.client's second positional parameter is
        # region_name, so passing the Config object positionally lands it there
        # and fails with "expected string or bytes-like object, got 'Config'".
        kwargs.setdefault("config", BOTO_CONFIG)
        return boto3.client("ec2", **kwargs)

    return _make


@pytest.fixture
def stubbed_ec2_client():
    """An EC2 client wired to a botocore Stubber, with no moto and no network.

    Needed because moto does not model EC2 pagination at all (see test_ebs.py).
    Stubber scripts raw API responses, so it is the only way here to produce real
    NextToken pages and test that the reaper walks them.
    """
    from botocore.stub import Stubber

    client = boto3.client(
        "ec2",
        config=BOTO_CONFIG,
        aws_access_key_id="testing",
        aws_secret_access_key="testing",
    )
    stubber = Stubber(client)
    with stubber:
        yield client, stubber
    stubber.assert_no_pending_responses()


@pytest.fixture
def make_volumes():
    """Create N EBS volumes and return their ids, newest tag first."""

    def _make(client, count: int, *, tags: dict[str, str] | None = None) -> list[str]:
        spec = (
            [{"ResourceType": "volume", "Tags": [{"Key": k, "Value": v} for k, v in tags.items()]}]
            if tags
            else []
        )
        return [
            client.create_volume(
                AvailabilityZone=f"{REGION}a",
                Size=8,
                TagSpecifications=spec,
            )["VolumeId"]
            for _ in range(count)
        ]

    return _make
