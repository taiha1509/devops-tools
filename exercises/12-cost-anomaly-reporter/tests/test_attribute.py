"""Contract for attribution and rendering.

Attribution looks like plumbing and contains one genuinely dangerous bug: tag
values that are the same team spelled four ways split one finding into four that
each fall under the dollar floor and disappear.
"""

from __future__ import annotations

from datetime import date

import httpx
import pytest
import respx

from cost_watch.attribute import attribute, coverage, top_owners, untagged_total
from cost_watch.models import UNTAGGED, Report
from cost_watch.render import post_slack, render_slack, render_text

WEBHOOK = "https://hooks.slack.com/services/T000/B000/XXXX"


class TestAttribution:
    def test_tag_variants_resolve_to_one_team(self, series):
        """`billing`, `Billing`, `billing-team` and `team-billing` are the same
        people. Treating them as four owners splits one $8,000 finding into four
        $2,000 ones that each fall under the floor - a real way to make a genuine
        anomaly vanish."""
        costs = [
            *series("AmazonEC2", [2000], owner="billing"),
            *series("AmazonEC2", [2000], owner="Billing"),
            *series("AmazonEC2", [2000], owner="billing-team"),
            *series("AmazonEC2", [2000], owner="team-billing"),
        ]
        mapping = {"billing-team": "billing", "team-billing": "billing"}
        resolved = attribute(costs, team_by_tag=mapping)
        assert {c.owner for c in resolved} == {"billing"}

    def test_an_unmapped_tag_keeps_its_own_value(self, series):
        """The team exists, your mapping is incomplete. Saying so beats hiding it
        under UNTAGGED, which would imply nobody owns the spend."""
        costs = series("AmazonEC2", [100], owner="new-team")
        assert attribute(costs, team_by_tag={})[0].owner == "new-team"

    def test_an_empty_tag_value_becomes_untagged(self, series):
        """Cost Explorer returns the tag key present with an empty value, not
        absent. Mapping that to an empty-string owner makes your biggest line
        item called ""."""
        costs = series("AmazonEC2", [100], owner="")
        assert attribute(costs, team_by_tag={})[0].owner == UNTAGGED

    def test_untagged_spend_is_totalled_separately(self, untagged_spend):
        """ "$14,000 of untagged spend" is a finding: money nobody can be asked
        about."""
        assert untagged_total(untagged_spend) > 0

    def test_top_owners_is_sorted_and_stable(self, series):
        costs = [
            *series("AmazonEC2", [500], owner="billing"),
            *series("AmazonRDS", [900], owner="growth"),
        ]
        assert [owner for owner, _ in top_owners(costs)] == ["growth", "billing"]

    def test_coverage_is_a_fraction(self, series):
        costs = [
            *series("AmazonEC2", [100], owner="billing"),
            *series("AmazonRDS", [100], owner=UNTAGGED),
        ]
        assert coverage(costs) == 0.5

    def test_coverage_of_an_empty_estate_does_not_divide_by_zero(self):
        assert coverage([]) in (0.0, 1.0)


class TestRenderText:
    def test_a_partial_report_says_so_first(self):
        """A reader who misses this draws conclusions from a report with an
        account missing, and will not think to check."""
        report = Report(
            generated_for=date(2026, 9, 21),
            lookback_days=14,
            unavailable_accounts=("222222222222",),
        )
        text = render_text(report)
        assert "partial" in text.lower().split("\n")[0] or "partial" in text.lower()[:200]

    def test_no_anomalies_renders_short(self):
        """The 90% case. A wall of text on a quiet day teaches people to skip it,
        and then they skip the noisy day too."""
        report = Report(generated_for=date(2026, 9, 21), lookback_days=14)
        assert len(render_text(report).splitlines()) < 12

    def test_the_thresholds_used_are_included(self):
        """Someone will disagree with a finding. The conversation is much shorter
        when the report says what it was looking for."""
        raise AssertionError("implement: thread Thresholds onto Report and assert they render")


class TestRenderSlack:
    def test_the_payload_stays_under_the_block_limit(self):
        """Block Kit caps at 50 blocks. A long report silently fails to post."""
        payload = render_slack(Report(generated_for=date(2026, 9, 21), lookback_days=14))
        assert len(payload["blocks"]) <= 50
        raise AssertionError("implement: repeat with 200 anomalies")

    def test_the_notification_text_carries_the_headline(self):
        """The mobile push shows this string. "cost-watch report" tells nobody
        whether to open it; "$2,400/day increase in CloudWatch Logs" does."""
        raise AssertionError("implement: assert payload['text'] names the biggest anomaly")

    def test_an_info_finding_does_not_mention_anyone(self):
        """One unnecessary 09:00 ping and the channel is muted forever - which
        costs you every future CRITICAL too."""
        raise AssertionError("implement: assert no <!here> or <@...> for INFO severity")


class TestPostSlack:
    @respx.mock
    def test_a_successful_post(self):
        route = respx.post(WEBHOOK).mock(return_value=httpx.Response(200, text="ok"))
        with httpx.Client() as client:
            post_slack({"text": "hi"}, webhook_url=WEBHOOK, client=client)
        assert route.called

    @respx.mock
    def test_a_failed_post_raises(self):
        """A report that was generated and not delivered is a report that does not
        exist. Exiting 0 here means the schedule believes it succeeded."""
        respx.post(WEBHOOK).mock(return_value=httpx.Response(500))
        with httpx.Client() as client, pytest.raises(Exception):  # noqa: B017
            post_slack({"text": "hi"}, webhook_url=WEBHOOK, client=client)


def test_slack_and_text_report_the_same_numbers(genuine_anomaly, target_day):
    """Two renderers, one set of facts. They drift the moment someone formats a
    dollar figure in one and not the other, and then the Slack message and the
    terminal disagree about the bill."""
    raise AssertionError("implement: build one Report, render both, assert the totals match")
