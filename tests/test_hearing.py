"""A word speech-to-text cannot tell from its twin, caught before a line costs a paid take."""

from dataclasses import replace

import pytest

from srstudio import hearing, sketch
from srstudio.sketch import Line
from support.sketch import LINES, SK, FakeClient, confirm_stub


@pytest.mark.parametrize(("text", "twin"), [("Son.", "sun"), ("Mae?", "may"), ("nell!", "no"), ("  Neil...", "kneel")])
def test_a_bare_word_with_a_twin_is_found(text, twin):
    assert hearing.twin(text) == twin


@pytest.mark.parametrize("text", ["My son.", "Mae, wait.", "Fine.", "", "..."])
def test_context_or_an_unambiguous_word_is_safe(text):
    assert hearing.twin(text) is None


def test_every_blind_line_is_named_with_its_number():
    lines = (Line("a", "Son."), Line("b", "My son."), Line("a", "Mae."))
    assert hearing.blind_lines(lines) == [
        'line 01 (a): "Son." alone may be heard as "sun"',
        'line 03 (a): "Mae." alone may be heard as "may"',
    ]


def test_a_hearing_already_accepted_is_not_blind():
    assert hearing.blind_lines((Line("a", "Son.", heard=("Sun.",)),)) == []


def test_record_refuses_a_blind_line_before_it_pays_for_a_take(tmp_path):
    client = FakeClient(tmp_path)
    blind = replace(LINES[1], text="Son.")
    with pytest.raises(sketch.SketchError, match=r'line 02 \(boss\): "Son\."') as caught:
        sketch.record(replace(SK, lines=(LINES[0], blind, LINES[2])), tmp_path, client, confirm=confirm_stub)
    assert "heard=" in str(caught.value)
    assert client.requests == []


def test_the_table_is_lowercase_single_words():
    assert all(word == word.lower() and word.isalpha() for word in hearing.TWINS)
