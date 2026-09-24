"""Contract for `sweep` - above all, the dry-run invariant."""

from __future__ import annotations

from datetime import timedelta

from logjanitor.models import Artifact, RetentionPolicy
from logjanitor.sweep import sweep


class RecordingStore:
    """Test double: records deletions instead of performing them.

    Satisfies the ArtifactStore protocol structurally - no inheritance needed,
    which is the point of using a Protocol for the seam.
    """

    def __init__(self, artifacts: list[Artifact]) -> None:
        self._artifacts = list(artifacts)
        self.deleted: list[Artifact] = []

    def list_artifacts(self) -> list[Artifact]:
        return list(self._artifacts)

    def delete(self, artifact: Artifact) -> None:
        self.deleted.append(artifact)


EXPIRE_AFTER_A_DAY = RetentionPolicy(max_age=timedelta(days=1))


def test_defaults_to_dry_run(make_artifact, now):
    store = RecordingStore([make_artifact("a.log", days_old=99)])
    result = sweep(store, EXPIRE_AFTER_A_DAY, now=now)
    assert result.dry_run is True
    assert store.deleted == []


def test_dry_run_never_calls_delete_but_still_reports(make_artifact, now):
    store = RecordingStore([make_artifact("a.log", days_old=99)])
    result = sweep(store, EXPIRE_AFTER_A_DAY, now=now, dry_run=True)
    assert store.deleted == []
    assert [a.key for a in result.deleted] == ["a.log"]
    assert result.reclaimed_bytes == 100


def test_dry_run_plan_is_identical_to_the_real_plan(make_artifact, now):
    """The invariant that makes a dry run evidence rather than theatre.

    If these two ever diverge, nobody can approve a destructive run by reading
    its dry-run output - which is the only way such a run ever gets approved.
    """
    artifacts = [make_artifact("a.log", days_old=99), make_artifact("b.log", days_old=0)]

    planned = sweep(RecordingStore(artifacts), EXPIRE_AFTER_A_DAY, now=now, dry_run=True)
    applied = sweep(RecordingStore(artifacts), EXPIRE_AFTER_A_DAY, now=now, dry_run=False)

    assert planned.deleted == applied.deleted
    assert planned.scanned == applied.scanned
    assert planned.reclaimed_bytes == applied.reclaimed_bytes


def test_apply_deletes_through_the_store(make_artifact, now):
    doomed = make_artifact("a.log", days_old=99)
    store = RecordingStore([doomed, make_artifact("b.log", days_old=0)])

    result = sweep(store, EXPIRE_AFTER_A_DAY, now=now, dry_run=False)

    assert store.deleted == [doomed]
    assert result.dry_run is False


def test_scanned_counts_everything_listed_not_just_deletions(make_artifact, now):
    store = RecordingStore([make_artifact(f"{i}.log", days_old=i) for i in range(5)])
    result = sweep(store, RetentionPolicy(max_age=timedelta(days=3)), now=now)
    assert result.scanned == 5
    assert [a.key for a in result.deleted] == ["4.log"]
