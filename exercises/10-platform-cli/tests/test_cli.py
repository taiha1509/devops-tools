"""Contract for the CLI surface itself - the thing this exercise is actually about.

`CliRunner` throughout. Testing only the library functions would miss every
decision that makes a platform tool usable: the confirmation prompt, the help
text, the exit codes, the error messages.
"""

from __future__ import annotations

from importlib.metadata import version

import pytest

from plat import __version__
from plat.cli import app


class TestVersion:
    def test_version_flag_works(self, runner):
        result = runner.invoke(app, ["--version"])
        assert result.exit_code == 0
        assert __version__ in result.stdout

    def test_the_version_matches_the_package_metadata(self):
        """Two version numbers that can disagree eventually will, and the first
        person to notice will report a bug against a version you never shipped."""
        assert version("plat") == __version__

    def test_version_works_even_with_a_broken_config(self, runner, tmp_path):
        """`--version` is the first thing anyone puts in a bug report. Needing a
        valid config to get it is a bad day for both of you.

        This is what `is_eager=True` on the callback buys.
        """
        broken = tmp_path / ".plat.yaml"
        broken.write_text("{{{ not yaml")
        result = runner.invoke(app, ["--version"], env={"PLAT_CONFIG": str(broken)})
        assert result.exit_code == 0


class TestHelpIsDocumentation:
    def test_bare_invocation_shows_help_rather_than_an_error(self, runner):
        """`no_args_is_help=True`. A user who types `plat` is exploring, not
        failing."""
        result = runner.invoke(app, [])
        assert "env" in result.stdout

    def test_the_noun_verb_structure_is_discoverable(self, runner):
        """A user who knows one noun should be able to guess the rest."""
        result = runner.invoke(app, ["env", "--help"])
        for verb in ("create", "list", "logs", "destroy"):
            assert verb in result.stdout

    @pytest.mark.parametrize("command", [["env", "create"], ["env", "destroy"], ["config", "show"]])
    def test_every_command_help_contains_an_example(self, runner, command):
        """The acceptance criterion: a colleague can use this with only `--help`.

        An options table is not an example. Someone reading `--ttl TEXT` does not
        learn that `48h` is the format.
        """
        result = runner.invoke(app, [*command, "--help"])
        assert "plat " in result.stdout.replace("Usage:", "")


class TestDestructiveDefaults:
    def test_destroy_without_yes_prompts(self, runner, backend):
        """There is no flag that makes destruction the default."""
        result = runner.invoke(app, ["env", "destroy", "feat-auth"], input="\n")
        assert result.exit_code != 0

    def test_destroy_with_yes_does_not_prompt(self, runner, backend):
        """The CI escape hatch. Every confirm needs one or automation routes
        around the tool entirely."""
        raise AssertionError("implement: create an env, destroy --yes, assert exit 0")

    def test_the_confirmation_requires_the_name_typed_back(self, runner):
        """A y/n is muscle memory within a week. Typing `feat-auth` is not."""
        raise AssertionError("implement: assert a bare 'y' does not destroy")

    def test_a_non_tty_invocation_without_yes_refuses_rather_than_hanging(self, runner):
        """`plat env destroy x </dev/null` must not block forever on stdin.

        This is how a tool wedges a CI job for six hours until the runner times
        out, and the log says nothing.
        """
        raise AssertionError("implement: decide the non-TTY behaviour and pin it")

    def test_reap_defaults_to_dry_run(self, runner):
        raise AssertionError("implement: create expired envs, run reap, assert nothing destroyed")


class TestErrorMessages:
    def test_an_unknown_template_lists_the_valid_ones(self, runner):
        result = runner.invoke(app, ["env", "create", "--name", "x", "--template", "prevew"])
        assert result.exit_code == 2
        assert "preview" in result.stdout

    def test_an_unknown_template_suggests_the_closest_match(self, runner):
        """The brief's worked example, asserted.

        unknown template 'prevew'. Available: preview, staging, perf.
        Did you mean 'preview'?
        """
        result = runner.invoke(app, ["env", "create", "--name", "x", "--template", "prevew"])
        assert "did you mean" in result.stdout.lower()

    def test_no_user_facing_error_is_a_traceback(self, runner):
        """A traceback tells the user they found a defect, which is only true if
        they did. Every `PlatError` is caught and printed as a message."""
        result = runner.invoke(app, ["env", "destroy", "does-not-exist", "--yes"])
        assert "Traceback" not in result.stdout
        assert result.exit_code == 2

    def test_a_duplicate_name_does_not_silently_overwrite(self, runner):
        """Reusing a name silently is how a colleague's environment disappears."""
        raise AssertionError("implement: create twice, assert the second fails with exit 2")


class TestConfigShow:
    def test_origin_attributes_every_value(self, runner, monkeypatch):
        """The acceptance criterion. Every effective value, with its source."""
        monkeypatch.setenv("PLAT_REGION", "us-east-1")
        result = runner.invoke(app, ["config", "show", "--origin"])
        assert "us-east-1" in result.stdout
        assert "env_var" in result.stdout

    def test_show_without_origin_is_just_the_values(self, runner):
        result = runner.invoke(app, ["config", "show"])
        assert result.exit_code == 0
