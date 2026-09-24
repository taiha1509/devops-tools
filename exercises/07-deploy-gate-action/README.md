# E07 — A Reusable Deploy-Gate Action

**Phase 4 · Python inside CI/CD · ~8-10 hours**

## The problem

Your org has a change freeze every Friday after 14:00 and during the last week of the quarter.
It's enforced by people remembering. Last quarter someone didn't, and the incident review produced
an action item: "add a check." The check that got added was a bash `if` comparing `date +%u` to `5`,
copy-pasted into nine repositories, and already wrong in three of them because it uses runner-local
time.

## What you're building

A **reusable GitHub Action, written in Python**, that a deploy job calls to decide whether it's
allowed to proceed.

```yaml
- uses: your-org/deploy-gate@v1
  with:
    environment: production
    freeze-windows: .github/freeze.yaml
    error-budget-threshold: "0.5"
  # fails the job, with a readable annotation, when the gate says no
```

Gates to implement:

1. **Freeze windows** from a config file — recurring (every Friday 14:00-23:59 UTC) and one-off
   (2026-12-20 to 2027-01-02). Timezone-explicit, always.
2. **Error budget** — read a burn-rate figure from a metrics endpoint; block if the remaining budget
   is below the threshold.
3. **Open Sev1** — query an incident API; block deploys to production while one is open.
4. **Override** — a `deploy-gate-override` label or an input, which **always logs loudly** with who
   overrode and why. A gate with no override is a gate people will route around; an override with no
   audit trail is a gate that doesn't exist.

## Requirements

- **Composite or Docker action** — pick one deliberately and write down why. Composite is lighter
  and starts faster; Docker gives you a pinned interpreter and real dependencies. Read
  [the GitHub docs on composite actions](https://docs.github.com/en/actions/sharing-automations/creating-actions/creating-a-composite-action)
  before choosing.
- **The same entrypoint runs locally.** `python -m deploy_gate check --environment production` must
  work on your laptop against the same config. This single property is the biggest quality-of-life
  improvement you can make to any pipeline, and it's the reason to write pipeline logic in Python at
  all rather than in YAML.
- **GitHub annotations** — emit `::error::`/`::notice::` workflow commands so the reason appears in
  the PR's Checks tab, not buried in log line 4,000.
- **Outputs** other steps can consume: `allowed`, `reason`, `overridden`.
- **Fail closed.** If the metrics endpoint is unreachable, the gate blocks and says why. A gate that
  fails open is decoration.
- **Every gate independently testable** with no network and no GitHub.

## Acceptance criteria

- [ ] Same done bar as E01
- [ ] Tests for each gate: allow, block, and the error path
- [ ] Freeze-window tests at the exact boundary minute, in two timezones
- [ ] Action runs green in a real workflow in a scratch repo — build it and screenshot it
- [ ] `action.yml` documents every input with a default and a description
- [ ] Overriding produces an audit log line naming the actor

## Why this one matters

This is the first artifact in the roadmap that other engineers *use* rather than run. That changes
the design constraints entirely: inputs are an API, error messages are UX, and a breaking change
costs nine teams an afternoon. It's also the most directly portfolio-able thing here — a public
`deploy-gate` action with a clear README is a link you can put in an application.
