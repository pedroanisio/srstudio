"""The silent clock: the shape of a recording and none of its cost, and never in a recording's place."""

import json

import pytest

from srstudio import silent, takes
from srstudio.direction import Direction
from srstudio.voice import Voice, VoiceSettings
from support.takes import script


def test_a_silent_timeline_has_the_recording_s_shape_and_says_what_it_is(tmp_path):
    made = silent.record(script(), tmp_path)
    assert made[silent.MARK] is True
    assert made["tts_engine"] == "none"
    assert json.loads((tmp_path / "timeline.json").read_text())[silent.MARK] is True
    spoken = [item for item in made["items"] if item["speech_duration"]]
    assert spoken
    for item in spoken:
        assert item["words"] and item["phones"]
        assert (tmp_path / item["audio"]).exists()


def test_a_line_lasts_by_its_length_and_its_speed(tmp_path):
    client = silent.SilentClient(tmp_path)
    plain = VoiceSettings(stability=0.5, similarity_boost=0.75, style=0.3, speed=1.0)
    fast = VoiceSettings(stability=0.5, similarity_boost=0.75, style=0.3, speed=1.2)
    voice = next(iter(script().voices.values()))
    short = client.synthesize("No.", voice, plain).duration
    long = client.synthesize("That was four plates.", voice, plain).duration
    quick = client.synthesize("That was four plates.", voice, fast).duration
    assert short < quick < long
    assert long == pytest.approx(silent.LEAD + silent.SECONDS_PER_CHARACTER * len("That was four plates."))


def test_the_client_hears_exactly_what_was_scripted(tmp_path):
    client = silent.SilentClient(tmp_path)
    settings = VoiceSettings(stability=0.5, similarity_boost=0.75, style=0.3, speed=1.0)
    line = client.synthesize("You look thin.", next(iter(script().voices.values())), settings)
    assert client.transcribe(line.wav).text == "You look thin."


def test_it_never_replaces_a_recording(tmp_path):
    recorded = tmp_path / "timeline.json"
    recorded.write_text(json.dumps({"tts_engine": "ElevenLabs", "items": []}))
    with pytest.raises(silent.SilentError, match="a recording"):
        silent.record(script(), tmp_path)
    assert json.loads(recorded.read_text())["tts_engine"] == "ElevenLabs"


def test_it_replaces_its_own_timeline(tmp_path):
    first = silent.record(script(), tmp_path)
    assert silent.record(script(), tmp_path)["duration"] == first["duration"]


def test_a_music_bed_is_refused(tmp_path):
    from dataclasses import replace

    from support.takes import BED_PLAN

    bedded = replace(script(), bed=takes.Bed(BED_PLAN, 1, 100.0))
    with pytest.raises(silent.SilentError, match="music bed"):
        silent.record(bedded, tmp_path)


def test_main_refuses_a_file_with_no_script(tmp_path):
    empty = tmp_path / "empty_audio.py"
    empty.write_text("VALUE = 1\n")
    with pytest.raises(silent.SilentError, match="no takes.Script"):
        silent.main([str(empty), str(tmp_path / "project")])


def test_a_directed_line_and_an_exchange_have_a_silent_stand_in(tmp_path):
    ana = Voice(role="ana", id="ana456", name="Matilda")
    v4 = VoiceSettings.expressive(0.4)
    lines = (
        takes.Take("01", "dev", "Did you feed the dog?", 0.0),
        takes.Take("02", "ana", "Dog food. Discipline.", 0.3, direction=Direction(tags=("sighs",))),
        takes.Take("03", "dev", "Fine.", 0.2, direction=Direction(model="eleven_v4", pre_hold=0.5)),
    )
    s = script(takes=lines, shots=(), voices={**script().voices, "ana": ana}, settings={"dev": v4, "ana": v4},
               exchanges=(takes.Exchange("01", "02"),))  # fmt: skip
    made = silent.record(s, tmp_path)
    one, two, three = made["items"]
    assert one["exchange"]["gap"] == pytest.approx(0.0, abs=0.05)
    assert two["duration"] == pytest.approx(two["speech_duration"] + 0.3, abs=1e-6)
    assert three["pre_hold"] == 0.5
