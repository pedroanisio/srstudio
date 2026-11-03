"""Did You Pack as data: arm A holds its still, nobody moves on a line, and the reel ends on the bite."""

import sys
from pathlib import Path

import pytest

EPISODES = Path(__file__).resolve().parent.parent / "episodes"


@pytest.fixture(scope="module")
def data():
    sys.path.insert(0, str(EPISODES))
    try:
        import did_you_pack_audio

        return did_you_pack_audio
    finally:
        sys.path.pop(0)


def test_arm_a_holds_a_still_and_has_no_bed(data):
    assert data.SCRIPT.still == data.STILL == 1.0
    assert data.SCRIPT.bed is None


def test_the_hook_is_her_first_line_and_the_note_ends_on_it(data):
    assert data.SCRIPT.takes[0].text == data.HOOK
    assert data.NOTE.endswith(data.HOOK.upper())


def test_the_holds_land_the_turns(data):
    takes = {take.id: take for take in data.SCRIPT.takes}
    assert takes["13"].text == "...No." and takes["13"].hold >= 1.2
    assert takes["16"].is_effect and takes["16"].hold >= 1.2


def test_the_reel_ends_on_the_bite(data):
    last = data.SCRIPT.takes[-1]
    assert last.is_effect and last.shot == "bite"


def test_every_shot_is_declared_and_used(data):
    assert {take.shot for take in data.SCRIPT.takes} == set(data.SHOTS)


def test_only_voices_the_reel_is_cleared_for(data):
    ids = {voice.id for voice in data.SCRIPT.voices.values()}
    assert ids == {"bIHbv24MWmeRgasZH58o", "pFZP5JQG7iQjIQuC4Bku", "cjVigY5qzO86Huf0OWal"}
