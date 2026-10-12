"""Config resolution with traceable precedence. E01's rule, grown up.

    flag > env var > project config > user config > default

YOUR JOB: implement `resolve`, `validate_config`, and `load_config_file`.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from collections.abc import Mapping
    from pathlib import Path

    from plat.models import EffectiveValue, ValidationProblem

ENV_PREFIX = "PLAT_"
PROJECT_CONFIG_NAME = ".plat.yaml"
USER_CONFIG_PATH = "~/.config/plat/config.yaml"

DEFAULTS: dict[str, Any] = {
    "template": "preview",
    "ttl": "48h",
    "region": "eu-west-1",
    "owner": None,  # resolved from the environment, see `resolve`
}


def load_config_file(path: Path) -> dict[str, Any]:
    """Read one YAML config file. A missing file is `{}`, not an error.

    Both config layers are optional, and the common case is neither existing.
    Raising here would make the tool unusable before it is configured, which is
    the opposite of self-service.

    Raises:
        ValueError: the file exists but is not readable YAML. That *is* an error -
            a typo'd config silently behaving as absent is how someone spends an
            afternoon wondering why their setting does nothing.
    """
    raise NotImplementedError


def resolve(
    *,
    flags: Mapping[str, Any],
    env: Mapping[str, str],
    project_config: Mapping[str, Any],
    user_config: Mapping[str, Any],
    defaults: Mapping[str, Any] | None = None,
) -> dict[str, EffectiveValue]:
    """Resolve every key, recording where each value came from.

    All five layers are parameters - nothing is read from `os.environ` or the
    filesystem in here. That is what makes precedence testable as a table instead
    of by monkeypatching the process environment.

    Details that matter:

        * **A flag explicitly set to a falsy value still wins.** `--ttl ""` or
          `--replicas 0` must not fall through to the next layer. This means the
          caller has to distinguish "flag absent" from "flag set to falsy", which
          is why typer defaults are `None` rather than the real default.
        * Env var names are `PLAT_` + the key upper-cased: `PLAT_TEMPLATE`.
        * Unknown keys in a config file are a **validation problem**, not a
          silent ignore. A typo'd `tempalte:` that does nothing is worse than an
          error.

    Returns:
        Every known key mapped to its resolved value and origin, including keys
        that fell all the way through to `DEFAULT`.
    """
    raise NotImplementedError


def validate_config(values: Mapping[str, EffectiveValue]) -> list[ValidationProblem]:
    """Validate the resolved config, returning **all** problems at once.

    Not the first one. A user with three things wrong in their config should
    learn all three in one run - pydantic gives you this for free via
    `ValidationError.errors()`, and throwing that away to raise on the first
    failure is a step backwards.

    Each problem carries a `hint`. Compare:

        KeyError: 'template'

        unknown template 'prevew'. Available: preview, staging, perf.
        Did you mean 'preview'?

    The second one is the deliverable. `difflib.get_close_matches` is in the
    standard library and does the "did you mean" part in one line.
    """
    raise NotImplementedError


__all__ = [
    "DEFAULTS",
    "ENV_PREFIX",
    "PROJECT_CONFIG_NAME",
    "USER_CONFIG_PATH",
    "load_config_file",
    "resolve",
    "validate_config",
]
