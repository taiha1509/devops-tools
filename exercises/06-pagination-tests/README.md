# E06 — Pagination, Normalisation, and the Bugs You Can't See

**Phase 3 · Testing infrastructure code · ~6-8 hours**

## The problem

The inventory from E04 says you run 1,200 resources. The real number is 4,100. Nothing errored,
nothing logged a warning, and the JSON looked completely plausible. Three services truncated at the
first page and one normaliser silently dropped every resource whose tag block was absent.

This is the defining bug class of infrastructure tooling: **wrong answers that look like right
answers.** No exception, no alert — just a number that's quietly false, which then gets used to make
a decision.

## What you're building

A test suite for E04 that makes this class of bug impossible to ship, plus the property-based tests
that catch the normaliser cases you wouldn't think to write by hand.

## Part 1 — Pagination, properly

- [ ] A fixture factory that produces N pages for any paginated API, parameterised by page count
- [ ] Every collector tested at **0, 1, and 3+ pages**. One page is the case that hides the bug;
      zero is the case that crashes on `[0]`.
- [ ] A test that asserts the **total count**, not just "some results came back"
- [ ] A deliberately broken paginator committed on a branch, with a note in your `DECISIONS.md`
      confirming the suite catches it. Proving your test fails when the code is wrong is the only
      way to know the test works.
- [ ] A regression test naming the real-world symptom in its docstring, so the next person
      understands why it exists

## Part 2 — Normalisation, property-based

Install `hypothesis`. Hand-written tests check the cases you imagined; property tests find the ones
you didn't.

Properties worth asserting about your E04 normaliser:

- [ ] **Total preservation** — normalising N raw resources yields exactly N records, never fewer.
      This is the one that would have caught the dropped-tags bug.
- [ ] **Idempotence** — normalising twice equals normalising once
- [ ] **Determinism** — input order doesn't change output
- [ ] **Totality** — no input shape raises. Missing tags, empty tag list, unicode tag values, a
      resource ID that's `None`, a timestamp with no timezone. Hypothesis will find these faster
      than you will.
- [ ] **Round-trip** — serialise and deserialise your schema, get the same object back

## Part 3 — The write-up

- [ ] Add a section to `TESTING.md` (from E05) on silent-wrongness: which of your collectors could
      still return a plausible-but-false answer, and what would detect it in production. Monitoring
      your own tooling's output for implausible deltas is the production-grade answer here, and
      noticing that is the point.

## Acceptance criteria

- [ ] Same done bar as E01
- [ ] Hypothesis finds at least one real bug in your E04 normaliser. If it doesn't, your properties
      are too weak — strengthen them before concluding the code is perfect.
- [ ] Every paginated collector has a 3+ page test asserting an exact count

## Why this one matters

Two reasons. The obvious one: first-page-only bugs are endemic and you'll now be immune. The less
obvious one: property-based testing is rare enough in infrastructure work that using it well is a
visible signal, and it maps directly onto how you should think about infrastructure invariants
generally — "what must always be true?" is the same question whether you're writing a Hypothesis
property or a Terraform policy check.
