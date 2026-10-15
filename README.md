# DevEx Survey CLI

Design, validate, and analyze small developer experience surveys without turning survey data into
an individual performance score.

`devex-survey` provides an original baseline questionnaire organized around three established
DevEx dimensions: **feedback loops**, **cognitive load**, and **flow state**. It produces transparent
Markdown and JSON reports from anonymous CSV exports.

## Quickstart

Install [uv](https://docs.astral.sh/uv/), then create a questionnaire:

```bash
uvx --from git+https://github.com/hkypro/devex-survey-cli@v0.1.0 \
  devex-survey init survey.yml

uvx --from git+https://github.com/hkypro/devex-survey-cli@v0.1.0 \
  devex-survey validate survey.yml

uvx --from git+https://github.com/hkypro/devex-survey-cli@v0.1.0 \
  devex-survey export survey.yml --output survey.md
```

Collect responses with the survey tool of your choice, export them as CSV, then analyze them:

```bash
uvx --from git+https://github.com/hkypro/devex-survey-cli@v0.1.0 \
  devex-survey analyze survey.yml responses.csv \
  --output report.md \
  --json-output report.json
```

The CSV must contain one column per scaled question ID. Open-question columns are optional. Unknown
columns are ignored and listed in the report.

## Commands

| Command | Purpose |
| --- | --- |
| `devex-survey init [path]` | Create the versioned baseline questionnaire |
| `devex-survey validate <survey>` | Check structure, IDs, scales, dimensions, and basic wording |
| `devex-survey export <survey>` | Render the questionnaire as Markdown or JSON |
| `devex-survey analyze <survey> <responses>` | Produce aggregate Markdown and optional JSON reports |

Use `--segment team --min-group-size 5` to add cohort-level results. Cohorts below the threshold are
suppressed. This is a guardrail against casual identification, not a privacy guarantee.

## What the analysis includes

- response and missing-value counts;
- mean, median, distribution, and favorable-response rate for each item;
- aggregate views for feedback loops, cognitive load, and flow state;
- the three answered items with the lowest mean scores;
- optional cohort breakdowns with small-group suppression;
- open-response counts, without copying sensitive free text into reports.

There is deliberately no universal “DevEx score.” Results are self-reported perceptions and should
be interpreted alongside qualitative research and workflow data. Do not use them to rank people or
teams, infer causation, or claim external benchmarks.

## Example

```bash
uv run devex-survey init /tmp/devex-survey.yml
uv run devex-survey analyze /tmp/devex-survey.yml examples/responses.csv \
  --segment team \
  --output /tmp/devex-report.md
```

The example keeps the five-response `Platform` cohort and suppresses the three-response `Payments`
cohort.

See the complete [questionnaire](examples/questionnaire.md), synthetic
[responses](examples/responses.csv), and generated [analysis report](examples/sample-report.md).

## Methodology

The included questions are original prompts informed by, but not copied from, established research:

- [DevEx: What Actually Drives Productivity](https://dl.acm.org/doi/10.1145/3595878), which
  describes feedback loops, cognitive load, and flow state;
- [The SPACE of Developer Productivity](https://www.microsoft.com/en-us/research/publication/the-space-of-developer-productivity-theres-more-to-it-than-you-think/),
  which argues against reducing developer productivity to one metric or dimension;
- [DORA survey methodology](https://dora.dev/research/2024/dora-report/), which emphasizes
  established constructs, answerability, cognitive interviews, and low respondent effort.

This project is a practical toolkit, not a statistically validated survey instrument. Pilot the
questionnaire with representative developers, review comprehension, and adapt it to the local
context before using the results to guide decisions.

## Development

```bash
uv sync --locked
uv run ruff check .
uv run ruff format --check .
uv run mypy
uv run pytest
```

Licensed under the [MIT License](LICENSE).
