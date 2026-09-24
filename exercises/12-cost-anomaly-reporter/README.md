# E12 — Cost-Anomaly Reporter (Capstone)

**Phase 6 · Operational Python · ~12-15 hours**

## The problem

The AWS bill went up 30% in March. It's now May, and finance is asking why. The answer turns out to
be a misconfigured log retention policy shipped on 4 March, which has been writing 400GB/day to
CloudWatch ever since. Nobody noticed, because nobody looks at the bill until the month closes, and
by then the shape of the increase is buried under normal variance.

## What you're building

A scheduled reporter that catches spend regressions in days, attributes them to the team that caused
them, and says so somewhere people read.

```bash
cost-watch report --lookback 14d --post slack
```

## Requirements

**The analysis:**

- **Cost Explorer via boto3** — `get_cost_and_usage`, grouped by service, by linked account, and by
  cost-allocation tag. Note that Cost Explorer charges **per API request**; a naive implementation
  that queries per-service-per-day is itself a cost anomaly. Batch and cache deliberately.
- **Anomaly detection that survives contact with real data.** Week-over-week percentage change is
  the starting point and it will drown you in false positives: weekends differ from weekdays,
  month-end batch jobs spike, and a service costing $0.40 that doubles is not news. Handle at least
  seasonality, an absolute-dollar floor, and new services appearing (infinite percentage increase
  from zero). Getting the false-positive rate low enough that people keep reading the report is the
  actual engineering problem here.
- **Attribution.** Map spend to an owning team through cost-allocation tags. Untagged spend is its
  own line item and should be reported prominently — "$14,000 of untagged spend" is a finding, not a
  gap in your tool.
- **Trend, not just delta.** Three consecutive days of +8% matters more than one day of +20%.

**The operational side — this is the phase's real content:**

- **Instrument the reporter itself with OpenTelemetry.** Traces for the collection phase, metrics for
  API calls made and dollars analysed. Your own tooling deserves the observability you'd demand of a
  service.
- **Alert on the automation, not just from it.** A reporter that silently stops running is worse than
  no reporter, because everyone assumes silence means no anomalies. Emit a heartbeat and alert on its
  absence.
- **Idempotent and re-runnable** for any historical date range, so you can backfill and so a failed
  run just runs again.
- **Report degraded results rather than failing.** One account's Cost Explorer being unavailable
  should produce a report covering the rest, clearly marked as partial.

## Acceptance criteria

- [ ] Same done bar as E01
- [ ] Tested against fixture cost data including: a genuine anomaly, a weekend dip, a month-end
      spike, a brand-new service, and a tiny-but-doubled service
- [ ] False-positive rate documented against your fixture set — with a number, not an adjective
- [ ] OpenTelemetry traces emitted and verified in a local collector
- [ ] Missing heartbeat triggers an alert path (test it by not running it)
- [ ] Report renders readably in Slack and as plain text

## Why this is the capstone

It requires everything the roadmap built: safe unattended execution (Phase 1), boto3 depth and
pagination (Phase 2), tests that prove the analysis rather than the plumbing (Phase 3), scheduled
pipeline execution (Phase 4), and an interface people consume (Phase 5). Plus the thing none of the
others needed — **judgment about what's worth alerting on**, which is the skill that separates
monitoring that gets read from monitoring that gets muted.

It's also FinOps-adjacent, which the August career report lists explicitly as a Senior→Staff
differentiator, and it produces the kind of outcome that belongs on a resume: not "wrote a Python
tool" but "cut time-to-detect on spend regressions from 30 days to 2."

## Publish this one

Along with E10, this is the strongest portfolio piece here. The write-up matters more than the code:
lead with the 30-days-to-2 framing, show the false-positive problem and how you attacked it, and be
honest about what you'd do differently. That's a technical blog post hiring managers finish reading.
