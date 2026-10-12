"""Contract for blast-radius ranking.

The acceptance criterion that matters here: **unknown resource types are handled
with a documented default, never a crash.** An estate has hundreds of resource
types and your map has twenty-five.
"""

from __future__ import annotations

import pytest

from driftwatch.models import ChangeKind, Severity
from driftwatch.plan import parse_plan
from driftwatch.severity import (
    DEFAULT_UNKNOWN_SEVERITY,
    apply_severities,
    load_severity_map,
    severity_for,
)


class TestResourceTypeRanking:
    def test_a_database_outranks_an_alarm(self):
        """A replaced RDS instance and a replaced CloudWatch alarm are not the
        same event. Ranking them identically is what makes a 900-line plan
        unreadable."""
        db = severity_for("aws_db_instance", ChangeKind.REPLACE)
        alarm = severity_for("aws_cloudwatch_metric_alarm", ChangeKind.REPLACE)
        assert db > alarm

    def test_severity_is_comparable_without_a_lookup_table(self):
        """`IntEnum`, deliberately. This is why thresholding works."""
        assert Severity.CRITICAL > Severity.HIGH > Severity.MEDIUM > Severity.LOW


class TestKindModulatesSeverity:
    def test_destroying_outranks_creating_the_same_type(self):
        """Creating an RDS instance is not the same event as destroying one."""
        created = severity_for("aws_db_instance", ChangeKind.CREATE)
        destroyed = severity_for("aws_db_instance", ChangeKind.DESTROY)
        assert destroyed > created

    def test_replace_is_ranked_as_destructively_as_destroy(self):
        """The central claim of the exercise. A replace *is* a destroy, wearing an
        update's clothes in the summary line."""
        replaced = severity_for("aws_db_instance", ChangeKind.REPLACE)
        destroyed = severity_for("aws_db_instance", ChangeKind.DESTROY)
        assert replaced == destroyed

    def test_no_op_is_info(self):
        assert severity_for("aws_db_instance", ChangeKind.NO_OP) is Severity.INFO

    def test_a_security_group_rule_update_is_not_merely_one_step_down(self):
        """The case that argues with the default rule.

        An in-place update to a security-group rule can open your database to the
        internet. `update-in-place.json` contains exactly that: `10.0.0.0/8`
        becoming `0.0.0.0/0`. Decide whether to special-case it, then make this
        test say what you decided - and record it in `DECISIONS.md` either way.
        """
        raise AssertionError("implement: decide how an in-place security change ranks")


class TestUnknownTypes:
    def test_an_unknown_type_gets_the_default_not_a_crash(self):
        assert severity_for("snowflake_warehouse", ChangeKind.REPLACE) is DEFAULT_UNKNOWN_SEVERITY

    def test_unknown_types_are_reported_on_the_report(self, plan):
        """Surfaced rather than swallowed: the reviewer should know the ranking was
        a guess. `unknown-type.json` has two providers' worth."""
        report = apply_severities(parse_plan(plan("unknown-type")))
        assert "snowflake_warehouse" in report.unknown_types
        assert "datadog_monitor" in report.unknown_types

    def test_the_default_errs_toward_visibility(self):
        """An unranked type is an *unknown* blast radius, and the safe direction
        for an unknown is "a human should look at this".

        Defaulting unknowns to LOW means every new resource type is invisible
        until someone notices. Same asymmetry question E09 asks about its matrix.
        """
        assert DEFAULT_UNKNOWN_SEVERITY >= Severity.MEDIUM


class TestSeverityMapOverrides:
    def test_no_override_file_returns_the_defaults(self):
        assert load_severity_map(None)["aws_db_instance"] is Severity.CRITICAL

    def test_an_override_merges_rather_than_replaces(self, tmp_path):
        """A team bumping one resource type should not have to restate the other
        twenty-four."""
        override = tmp_path / "severity.yaml"
        override.write_text("aws_instance: critical\n")
        merged = load_severity_map(override)
        assert merged["aws_instance"] is Severity.CRITICAL
        assert merged["aws_db_instance"] is Severity.CRITICAL  # still there

    def test_a_typod_severity_name_is_rejected(self, tmp_path):
        """`criticial` silently falling back to the default is how someone's
        override quietly stops working six months after they wrote it."""
        override = tmp_path / "severity.yaml"
        override.write_text("aws_instance: criticial\n")
        with pytest.raises(ValueError, match="criticial"):
            load_severity_map(override)


class TestOrdering:
    def test_the_most_severe_change_sorts_first(self, plan):
        """The only ordering that makes a long plan readable: a reviewer reads the
        top of the comment, so the dangerous things have to be there."""
        report = apply_severities(parse_plan(plan("replace")))
        severities = [c.severity for c in report.changes]
        assert severities == sorted(severities, reverse=True)

    def test_ordering_is_stable_within_a_severity(self, plan):
        """Two runs on the same plan produce the same comment, so a re-push does
        not look like a change. Tie-break on address."""
        first = apply_severities(parse_plan(plan("creates-only")))
        second = apply_severities(parse_plan(plan("creates-only")))
        assert [c.address for c in first.changes] == [c.address for c in second.changes]
