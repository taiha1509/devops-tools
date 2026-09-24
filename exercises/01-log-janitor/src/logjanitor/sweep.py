"""Orchestration: list, decide, (maybe) delete, report.

YOUR JOB: implement `sweep`.
"""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from logjanitor.policy import select_for_deletion

from logjanitor.models import RetentionPolicy, SweepResult
from logjanitor.store import ArtifactStore
from logjanitor.cli import log

def sweep(
    store: ArtifactStore,
    policy: RetentionPolicy,
    *,
    now: datetime,
    dry_run: bool = True,
) -> SweepResult:
    """Apply `policy` to everything in `store`.

    The invariant that makes this tool reviewable: **the plan does not depend on
    `dry_run`.** A dry run and a real run select exactly the same artifacts and
    report exactly the same numbers; the only difference is whether
    `store.delete` is called. If the two paths ever diverge, the dry run stops
    being evidence of anything. There is a test for this.

    `dry_run` defaults to True. Destructive tools default to safe.

    Log one structured event per deletion and one summary event at the end - see
    `cli.py` for the required shape. Logging belongs here rather than in
    `policy.py` so the decision logic stays pure and trivially testable.

    Returns:
        A SweepResult with `scanned` set to the number of artifacts listed and
        `deleted` to those selected (whether or not they were actually removed).
    """


    all_arts = list(store.list_artifacts())

    deletable_artifacts = select_for_deletion(all_arts, policy, now=now)
    sweep_rs = SweepResult(dry_run=dry_run, scanned=len(all_arts), deleted=deletable_artifacts)
    if not dry_run:
        for art in deletable_artifacts:
            store.delete(art)
    return sweep_rs
