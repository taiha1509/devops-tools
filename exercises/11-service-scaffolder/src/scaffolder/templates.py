"""Template discovery and the Jinja2 environment.

YOUR JOB: implement `available_templates`, `load_template_version`, and
`build_environment`.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pathlib import Path

    from jinja2 import Environment

    from scaffolder.models import TemplateVersion

TEMPLATE_MANIFEST = "template.yaml"
"""Per-template metadata: its name, its version, and which files are generated.

    name: python-fastapi
    version: "1.3.0"
    files:
      - src: "github/workflows/ci.yaml.j2"
        path: ".github/workflows/ci.yaml"
        generated: true
      - src: "src/main.py.j2"
        path: "src/{{ module }}/main.py"
        generated: false      # seeded once, then the team's

Two things to notice in that shape:

`src` and `path` are separate. The template file lives at `src`; the generated
file lands at `path`. Keeping a real `.github/` directory inside the template
tree confuses packaging tools and git hooks, so templates store workflows under
`github/` and map them into place.

**`path` is itself a Jinja2 template.** A service's module directory is named
after the service, and hardcoding that into the tool rather than the template is
how you end up with a scaffolder that can only generate Python services.
"""


def available_templates(templates_root: Path) -> tuple[str, ...]:
    """Every directory under `templates_root` containing a `template.yaml`.

    Sorted, so `--help` and error messages list them in a stable order. Used by
    E10's `UnknownTemplate` error to produce its "Available: ..." line, which is
    why this returns names rather than paths.
    """
    raise NotImplementedError


def load_template_version(template_dir: Path) -> TemplateVersion:
    """Read the template's name and version from its manifest.

    **Bump this whenever you change a generated file.** The version is what makes
    `--check` meaningful: a service stamped `1.2.0` against a template now at
    `1.3.0` is the answer to "which services have the old CI config?", and it is
    the only cheap way to get that answer across 23 repositories.

    Raises:
        ValueError: no manifest, or no version in it. A template that cannot say
            what version it is cannot be managed, so this is fatal rather than
            defaulted.
    """
    raise NotImplementedError


def build_environment(template_dir: Path) -> Environment:
    """The Jinja2 environment for one template.

    Settings that matter, each for a specific reason:

        * `undefined=StrictUndefined` - **the important one.** By default Jinja2
          renders an unknown variable as the empty string, so a typo'd
          `{{ tem }}` produces a Dockerfile with a blank `FROM` line and no
          error at all. Generating broken-but-plausible files silently is the
          worst failure this tool has available.
        * `keep_trailing_newline=True` - otherwise every generated file is
          missing its final newline and every first commit has a noisy diff.
        * `trim_blocks` / `lstrip_blocks` - control-flow blocks in YAML
          otherwise leave blank lines that break indentation.
        * Autoescaping **off**. These are YAML, Dockerfiles and Python, not HTML;
          autoescaping would corrupt them. Worth knowing you made that choice
          rather than inheriting it.
    """
    raise NotImplementedError


__all__ = [
    "TEMPLATE_MANIFEST",
    "available_templates",
    "build_environment",
    "load_template_version",
]
