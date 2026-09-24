"""Contract for `select_for_deletion`.

Read these before you write any code: together they are the specification. Each
one encodes a decision that a real retention tool has to make, and getting them
green means you have made all of them deliberately.
"""

from __future__ import annotations

from datetime import timedelta, datetime, timezone

from logjanitor.models import RetentionPolicy
from logjanitor.policy import select_for_deletion


def test_empty_policy_selects_nothing(make_artifact, now):
    """No rules means no deletions, however old the artifact is.

    The pure function is permissive; the CLI is the layer that treats a
    rule-less invocation as user error.
    """
    artifacts = [make_artifact("ancient.log", days_old=999)]
    assert select_for_deletion(artifacts, RetentionPolicy(), now=now) == []


def test_age_rule_selects_only_what_is_older(make_artifact, now):
    old = make_artifact("old.log", days_old=10)
    fresh = make_artifact("fresh.log", days_old=1)
    policy = RetentionPolicy(max_age=timedelta(days=7))
    assert select_for_deletion([fresh, old], policy, now=now) == [old]


def test_age_boundary_is_exclusive(make_artifact, now):
    """Exactly max_age old is kept. Boundaries need a decision, not a coin flip."""
    # now = datetime.now(timezone.utc)
    print(f'now: {now}')
    exactly = make_artifact("exact.log", days_old=7)
    policy = RetentionPolicy(max_age=timedelta(days=7))
    assert select_for_deletion([exactly], policy, now=now) == []


def test_protected_patterns_are_never_selected(make_artifact, now):
    protected = make_artifact("keep/important.log", days_old=100)
    doomed = make_artifact("build/tmp.log", days_old=100)
    policy = RetentionPolicy(max_age=timedelta(days=1), protect_patterns=("keep/*",))
    assert select_for_deletion([protected, doomed], policy, now=now) == [doomed]


def test_keep_minimum_retains_newest_even_when_expired(make_artifact, now):
    """Everything has expired, but keep_minimum still leaves the newest behind.

    This is the rule that stops a misconfigured max_age from emptying the store.
    """
    a = make_artifact("a.log", days_old=30)
    b = make_artifact("b.log", days_old=20)
    c = make_artifact("c.log", days_old=10)
    policy = RetentionPolicy(max_age=timedelta(days=1), keep_minimum=1)
    assert select_for_deletion([a, b, c], policy, now=now) == [a, b]


def test_size_budget_deletes_oldest_first(make_artifact, now):
    a = make_artifact("a.log", days_old=3, size=100)
    b = make_artifact("b.log", days_old=2, size=100)
    c = make_artifact("c.log", days_old=1, size=100)
    policy = RetentionPolicy(max_total_bytes=200)
    # 300 bytes retained against a 200 budget: one has to go, and it is the oldest.
    assert select_for_deletion([c, a, b], policy, now=now) == [a]


def test_protected_artifacts_still_count_toward_the_budget(make_artifact, now):
    """Protection means "do not delete", not "does not occupy space".

    keep.log is the oldest thing here and would be the obvious victim, but it is
    immune - so the budget has to come out of the next-oldest deletable artifact.
    """
    protected = make_artifact("keep.log", days_old=10, size=100)
    a = make_artifact("a.log", days_old=5, size=100)
    b = make_artifact("b.log", days_old=1, size=100)
    policy = RetentionPolicy(max_total_bytes=200, protect_patterns=("keep.log",))
    assert select_for_deletion([protected, a, b], policy, now=now) == [a]


def test_unsatisfiable_budget_does_not_raise(make_artifact, now):
    """Protected data alone blows the budget. Delete what you can, then stop.

    An impossible budget is a reporting problem for the operator, not a crash in
    a scheduled job at 3am.
    """
    protected = make_artifact("big.log", days_old=10, size=500)
    a = make_artifact("a.log", days_old=5, size=100)
    policy = RetentionPolicy(max_total_bytes=50, protect_patterns=("big.log",))
    assert select_for_deletion([protected, a], policy, now=now) == [a]


def test_ties_are_broken_deterministically(make_artifact, now):
    """Identical timestamps must not produce a different victim on each run.

    Sorting by (modified_at, key) makes a.log the older of the two, always.
    """
    b = make_artifact("b.log", days_old=5, size=100)
    a = make_artifact("a.log", days_old=5, size=100)
    policy = RetentionPolicy(max_total_bytes=100)
    assert select_for_deletion([b, a], policy, now=now) == [a]
    assert select_for_deletion([a, b], policy, now=now) == [a]


def test_age_and_size_rules_compose(make_artifact, now):
    """Age pass first, then the size pass tops up if still over budget."""
    c = make_artifact("c.log", days_old=10, size=100)
    b = make_artifact("b.log", days_old=5, size=100)
    a = make_artifact("a.log", days_old=1, size=100)
    policy = RetentionPolicy(max_age=timedelta(days=7), max_total_bytes=100)
    # Age takes c (300 -> 200). Still over 100, so b goes too.
    assert select_for_deletion([a, b, c], policy, now=now) == [c, b]
