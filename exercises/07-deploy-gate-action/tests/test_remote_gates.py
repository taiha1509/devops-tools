"""Contract for the two gates that talk to the network: error budget and incidents.

Both have the same three cases - allow, block, and **error** - and the error case
is the one that matters. A gate that fails open is decoration: the one moment it
cannot reach your metrics is disproportionately likely to be the moment your
metrics stack is already on fire, which is when you least want a deploy going
out.

Every test here runs with no network. `respx` intercepts at the transport layer,
so the gate's own timeout and error handling are what gets exercised.
"""

from __future__ import annotations

import httpx
import pytest
import respx

from deploy_gate.budget import MetricsUnavailable, evaluate_error_budget, fetch_burn_rate
from deploy_gate.incidents import (
    Incident,
    IncidentApiUnavailable,
    evaluate_open_incidents,
    fetch_open_incidents,
)

METRICS_URL = "https://metrics.example.com/error-budget"
INCIDENTS_URL = "https://incidents.example.com/open"


class TestErrorBudgetDecision:
    """Pure half - no HTTP. The cheap tests, so there is no excuse for skipping them."""

    def test_budget_above_threshold_allows(self):
        assert evaluate_error_budget(0.80, threshold=0.5).allowed is True

    def test_budget_below_threshold_blocks(self):
        result = evaluate_error_budget(0.20, threshold=0.5)
        assert result.allowed is False
        assert result.failed_closed is False

    def test_exactly_at_the_threshold_allows(self):
        """Boundary decision, pinned. Document it in the --help either way."""
        assert evaluate_error_budget(0.5, threshold=0.5).allowed is True

    def test_unavailable_blocks_and_is_marked_failed_closed(self):
        """`failed_closed` is what separates "stop shipping, fix reliability" from
        "fix your metrics endpoint". They look identical in a Checks tab
        otherwise, and they need completely different responses."""
        result = evaluate_error_budget(None, threshold=0.5)
        assert result.allowed is False
        assert result.failed_closed is True


class TestErrorBudgetFetch:
    @respx.mock
    def test_reads_the_remaining_fraction(self, client):
        respx.get(METRICS_URL).mock(return_value=httpx.Response(200, json={"remaining": 0.42}))
        assert fetch_burn_rate(METRICS_URL, client=client) == pytest.approx(0.42)

    @respx.mock
    def test_a_connection_error_raises_metrics_unavailable(self, client):
        respx.get(METRICS_URL).mock(side_effect=httpx.ConnectError("no route to host"))
        with pytest.raises(MetricsUnavailable):
            fetch_burn_rate(METRICS_URL, client=client)

    @respx.mock
    def test_a_timeout_raises_rather_than_hanging_the_deploy(self, client):
        """A metrics endpoint that hangs must not hang the deploy. Five seconds
        then fail closed is a decision; an indefinite wait is not."""
        respx.get(METRICS_URL).mock(side_effect=httpx.ReadTimeout("too slow"))
        with pytest.raises(MetricsUnavailable):
            fetch_burn_rate(METRICS_URL, client=client)

    @respx.mock
    def test_a_500_raises(self, client):
        respx.get(METRICS_URL).mock(return_value=httpx.Response(500))
        with pytest.raises(MetricsUnavailable):
            fetch_burn_rate(METRICS_URL, client=client)

    @respx.mock
    @pytest.mark.parametrize("bad", [-1.0, 1.5, 1e9])
    def test_an_out_of_range_value_is_not_treated_as_healthy(self, client, bad):
        """A metrics bug returning `-1` must not read as "budget is fine".

        This is the subtle one: every other failure here is loud, and this one
        arrives as a perfectly valid HTTP 200.
        """
        respx.get(METRICS_URL).mock(return_value=httpx.Response(200, json={"remaining": bad}))
        with pytest.raises(MetricsUnavailable):
            fetch_burn_rate(METRICS_URL, client=client)

    @respx.mock
    def test_an_unparseable_body_raises(self, client):
        respx.get(METRICS_URL).mock(return_value=httpx.Response(200, text="<html>nope</html>"))
        with pytest.raises(MetricsUnavailable):
            fetch_burn_rate(METRICS_URL, client=client)


class TestIncidentDecision:
    def test_no_open_incidents_allows(self):
        assert evaluate_open_incidents([], environment="production").allowed is True

    def test_an_open_sev1_blocks_production(self):
        sev1 = Incident(incident_id="INC-42", severity="sev1", title="checkout 5xx")
        result = evaluate_open_incidents([sev1], environment="production")
        assert result.allowed is False
        assert "INC-42" in result.reason

    def test_an_open_sev1_does_not_block_staging(self):
        """The fix often *is* a deploy, and it needs to reach staging first.
        Blocking every environment during an incident is counterproductive."""
        sev1 = Incident(incident_id="INC-42", severity="sev1", title="checkout 5xx")
        assert evaluate_open_incidents([sev1], environment="staging").allowed is True

    def test_a_sev3_does_not_block(self):
        sev3 = Incident(incident_id="INC-43", severity="sev3", title="typo in footer")
        assert evaluate_open_incidents([sev3], environment="production").allowed is True

    def test_unavailable_blocks_production_and_is_marked_failed_closed(self):
        result = evaluate_open_incidents(None, environment="production")
        assert result.allowed is False
        assert result.failed_closed is True

    @pytest.mark.parametrize("spelling", ["SEV1", "Sev1", "sev-1", "P1", "1", "critical"])
    def test_severity_spellings_are_normalised(self, spelling):
        """Every incident tool spells it differently. Normalise in one place, at
        fetch time - scattering it across the gate is how you end up blocking on
        `SEV1` but not on `Sev1`.

        Decide which spellings you support and pin them here. If you reject `P1`
        and `critical`, change this list and say why in `DECISIONS.md`.
        """
        inc = Incident(incident_id="INC-44", severity=spelling, title="down")
        assert evaluate_open_incidents([inc], environment="production").allowed is False


class TestIncidentFetch:
    @respx.mock
    def test_parses_the_open_list(self, client):
        respx.get(INCIDENTS_URL).mock(
            return_value=httpx.Response(
                200,
                json={
                    "incidents": [
                        {"id": "INC-42", "severity": "SEV1", "title": "checkout 5xx"},
                    ]
                },
            )
        )
        incidents = fetch_open_incidents(INCIDENTS_URL, client=client)
        assert [i.incident_id for i in incidents] == ["INC-42"]

    @respx.mock
    def test_unreachable_raises(self, client):
        respx.get(INCIDENTS_URL).mock(side_effect=httpx.ConnectError("down"))
        with pytest.raises(IncidentApiUnavailable):
            fetch_open_incidents(INCIDENTS_URL, client=client)
