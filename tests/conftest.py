from __future__ import annotations

from importlib.resources import files
from pathlib import Path

import pytest

from devex_survey.models import Survey
from devex_survey.questionnaire import load_survey


@pytest.fixture
def survey_path(tmp_path: Path) -> Path:
    path = tmp_path / "survey.yml"
    content = files("devex_survey").joinpath("data/default-survey.yml").read_text(encoding="utf-8")
    path.write_text(content, encoding="utf-8")
    return path


@pytest.fixture
def survey(survey_path: Path) -> Survey:
    return load_survey(survey_path)
