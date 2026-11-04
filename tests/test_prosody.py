"""The prosody gate (ADR 0234 c): pitch and level per heard word, a stressed word over the rest of its line, the
pace, the timing of first word, replies, punchlines and the end, holds against the direction, waivers with reasons,
and takes ranked and recorded with their numbers. Every check fails on a fixture that breaks it.

Audio is synthesised here (tones of known pitch and level per word); the provider is a fake; ffmpeg is real."""

import json
import math
import wave
from pathlib import Path

import numpy as np
import pytest

from srstudio import prosody, takes
from srstudio.direction import Direction, DirectionError, Waiver
from srstudio.prosody import Finding, ProsodyError, gate, measure, pitch_track
from srstudio.voice import RATE, Alignment, SpokenLine, Transcript, VoiceSettings, Word
from support.takes import DEV, script


def harmonic(f: float, seconds: float, amp: float, rate: int = RATE) -> np.ndarray:
    t = np.arange(round(seconds * rate)) / rate
    return amp * sum(np.sin(2 * np.pi * f * k * t) / k for k in range(1, 6)) / 2.3


def write(path: Path, x: np.ndarray, rate: int = RATE) -> Path:
    pcm = np.clip(np.round(x * 32767), -32768, 32767).astype("<i2")
    with wave.open(str(path), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(rate)
        w.writeframes(pcm.tobytes())
    return path


def line_wav(path: Path, words: list[tuple[str, float, float]], pitch: dict[str, tuple[float, float]]) -> list[Word]:
    """A clip with each word a harmonic tone (``pitch[word] = (hz, amplitude)``, else 150 Hz at 0.2) over its span,
    silence between; returns the words as speech-to-text would report them."""
    end = max(e for _, _, e in words) + 0.3
    x = np.zeros(round(end * RATE))
    for text, a, b in words:
        hz, amp = pitch.get(text, (150.0, 0.2))
        tone = harmonic(hz, b - a, amp)
        x[round(a * RATE) : round(a * RATE) + tone.size] = tone
    write(path, x)
    return [Word(t, a, b, "word") for t, a, b in words]


WORDS = [("Dog", 0.1, 0.4), ("food", 0.5, 0.8), ("and", 0.9, 1.1), ("discipline.", 1.2, 1.8)]


# -- measuring ----------------------------------------------------------------------------------------------------
@pytest.mark.parametrize("hz", [90.0, 150.0, 240.0, 330.0])
def test_the_pitch_track_finds_a_voices_fundamental(hz):
    _, f0 = pitch_track(harmonic(hz, 1.0, 0.3), RATE)
    voiced = f0[~np.isnan(f0)]
    assert voiced.size > 0.9 * f0.size
    assert np.median(voiced) == pytest.approx(hz, rel=0.01)


def test_silence_and_noise_have_no_pitch():
    _, f0 = pitch_track(np.zeros(RATE), RATE)
    assert np.isnan(f0).all()
    noise = np.random.default_rng(3).normal(0, 0.2, RATE)
    _, f0 = pitch_track(noise, RATE)
    assert np.isnan(f0).mean() > 0.9


def test_a_stressed_word_louder_and_higher_than_its_line_lands(tmp_path):
    words = line_wav(tmp_path / "l.wav", WORDS, {"discipline.": (190.0, 0.4)})
    m = measure(tmp_path / "l.wav", words, ("discipline",))
    (s,) = m.stressed
    assert s.heard and s.db == pytest.approx(20 * math.log10(2), abs=0.3)
    assert s.st == pytest.approx(12 * math.log2(190 / 150), abs=0.2)
    assert s.landed
    assert [w.text for w in m.words] == ["Dog", "food", "and", "discipline."]
    assert all(w.hz == pytest.approx(150, rel=0.01) for w in m.words[:3])


@pytest.mark.parametrize(
    ("pitch", "why"),
    [
        ({}, "flat"),
        ({"discipline.": (150.0, 0.4)}, "louder only"),
        ({"discipline.": (190.0, 0.2)}, "higher only"),
        ({"discipline.": (155.0, 0.25)}, "a little of both"),
    ],
)
def test_a_stressed_word_that_does_not_stand_out_does_not_land(tmp_path, pitch, why):
    words = line_wav(tmp_path / "l.wav", WORDS, pitch)
    (s,) = measure(tmp_path / "l.wav", words, ("discipline",)).stressed
    assert s.heard and not s.landed, why


def test_a_stressed_word_not_heard_is_recorded_as_not_heard(tmp_path):
    words = line_wav(tmp_path / "l.wav", WORDS, {})
    (s,) = measure(tmp_path / "l.wav", words, ("doctor",)).stressed
    assert not s.heard and not s.landed and s.db is None


def test_the_pace_is_words_over_the_spoken_span_and_events_are_not_words(tmp_path):
    words = line_wav(tmp_path / "l.wav", WORDS, {})
    m = measure(tmp_path / "l.wav", [Word("(sighs)", 0.0, 0.1, "audio_event"), *words, Word(" ", 1.8, 1.9, "spacing")])
    assert len(m.words) == 4 and m.first == 0.1 and m.last == 1.8
    assert m.pace == pytest.approx(4 / 1.7, abs=1e-3)


def test_a_word_too_short_or_unvoiced_has_no_number_and_an_empty_line_no_pace(tmp_path):
    write(tmp_path / "s.wav", np.zeros(RATE))
    m = measure(tmp_path / "s.wav", [Word("Hm", 0.2, 0.2, "word")], ("Hm",))
    assert m.words[0].db is None and m.words[0].hz is None and m.pace is None
    assert not m.stressed[0].landed
    assert measure(tmp_path / "s.wav", []).pace is None


def test_the_record_moves_word_times_onto_the_takes_clock(tmp_path):
    words = line_wav(tmp_path / "l.wav", WORDS, {"discipline.": (190.0, 0.4)})
    rec = measure(tmp_path / "l.wav", words, ("discipline",)).record(offset=0.4)
    assert rec["first"] == 0.5 and rec["last"] == 2.2
    assert rec["words"][0] | {} == {"text": "Dog", "start": 0.5, "end": 0.8, "db": rec["words"][0]["db"], "hz": 150.0}
    assert rec["stressed"][0]["landed"] is True and rec["stressed"][0]["word"] == "discipline"


def test_a_take_whose_stress_lands_ranks_above_one_whose_does_not(tmp_path):
    flat = measure(tmp_path / "a.wav", line_wav(tmp_path / "a.wav", WORDS, {}), ("discipline",))
    lands = measure(
        tmp_path / "b.wav", line_wav(tmp_path / "b.wav", WORDS, {"discipline.": (190, 0.4)}), ("discipline",)
    )
    assert lands.rank() > flat.rank()
    fast = [(w, a / 2, b / 2) for w, a, b in WORDS]
    quick = measure(
        tmp_path / "c.wav", line_wav(tmp_path / "c.wav", fast, {"discipline.": (190, 0.4)}), ("discipline",)
    )
    assert quick.pace > prosody.LINE_PACE and lands.rank() > quick.rank()


# -- the gate -----------------------------------------------------------------------------------------------------
def item(id, actor, text, start, duration, first, last, n, stressed=(), direction=None):
    return {
        "id": id, "actor": actor, "text": text, "start": start, "duration": duration,
        "prosody": {"first": first, "last": last, "words_per_second": round(n / (last - first), 3),
                    "words": [{"text": "w"}] * n, "stressed": [dict(s) for s in stressed]},
    } | ({"direction": direction} if direction else {})  # fmt: skip


LANDED = {"word": "Discipline", "heard": True, "db": 4.0, "st": 3.0, "landed": True}


def timeline() -> dict:
    """A reel that keeps every target: a question answered after 0.5 s, a reply after 0.55 s, a punchline after 1.2 s
    and 0.6 s to the end."""
    return {
        "duration": 6.3,
        "items": [
            item("01", "dev", "Did you feed the dog?", 0.0, 1.6, 0.1, 1.3, 5),
            item("02", "ana", "Dog food.", 1.6, 1.3, 0.2, 1.0, 2),
            item("03", "dev", "Then what?", 2.9, 2.0, 0.25, 0.9, 2),
            item("04", "ana", "Discipline.", 4.9, 1.4, 0.1, 0.8, 1, [LANDED], {"punchline": "Discipline"}),
        ],
    }


def test_a_reel_that_keeps_every_target_has_no_finding():
    assert gate(timeline()) == []


def shift(t: dict, index: int, seconds: float) -> dict:
    """Moves take ``index`` and everything after it later by ``seconds``."""
    for it in t["items"][index:]:
        it["start"] = round(it["start"] + seconds, 6)
    t["duration"] = round(t["duration"] + seconds, 6)
    return t


def edit(path, value):
    def go(t):
        node = t
        for key in path[:-1]:
            node = node[key]
        node[path[-1]] = value
        return t

    return go


def first_word_late(t):
    for it in t["items"]:
        it["start"] += 0.3
    t["duration"] += 0.3
    return t


def fast_reel(t):
    """More words in the same spans: every line within 4.3 words a second, the reel at 3.9."""
    for it in t["items"]:
        p = it["prosody"]
        n = math.floor(prosody.LINE_PACE * (p["last"] - p["first"]))
        p["words"], p["words_per_second"] = [{"text": "w"}] * n, round(n / (p["last"] - p["first"]), 3)
    return t


def second_long_answer(t):
    t = shift(t, 1, 0.5)  # 01 -> 02: 1.0 s, the reel's one emotional hold
    t["items"][2]["text"] = "Then what?"
    t["items"][1]["text"] = "Dog food?"
    return shift(t, 2, 0.5)  # 02 -> 03: a second question answered after 1.05 s


@pytest.mark.parametrize(
    ("spoil", "check", "take"),
    [
        (edit(("items", 0, "prosody", "words_per_second"), 5.0), "line_pace", "01"),
        (fast_reel, "reel_pace", None),
        (first_word_late, "first_word", "01"),
        (lambda t: shift(t, 2, -0.35), "turn_gap", "03"),
        (lambda t: shift(t, 2, 0.2), "turn_gap", "03"),
        (lambda t: shift(t, 1, -0.2), "answer_gap", "02"),
        (lambda t: shift(t, 1, 1.2), "answer_gap", "02"),
        (second_long_answer, "answer_gap", "03"),
        (lambda t: shift(t, 3, -0.5), "punch_gap", "04"),
        (lambda t: shift(t, 3, 0.7), "punch_gap", "04"),
        (edit(("duration",), 5.8), "end_breath", "04"),
        (edit(("duration",), 7.2), "end_breath", "04"),
        (edit(("items", 3, "prosody", "stressed", 0), LANDED | {"st": 0.5, "landed": False}), "stress", "04"),
        (edit(("items", 3, "prosody", "stressed", 0), {"word": "Discipline", "heard": False}), "stress", "04"),
        (edit(("items", 1, "direction"), {"pre_hold": 0.5}), "hold", "02"),
        (edit(("items", 1, "direction"), {"post_hold": 0.6}), "hold", "02"),
        (edit(("items", 1, "prosody", "first"), None), "heard", "02"),
    ],
)  # fmt: skip
def test_each_check_fails_on_a_reel_that_breaks_it(spoil, check, take):
    found = gate(spoil(timeline()))
    assert [(f.check, f.take) for f in found] == [(check, take)], [f.line() for f in found]
    assert prosody.failing(found) == found


def test_one_emotional_hold_per_reel_is_allowed_after_a_question():
    t = shift(timeline(), 1, 0.8)  # 01 -> 02: 1.3 s
    assert gate(t) == []


def test_a_waiver_states_its_reason_and_keeps_the_finding_visible():
    t = timeline()
    t["items"][3]["prosody"]["stressed"][0] |= {"st": 0.5, "landed": False}
    t["items"][3]["direction"]["waive"] = [{"check": "stress", "reason": "the deadpan is the joke here"}]
    (finding,) = gate(t)
    assert finding.waived == "the deadpan is the joke here" and prosody.failing([finding]) == []
    assert "waived: the deadpan is the joke here" in finding.line()


def test_a_waiver_with_bounds_moves_the_target_and_a_value_outside_them_still_fails():
    t = shift(timeline(), 2, 0.5)  # 02 -> 03: 1.05 s
    t["items"][2]["direction"] = {"waive": [{"check": "turn_gap", "reason": "he lets it hang", "bounds": [0.9, 1.2]}]}
    assert gate(t) == []
    t = shift(t, 2, 0.5)
    (finding,) = gate(t)
    assert finding.bounds == (0.9, 1.2) and not finding.waived


def test_the_reels_pace_is_waived_on_the_reel():
    t = fast_reel(timeline())
    t["prosody"] = {"waive": [{"check": "reel_pace", "reason": "an auctioneer sketch is fast"}]}
    (finding,) = gate(t)
    assert finding.check == "reel_pace" and finding.waived


def test_an_effect_between_two_lines_times_that_silence_itself():
    t = timeline()
    t["items"].insert(2, {"id": "02b", "actor": "sfx", "start": 2.9, "duration": 0.1})
    shift(t, 3, 2.0)
    assert gate(t) == []


@pytest.mark.parametrize(
    ("spoil", "match"),
    [
        (edit(("items",), "x"), "no items"),
        (edit(("items", 0, "prosody"), None), "not measured"),
        (edit(("items", 0), "x"), "not an object"),
        (edit(("items", 0, "start"), float("nan")), "finite number"),
        (edit(("items", 0, "prosody", "stressed"), [{"word": 3}]), "stressed word record"),
        (edit(("items", 0, "prosody", "words"), 4), "not a list"),
        (edit(("items", 0, "direction"), []), "direction is not an object"),
        (edit(("items",), [{"id": "x", "actor": "sfx"}]), "no spoken take"),
    ],
)  # fmt: skip
def test_a_timeline_the_gate_cannot_read_is_a_typed_error(spoil, match):
    with pytest.raises(ProsodyError, match=match):
        gate(spoil(timeline()))


def test_the_command_exits_on_findings_and_on_an_unmeasured_timeline(tmp_path, capsys):
    (tmp_path / "timeline.json").write_text(json.dumps(timeline()))
    assert prosody.main([str(tmp_path)]) == 0
    (tmp_path / "timeline.json").write_text(json.dumps(edit(("duration",), 9.0)(timeline())))
    assert prosody.main([str(tmp_path)]) == 1
    assert "take 04: end_breath" in capsys.readouterr().out
    assert prosody.main([str(tmp_path), "--json"]) == 1
    assert json.loads(capsys.readouterr().out)[0]["check"] == "end_breath"
    (tmp_path / "timeline.json").write_text(json.dumps({"items": [{"id": "1", "actor": "dev"}], "duration": 1}))
    assert prosody.main([str(tmp_path)]) == 2


# -- waivers and the gate's fields on a direction -----------------------------------------------------------------
@pytest.mark.parametrize(
    ("kw", "match"),
    [
        ({"check": "loudness", "reason": "it is loud on purpose"}, "the checks are"),
        ({"check": "stress", "reason": "deadpan"}, "at least 3 words"),
        ({"check": "stress", "reason": 3}, "at least 3 words"),
        ({"check": "stress", "reason": "x " * 120}, "at most 200"),
        ({"check": "stress", "reason": "the deadpan is the joke", "bounds": (1.0, 2.0)}, "no bounds"),
        ({"check": "turn_gap", "reason": "he lets it hang", "bounds": (1.2, 0.9)}, "low <= high"),
        ({"check": "turn_gap", "reason": "he lets it hang", "bounds": [0.9, 1.2]}, "low <= high"),
        ({"check": "turn_gap", "reason": "he lets it hang", "bounds": (-1.0, 1.2)}, "low <= high"),
    ],
)  # fmt: skip
def test_a_waiver_without_a_reason_or_with_bounds_that_mean_nothing_is_refused(kw, match):
    with pytest.raises(DirectionError, match=match):
        Waiver(**kw)


@pytest.mark.parametrize(
    ("kw", "match"),
    [
        ({"punchline": "dog food"}, "the one word"),
        ({"waive": (Waiver("stress", "the deadpan is the joke"),) * 2}, "waived twice"),
        ({"waive": (Waiver("reel_pace", "an auctioneer sketch is fast"),)}, "waive them on the script"),
        ({"waive": ("stress",)}, "tuple of Waiver"),
    ],
)
def test_a_direction_refuses_a_malformed_punchline_or_waiver(kw, match):
    with pytest.raises(DirectionError, match=match):
        Direction(**kw)


def test_marking_a_punchline_or_a_waiver_asks_nothing_of_the_provider():
    assert not Direction(punchline="Fine", waive=(Waiver("stress", "the deadpan is the joke"),)).asks
    assert Direction(emphasis=("Fine",)).asks and Direction(post_hold=0.3).asks
    assert Direction(emphasis=("dog",), punchline="Food").stressed == ("dog", "Food")
    assert Direction(emphasis=("food",), punchline="Food").stressed == ("food",)


# -- recording: measured, ranked, recorded ------------------------------------------------------------------------
class Provider:
    """Seed 7 says "discipline" flat, seed 8 stressed; a take without a seed is flat. Words as speech-to-text reports
    them."""

    def __init__(self, root: Path, stressed_seeds=(8,)):
        self.root, self.stressed_seeds, self.calls = root, stressed_seeds, []
        self.words: dict[str, list[Word]] = {}

    def synthesize(self, text, voice, settings, **kw):
        self.calls.append(dict(text=text, **kw))
        seed = kw.get("seed")
        spans = [(w, 0.1 + 0.4 * i, 0.4 + 0.4 * i) for i, w in enumerate(text.split())]
        pitch = {spans[-1][0]: (190.0, 0.4)} if seed in self.stressed_seeds else {}
        wav = self.root / f"speech-{len(self.calls)}.wav"
        self.words[str(wav)] = line_wav(wav, spans, pitch)
        n = len(text)
        alignment = Alignment(
            tuple(text), tuple(0.1 + i * 0.01 for i in range(n)), tuple(0.11 + i * 0.01 for i in range(n))
        )
        return SpokenLine(text, voice, settings, alignment, wav, self.root / "t.json", 1.0, "eleven_v4", seed)

    def transcribe(self, path):
        words = self.words[str(path)]
        return Transcript("en", 1.0, " ".join(w.text for w in words), tuple(words))

    def sound_effect(self, prompt, seconds):
        raise AssertionError("no effects")


def confirm(voice):
    return {"voice_id": voice.id, "name": voice.name, "category": "premade"}


V4 = VoiceSettings.expressive(0.4)
STRESSED = Direction(model="eleven_v4", emphasis=("discipline",), takes=2)


def record(tmp_path, *lines, provider=None, **changes):
    provider = provider or Provider(tmp_path)
    s = script(**{"takes": lines, "shots": (), "settings": {"dev": V4}, **changes})
    return takes.record(s, tmp_path / "project", client=provider, confirm=confirm), provider


def test_takes_are_ranked_on_their_stress_and_listed_best_first_with_their_numbers(tmp_path):
    with pytest.raises(takes.TakesError, match=r"pick one with Direction\(pick=k\), best first: 1 seed 8 heard") as e:
        record(tmp_path, takes.Take("01", "dev", "Dog food and discipline", 0.4, direction=STRESSED))
    assert "discipline +6.0 dB +4.1 st" in str(e.value)
    report = json.loads((tmp_path / "project" / "voice-transcript.json").read_text())
    flat, stressed = report["lines"][0]["takes"]
    assert stressed["stressed"][0]["landed"] and not flat["stressed"][0]["landed"]


def test_the_kept_take_records_its_measures_on_the_takes_clock_and_the_reel_its_findings(tmp_path):
    from dataclasses import replace

    take = takes.Take("01", "dev", "Dog food and discipline", 0.0,
                      direction=replace(STRESSED, pick=1, pre_hold=0.5, post_hold=0.6))  # fmt: skip
    timeline, _ = record(tmp_path, take)
    (it,) = timeline["items"]
    assert it["rank"] == [1, 0] and it["pick"] == 1
    p = it["prosody"]
    assert p["first"] == pytest.approx(0.5 + 0.1 - it["trim_start"], abs=0.002)
    assert p["stressed"][0]["landed"] and p["words_per_second"] == pytest.approx(4 / 1.5, abs=0.01)
    reel = timeline["prosody"]
    assert reel["targets"]["reel_pace"] == 3.6 and reel["targets"]["stress_st"] == 2.0
    assert any("first_word" in f for f in reel["findings"]) and reel["passed"] is False
    assert gate(timeline) == gate(json.loads((tmp_path / "project" / "timeline.json").read_text()))


def test_a_line_marked_only_for_the_gate_is_requested_as_an_undirected_line(tmp_path):
    marked = Direction(punchline="discipline", waive=(Waiver("first_word", "the cold open holds a beat"),))
    timeline, provider = record(tmp_path, takes.Take("01", "dev", "Dog food and discipline", 0.4, direction=marked))
    assert provider.calls == [{"text": "Dog food and discipline"}]
    (it,) = timeline["items"]
    assert it["direction"] == {"punchline": "discipline",
                               "waive": [{"check": "first_word", "reason": "the cold open holds a beat"}]}  # fmt: skip
    assert not it["prosody"]["stressed"][0]["landed"]
    assert "take 01: stress" in " ".join(timeline["prosody"]["findings"])


def test_a_punchline_word_the_line_does_not_have_is_refused():
    s = script(takes=(takes.Take("01", "dev", "Dog food.", 0.4, direction=Direction(punchline="discipline")),),
               shots=())  # fmt: skip
    with pytest.raises(takes.TakesError, match="punchline's word 'discipline' is not in the line"):
        s.check()


@pytest.mark.parametrize(
    ("waive", "match"),
    [
        ((Waiver("stress", "the deadpan is the joke"),), "a line's checks go in its direction"),
        ((Waiver("reel_pace", "an auctioneer is fast"),) * 2, "once each"),
        ([Waiver("reel_pace", "an auctioneer is fast")], "tuple of Waiver"),
    ],
)
def test_a_script_waives_only_the_reels_targets(waive, match):
    with pytest.raises(takes.TakesError, match=match):
        script(waive=waive).check()


def test_a_reel_passes_its_waivers_to_its_script():
    from srstudio import series

    s = series.Series(None, {"dev": DEV}, {"dev": V4}, ("f", "l"), {}, lambda *a, **k: {})

    class Reel(series.Reel):
        pass

    Reel.series = s
    w = (Waiver("reel_pace", "an auctioneer is fast"),)
    lines = (takes.Take("01", "dev", "Sold.", 0.4),)
    assert Reel("r", "01", "T", "d", "a", lines, "hook", lambda t: {}, waive=w).script().waive == w


def test_a_finding_reads_as_one_line():
    f = Finding("turn_gap", "03", 0.2, (0.3, 0.65))
    assert f.line() == "take 03: turn_gap 0.200 outside 0.3..0.65"
    assert Finding("reel_pace", None, 4.0, (0.0, 3.6), waived="fast on purpose").line().startswith("reel: reel_pace")
