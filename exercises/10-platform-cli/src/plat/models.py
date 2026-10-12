"""Core types. Given to you complete; everything else is a stub."""

from __future__ import annotations

from datetime import datetime, timedelta
from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field


class EnvState(StrEnum):
    CREATING = "creating"
    READY = "ready"
    FAILED = "failed"
    DESTROYING = "destroying"


class Origin(StrEnum):
    """Where an effective config value came from.

    The ordering here **is** the precedence, highest first. `plat config show
    --origin` prints it, and that one command will save you more support
    questions than any other feature in the tool - "why is it deploying to
    staging" is almost always a config-precedence question.
    """

    FLAG = "flag"
    ENV_VAR = "env_var"
    PROJECT_CONFIG = "project_config"
    USER_CONFIG = "user_config"
    DEFAULT = "default"


class Environment(BaseModel):
    """One preview environment."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    name: str
    template: str
    owner: str
    state: EnvState = EnvState.CREATING
    created_at: datetime
    ttl: timedelta | None = None

    @property
    def expires_at(self) -> datetime | None:
        """None means no TTL, which should be rare and deliberate.

        Preview environments that never expire become permanent ones - and then
        production depends on one, and then nobody can delete it.
        """
        return None if self.ttl is None else self.created_at + self.ttl

    def is_expired(self, *, now: datetime) -> bool:
        """`now` is a parameter. Same reason as E01: testable without the clock."""
        expiry = self.expires_at
        return expiry is not None and now > expiry


class EffectiveValue(BaseModel):
    """One resolved config value, and where it came from."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    key: str
    value: str | int | bool | None
    origin: Origin
    # The file or variable it came from, when there is one. "project_config" is
    # an answer; "project_config (/Users/me/work/api/.plat.yaml)" ends the
    # conversation.
    source: str | None = None


class ValidationProblem(BaseModel):
    """One thing wrong with the config, in a form a human can act on.

    `hint` is required and non-empty on purpose. An error that only says what is
    wrong makes the user guess the fix; the brief's rule is errors that say what
    to do next.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    key: str
    problem: str = Field(min_length=1)
    hint: str = Field(min_length=1)
