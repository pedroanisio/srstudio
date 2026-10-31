"""The wording checks: figures in a spoken line."""

from __future__ import annotations

import pytest

from srstudio import wording


@pytest.mark.parametrize(
    "text, found",
    [
        ("It's 2:00 AM.", ["2:00 AM."]),
        ("since 1987", ["1987"]),
        ("At 1 a.m. sharp", ["1 a.m."]),
        ("about 3 pounds", ["3"]),
        ("by a.m. tomorrow", ["a.m."]),
    ],
)
def test_figures_in_a_spoken_line_are_found(text, found):
    assert wording.figures(text) == found


def test_spelled_numbers_pass():
    assert wording.figures("Two in the morning. Two-oh-one, in nineteen eighty-seven.") == []


def test_the_command_reports_file_and_line_and_fails(tmp_path, capsys):
    script = tmp_path / "script.txt"
    script.write_text("fine\nAt 2:00 AM\n", encoding="utf-8")
    assert wording.main([str(script)]) == 0
    assert wording.main(["--spoken", str(script)]) == 1
    assert capsys.readouterr().out == f"{script}:2: 2:00 AM: spell it out\n"
