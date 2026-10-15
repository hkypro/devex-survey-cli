from __future__ import annotations

import argparse
import sys
from collections.abc import Sequence
from importlib.resources import files
from pathlib import Path

from devex_survey.analysis import ResponseValidationError, analyze_responses
from devex_survey.questionnaire import (
    SurveyValidationError,
    inspect_survey,
    load_survey,
    survey_as_json,
    survey_as_markdown,
)
from devex_survey.reporting import render_json, render_markdown


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="devex-survey",
        description="Design, validate, and analyze small developer experience surveys.",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    init_parser = subparsers.add_parser("init", help="Create a baseline questionnaire")
    init_parser.add_argument("path", nargs="?", type=Path, default=Path("survey.yml"))
    init_parser.add_argument("--force", action="store_true", help="Overwrite an existing file")

    validate_parser = subparsers.add_parser("validate", help="Validate a questionnaire")
    validate_parser.add_argument("survey", type=Path)

    export_parser = subparsers.add_parser("export", help="Export a questionnaire")
    export_parser.add_argument("survey", type=Path)
    export_parser.add_argument("--format", choices=("markdown", "json"), default="markdown")
    export_parser.add_argument("--output", "-o", type=Path)

    analyze_parser = subparsers.add_parser("analyze", help="Analyze CSV responses")
    analyze_parser.add_argument("survey", type=Path)
    analyze_parser.add_argument("responses", type=Path)
    analyze_parser.add_argument("--output", "-o", type=Path, default=Path("report.md"))
    analyze_parser.add_argument("--json-output", type=Path)
    analyze_parser.add_argument("--segment")
    analyze_parser.add_argument("--min-group-size", type=int, default=5)
    return parser


def _write_or_print(content: str, output: Path | None) -> None:
    if output is None:
        print(content, end="")
        return
    output.write_text(content, encoding="utf-8")
    print(f"Wrote {output}")


def _run_init(path: Path, force: bool) -> int:
    if path.exists() and not force:
        print(f"error: {path} already exists; use --force to replace it", file=sys.stderr)
        return 2
    template = files("devex_survey").joinpath("data/default-survey.yml").read_text(encoding="utf-8")
    path.write_text(template, encoding="utf-8")
    print(f"Created {path}")
    return 0


def _run_validate(path: Path) -> int:
    survey, issues = inspect_survey(path)
    for issue in issues:
        stream = sys.stderr if issue.severity == "error" else sys.stdout
        print(f"{issue.severity}: {issue.path}: {issue.message}", file=stream)
    if survey is None:
        return 2
    print(
        f"Valid questionnaire: {len(survey.questions)} scaled and "
        f"{len(survey.open_questions)} open question(s)"
    )
    return 0


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        if args.command == "init":
            return _run_init(args.path, args.force)
        if args.command == "validate":
            return _run_validate(args.survey)
        if args.command == "export":
            survey = load_survey(args.survey)
            content = (
                survey_as_markdown(survey) if args.format == "markdown" else survey_as_json(survey)
            )
            _write_or_print(content, args.output)
            return 0
        if args.command == "analyze":
            survey = load_survey(args.survey)
            result = analyze_responses(
                survey,
                args.responses,
                segment=args.segment,
                min_group_size=args.min_group_size,
            )
            _write_or_print(render_markdown(result), args.output)
            if args.json_output is not None:
                _write_or_print(render_json(result), args.json_output)
            return 0
    except (OSError, ValueError) as error:
        if isinstance(error, SurveyValidationError):
            for issue in error.issues:
                print(f"{issue.severity}: {issue.path}: {issue.message}", file=sys.stderr)
        elif isinstance(error, ResponseValidationError):
            for message in error.messages:
                print(f"error: {message}", file=sys.stderr)
        else:
            print(f"error: {error}", file=sys.stderr)
        return 2
    return 2


def entrypoint() -> None:
    raise SystemExit(main())
