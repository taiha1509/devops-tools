"""Reading `terraform show -json`. Pure: a parsed document in, models out.

**Parse the JSON, never the human-readable output.** The JSON plan format is
documented and versioned; the text output is for humans and changes between
minor releases. Scraping `terraform plan`'s text is how you build something that
breaks on the next upgrade, at which point it silently reports "no changes".

YOUR JOB: implement `load_plan` and `parse_plan`.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from pathlib import Path

    from driftwatch.models import ChangeKind, PlanReport


class UnsupportedPlanFormat(Exception):
    """The document is not a plan, or is a format version we do not handle.

    Exit 2, with a message naming the version found. Guessing at an unknown
    format is how a drift detector starts reporting "no changes" for every plan.
    """


def load_plan(path: Path) -> dict[str, Any]:
    """Read and minimally validate the plan JSON.

    Check `format_version` is present and that the major version is one you
    support (`"1.x"` at time of writing). A plan file is also sometimes
    *enormous* - hundreds of MB for a large estate - so if you find yourself
    wanting to stream it, note that in `DECISIONS.md` rather than doing it now.

    Raises:
        UnsupportedPlanFormat: missing or unsupported `format_version`.
    """
    raise NotImplementedError


def classify_actions(actions: list[str]) -> ChangeKind:
    """Map the plan's `actions` array onto a `ChangeKind`.

    This is the whole trick of the exercise, and it is a five-line function:

        ["no-op"]            -> NO_OP
        ["create"]           -> CREATE
        ["update"]           -> UPDATE
        ["delete"]           -> DESTROY
        ["delete", "create"] -> REPLACE   destroy-then-create
        ["create", "delete"] -> REPLACE   create-before-destroy
        ["read"]             -> READ      a data source, not a change

    **Both two-element orderings are a replace.** `["create", "delete"]` is what
    you get with `create_before_destroy = true`, and an implementation that only
    checks for `["delete", "create"]` misses every resource in a module that uses
    the lifecycle block - which tends to be the carefully-managed ones.

    Raises:
        ValueError: an actions array you have never seen. Loudly, naming it. A
            silent fallback to NO_OP here would report a destroy as nothing.
    """
    raise NotImplementedError


def parse_plan(document: dict[str, Any]) -> PlanReport:
    """Turn the plan document into a `PlanReport`.

    Walk `resource_changes`. For each entry take `address`, `type`, `name`, and
    `change.actions`. Note:

        * `resource_changes` can be **absent entirely** (an empty plan), not just
          empty. `document["resource_changes"]` raises on exactly the input you
          most want to handle gracefully.
        * `mode` is `"managed"` or `"data"`. Data sources are reads, not changes.
        * For a REPLACE, `change.replace_paths` names the attributes that forced
          it. Put them in `changed_attributes` - "replaced because
          `availability_zone` changed" is the most useful line in the whole
          comment.
        * Severity is **not** assigned here. That is `severity.py`'s job, and
          keeping them apart is what lets the severity map be configurable
          without touching the parser.
    """
    raise NotImplementedError


def detect_drift(document: dict[str, Any]) -> frozenset[str]:
    """Addresses whose change came from outside Terraform. The 3am console fix.

    Terraform reports this separately from the plan: `resource_drift` is a
    top-level array, populated when the refresh found state and reality
    disagreeing. That is *different* from a plan diff caused by someone editing
    `.tf`, and conflating the two is why the original outage happened - the
    console fix looked like an ordinary intentional diff and got reverted.

    Returns:
        The set of drifted addresses. Empty when `resource_drift` is absent,
        which is the common case and not an error.
    """
    raise NotImplementedError


__all__ = ["UnsupportedPlanFormat", "classify_actions", "detect_drift", "load_plan", "parse_plan"]
