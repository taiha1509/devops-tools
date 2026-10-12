"""Contract for config precedence and validation.

Precedence is testable as a table because every layer is a parameter - nothing
reaches into `os.environ`. That design choice is why this file is short and
boring, which is the goal.
"""

from __future__ import annotations

from typing import Any

from plat.config import resolve, validate_config
from plat.models import EffectiveValue, Origin


def _resolve(**layers: Any) -> dict[str, EffectiveValue]:
    """Resolve with every layer defaulting to empty."""
    return resolve(
        flags=layers.get("flags", {}),
        env=layers.get("env", {}),
        project_config=layers.get("project_config", {}),
        user_config=layers.get("user_config", {}),
        defaults=layers.get("defaults", {"template": "preview", "ttl": "48h"}),
    )


class TestPrecedence:
    def test_a_flag_beats_everything(self):
        values = _resolve(
            flags={"template": "perf"},
            env={"PLAT_TEMPLATE": "staging"},
            project_config={"template": "preview"},
            user_config={"template": "preview"},
        )
        assert values["template"].value == "perf"
        assert values["template"].origin is Origin.FLAG

    def test_an_env_var_beats_both_config_files(self):
        values = _resolve(
            env={"PLAT_TEMPLATE": "staging"},
            project_config={"template": "preview"},
            user_config={"template": "perf"},
        )
        assert values["template"].origin is Origin.ENV_VAR

    def test_project_config_beats_user_config(self):
        values = _resolve(project_config={"template": "staging"}, user_config={"template": "perf"})
        assert values["template"].origin is Origin.PROJECT_CONFIG

    def test_an_unset_key_falls_through_to_the_default(self):
        values = _resolve()
        assert values["template"].value == "preview"
        assert values["template"].origin is Origin.DEFAULT


class TestFalsyFlags:
    def test_a_flag_set_to_an_empty_string_still_wins(self):
        """`--ttl ""` means "no TTL", not "use the project config".

        This is why every typer option defaults to `None` rather than its real
        default - the CLI layer has to distinguish absent from falsy before
        `resolve` ever sees it.
        """
        values = _resolve(flags={"ttl": ""}, project_config={"ttl": "48h"})
        assert values["ttl"].origin is Origin.FLAG
        assert values["ttl"].value == ""

    def test_a_flag_set_to_zero_still_wins(self):
        values = _resolve(flags={"replicas": 0}, project_config={"replicas": 3}, defaults={})
        assert values["replicas"].value == 0

    def test_a_flag_set_to_false_still_wins(self):
        values = _resolve(flags={"public": False}, project_config={"public": True}, defaults={})
        assert values["public"].value is False

    def test_an_absent_flag_does_not_win(self):
        """The other half: `None` means absent and must fall through."""
        values = _resolve(flags={"template": None}, project_config={"template": "staging"})
        assert values["template"].origin is Origin.PROJECT_CONFIG


class TestOriginReporting:
    def test_the_source_names_the_env_var(self):
        """`env_var` is an answer. `env_var (PLAT_TEMPLATE)` ends the conversation."""
        values = _resolve(env={"PLAT_TEMPLATE": "staging"})
        assert values["template"].source is not None
        assert "PLAT_TEMPLATE" in values["template"].source

    def test_the_source_names_the_config_file_path(self):
        raise AssertionError("implement: thread the file path through resolve and assert it here")


class TestValidation:
    def test_all_problems_are_returned_not_just_the_first(self):
        """A user with three things wrong learns all three in one run.

        pydantic gives you this for free via `ValidationError.errors()`; raising
        on the first failure throws it away.
        """
        values = _resolve(flags={"template": "prevew", "ttl": "banana"})
        problems = validate_config(values)
        assert len(problems) >= 2

    def test_an_unknown_template_problem_suggests_the_right_one(self):
        values = _resolve(flags={"template": "prevew"})
        problems = validate_config(values)
        assert any("preview" in p.hint for p in problems)

    def test_every_problem_has_a_non_empty_hint(self):
        """Enforced by the model, asserted here so nobody loosens it. An error
        that only says what is wrong makes the user guess the fix."""
        values = _resolve(flags={"ttl": "banana"})
        assert all(p.hint for p in validate_config(values))

    def test_a_typod_config_key_is_a_problem_not_a_silent_ignore(self):
        """`tempalte:` doing nothing at all is worse than an error, because the
        user believes they configured something."""
        values = _resolve(project_config={"tempalte": "preview"})
        problems = validate_config(values)
        assert any("tempalte" in p.key or "tempalte" in p.problem for p in problems)

    def test_a_valid_config_has_no_problems(self):
        assert validate_config(_resolve(flags={"template": "preview", "ttl": "48h"})) == []
