"""Attributing spend to the team that caused it. Pure.

YOUR JOB: implement `attribute` and `untagged_total`.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Iterable, Mapping, Sequence

    from cost_watch.models import DailyCost


def attribute(
    costs: Iterable[DailyCost],
    *,
    team_by_tag: Mapping[str, str] | None = None,
) -> list[DailyCost]:
    """Resolve each record's `owner` to a real team name.

    `team_by_tag` maps raw tag values to canonical team names, because tag
    hygiene is never what you would like: `billing`, `Billing`, `billing-team`
    and `team-billing` are all the same people, and treating them as four owners
    splits one $8,000 finding into four $2,000 ones that each fall under the
    dollar floor. That is a real way to make a genuine anomaly disappear.

    Normalise case and whitespace before looking up. An unmapped non-empty tag
    value stays as itself rather than becoming `UNTAGGED` - the team exists, your
    mapping is just incomplete, and saying so is more useful than hiding it.
    """
    raise NotImplementedError


def untagged_total(costs: Iterable[DailyCost]) -> float:
    """Total spend with no owner tag.

    Reported **prominently**, as its own line. "$14,000 of untagged spend" is a
    finding: it is money nobody can be asked about, and it is usually the first
    thing a FinOps conversation needs. Folding it into an "other" bucket is the
    easiest way to make this whole report ignorable.
    """
    raise NotImplementedError


def top_owners(costs: Iterable[DailyCost], *, limit: int = 5) -> list[tuple[str, float]]:
    """The biggest spenders, descending. Ties broken by name for stable output."""
    raise NotImplementedError


def coverage(costs: Sequence[DailyCost]) -> float:
    """Fraction of spend that carries an owner tag, 0.0-1.0.

    Worth trending over time. Tag coverage going **down** means new resources are
    being created untagged, which is a process problem the scaffolder in E11 is
    meant to solve - and a number you can put in front of people.
    """
    raise NotImplementedError


__all__ = ["attribute", "coverage", "top_owners", "untagged_total"]
