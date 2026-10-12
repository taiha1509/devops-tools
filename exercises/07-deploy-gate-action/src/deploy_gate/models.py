"""Core types. Given to you complete; everything else is a stub.

Note `GateDecision.allowed` is a bool and `reason` is never empty. A gate that
blocks without saying why is a gate people route around, and "the deploy gate
failed" in a Slack thread at 17:40 on a Friday is not a reason.
"""

from __future__ import annotations

from datetime import datetime, time
from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field


class Weekday(StrEnum):
    """ISO weekday names. Config is written by humans, so it reads as text."""

    MONDAY = "monday"
    TUESDAY = "tuesday"
    WEDNESDAY = "wednesday"
    THURSDAY = "thursday"
    FRIDAY = "friday"
    SATURDAY = "saturday"
    SUNDAY = "sunday"


class GateName(StrEnum):
    FREEZE = "freeze"
    ERROR_BUDGET = "error_budget"
    OPEN_INCIDENT = "open_incident"


class RecurringWindow(BaseModel):
    """ "Every Friday from 14:00 to 23:59, in this timezone."

    `timezone` is **required**, with no default. That is the entire point of this
    model: the bash gate it replaces compared `date +%u` to `5` on the runner,
    which meant the freeze started at a different wall-clock moment depending on
    which region the runner booted in. There is no sensible default timezone for
    a company-wide change freeze, so the config has to say.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    days: tuple[Weekday, ...]
    start: time
    end: time
    timezone: str
    label: str = ""


class OneOffWindow(BaseModel):
    """ "From 2026-12-20 until 2027-01-02." Both bounds tz-aware."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    start: datetime
    end: datetime
    label: str = ""


class FreezeConfig(BaseModel):
    """The contents of `.github/freeze.yaml`."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    recurring: tuple[RecurringWindow, ...] = ()
    one_off: tuple[OneOffWindow, ...] = ()
    # Environments the freeze does not apply to. A freeze that blocks deploys to
    # a developer's preview environment teaches people to use the override, and
    # an override used daily is not an override.
    exempt_environments: tuple[str, ...] = ()


class GateResult(BaseModel):
    """One gate's verdict."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    gate: GateName
    allowed: bool
    reason: str = Field(min_length=1)
    # True when the gate could not reach what it needed and blocked as a result.
    # Distinguished from a real block because they need different fixes: one is a
    # policy decision, the other is broken infrastructure.
    failed_closed: bool = False


class GateDecision(BaseModel):
    """The whole gate's verdict, which is what the job's exit code comes from."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    allowed: bool
    reason: str = Field(min_length=1)
    results: tuple[GateResult, ...] = ()
    overridden: bool = False
    override_actor: str | None = None
    override_reason: str | None = None

    @property
    def blocking(self) -> tuple[GateResult, ...]:
        """Every gate that said no, in evaluation order."""
        return tuple(r for r in self.results if not r.allowed)
