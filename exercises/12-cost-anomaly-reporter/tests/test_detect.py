"""Contract for detection - the engineering problem in this exercise.

Each `TestFalsePositives` test is a class of noise that a naive week-over-week
implementation reports. Getting them all quiet **without** silencing
`genuine_anomaly` is the work. If you find yourself raising a threshold until the
noise stops, you are trading real findings for quiet - which is why the
acceptance criterion is a measured rate rather than "it seems fine now".
"""

from __future__ import annotations

from datetime import date, timedelta

from cost_watch.detect import Thresholds, baseline_for, classify, detect, detect_trends
from cost_watch.models import Anomaly, AnomalyKind, DailyCost

THRESHOLDS = Thresholds()


def _for_service(anomalies, service: str) -> list[Anomaly]:
    return [a for a in anomalies if a.service == service]


class TestTruePositives:
    def test_a_genuine_spike_is_reported(self, genuine_anomaly, target_day):
        """$400/day to $2,800. If this is quiet, nothing else matters."""
        found = detect(genuine_anomaly, target_day=target_day)
        assert _for_service(found, "AmazonCloudWatch")

    def test_the_spike_reports_dollars_not_just_a_percentage(self, genuine_anomaly, target_day):
        """A reader needs to know it is $2,400/day, which is $72,000/month."""
        anomaly = _for_service(detect(genuine_anomaly, target_day=target_day), "AmazonCloudWatch")[
            0
        ]
        assert anomaly.delta_usd > 2000

    def test_a_sustained_trend_is_caught(self, sustained_trend, target_day):
        """The case the problem statement describes: no single day trips a spike
        threshold, and two months later the bill is 30% up."""
        found = detect_trends(sustained_trend, thresholds=THRESHOLDS)
        assert found

    def test_a_trend_is_one_finding_not_one_per_day(self, sustained_trend):
        """Three findings for one cause is how a report becomes noise."""
        found = detect_trends(sustained_trend, thresholds=THRESHOLDS)
        assert len(_for_service(found, "AmazonS3")) == 1

    def test_a_drop_is_reported_too(self, series, target_day):
        """A service costing nothing suddenly is as likely to mean "it broke" as
        "we optimised it", and the first one is an outage nobody has noticed."""
        collapsed = series("AmazonRDS", [900] * 20 + [10])
        found = detect(collapsed, target_day=target_day)
        assert any(a.kind is AnomalyKind.DROP for a in found)


class TestFalsePositives:
    def test_the_weekend_dip_is_not_reported(self, weekend_dip, target_day):
        """The first false positive you will hit, on the very first Monday.

        `target_day` is a Monday and the day before is a Sunday at 40% of normal.
        Week-over-week against yesterday reports +150%. A same-weekday baseline
        reports nothing, which is correct.
        """
        assert detect(weekend_dip, target_day=target_day) == []

    def test_the_month_end_spike_is_not_reported_as_a_surprise(self, month_end_spike):
        """The hard one - a same-weekday baseline does not fix it.

        Whatever you chose (suppress the last N days, compare to the previous
        month-end, or label it rather than suppress it), make this test say so.
        If you chose to label it, assert the label instead of the silence.
        """
        found = detect(month_end_spike, target_day=date(2026, 9, 30))
        assert found == []

    def test_a_tiny_service_doubling_is_not_reported(self, tiny_but_doubled, target_day):
        """$0.40 to $0.85. A 112% increase and 45 cents.

        Small services have the most volatile percentages, which is why a
        percentage-only detector reports mostly rounding errors.
        """
        assert detect(tiny_but_doubled, target_day=target_day) == []

    def test_steady_spend_is_silent(self, series, target_day):
        """The 90% case. A detector that is noisy here is unusable."""
        steady = series("AmazonEC2", [1000] * 21)
        assert detect(steady, target_day=target_day) == []

    def test_a_partial_final_day_is_not_reported_as_a_drop(self, series):
        """Today's Cost Explorer data is incomplete and revised for 24 hours.

        Analysing today reports a drop every single morning - the most
        embarrassing false positive available here, which is why the CLI defaults
        to yesterday.
        """
        today = date(2026, 9, 22)
        partial = series("AmazonEC2", [1000] * 20 + [230], end=today)
        assert detect(partial, target_day=today - timedelta(days=1)) == []


