"""Contract for parsing and classification.

`classify_actions` is five lines long and carries most of the exercise's value.
The `replace` cases are the reason: in a plan's summary line a replace looks like
an update, and in reality it is an outage.
"""

from __future__ import annotations

import pytest

from driftwatch.models import ChangeKind
from driftwatch.plan import (
    UnsupportedPlanFormat,
    classify_actions,
    detect_drift,
    load_plan,
    parse_plan,
)


class TestClassifyActions:
    @pytest.mark.parametrize(
        ("actions", "expected"),
        [
            (["no-op"], ChangeKind.NO_OP),
            (["create"], ChangeKind.CREATE),
            (["update"], ChangeKind.UPDATE),
            (["delete"], ChangeKind.DESTROY),
            (["read"], ChangeKind.READ),
        ],
    )
    def test_single_actions(self, actions, expected):
        assert classify_actions(actions) is expected

    def test_delete_then_create_is_a_replace(self):
        assert classify_actions(["delete", "create"]) is ChangeKind.REPLACE

    def test_create_then_delete_is_also_a_replace(self):
        """`create_before_destroy = true` produces this ordering.

        An implementation that only checks `["delete", "create"]` misses every
        resource in a module using the lifecycle block - which tends to be the
        carefully-managed, high-blast-radius ones.
        """
        assert classify_actions(["create", "delete"]) is ChangeKind.REPLACE

    def test_an_unrecognised_actions_array_raises(self):
        """Loudly, naming it. A silent fallback to NO_OP would report a destroy
        as nothing at all, which is the worst available outcome."""
        with pytest.raises(ValueError, match="forget-me-not"):
            classify_actions(["forget-me-not"])


class TestParsePlan:
    def test_a_clean_plan_has_no_changes(self, plan):
        report = parse_plan(plan("no-changes"))
        assert report.has_changes is False

    def test_a_data_source_read_is_not_counted_as_a_change(self, plan):
        """`no-changes.json` contains a `read` entry. It is in `resource_changes`
        but it changes nothing, and counting it would make every plan look dirty."""
        report = parse_plan(plan("no-changes"))
        assert report.counts().get(ChangeKind.READ) == 1
        assert report.has_changes is False

    def test_an_absent_resource_changes_key_is_handled(self, plan):
        """`empty.json` has no `resource_changes` key at all - not an empty array.

        `document["resource_changes"]` raises on exactly the input you most want
        to handle gracefully.
        """
        report = parse_plan(plan("empty"))
        assert report.changes == ()
        assert report.has_changes is False

    def test_both_replaces_are_found(self, plan):
        report = parse_plan(plan("replace"))
        assert len(report.destructive) == 2

    def test_replace_paths_become_changed_attributes(self, plan):
        """ "Replaced because `availability_zone` changed" is actionable.
        "Replaced" is not. This is the most useful line in the whole comment."""
        report = parse_plan(plan("replace"))
        rds = next(c for c in report.changes if c.resource_type == "aws_db_instance")
        assert "availability_zone" in rds.changed_attributes

    def test_module_addresses_are_preserved(self, plan):
        """`creates-only.json` has one resource inside `module.api`. The address
        must stay fully qualified or two resources called `handler` collide."""
        report = parse_plan(plan("creates-only"))
        assert any(c.address.startswith("module.api.") for c in report.changes)

    def test_counts_by_category(self, plan):
        report = parse_plan(plan("creates-only"))
        assert report.counts()[ChangeKind.CREATE] == 3


class TestDriftDetection:
    def test_true_drift_is_found_in_resource_drift(self, plan):
        """The console fix. Terraform reports it in a **separate top-level array**
        from the plan, and that distinction is the whole reason the tool is called
        driftwatch - a plan diff caused by editing `.tf` is not drift."""
        drifted = detect_drift(plan("true-drift"))
        assert "aws_security_group_rule.emergency_ingress" in drifted

    def test_an_intentional_change_is_not_drift(self, plan):
        """The alarm threshold in the same fixture changed in code, not in the
        console. It appears in `resource_changes` but not in `resource_drift`."""
        drifted = detect_drift(plan("true-drift"))
        assert "aws_cloudwatch_metric_alarm.cpu" not in drifted

    def test_no_resource_drift_key_is_an_empty_set_not_an_error(self, plan):
        """The common case: most plans have no drift at all."""
        assert detect_drift(plan("creates-only")) == frozenset()


class TestFormatVersion:
    def test_a_missing_format_version_is_rejected(self, tmp_path):
        """Guessing at an unknown format is how a drift detector starts reporting
        "no changes" for every plan after a Terraform upgrade."""
        bad = tmp_path / "bad.json"
        bad.write_text('{"terraform_version": "1.9.5"}')
        with pytest.raises(UnsupportedPlanFormat):
            load_plan(bad)

    def test_a_future_major_version_is_rejected(self, tmp_path):
        bad = tmp_path / "future.json"
        bad.write_text('{"format_version": "99.0", "terraform_version": "99.0.0"}')
        with pytest.raises(UnsupportedPlanFormat):
            load_plan(bad)

    def test_a_supported_version_loads(self, plan_path):
        document = load_plan(plan_path("creates-only"))
        assert document["format_version"].startswith("1.")
