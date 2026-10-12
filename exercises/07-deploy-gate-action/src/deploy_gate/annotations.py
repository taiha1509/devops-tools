"""GitHub Actions workflow commands and step outputs.

The reason this is its own module: a gate's output is **UX**. The decision can be
perfect and still useless if the engineer has to scroll to log line 4,000 to find
it. `::error::` puts it in the PR's Checks tab, which is where people actually
look.

YOUR JOB: implement `emit_annotation`, `write_outputs`, and `render_decision`.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, TextIO

if TYPE_CHECKING:
    from pathlib import Path

    from deploy_gate.models import GateDecision


def emit_annotation(
    level: str,
    message: str,
    *,
    stream: TextIO,
    title: str | None = None,
) -> None:
    """Write one workflow command.

    Format: `::error title=Deploy blocked::Frozen until 23:59 UTC`

    Two things that will bite you:

        * **Multi-line messages must be escaped.** A literal newline ends the
          command and the rest becomes ordinary log output. Encode `\\n` as
          `%0A`, `\\r` as `%0D`, and `:` as `%3A` in the *message*.
        * `stream` is injected so tests capture it. Writing to `sys.stdout`
          directly makes this function untestable, and "every gate independently
          testable with no network and no GitHub" is an acceptance criterion.

    Valid levels: `error`, `warning`, `notice`.
    """
    raise NotImplementedError


def write_outputs(outputs: dict[str, str], *, github_output: Path | None) -> None:
    """Write step outputs other jobs can consume: `allowed`, `reason`, `overridden`.

    Appends `key=value` lines to the file named by `$GITHUB_OUTPUT`. Notes:

        * `github_output=None` means we are running locally - a no-op, not an
          error. The brief's "the same entrypoint runs locally" requirement dies
          here if you raise.
        * A value containing a newline needs the heredoc form
          (`key<<EOF`/`EOF`), or it silently truncates. `reason` is exactly the
          kind of value that grows a newline six months from now.
        * **`set-output` is deprecated** and disabled on current runners. If you
          find a tutorial using `::set-output name=...`, it is out of date.
    """
    raise NotImplementedError


def render_decision(decision: GateDecision) -> str:
    """One human-readable summary line for the annotation body.

    Lead with what the reader needs: whether they can deploy, and if not, which
    gate stopped them and until when. If overridden, say who and why - loudly.
    """
    raise NotImplementedError


__all__ = ["emit_annotation", "render_decision", "write_outputs"]
