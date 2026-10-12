# What this suite proves, and what it does not

**The honesty artifact.** This file is an acceptance criterion, not documentation
garnish, and it is the half of the sentence that makes "I wrote a reaper" into a
Senior answer. Fill in every section with specifics. If a section still reads like
the prompt below it, it is not done.

Keep it short and concrete. Boilerplate here is worse than nothing, because
boilerplate claims rigour you have not got.

---

## What it proves

List the properties the suite actually establishes, each with the test that
establishes it. One line each.

| Property | Test |
|---|---|
| A dry run makes zero delete calls | `test_dry_run_makes_zero_delete_calls` |
| ... | ... |

## How deletions are counted

The dry-run invariant is only as good as the boundary you assert at. State which
mechanism you used — `botocore` event hook, `Stubber`, monkeypatched client — and
why. Then state what that mechanism would **miss**: if the reaper deleted via a
path your hook does not cover, would this suite notice?

## What it does not prove

This is the section that matters. moto reimplements AWS behaviour rather than
reproducing it. Be specific about each gap, not just that gaps exist:

- **IAM is not evaluated.** moto does not run policy evaluation, so every test
  here runs with effectively unlimited permissions. A reaper that works in this
  suite can still fail on `UnauthorizedOperation` against a real account, and the
  interesting case — permission to *describe* but not to *delete* — is invisible
  here. Say what you would check against a real account before trusting `--apply`.
- **Eventual consistency is absent.** moto is immediately consistent. In reality a
  volume can appear `available` in one call and be attached by the next. Which of
  your tests would pass but should not?
- **Service quotas and real throttling are absent.** Every throttle in this suite
  is one *you injected*. You tested your handling of a `ThrottlingException`
  object, not your handling of being throttled — the retry timing, the total run
  duration, the interaction with a Lambda timeout are all untested.
- **Pagination page sizes are yours, not AWS's.** Your 3-page fixture uses your
  page size. Real `describe_volumes` pages at up to 500 and the boundary cases are
  different.
- **Cost estimates are unvalidated.** Pricing came from where? Is it per-region?
  Does it account for volume type? A confidently wrong dollar figure is worse than
  none, because it gets quoted in a meeting.

Add anything else your implementation made you aware of.

## What must be verified against a real account first

A short, ordered checklist for the day someone wants to run this for real.
Scratch account, `--dry-run`, and what to read in the output before trusting it.

- [ ] ...

## Suite health

- Runtime: `___` seconds (criterion: under 10 — moto is in-process, there is no
  excuse for slow)
- Passes under `pytest-randomly`: yes / no
- Branch coverage used as a diagnostic: which branch did it find that you had
  forgotten? (Then stop looking at the number.)
