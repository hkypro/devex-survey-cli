from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum


class Dimension(StrEnum):
    FEEDBACK_LOOPS = "feedback_loops"
    COGNITIVE_LOAD = "cognitive_load"
    FLOW_STATE = "flow_state"


DIMENSION_LABELS: dict[Dimension, str] = {
    Dimension.FEEDBACK_LOOPS: "Feedback loops",
    Dimension.COGNITIVE_LOAD: "Cognitive load",
    Dimension.FLOW_STATE: "Flow state",
}


@dataclass(frozen=True)
class Scale:
    minimum: int
    maximum: int
    labels: dict[int, str]


@dataclass(frozen=True)
class Question:
    question_id: str
    dimension: Dimension
    text: str


@dataclass(frozen=True)
class OpenQuestion:
    question_id: str
    text: str


@dataclass(frozen=True)
class Survey:
    title: str
    description: str
    scale: Scale
    questions: tuple[Question, ...]
    open_questions: tuple[OpenQuestion, ...] = ()


@dataclass(frozen=True)
class ValidationIssue:
    severity: str
    path: str
    message: str


@dataclass(frozen=True)
class ItemResult:
    question_id: str
    text: str
    dimension: str
    responses: int
    missing: int
    mean: float
    median: float
    favorable_percent: float
    distribution: dict[int, int]


@dataclass(frozen=True)
class DimensionResult:
    dimension: str
    responses: int
    mean: float
    favorable_percent: float


@dataclass(frozen=True)
class SegmentResult:
    value: str
    respondents: int
    dimensions: tuple[DimensionResult, ...]


@dataclass(frozen=True)
class AnalysisResult:
    survey_title: str
    generated_at: str
    respondents: int
    scale_minimum: int
    scale_maximum: int
    dimensions: tuple[DimensionResult, ...]
    items: tuple[ItemResult, ...]
    top_frictions: tuple[ItemResult, ...]
    open_response_counts: dict[str, int]
    ignored_columns: tuple[str, ...] = ()
    segment_name: str | None = None
    segments: tuple[SegmentResult, ...] = ()
    suppressed_segments: dict[str, int] = field(default_factory=dict)
