"""Contract for the CLI: safe defaults, structured output, honest exit codes."""

from __future__ import annotations

import json
import os
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

from typer.testing import CliRunner

from logjanitor.cli import app

runner = CliRunner()


def _events(output: str) -> list[dict[str, Any]]:
    """Every non-blank line of stdout must be one JSON object."""
    return [json.loads(line) for line in output.splitlines() if line.strip()]


def _summary(output: str) -> dict[str, Any]:
    print(f'output: {output}')
    found = [e for e in _events(output) if e.get("event") == "sweep.summary"]
    assert len(found) == 1, f"expected exactly one sweep.summary event, got {found}"
    return found[0]


def _aged_file(tmp_path, name: str, *, days_old: int, size: int = 10) -> Path:
    path = tmp_path / name
    path.write_text("x" * size)
    stamp = (datetime.now(tz=UTC) - timedelta(days=days_old)).timestamp()
    os.utime(path, (stamp, stamp))
    return path


def test_defaults_to_dry_run(tmp_path):
    """No --apply, no deletions. A destructive tool defaults to safe."""
    target = _aged_file(tmp_path, "old.log", days_old=30)

    result = runner.invoke(app, ["--root", str(tmp_path), "--max-age-days", "7"])

    assert result.exit_code == 0, result.output
    assert target.exists(), "a default run must not delete anything"
    assert _summary(result.output)["dry_run"] is True


def test_apply_actually_deletes(tmp_path):
    target = _aged_file(tmp_path, "old.log", days_old=30)

    result = runner.invoke(app, ["--root", str(tmp_path), "--max-age-days", "7", "--apply"])

    assert result.exit_code == 0, result.output
    assert not target.exists()
    assert _summary(result.output)["dry_run"] is False


def test_stdout_is_json_lines_only(tmp_path):
    _aged_file(tmp_path, "old.log", days_old=30)

    result = runner.invoke(app, ["--root", str(tmp_path), "--max-age-days", "7"])

    assert result.exit_code == 0, result.output
    events = _events(result.output)
    assert events, "expected structured log output on stdout"
    assert all({"ts", "level", "event"} <= set(e) for e in events)


def test_summary_reports_scanned_deleted_and_bytes(tmp_path):
    _aged_file(tmp_path, "old.log", days_old=30, size=10)
    _aged_file(tmp_path, "fresh.log", days_old=1, size=10)

    result = runner.invoke(app, ["--root", str(tmp_path), "--max-age-days", "7"])

    summary = _summary(result.output)
    assert summary["scanned"] == 2
    assert summary["deleted"] == 1
    assert summary["reclaimed_bytes"] == 10


def test_protect_option_is_repeatable(tmp_path):
    _aged_file(tmp_path, "keep-me.log", days_old=30)
    _aged_file(tmp_path, "also-keep.log", days_old=30)
    _aged_file(tmp_path, "drop.log", days_old=30)

    result = runner.invoke(
        app,
        [
            "--root",
            str(tmp_path),
            "--max-age-days",
            "7",
            "--protect",
            "keep-me.log",
            "--protect",
            "also-keep.log",
        ],
    )

    assert result.exit_code == 0, result.output
    assert _summary(result.output)["deleted"] == 1


def test_missing_root_is_exit_2(tmp_path):
    result = runner.invoke(app, ["--root", str(tmp_path / "nope"), "--max-age-days", "7"])
    assert result.exit_code == 2


def test_policy_with_no_rules_is_exit_2(tmp_path):
    """Sweeping with no retention rule is a mistake, not a no-op request.

    Exiting 0 here would let a broken CI job report success forever.
    """
    result = runner.invoke(app, ["--root", str(tmp_path)])
    assert result.exit_code == 2
