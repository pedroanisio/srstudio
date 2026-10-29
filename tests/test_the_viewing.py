"""The Viewing (Stick 05) as data: the script checks, three distinct voices, a performance for every take, the bed
coming down once before Gary is seen, and Gary answering last."""

import sys
from pathlib import Path

import pytest

EPISODES = Path(__file__).resolve().parent.parent / "episodes"


@pytest.fixture(scope="module")
def data():
    sys.path.insert(0, str(EPISODES))
    try:
        import the_viewing_audio

        return the_viewing_audio
    finally:
        sys.path.pop(0)


def test_the_script_checks_and_opens_on_a_question_with_three_distinct_voices(data):
    script = data.SCRIPT
    script.check()
    assert script.takes[0].text.endswith("?")
    assert len({v.id for v in script.voices.values()}) == 3
    assert "steady kick on every beat" in script.bed.plan.chunks[0].styles


def test_the_bed_comes_down_before_gary_is_seen_and_he_answers_last(data):
    ids = [take.id for take in data.SCRIPT.takes]
    drop, _ = data.DROP
    gary = [take.id for take in data.SCRIPT.takes if "Gary" in take.text]
    assert ids.index(drop) < ids.index(gary[0])
    assert data.GARY_TALKS == ids[-1] and data.SCRIPT.takes[-1].actor == "gary"


def test_every_take_has_a_performance_for_both_figures(data):
    dev_part, agent_part = (EPISODES / "the_viewing.py").read_text().split("AGENT_PART", 1)
    for take in data.SCRIPT.takes:
        assert f'"{take.id}": [(0,' in dev_part
        assert f'"{take.id}": [(0,' in agent_part
