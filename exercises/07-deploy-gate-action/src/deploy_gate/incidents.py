"""The open-incident gate. Blocks production deploys while a Sev1 is open.

Same fail-closed rule as the error-budget gate, and the same injected client.

YOUR JOB: implement `fetch_open_incidents` and `evaluate_open_incidents`.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from pydantic import BaseModel, ConfigDict

if TYPE_CHECKING:
    import httpx

    from deploy_gate.models import GateResult


class Incident(BaseModel):
    """One open incident, normalised. Given to you complete."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    incident_id: str
    severity: str
    title: str
    url: str | None = None


class IncidentApiUnavailable(Exception):
    """The incident API could not be read. Fails closed."""


def fetch_open_incidents(
    endpoint: str,
    *,
    client: httpx.Client,
    timeout_seconds: float = 5.0,
) -> list[Incident]:
    """Return currently-open incidents.

    Normalise severity to a comparable form here rather than at the comparison
    site. Every incident tool spells it differently - `SEV1`, `sev-1`, `P1`,
    `critical`, `1` - and scattering that normalisation across the gate is how
    you end up blocking on `SEV1` but not on `Sev1`.

    Raises:
        IncidentApiUnavailable: unreachable, timeout, non-2xx, unparseable.
    """
    raise NotImplementedError


def evaluate_open_incidents(
    incidents: list[Incident] | None,
    *,
    environment: str,
    blocking_severities: tuple[str, ...] = ("sev1",),
    protected_environments: tuple[str, ...] = ("production",),
) -> GateResult:
    """Block deploys to a protected environment while a blocking incident is open.

    Only protected environments are gated. Blocking a staging deploy during a
    production Sev1 is counterproductive - the fix often *is* a deploy, and it
    needs to reach staging first.

    `incidents=None` means the fetch failed: blocked, `failed_closed=True`.

    When blocked, name the incident and link it. The engineer reading this is
    mid-incident and should not have to go looking for which one.
    """
    raise NotImplementedError


__all__ = [
    "Incident",
    "IncidentApiUnavailable",
    "evaluate_open_incidents",
    "fetch_open_incidents",
]
