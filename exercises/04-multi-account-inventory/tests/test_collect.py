"""Contract for the sweep: partial failure is the normal case.

These are the tests that make the difference between tooling that works in your
sandbox and tooling that works across an organisation's estate. Every one of them
describes something that happens on a real fourteen-account sweep.

`collect_one` must **never raise**. If any test here fails with an exception
rather than an assertion, that is the finding.
"""

from __future__ import annotations

import pytest

from inventory.collect import collect, collect_one
from inventory.models import FailureReason

pytestmark = pytest.mark.usefixtures("accounts")


class TestPartialFailure:
    def test_one_denied_account_does_not_end_the_run(self, accounts, now):
        """Account A works, account B's trust policy is broken. A's data survives.

        A run that aborts on the first failure is useless at this scale - that is
        the whole lesson of the exercise.
        """
        pytest.fail("implement: stub STS to deny account B, assert A's resources present")

    def test_denied_account_is_reported_with_a_reason(self, accounts, now):
        inv = collect(accounts, [], now=now)
        assert any(f.reason is FailureReason.ASSUME_ROLE_DENIED for f in inv.failures)

    def test_unavailable_region_fails_only_that_region(self, accounts, now):
        """An opt-in region that is not enabled. The account's other regions still sweep."""
        pytest.fail("implement: stub one region to raise AuthFailure, assert the other collected")

    def test_throttling_exhaustion_is_a_failure_not_an_empty_result(self, accounts, now):
        """The most dangerous bug in this exercise.

        A throttle that botocore retries into success is **not** a failure and must
        not be reported. A throttle that exhausts the retry budget **is** - and
        returning `[]` for it would report a confident, successful sweep of zero
        resources, which is worse than crashing.
        """
        pytest.fail("implement: inject ThrottlingException on every call, assert throttled_out")

    def test_expired_credentials_mid_sweep_are_reported(self, accounts, now):
        pytest.fail("implement: raise ExpiredToken from the second collector call")


class TestSummaryHonesty:
    def test_collected_zero_differs_from_failed_to_collect(self, accounts, now):
        """An empty estate and an unreachable estate must not render identically.

        A security team reading "0 public IPs" needs to know which one it was.
        """
        empty = collect(accounts, [], now=now)
        assert empty.partial is False
        assert empty.accounts_reached == len(accounts)

    def test_accounts_reached_counts_access_not_resources(self, accounts, now):
        """An account genuinely running nothing was still reached."""
        inv = collect(accounts, [], now=now)
        assert inv.accounts_reached == len(accounts)
        assert inv.resources == ()


class TestDeterminism:
    def test_two_runs_over_identical_state_are_byte_identical(self, accounts, now):
        """The acceptance criterion most likely to catch a thread-ordering bug.

        Threads complete in arbitrary order, so `collect()` has to sort before
        returning. Without this you cannot diff two runs, and diffing two runs is
        the reason the tool exists.
        """
        first = collect(accounts, [], now=now, max_workers=4)
        second = collect(accounts, [], now=now, max_workers=4)
        assert first.model_dump_json() == second.model_dump_json()

    def test_resources_are_sorted_by_sort_key(self, accounts, now):
        inv = collect(accounts, [], now=now)
        keys = [r.sort_key() for r in inv.resources]
        assert keys == sorted(keys)


class TestPagination:
    def test_collectors_see_past_the_first_page(self, accounts, now, make_pages):
        """E06 goes after this properly. One test here so the bug cannot land first.

        Assert an exact total, not "some results came back" - a first-page-only
        bug returns results, which is precisely why it survives review.
        """
        pytest.fail("implement: 3-page fixture, assert the page-3 resource is in the output")


def test_collect_one_never_raises(accounts):
    """The contract, stated as a test. Every failure mode is a record, not an exception."""
    resources, failures = collect_one(accounts[0], "eu-west-1", [], session_name="test")
    assert isinstance(resources, list)
    assert isinstance(failures, list)
