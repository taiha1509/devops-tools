"""Entry point for `python -m deploy_gate`.

This file is three lines long and it is the most important quality-of-life
decision in the exercise. The requirement from the brief:

    python -m deploy_gate check --environment production

must work on your laptop, against the same config the Action uses. One entry
point, one code path, one set of behaviour to reason about.

This is also the whole answer to "why write pipeline logic in Python instead of
YAML": a workflow expression cannot be run locally, so every change to it is
tested by pushing a commit and waiting. Debugging a gate by pushing commits is
how the bash version stayed broken in three repositories.
"""

from __future__ import annotations

from deploy_gate.cli import app

if __name__ == "__main__":
    app()
