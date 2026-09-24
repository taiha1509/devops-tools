# E04 — Multi-Account Inventory

**Phase 2 · boto3 at depth · ~8-10 hours**

## The problem

Someone from security asks: "which accounts have EC2 instances with public IPs and no tag telling us
who owns them?" Nobody can answer. There are fourteen AWS accounts, four regions in active use, and
the last inventory was a spreadsheet maintained by someone who left.

## What you're building

`inventory collect` — assumes a role into every account, sweeps every region, normalises what it
finds, and writes one dataset you can actually query.

```bash
inventory collect --accounts accounts.yaml --output inventory.json
inventory query inventory.json --public-ip --missing-tag Owner
```

## Requirements

- **Cross-account `sts:AssumeRole`**, one role per account from config. This is the single most
  useful boto3 pattern you don't currently have, and it's on the critical path for any estate-wide
  tooling.
- **Credential expiry.** Assumed-role credentials are short-lived. A sweep across fourteen accounts
  and four regions can outlive them. Handle refresh rather than hoping the run is fast enough —
  `botocore`'s `RefreshableCredentials` exists for exactly this, and knowing it exists is half the
  battle.
- **Partial failure is the normal case.** One account has a broken trust policy, one region isn't
  enabled, one call gets throttled into exhaustion. The run must complete, collect everything it
  can, and report precisely what it couldn't reach and why. **A run that aborts on the first failure
  is useless at this scale** — that's the whole lesson of this exercise.
- **Concurrency**, because serial across 56 account-region pairs is a coffee break. Thread pool is
  fine. Watch out: a botocore `Session` is not safe to share carelessly across threads — create one
  per worker and understand why.
- **Normalise to a stable schema.** EC2, RDS, and Lambda all describe themselves differently;
  your output shouldn't. Define the target schema first, with pydantic, then map into it.
- **Deterministic output.** Same estate, same JSON, byte for byte — so you can diff two runs and see
  what changed. Sort everything.

## Acceptance criteria

- [ ] Same done bar as E01
- [ ] moto tests covering: happy path, one account's assume-role denied, one region unavailable,
      throttling exhaustion in one account
- [ ] The summary distinguishes "collected 0 resources" from "failed to collect"
- [ ] Two runs against identical state produce byte-identical output
- [ ] `query` supports at least: filter by tag presence/absence, by public IP, by resource type

## Why this one matters

Cross-account access and honest partial-failure handling are the two things that separate tooling
that works in your sandbox from tooling that works across an organisation's estate. The August
career report puts "cross-team influence" at the centre of Staff scope — this is the technical
prerequisite for it. You cannot influence an estate you cannot see.

## Stretch

If the thread pool starts feeling like the wrong tool — and at 56 concurrent sweeps it might —
this is the natural place to take the async detour the roadmap mentions. `aioboto3` exists.
Measure before you rewrite, and write down what the measurement said.
