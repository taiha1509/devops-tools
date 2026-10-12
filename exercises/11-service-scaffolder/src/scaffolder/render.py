"""Rendering a template into in-memory files. Pure once the template is loaded.

Everything renders before anything is written. That ordering is the whole reason
"fail before writing a single file, never halfway through" is achievable.

YOUR JOB: implement `render_template` and `template_context`.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from pathlib import Path

    from scaffolder.models import RenderedFile, ServiceSpec, TemplateVersion


def template_context(spec: ServiceSpec, version: TemplateVersion) -> dict[str, Any]:
    """The variables every template gets.

    At minimum: `name`, `module` (the name with hyphens turned into
    underscores - `payments-api` is not an importable Python module),
    `team`, `description`, `template_name`, `template_version`.

    Deliberately **no** `now()` or `uuid()`. A timestamp in generated output
    makes regeneration non-idempotent: `--check` would report drift on every
    service every day, the signal would be useless, and people would stop
    running it. If a template genuinely needs a creation date, it belongs in the
    stamp file, which is written once.
    """
    raise NotImplementedError


def render_template(
    template_dir: Path,
    spec: ServiceSpec,
    version: TemplateVersion,
) -> list[RenderedFile]:
    """Render every file the template declares. Writes nothing.

    Steps:

        1. Read the manifest's `files` list.
        2. Render each **path** as a template too - `src/{{ module }}/main.py`.
        3. Render each file's contents.
        4. Insert `GENERATED_MARKER` into every file where `generated: true`, as
           a comment in that file's own syntax. This is the part that needs
           thought: `#` for YAML and Python, `#` for Dockerfile, `<!-- -->` for
           Markdown, `//` for JSON-with-comments (or nothing, since JSON has no
           comments - decide what you do about `.json` files and write it down).
        5. Sort by path, so two renders produce identical output in identical
           order.

    Raises:
        jinja2.UndefinedError: a template referenced a variable that does not
            exist. Let it escape - `StrictUndefined` exists so this is loud, and
            catching it here would restore the silent-empty-string behaviour it
            was turned on to prevent.
    """
    raise NotImplementedError


__all__ = ["render_template", "template_context"]
