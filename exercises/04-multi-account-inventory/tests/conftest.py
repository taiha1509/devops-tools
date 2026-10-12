from __future__ import annotations

from datetime import UTC, datetime
from typing import Any, Protocol

import pytest

from inventory.accounts import AccountConfig

# A fixed reference time, for the same reason E01 has one: `collected_at` is a
# parameter, never something the code reads from the clock for itself.
NOW = datetime(2026, 9, 21, 12, 0, tzinfo=UTC)

ACCOUNT_A = "111111111111"
ACCOUNT_B = "222222222222"


class MakePages(Protocol):
    def __call__(self, items: list[Any], *, per_page: int = ...) -> list[dict[str, Any]]: ...


@pytest.fixture
def now() -> datetime:
    return NOW


@pytest.fixture
def accounts() -> tuple[AccountConfig, ...]:
    return (
        AccountConfig(
            account_id=ACCOUNT_A,
            role_arn=f"arn:aws:iam::{ACCOUNT_A}:role/InventoryReader",
            regions=("eu-west-1", "us-east-1"),
            label="prod",
        ),
        AccountConfig(
            account_id=ACCOUNT_B,
            role_arn=f"arn:aws:iam::{ACCOUNT_B}:role/InventoryReader",
            regions=("eu-west-1",),
            label="staging",
        ),
    )


@pytest.fixture
def make_pages() -> MakePages:
    """Split a list of items into paginator-shaped pages.

    This factory is the one piece of E04's test kit that E06 reuses wholesale, so
    keep it generic: `per_page=1` over three items is the 3-page case, an empty
    list is the 0-page case, and a single short page is the case that hides the
    first-page-only bug.
    """

    def _make(items: list[Any], *, per_page: int = 1) -> list[dict[str, Any]]:
        if not items:
            return [{"Items": []}]
        return [{"Items": items[i : i + per_page]} for i in range(0, len(items), per_page)]

    return _make


@pytest.fixture
def raw_ec2_instance() -> dict[str, Any]:
    """A realistic `DescribeInstances` instance dict."""
    return {
        "InstanceId": "i-0abc123",
        "LaunchTime": datetime(2026, 1, 15, 9, 30, tzinfo=UTC),
        "PublicIpAddress": "203.0.113.17",
        "Tags": [
            {"Key": "Name", "Value": "web-01"},
            {"Key": "Owner", "Value": "billing"},
        ],
    }
