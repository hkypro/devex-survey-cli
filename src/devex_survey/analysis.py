from __future__ import annotations

import csv
from collections import defaultdict
from datetime import UTC, datetime
from pathlib import Path
from statistics import mean, median

from devex_survey.models import (
    AnalysisResult,
    Dimension,
    DimensionResult,
    ItemResult,
    SegmentResult,
    Survey,
)


class ResponseValidationError(ValueError):
    def __init__(self, messages: list[str]) -> None:
        self.messages = messages
        super().__init__("The response file is invalid")


def _round(value: float) -> float:
    return round(value, 2)


def _favorable_percent(values: list[int], threshold: int) -> float:
    if not values:
        return 0.0
    return _round(100 * sum(value >= threshold for value in values) / len(values))


def _dimension_results(
    survey: Survey, answers: dict[str, list[int]]
) -> tuple[DimensionResult, ...]:
    threshold = survey.scale.maximum - 1
    results: list[DimensionResult] = []
    for dimension in Dimension:
        values = [
            value
            for question in survey.questions
            if question.dimension == dimension
            for value in answers[question.question_id]
        ]
        if values:
            results.append(
                DimensionResult(
                    dimension=dimension.value,
                    responses=len(values),
                    mean=_round(mean(values)),
                    favorable_percent=_favorable_percent(values, threshold),
                )
            )
    return tuple(results)


def analyze_responses(
    survey: Survey,
    responses_path: Path,
    *,
    segment: str | None = None,
    min_group_size: int = 5,
    generated_at: str | None = None,
) -> AnalysisResult:
    if min_group_size < 5:
        raise ValueError("min_group_size must be at least 5")

    with responses_path.open(encoding="utf-8-sig", newline="") as response_file:
        reader = csv.DictReader(response_file)
        headers = reader.fieldnames or []
        rows = list(reader)

    question_ids = {question.question_id for question in survey.questions}
    open_question_ids = {question.question_id for question in survey.open_questions}
    missing_columns = sorted(question_ids - set(headers))
    errors = [f"missing required column: {column}" for column in missing_columns]
    if segment is not None and segment not in headers:
        errors.append(f"missing segment column: {segment}")
    if not rows:
        errors.append("the response file contains no data rows")

    answers_by_row: list[dict[str, int | None]] = []
    answers: dict[str, list[int]] = defaultdict(list)
    for row_number, row in enumerate(rows, start=2):
        parsed_row: dict[str, int | None] = {}
        for question in survey.questions:
            raw_value = (row.get(question.question_id) or "").strip()
            if not raw_value:
                parsed_row[question.question_id] = None
                continue
            try:
                value = int(raw_value)
            except ValueError:
                errors.append(
                    f"row {row_number}, {question.question_id}: expected an integer response"
                )
                continue
            if not survey.scale.minimum <= value <= survey.scale.maximum:
                errors.append(
                    f"row {row_number}, {question.question_id}: expected a value from "
                    f"{survey.scale.minimum} to {survey.scale.maximum}"
                )
                continue
            parsed_row[question.question_id] = value
            answers[question.question_id].append(value)
        answers_by_row.append(parsed_row)

    if errors:
        raise ResponseValidationError(errors)

    threshold = survey.scale.maximum - 1
    items: list[ItemResult] = []
    for question in survey.questions:
        values = answers[question.question_id]
        distribution = {
            score: values.count(score)
            for score in range(survey.scale.minimum, survey.scale.maximum + 1)
        }
        items.append(
            ItemResult(
                question_id=question.question_id,
                text=question.text,
                dimension=question.dimension.value,
                responses=len(values),
                missing=len(rows) - len(values),
                mean=_round(mean(values)) if values else 0.0,
                median=_round(float(median(values))) if values else 0.0,
                favorable_percent=_favorable_percent(values, threshold),
                distribution=distribution,
            )
        )

    segment_results: list[SegmentResult] = []
    suppressed_segments: dict[str, int] = {}
    if segment is not None:
        grouped_rows: dict[str, list[int]] = defaultdict(list)
        for index, row in enumerate(rows):
            segment_label = (row.get(segment) or "").strip()
            if segment_label:
                grouped_rows[segment_label].append(index)
        for segment_value in sorted(grouped_rows):
            indexes = grouped_rows[segment_value]
            if len(indexes) < min_group_size:
                suppressed_segments[segment_value] = len(indexes)
                continue
            group_answers: dict[str, list[int]] = defaultdict(list)
            for index in indexes:
                for question_id, answer_value in answers_by_row[index].items():
                    if answer_value is not None:
                        group_answers[question_id].append(answer_value)
            segment_results.append(
                SegmentResult(
                    value=segment_value,
                    respondents=len(indexes),
                    dimensions=_dimension_results(survey, group_answers),
                )
            )

    known_columns = question_ids | open_question_ids
    if segment is not None:
        known_columns.add(segment)
    ignored_columns = tuple(sorted(set(headers) - known_columns))
    open_response_counts = {
        question.question_id: sum(
            bool((row.get(question.question_id) or "").strip()) for row in rows
        )
        for question in survey.open_questions
    }
    ranked_items = [item for item in items if item.responses]
    ranked_items.sort(key=lambda item: (item.mean, item.question_id))

    return AnalysisResult(
        survey_title=survey.title,
        generated_at=generated_at or datetime.now(UTC).isoformat(timespec="seconds"),
        respondents=len(rows),
        scale_minimum=survey.scale.minimum,
        scale_maximum=survey.scale.maximum,
        dimensions=_dimension_results(survey, answers),
        items=tuple(items),
        top_frictions=tuple(ranked_items[:3]),
        open_response_counts=open_response_counts,
        ignored_columns=ignored_columns,
        segment_name=segment,
        segments=tuple(segment_results),
        suppressed_segments=suppressed_segments,
    )
