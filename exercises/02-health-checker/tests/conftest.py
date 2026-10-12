from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Protocol

import pytest

from healthchecker.models import Check

# A fixed reference time. Age policies are tested against a value we control, not
# against the wall clock - that is why `now` is a parameter everywhere in this
# codebase rather than something the code reads for itself.
NOW = datetime(2026, 9, 21, 12, 0, tzinfo=UTC)

@pytest.fixture
def now() -> datetime:
    return NOW


@pytest.fixture
def init_check():
    def _make(name: str, url, **kwargs):
        return Check(**kwargs, name=name, url=url)

    return _make
