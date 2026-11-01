"""The sting table: every entry makes an effect take the recording accepts, and a wrong name says what exists."""

import pytest

from srstudio import stings, takes
from srstudio.voice import Voice, VoiceSettings


@pytest.mark.parametrize("name", sorted(stings.STINGS))
def test_every_sting_is_a_short_effect_that_sits_under_the_voices(name):
    take = stings.sting(3, name, 0.2, "wide")
    assert take.is_effect and take.id == "03" and take.shot == "wide"
    assert take.longest == take.seconds <= 3
    assert take.peak < takes.VOICE_PEAK  # under the voices


@pytest.mark.parametrize("name", sorted(stings.STINGS))
def test_no_prompt_asks_for_a_voice_or_a_bed(name):
    prompt = stings.STINGS[name].prompt
    assert prompt.endswith("no voices")
    assert "loop" not in prompt and "background" not in prompt


def test_tags_are_distinct_so_a_script_reads():
    tags = [known.tag for known in stings.STINGS.values()]
    assert len(tags) == len(set(tags))


def test_a_script_takes_a_sting_like_any_effect():
    script = takes.Script(
        title="T",
        seed=1,
        voices={"a": Voice(role="a", id="x", name="X")},
        settings={"a": VoiceSettings(stability=0.5, similarity_boost=0.75, style=0.3, speed=1.0)},
        takes=(takes.Take("01", "a", "Hello.", 0.2, shot="s"), stings.sting(2, "tada", 0.2, "s")),
        voice_note="note",
        shots=("s",),
    )
    assert script.takes[1].text == "[TADA]"


def test_an_unknown_sting_names_those_that_exist():
    with pytest.raises(stings.StingError, match="known: cabin-ding"):
        stings.sting(1, "airhorn", 0.2, "s")
