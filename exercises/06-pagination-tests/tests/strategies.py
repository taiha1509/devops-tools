"""Hypothesis strategies over the raw shapes AWS actually returns.

Separate from `conftest.py` because strategies are values that tests import, not
fixtures that pytest injects. (No `__init__.py` in `tests/` - pytest puts this
directory on `sys.path`, so `from strategies import ...` works.)

Every oddity encoded below is real. The normaliser bug in E06's problem statement
was a resource whose tag block was simply absent, which is the second strategy in
`raw_tags`. Widen these when Hypothesis stops finding anything: the acceptance
criterion is that it finds a bug, and weak strategies are the usual reason it
does not.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from hypothesis import strategies as st

ACCOUNT_A = "111111111111"
REGION = "eu-west-1"

tag_keys = st.text(min_size=1, max_size=40).filter(lambda s: s.strip() == s)
tag_values = st.text(max_size=80)

taglist_entries = st.one_of(
    st.fixed_dictionaries({"Key": tag_keys, "Value": tag_values}),
    # A tag with no Value. Real, and it must keep the key - presence is what a
    # "which resources lack an Owner tag" query reads.
    st.fixed_dictionaries({"Key": tag_keys}),
    # A tag with no Key. Also real, and unqueryable, so it gets dropped.
    st.fixed_dictionaries({"Value": tag_values}),
)

raw_tags: st.SearchStrategy[Any] = st.one_of(
    st.none(),
    st.just([]),
    st.just({}),
    st.lists(taglist_entries, max_size=8),
    st.dictionaries(tag_keys, tag_values, max_size=8),
)
"""Every tag shape AWS has ever returned, including the absent ones."""


@st.composite
def raw_ec2_instances(draw: st.DrawFn) -> dict[str, Any]:
    """A `DescribeInstances` instance dict, with the awkward cases included."""
    body: dict[str, Any] = {"InstanceId": draw(st.text(min_size=1, max_size=20))}
    tags = draw(raw_tags)
    if tags is not None:
        body["Tags"] = tags
    if draw(st.booleans()):
        body["PublicIpAddress"] = draw(st.ip_addresses(v=4).map(str))
    if draw(st.booleans()):
        body["LaunchTime"] = draw(
            st.datetimes(
                min_value=datetime(2020, 1, 1),  # noqa: DTZ001
                max_value=datetime(2030, 1, 1),  # noqa: DTZ001
            ).map(lambda d: d.replace(tzinfo=UTC))
        )
    return body


__all__ = [
    "ACCOUNT_A",
    "REGION",
    "raw_ec2_instances",
    "raw_tags",
    "tag_keys",
    "tag_values",
    "taglist_entries",
]
