"""The failure-path tests - the ones nobody writes.

Every test in this file describes something that has taken down a real
infrastructure script. They are also, collectively, the second half of the
sentence that makes a Senior answer: not just "I wrote a reaper and tested it"
but "here is what my tests prove it survives".
"""

from __future__ import annotations

REGION = "ap-southeast-1"
OTHER_REGION = "eu-west-1"


class TestPagination:
    """The entire reason E03 insisted on paginators.

    Note from E03's pyproject: moto does not model EC2 `NextToken` pages, so these
    need `botocore.stub.Stubber` rather than moto. That is awkward, and the
    awkwardness is the point - it is why people skip this test and why the bug
    class survives.
    """

    def test_resources_on_page_three_are_found(self, reap):
        """Assert the **exact total**, not "some results came back".

        A first-page-only bug returns results. It looks like success. That is why
        it gets through review, and why asserting a count is the only test that
        catches it.
        """
        raise AssertionError(
            "implement: 3-page Stubber fixture, assert all pages' volumes selected"
        )

    def test_a_deliberately_broken_paginator_is_caught(self, reap):
        """Prove the test works by breaking the code.

        Replace the paginator with a bare `describe_volumes` on a scratch branch
        and confirm the test above goes red. A test you have never seen fail is a
        test you do not know works. Record the result in `DECISIONS.md`.
        """
        raise AssertionError("implement: see docstring - this one is a procedure, not an assertion")

    def test_zero_pages_does_not_crash(self, reap):
        """The empty-estate case that crashes on `pages[0]`."""
        outcome = reap(apply=False)
        assert outcome.deleted_ids == []
        assert outcome.exit_code == 0


class TestThrottling:
    def test_transient_throttling_is_retried_into_success(
        self, reap, unattached_volume, throttle_after
    ):
        """botocore's standard retry mode already handles this - five attempts,
        exponential backoff. The test proves you configured it rather than
        wrapping every call in your own decorator on top of it."""
        unattached_volume()
        throttle_after(after=2)
        outcome = reap(apply=False, older_than_days=0)
        assert outcome.exit_code == 0
        assert outcome.deleted_ids

    def test_exhausted_throttling_fails_loudly(self, reap, unattached_volume, throttle_after):
        """The worst possible outcome in this exercise is a **successful sweep of
        zero resources**. Throttled into oblivion must be an error, never an empty
        result with exit 0."""
        unattached_volume()
        throttle_after(after=0)
        outcome = reap(apply=False, older_than_days=0)
        assert outcome.exit_code != 0
        assert outcome.failures


class TestPartialFailure:
    def test_one_region_failing_preserves_the_others_results(self, reap, unattached_volume):
        """Region A works, region B raises. A's findings are in the output and B is
        reported as failed - both, not either."""
        raise AssertionError("implement: make OTHER_REGION raise, assert REGION's results present")

    def test_a_failed_delete_mid_run_is_reported_and_changes_the_exit_code(
        self, reap, unattached_volume
    ):
        """Four of five deletes succeed and the fifth raises `VolumeInUse`.

        The run must finish the other four, report the one, and exit non-zero.
        Exiting 0 here means a scheduled job silently leaves orphans behind
        forever.
        """
        raise AssertionError("implement: inject ClientError VolumeInUse on one DeleteVolume")

    def test_expired_credentials_mid_sweep(self, reap, unattached_volume):
        """A long sweep outliving its assumed-role session. E04 solves this
        properly with `RefreshableCredentials`; here you only have to **report** it
        rather than crash on it."""
        raise AssertionError("implement: raise ExpiredToken partway through")


class TestMalformedData:
    def test_a_resource_with_no_tags_at_all(self, reap, ec2):
        """The `KeyError` that takes down more infra scripts than any other.

        `describe_volumes` omits `Tags` entirely for an untagged volume - it does
        not return an empty list. `vol["Tags"]` raises, and it raises in the middle
        of a destructive run.
        """
        raise AssertionError("implement: create an untagged volume, assert the run completes")

    def test_error_branching_is_on_codes_not_message_strings(self, reap):
        """`err.response["Error"]["Code"] == "VolumeInUse"`, never
        `"in use" in str(err)`.

        Test it by raising a `ClientError` whose **message** does not contain the
        word at all while its code does. A string-matching implementation goes red
        here, which is the only way to prove you did not write one.
        """
        raise AssertionError(
            "implement: ClientError with code VolumeInUse and an unrelated message"
        )
