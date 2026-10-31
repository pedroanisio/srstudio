"""Some Assembly as data: arm B moves over the silent second, pages are held to read, and it ends on Noor."""

import sys
from pathlib import Path

import pytest

EPISODES = Path(__file__).resolve().parent.parent / "episodes"


@pytest.fixture(scope="module")
def data():
    sys.path.insert(0, str(EPISODES))
    try:
        import some_assembly_audio

        return some_assembly_audio
    finally:
        sys.path.pop(0)


def test_arm_b_keeps_the_recorded_silent_second_and_has_no_bed(data):
    assert data.SCRIPT.still == data.STILL == 1.0
    assert data.SCRIPT.bed is None


def test_the_script_speaks_the_approved_lines_in_order(data):
    lines = [take.text.lstrip(".") for take in data.SCRIPT.takes if not take.is_effect]
    assert lines == [
        "Step one. Two people, smiling.",
        "Easy.",
        "That's the wrong way round.",
        "You said you measured.",
        "Step nine.",
        "It's fine.",
        "It says you say that.",
        "Step twenty-three: Call your mother.",
        "That's normal, right?",
        "It says that's normal.",
        "There's one more.",
        "That's your bun.",
    ]


def test_the_pages_with_a_reveal_are_held_to_read(data):
    takes = {take.id: take for take in data.SCRIPT.takes}
    assert takes["06"].hold >= data.READ and takes["17"].hold >= data.READ
    assert takes["13"].hold >= 1.2


def test_the_reel_ends_on_a_silent_hold_past_the_last_line(data):
    last = data.SCRIPT.takes[-1]
    assert last.text.endswith("That's your bun.") and last.hold >= 2.0


def test_every_shot_is_declared_and_used(data):
    assert {take.shot for take in data.SCRIPT.takes} == set(data.SHOTS)


def test_only_voices_the_reel_is_cleared_for(data):
    assert {voice.id for voice in data.SCRIPT.voices.values()} == {"cgSgspJ2msm6clMCkdW9", "bIHbv24MWmeRgasZH58o"}
