"""The dependency graph. Pure: services and changed files in, inclusions out.

This module is the exercise. Everything else is plumbing around it.

YOUR JOB: implement `build_graph`, `find_cycles`, `reverse_closure`, and
`services_for_paths`.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Iterable, Mapping

    from ci_matrix.models import Service


def build_graph(services: Mapping[str, Service]) -> dict[str, frozenset[str]]:
    """Forward edges: service -> what it depends on.

    A `depends_on` entry naming a service that does not exist is a **loud error**,
    not a silently dropped edge. A dropped edge means the dependent service stops
    being rebuilt when its dependency changes, which is the exact failure this
    tool is supposed to prevent, arriving quietly.

    Raises:
        ValueError: an unknown dependency, naming both services.
    """
    raise NotImplementedError


def find_cycles(graph: Mapping[str, frozenset[str]]) -> tuple[tuple[str, ...], ...]:
    """Every cycle in the graph, each as the chain of names involved.

    An acceptance criterion: cycles are **detected and reported, not looped on
    forever**. A naive recursive closure on `A -> B -> A` recurses until Python
    gives up, and the error you get is a `RecursionError` from inside a CI job,
    which tells the reader nothing.

    Return the chains rather than just a bool so the error message can name them.
    Depth-first search with a colour marking (white/grey/black) is the standard
    approach; a grey node you reach again is the cycle.
    """
    raise NotImplementedError


def reverse_closure(
    graph: Mapping[str, frozenset[str]],
    roots: Iterable[str],
) -> dict[str, tuple[str, ...]]:
    """Everything that must rebuild because something in `roots` changed.

    This is the **transitive, reverse** closure, and both words matter:

        * *reverse* - the graph says "A depends on L", and what you need is
          "L changed, so rebuild A". Walk the edges backwards.
        * *transitive* - L is depended on by A, A by B. Changing L builds all
          three. Stopping at direct dependents is the bug that makes the tool
          appear to work until the first two-level change ships untested.

    Returns:
        For each service that must build, the **chain** that pulled it in, e.g.
        `{"B": ("L", "A", "B")}`. `--explain` needs the chain, not just the name:
        "B was included because A changed" is not an explanation when A did not
        change either.

    Must terminate on a cyclic graph. Call `find_cycles` first and refuse, or
    track visited nodes here - decide which, and say why in `DECISIONS.md`.
    """
    raise NotImplementedError


def services_for_paths(
    services: Mapping[str, Service],
    changed_files: Iterable[str],
) -> dict[str, tuple[str, ...]]:
    """Map changed file paths onto the services that own them.

    Longest-prefix match: `services/api/src/main.py` belongs to the service at
    `services/api`, not to one at `services`. Sort candidate paths by length
    descending and take the first match, or nested services silently attribute
    changes to their parent.

    A changed file owned by no service is **not** an error here - it might be
    documentation, or a global trigger, both of which are handled elsewhere.
    Return only what matched and let the caller decide.

    Returns:
        Service name -> the changed files that caused its inclusion.
    """
    raise NotImplementedError


__all__ = ["build_graph", "find_cycles", "reverse_closure", "services_for_paths"]
