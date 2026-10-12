"""Internal platform CLI - exercise E10.

`__version__` is the single source of truth for `plat --version`, and the test
suite asserts it matches the installed package metadata. Two version numbers that
can disagree will eventually disagree, and the first person to notice will be a
user reporting a bug against a version you never shipped.
"""

from __future__ import annotations

__all__ = ["__version__"]

__version__ = "0.1.0"
