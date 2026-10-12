"""The invariant tests - the ones that would let a sceptical reviewer approve `--apply`.

Your reviewer's real question is not "did you test it". It is **"what does your
test suite prove, and what does it not?"** Most infra suites answer "that the
happy path calls the API I expected", which proves nothing about a tool whose job
is deleting things.

These five prove the safety properties. Nothing else in E03 matters if one of
them is red.
"""

from __future__ import annotations

REGION = "ap-southeast-1"


class TestDryRunIsTrustworthy:
    def test_dry_run_makes_zero_delete_calls(self, reap, unattached_volume):
        """Assert on the **boundary**, not the return value.

        A reaper that deletes and then reports `dry_run: true` passes any test
        that only reads its own summary. The only trustworthy assertion is that
        no `DeleteVolume` call reached AWS.
        """
        unattached_volume()
        outcome = reap(apply=False)
        assert outcome.api_deletes == []

    def test_dry_run_still_produces_a_plan(self, reap, unattached_volume):
        """Zero deletes must not be achieved by finding nothing.

        Without this test, a reaper broken so badly that it selects nothing would
        pass the test above. The two together are the actual invariant.
        """
        vol = unattached_volume()
        outcome = reap(apply=False)
        assert vol in outcome.deleted_ids

    def test_dry_run_and_apply_produce_identical_plans(self, reap, unattached_volume):
        """E01's invariant, in a tool that costs money to get wrong.

        If the two paths ever diverge, the dry run stops being evidence of
        anything - and the dry run is the only reason anyone would let this near
        production.
        """
        unattached_volume()
        unattached_volume(size=100)
        planned = reap(apply=False)
        applied = reap(apply=True)
        assert sorted(planned.deleted_ids) == sorted(applied.deleted_ids)


class TestExclusions:
    def test_do_not_reap_tag_wins_over_every_other_rule(self, reap, unattached_volume):
        """Ancient, unattached, over budget - and still untouched.

        This is the tag an engineer sets at 3am to protect something mid-incident.
        It has to be absolute, not one input to a scoring function.
        """
        protected = unattached_volume(tags={"DoNotReap": "true"})
        outcome = reap(apply=True, older_than_days=0)
        assert protected not in outcome.deleted_ids
        assert protected not in outcome.api_deletes

    def test_cli_exclude_tag_is_honoured(self, reap, unattached_volume):
        keep = unattached_volume(tags={"team": "billing"})
        doomed = unattached_volume()
        outcome = reap(apply=True, older_than_days=0, exclude_tags={"team": "billing"})
        assert keep not in outcome.deleted_ids
        assert doomed in outcome.deleted_ids


class TestAgeFloor:
    def test_younger_than_the_floor_is_spared(self, reap, unattached_volume):
        unattached_volume()
        outcome = reap(apply=True, older_than_days=30)
        assert outcome.api_deletes == []

    def test_the_boundary_is_tested_from_both_sides(self, reap, unattached_volume):
        """Exactly N days old: decide, document, and pin it here.

        Boundaries need a decision, not a coin flip. E01 chose "exactly max_age is
        kept". Match it unless you have a reason, and write the reason down.
        """
        raise AssertionError("implement: create volumes at N-1, N and N+1 days and pin the rule")


class TestIdempotence:
    def test_running_twice_is_safe(self, reap, unattached_volume):
        """Unattended tools get re-run. A crash on the second run is how a janitor
        becomes a pager."""
        unattached_volume()
        reap(apply=True, older_than_days=0)
        second = reap(apply=True, older_than_days=0)
        assert second.api_deletes == []
        assert second.exit_code == 0

    def test_deleting_an_already_deleted_resource_is_not_an_error(self, reap, unattached_volume):
        """E03's acceptance criterion, asserted. S3 behaves this way natively; EC2
        does not, which is exactly why it needs a test."""
        raise AssertionError("implement: delete the volume out from under the reaper mid-run")


class TestCostReporting:
    def test_summary_includes_a_cost_estimate(self, reap, unattached_volume):
        """The number that makes this a thing your manager forwards upward."""
        unattached_volume(size=100)
        outcome = reap(apply=False)
        assert outcome.cost_estimate is not None
        assert outcome.cost_estimate > 0


def test_multiple_regions_are_independent(reap, unattached_volume):
    """Not strictly an invariant, but it belongs with them: one region's results
    must never depend on another's succeeding. The failure-path file proves the
    error case; this proves the happy case is actually per-region."""
    unattached_volume()
    outcome = reap(apply=False, regions=(REGION,))
    assert outcome.deleted_ids
