"""Raw AWS shapes in, `Resource` out. Pure: no I/O, no clock, no boto3.

This module is where E06's property-based tests will attach, so keep it honest:
every function here is a total function from a raw API dict to a `Resource`, and
it must not raise on any input shape AWS can produce.

The invariant that matters most: **N raw resources in, N records out.** Never
fewer. A normaliser that silently drops anything is the bug in E06's problem
statement - the inventory said 1,200 and the real number was 4,100, with no
error and no warning.

YOUR JOB: implement all four normalisers and `normalise_tags`.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from collections.abc import Iterable

    from inventory.models import Resource


def normalise_tags(raw: Any) -> dict[str, str]:  # noqa: ANN401
    """Turn any of AWS's several tag spellings into a plain dict.

    The shapes you will actually meet:

        * `[{"Key": "Owner", "Value": "billing"}, ...]`   EC2, RDS (`TagList`)
        * `{"Owner": "billing"}`                          Lambda
        * `[]`, `{}`, missing entirely, or `None`         any of them

    Rules, all of which exist because something broke:

        * Absent, None, or empty -> `{}`. Never raise. Never return None.
        * A tag entry missing `Value` -> empty-string value, not dropped. The key
          is the interesting part for a "which resources lack an Owner tag" query.
        * A tag entry missing `Key` -> skipped, because it cannot be queried.
        * Duplicate keys -> last wins, and say so in `DECISIONS.md`.
        * Values stay strings. Do not coerce `"true"` to a bool; a tag value is
          text and guessing its type is how you get `Owner: True`.

    `Any` is deliberate here (and the ANN401 ignore with it): the point of the
    function is that it accepts whatever arrives.
    """
    raise NotImplementedError


def normalise_ec2_instance(raw: dict[str, Any], *, account_id: str, region: str) -> Resource:
    """One element of `DescribeInstances` -> `Resource`.

    Fields: `InstanceId`, `Tags`, `PublicIpAddress` (absent on private
    instances - absent, not empty string), `LaunchTime` (already tz-aware; do not
    re-localise it). `name` comes from the `Name` tag if present, else None.
    """
    raise NotImplementedError


def normalise_ebs_volume(raw: dict[str, Any], *, account_id: str, region: str) -> Resource:
    """One element of `DescribeVolumes` -> `Resource`. Volumes have no public IP."""
    raise NotImplementedError


def normalise_rds_instance(raw: dict[str, Any], *, account_id: str, region: str) -> Resource:
    """One element of `DescribeDBInstances` -> `Resource`.

    Note the shape mismatch that makes this exercise worth doing: the identifier
    is `DBInstanceIdentifier`, tags are `TagList`, creation time is
    `InstanceCreateTime`, and "publicly accessible" is a **bool**
    (`PubliclyAccessible`) rather than an address. Decide how that maps onto
    `public_ip` and write the decision down - there is no obviously right answer
    and the reviewer will ask.
    """
    raise NotImplementedError


def normalise_lambda_function(raw: dict[str, Any], *, account_id: str, region: str) -> Resource:
    """One element of `ListFunctions` -> `Resource`.

    `LastModified` is an **ISO-8601 string**, not a datetime, and `ListFunctions`
    does not return tags at all - they need a separate `ListTags` call per
    function. Decide whether to make it (N extra API calls) or to leave tags
    empty (a query for untagged resources then lies). Write down which and why.
    """
    raise NotImplementedError


def normalise_all(
    raw_items: Iterable[dict[str, Any]],
    *,
    normaliser: str,
    account_id: str,
    region: str,
) -> list[Resource]:
    """Map a page of raw items through one normaliser, preserving count and order.

    Keep this the only place that loops, so the count-preservation property has a
    single place to hold. `normaliser` names one of the functions above; a dict
    lookup is fine and an unknown name should raise `KeyError` loudly - that is a
    programming error, not bad input.
    """
    raise NotImplementedError


__all__ = [
    "normalise_all",
    "normalise_ebs_volume",
    "normalise_ec2_instance",
    "normalise_lambda_function",
    "normalise_rds_instance",
    "normalise_tags",
]
