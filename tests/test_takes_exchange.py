"""Exchanges (ADR 0234): a run of takes said as one Text to Dialogue generation, cut back into one take per line, each
turn heard back on its own, and the silence between turns taken from the dialogue rather than from holds.

Fakes stand in for the provider and the dialogue; ffmpeg is real, as in test_takes.py."""

import math
import struct
import wave
from dataclasses import replace
from pathlib import Path

import pytest

from srstudio import series, takes
from srstudio.dialogue import Said
from srstudio.direction import Direction
from srstudio.voice import RATE, Alignment, SpokenLine, Transcript, Voice, VoiceSettings, Word
from support.takes import DEV, script

ANA = Voice(role="ana", id="ana456", name="Matilda")
V4 = VoiceSettings.expressive(0.4)
SPEECH, GAP = 1.0, 0.3


def tone(path: Path, seconds: float) -> Path:
    with wave.open(str(path), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(RATE)
        w.writeframes(
            b"".join(struct.pack("<h", round(16000 * math.sin(i * 0.05))) for i in range(round(seconds * RATE)))
        )
    return path


def aligned(text: str) -> Alignment:
    n, step = len(text), 0.8 / len(text)
    return Alignment(
        tuple(text), tuple(0.1 + i * step for i in range(n)), tuple(0.1 + (i + 1) * step for i in range(n))
    )


class Studio:
    """Lines are tones; a dialogue's turns are tones ``SPEECH`` long that sit ``GAP`` apart on the dialogue's clock.
    ``heard`` maps (turn text, seed) to what recognition hears; by default the turn's own words."""

    def __init__(self, root: Path, heard=None, drop_turn=False):
        self.root, self.heard, self.drop_turn = root, heard or {}, drop_turn
        self.lines: list[str] = []
        self.dialogues: list[dict] = []
        self.said: dict[str, tuple[str, int | None]] = {}

    def synthesize(self, text, voice, settings, **kw):
        self.lines.append(text)
        wav = tone(self.root / f"line-{len(self.lines)}.wav", SPEECH)
        self.said[str(wav)] = (text, None)
        return SpokenLine(text, voice, settings, aligned(text), wav, self.root / "t.json", SPEECH)

    def converse(self, turns, model, settings, seed):
        self.dialogues.append({"turns": list(turns), "model": model, "settings": settings, "seed": seed})
        out = []
        for k, turn in enumerate(turns[:-1] if self.drop_turn else turns):
            wav = tone(self.root / f"dlg-{len(self.dialogues)}-{k}.wav", SPEECH)
            self.said[str(wav)] = (turn.text, seed)
            line = SpokenLine(turn.text, turn.voice, settings, aligned(turn.text), wav, self.root / "d.json", SPEECH,
                              model, seed)  # fmt: skip
            start = k * (SPEECH + GAP)
            out.append(Said(line, start, start + SPEECH))
        return out

    def transcribe(self, path):
        text, seed = self.said[str(path)]
        text = self.heard.get((text, seed), text)
        return Transcript("en", 1.0, text, tuple(Word(w, 0, 0, "word") for w in text.split()))

    def sound_effect(self, prompt, seconds):
        raise AssertionError("no effects here")


def confirm(voice):
    return {"voice_id": voice.id, "name": voice.name, "category": "premade"}


LINES = (
    takes.Take("01", "dev", "Did you feed the dog?", 0.0),
    takes.Take("02", "ana", "Dog food. Discipline.", 0.0, direction=Direction(tags=("sighs",))),
    takes.Take("03", "dev", "That is not food.", 0.4),
    takes.Take("04", "ana", "Fine.", 0.2),
)


ONE_TO_THREE = (takes.Exchange("01", "03"),)
BUZZ = takes.Take("03", "sfx", "[BUZZ]", 0.1, prompt="buzz", seconds=1.0, longest=0.5)


def exchanged(lines=LINES, exchanges=ONE_TO_THREE, **changes) -> takes.Script:
    return script(**{
        "takes": lines, "shots": (), "voices": {"dev": DEV, "ana": ANA}, "settings": {"dev": V4, "ana": V4},
        "exchanges": exchanges, **changes,
    })  # fmt: skip


def run(tmp_path, s, studio=None):
    studio = studio or Studio(tmp_path)
    root = tmp_path / "project"
    timeline = takes.record(s, root, client=studio, confirm=confirm, converse=studio.converse)
    return root, timeline, studio


# -- recording ----------------------------------------------------------------------------------------------------
def test_an_exchange_is_one_dialogue_and_the_lines_outside_it_are_their_own_requests(tmp_path):
    _, timeline, studio = run(tmp_path, exchanged())
    (dialogue,) = studio.dialogues
    assert [t.text for t in dialogue["turns"]] == [t.text for t in LINES[:3]]
    assert [t.voice for t in dialogue["turns"]] == [DEV, ANA, DEV]
    assert dialogue["turns"][1].direction == Direction(tags=("sighs",))
    assert dialogue["model"] == "eleven_v4" and dialogue["seed"] == 7
    assert studio.lines == ["Fine."]
    assert [i["id"] for i in timeline["items"]] == ["01", "02", "03", "04"]
    first = timeline["items"][0]
    assert first["model"] == "eleven_v4" and first["seed"] == 7
    assert first["exchange"] | {} == {"first": "01", "last": "03", "start": 0.0, "end": SPEECH, "gap": GAP}
    assert timeline["items"][1]["direction"] == {"tags": ["sighs"]}


def test_a_turn_lasts_until_the_next_turn_speaks_and_the_last_keeps_its_hold(tmp_path):
    _, timeline, _ = run(tmp_path, exchanged())
    one, two, three, four = timeline["items"]
    for item in (one, two):
        assert item["exchange"]["gap"] == pytest.approx(GAP, abs=1e-6)
        assert item["duration"] == pytest.approx(item["speech_duration"] + GAP, abs=1e-6)
    assert "gap" not in three["exchange"]
    assert three["duration"] == pytest.approx(three["speech_duration"] + 0.4, abs=1e-6)
    assert two["start"] == pytest.approx(one["start"] + one["duration"], abs=1 / 30)


def test_the_still_opening_moves_the_first_turn_and_leaves_its_gap(tmp_path):
    _, timeline, _ = run(tmp_path, exchanged(still=0.5))
    first = timeline["items"][0]
    assert first["still"] == 0.5
    assert first["duration"] == pytest.approx(SPEECH + 0.5 + GAP, abs=0.01)


def test_each_turn_is_heard_back_on_its_own_and_a_misheard_turn_fails_the_check(tmp_path):
    studio = Studio(tmp_path, heard={("Dog food. Discipline.", 7): "Doctor's discipline."})
    with pytest.raises(takes.TakesError, match="take 02"):
        run(tmp_path, exchanged(), studio)


def test_a_performed_sound_on_a_tagged_turn_is_not_a_misheard_word(tmp_path):
    studio = Studio(tmp_path, heard={("Dog food. Discipline.", 7): "[sighs] Dog food. Discipline."})
    _, timeline, _ = run(tmp_path, exchanged(), studio)
    assert len(timeline["items"]) == 4


def test_several_dialogues_are_recorded_on_their_own_seeds_and_one_must_be_picked(tmp_path):
    studio = Studio(tmp_path, heard={("That is not food.", 8): "That is knot food."})
    with pytest.raises(takes.TakesError, match=r"3 dialogues recorded, pick one with Exchange\(pick=k\)") as err:
        run(tmp_path, exchanged(exchanges=(takes.Exchange("01", "03", takes=3),)), studio)
    assert "1 seed 8 MISHEARD" in str(err.value) and "2 seed 9 heard" in str(err.value)
    assert [d["seed"] for d in studio.dialogues] == [7, 8, 9]


def test_the_picked_dialogue_is_kept_and_the_build_records_every_take(tmp_path):
    _, timeline, studio = run(tmp_path, exchanged(exchanges=(takes.Exchange("01", "03", takes=2, pick=1),)))
    first = timeline["items"][0]
    assert first["seed"] == 8 and first["exchange"]["pick"] == 1
    assert [c["seed"] for c in first["exchange"]["takes"]] == [7, 8]
    assert all(c["passed"] for c in first["exchange"]["takes"])
    assert "takes" not in timeline["items"][1]["exchange"]


def test_a_picked_dialogue_with_a_misheard_turn_is_refused(tmp_path):
    studio = Studio(tmp_path, heard={("Did you feed the dog?", 8): "Did you feed the doctor?"})
    with pytest.raises(takes.TakesError, match="take 01"):
        run(tmp_path, exchanged(exchanges=(takes.Exchange("01", "03", takes=2, pick=1),)), studio)


def test_a_dialogue_that_returns_too_few_turns_is_refused(tmp_path):
    with pytest.raises(takes.TakesError, match="2 turns came back for 3"):
        run(tmp_path, exchanged(), Studio(tmp_path, drop_turn=True))


def test_exchanges_need_something_that_says_a_dialogue(tmp_path):
    with pytest.raises(takes.TakesError, match="nothing says a dialogue"):
        takes.record(exchanged(), tmp_path / "p", client=Studio(tmp_path), confirm=confirm)


def test_a_script_without_exchanges_asks_for_no_dialogue(tmp_path):
    _, _, studio = run(tmp_path, exchanged(exchanges=(), models={"ana": "eleven_v4"}))
    assert studio.dialogues == [] and len(studio.lines) == 4


# -- the script's checks ------------------------------------------------------------------------------------------
@pytest.mark.parametrize(
    ("changes", "match"),
    [
        ({"exchanges": (takes.Exchange("01", "09"),)}, "both ends must be takes"),
        ({"exchanges": (takes.Exchange("03", "01"),)}, "at least two takes"),
        ({"exchanges": (takes.Exchange("02", "02"),)}, "at least two takes"),
        ({"exchanges": (takes.Exchange("01", "02"), takes.Exchange("02", "03"))}, "in two exchanges"),
        ({"exchanges": (takes.Exchange("01", "04"),)}, "take 03: inside exchange 01..04 the silence after it"),
        ({"exchanges": (takes.Exchange("01", "03", takes=0),)}, "takes is 1 to"),
        ({"exchanges": (takes.Exchange("01", "03", takes=2, pick=2),)}, "pick is a take of"),
        ({"exchanges": (takes.Exchange("01", "03", model="eleven_multilingual_v2"),)}, "does not say dialogue"),
        ({"exchanges": (takes.Exchange("01", "03", settings=VoiceSettings(0.4, 0.75, 0.3)),)}, "no style"),
        ({"lines": (replace(LINES[0], speed=1.1), *LINES[1:])}, "no pace of its own"),
        ({"lines": (replace(LINES[0], direction=Direction(post_hold=0.3)), *LINES[1:])}, "silence after it"),
        ({"lines": (LINES[0], replace(LINES[1], direction=Direction(pre_hold=0.3)), *LINES[2:])}, "its own timing"),
        ({"lines": (LINES[0], replace(LINES[1], direction=Direction(takes=2)), *LINES[2:])}, "its own timing"),
        ({"lines": (*LINES[:2], BUZZ, LINES[3])},
         "effect cannot be said"),
    ],
)  # fmt: skip
def test_an_exchange_the_dialogue_cannot_say_is_refused_before_anything_is_requested(changes, match):
    lines = changes.pop("lines", LINES)
    with pytest.raises(takes.TakesError, match=match):
        exchanged(lines=lines, **changes).check()


def test_a_reel_passes_its_exchanges_to_its_script():
    voices = {"dev": DEV, "ana": ANA}
    s = series.Series(None, voices, {"dev": V4, "ana": V4}, ("f", "l"), {}, lambda *a, **k: {})

    class Reel(series.Reel):
        pass

    Reel.series = s
    reel = Reel("r", "01", "T", "d", "a", LINES, "hook", lambda takes: {}, exchanges=(takes.Exchange("01", "03"),))
    assert reel.script().exchanges == (takes.Exchange("01", "03"),)


def test_each_turn_is_measured_and_the_dialogues_are_ranked_with_their_numbers(tmp_path):
    studio = Studio(tmp_path, heard={("That is not food.", 7): "That is knot food."})
    _, timeline, _ = run(tmp_path, exchanged(exchanges=(takes.Exchange("01", "03", takes=2, pick=1),)), studio)
    first = timeline["items"][0]
    assert first["exchange"]["rank"] == [1, 0]  # the misheard dialogue ranks last
    assert all("measured" in c for c in first["exchange"]["takes"])
    assert all("words_per_second" in t for c in first["exchange"]["takes"] for t in c["turns"])
    assert all("prosody" in item for item in timeline["items"])
