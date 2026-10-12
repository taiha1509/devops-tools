from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

import pytest
from typer.testing import CliRunner

from scaffolder.models import ServiceSpec, TemplateVersion

if TYPE_CHECKING:
    from collections.abc import Callable

# The real templates, not fixtures. Rendering the shipped templates and then
# running the generated project's own lint and tests is an acceptance criterion -
# a scaffolder that emits code failing its own standards is worse than no
# scaffolder, and only the real templates can catch that.
TEMPLATES_ROOT = Path(__file__).parent.parent / "templates"

KNOWN_TEAMS = ("billing", "platform", "growth")


@pytest.fixture
def templates_root() -> Path:
    return TEMPLATES_ROOT


@pytest.fixture
def fastapi_template() -> Path:
    return TEMPLATES_ROOT / "python-fastapi"


@pytest.fixture
def worker_template() -> Path:
    return TEMPLATES_ROOT / "python-worker"


@pytest.fixture
def runner() -> CliRunner:
    return CliRunner()


@pytest.fixture
def version() -> TemplateVersion:
    """A fixed template version.

    Passed in rather than read from the manifest for the same reason `now` is a
    parameter in E01: the stale-stamp tests need to render at one version and
    check against another, which is impossible if the version is only ever read
    off disk.
    """
    return TemplateVersion(name="python-fastapi", version="1.0.0")


@pytest.fixture
def spec() -> ServiceSpec:
    return ServiceSpec(
        name="payments-api",
        template="python-fastapi",
        team="billing",
        description="Takes money.",
    )


@pytest.fixture
def make_spec() -> Callable[..., ServiceSpec]:
    def _make(**overrides: str) -> ServiceSpec:
        base = {
            "name": "payments-api",
            "template": "python-fastapi",
            "team": "billing",
            "description": "Takes money.",
        }
        return ServiceSpec(**{**base, **overrides})  # type: ignore[arg-type]

    return _make