class TestNewServices:
    def test_a_new_service_is_its_own_kind(self, brand_new_service, target_day):
        """Not an infinite percentage increase."""
        found = _for_service(detect(brand_new_service, target_day=target_day), "AmazonBedrock")
        assert found
        assert found[0].kind is AnomalyKind.NEW_SERVICE

    def test_a_new_service_has_no_percentage(self, brand_new_service, target_day):
        """`delta_pct is None`. Dividing by a zero baseline without checking is
        the first bug everyone writes here."""
        found = _for_service(detect(brand_new_service, target_day=target_day), "AmazonBedrock")
        assert found[0].delta_pct is None

    def test_a_new_but_trivial_service_is_not_reported(self, series, target_day):
        """New and $3/day is not news. The dollar floor applies here too - without
        it, every experiment anyone starts generates an alert."""
        trivial = series("AmazonPolly", [0] * 20 + [3])
        assert detect(trivial, target_day=target_day) == []

    def test_no_history_is_not_the_same_as_an_expected_zero(self, series, target_day):
        """Conflating them makes every genuinely new service a critical anomaly
        forever, which trains people to ignore the NEW_SERVICE kind entirely."""
        short = series("AmazonEKS", [500, 500])
        assert baseline_for(short, target_day, thresholds=THRESHOLDS) == 0.0


class TestOrderingAndSeverity:
    def test_anomalies_sort_by_absolute_dollars(self, all_fixtures, target_day):
        """Someone reads the first three lines. They must be the three that cost
        the most money - not the three with the biggest percentages."""
        found = detect(all_fixtures, target_day=target_day)
        deltas = [abs(a.delta_usd) for a in found]
        assert deltas == sorted(deltas, reverse=True)

    def test_severity_comes_from_dollars_not_percentage(self, genuine_anomaly, target_day):
        found = _for_service(detect(genuine_anomaly, target_day=target_day), "AmazonCloudWatch")
        assert found[0].severity.value in {"warning", "critical"}

    def test_services_are_compared_independently(self, series, target_day):
        """A $2,000 rise in one service hidden behind a $2,000 fall in another is
        two findings, not zero. Grouping before comparing is what prevents it."""
        up = series("AmazonEC2", [1000] * 20 + [3000])
        down = series("AmazonRDS", [3000] * 20 + [1000])
        found = detect([*up, *down], target_day=target_day)
        assert len(found) == 2


class TestFalsePositiveRate:
    def test_exactly_the_expected_findings_across_all_fixtures(self, all_fixtures, target_day):
        """The acceptance criterion, as a test.

        Seven fixtures. On the target day, exactly two should be reported:
        `AmazonCloudWatch` (the genuine spike) and `AmazonBedrock` (the new
        service). `AmazonS3`'s sustained trend is found by `detect_trends` and
        should also surface through `detect` - decide whether it counts here and
        update the expected set, deliberately.

        Every other service appearing is a false positive. Record the rate and
        the thresholds that produced it in `DECISIONS.md`, **with a number**.
        """
        found = {a.service for a in detect(all_fixtures, target_day=target_day)}
        assert found == {"AmazonCloudWatch", "AmazonBedrock", "AmazonS3"}

    def test_the_thresholds_used_are_reportable(self):
        """Someone will disagree with a finding. The conversation is much shorter
        when the report can say what it was looking for."""
        assert Thresholds().min_delta_usd > 0
        assert Thresholds().trend_days >= 2


def test_classify_returns_none_for_a_normal_day():
    """The pure unit, directly. Most days are not anomalies."""
    normal = DailyCost(day=date(2026, 9, 21), service="AmazonEC2", amount_usd=1000.0)
    assert classify(normal, 1000.0, thresholds=THRESHOLDS) is None
