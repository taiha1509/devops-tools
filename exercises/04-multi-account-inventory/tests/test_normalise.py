"""Contract for the normalisers.

Read these before writing any code: together they are the specification. The tag
cases are not hypothetical - every one of them is a shape AWS actually returns,
and the `KeyError` they prevent takes down more infrastructure scripts than any
other single bug.

E06 strengthens this file with Hypothesis properties. These are the hand-written
cases that pin down the decisions; the properties find the ones nobody imagined.
"""

from __future__ import annotations

from datetime import UTC, datetime

import pytest

from inventory.models import ResourceType
from inventory.normalise import (
    normalise_all,
    normalise_ec2_instance,
    normalise_lambda_function,
    normalise_tags,
)

ACCOUNT_A = "111111111111"


class TestNormaliseTags:
    def test_ec2_taglist_shape(self):
        raw = [{"Key": "Owner", "Value": "billing"}, {"Key": "env", "Value": "prod"}]
        assert normalise_tags(raw) == {"Owner": "billing", "env": "prod"}

    def test_lambda_dict_shape(self):
        assert normalise_tags({"Owner": "billing"}) == {"Owner": "billing"}

    @pytest.mark.parametrize("empty", [None, [], {}])
    def test_absent_tags_are_an_empty_dict_not_a_crash(self, empty):
        """The single most common infra-script bug. It is a `{}`, never a raise."""
        assert normalise_tags(empty) == {}

    def test_tag_without_value_keeps_the_key(self):
        """A key with no value is still a key, and presence is what we query on."""
        assert normalise_tags([{"Key": "Owner"}]) == {"Owner": ""}

    def test_tag_without_key_is_skipped(self):
        """No key means nothing can query it, so it cannot be represented."""
        assert normalise_tags([{"Value": "orphan"}]) == {}

    def test_values_are_not_coerced(self):
        """`Owner: "true"` is the string "true". Guessing types gives you `Owner: True`."""
        assert normalise_tags([{"Key": "flag", "Value": "true"}]) == {"flag": "true"}


class TestNormaliseEc2:
    def test_maps_every_field(self, raw_ec2_instance):
        res = normalise_ec2_instance(raw_ec2_instance, account_id=ACCOUNT_A, region="eu-west-1")
        assert res.resource_id == "i-0abc123"
        assert res.resource_type is ResourceType.EC2_INSTANCE
        assert res.account_id == ACCOUNT_A
        assert res.region == "eu-west-1"
        assert res.public_ip == "203.0.113.17"
        assert res.tags["Owner"] == "billing"

    def test_name_comes_from_the_name_tag(self, raw_ec2_instance):
        res = normalise_ec2_instance(raw_ec2_instance, account_id=ACCOUNT_A, region="eu-west-1")
        assert res.name == "web-01"

    def test_private_instance_has_no_public_ip(self, raw_ec2_instance):
        """Absent, not empty string. `--public-ip` filtering depends on the difference."""
        del raw_ec2_instance["PublicIpAddress"]
        res = normalise_ec2_instance(raw_ec2_instance, account_id=ACCOUNT_A, region="eu-west-1")
        assert res.public_ip is None

    def test_launch_time_stays_timezone_aware(self, raw_ec2_instance):
        res = normalise_ec2_instance(raw_ec2_instance, account_id=ACCOUNT_A, region="eu-west-1")
        assert res.created_at is not None
        assert res.created_at.tzinfo is not None


class TestNormaliseLambda:
    def test_last_modified_string_is_parsed(self):
        """Lambda returns ISO-8601 **text** where EC2 returns a datetime."""
        raw = {"FunctionName": "charge-card", "LastModified": "2026-01-15T09:30:00.000+0000"}
        res = normalise_lambda_function(raw, account_id=ACCOUNT_A, region="eu-west-1")
        assert res.created_at == datetime(2026, 1, 15, 9, 30, tzinfo=UTC)

    def test_list_functions_returns_no_tags(self):
        """Not a bug in your code - `ListFunctions` genuinely omits them. `{}`, not a crash."""
        raw = {"FunctionName": "charge-card", "LastModified": "2026-01-15T09:30:00.000+0000"}
        res = normalise_lambda_function(raw, account_id=ACCOUNT_A, region="eu-west-1")
        assert res.tags == {}


class TestNormaliseAll:
    def test_count_is_preserved(self, raw_ec2_instance):
        """N in, N out. The invariant that would have caught E06's 1,200-vs-4,100 bug.

        Not "no exception raised" - an exact count. A normaliser that drops the
        resources it cannot parse produces a plausible, wrong, silent answer, and
        that is the defining bug class of infrastructure tooling.
        """
        raw = [dict(raw_ec2_instance, InstanceId=f"i-{n}") for n in range(5)]
        out = normalise_all(
            raw, normaliser="ec2_instance", account_id=ACCOUNT_A, region="eu-west-1"
        )
        assert len(out) == 5

    def test_a_resource_with_no_tags_at_all_survives(self):
        """The `KeyError` case, at the level that matters: the whole batch, not one item."""
        raw = [{"InstanceId": "i-notags"}]
        out = normalise_all(
            raw, normaliser="ec2_instance", account_id=ACCOUNT_A, region="eu-west-1"
        )
        assert len(out) == 1
        assert out[0].tags == {}

    def test_empty_input_is_an_empty_list(self):
        out = normalise_all([], normaliser="ec2_instance", account_id=ACCOUNT_A, region="eu-west-1")
        assert out == []
