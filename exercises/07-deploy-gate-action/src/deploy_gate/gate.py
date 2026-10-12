"""Orchestration: run every gate, combine the verdicts, handle the override.

YOUR JOB: implement `decide` and `audit_override`.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Sequence
    from datetime import datetime

    from deploy_gate.models import GateDecision, GateResult


def decide(results: Sequence[GateResult], *, override: Override | None = None) -> GateDecision:
    """Combine gate results into one decision.

    **Every gate runs.** Do not short-circuit on the first block. An engineer who
    learns they are inside a change freeze, fixes that, re-runs, and *then*
    learns a Sev1 is open has been through the loop twice for no reason. Collect
    all the verdicts and report them together.

    `allowed` is the AND of every gate. `reason` summarises *all* blocking gates,
    not just the first.

    An override makes `allowed` True regardless, while **keeping the underlying
    results intact** in `results`. That is what makes the audit trail real: the
    record shows both that the gates said no and that someone decided to proceed
    anyway. Dropping the results and reporting a clean pass would make the
    override invisible, which is the same as not having one.
    """
    raise NotImplementedError


class Override:
    """An override request: who, and why.

    A gate with no override is a gate people route around - they will find the
    `if: false`, or deploy from their laptop, and you will have learned nothing
    about why. An override with no audit trail is a gate that does not exist.

    So: the override is supported, and it is **loud**. Required fields are the
    actor and a non-empty reason. "Because I need to" is a reason; an empty
    string is not, and should be rejected rather than defaulted.
    """

    def __init__(self, *, actor: str, reason: str) -> None:
        raise NotImplementedError


def audit_override(
    override: Override,
    *,
    blocked_by: Sequence[GateResult],
    environment: str,
    now: datetime,
) -> dict[str, object]:
    """Build the audit record for an override, as a structured log payload.

    Must name: the actor, their reason, the environment, **which gates were
    overridden**, and when. Log it at warning level, not info - this should be
    visible in a log search for "things that bypassed a control", and info is
    where things go to be ignored.

    The acceptance criterion is that overriding produces a log line naming the
    actor. Think about where the actor comes from: a label on the PR tells you
    the label exists, not who added it. `github.actor` on the triggering event is
    the honest answer, and if you use a label, say in `DECISIONS.md` how you
    establish who applied it.
    """
    raise NotImplementedError


__all__ = ["Override", "audit_override", "decide"]
