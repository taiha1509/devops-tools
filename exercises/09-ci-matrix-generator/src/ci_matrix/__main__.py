"""Entry point for `python -m ci_matrix`.

The workflow in the brief calls it this way:

    run: python -m ci_matrix plan --base ${{ github.event.pull_request.base.sha }}

Same reasoning as E07: one entry point that runs identically on a laptop. You
will be debugging "why did it skip my service" accusations for months, and doing
that by pushing commits is unbearable.
"""

from __future__ import annotations

from ci_matrix.cli import app

if __name__ == "__main__":
    app()
