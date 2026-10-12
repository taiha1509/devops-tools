"""Rendering the report, for Slack and for a terminal.

The report is the product. Perfect detection rendered badly gets muted.

YOUR JOB: implement `render_text`, `render_slack`, and `post_slack`.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    import httpx

    from cost_watch.models import Report


def render_text(report: Report) -> str:
    """Plain text, for a terminal and for the `--no-post` path.

    Order, and the reasoning:

        1. The headline: total spend, change against baseline, anomaly count.
        2. **"Partial report"** first and loudly if any account was unreachable.
           A reader who does not notice this draws conclusions from a report
           missing an account, and will not think to check.
        3. Anomalies, biggest **dollar** impact first.
        4. Untagged spend as its own line.
        5. The thresholds used. Someone will disagree with a finding, and the
           conversation is much shorter when the report says what it was looking
           for.

    Keep "no anomalies" short and unmistakable. It is the output 90% of runs
    produce, and a wall of text on a quiet day teaches people to skip it - at
    which point they skip the noisy day too.
    """
    raise NotImplementedError


def render_slack(report: Report) -> dict[str, Any]:
    """Slack Block Kit payload.

    Constraints that bite:

        * Block Kit caps at **50 blocks** per message and ~3,000 characters per
          text object. A long report silently fails to post, or posts truncated.
          Cap the anomaly list and link out for the rest.
        * Put the headline in the **notification text** as well as the blocks.
          The mobile push shows that string, and "cost-watch report" tells nobody
          whether to open it; "$2,400/day increase in CloudWatch Logs" does.
        * Do not @-mention a team for an INFO finding. One unnecessary ping at
          09:00 and the channel is muted forever, which costs you every future
          CRITICAL too.
    """
    raise NotImplementedError


def post_slack(payload: dict[str, Any], *, webhook_url: str, client: httpx.Client) -> None:
    """POST to a Slack webhook.

    `client` injected so tests stub the transport. Treat a non-2xx as a failure
    of the **run**, not a warning: a report that was generated and not delivered
    is a report that does not exist, and exiting 0 means the schedule believes it
    succeeded.
    """
    raise NotImplementedError


__all__ = ["post_slack", "render_slack", "render_text"]
