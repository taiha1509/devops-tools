"""Part 2 - normalisation, property-based.

Hand-written tests check the cases you imagined. Property tests find the ones you
did not, and E04's normaliser is exactly the kind of code where the cases you did
not imagine are the ones AWS returns.

The acceptance criterion is sharp: **Hypothesis must find at least one real bug in
your E04 normaliser.** If it does not, your properties are too weak. Strengthen
them before concluding the code is perfect.
"""

from __future__ import annotations

from hypothesis import given, settings
from hypothesis import strategies as st
from inventory.models import Resource
from inventory.normalise import normalise_all, normalise_ec2_instance, normalise_tags

from strategies import ACCOUNT_A, REGION, raw_ec2_instances, raw_tags


class TestTotality:
    """No input shape raises. The property that subsumes a dozen hand-written tests."""

    @given(raw_tags)
    def test_normalise_tags_never_raises(self, raw):
        """Absent, None, empty, list-of-dicts, dict, entries missing Key or Value."""
        assert isinstance(normalise_tags(raw), dict)

    @given(raw_ec2_instances())
    def test_normalise_ec2_never_raises(self, raw):
        assert isinstance(
            normalise_ec2_instance(raw, account_id=ACCOUNT_A, region=REGION), Resource
        )

    @given(st.text(max_size=20))
    def test_a_none_resource_id_is_rejected_not_crashed_on(self, rid):
        """Decide what an identifier-less resource means and enforce it.

        Dropping it silently is the bug this whole exercise exists to kill, so the
        answer is almost certainly "raise, loudly, naming the account and region".
        Whatever you choose, it must be deliberate.
        """
        raise AssertionError("implement: decide and pin the rule for a missing identifier")


class TestCountPreservation:
    """The property that would have caught the dropped-tags bug."""

    @given(st.lists(raw_ec2_instances(), min_size=0, max_size=30))
    @settings(max_examples=200)
    def test_n_in_n_out(self, raws):
        """Normalising N raw resources yields exactly N records. Never fewer.

        This is the single most valuable property in the file. A normaliser that
        skips what it cannot parse produces a plausible, silent, wrong answer -
        and "1,200 instead of 4,100" is what that looks like in production.
        """
        out = normalise_all(raws, normaliser="ec2_instance", account_id=ACCOUNT_A, region=REGION)
        assert len(out) == len(raws)

    @given(st.lists(raw_ec2_instances(), max_size=20))
    def test_resources_with_no_tag_block_are_not_dropped(self, raws):
        stripped = [{k: v for k, v in r.items() if k != "Tags"} for r in raws]
        out = normalise_all(
            stripped, normaliser="ec2_instance", account_id=ACCOUNT_A, region=REGION
        )
        assert len(out) == len(stripped)


class TestIdempotence:
    @given(raw_tags)
    def test_normalising_tags_twice_equals_once(self, raw):
        once = normalise_tags(raw)
        assert normalise_tags(once) == once


class TestDeterminism:
    @given(st.lists(raw_ec2_instances(), min_size=2, max_size=15))
    def test_input_order_does_not_change_the_result_set(self, raws):
        """Reversed input, same set of records out.

        E04's `collect()` sorts before returning precisely so that a thread
        finishing in a different order cannot change the output. This is that
        guarantee, at the normaliser level.
        """
        forward = normalise_all(
            raws, normaliser="ec2_instance", account_id=ACCOUNT_A, region=REGION
        )
        backward = normalise_all(
            list(reversed(raws)), normaliser="ec2_instance", account_id=ACCOUNT_A, region=REGION
        )
        assert sorted(r.sort_key() for r in forward) == sorted(r.sort_key() for r in backward)


class TestRoundTrip:
    @given(raw_ec2_instances())
    def test_serialise_deserialise_is_identity(self, raw):
        """The dataset is written to JSON and read back by `inventory query`. If
        the round trip is lossy, every query result is quietly wrong."""
        res = normalise_ec2_instance(raw, account_id=ACCOUNT_A, region=REGION)
        assert Resource.model_validate_json(res.model_dump_json()) == res


def test_record_the_bug_hypothesis_found():
    """Acceptance criterion, as a test so you cannot skip it.

    Hypothesis must find at least one real bug in your E04 normaliser. Write the
    falsifying example and the fix into `DECISIONS.md`, then delete this test.

    If nothing was found: the properties are too weak, not the code too good.
    Widen the strategies in `conftest.py` first - unicode tag values, a `None`
    identifier, a naive timestamp, an empty-string key.
    """
    raise AssertionError("implement: record the falsifying example, then delete this test")
