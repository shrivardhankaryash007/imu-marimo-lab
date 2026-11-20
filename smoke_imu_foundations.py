"""Headless smoke test for imu_foundations.py; run explicitly with pytest (not test_*-named).

It stays outside default collection until the notebook exists, so main stays green.
"""

import math
from pathlib import Path

import imu_foundations

SOURCE = Path(__file__).with_name("imu_foundations.py").read_text(encoding="utf-8")


def test_every_lesson_cell_runs_headless() -> None:
    _, defs = imu_foundations.app.run()
    missing = [f"lesson_{n:02d}" for n in range(15) if f"lesson_{n:02d}" not in defs]
    assert not missing, f"lesson views not defined headless: {missing}"


def test_answers_are_computed_not_typed() -> None:
    _, defs = imu_foundations.app.run()
    answers = defs["answers"]
    assert isinstance(answers, dict) and len(answers) >= 10
    for key, value in answers.items():
        assert isinstance(value, float) and math.isfinite(value), key


def test_physics_comes_from_the_tested_module() -> None:
    assert "import imu_basics" in SOURCE
    for forbidden in ("np.arctan2(", "np.cumsum(", "np.linalg.lstsq("):
        assert forbidden not in SOURCE, f"reimplemented physics inline: {forbidden}"
