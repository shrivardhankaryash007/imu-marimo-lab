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


def test_every_lesson_cell_displays_output() -> None:
    # A cell that only returns its view defines the name but renders a blank page.
    outputs, _ = imu_foundations.app.run()
    shown = sum(output is not None for output in outputs)
    assert shown >= 15, f"only {shown} cells render output; end each lesson cell with its view"


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


def test_lesson_text_has_no_swallowed_latex_escapes() -> None:
    # "$\tau$" in a plain string becomes a tab plus "au"; the page then shows "$ au$".
    import ast

    control = set("\t\x0c\x08\r\x07\x0b")
    bad = [
        node.lineno
        for node in ast.walk(ast.parse(SOURCE))
        if isinstance(node, ast.Constant)
        and isinstance(node.value, str)
        and control & set(node.value)
    ]
    assert not bad, f"string literals with control characters (unescaped LaTeX?) at lines {bad}"
