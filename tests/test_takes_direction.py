"""Directed takes (ADR 0234): the script's checks, several takes and the one kept, the silence cut in around a line,
the model per voice, and tags kept out of the words, the captions and the speech check.

Fakes stand in for the provider; ffmpeg is real, as in test_takes.py."""

import json
import math
import struct
import wave
from dataclasses import replace
from pathlib import Path

import pytest

from srstudio import series, takes
from srstudio.direction import Direction, Pause, render
from srstudio.voice import RATE, Alignment, EffectClip, SpokenLine, Transcript, Voice, VoiceSettings, Word
from support.takes import DEV, script


def tone(path: Path, seconds: float) -> Path:
    with wave.open(str(path), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(RATE)
        w.writeframes(
            b"".join(struct.pack("<h", round(16000 * math.sin(i * 0.05))) for i in range(round(seconds * RATE)))
        )
    return path


class Provider:
    """Speech is a tone; its alignment spells the line (as the client returns it, tags already taken back out).
    ``heard`` maps (take text, seed) to what recognition hears; by default the sent text, tags as events."""

    def __init__(self, root: Path, heard=None):
        self.root, self.heard = root, heard or {}
        self.calls: list[dict] = []

    def synthesize(self, text, voice, settings, **kw):
        self.calls.append(dict(text=text, voice=voice, settings=settings, **kw))
        direction = kw.get("direction")
        model = (direction.model if direction else None) or "eleven_multilingual_v2"
        sent = render(text, direction, model).text if direction else text
        wav = tone(self.root / f"speech-{len(self.calls)}.wav", 1.2)
        n, step = len(text), 0.8 / len(text)
        alignment = Alignment(
            tuple(text), tuple(0.2 + i * step for i in range(n)), tuple(0.2 + (i + 1) * step for i in range(n))
        )
        self.calls[-1]["sent"] = sent
        return SpokenLine(text, voice, settings, alignment, wav, self.root / "t.json", 1.2, model, kw.get("seed"))

    def transcribe(self, path):
        call = self.calls[int(Path(path).stem.split("-")[1]) - 1]
        text = self.heard.get(
            (call["text"], call.get("seed")), call["sent"].upper().replace("DISCIPLINE", "discipline")
        )
        return Transcript("en", 1.0, text, tuple(Word(w, 0, 0, "word") for w in text.split()))

    def sound_effect(self, prompt, seconds):
        return EffectClip(prompt, seconds, tone(self.root / "effect.wav", seconds), self.root / "effect.json", seconds)


def confirm(voice):
    return {"voice_id": voice.id, "name": voice.name, "category": "premade"}


V4 = VoiceSettings.expressive(0.4)


def directed(*lines: takes.Take, **changes) -> takes.Script:
    return script(**{"takes": lines, "shots": (), "settings": {"dev": V4}, **changes})


def run(tmp_path, s, provider=None):
    provider = provider or Provider(tmp_path)
    root = tmp_path / "project"
    return root, takes.record(s, root, client=provider, confirm=confirm), provider


def line(id, text, hold=0.2, **direction):
    return takes.Take(id, "dev", text, hold, direction=Direction(**direction))


def test_a_tagged_v4_line_keeps_its_words_out_of_the_tags_and_records_its_direction(tmp_path):
    s = directed(line("01", "Just... discipline.", model="eleven_v4", tags=("sighs",), emphasis=("discipline",)))
    root, timeline, provider = run(tmp_path, s)
    item = timeline["items"][0]
    assert provider.calls[0]["sent"] == "[sighs] Just... DISCIPLINE." and provider.calls[0]["seed"] == 7
    assert item["text"] == "Just... discipline."
    assert [w["text"] for w in item["words"]] == ["Just...", "discipline."]  # the captions read these
    assert not any("[" in w["text"] or "]" in w["text"] for w in item["words"])
    assert not any(p["c"] in "[]" or p["c"].isupper() and p["c"] != "J" for p in item["phones"])
    assert item["model"] == "eleven_v4" and item["seed"] == 7
    assert item["direction"] == {"model": "eleven_v4", "tags": ["sighs"], "emphasis": ["discipline"]}
    report = json.loads((root / "voice-transcript.json").read_text())
    assert report["passed"] and report["lines"][0]["expected"] == "Just... discipline."


def test_a_tag_heard_as_words_fails_the_speech_check(tmp_path):
    s = directed(line("01", "Allergies.", model="eleven_v4", tags=("sighs",)))
    provider = Provider(tmp_path, heard={("Allergies.", 7): "Size allergies?"})
    with pytest.raises(takes.TakesError, match="Size allergies"):
        run(tmp_path, s, provider)


def test_several_takes_are_recorded_on_their_own_seeds_and_one_must_be_picked(tmp_path):
    s = directed(line("01", "Allergies.", model="eleven_v4", takes=3))
    provider = Provider(tmp_path, heard={("Allergies.", 8): "Energies."})
    with pytest.raises(takes.TakesError, match=r"3 takes recorded, pick one with Direction\(pick=k\)") as err:
        run(tmp_path, s, provider)
    assert "1 seed 8 MISHEARD" in str(err.value) and "2 seed 9 heard" in str(err.value)
    assert [c["seed"] for c in provider.calls] == [7, 8, 9]
    report = json.loads((tmp_path / "project" / "voice-transcript.json").read_text())
    assert [t["passed"] for t in report["lines"][0]["takes"]] == [True, False, True]


def test_the_picked_take_is_kept_and_the_build_records_every_take_and_the_pick(tmp_path):
    s = directed(line("01", "Allergies.", model="eleven_v4", takes=3, pick=2))
    _, timeline, provider = run(tmp_path, s)
    item = timeline["items"][0]
    assert item["seed"] == 9 and item["pick"] == 2 and [t["seed"] for t in item["takes"]] == [7, 8, 9]
    assert item["direction"]["pick"] == 2 and item["direction"]["takes"] == 3


def test_a_picked_take_that_was_misheard_is_refused(tmp_path):
    s = directed(line("01", "Allergies.", model="eleven_v4", takes=2, pick=1))
    provider = Provider(tmp_path, heard={("Allergies.", 8): "Energies."})
    with pytest.raises(takes.TakesError, match="take 01: heard 'Energies.'"):
        run(tmp_path, s, provider)


def test_holds_are_exact_silence_before_and_after_the_take(tmp_path):
    s = directed(
        line("01", "I don't have feelings anymore.", hold=0.0, model="eleven_v4", post_hold=0.7),
        line("02", "Just... discipline.", hold=0.3, model="eleven_v4", pre_hold=0.5),
    )
    root, timeline, _ = run(tmp_path, s)
    first, second = timeline["items"]
    assert first["duration"] == pytest.approx(first["speech_duration"] + 0.7)
    assert second["pre_hold"] == 0.5 and second["words"][0]["start"] >= 0.5
    with wave.open(str(root / second["audio"])) as w:
        pcm = w.readframes(round(0.5 * RATE))
    assert set(pcm) == {0}  # digital silence, not room tone
    assert second["duration"] == pytest.approx(second["speech_duration"] + 0.3)


def test_context_sends_the_neighbouring_spoken_lines(tmp_path):
    s = directed(
        takes.Take("01", "dev", "You cried at a dog food commercial.", 0.2),
        line("02", "Allergies.", model="eleven_v4", context=True),
        takes.Take("03", "sfx", "[BUZZ]", 0.1, prompt="a buzz", seconds=1.0, longest=0.5),
        takes.Take("04", "dev", "I wake up at four now.", 0.2),
    )
    s = replace(s, takes=s.takes[:2] + s.takes[3:])  # an effect between them is no line
    _, _, provider = run(tmp_path, s)
    directed_call = provider.calls[1]
    assert directed_call["previous_text"] == "You cried at a dog food commercial."
    assert directed_call["next_text"] == "I wake up at four now."
    assert "direction" not in provider.calls[0]  # an undirected take is asked as before


def test_a_voice_model_directs_every_line_of_that_voice(tmp_path):
    s = directed(takes.Take("01", "dev", "Allergies.", 0.2), models={"dev": "eleven_v4"})
    _, timeline, provider = run(tmp_path, s)
    assert provider.calls[0]["direction"] == Direction(model="eleven_v4")
    assert timeline["items"][0]["model"] == "eleven_v4"
    own = directed(line("01", "Allergies.", model="eleven_v3"), models={"dev": "eleven_v4"})
    assert own.direction_for(own.takes[0]).model == "eleven_v3"  # a line's own model wins


def test_an_undirected_script_asks_and_records_exactly_what_it_did(tmp_path):
    _, timeline, provider = run(tmp_path, script(shots=()))
    assert all(set(c) == {"text", "voice", "settings", "sent"} for c in provider.calls)
    assert all(not ({"model", "seed", "direction", "pre_hold"} & set(q)) for q in timeline["items"])


@pytest.mark.parametrize(
    ("take", "changes", "match"),
    [
        (line("01", "Fine.", tags=("sighs",)), {}, "speaks an audio tag aloud"),
        (line("01", "Fine.", model="eleven_v4", emphasis=("good",)), {}, "not in the line"),
        (line("01", "Fine.", model="eleven_v4", pauses=(Pause("fine", 0.5),)), {}, "no break tag"),
        (line("01", "Fine.", model="eleven_v4", post_hold=0.5), {}, "hold is said twice"),
        (takes.Take("01", "dev", "Fine.", 0, speed=0.9, direction=Direction(speed=0.9)), {}, "pace is said twice"),
        (line("01", "Fine.", model="eleven_v4"), {"settings": {"dev": VoiceSettings(0.4, 0.75, 0.3)}}, "no style"),
        (line("01", "Fine.", model="eleven_v3", context=True), {}, "refuses previous and next"),
        (takes.Take("01", "sfx", "[BUZZ]", 0.1, prompt="b", seconds=1.0, longest=0.5, direction=Direction()), {},
         "no direction"),
        (takes.Take("01", "dev", "Fine.", 0.1), {"models": {"dev": "eleven_v9"}}, "not one this kit"),
        (takes.Take("01", "dev", "Fine.", 0.1), {"models": {"ghost": "eleven_v4"}}, "who has no voice"),
    ],
)  # fmt: skip
def test_a_direction_the_take_cannot_use_is_refused_before_anything_is_requested(take, changes, match):
    with pytest.raises(takes.TakesError, match=match):
        directed(take, **changes).check()


def test_a_rehearsal_keeps_the_holds_of_a_directed_line(tmp_path):
    s = directed(
        line("01", "Fine.", hold=0.0, model="eleven_v4", pre_hold=0.4, post_hold=0.6),
        line("02", "Good.", model="eleven_v4"),
    )
    root = tmp_path / "p"
    (root / "assets").mkdir(parents=True)
    timeline = takes.rehearse(s, root)
    first = timeline["items"][0]
    assert first["pre_hold"] == 0.4 and first["words"][0]["start"] == pytest.approx(0.4)
    assert first["duration"] == pytest.approx(first["speech_duration"] + 0.6)


def test_a_series_line_carries_its_direction_and_a_series_its_voice_models():
    d = Direction(model="eleven_v4", tags=("sighs",))
    assert series.line("01", "dev", "Fine.", 0.0, direction=d).direction == d
    with pytest.raises(series.SeriesError, match="who have no voice"):
        series.Series(None, {"dev": DEV}, {"dev": V4}, ("f", "l"), {}, lambda *a, **k: {}, models={"x": "eleven_v4"})


def test_the_voice_of_a_series_line_is_unchanged_without_direction():
    assert series.line("01", "dev", "Fine.").direction is None
    assert Voice("dev", "dev123", "Will") == DEV
