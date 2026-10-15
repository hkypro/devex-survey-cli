from __future__ import annotations

import json
import re
from dataclasses import asdict
from pathlib import Path
from typing import Any, cast

import yaml

from devex_survey.models import (
    DIMENSION_LABELS,
    Dimension,
    OpenQuestion,
    Question,
    Scale,
    Survey,
    ValidationIssue,
)

ID_PATTERN = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
LOADED_TERMS = re.compile(r"\b(obviously|clearly|of course|don't you|shouldn't you)\b", re.I)


class SurveyValidationError(ValueError):
    def __init__(self, issues: list[ValidationIssue]) -> None:
        self.issues = issues
        super().__init__("The questionnaire is invalid")


def read_document(path: Path) -> object:
    try:
        return yaml.safe_load(path.read_text(encoding="utf-8"))
    except yaml.YAMLError as error:
        raise ValueError(f"Invalid YAML in {path}: {error}") from error


def _mapping(value: object) -> dict[str, Any] | None:
    if not isinstance(value, dict):
        return None
    return cast(dict[str, Any], value)


def _validate_question_list(
    value: object,
    *,
    path: str,
    require_dimension: bool,
    seen_ids: set[str],
) -> list[ValidationIssue]:
    issues: list[ValidationIssue] = []
    if not isinstance(value, list):
        return [ValidationIssue("error", path, "must be a list")]

    for index, raw_question in enumerate(value):
        item_path = f"{path}[{index}]"
        question = _mapping(raw_question)
        if question is None:
            issues.append(ValidationIssue("error", item_path, "must be a mapping"))
            continue

        question_id = question.get("id")
        if not isinstance(question_id, str) or not ID_PATTERN.fullmatch(question_id):
            issues.append(
                ValidationIssue(
                    "error",
                    f"{item_path}.id",
                    "must use lowercase words separated by hyphens",
                )
            )
        elif question_id in seen_ids:
            issues.append(ValidationIssue("error", f"{item_path}.id", "must be unique"))
        else:
            seen_ids.add(question_id)

        text = question.get("text")
        if not isinstance(text, str) or not text.strip():
            issues.append(ValidationIssue("error", f"{item_path}.text", "must not be empty"))
        elif len(text) > 180:
            issues.append(
                ValidationIssue("warning", f"{item_path}.text", "is longer than 180 characters")
            )
        elif LOADED_TERMS.search(text):
            issues.append(
                ValidationIssue("warning", f"{item_path}.text", "may contain leading language")
            )

        if require_dimension:
            dimension = question.get("dimension")
            valid_dimensions = {item.value for item in Dimension}
            if not isinstance(dimension, str) or dimension not in valid_dimensions:
                valid = ", ".join(item.value for item in Dimension)
                issues.append(
                    ValidationIssue("error", f"{item_path}.dimension", f"must be one of: {valid}")
                )
    return issues


