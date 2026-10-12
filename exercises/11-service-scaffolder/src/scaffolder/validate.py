"""Pre-flight validation. Everything checked before anything is written.

"Fail before writing a single file, never halfway through." A scaffolder that
dies on file nine leaves a directory that is neither a service nor empty, and
the user has to work out which eight files to delete.

YOUR JOB: implement `validate_spec` and `validate_target`.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Sequence
    from pathlib import Path

    from scaffolder.models import ServiceSpec


class ValidationFailed(Exception):
    """Pre-flight checks failed. Exit 2, report **every** problem.

    Same rule as E10's config validation: a user with three things wrong should
    learn all three in one run.
    """

    def __init__(self, problems: Sequence[str]) -> None:
        self.problems = tuple(problems)
        super().__init__(f"{len(problems)} validation problem(s)")


def validate_spec(
    spec: ServiceSpec,
    *,
    available_templates: Sequence[str],
    known_teams: Sequence[str],
) -> list[str]:
    """Check the spec. Returns every problem, in order.

    What to check:

        * The template exists. Suggest the closest match - this is E10's
          `did_you_mean` and the two tools should produce the same message, so
          import it rather than reimplementing it.
        * The team exists. A service with a made-up team gets a `CODEOWNERS`
          naming a group that cannot be mentioned, and nobody finds out until the
          first incident.
        * The name matches the org convention. `ServiceSpec` already enforces the
          pattern, so this is where you turn a pydantic error into a sentence a
          human can act on: "service names are lowercase with hyphens, e.g.
          payments-api" beats a regex.
        * Reserved names - `test`, `src`, `lib`, `docs`, anything that collides
          with a path component the generated layout uses.
    """
    raise NotImplementedError


def validate_target(target: Path, *, allow_existing: bool = False) -> list[str]:
    """Check the destination directory.

    `allow_existing=False` (generation): the directory must not exist, or must be
    empty. A directory containing a `.git` and nothing else counts as empty for
    this purpose - that is the normal case for a freshly-created repo, and
    refusing it would make the tool useless exactly when it is needed.

    `allow_existing=True` (`--check` and regeneration): the directory must exist
    and contain a `STAMP_FILE`. Running `--check` against a directory that was
    never generated should say so plainly rather than reporting every file as
    drifted - "this is not a scaffolded service" is the useful message.
    """
    raise NotImplementedError


__all__ = ["ValidationFailed", "validate_spec", "validate_target"]
