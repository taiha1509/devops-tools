# Changelog

All notable changes to `plat`. Format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/); versioning follows
[Semantic Versioning](https://semver.org/).

**Why this file is an acceptance criterion:** once other teams depend on `plat`,
a change costs them an afternoon. The CHANGELOG is where you tell them which
changes those are. A tool with no changelog gets pinned to an old version by
every careful team, and then you are maintaining five versions.

What counts as breaking here is wider than it looks. All of these are major
bumps, and all of them are easy to ship by accident:

- removing or renaming a command, subcommand, or option
- changing an **exit code**, because CI reads them
- changing the **shape of output** anyone might parse (`--json` especially)
- making a previously optional option required
- changing a default in a way that changes what happens

## [Unreleased]

### Added

- `plat env create|list|logs|destroy`
- `plat env reap` for expired environments
- `plat config show --origin`

## [0.1.0] - unreleased

Initial scaffold.
