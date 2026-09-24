# E09 — Dynamic CI Matrix Generator

**Phase 4 · Python inside CI/CD · ~6-8 hours**

## The problem

Your monorepo has 23 services. Every pull request builds all 23, runs all 23 test suites, and pushes
all 23 images. A one-line README change takes 40 minutes of CI and burns runner minutes you pay for.
Everyone has learned to open the PR and go make coffee, which means nobody notices when CI is
actually broken.

## What you're building

`ci-matrix` — computes, from the repo's actual state, the minimum set of jobs a change requires, and
emits it as a GitHub Actions matrix.

```yaml
jobs:
  plan:
    outputs:
      matrix: ${{ steps.plan.outputs.matrix }}
    steps:
      - id: plan
        run: python -m ci_matrix plan --base ${{ github.event.pull_request.base.sha }}
  build:
    needs: plan
    strategy:
      matrix: ${{ fromJson(needs.plan.outputs.matrix) }}
```

## Requirements

- **Changed-file detection** against the merge base — not against `HEAD~1`, which is wrong for any
  PR with more than one commit and wrong in a different way after a merge.
- **Dependency graph.** Service A depends on shared library L. A change to L must rebuild A. Read
  the graph from the repo (a manifest per service, or parsed imports), don't hardcode it. This is
  the part people get wrong and it's the part that makes the tool trustworthy.
- **Transitive closure** — L is depended on by A, A by B; changing L builds all three.
- **Global triggers.** Some paths (the base image, the CI config itself, a shared lockfile) mean
  "build everything." Get this wrong in the unsafe direction and you ship untested code.
- **Bounded output.** GitHub caps matrix jobs at 256. Degrade deliberately when you exceed it —
  chunk, or fall back to build-all — never emit an invalid matrix.
- **Explain itself.** `--explain` prints why each service was included. Without this, nobody will
  believe the tool the first time it skips their service, and they'll be right not to.

## Acceptance criteria

- [ ] Same done bar as E01
- [ ] Tests with a fixture repo: leaf change, shared-library change, global-trigger change, docs-only
      change (empty matrix), and a change touching a deleted service
- [ ] Empty matrix is emitted as valid JSON and the downstream job skips cleanly rather than failing
- [ ] Cycles in the dependency graph are detected and reported, not looped on forever
- [ ] `--explain` output is readable by someone who's never seen the tool

## The safety question

Write it down in `DECISIONS.md`: **when this tool is wrong, which direction should it be wrong in?**
Building too much wastes money. Building too little ships untested code. That asymmetry should drive
every default you pick — for instance, an unparseable manifest should mean "build everything," not
"build nothing."

Being able to articulate that trade-off is worth more in an interview than the implementation is.

## Why this one matters

It's the clearest example in the roadmap of pipeline logic that simply cannot live in YAML. Nobody
computes a transitive dependency closure in a workflow expression. Once you've built one of these,
the "why Python instead of bash" argument becomes self-evident rather than a matter of taste.
