"""Core types. Given to you complete; everything else is a stub.

`GENERATED_MARKER` and `TemplateVersion` are the two ideas that make this a
fleet-management tool rather than a one-off generator. Everything else is
plumbing.
"""

from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field

GENERATED_MARKER = "scaffolder:generated"
"""Marks a file as owned by the tool.

The ownership rule, which has to be decided once and enforced everywhere:
**files carrying this marker belong to the scaffolder and are overwritten on
regeneration; everything else belongs to the team and is never touched.**

Any other rule collapses. "Overwrite unless modified" needs a hash of the
original, and the first time someone reformats a generated file the tool either
clobbers their change or stops updating that file forever. An explicit marker
makes the contract visible in the file itself, to a human reading it in six
months.
"""

STAMP_FILE = ".scaffolder.yaml"
"""Records which template version produced this service.

Without this you cannot answer "which services have the old CI config?" - and
answering that question is the entire long-term value of the tool. A generator
that cannot report on its own output is a one-off script with extra steps.
"""


class DriftKind(StrEnum):
    """How a generated file differs from what the current template produces."""

    MISSING = "missing"  # template has it, service does not
    MODIFIED = "modified"  # generated file was hand-edited, or the template moved on
    EXTRA = "extra"  # service has a generated file the template no longer emits
    UP_TO_DATE = "up_to_date"


class ServiceSpec(BaseModel):
    """The inputs to a generation. Validated **before** any file is written."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    # Org naming convention: lowercase, hyphens, no leading digit. Enforced here
    # rather than in the CLI so `--check` and generation cannot disagree.
    name: str = Field(pattern=r"^[a-z][a-z0-9]*(-[a-z0-9]+)*$", min_length=3, max_length=40)
    template: str
    team: str
    description: str = ""


class TemplateVersion(BaseModel):
    """A template's identity, stamped into every service it generates."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    name: str
    version: str


class RenderedFile(BaseModel):
    """One file a template would produce. Rendered in memory first.

    Rendering everything before writing anything is what makes "fail before
    writing a single file, never halfway through" achievable - a template error
    on file nine must not leave eight files on disk.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    path: str
    content: str
    generated: bool = True
    # Some files are seeded once and then owned by the team: the service's actual
    # source, its README body. Marked `generated=False` so regeneration leaves
    # them alone.
    executable: bool = False


class DriftFinding(BaseModel):
    """One difference between a service and its template's current output."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    path: str
    kind: DriftKind
    detail: str = ""
