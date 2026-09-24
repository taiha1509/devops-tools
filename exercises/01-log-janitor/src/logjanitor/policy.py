"""Retention policy evaluation.

This module is pure: no I/O, no clock, no AWS. That is deliberate - the hard part
of a destructive tool is deciding *what* to destroy, and you want that decision
testable without a filesystem or a network.

YOUR JOB: implement `select_for_deletion`.
"""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING
import re

if TYPE_CHECKING:
    from collections.abc import Iterable

    from logjanitor.models import Artifact, RetentionPolicy

class Desc:
    __slots__ = ("v",)
    def __init__(self, v): self.v = v
    def __lt__(self, other): return other.v < self.v
    def __eq__(self, other): return self.v == other.v

def sort_art(art: Artifact):
    return -art.modified_at.timestamp(), Desc(art.key)

def select_for_deletion(
    artifacts: Iterable[Artifact],
    policy: RetentionPolicy,
    *,
    now: datetime,
) -> list[Artifact]:
    """Decide which artifacts to delete. Returns them oldest-first.

    The algorithm, in order:

    1. **Protect.** An artifact whose `key` matches any `policy.protect_patterns`
       entry (fnmatch semantics) is never deletable.
    2. **Immunity.** The newest `policy.keep_minimum` artifacts - counted across
       *all* artifacts, protected or not - are never deletable.
    3. **Age pass.** If `policy.max_age` is set, mark every deletable artifact
       strictly older than it. Exactly `max_age` old is kept, not deleted.
    4. **Size pass.** If `policy.max_total_bytes` is set, sum the sizes of
       everything still retained (protected artifacts included - they really do
       occupy the disk). While that total exceeds the budget, mark the oldest
       remaining deletable artifact. If nothing deletable is left and the total is
       still over budget, stop and return what you have. Do not raise: an
       unsatisfiable budget is a reporting problem, not a crash.
    5. **Order.** Return marked artifacts sorted oldest-first.

    Ordering must be **deterministic**. Sort by `(modified_at, key)` ascending so
    that artifacts sharing a timestamp always resolve the same way. A reaper that
    picks a different victim on each run is not reviewable.

    Args:
        artifacts: candidates, in any order.
        policy: the rules to apply.
        now: the reference time for age calculations. Passed in, never read from
            the clock inside this function - that is what makes age policies
            testable without freezing time.

    Returns:
        The artifacts to delete, oldest-first. Empty list if the policy spares
        everything.
    """
    # step 1, check rule to protect art
    protected_artifacts: set[Artifact] = set()
    # loop through the protected rules
    for rule in policy.protect_patterns:
        for artifact in artifacts:
            if re.match(rule, artifact.key, re.IGNORECASE):
                protected_artifacts.add(artifact)
                continue
    # sort newest to oldest
    artifacts_sort_by_created: list[Artifact] = sorted(artifacts, key=sort_art)
    # step 2, check keep min config
    if policy.keep_minimum > 0:
        protected_artifacts.update(artifacts_sort_by_created[0:policy.keep_minimum])
    # step 3, check max_age
    remaining: list[Artifact] = [artifact for artifact in artifacts if artifact not in protected_artifacts]
    if len(remaining) == 0: return []
    deletable_artifacts = set()
    if policy.max_age:
        time_milestone = now - policy.max_age
        for art in remaining:
            # not too old to mark as deletable
            if art.modified_at < time_milestone:
                deletable_artifacts.add(art)
    # count total bytes for protected artifacts
    total_bytes_protected: int = sum([art.size_bytes for art in protected_artifacts])
    remaining: list[Artifact] = [artifact for artifact in artifacts if artifact not in protected_artifacts and artifact not in deletable_artifacts]
    # newest to oldest
    remaining.sort(key=sort_art)
    if policy.max_total_bytes:
        remaining_max_bytes = policy.max_total_bytes - total_bytes_protected
        total_bytes_remaining = sum([art.size_bytes for art in remaining])
        while remaining_max_bytes < total_bytes_remaining and len(remaining) > 0:
            deletable_art = remaining.pop()
            total_bytes_remaining -= deletable_art.size_bytes
            deletable_artifacts.add(deletable_art)

    # oldest to newest
    deletable_artifacts=sorted(deletable_artifacts, key=sort_art, reverse=True)
    return list(deletable_artifacts)