def validate_document(document: object) -> list[ValidationIssue]:
    issues: list[ValidationIssue] = []
    data = _mapping(document)
    if data is None:
        return [ValidationIssue("error", "$", "must be a YAML mapping")]

    if data.get("version") != 1:
        issues.append(ValidationIssue("error", "version", "must be 1"))

    for field_name in ("title", "description"):
        value = data.get(field_name)
        if not isinstance(value, str) or not value.strip():
            issues.append(ValidationIssue("error", field_name, "must not be empty"))

    scale = _mapping(data.get("scale"))
    if scale is None:
        issues.append(ValidationIssue("error", "scale", "must be a mapping"))
    else:
        minimum = scale.get("min")
        maximum = scale.get("max")
        if not isinstance(minimum, int) or isinstance(minimum, bool):
            issues.append(ValidationIssue("error", "scale.min", "must be an integer"))
        if not isinstance(maximum, int) or isinstance(maximum, bool):
            issues.append(ValidationIssue("error", "scale.max", "must be an integer"))
        if isinstance(minimum, int) and isinstance(maximum, int) and minimum >= maximum:
            issues.append(ValidationIssue("error", "scale", "min must be lower than max"))

        labels = _mapping(scale.get("labels"))
        if labels is None:
            issues.append(ValidationIssue("error", "scale.labels", "must be a mapping"))
        elif isinstance(minimum, int) and isinstance(maximum, int) and minimum < maximum:
            invalid_keys = [key for key in labels if not str(key).isdigit()]
            normalized_keys = {int(key) for key in labels if str(key).isdigit()}
            expected_keys = set(range(minimum, maximum + 1))
            if invalid_keys or normalized_keys != expected_keys:
                issues.append(
                    ValidationIssue(
                        "error",
                        "scale.labels",
                        f"must define every value from {minimum} to {maximum}",
                    )
                )
            if any(not isinstance(label, str) or not label.strip() for label in labels.values()):
                issues.append(ValidationIssue("error", "scale.labels", "labels must not be empty"))

    seen_ids: set[str] = set()
    questions = data.get("questions")
    issues.extend(
        _validate_question_list(
            questions, path="questions", require_dimension=True, seen_ids=seen_ids
        )
    )
    if isinstance(questions, list) and not questions:
        issues.append(ValidationIssue("error", "questions", "must contain at least one item"))

    open_questions = data.get("open_questions", [])
    issues.extend(
        _validate_question_list(
            open_questions,
            path="open_questions",
            require_dimension=False,
            seen_ids=seen_ids,
        )
    )

    if isinstance(questions, list):
        present_dimensions = {
            item.get("dimension")
            for raw_item in questions
            if (item := _mapping(raw_item)) is not None
        }
        for dimension in Dimension:
            if dimension.value not in present_dimensions:
                issues.append(
                    ValidationIssue(
                        "warning",
                        "questions",
                        f"contains no item for {DIMENSION_LABELS[dimension]}",
                    )
                )
    return issues


def _parse_survey(document: object) -> Survey:
    data = cast(dict[str, Any], document)
    raw_scale = cast(dict[str, Any], data["scale"])
    raw_labels = cast(dict[object, str], raw_scale["labels"])
    scale = Scale(
        minimum=cast(int, raw_scale["min"]),
        maximum=cast(int, raw_scale["max"]),
        labels={int(cast(str | int, key)): value for key, value in raw_labels.items()},
    )
    questions = tuple(
        Question(
            question_id=cast(str, item["id"]),
            dimension=Dimension(cast(str, item["dimension"])),
            text=cast(str, item["text"]).strip(),
        )
        for item in cast(list[dict[str, Any]], data["questions"])
    )
    open_questions = tuple(
        OpenQuestion(
            question_id=cast(str, item["id"]),
            text=cast(str, item["text"]).strip(),
        )
        for item in cast(list[dict[str, Any]], data.get("open_questions", []))
    )
    return Survey(
        title=cast(str, data["title"]).strip(),
        description=cast(str, data["description"]).strip(),
        scale=scale,
        questions=questions,
        open_questions=open_questions,
    )


def inspect_survey(path: Path) -> tuple[Survey | None, list[ValidationIssue]]:
    document = read_document(path)
    issues = validate_document(document)
    if any(issue.severity == "error" for issue in issues):
        return None, issues
    return _parse_survey(document), issues


def load_survey(path: Path) -> Survey:
    survey, issues = inspect_survey(path)
    if survey is None:
        raise SurveyValidationError(issues)
    return survey


def survey_as_json(survey: Survey) -> str:
    return json.dumps(asdict(survey), indent=2, ensure_ascii=False) + "\n"


def survey_as_markdown(survey: Survey) -> str:
    lines = [f"# {survey.title}", "", survey.description, "", "## Response scale", ""]
    lines.extend(f"- **{value}:** {survey.scale.labels[value]}" for value in survey.scale.labels)

    number = 1
    for dimension in Dimension:
        dimension_questions = [q for q in survey.questions if q.dimension == dimension]
        if not dimension_questions:
            continue
        lines.extend(["", f"## {DIMENSION_LABELS[dimension]}", ""])
        for question in dimension_questions:
            lines.append(f"{number}. {question.text} `[{question.question_id}]`")
            number += 1

    if survey.open_questions:
        lines.extend(["", "## Open questions", ""])
        lines.extend(
            f"{index}. {question.text} `[{question.question_id}]`"
            for index, question in enumerate(survey.open_questions, start=number)
        )
    return "\n".join(lines) + "\n"
