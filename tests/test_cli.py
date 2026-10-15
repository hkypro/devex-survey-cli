from __future__ import annotations

from pathlib import Path

import pytest

from devex_survey.cli import main
from tests.test_analysis import EXAMPLE_RESPONSES


def test_init_validate_and_export(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    survey = tmp_path / "survey.yml"
    exported = tmp_path / "survey.md"

    assert main(["init", str(survey)]) == 0
    assert main(["validate", str(survey)]) == 0
    assert main(["export", str(survey), "--output", str(exported)]) == 0

    assert survey.exists()
    assert "# Developer Experience Pulse" in exported.read_text(encoding="utf-8")
    assert "Valid questionnaire: 9 scaled and 2 open question(s)" in capsys.readouterr().out


def test_init_does_not_overwrite_without_force(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    survey = tmp_path / "survey.yml"
    survey.write_text("keep me", encoding="utf-8")

    assert main(["init", str(survey)]) == 2

    assert survey.read_text(encoding="utf-8") == "keep me"
    assert "use --force" in capsys.readouterr().err


def test_analyze_writes_both_reports(
    tmp_path: Path,
    survey_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    markdown = tmp_path / "report.md"
    json_output = tmp_path / "report.json"

    result = main(
        [
            "analyze",
            str(survey_path),
            str(EXAMPLE_RESPONSES),
            "--output",
            str(markdown),
            "--json-output",
            str(json_output),
            "--segment",
            "team",
        ]
    )

    assert result == 0
    assert "## Dimension summary" in markdown.read_text(encoding="utf-8")
    assert '"respondents": 8' in json_output.read_text(encoding="utf-8")
    assert f"Wrote {markdown}" in capsys.readouterr().out
