"""The narration script of Work Training Be Like: what it asks the narrator to say (the shared fitting steps are
tested in test_narration.py)."""

import sys
from pathlib import Path

import pytest

from srstudio import narration as library

EPISODES = Path(__file__).resolve().parent.parent / "episodes"


@pytest.fixture(scope="module")
def script():
    sys.path.insert(0, str(EPISODES))
    try:
        import mushroom_training_audio
    finally:
        sys.path.pop(0)
    return mushroom_training_audio


def test_the_script_uses_the_library_steps_not_a_copy(script):
    for name in ("slots", "plan_relaxed", "conform", "confirm_voice", "require_consent"):
        assert getattr(script, name) is getattr(library, name), name


def test_a_respelling_keeps_the_caption_words_it_can_confirm(script):
    for caption, said in script.SPOKEN.items():
        if caption.endswith("..."):  # a lone fragment becomes the start of a sentence
            assert said.startswith(caption[:-3]) and said.endswith("."), caption
        else:  # a spelt-out number is written as the recogniser writes it back
            assert said.replace("100%", "one hundred percent") == caption
    assert script.SETTINGS.speed == 1.0  # the narrator's natural pace; nothing is quickened (user: it sounded rushed)


def test_the_typing_bed_sits_under_the_voice(script):
    assert script.TYPING_GAIN_DB <= -6 and 0 < script.TYPING_PEAK <= script.VOICE_PEAK
