# Python for DevOps — Exercises

Practice track for the roadmap in
[`../research/2026-09-21-python-devops-automation-roadmap.md`](../research/2026-09-21-python-devops-automation-roadmap.md).

Twelve exercises, each a problem that shows up in real infrastructure work. E01 is scaffolded with
failing tests — start there. The rest are briefs; scaffold them as you reach them.

## The done bar

Identical for every exercise. An exercise is finished when this exits 0 on a clean clone:

```bash
uv run ruff check .
uv run ruff format --check .
uv run mypy --strict src
uv run pytest
```

Plus the exercise-specific acceptance criteria in its README. "It works when I run it" is not the bar
— the bar is that someone else can verify it works without asking you anything.

## Setup

Install [uv](https://docs.astral.sh/uv/) once:

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

Then per exercise:

```bash
cd exercises/01-log-janitor
uv sync          # creates .venv and installs deps from pyproject.toml
uv run pytest    # should fail — that is the starting line
```

Copy `01-log-janitor/pyproject.toml` forward as the template for later exercises; it already encodes
the ruff/mypy-strict/pytest configuration the done bar checks.

## AWS in these exercises

Everything runs against [moto](https://github.com/getmoto/moto), which patches boto3 in-process. No
Docker, no AWS account, no credentials, no bill. LocalStack is deliberately **not** used — its
Community edition ended on 23 March 2026 and the remaining free tier requires an account and is
restricted to non-commercial use; see the roadmap's *Environment Decision* section.

**Never point these at a real account.** Several exercises delete things. If you do want to try one
against real AWS later, do it in a scratch account, with `--dry-run` first, and read your own
teardown code before you trust it.

**Know what moto does not prove.** It reimplements AWS behaviour rather than reproducing it: IAM
policy evaluation, eventual consistency, real throttling, and service quotas are simplified or
absent. Each exercise that leans on those says so. Being able to state the gap is itself part of the
skill being practised.

## Working notes

Keep a `DECISIONS.md` in each exercise directory: what you chose, what you rejected, why. Three lines
per decision is enough. It costs you a minute and it is the difference between "I built a reaper" and
a specific, credible interview answer six months from now.

## Exercise index

| # | Exercise | Phase | Real problem |
|---|---|---|---|
| [E01](exercises/01-log-janitor/) | Build-artifact janitor | 1 · unattended scripts | CI runners filling their disks |
| [E02](exercises/02-health-checker/) | Config-driven health checker | 1 · unattended scripts | Post-deploy smoke gate |
| [E03](exercises/03-orphan-reaper/) | Orphan resource reaper | 2 · boto3 depth | Unattached EBS/EIPs quietly billing |
| [E04](exercises/04-multi-account-inventory/) | Multi-account inventory | 2 · boto3 depth | "What do we actually run?" |
| [E05](exercises/05-reaper-test-suite/) | Test suite for the reaper | 3 · testing | Making destructive code reviewable |
| [E06](exercises/06-pagination-tests/) | Pagination & normaliser tests | 3 · testing | The first-page-only bug class |
| [E07](exercises/07-deploy-gate-action/) | Reusable deploy-gate action | 4 · CI/CD | Change freezes enforced, not remembered |
| [E08](exercises/08-drift-detector/) | Terraform drift detector | 4 · CI/CD | Console drift found before apply |
| [E09](exercises/09-ci-matrix-generator/) | Dynamic CI matrix generator | 4 · CI/CD | Monorepo CI that builds only what changed |
| [E10](exercises/10-platform-cli/) | Internal platform CLI | 5 · platform | Self-service instead of ticket queues |
| [E11](exercises/11-service-scaffolder/) | Service scaffolder | 5 · platform | New services born production-ready |
| [E12](exercises/12-cost-anomaly-reporter/) | Cost-anomaly reporter | 6 · operational | Spend regressions caught in days |
