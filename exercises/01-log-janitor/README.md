# E01 — Build-Artifact Janitor

**Phase 1 · Scripts that survive being run unattended · ~6-8 hours**

## The problem

Your self-hosted CI runners keep going amber and then red. Someone SSHes in, runs
`rm -rf /var/lib/builds/*`, and the fleet is healthy again for eleven days. Last time, that someone
deleted a directory another job was mid-way through writing to, and a release went out with a
truncated artifact.

You need a janitor that runs on a schedule, prunes by policy instead of by vibes, can be reviewed
before it's trusted, and cannot be the reason a release breaks.

This is deliberately the least glamorous exercise in the set. It is also the one whose habits every
later exercise assumes — E03 deletes EBS volumes, and nobody should let you write that until you can
write this.

## What you're building

A `logjanitor` CLI that sweeps a directory tree against a retention policy:

```bash
logjanitor --root /var/lib/builds --max-age-days 14 --keep-minimum 5 --protect 'release/*'
logjanitor --root /var/lib/builds --max-age-days 14 --apply
```

Three rules that compose: maximum age, maximum total size, and a minimum number of artifacts to keep
whatever else happens. Plus glob patterns that are never deleted.

## Start here

```bash
uv sync
uv run pytest        # 26 failed, 1 passed. That's the starting line.
```

(The one that already passes is `test_missing_root_is_exit_2` — typer rejects a non-existent
`--root` before your code ever runs. Free exit code, courtesy of declaring the option properly.)

Then implement, in this order — each module is independently testable, so you get green tests before
moving on:

1. **`src/logjanitor/policy.py`** → `select_for_deletion`. Pure function, no I/O, no clock. This is
   the real exercise; the rest is plumbing. `tests/test_policy.py` is its specification — read all
   ten tests before writing anything, because several of them encode decisions you'd otherwise make
   by accident.
2. **`src/logjanitor/store.py`** → `LocalStore`. Walk a tree, yield artifacts, delete idempotently.
3. **`src/logjanitor/sweep.py`** → `sweep`. Wire the two together, honour `dry_run`, log events.
4. **`src/logjanitor/cli.py`** → `main`. Parse options, build the policy, set exit codes.

`models.py` and the JSON logging setup in `cli.py` are given to you complete.

## Acceptance criteria

- [ ] `uv run pytest` — all green
- [ ] `uv run ruff check . && uv run ruff format --check .` — clean
- [ ] `uv run mypy --strict src` — clean
- [ ] Default invocation deletes nothing; `--apply` is required to remove anything
- [ ] A dry run and a real run produce identical plans and identical reported numbers
- [ ] Every line on stdout is a JSON object with at least `ts`, `level`, `event`
- [ ] Exit 0 on success, 2 on misuse (bad path, or no retention rule given)
- [ ] Running it twice in a row is safe and the second run reports nothing to do

## Hints, in increasing order of spoiler

<details>
<summary>The policy function keeps getting tangled</summary>

Don't try to compute the answer in one pass. Build a set of "immune" keys first (protected patterns
plus the newest `keep_minimum`), then walk a sorted list marking victims, then return the marked
ones. Three simple passes beat one clever comprehension, and only one of them is readable in review.
</details>

<details>
<summary>The size-budget test is fighting me</summary>

The budget is about what *remains*, not about what you delete. Compute the retained total including
protected artifacts, then delete oldest-first until you're under — or until nothing deletable is
left. That second exit condition is what `test_unsatisfiable_budget_does_not_raise` is checking.
</details>

<details>
<summary>How do I make dry-run and apply provably identical?</summary>

If you find yourself writing `if dry_run:` anywhere in the selection logic, stop. Select first,
unconditionally; then loop over the selection and call `store.delete` only when applying. One
branch, at the very end, is the whole difference.
</details>

<details>
<summary>mypy is unhappy about the store protocol</summary>

`RecordingStore` in the tests never inherits from `ArtifactStore` — it matches structurally. If mypy
complains where you pass it, your `sweep` signature is probably asking for a concrete class instead
of the protocol.
</details>

## Stretch: the S3 backend

Add `S3Store(bucket, prefix)` behind the same protocol and test it with moto. See the notes at the
bottom of `store.py` — pagination, batched deletes, and idempotent deletion are all things Phase 2
will assume you've met.

The interesting part isn't the S3 API. It's that `sweep`, `policy`, and every test you already wrote
should need **zero** changes. If they don't, the seam was in the wrong place, and finding that out
here costs you an hour instead of a sprint.

## When you're done

Write three lines in `DECISIONS.md` about the boundary case you found hardest to settle. There's at
least one in here where two defensible answers exist and the tests pick one — being able to name it,
and say why the other was worse, is a Senior-level interview answer about a junior-level tool.
