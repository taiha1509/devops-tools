"""Core types. Given to you complete; everything else is a stub.

`Inclusion` is the one worth reading twice. Every service in the matrix carries
the reason it got there, because `--explain` is not a debugging nicety - it is
the feature that makes the tool trustworthy. Nobody will believe the tool the
first time it skips their service, and they are right not to.
"""

from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel, ConfigDict


class Reason(StrEnum):
    """Why a service is in the matrix."""

    DIRECTLY_CHANGED = "directly_changed"
    DEPENDENCY_CHANGED = "dependency_changed"
    GLOBAL_TRIGGER = "global_trigger"
    # The fail-safe paths. Both mean "we could not work it out, so we are
    # building everything" - and both must be visible in `--explain`, because a
    # tool that silently degrades to build-all has stopped being a tool and
    # become a 40-minute CI run again.
    UNPARSEABLE_MANIFEST = "unparseable_manifest"
    MATRIX_LIMIT_EXCEEDED = "matrix_limit_exceeded"


class Service(BaseModel):
    """One buildable unit, as declared by its own manifest."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    name: str
    path: str
    depends_on: tuple[str, ...] = ()
    # Extra matrix dimensions this service needs, e.g. {"python": ["3.12", "3.13"]}.
    # Note these multiply against the service count when you check the 256 cap.
    extra: dict[str, tuple[str, ...]] = {}


class Inclusion(BaseModel):
    """One matrix entry, and why it exists."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    service: str
    reason: Reason
    # The changed file or dependency that caused it. For a transitive inclusion
    # this is the whole chain - "L -> A -> B" - because "B was included because A
    # changed" is not an explanation when A did not change either.
    because: tuple[str, ...] = ()


class Plan(BaseModel):
    """The computed build plan."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    inclusions: tuple[Inclusion, ...] = ()
    changed_files: tuple[str, ...] = ()
    degraded: bool = False
    degraded_reason: str = ""

    @property
    def services(self) -> tuple[str, ...]:
        """Service names, sorted and deduplicated. Deterministic output matters
        here for the same reason it does in E04: a matrix that reorders between
        runs makes the Actions UI unreadable and breaks required-check names."""
        return tuple(sorted({i.service for i in self.inclusions}))

    @property
    def empty(self) -> bool:
        return not self.inclusions
