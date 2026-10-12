"""Querying a collected inventory. Pure: a dataset and a filter in, a subset out.

The security question from the brief - "which accounts have EC2 instances with
public IPs and no tag telling us who owns them?" - is this module plus the CLI.

YOUR JOB: implement `Filter` and `apply_filters`.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Sequence

    from inventory.models import Resource, ResourceType


@dataclass(frozen=True, slots=True)
class Filter:
    """A conjunction of predicates. Given to you complete.

    Every field is independently optional and they compose with AND, which is the
    only composition the brief needs. If you want OR, build it by unioning two
    query results rather than by growing this dataclass a mode flag.

    has_tag / missing_tag:  tag **presence**, not value. "no tag telling us who
                            owns them" is a presence question.
    tag_equals:             exact value match, for the cases where it is not.
    public_ip:              True = only resources with one, False = only without,
                            None = do not filter. Note that `False` and `None`
                            are different, which is exactly the bug a bare
                            `if filter.public_ip:` check would introduce.
    """

    resource_types: tuple[ResourceType, ...] = ()
    accounts: tuple[str, ...] = ()
    regions: tuple[str, ...] = ()
    has_tag: tuple[str, ...] = ()
    missing_tag: tuple[str, ...] = ()
    tag_equals: tuple[tuple[str, str], ...] = ()
    public_ip: bool | None = None


def matches(resource: Resource, flt: Filter) -> bool:
    """Does one resource satisfy every active clause of `flt`?

    An empty `Filter()` matches everything - the permissive-library rule from
    E01's `select_for_deletion`. The CLI is the layer that decides whether a
    query with no clauses is a mistake.
    """
    raise NotImplementedError


def apply_filters(resources: Sequence[Resource], flt: Filter) -> list[Resource]:
    """Filter, preserving the input's (already sorted) order."""
    raise NotImplementedError


__all__ = ["Filter", "apply_filters", "matches"]
