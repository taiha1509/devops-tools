"""Discovering services and reading the dependency graph from the repo.

**Read the graph from the repo, never hardcode it.** This is the part people get
wrong and it is the part that makes the tool trustworthy: a hardcoded graph is
wrong the first time someone adds a service and nobody updates the generator.

YOUR JOB: implement `discover_services` and `load_manifest`.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pathlib import Path

    from ci_matrix.models import Service

MANIFEST_NAME = "ci-service.yaml"
"""One manifest per service, committed next to the service.

A single central `services.yaml` is the tempting alternative and it is worse: it
becomes a merge-conflict magnet, and it decouples the declaration from the thing
declared, so it rots. A manifest living in the service's own directory is updated
by the person who changes the service.
"""


class UnparseableManifest(Exception):
    """A manifest exists but cannot be read.

    **Not fatal, and not ignorable.** The caller degrades to build-everything and
    records `Reason.UNPARSEABLE_MANIFEST`. See the safety question in the brief:
    an unparseable manifest means "build everything", never "build nothing".
    """


def load_manifest(path: Path) -> Service:
    """Parse one `ci-service.yaml`.

    Expected shape::

        name: payments-api
        depends_on: [shared-auth, shared-logging]
        extra:
          python: ["3.12", "3.13"]

    `name` defaults to the directory name when absent - the common case should
    need no configuration at all. `depends_on` names other services, not paths:
    paths change, names are the stable identifier, and a rename then shows up as
    a loud "unknown dependency" rather than a silent orphan.

    Raises:
        UnparseableManifest: invalid YAML, or validation failure.
    """
    raise NotImplementedError


def discover_services(repo_root: Path) -> tuple[dict[str, Service], tuple[str, ...]]:
    """Walk the repo for manifests.

    Returns:
        The services by name, and the paths of any manifest that failed to parse.
        Two values rather than raising, because one broken manifest must not stop
        the other twenty-two services from being planned - it just forces the
        safe degradation.

    Skip `.git`, `node_modules`, `.venv` and friends. On a 23-service monorepo
    this runs on every push, so an unbounded `rglob` through
    `node_modules` is a real cost, not a theoretical one.
    """
    raise NotImplementedError


__all__ = ["MANIFEST_NAME", "UnparseableManifest", "discover_services", "load_manifest"]
