"""Errors that say what to do next.

This module exists because error messages are the UX of a CLI. The brief's
example is the spec:

    not:  KeyError: 'template'
    but:  unknown template 'prevew'. Available: preview, staging, perf.
          Did you mean 'preview'?

YOUR JOB: implement `did_you_mean` and the `message` methods.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Sequence


def did_you_mean(given: str, options: Sequence[str], *, limit: int = 1) -> list[str]:
    """Closest matches to `given` from `options`.

    `difflib.get_close_matches` does this in one line. Two judgement calls:

        * The cutoff. Too low and `prevew` suggests `perf`, which is worse than
          suggesting nothing because the user might believe it.
        * Returning `[]` is fine and common. Do not invent a suggestion to avoid
          an empty list - "unknown template 'xyzzy'. Available: ..." is a
          complete, useful message on its own.
    """
    raise NotImplementedError


class PlatError(Exception):
    """Base for every error this tool shows a user.

    The CLI catches `PlatError`, prints `message()`, and exits with `exit_code`.
    Anything that escapes as a bare traceback is a bug - a traceback tells the
    user they found a defect, which is only true if they did.
    """

    exit_code: int = 1

    def message(self) -> str:
        """The full user-facing text: what happened, and what to do about it."""
        raise NotImplementedError


class UnknownTemplate(PlatError):
    """The brief's worked example. Get this one exactly right."""

    exit_code = 2

    def __init__(self, given: str, available: Sequence[str]) -> None:
        self.given = given
        self.available = tuple(available)
        super().__init__(given)

    def message(self) -> str:
        """Must contain: the bad value, the full list of valid ones, and a
        suggestion when there is a close match."""
        raise NotImplementedError


class EnvironmentNotFound(PlatError):
    exit_code = 2

    def __init__(self, name: str, existing: Sequence[str]) -> None:
        self.name = name
        self.existing = tuple(existing)
        super().__init__(name)

    def message(self) -> str:
        """Name what was not found, and suggest from the user's **own**
        environments - listing all 200 in the account is noise, and `--mine` is
        the scope they were thinking in."""
        raise NotImplementedError


class EnvironmentExists(PlatError):
    exit_code = 2

    def __init__(self, name: str) -> None:
        self.name = name
        super().__init__(name)

    def message(self) -> str:
        """Say what to do: `plat env destroy` it first, or pick another name.

        Do **not** offer to overwrite. Reusing a name silently is how someone's
        colleague's environment disappears.
        """
        raise NotImplementedError


class ConfigInvalid(PlatError):
    exit_code = 2

    def __init__(self, problems: Sequence[object]) -> None:
        self.problems = tuple(problems)
        super().__init__(f"{len(problems)} config problem(s)")

    def message(self) -> str:
        """All problems, one per line, each with its hint. Not just the first."""
        raise NotImplementedError


__all__ = [
    "ConfigInvalid",
    "EnvironmentExists",
    "EnvironmentNotFound",
    "PlatError",
    "UnknownTemplate",
    "did_you_mean",
]
