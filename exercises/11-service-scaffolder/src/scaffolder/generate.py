"""Writing files to disk. The only module here that touches the filesystem.

YOUR JOB: implement `write_files`, `write_stamp`, and `file_tree`.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pathlib import Path

    from scaffolder.models import RenderedFile, ServiceSpec, TemplateVersion


def write_files(
    target: Path,
    rendered: list[RenderedFile],
    *,
    overwrite_generated: bool = False,
) -> list[Path]:
    """Write rendered files under `target`. Returns what was written.

    The idempotent-regeneration rule, enforced here:

        * `overwrite_generated=False` (first generation): nothing may exist.
        * `overwrite_generated=True` (regeneration): a file is overwritten
          **only if the copy on disk carries `GENERATED_MARKER`**. Not if the
          template says it is generated - if the marker is gone, somebody took
          ownership of that file, deliberately or by accident, and either way the
          tool is not entitled to clobber it. Skip it and report it.
        * Files with `generated=False` are never overwritten, ever.

    Create parent directories. Set the executable bit where asked - a generated
    `scripts/entrypoint.sh` that is not executable fails in a way that looks like
    a Docker problem.

    Write atomically per file (temp file plus `Path.replace`) so an interrupted
    regeneration leaves whole files rather than truncated ones.
    """
    raise NotImplementedError


def write_stamp(target: Path, spec: ServiceSpec, version: TemplateVersion) -> Path:
    """Write `.scaffolder.yaml`.

    Records the template name and version, and the spec that produced the
    service. Regeneration needs the spec: `--check` has to render the template
    with the *same inputs* to produce a meaningful comparison, and asking the
    user to retype `--team billing` a year later means they will get it wrong.

    This file is itself generated and carries the marker, so it updates on
    regeneration. It is also the file whose absence means "not a scaffolded
    service", so it must be written **last** - a crash partway through generation
    then leaves a directory that `--check` correctly refuses to interpret rather
    than one it misreads as fully drifted.
    """
    raise NotImplementedError


def file_tree(rendered: list[RenderedFile]) -> str:
    """Render a `tree`-style listing of what would be produced, for `--dry-run`.

    This is the output someone stares at before running the real thing, so it
    should mark which files are generated-and-owned versus seeded-and-yours.
    Those are different promises and the distinction is invisible otherwise.
    """
    raise NotImplementedError


__all__ = ["file_tree", "write_files", "write_stamp"]
