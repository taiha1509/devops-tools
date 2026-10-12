"""Core types. Given to you complete; everything else is a stub.

The one that carries the exercise is `ChangeKind.REPLACE`. In a plan's summary
line a replace looks like an update - "1 to add, 1 to destroy" buried among
thirty other lines - and in reality it is an outage. Modelling it as its own kind
rather than as an update-with-a-flag is why this tool can rank it correctly.
"""

from __future__ import annotations

from enum import IntEnum, StrEnum

from pydantic import BaseModel, ConfigDict


class ChangeKind(StrEnum):
    NO_OP = "no-op"
    CREATE = "create"
    UPDATE = "update-in-place"
    REPLACE = "replace"
    DESTROY = "destroy"
    # `terraform show -json` also emits "read" for data sources being refreshed.
    # Not a change to anything, but it appears in the array and must not be
    # miscounted as one.
    READ = "read"

    @property
    def destructive(self) -> bool:
        """Replace counts. That is the entire point of the tool."""
        return self in {ChangeKind.REPLACE, ChangeKind.DESTROY}


class Severity(IntEnum):
    """Ordered so comparison works: `Severity.HIGH > Severity.LOW`.

    `IntEnum` rather than `StrEnum` precisely so you can sort and threshold on it
    without a lookup table.
    """

    INFO = 0
    LOW = 1
    MEDIUM = 2
    HIGH = 3
    CRITICAL = 4


class ResourceChange(BaseModel):
    """One entry from the plan's `resource_changes` array, normalised."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    address: str
    resource_type: str
    name: str
    kind: ChangeKind
    severity: Severity = Severity.INFO
    # True when the plan differs from state without a corresponding code change -
    # the 3am console fix. Different from an intentional diff, and the whole
    # reason "drift" is in the tool's name.
    is_drift: bool = False
    # Attribute paths that changed. For a REPLACE these are the ones that forced
    # it, which is the single most useful line in the PR comment: "replaced
    # because `availability_zone` changed" is actionable, "replaced" is not.
    changed_attributes: tuple[str, ...] = ()

    def sort_key(self) -> tuple[int, str, str]:
        """Most severe first, then stable. Negated severity so ascending sort puts
        the dangerous things at the top where a reviewer will see them."""
        return (-int(self.severity), str(self.kind), self.address)


class PlanReport(BaseModel):
    """Everything the tool concluded about one plan."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    terraform_version: str = ""
    format_version: str = ""
    changes: tuple[ResourceChange, ...] = ()
    # Resource types with no entry in the severity map. Surfaced rather than
    # swallowed: an unknown type got the default severity, and the reviewer
    # should know the ranking was a guess.
    unknown_types: tuple[str, ...] = ()

    @property
    def destructive(self) -> tuple[ResourceChange, ...]:
        return tuple(c for c in self.changes if c.kind.destructive)

    @property
    def has_changes(self) -> bool:
        return any(c.kind is not ChangeKind.NO_OP for c in self.changes)

    def counts(self) -> dict[ChangeKind, int]:
        """Counts by category, for the comment's summary line."""
        out: dict[ChangeKind, int] = {}
        for change in self.changes:
            out[change.kind] = out.get(change.kind, 0) + 1
        return out
