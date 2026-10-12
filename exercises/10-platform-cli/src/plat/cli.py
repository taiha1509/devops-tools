"""The CLI surface. This is the exercise - the interface, not the provisioning.

## Subcommand structure

`plat <noun> <verb>`, held everywhere. A flat list of thirty commands is
unlearnable; `plat env create` / `plat env list` means a user who knows one noun
can guess the rest. Pick the convention and do not make exceptions for the one
command that feels awkward - the exception is what breaks the guessing.

## `--help` is the documentation

Every command: a one-line summary, an example, and described options. If someone
has to read your source to use your tool, the tool is unfinished. The acceptance
criterion is that a colleague can install it and create an environment using only
`--help`.

YOUR JOB: implement every command below.
"""

from __future__ import annotations

from pathlib import Path
from typing import Annotated

import typer

from plat import __version__

app = typer.Typer(
    add_completion=False,
    no_args_is_help=True,
    help="Self-service platform environments.",
)

env_app = typer.Typer(no_args_is_help=True, help="Create and manage preview environments.")
config_app = typer.Typer(no_args_is_help=True, help="Inspect effective configuration.")
app.add_typer(env_app, name="env")
app.add_typer(config_app, name="config")


def _version_callback(value: bool) -> None:
    """Eager `--version`, so it works before any other validation runs.

    `plat --version` must answer even when the config is broken - it is the first
    thing anyone asks for in a bug report, and needing a valid config to get it
    is a bad day for both of you.
    """
    if value:
        typer.echo(__version__)
        raise typer.Exit


@app.callback()
def main(
    version: Annotated[
        bool,
        typer.Option("--version", callback=_version_callback, is_eager=True, help="Show version."),
    ] = False,
) -> None:
    """Root callback. Holds the global flags."""


@env_app.command("create")
def env_create(
    name: Annotated[str, typer.Option(help="Environment name. Must be unique.")],
    template: Annotated[str | None, typer.Option(help="Template to use.")] = None,
    ttl: Annotated[str | None, typer.Option(help="Lifetime, e.g. 48h. 'none' to disable.")] = None,
) -> None:
    """Create a preview environment.

    Example:

        plat env create --name feat-auth --template preview --ttl 48h

    Note every option defaults to `None`, not to its real default. That is what
    lets `config.resolve` tell "flag absent" from "flag set to a falsy value" -
    `--ttl ""` has to win over the project config rather than falling through it.
    """
    raise NotImplementedError


@env_app.command("list")
def env_list(
    mine: Annotated[bool, typer.Option("--mine", help="Only your environments.")] = False,
    show_expired: Annotated[bool, typer.Option("--expired", help="Only expired ones.")] = False,
) -> None:
    """List environments.

    Example:

        plat env list --mine

    Show the time remaining, not just the expiry timestamp. "expires in 3h" is
    actionable; "expires 2026-09-21T14:00:00Z" needs mental arithmetic from
    someone who is already busy.
    """
    raise NotImplementedError


@env_app.command("logs")
def env_logs(
    name: Annotated[str, typer.Argument(help="Environment name.")],
    follow: Annotated[bool, typer.Option("--follow", "-f", help="Stream new lines.")] = False,
) -> None:
    """Show an environment's logs.

    Example:

        plat env logs feat-auth --follow

    `--follow` must stream, not buffer. Handle `KeyboardInterrupt` cleanly and
    exit 0 - Ctrl-C on a follow is the user succeeding, and a traceback there
    looks like a crash they caused.
    """
    raise NotImplementedError


@env_app.command("destroy")
def env_destroy(
    name: Annotated[str, typer.Argument(help="Environment name.")],
    yes: Annotated[bool, typer.Option("--yes", help="Skip confirmation. For CI.")] = False,
) -> None:
    """Destroy an environment.

    Example:

        plat env destroy feat-auth

    **Never a destructive default.** This confirms interactively; `--yes` skips
    it for automation; there is no flag that makes destruction the default.

    Confirm by requiring the **name** typed back, not a y/n. A y/n is muscle
    memory within a week. Also: `typer.confirm` on a non-TTY must not hang
    forever waiting on stdin - decide what a piped invocation without `--yes`
    does, and make it refuse rather than block.
    """
    raise NotImplementedError


@env_app.command("reap")
def env_reap(
    dry_run: Annotated[bool, typer.Option("--dry-run/--apply", help="Plan only.")] = True,
) -> None:
    """Destroy every expired environment.

    E01's invariant, restated: **the plan does not depend on `--dry-run`.** Same
    environments selected, same output, only the destroy call is conditional.
    Dry-run is the default because this command deletes things.
    """
    raise NotImplementedError


@config_app.command("show")
def config_show(
    origin: Annotated[
        bool, typer.Option("--origin", help="Show where each value came from.")
    ] = False,
    config_file: Annotated[
        Path | None, typer.Option(exists=True, help="Override project config.")
    ] = None,
) -> None:
    """Print the effective configuration.

    Example:

        plat config show --origin

    Output shape for `--origin`:

        template  preview       default
        ttl       48h           project_config (/Users/me/work/api/.plat.yaml)
        region    eu-west-1     env_var (PLAT_REGION)

    This command will save you more support questions than any other feature.
    "Why is it deploying to staging" is almost always a precedence question, and
    this answers it without anyone reading your source.
    """
    raise NotImplementedError


__all__ = ["app", "config_app", "env_app"]
