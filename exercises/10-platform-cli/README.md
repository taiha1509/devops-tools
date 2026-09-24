# E10 — An Internal Platform CLI

**Phase 5 · Platform tooling · ~12-15 hours**

## The problem

A developer needs a preview environment for their feature branch. Today that means filing a ticket,
waiting a day, and receiving a hand-rolled stack that's subtly different from the last one. The
platform team spends a third of its week on these tickets and none of that work compounds.

## What you're building

`plat` — the self-service CLI that replaces the ticket queue.

```bash
plat env create --name feat-auth --template preview --ttl 48h
plat env list --mine
plat env logs feat-auth --follow
plat env destroy feat-auth
```

The provisioning behind it can be shallow — this exercise is about the *interface*, not about
building a real control plane. Back it with moto, or with a local state file. What matters is that
the thing in front is production-quality.

## Requirements

**Interface design — the actual exercise:**

- **Subcommand structure that scales.** `plat <noun> <verb>` beats a flat list of 30 commands. Pick
  a convention and hold it everywhere.
- **`--help` that is the documentation.** Every command has a one-line summary, an example, and
  described options. If someone has to read your source to use your tool, the tool is unfinished.
- **Errors that say what to do next.** Not `KeyError: 'template'` but `unknown template 'prevew'.
  Available: preview, staging, perf. Did you mean 'preview'?`
- **Config validation with pydantic**, surfacing *all* validation errors at once rather than dying
  on the first.
- **Config precedence**, the E01 rule again: flag > env var > project config > user config > default.
  `plat config show --origin` prints each effective value and where it came from. This one command
  will save you more support questions than any other feature.
- **Never a destructive default.** `plat env destroy` confirms interactively; `--yes` skips it for
  CI; there is no flag that makes destruction the default.
- **TTL and reaping.** Preview environments that never expire become permanent ones. This is E01's
  policy logic again, in a new costume — reuse the thinking.

**Distribution:**

- Packaged with uv, installable via `uv tool install`
- Pinned dependencies, a lockfile, a version command
- Semantic versioning, with a `CHANGELOG.md` — because once people depend on you, changes cost them

## Acceptance criteria

- [ ] Same done bar as E01
- [ ] A colleague (or you, six weeks later) can install it and create an environment using only
      `--help`
- [ ] `plat config show --origin` correctly attributes every value
- [ ] Every destructive command confirms, and every confirm has a `--yes` escape for automation
- [ ] Tests cover the CLI surface, not just the internals — `typer.testing.CliRunner` throughout
- [ ] `plat --version` works, and the version matches the package metadata

## Why this one matters

The August career report is direct about this: *"building internal developer platforms/abstractions
other teams consume, not just maintaining infrastructure"* is the top Senior→Staff differentiator.
This is that, in the smallest form that's still real.

It's also the strongest single portfolio artifact in the roadmap. Publish it with a README that
opens on the ticket-queue problem rather than on the feature list — the report notes that several
target companies (GitLab/HashiCorp-style cultures) explicitly value public technical writing, and a
tool plus the story of why it exists is worth more than either alone.

## Stretch

Add a plugin system so other teams extend `plat` with their own nouns without patching your repo.
Entry points via `importlib.metadata` is the standard mechanism. This is where a tool becomes a
platform, and where the interface-design decisions you made early start paying — or start hurting.
