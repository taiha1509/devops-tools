"""Contract for the query layer. Pure functions, so these are the cheap tests."""

from __future__ import annotations

import pytest

from inventory.models import Resource, ResourceType
from inventory.query import Filter, apply_filters, matches

ACCOUNT_A = "111111111111"
ACCOUNT_B = "222222222222"


def _res(
    rid: str,
    *,
    account: str = ACCOUNT_A,
    region: str = "eu-west-1",
    rtype: ResourceType = ResourceType.EC2_INSTANCE,
    tags: dict[str, str] | None = None,
    public_ip: str | None = None,
) -> Resource:
    return Resource(
        resource_id=rid,
        resource_type=rtype,
        account_id=account,
        region=region,
        tags=tags or {},
        public_ip=public_ip,
    )


def test_empty_filter_matches_everything():
    """The permissive-library rule from E01: the CLI decides what counts as misuse."""
    assert matches(_res("i-1"), Filter()) is True


def test_missing_tag_is_about_presence_not_value():
    """`--missing-tag Owner` is the brief's motivating security question."""
    unowned = _res("i-1", tags={"env": "prod"})
    owned = _res("i-2", tags={"Owner": "billing"})
    flt = Filter(missing_tag=("Owner",))
    assert apply_filters([unowned, owned], flt) == [unowned]


def test_an_owner_tag_with_an_empty_value_still_counts_as_present():
    """Presence, not truthiness. `Owner: ""` is a tagging problem, not an absent tag,
    and conflating them makes the query answer a question nobody asked."""
    blank = _res("i-1", tags={"Owner": ""})
    assert apply_filters([blank], Filter(missing_tag=("Owner",))) == []


def test_public_ip_true_false_and_none_are_three_different_filters():
    """The bug a bare `if flt.public_ip:` would introduce: `False` would behave as
    "do not filter" and the query would silently include private instances."""
    public = _res("i-1", public_ip="203.0.113.17")
    private = _res("i-2")
    assert apply_filters([public, private], Filter(public_ip=True)) == [public]
    assert apply_filters([public, private], Filter(public_ip=False)) == [private]
    assert apply_filters([public, private], Filter(public_ip=None)) == [public, private]


def test_clauses_compose_with_and():
    """The full brief query: public IP **and** no Owner tag."""
    target = _res("i-1", public_ip="203.0.113.17", tags={"env": "prod"})
    tagged_public = _res("i-2", public_ip="203.0.113.18", tags={"Owner": "billing"})
    untagged_private = _res("i-3", tags={"env": "prod"})
    flt = Filter(public_ip=True, missing_tag=("Owner",))
    assert apply_filters([target, tagged_public, untagged_private], flt) == [target]


@pytest.mark.parametrize(
    ("flt", "expected"),
    [
        (Filter(accounts=(ACCOUNT_B,)), ["i-2"]),
        (Filter(regions=("us-east-1",)), ["i-3"]),
        (Filter(resource_types=(ResourceType.RDS_INSTANCE,)), ["i-4"]),
        (Filter(tag_equals=(("env", "prod"),)), ["i-1"]),
    ],
)
def test_each_scalar_clause(flt, expected):
    pool = [
        _res("i-1", tags={"env": "prod"}),
        _res("i-2", account=ACCOUNT_B),
        _res("i-3", region="us-east-1"),
        _res("i-4", rtype=ResourceType.RDS_INSTANCE),
    ]
    assert [r.resource_id for r in apply_filters(pool, flt)] == expected


def test_order_is_preserved():
    """Input arrives already sorted by `collect()`. Filtering must not reshuffle it."""
    pool = [_res("i-1"), _res("i-2"), _res("i-3")]
    assert apply_filters(pool, Filter()) == pool
