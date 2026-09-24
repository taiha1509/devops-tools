# E03 — Orphan Resource Reaper

**Phase 2 · boto3 at depth · ~8-10 hours**

## The problem

Your AWS bill has a floor nobody can explain. Someone eventually runs a manual audit and finds 340
unattached EBS volumes, 22 unassociated Elastic IPs, and snapshots going back three years from an
instance class you stopped using in 2024. Together: low five figures a year, for nothing.

The obvious fix — a script that deletes unattached volumes — is also how you delete the volume
someone detached twenty minutes ago while debugging a production incident.

## What you're building

`reaper` — finds orphaned AWS resources, prices them, and (only when explicitly told) deletes them.

```bash
reaper scan --region ap-southeast-1 --older-than-days 30
reaper scan --region ap-southeast-1 --older-than-days 30 --apply
```

Resource types, in increasing order of difficulty:

1. **Unattached EBS volumes** — `state == "available"`
2. **Unassociated Elastic IPs** — no `AssociationId`
3. **Snapshots** whose source volume no longer exists, older than N days
4. **Empty target groups** — no registered targets, no listener rules

## Requirements

This is the phase where boto3 stops being snippets. Every item below is a real failure mode:

- **Paginate everything.** `describe_volumes` truncates. A reaper that reads page one finds 50
  orphans out of 340 and reports success — the worst possible outcome, because it looks like it
  worked. Use `client.get_paginator(...)`, never a bare call, and never a hand-rolled `NextToken`
  loop.
- **Respect a `DoNotReap` tag** and any `--exclude-tag key=value` passed on the command line.
- **Respect an age floor.** Nothing created or detached within `--older-than-days` is touched. This
  is what protects the engineer mid-incident.
- **Handle throttling properly.** Read
  [the boto3 retries guide](https://boto3.amazonaws.com/v1/documentation/api/latest/guide/retries.html)
  first: standard mode already retries `Throttling`, `ThrottlingException`,
  `RequestThrottledException`, `ProvisionedThroughputExceededException`, and HTTP 429/5xx, five
  attempts, exponential backoff base 2 capped at 20s. Configure the mode deliberately via
  `botocore.config.Config`; don't wrap every call in your own retry decorator on top of it. Know
  what you're adding and why.
- **Branch on error codes, not strings.** `err.response["Error"]["Code"] == "VolumeInUse"`, not
  `"in use" in str(err)`.
- **Estimate cost.** Report monthly spend per orphan class. This is what turns a script into a thing
  your manager forwards to their manager.
- **Dry-run by default**, same invariant as E01: the plan must not depend on the flag.

## Acceptance criteria

- [ ] Same done bar as E01
- [ ] Multi-page fixtures in the tests — at least one resource type returns 3 pages
- [ ] Deleting an already-deleted resource is not an error
- [ ] One region failing doesn't abort the others; the summary reports which failed and why
- [ ] `--apply` deletes; anything else does not, and the two produce identical plans
- [ ] Cost estimate in the summary output

## Testing

moto for everything. Tests come in E05 — but write them as you go anyway; you'll just go deeper
there. Note what moto **doesn't** model: it won't enforce IAM, won't throttle you, and won't show
you eventual consistency. Write those gaps down; E05 asks you to.

## Why this one matters

This is the exercise you'll talk about in interviews. It's destructive, it touches money, and the
interesting content is entirely in the safety design — the tag exclusions, the age floor, the
dry-run invariant, the partial-failure handling. Anyone can call `delete_volume`. The gap between
mid-level and Senior is everything around it.
