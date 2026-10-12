"""Part 1 - pagination, properly.

Every collector in E04, at 0, 1 and 3+ pages, asserting exact totals. One page is
the case that hides the bug. Zero is the case that crashes on `pages[0]`. Three is
the only case that catches a first-page-only implementation.
"""

from __future__ import annotations

import pytest
from inventory.models import ResourceType

# (collector class name, the response key its operation nests items under)
COLLECTORS = [
    pytest.param("Ec2InstanceCollector", "Reservations", ResourceType.EC2_INSTANCE, id="ec2"),
    pytest.param("EbsVolumeCollector", "Volumes", ResourceType.EBS_VOLUME, id="ebs"),
    pytest.param("RdsInstanceCollector", "DBInstances", ResourceType.RDS_INSTANCE, id="rds"),
    pytest.param("LambdaFunctionCollector", "Functions", ResourceType.LAMBDA_FUNCTION, id="lambda"),
]


@pytest.mark.parametrize(("collector_name", "key", "rtype"), COLLECTORS)
def test_three_pages_yields_every_item(collector_name, key, rtype, paged):
    """The test that catches the bug. Assert an **exact count**.

    "Some results came back" is what a first-page-only implementation produces,
    which is precisely why it survives code review. Only a total is evidence.
    """
    raise AssertionError(f"implement: 3-page {collector_name} fixture, assert exact total")


@pytest.mark.parametrize(("collector_name", "key", "rtype"), COLLECTORS)
def test_single_page_yields_every_item(collector_name, key, rtype, paged):
    """The case that hides the bug. It must pass - and passing proves nothing on
    its own, which is the lesson."""
    raise AssertionError(f"implement: 1-page {collector_name} fixture")


@pytest.mark.parametrize(("collector_name", "key", "rtype"), COLLECTORS)
def test_zero_pages_returns_empty_without_crashing(collector_name, key, rtype, paged):
    """An account genuinely running nothing. `pages[0]` raises `IndexError` here."""
    raise AssertionError(f"implement: empty {collector_name} fixture, assert []")


def test_ec2_reservations_nesting_is_traversed(paged):
    """The EC2-specific trap, worth its own test.

    Instances live at `Reservations[*].Instances[*]`. A naive `page["Instances"]`
    finds nothing, raises nothing, and reports a successful sweep of zero
    instances. Put **two instances in one reservation and one in another** so a
    flattening bug and an off-by-one both show up.
    """
    raise AssertionError("implement: 2 reservations, 3 instances total, assert 3")


def test_deliberately_broken_paginator_is_caught():
    """Prove the suite works by breaking the code.

    Procedure, not an assertion:

        1. branch, and replace one collector's paginator with a bare
           `describe_*` call
        2. run the tests above and confirm the 3-page one goes **red** and the
           1-page one stays green
        3. record both results in `DECISIONS.md`
        4. throw the branch away

    Step 2 is the whole exercise. A test you have never watched fail is a test you
    do not know works.
    """
    raise AssertionError("implement: see docstring - delete this test once recorded")


def test_regression_inventory_undercounted_by_seventy_percent(paged):
    """The symptom, named, so the next person understands why this file exists.

    The inventory reported 1,200 resources against a real 4,100. Three services
    truncated at the first page and one normaliser silently dropped every resource
    with no tag block. Nothing errored. The number was simply false, and it was
    used to make a decision.
    """
    raise AssertionError("implement: multi-page + untagged fixture, assert the exact total")
