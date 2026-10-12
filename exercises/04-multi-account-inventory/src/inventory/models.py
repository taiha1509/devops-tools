"""The normalised inventory schema.

Given to you complete. Everything else in this package is a stub.

The schema *is* the exercise's spine. EC2, RDS and Lambda describe themselves
completely differently, and the whole value of this tool is that its output does
not. Define the target shape first and map into it - doing it the other way round
produces a schema that is the union of three APIs' accidents.

Note `CollectionFailure`: a failure is a **record in the output**, not an
exception that ends the run. At fourteen accounts and four regions, something is
always broken, and a sweep that aborts on the first problem is useless.
"""

from __future__ import annotations

from datetime import datetime
from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field


class ResourceType(StrEnum):
    """Stable type identifiers. These are ours, not AWS's."""

    EC2_INSTANCE = "ec2:instance"
    EBS_VOLUME = "ec2:volume"
    RDS_INSTANCE = "rds:db"
    LAMBDA_FUNCTION = "lambda:function"


class FailureReason(StrEnum):
    """Why a sweep could not reach something.

    Machine-readable on purpose: "the run partially failed" is not actionable,
    "three accounts returned assume_role_denied" is.
    """

    ASSUME_ROLE_DENIED = "assume_role_denied"
    REGION_UNAVAILABLE = "region_unavailable"
    THROTTLED_OUT = "throttled_out"
    CREDENTIALS_EXPIRED = "credentials_expired"
    UNKNOWN = "unknown"


class Resource(BaseModel):
    """One resource, in the shape this tool defines rather than the shape AWS returned.

    `tags` is always a dict, never None. An absent tag block is the single most
    common cause of a `KeyError` taking down an infrastructure script - the schema
    refuses to represent it so your collectors cannot forward it.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    resource_id: str
    resource_type: ResourceType
    account_id: str
    region: str
    name: str | None = None
    tags: dict[str, str] = Field(default_factory=dict)
    public_ip: str | None = None
    created_at: datetime | None = None

    def sort_key(self) -> tuple[str, str, str, str]:
        """Total ordering over the estate. Determinism comes from here.

        Two runs against an unchanged estate must produce byte-identical JSON, or
        you cannot diff them to see what changed - and that diff is the reason to
        build the tool at all.
        """
        return (self.account_id, self.region, str(self.resource_type), self.resource_id)


class CollectionFailure(BaseModel):
    """One account-region-service pair that could not be collected, and why.

    `region` and `resource_type` are None when the failure happened before that
    level was reached - an assume-role denial fails the whole account at once.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    account_id: str
    region: str | None = None
    resource_type: ResourceType | None = None
    reason: FailureReason = FailureReason.UNKNOWN
    detail: str = ""

    def sort_key(self) -> tuple[str, str, str]:
        return (self.account_id, self.region or "", str(self.resource_type or ""))


class Inventory(BaseModel):
    """The whole dataset: what was found, and what could not be reached.

    `accounts_requested` vs `accounts_reached` is what lets the summary
    distinguish **"collected 0 resources"** from **"failed to collect"**. Those
    are opposite findings and a tool that renders them identically is actively
    misleading - a security team reading "0 public IPs" needs to know whether
    that means "none exist" or "we couldn't look".
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    collected_at: datetime
    accounts_requested: int
    accounts_reached: int
    resources: tuple[Resource, ...] = ()
    failures: tuple[CollectionFailure, ...] = ()

    @property
    def partial(self) -> bool:
        """True when any part of the estate was unreachable."""
        return bool(self.failures)
