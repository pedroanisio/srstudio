"""In Two Hundred as data: the three voices, the held beat in the field, what the phone says at each of its lines."""

import sys
from pathlib import Path

import pytest

from srstudio import stick, stick_satnav, stick_windshield

EPISODES = Path(__file__).resolve().parent.parent / "episodes"


@pytest.fixture(scope="module")
def data():
    sys.path.insert(0, str(EPISODES))
    try:
        import in_two_hundred_audio

        return in_two_hundred_audio
    finally:
        sys.path.pop(0)


def by_id(data):
    return {t.id: t for t in data.SCRIPT.takes}


def test_the_voices_are_the_briefs_and_there_is_no_bed(data):
    assert {v.name for v in data.SCRIPT.voices.values()} == {"Will", "Jessica", "Alice"}
    assert data.SCRIPT.seed == 3308 and data.SCRIPT.bed is None
    assert data.HOOK == "LATE FOR THE WEDDING"


def test_the_lines_run_as_the_script_has_them(data):
    lines = [t.text for t in data.SCRIPT.takes]
    assert lines[0] == "It's left." and lines[-1] == "Your destination is the couch."
    assert lines.count("Continue straight.") == 2
    assert "In two hundred feet, apologize." in lines and "At the fence, tell her she was right." in lines


def test_noor_says_nothing_in_the_field(data):
    takes = by_id(data)
    assert takes["06"].hold >= data.GRAVEL + data.GRASS + data.STOPPING + 2.0
    assert [t.actor for t in data.SCRIPT.takes[6:]].count("noor") == 0


def test_each_screen_it_names_exists(data):
    assert set(data.SCREENS.values()) <= set(stick_satnav.SCREENS)
    takes = by_id(data)
    assert all(takes[i].actor == "map" for i in data.SCREENS)


def test_the_map_keeps_one_voice_and_the_last_line(data):
    assert data.SCRIPT.takes[-1].actor == "map"
    assert {t.actor for t in data.SCRIPT.takes} == {"dev", "noor", "map"}


def test_the_couple_keep_their_published_rig_and_his_tie_is_clothes(data):
    assert data.NOOR_LOOK == stick_windshield.NOOR
    assert data.DEV_LOOK == stick.Look(tie="#c0453b")


def test_the_code_sits_on_the_dash_clear_of_the_captions(data):
    x, y, height, _ = data.CAR_MARKS["code"]
    assert y + height < 1424  # above the wipers
    assert data.CAR_MARKS["cactus"] > stick_windshield.DASH_CACTUS
    assert 0 < x < 926
