# E08 — Terraform Drift Detector

**Phase 4 · Python inside CI/CD · ~8-10 hours**

## The problem

Someone fixed a production outage at 3am by changing a security group rule in the console. Entirely
the right call at the time. Six weeks later an unrelated `terraform apply` silently reverted it and
caused a second outage — and the plan output that would have shown this scrolled past in a CI log
nobody reads.

Plans are reviewed by humans only when humans can see them. A 900-line plan in a collapsed log is
not visible.

## What you're building

`driftwatch` — runs against a Terraform plan, classifies what's changing by blast radius, and posts
a summary where reviewers actually look.

```bash
terraform plan -out=tf.plan && terraform show -json tf.plan > plan.json
driftwatch analyse plan.json --post-comment --fail-on destructive
```

## Requirements

- **Parse `terraform show -json`**, not the human-readable output. The JSON plan format is stable
  and documented; scraping the text output is how you build something that breaks on the next
  Terraform minor release.
- **Classify every change** into: `create`, `update-in-place`, `replace` (destroy-then-create), and
  `destroy`. `replace` is the interesting one — it looks like an update in the summary line and
  causes an outage in reality.
- **Blast-radius ranking.** A replaced RDS instance and a replaced CloudWatch alarm are not the same
  event. Maintain a severity map by resource type, with a sensible default for unknown types, and
  make it configurable — you'll get the defaults wrong for someone's stack.
- **Detect true drift** specifically: changes where the plan differs from state *without* a
  corresponding code change. That's the console-fix case, and it's different from an intentional
  diff.
- **PR comment** that's a summary, not a dump: counts by category, the destructive changes in full,
  everything else collapsed behind a `<details>`. Update the existing comment on re-runs rather than
  posting a new one each push — ten stale comments is worse than none.
- **Exit codes** driving the gate: 0 clean, 1 changes present, 2 destructive changes present.

## Testing

Use committed **plan-file fixtures** — real `terraform show -json` output, captured once and saved.
No Terraform binary in the test suite, no AWS, no emulator. This is also why this exercise isn't
blocked by the LocalStack situation described in the roadmap.

Capture fixtures for: no changes, creates only, an in-place update, a replace, a destroy, an empty
plan, and a plan with a resource type your severity map has never seen.

## Acceptance criteria

- [ ] Same done bar as E01
- [ ] Fixtures for all seven cases above
- [ ] Unknown resource types are handled with a documented default, never a crash
- [ ] Re-running updates the existing PR comment instead of adding one
- [ ] `--fail-on destructive` blocks; `--fail-on none` reports without blocking
- [ ] Works locally against a plan file with no GitHub token present

## Why this one matters

Parsing structured tool output and turning it into a decision is the core competency of pipeline
engineering — this happens to be Terraform, but it's the same shape for `trivy`, `kubectl diff`,
coverage reports, and SBOM scanners. Build it once properly and you own the pattern.

## Stretch

Post the severity summary as a GitHub Check Run with annotations on the specific `.tf` lines
responsible. Considerably more work, and it's the difference between a tool people tolerate and one
they ask for.
