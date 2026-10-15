from __future__ import annotations

import csv
from pathlib import Path

import pytest

from devex_survey.analysis import ResponseValidationError, analyze_responses
from devex_survey.models import Survey

EXAMPLE_RESPONSES = Path(__file__).parents[1] / "examples/responses.csv"


def test_analyzes_aggregate_responses(survey: Survey) -> None:
    result = analyze_responses(
        survey,
        EXAMPLE_RESPONSES,
        generated_at="2026-10-15T00:00:00+00:00",
    )

    assert result.respondents == 8
    assert len(result.dimensions) == 3
    assert len(result.items) == 9
    assert len(result.top_frictions) == 3
    assert result.open_response_counts == {
        "biggest-friction": 7,
        "highest-impact-improvement": 7,
    }
    assert result.ignored_columns == ("team",)


def test_suppresses_small_segments(survey: Survey) -> None:
    result = analyze_responses(
        survey,
        EXAMPLE_RESPONSES,
        segment="team",
        min_group_size=5,
        generated_at="2026-10-15T00:00:00+00:00",
    )

    assert [segment.value for segment in result.segments] == ["Platform"]
    assert result.segments[0].respondents == 5
    assert result.suppressed_segments == {"Payments": 3}
    assert result.ignored_columns == ()


def test_rejects_response_outside_scale(tmp_path: Path, survey: Survey) -> None:
    path = tmp_path / "invalid.csv"
    headers = [question.question_id for question in survey.questions]
    with path.open("w", encoding="utf-8", newline="") as response_file:
        writer = csv.DictWriter(response_file, fieldnames=headers)
        writer.writeheader()
        writer.writerow({question_id: 3 for question_id in headers} | {headers[0]: 9})

    with pytest.raises(ResponseValidationError, match="response file is invalid") as error:
        analyze_responses(survey, path)

    assert "expected a value from 1 to 5" in error.value.messages[0]


def test_requires_all_scaled_question_columns(tmp_path: Path, survey: Survey) -> None:
    path = tmp_path / "missing.csv"
    path.write_text("local-feedback-speed\n4\n", encoding="utf-8")

    with pytest.raises(ResponseValidationError) as error:
        analyze_responses(survey, path)

    assert len(error.value.messages) == 8


def test_enforces_minimum_cohort_size(survey: Survey) -> None:
    with pytest.raises(ValueError, match="at least 5"):
        analyze_responses(survey, EXAMPLE_RESPONSES, segment="team", min_group_size=4)
