"""A build's record of which nodes are a character, ``figures.json``."""

from __future__ import annotations

import json

import pytest

from srstudio import figure_record as R
from srstudio.figure_record import Figure, FigureRecordError


def test_a_record_reads_back_what_was_written(tmp_path):
    figures = [Figure("toon-fox@2", ("k1", "k2")), Figure("barista", ("rect-0001",))]
    R.write(tmp_path, figures)
    assert R.read(tmp_path) == figures


def test_a_project_built_before_records_has_none(tmp_path):
    assert R.read(tmp_path) is None


@pytest.mark.parametrize(
    "text",
    [
        "not json",
        "[]",
        json.dumps({"schema": R.SCHEMA}),
        json.dumps({"schema": R.SCHEMA, "figures": [{"part": "fox"}]}),
        json.dumps({"schema": "0.9.0", "figures": []}),
    ],
)
def test_a_record_that_is_not_one_is_refused(tmp_path, text):
    (tmp_path / R.RECORD).write_text(text, encoding="utf-8")
    with pytest.raises(FigureRecordError, match=R.RECORD):
        R.read(tmp_path)
