"""Contract for combining verdicts, the override, and the annotation output.

The override is the part most people either skip or get wrong. A gate with no
override is a gate people route around - they will find the `if: false` or deploy
from a laptop, and you will have learned nothing about why. An override with no
audit trail is a gate that does not exist.
"""

from __future__ import annotations

import io

import pytest

from deploy_gate.annotations import emit_annotation, render_decision, write_outputs
from deploy_gate.gate import Override, audit_override, decide
from deploy_gate.models import GateName, GateResult
from helpers import at


def _allow(gate: GateName) -> GateResult:
    return GateResult(gate=gate, allowed=True, reason="ok")


def _block(gate: GateName, reason: str = "nope") -> GateResult:
    return GateResult(gate=gate, allowed=False, reason=reason)


class TestCombining:
    def test_all_gates_allowing_allows(self):
        decision = decide([_allow(GateName.FREEZE), _allow(GateName.ERROR_BUDGET)])
        assert decision.allowed is True

    def test_one_gate_blocking_blocks(self):
        decision = decide([_allow(GateName.FREEZE), _block(GateName.ERROR_BUDGET)])
        assert decision.allowed is False

    def test_no_gates_configured_allows(self):
        """Adopting this Action in a repo with no incident API must be possible.

        The CLI is responsible for *saying* which gates did not run - a silent
        omission eventually has someone believing they are protected by a gate
        they never configured.
        """
        assert decide([]).allowed is True

    def test_every_blocking_gate_is_reported_not_just_the_first(self):
        """No short-circuiting.

        An engineer who learns they are in a change freeze, fixes that, re-runs,
        and *then* learns a Sev1 is open has been through the loop twice for no
        reason.
        """
        decision = decide(
            [
                _block(GateName.FREEZE, "frozen until 23:59"),
                _block(GateName.OPEN_INCIDENT, "INC-42 open"),
            ]
        )
        assert len(decision.blocking) == 2
        assert "frozen until 23:59" in decision.reason
        assert "INC-42 open" in decision.reason


class TestOverride:
    def test_override_allows_a_blocked_deploy(self):
        override = Override(actor="hant", reason="hotfix for INC-42")
        decision = decide([_block(GateName.FREEZE)], override=override)
        assert decision.allowed is True
        assert decision.overridden is True

    def test_override_preserves_the_underlying_verdicts(self):
        """The record must show both that the gates said no **and** that someone
        decided to proceed. Reporting a clean pass would make the override
        invisible, which is the same as not having one."""
        override = Override(actor="hant", reason="hotfix for INC-42")
        decision = decide([_block(GateName.FREEZE, "frozen")], override=override)
        assert len(decision.blocking) == 1
        assert decision.override_actor == "hant"
        assert decision.override_reason == "hotfix for INC-42"

    def test_an_override_with_an_empty_reason_is_rejected(self):
        """ "Because I need to" is a reason. An empty string is not, and defaulting
        it to something is how the audit trail becomes worthless."""
        with pytest.raises(ValueError, match="reason"):
            Override(actor="hant", reason="")

    def test_overriding_when_nothing_was_blocking_is_not_an_error(self):
        """But it should be visible - someone has the label on by habit, which is
        worth knowing. Decide whether that is a notice or a warning."""
        override = Override(actor="hant", reason="belt and braces")
        decision = decide([_allow(GateName.FREEZE)], override=override)
        assert decision.allowed is True

    def test_the_audit_record_names_the_actor_the_reason_and_the_gates(self):
        """The acceptance criterion, asserted."""
        override = Override(actor="hant", reason="hotfix for INC-42")
        record = audit_override(
            override,
            blocked_by=[_block(GateName.FREEZE, "frozen")],
            environment="production",
            now=at(2026, 9, 25, 16),
        )
        assert record["actor"] == "hant"
        assert record["reason"] == "hotfix for INC-42"
        assert record["environment"] == "production"
        assert GateName.FREEZE in record["overridden_gates"]  # type: ignore[operator]


class TestAnnotations:
    def test_an_error_annotation_has_the_workflow_command_shape(self):
        stream = io.StringIO()
        emit_annotation("error", "Deploy blocked", stream=stream, title="Deploy Gate")
        assert stream.getvalue().startswith("::error ")
        assert "Deploy blocked" in stream.getvalue()

    def test_a_multiline_message_is_escaped(self):
        """A literal newline ends the workflow command and the rest becomes
        ordinary log output - which is exactly where the reason must not end up."""
        stream = io.StringIO()
        emit_annotation("error", "line one\nline two", stream=stream)
        value = stream.getvalue()
        assert "%0A" in value
        assert value.count("\n") == 1  # only the trailing newline

    def test_outputs_are_written_as_key_value_lines(self, tmp_path):
        out = tmp_path / "github_output"
        out.touch()
        write_outputs({"allowed": "false", "reason": "frozen"}, github_output=out)
        assert "allowed=false" in out.read_text()

    def test_a_multiline_output_value_uses_the_heredoc_form(self, tmp_path):
        """`reason` is exactly the kind of value that grows a newline six months
        from now, and `key=value` silently truncates at the first one."""
        out = tmp_path / "github_output"
        out.touch()
        write_outputs({"reason": "frozen\nand INC-42 open"}, github_output=out)
        assert "<<" in out.read_text()

    def test_no_github_output_is_a_noop_not_an_error(self):
        """Running locally. "The same entrypoint runs locally" dies here if you raise."""
        write_outputs({"allowed": "true"}, github_output=None)

    def test_render_leads_with_the_decision(self):
        decision = decide([_block(GateName.FREEZE, "frozen until 23:59 UTC")])
        assert "frozen until 23:59 UTC" in render_decision(decision)
