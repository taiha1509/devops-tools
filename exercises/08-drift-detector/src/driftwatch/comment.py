"""Rendering the PR comment, and posting exactly one of them.

A 900-line plan in a collapsed CI log is not visible, and neither is a 900-line
PR comment. The rendering rule: **counts, then the destructive changes in full,
then everything else behind a `<details>`.**

YOUR JOB: implement `render_comment`, `find_existing_comment`, `upsert_comment`.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    import httpx

    from driftwatch.models import PlanReport

MARKER = "<!-- driftwatch:plan-summary -->"
"""Hidden HTML marker identifying our comment.

This is how `upsert_comment` finds the comment it posted last time. Matching on
the comment body's text would break the moment you reword the heading; matching
on the author would collide with every other bot. An invisible marker is the
standard trick and it is worth knowing.
"""


def render_comment(report: PlanReport, *, drift_only: bool = False) -> str:
    """Render the Markdown body.

    Required shape, in order:

        1. `MARKER` on the first line
        2. a heading and a one-line verdict: clean / changes / **destructive**
        3. counts by category as a table
        4. **destructive changes in full** - address, type, severity, and for a
           replace the attributes that forced it
        5. true drift called out separately, if any: these are console fixes
           about to be reverted, which is a different message from "someone
           changed the code"
        6. everything else inside `<details><summary>`
        7. unknown resource types, if any, with a note that their ranking was a
           default

    Two things to get right because they bite in review:

        * **Blank line after `<summary>`.** GitHub will not render Markdown
          inside `<details>` without it, and your table silently becomes one long
          line of text.
        * **Cap the collapsed list.** A plan with 4,000 no-op entries exceeds
          GitHub's 65,536-character comment limit and the API rejects the whole
          post. Truncate with "...and N more" rather than failing.
    """
    raise NotImplementedError


def find_existing_comment(
    *,
    repo: str,
    pr_number: int,
    client: httpx.Client,
    token: str,
) -> int | None:
    """Find our previous comment's ID by looking for `MARKER`, or None.

    Paginate. A busy PR has more than thirty comments and ours is usually the
    oldest - looking only at page one is how you end up posting a second comment
    on exactly the PRs that are already hardest to read.
    """
    raise NotImplementedError


def upsert_comment(
    body: str,
    *,
    repo: str,
    pr_number: int,
    client: httpx.Client,
    token: str,
) -> None:
    """Update our existing comment if there is one, otherwise create it.

    Ten stale comments is worse than none - it trains people to collapse
    everything your bot writes, at which point the tool has negative value.

    `PATCH /repos/{repo}/issues/comments/{id}` to update,
    `POST /repos/{repo}/issues/{pr}/comments` to create. Note the asymmetry in
    those paths; it catches everyone once.
    """
    raise NotImplementedError


__all__ = ["MARKER", "find_existing_comment", "render_comment", "upsert_comment"]
