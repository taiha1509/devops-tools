# E05 — A Test Suite That Earns Approval

**Phase 3 · Testing infrastructure code · ~8-10 hours**

## The problem

You've written the reaper (E03). Now get it approved. Your reviewer's actual question isn't "did you
test it" — it's *"what does your test suite prove, and what does it not?"* Most infra test suites
answer: "that the happy path calls the API I expected." That proves nothing about a tool whose job is
deleting things.

## What you're building

No new features. You're retrofitting E03 with a suite that would let a sceptical reviewer approve
`--apply` against production.

## Required tests

**The invariant tests** — these are the ones that matter:

- [ ] **Dry run deletes nothing.** Assert on the store/client, not on the return value: zero
      `delete_*` calls reached AWS.
- [ ] **Dry run and apply produce identical plans** for identical input.
- [ ] **Exclusion tags are honoured** even when every other rule says delete.
- [ ] **The age floor is honoured** at the boundary, both sides.
- [ ] **Running twice is safe** — the second run finds nothing and deletes nothing.

**The failure-path tests** — the ones nobody writes:

- [ ] **Pagination.** A fixture with 3 pages. Assert the reaper found resources on page 3. This test
      is the entire reason E03 insisted on paginators; write it and then deliberately break the
      paginator to watch it catch the bug.
- [ ] **Throttling.** Inject `ThrottlingException` on the first N calls and assert the run still
      completes. Then inject it on *every* call and assert the run fails loudly rather than
      reporting a successful sweep of zero resources.
- [ ] **Partial failure.** Region A works, region B raises. Assert A's results are present and B is
      reported as failed.
- [ ] **A delete that fails mid-run** — assert the summary reports it and the exit code reflects it.
- [ ] **Expired credentials** mid-sweep.
- [ ] **A resource with no tags at all** — the `KeyError` that takes down more infra scripts than any
      other single bug.

**The honesty artifact:**

- [ ] `TESTING.md` stating what this suite does **not** prove. moto doesn't evaluate IAM policies,
      doesn't reproduce eventual consistency, doesn't enforce service quotas, and its throttling is
      something you injected rather than something that happened. Write down what would have to be
      verified against a real account before anyone runs this for real.

## Technique

- `moto` mocks as pytest fixtures, scoped so state doesn't leak between tests. A test that passes
  alone and fails in a suite is a scoping bug — find it now, not in CI.
- Freeze time rather than sleeping. Age policies tested against the wall clock are flaky by
  construction.
- Inject failures with `botocore.stub.Stubber` or by patching at a seam you own. If you can't inject
  a throttle without monkeypatching something private, that's a design signal about E03.
- Coverage is a diagnostic, not a target. Use it to find the branch you forgot, then ignore the
  number.

## Acceptance criteria

- [ ] Every box above ticked
- [ ] Full suite runs in under 10 seconds (moto is in-process; there's no excuse for slow)
- [ ] Tests pass in a random order (`pytest -p no:randomly` off, or add `pytest-randomly`)
- [ ] `TESTING.md` exists and is specific, not boilerplate

## Why this one matters

This is the highest-leverage exercise in the roadmap for interview performance. "I wrote a reaper" is
a mid-level answer. "I wrote a reaper, and here's the test that proves a dry run is trustworthy, and
here's the list of things my tests deliberately don't cover" is a Senior answer — and the second half
of that sentence is what makes it one.
