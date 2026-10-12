"""Fixtures, centred on a builder for throwaway monorepos.

The acceptance criteria all describe a *repo shape*: leaf change, shared-library
change, global trigger, docs-only, deleted service. Building those by hand in
each test is tedious enough that you would skip half of them, so the builder is
the first thing worth writing.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from ci_matrix.models import Service

if TYPE_CHECKING:
    from collections.abc import Callable
    from pathlib import Path


@pytest.fixture
def fixture_repo() -> Callable[..., Path]:
    """Build a monorepo in `tmp_path` from a compact description.

    Implement it to take something like::

        repo({
            "shared-auth": [],
            "checkout-api": ["shared-auth"],
            "web": ["checkout-api"],
            "docs-site": [],
        })

    and write a `ci-service.yaml` per service under `services/<name>/`, plus one
    source file each so there is something to change.

    Returning the path rather than a model keeps the tests honest: they exercise
    `discover_services` walking a real tree, which is where the longest-prefix
    and skip-`node_modules` behaviour lives.
    """
    raise NotImplementedError


@pytest.fixture
def chain() -> dict[str, Service]:
    """`L <- A <- B`: the transitive case, as models, for the pure graph tests.

    Read the arrows as "depends on": A depends on L, B depends on A. A change to
    L must build all three, and the test that only checks direct dependents
    passes while the tool is broken.
    """
    return {
        "shared-logging": Service(name="shared-logging", path="libs/shared-logging"),
        "shared-auth": Service(
            name="shared-auth",
            path="libs/shared-auth",
            depends_on=("shared-logging",),
        ),
        "checkout-api": Service(
            name="checkout-api",
            path="services/checkout-api",
            depends_on=("shared-auth",),
        ),
        "docs-site": Service(name="docs-site", path="services/docs-site"),
    }


@pytest.fixture
def cyclic() -> dict[str, Service]:
    """`A -> B -> A`. A naive recursive closure recurses until Python gives up."""
    return {
        "a": Service(name="a", path="services/a", depends_on=("b",)),
        "b": Service(name="b", path="services/b", depends_on=("a",)),
    }


@pytest.fixture
def nested() -> dict[str, Service]:
    """A service inside another service's path, for the longest-prefix test."""
    return {
        "platform": Service(name="platform", path="services"),
        "api": Service(name="api", path="services/api"),
    }
