"""Fixtures for the silent-wrongness suite.

The bug this exercise exists to kill: the inventory said 1,200 resources, the real
number was 4,100, nothing errored, and the JSON looked completely plausible.
**Wrong answers that look like right answers** are the defining bug class of
infrastructure tooling, and no exception handler catches them.

Hypothesis strategies live in `strategies.py` next door - tests import those
directly. This file holds the pagination factory, which is the Part 1 tool.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any

import pytest

if TYPE_CHECKING:
    from collections.abc import Callable

NOW = datetime(2026, 9, 21, 12, 0, tzinfo=UTC)


@pytest.fixture
def now() -> datetime:
    return NOW


@pytest.fixture
def paged() -> Callable[..., list[dict[str, Any]]]:
    """Build `page_count` paginator-shaped pages for any AWS list operation.

    Parameterised by page count because the three interesting cases are not
    "works / does not work" but:

        0 pages  the empty-estate case that crashes on `pages[0]`
        1 page   **the case that hides the bug** - a first-page-only
                 implementation passes every single-page test ever written
        3+ pages the only case that catches it

    `key` is the response field the operation nests items under
    (`Reservations` for `DescribeInstances`, `DBInstances` for
    `DescribeDBInstances`, `Functions` for `ListFunctions`), so one factory covers
    every collector in E04.

    The `NextToken` on every page but the last is what makes these usable with
    `botocore.stub.Stubber` - moto does not model EC2 paging, so the stubber is
    the only way to produce a real multi-page response.
    """

    def _paged(
        items: list[Any],
        *,
        key: str,
        page_count: int = 3,
    ) -> list[dict[str, Any]]:
        if page_count <= 0:
            return []
        per = max(1, -(-len(items) // page_count))  # ceil division
        chunks = [items[i : i + per] for i in range(0, len(items), per)] or [[]]
        pages: list[dict[str, Any]] = []
        for n, chunk in enumerate(chunks):
            page: dict[str, Any] = {key: chunk}
            if n < len(chunks) - 1:
                page["NextToken"] = f"tok-{n}"
            pages.append(page)
        return pages

    return _paged
