"""The error-budget gate. Reads a burn rate from a metrics endpoint.

**Fail closed.** If the endpoint is unreachable, this gate blocks and says why. A
gate that fails open is decoration: the one moment it cannot reach your metrics
is disproportionately likely to be the moment your metrics stack is already on
fire, which is exactly when you least want a deploy going out.

YOUR JOB: implement `fetch_burn_rate` and `evaluate_error_budget`.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    import httpx

    from deploy_gate.models import GateResult


class MetricsUnavailable(Exception):
    """The endpoint could not be read. Becomes a fail-closed block, not a crash."""


def fetch_burn_rate(
    endpoint: str,
    *,
    client: httpx.Client,
    timeout_seconds: float = 5.0,
) -> float:
    """Read the remaining error budget as a fraction between 0.0 and 1.0.

    `client` is injected so tests stub the transport rather than the function -
    `respx` intercepts at that layer, which means the gate's own logic (including
    its timeout and error handling) is what gets tested. Passing a fake
    `fetch_burn_rate` instead would test nothing.

    **A short timeout is part of the contract.** A metrics endpoint that hangs
    must not hang the deploy; five seconds then fail closed is a decision, an
    indefinite wait is not.

    Raises:
        MetricsUnavailable: connection error, timeout, non-2xx, unparseable body,
            or a value outside 0.0-1.0. That last one matters: a metrics bug that
            returns `-1` or `1e9` must not be treated as "budget is fine".
    """
    raise NotImplementedError


def evaluate_error_budget(remaining: float | None, *, threshold: float) -> GateResult:
    """Block when the remaining budget is below `threshold`.

    `remaining=None` means the fetch failed. Return a blocked result with
    `failed_closed=True` and a reason that distinguishes it from a real budget
    exhaustion - the two look identical in a Checks tab otherwise, and they need
    completely different responses: one means "stop shipping and fix
    reliability", the other means "fix your metrics endpoint".

    The boundary: `remaining == threshold` **allows**. Document it either way.
    """
    raise NotImplementedError


__all__ = ["MetricsUnavailable", "evaluate_error_budget", "fetch_burn_rate"]
