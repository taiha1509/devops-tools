"""Core data types.

These are given to you complete. Everything else in this package is a stub.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta


@dataclass(frozen=True, slots=True)
class Artifact:
    """One stored object, wherever it lives.

    `key` is the store-relative identifier: a POSIX-style relative path for a
    filesystem store, an object key for an S3 store. Keep it store-relative so
    protect patterns behave the same regardless of backend.

    `modified_at` must be timezone-aware. Naive datetimes in an age policy are a
    real production bug class, so ruff's DTZ rules are on to stop you writing one.
    """

    key: str
    size_bytes: int
    modified_at: datetime


@dataclass(frozen=True, slots=True)
class RetentionPolicy:
    """What to keep. Every field is independently optional; they compose.

    max_age:         delete anything strictly older than this. None disables the rule.
    max_total_bytes: keep the retained total at or below this, deleting oldest-first.
                     None disables the rule.
    keep_minimum:    never let the sweep leave fewer than this many artifacts. The
                     newest `keep_minimum` artifacts are immune to every rule.
    protect_patterns: fnmatch patterns matched against `Artifact.key`. Matching
                     artifacts are never deleted - but they still occupy space, so
                     they still count toward max_total_bytes.
    """

    max_age: timedelta | None = None
    max_total_bytes: int | None = None
    keep_minimum: int = 0
    protect_patterns: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class SweepResult:
    """What a sweep did, or would have done.

    `deleted` is identical whether or not `dry_run` is set - that equivalence is
    the whole point of a dry run, and there is a test asserting it.
    """

    scanned: int
    deleted: list[Artifact] = field(default_factory=list)
    dry_run: bool = True

    @property
    def reclaimed_bytes(self) -> int:
        return sum(a.size_bytes for a in self.deleted)
