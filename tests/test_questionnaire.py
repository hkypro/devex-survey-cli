from __future__ import annotations

from pathlib import Path

from devex_survey.models import Dimension
from devex_survey.questionnaire import (
    inspect_survey,
    load_survey,
    survey_as_json,
    survey_as_markdown,
)


def test_default_questionnaire_is_balanced(survey_path: Path) -> None:
    survey = load_survey(survey_path)

    assert len(survey.questions) == 9
    assert len(survey.open_questions) == 2
    assert {
        dimension: sum(question.dimension == dimension for question in survey.questions)
        for dimension in Dimension
    } == {dimension: 3 for dimension in Dimension}


def test_exports_questionnaire(survey_path: Path) -> None:
    survey = load_survey(survey_path)

    markdown = survey_as_markdown(survey)
    json_output = survey_as_json(survey)

    assert "## Feedback loops" in markdown
    assert "`[local-feedback-speed]`" in markdown
    assert '"question_id": "local-feedback-speed"' in json_output


def test_validation_rejects_duplicate_ids(tmp_path: Path) -> None:
    path = tmp_path / "invalid.yml"
    path.write_text(
        """\
version: 1
title: Test
description: Test survey
scale:
  min: 1
  max: 2
  labels: {1: "No", 2: "Yes"}
questions:
  - {id: repeated, dimension: feedback_loops, text: First}
  - {id: repeated, dimension: flow_state, text: Second}
""",
        encoding="utf-8",
    )

    survey, issues = inspect_survey(path)

    assert survey is None
    assert any(issue.path == "questions[1].id" for issue in issues)


def test_validation_warns_about_leading_language(tmp_path: Path) -> None:
    path = tmp_path / "warning.yml"
    path.write_text(
        """\
version: 1
title: Test
description: Test survey
scale:
  min: 1
  max: 2
  labels: {1: "No", 2: "Yes"}
questions:
  - id: loaded-question
    dimension: feedback_loops
    text: Clearly the build should be faster.
""",
        encoding="utf-8",
    )

    survey, issues = inspect_survey(path)

    assert survey is not None
    assert any("leading language" in issue.message for issue in issues)
    assert sum(issue.severity == "warning" for issue in issues) == 3


def test_validation_rejects_unknown_dimension(tmp_path: Path) -> None:
    path = tmp_path / "unknown-dimension.yml"
    path.write_text(
        """\
version: 1
title: Test
description: Test survey
scale:
  min: 1
  max: 2
  labels: {1: "No", 2: "Yes"}
questions:
  - id: invalid-dimension
    dimension: velocity
    text: Feedback arrives quickly.
""",
        encoding="utf-8",
    )

    survey, issues = inspect_survey(path)

    assert survey is None
    assert any(issue.path == "questions[0].dimension" for issue in issues)


def test_validation_rejects_extra_scale_label(tmp_path: Path) -> None:
    path = tmp_path / "extra-label.yml"
    path.write_text(
        """\
version: 1
title: Test
description: Test survey
scale:
  min: 1
  max: 2
  labels: {1: "No", 2: "Yes", other: "Unknown"}
questions:
  - id: valid-question
    dimension: flow_state
    text: I have time to focus.
""",
        encoding="utf-8",
    )

    survey, issues = inspect_survey(path)

    assert survey is None
    assert any(issue.path == "scale.labels" for issue in issues)
