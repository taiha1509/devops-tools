"""Probes for how EBS enumeration behaves, and where moto lies about it.

No production code exists yet - these establish the boto3 behaviour the reaper will
depend on, above all that pagination gets walked to exhaustion. The README's central
warning is a reaper that reads page one, finds 50 orphans out of 340, and reports
success.

Debug output: pytest captures stdout and only replays it for *failing* tests, so a
`print` in a passing test is swallowed. Use `pytest -s` (or `--capture=no`) to see it.
`-q` is not what hides it - capture is on by default at any verbosity.

## moto gaps found here (the README asks for these; E05 will want them)

1. **moto does not paginate EC2 `describe_*` at all.** `MaxResults` is ignored and
   `NextToken` is never returned, so every paginator collapses to one page no matter
   how many resources exist. Verified with 12 volumes at `PageSize=5`: one page, 12
   items. Consequence: **moto cannot prove your pagination works.** A reaper that
   reads only page one passes a moto suite cleanly and then finds 50 of 340 orphans in
   production. Pagination has to be tested with `botocore.stub.Stubber` instead - see
   `test_paginator_follows_nexttoken_across_three_pages`.
2. **`describe_snapshots` returns ~1160 seeded snapshots** that nobody created, and
   `OwnerIds=["self"]` does **not** filter them (verified: 1162 either way). A snapshot
   reaper tested against moto would report a thousand phantom orphans. Filter on your
   own volume ids, not on the owner filter.
3. Already in the README, not re-verified here: moto enforces no IAM, never throttles,
   and shows no eventual consistency.
"""

from __future__ import annotations

import pytest
from moto import mock_aws


def _all_volumes(client, **paginate_kwargs) -> list[dict]:
    """Walk every page. The reaper must never use a bare describe_volumes()."""
    return [
        v
        for page in client.get_paginator("describe_volumes").paginate(**paginate_kwargs)
        for v in page["Volumes"]
    ]


# --------------------------------------------------------------------------------
# Pagination - the point of the exercise, and the thing moto cannot test.
# --------------------------------------------------------------------------------


def test_paginator_follows_nexttoken_across_three_pages(stubbed_ec2_client):
    """The acceptance criterion: one resource type returns 3 pages.

    Scripted with Stubber because moto won't produce a second page (gap 1). This is
    the test that actually protects against the page-one-only bug.
    """
    client, stubber = stubbed_ec2_client

    def page(ids: list[str], next_token: str | None = None) -> dict:
        body = {"Volumes": [{"VolumeId": i, "State": "available", "Attachments": []} for i in ids]}
        if next_token:
            body["NextToken"] = next_token
        return body

    stubber.add_response("describe_volumes", page(["vol-1", "vol-2"], "t1"), {})
    stubber.add_response("describe_volumes", page(["vol-3", "vol-4"], "t2"), {"NextToken": "t1"})
    stubber.add_response("describe_volumes", page(["vol-5"]), {"NextToken": "t2"})

    pages = list(client.get_paginator("describe_volumes").paginate())

    assert len(pages) == 3
    ids = [v["VolumeId"] for p in pages for v in p["Volumes"]]
    assert ids == ["vol-1", "vol-2", "vol-3", "vol-4", "vol-5"]


@pytest.mark.xfail(
    strict=True,
    reason=(
        "moto gap 1: EC2 describe_volumes ignores MaxResults and never returns "
        "NextToken, so PageSize cannot split the result. Remove this marker if moto "
        "ever implements EC2 pagination - strict=True will flag the XPASS."
    ),
)
@mock_aws
def test_moto_would_paginate_if_it_modelled_pagination(init_ec2_client, make_volumes):
    client = init_ec2_client()
    make_volumes(client, 12)

    pages = list(
        client.get_paginator("describe_volumes").paginate(PaginationConfig={"PageSize": 5})
    )

    assert len(pages) == 3


@mock_aws
def test_paginator_still_returns_every_volume_under_moto(init_ec2_client, make_volumes):
    """What moto *can* verify: nothing is dropped. Page count is untestable here."""
    client = init_ec2_client()
    created = make_volumes(client, 12)

    seen = [v["VolumeId"] for v in _all_volumes(client)]

    assert sorted(seen) == sorted(created)


# --------------------------------------------------------------------------------
# Orphan identification and the safety rails.
# --------------------------------------------------------------------------------


@mock_aws
def test_unattached_volumes_are_available(init_ec2_client, make_volumes):
    """An orphan EBS volume is one in state "available" with nothing attached."""
    client = init_ec2_client()
    make_volumes(client, 3)

    volumes = _all_volumes(client)

    assert {v["State"] for v in volumes} == {"available"}
    assert all(v["Attachments"] == [] for v in volumes)


@mock_aws
def test_donotreap_tag_survives_the_round_trip(init_ec2_client, make_volumes):
    """Tag exclusion is a safety rail, so the tag has to actually come back."""
    client = init_ec2_client()
    protected = make_volumes(client, 1, tags={"DoNotReap": "true"})[0]
    make_volumes(client, 2)

    make_volumes(client, 500)

    all_vols = _all_volumes(client)

    by_id = {v["VolumeId"]: v for v in _all_volumes(client)}

    tags = {t["Key"]: t["Value"] for t in by_id[protected].get("Tags", [])}
    assert tags == {"DoNotReap": "true"}
    assert all(not v.get("Tags") for vid, v in by_id.items() if vid != protected)


@mock_aws
def test_client_uses_the_configured_region(init_ec2_client, region):
    client = init_ec2_client()
    assert client.meta.region_name == region
