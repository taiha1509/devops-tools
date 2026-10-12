"""Assembling the plan and emitting a valid GitHub Actions matrix.

YOUR JOB: implement `plan_builds`, `to_matrix`, and `explain`.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from collections.abc import Iterable, Mapping

    from ci_matrix.models import Plan, Service

MATRIX_JOB_LIMIT = 256
"""GitHub's hard cap on matrix jobs per workflow run.

Exceeding it does not truncate - the **whole run fails to start**, which on a
monorepo means a broken CI for everyone until someone notices. Hence the
`degrade deliberately` requirement.
"""

DEFAULT_GLOBAL_TRIGGERS: tuple[str, ...] = (
    ".github/workflows/**",
    "ci-service.yaml",
    "Dockerfile.base",
    "uv.lock",
    "poetry.lock",
    "package-lock.json",
)
"""Paths that mean "build everything".

Note the direction of the risk. Get this list **too small** and you ship
untested code: a change to the base image rebuilds nothing, and every service
inherits the break silently. Get it too large and you waste runner minutes. The
asymmetry is not close, so when in doubt, add the path.

`.github/workflows/**` includes this tool's own workflow, which is deliberate -
a change to how CI runs invalidates every previous result.
"""


def plan_builds(
    services: Mapping[str, Service],
    changed: Iterable[str],
    *,
    global_triggers: tuple[str, ...] = DEFAULT_GLOBAL_TRIGGERS,
    unparseable: tuple[str, ...] = (),
    job_limit: int = MATRIX_JOB_LIMIT,
) -> Plan:
    """Compute the minimum set of services a change requires.

    The order of operations, which matters:

        1. **Unparseable manifests force build-all.** Before anything else. If
           the graph might be incomplete, no conclusion drawn from it is safe.
        2. **Global triggers force build-all.** `fnmatch` each changed path
           against the patterns.
        3. Map changed paths to directly-changed services.
        4. Take the reverse transitive closure for dependency-changed services.
        5. **Check the job limit.** Count services times their `extra`
           dimensions, not just services - a 20-service matrix with a
           4-way Python version axis is 80 jobs.
        6. If over the limit, degrade deliberately: chunk, or fall back to
           build-all. Never emit an invalid matrix.

    Every degradation sets `Plan.degraded` and a `degraded_reason`. A tool that
    silently degrades to build-all has quietly become the 40-minute CI run it was
    written to replace, and nobody will know why.
    """
    raise NotImplementedError


def to_matrix(plan: Plan, *, services: Mapping[str, Service]) -> dict[str, Any]:
    """Render the plan as a GitHub Actions matrix object.

    Shape, consumed by `matrix: ${{ fromJson(needs.plan.outputs.matrix) }}`::

        {"include": [{"service": "api", "path": "services/api", "python": "3.12"}]}

    `include` form rather than bare lists, because services need different extra
    dimensions and a cartesian product over the union would generate combinations
    that do not exist.

    **An empty plan must be valid JSON.** `{"include": []}` - GitHub then skips
    the dependent job cleanly. Emitting `{}`, or `null`, or an empty string makes
    the downstream job *fail* rather than skip, which turns a docs-only PR into a
    red build. This is an acceptance criterion and it is the one most likely to
    bite in the first week.

    Sort `include` deterministically. An unstable order makes the Actions UI
    unreadable and breaks required-check names between runs.
    """
    raise NotImplementedError


def explain(plan: Plan) -> str:
    """Human-readable account of why each service is in or out.

    The acceptance criterion is that it is **readable by someone who has never
    seen the tool**, which rules out dumping the `Plan` model. Aim for:

        payments-api     directly changed    services/payments-api/src/main.py
        checkout-api     shared-auth changed shared-auth -> checkout-api
        docs-site        not included        no changed files under services/docs-site

    Include the **excluded** services too, with the reason. The question people
    actually ask is "why did my service not build", and a tool that only explains
    inclusions cannot answer it.
    """
    raise NotImplementedError


__all__ = [
    "DEFAULT_GLOBAL_TRIGGERS",
    "MATRIX_JOB_LIMIT",
    "explain",
    "plan_builds",
    "to_matrix",
]
