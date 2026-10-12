# Silent wrongness — what could still return a plausible, false answer

**Part 3 of E06.** The brief says to add this as a section to E05's `TESTING.md`;
it lives here as its own file so the two exercises stay independently runnable.
Either merge it into E05's when you finish, or link them — but keep one place
where the honest limits of the whole inventory pipeline are written down.

Fill in every section with specifics about *your* implementation.

---

## The bug class

An exception is a gift: it has a stack trace, it fires an alert, and somebody
fixes it. The dangerous failure is the one that returns a number.

> The inventory reported 1,200 resources. The real number was 4,100. Nothing
> errored, nothing logged a warning, and the JSON looked completely plausible.

That number then got used to make a decision. No test of the form "assert it
didn't crash" would have caught it, and neither would a coverage target.

## Which of my collectors could still lie

Go through them one at a time. For each, name the specific mechanism by which it
could return a plausible-but-false answer, and say whether a test now prevents it.

| Collector | How it could silently undercount | Prevented by |
|---|---|---|
| EC2 instances | `Reservations` nesting flattened wrongly | `test_ec2_reservations_nesting_is_traversed` |
| EBS volumes | ... | ... |
| RDS instances | ... | ... |
| Lambda functions | tags need a second API call; skipping it makes every "untagged resources" query wrong *in the safe-looking direction* | ... |

Then the ones no test covers:

- **Region lists.** If a region is missing from config, its resources do not
  exist as far as this tool is concerned, and the output looks complete. What
  would detect a forgotten region?
- **Resource types not implemented.** The schema has four. An estate has
  hundreds. Does the output make clear that "no S3 buckets" means "S3 was never
  collected" rather than "there are none"?
- **Partial runs read as complete.** E04 writes `failures` and the `partial`
  flag, and `inventory query` warns on a partial dataset. Is that warning
  impossible to miss, or is it one line above the results?

## What would detect this in production

Testing cannot. The production-grade answer is **monitoring your own tooling's
output for implausible deltas** — and noticing that is the point of this
exercise.

Specifics to decide on:

- Alert when the resource count moves by more than N% between runs. What is N for
  your estate, and why?
- Alert when a collector returns exactly zero for an account that returned
  non-zero yesterday. Zero is the signature of a broken collector far more often
  than of a cleaned-up account.
- Alert when a collector's result count equals its page size exactly — the
  fingerprint of a first-page-only bug.
- Reconcile against an independent source (AWS Config, Cost Explorer line items,
  a billing resource count). Two tools agreeing is weak evidence; two tools
  disagreeing is strong evidence.

## What Hypothesis found

The acceptance criterion: at least one real bug in the E04 normaliser.

- Falsifying example:
- What was wrong:
- The fix:
- Which property caught it:

If Hypothesis found nothing, record what you widened in `strategies.py` and try
again. "The code was already correct" is almost never the explanation.

## Suite health

- Runtime: `___` seconds
- Passes under `pytest-randomly`: yes / no
- Every paginated collector has a 3+ page test asserting an exact count: yes / no
