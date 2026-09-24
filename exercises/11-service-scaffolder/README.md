# E11 — Service Scaffolder (The Golden Path)

**Phase 5 · Platform tooling · ~10-12 hours**

## The problem

Every new service at your company starts by copying the last one. So every new service inherits that
one's CI config, including the deprecated action, the missing `timeout-minutes`, and the Dockerfile
that runs as root. Six months in, you have 23 services with 23 slightly different definitions of
"correct," and no way to fix them all.

## What you're building

`plat new service <name>` — generates a service that is production-ready on day one, from templates
you can update centrally.

```bash
plat new service payments-api --template python-fastapi --team billing
```

What it generates:

- Source skeleton with the project's standard layout
- CI workflow: lint, typecheck, test, build, scan, deploy — wired to the org's reusable workflows
- Dockerfile: non-root user, pinned base image, multi-stage
- Terraform module stub with required tags already populated
- Observability: healthz endpoint, structured logging, OpenTelemetry bootstrap
- `CODEOWNERS`, a README from a template, a `.gitignore` that isn't a guess

## Requirements

- **Jinja2 templates, versioned in the repo.** Every generated project records which template
  version produced it, in a file. Without this you cannot answer "which services have the old CI
  config?" — and answering that question is the entire long-term value of the tool.
- **`plat new --check`** — run against an *existing* service and report how far it has drifted from
  the current template. This is the feature that makes the scaffolder useful after month one, when
  everything has already been generated.
- **Idempotent regeneration.** Re-running must not clobber hand-written code. Decide the rule —
  generated files are marked and owned by the tool; everything else is the team's — and enforce it.
- **Validation before generation.** Service name matches the org convention, the team exists, the
  target directory is empty. Fail before writing a single file, never halfway through.
- **A dry run that prints the file tree** it would produce.
- **Templates are testable.** Rendering every template with representative inputs, then running the
  generated project's own lint and tests, is a test you can and should automate. A scaffolder that
  emits code failing its own standards is worse than no scaffolder.

## Acceptance criteria

- [ ] Same done bar as E01
- [ ] A generated service passes its own lint, typecheck, and tests with zero manual edits
- [ ] `--check` correctly reports drift on a deliberately outdated service
- [ ] Re-running over an existing service preserves hand-written files
- [ ] At least two templates, so the abstraction is proven rather than assumed
- [ ] Generated CI workflow actually runs green in a scratch repo — prove it, don't assume it

## Why this one matters

A scaffolder is how a platform team's standards become the path of least resistance instead of a wiki
page nobody reads. That shift — from enforcing standards to making them the easy option — is
precisely the "cross-team influence" the August report puts at the centre of Staff scope, expressed
as code rather than as meetings.

The `--check` mode is the part most people don't build, and it's the part that turns a one-off
generator into an ongoing fleet-management capability. If you build only one feature beyond the
minimum, build that one.
