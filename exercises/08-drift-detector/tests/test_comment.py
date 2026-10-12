"""Contract for rendering and posting.

The acceptance criterion that people skip: **re-running updates the existing
comment instead of adding one.** Ten stale comments is worse than none, because
it trains people to collapse everything your bot writes - at which point the
tool has negative value.
"""

from __future__ import annotations

import httpx
import respx

from driftwatch.comment import MARKER, find_existing_comment, render_comment, upsert_comment
from driftwatch.models import PlanReport
from driftwatch.plan import parse_plan
from driftwatch.severity import apply_severities

REPO = "your-org/infra"
PR = 42
COMMENTS_URL = f"https://api.github.com/repos/{REPO}/issues/{PR}/comments"


def _report(plan, name: str) -> PlanReport:
    return apply_severities(parse_plan(plan(name)))


class TestRendering:
    def test_the_marker_is_on_the_first_line(self, plan):
        """How `upsert_comment` finds its own comment next time. Matching on body
        text breaks when you reword the heading; matching on author collides with
        every other bot."""
        body = render_comment(_report(plan, "replace"))
        assert body.splitlines()[0] == MARKER

    def test_destructive_changes_appear_in_full_not_collapsed(self, plan):
        """A 900-line plan in a collapsed log is not visible, and neither is a
        900-line comment. The destructive ones are the whole point."""
        body = render_comment(_report(plan, "replace"))
        head = body.split("<details>")[0]
        assert "aws_db_instance.primary" in head

    def test_non_destructive_changes_are_collapsed(self, plan):
        body = render_comment(_report(plan, "creates-only"))
        assert "<details>" in body

    def test_there_is_a_blank_line_after_summary(self, plan):
        """GitHub will not render Markdown inside `<details>` without it, and your
        table silently becomes one long line of text. Costs an afternoon to find."""
        body = render_comment(_report(plan, "creates-only"))
        assert "</summary>\n\n" in body

    def test_counts_by_category_are_present(self, plan):
        body = render_comment(_report(plan, "creates-only"))
        assert "3" in body

    def test_a_clean_plan_says_so_plainly(self, plan):
        body = render_comment(_report(plan, "no-changes"))
        assert "no changes" in body.lower()

    def test_true_drift_is_called_out_separately_from_the_diff(self, plan):
        """ "Someone changed this in the console and this apply will revert it" is a
        different message from "someone changed the code", and the first one is
        what caused the second outage in the problem statement."""
        raise AssertionError("implement: render true-drift.json, assert drift has its own section")

    def test_unknown_types_are_noted(self, plan):
        body = render_comment(_report(plan, "unknown-type"))
        assert "snowflake_warehouse" in body

    def test_a_huge_plan_is_truncated_below_githubs_limit(self):
        """GitHub rejects comment bodies over 65,536 characters, and it rejects the
        **whole post** - so one 4,000-resource plan means no comment at all rather
        than a long one. Truncate with "...and N more"."""
        raise AssertionError("implement: synthesise 4000 no-op changes, assert len(body) < 65536")


class TestUpsert:
    @respx.mock
    def test_finds_our_previous_comment_by_marker(self, client):
        respx.get(COMMENTS_URL).mock(
            return_value=httpx.Response(
                200,
                json=[
                    {"id": 1, "body": "LGTM"},
                    {"id": 2, "body": f"{MARKER}\n## Plan summary"},
                ],
            )
        )
        found = find_existing_comment(repo=REPO, pr_number=PR, client=client, token="t")
        assert found == 2

    @respx.mock
    def test_returns_none_when_we_have_not_commented(self, client):
        respx.get(COMMENTS_URL).mock(
            return_value=httpx.Response(200, json=[{"id": 1, "body": "hi"}])
        )
        assert find_existing_comment(repo=REPO, pr_number=PR, client=client, token="t") is None

    @respx.mock
    def test_comment_search_paginates(self, client):
        """A busy PR has more than thirty comments and ours is usually the oldest -
        reading only page one is how you post a second comment on exactly the PRs
        that are already hardest to read."""
        raise AssertionError("implement: two pages with a Link header, marker on page 2")

    @respx.mock
    def test_an_existing_comment_is_patched_not_duplicated(self, client):
        respx.get(COMMENTS_URL).mock(
            return_value=httpx.Response(200, json=[{"id": 7, "body": MARKER}])
        )
        patch = respx.patch(f"https://api.github.com/repos/{REPO}/issues/comments/7").mock(
            return_value=httpx.Response(200, json={"id": 7})
        )
        post = respx.post(COMMENTS_URL).mock(return_value=httpx.Response(201, json={"id": 8}))

        upsert_comment("new body", repo=REPO, pr_number=PR, client=client, token="t")

        assert patch.called
        assert not post.called

    @respx.mock
    def test_a_first_run_creates_the_comment(self, client):
        respx.get(COMMENTS_URL).mock(return_value=httpx.Response(200, json=[]))
        post = respx.post(COMMENTS_URL).mock(return_value=httpx.Response(201, json={"id": 8}))

        upsert_comment("body", repo=REPO, pr_number=PR, client=client, token="t")

        assert post.called
