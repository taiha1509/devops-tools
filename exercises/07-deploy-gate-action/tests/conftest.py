from __future__ import annotations

from datetime import UTC, datetime, time

import httpx
import pytest

from deploy_gate.models import FreezeConfig, OneOffWindow, RecurringWindow, Weekday
from helpers import HANOI, UTC_TZ


@pytest.fixture
def friday_afternoon_freeze() -> FreezeConfig:
    """ "Every Friday 14:00-23:59 UTC" - the window from the incident review."""
    return FreezeConfig(
        recurring=(
            RecurringWindow(
                days=(Weekday.FRIDAY,),
                start=time(14, 0),
                end=time(23, 59),
                timezone=UTC_TZ,
                label="Friday afternoon freeze",
            ),
        )
    )


@pytest.fixture
def hanoi_freeze() -> FreezeConfig:
    """The same window, declared in UTC+7. Same wall-clock rule, different instants."""
    return FreezeConfig(
        recurring=(
            RecurringWindow(
                days=(Weekday.FRIDAY,),
                start=time(14, 0),
                end=time(23, 59),
                timezone=HANOI,
                label="Friday afternoon freeze (Hanoi)",
            ),
        )
    )


@pytest.fixture
def year_end_freeze() -> FreezeConfig:
    return FreezeConfig(
        one_off=(
            OneOffWindow(
                start=datetime(2026, 12, 20, 0, 0, tzinfo=UTC),
                end=datetime(2027, 1, 2, 23, 59, 59, tzinfo=UTC),
                label="End-of-year change freeze",
            ),
        )
    )


@pytest.fixture
def client() -> httpx.Client:
    """A real client, stubbed at the transport layer by respx in the tests.

    Injected rather than constructed inside the gate so the gate's own timeout and
    error handling are what gets exercised. Stubbing `fetch_burn_rate` itself
    would test nothing but the test.
    """
    return httpx.Client(timeout=5.0)
