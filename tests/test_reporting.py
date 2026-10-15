from __future__ import annotations

import json

from devex_survey.analysis import analyze_responses
from devex_survey.models import Survey
from devex_survey.reporting import render_json, render_markdown
from tests.test_analysis import EXAMPLE_RESPONSES


def test_markdown_report_contains_guardrails_and_suppression(survey: Survey) -> None:
    result = analyze_responses(
        survey,
        EXAMPLE_RESPONSES,
        segment="team",
        generated_at="2026-10-15T00:00:00+00:00",
    )

    report = render_markdown(result)

    assert "## Highest-friction items" in report
    assert "Payments (n=3)" in report
    assert "Do not use this report to rank individuals or teams." in report
    assert "Open-text content is intentionally excluded" in report


def test_json_report_is_machine_readable(survey: Survey) -> None:
    result = analyze_responses(
        survey,
        EXAMPLE_RESPONSES,
        generated_at="2026-10-15T00:00:00+00:00",
    )

    payload = json.loads(render_json(result))

    assert payload["respondents"] == 8
    assert payload["dimensions"][0]["dimension"] == "feedback_loops"
