from __future__ import annotations

import json
from dataclasses import asdict

from devex_survey.models import DIMENSION_LABELS, AnalysisResult, Dimension


def _dimension_label(value: str) -> str:
    return DIMENSION_LABELS[Dimension(value)]


def render_json(result: AnalysisResult) -> str:
    return json.dumps(asdict(result), indent=2, ensure_ascii=False) + "\n"


def render_markdown(result: AnalysisResult) -> str:
    lines = [
        f"# {result.survey_title} — analysis",
        "",
        f"- Generated: `{result.generated_at}`",
        f"- Responses: **{result.respondents}**",
        f"- Scale: **{result.scale_minimum}-{result.scale_maximum}**",
        "",
        "## Dimension summary",
        "",
        "| Dimension | Responses | Mean | Favorable |",
        "| --- | ---: | ---: | ---: |",
    ]
    lines.extend(
        f"| {_dimension_label(item.dimension)} | {item.responses} | {item.mean:.2f} | "
        f"{item.favorable_percent:.2f}% |"
        for item in result.dimensions
    )

    lines.extend(
        [
            "",
            "## Highest-friction items",
            "",
            "These are the answered items with the lowest mean scores.",
            "",
            "| Item | Dimension | Mean | Favorable |",
            "| --- | --- | ---: | ---: |",
        ]
    )
    lines.extend(
        f"| {item.text} | {_dimension_label(item.dimension)} | {item.mean:.2f} | "
        f"{item.favorable_percent:.2f}% |"
        for item in result.top_frictions
    )

    lines.extend(
        [
            "",
            "## Item detail",
            "",
            "| ID | Dimension | Responses | Missing | Mean | Median | Favorable |",
            "| --- | --- | ---: | ---: | ---: | ---: | ---: |",
        ]
    )
    lines.extend(
        f"| `{item.question_id}` | {_dimension_label(item.dimension)} | {item.responses} | "
        f"{item.missing} | {item.mean:.2f} | {item.median:.2f} | "
        f"{item.favorable_percent:.2f}% |"
        for item in result.items
    )

    if result.segment_name is not None:
        lines.extend(["", f"## Segments: `{result.segment_name}`", ""])
        for segment in result.segments:
            lines.extend(
                [
                    f"### {segment.value} (n={segment.respondents})",
                    "",
                    "| Dimension | Mean | Favorable |",
                    "| --- | ---: | ---: |",
                ]
            )
            lines.extend(
                f"| {_dimension_label(item.dimension)} | {item.mean:.2f} | "
                f"{item.favorable_percent:.2f}% |"
                for item in segment.dimensions
            )
            lines.append("")
        if result.suppressed_segments:
            suppressed = ", ".join(
                f"{name} (n={count})" for name, count in result.suppressed_segments.items()
            )
            lines.append(f"Suppressed because the cohort was too small: {suppressed}.")

    if result.open_response_counts:
        lines.extend(["", "## Open-response coverage", ""])
        lines.extend(
            f"- `{question_id}`: {count} response(s)"
            for question_id, count in result.open_response_counts.items()
        )
        lines.append("")
        lines.append("Open-text content is intentionally excluded from generated reports.")

    if result.ignored_columns:
        lines.extend(
            [
                "",
                "## Ignored columns",
                "",
                ", ".join(f"`{column}`" for column in result.ignored_columns),
            ]
        )

    lines.extend(
        [
            "",
            "## Interpretation guardrails",
            "",
            "- These results describe self-reported perceptions; they do not establish causation.",
            "- Do not use this report to rank individuals or teams.",
            "- Compare trends within the same context instead of treating scores as "
            "universal benchmarks.",
            "- Review qualitative responses manually and apply appropriate privacy safeguards.",
        ]
    )
    return "\n".join(lines) + "\n"
