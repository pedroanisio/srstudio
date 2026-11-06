"""An interview line's key words stressed by gain on a derived clip of its take (Spoken.stress, interview.stress)."""

from __future__ import annotations

import json
import wave
from pathlib import Path

import numpy as np
import pytest

from srstudio import interview as I
from srstudio import prosody
from srstudio.emphasis import EmphasisError
from srstudio.generated import Resolved, sha256_of
from srstudio.voice import Transcript, Word
from support.interview import make
from support.song import engine, tone

RATE = 48000
TEXT = "A fish expert says weeks."


def take(path: Path, text: str = TEXT, levels: dict[str, float] | None = None) -> tuple[Path, Transcript]:
    """A synthetic take of ``text``: 0.3 s of a voice-like tone per word, 0.1 s apart, all at one level unless
    ``levels`` says; and the transcript a recogniser would hear of it."""
    x, words, at = [np.zeros(round(0.05 * RATE))], [], 0.05
    for i, w in enumerate(text.split()):
        t = np.arange(round(0.3 * RATE)) / RATE
        x.append((levels or {}).get(w.strip(".").lower(), 0.25) * np.sin(2 * np.pi * (150 + 10 * i) * t))
        words.append(Word(w, round(at, 6), round(at + 0.3, 6), "word"))
        x += [np.zeros(round(0.1 * RATE))]
        at += 0.4
    path.parent.mkdir(parents=True, exist_ok=True)
    with wave.open(str(path), "wb") as f:
        f.setnchannels(1)
        f.setsampwidth(2)
        f.setframerate(RATE)
        f.writeframes((np.concatenate(x) * 32767).astype("<i2").tobytes())
    return path, Transcript("en", 1.0, text, tuple(words))


def stressed_interview(stress: tuple[str, ...] = ("weeks",), text: str = TEXT) -> I.Interview:
    return make(lines=[I.Spoken("manager", "Why here?", "Why here?"), I.Spoken("candidate", text, text, stress=stress)])


def pins_and_ears(root: Path, iv: I.Interview, transcripts: dict[str, Transcript] | None = None):
    """Every line's pinned take under ``root/assets/generated`` and a recogniser that hears them."""
    lines, _ = I.declarations(iv)
    pins, heard = {}, {}
    for item, line in zip(lines, iv.lines, strict=True):
        path, transcript = take(root / item.cache, line.text)
        pins[item.id] = Resolved(item, path, sha256_of(path))
        heard[path] = (transcripts or {}).get(item.id, transcript)
    return pins, lambda path: heard[path]


# -- the checks --------------------------------------------------------------------------------------------------
@pytest.mark.parametrize(
    "stress, text, match",
    [
        (["weeks"], TEXT, "stress must be a tuple of non-empty strings"),
        (("",), TEXT, "stress must be a tuple of non-empty strings"),
        (("weeks", 3), TEXT, "stress must be a tuple of non-empty strings"),
        (("month",), TEXT, "the stressed word 'month' is not one word of"),
        (("fish expert",), TEXT, "the stressed word 'fish expert' is not one word of"),
        (("weeks", "Weeks"), TEXT, "names 'Weeks' twice"),
        (("chair",), "Chair!", "one word"),
    ],
)
def test_a_stress_the_line_cannot_carry_is_refused_when_made_naming_the_line(stress, text, match):
    with pytest.raises(I.InterviewError, match=match) as caught:
        stressed_interview(stress, text)
    assert str(caught.value).startswith("line 2:")


def test_a_stressed_word_is_matched_without_case_or_punctuation():
    iv = stressed_interview(("WEEKS!", "fish,"))
    assert iv.lines[1].stress == ("WEEKS!", "fish,")
    assert I.Spoken("x", "y", "y").stress == ()


# -- the build step ----------------------------------------------------------------------------------------------
def test_a_flat_word_is_raised_on_a_derived_clip_and_the_take_keeps_its_pin(tmp_path):
    iv = stressed_interview()
    pins, ears = pins_and_ears(tmp_path, iv)
    source = pins["line-2"]
    before = source.path.read_bytes()
    assert prosody.measure(source.path, ears(source.path).words, ["weeks"]).stressed[0].db < prosody.STRESS_DB

    out, record = I.stress(iv, tmp_path, pins, ears)

    assert out["line-1"] is pins["line-1"]  # a line with no stress keeps its take
    derived = out["line-2"]
    assert derived.path == tmp_path / "assets" / "stressed" / "line-2.wav"
    assert derived.generated.cache == "assets/stressed/line-2.wav" and derived.sha256 == sha256_of(derived.path)
    assert source.path.read_bytes() == before and sha256_of(source.path) == source.sha256  # the take is untouched
    got = prosody.measure(derived.path, ears(source.path).words, ["weeks"]).stressed[0]
    assert got.db >= prosody.STRESS_DB
    [entry] = record
    assert entry["line"] == 2 and entry["source"] == "assets/generated/line-2.wav"
    assert entry["source_sha256"] == source.sha256 and entry["sha256"] == derived.sha256
    assert entry["clip"] == "assets/stressed/line-2.wav" and 0 < entry["words"]["weeks"] <= 9.0

    placed = I.place(iv, {**out, "squeak": squeak(tmp_path, iv)}, back_to_back)
    clip = next(c for c in placed.clips if c.generated.id == "line-2")
    assert clip.sha256 == derived.sha256  # placed (trimmed, levelled) from the derived clip; build names its file


def test_the_same_take_gives_the_same_clip_on_every_build(tmp_path):
    iv = stressed_interview()
    pins, ears = pins_and_ears(tmp_path, iv)
    first = I.stress(iv, tmp_path, pins, ears)
    again = I.stress(iv, tmp_path, pins, ears)
    assert first[0]["line-2"].sha256 == again[0]["line-2"].sha256 and first[1] == again[1]


def test_a_word_the_take_already_stresses_is_raised_by_nothing(tmp_path):
    iv = stressed_interview()
    pins, ears = pins_and_ears(tmp_path, iv)
    path, transcript = take(pins["line-2"].path, TEXT, {"weeks": 0.6})
    pins["line-2"] = Resolved(pins["line-2"].generated, path, sha256_of(path))
    _, record = I.stress(iv, tmp_path, pins, lambda p: transcript if p == path else ears(p))
    assert record[0]["words"] == {"weeks": 0.0}


def test_a_stressed_word_the_take_does_not_say_stops_the_build_naming_the_line(tmp_path):
    iv = stressed_interview()
    pins, ears = pins_and_ears(tmp_path, iv)
    words = tuple(w for w in ears(pins["line-2"].path).words if w.text != "weeks.")
    misheard = Transcript("en", 1.0, "A fish expert says.", words)
    pins, ears = pins_and_ears(tmp_path, iv, {"line-2": misheard})
    with pytest.raises(I.InterviewError, match=r"line 2: .*weeks.* not heard") as caught:
        I.stress(iv, tmp_path, pins, ears)
    assert isinstance(caught.value, EmphasisError)


def test_a_take_heard_as_one_word_cannot_be_stressed(tmp_path):
    iv = stressed_interview()
    pins, ears = pins_and_ears(tmp_path, iv)
    one = Transcript("en", 1.0, "weeks", (Word("weeks", 1.65, 1.95, "word"),))
    with pytest.raises(I.InterviewError, match="line 2: the take is heard as 1 word.*one-word take cannot be stressed"):
        I.stress(iv, tmp_path, pins, lambda p: one if p == pins["line-2"].path else ears(p))


def test_no_stress_changes_nothing(tmp_path):
    iv = make()
    pins, ears = pins_and_ears(tmp_path, iv)
    out, record = I.stress(iv, tmp_path, pins, ears)
    assert out == pins and all(out[k] is pins[k] for k in pins) and record == []
    assert not (tmp_path / "assets" / "stressed").exists()


def test_a_two_word_line_is_stressed_on_the_word_it_names(tmp_path):
    # "I'm not.": the stressed word is half of the line's median word, so the median moves with its gain
    iv = stressed_interview(("not",), "I'm not.")
    pins, ears = pins_and_ears(tmp_path, iv)
    path, transcript = take(pins["line-2"].path, "I'm not.", {"not": 0.25 * 10 ** (-1.5 / 20)})
    pins["line-2"] = Resolved(pins["line-2"].generated, path, sha256_of(path))
    assert prosody.measure(path, transcript.words, ["not"]).stressed[0].db < 0

    out, record = I.stress(iv, tmp_path, pins, lambda p: transcript if p == path else ears(p))

    got = prosody.measure(out["line-2"].path, transcript.words, ["not"]).stressed[0]
    assert got.db >= prosody.STRESS_DB
    assert 0 < record[0]["words"]["not"] <= 9.0


# -- the whole build, on the fake provider ------------------------------------------------------------------------
def back_to_back(speech, effect) -> I.Schedule:
    starts, cursor = [], 0.5
    for length in speech:
        starts.append(cursor)
        cursor += length + 0.3
    return I.Schedule(starts, {"squeak": starts[0] + speech[0] + 0.05})


def squeak(root: Path, iv: I.Interview) -> Resolved:
    item = I.declarations(iv)[1][0]
    p = tone(root / item.cache, 0.2, lead=0.02)
    return Resolved(item, p, sha256_of(p))


def test_a_build_without_stress_writes_no_stress_record(tmp_path, fake_env):
    # one fake MP3 for every line shares one cached hearing, so both lines say the same words (as test_interview did)
    iv = make(lines=[I.Spoken("manager", "Sit down.", "Sit down."), I.Spoken("candidate", "Sit down.", "Sit.")])
    out = I.build(iv, tmp_path / "p", engine=engine(), key="sk-test", env=fake_env, schedule=back_to_back)
    data = json.loads(out.read_text())
    assert "stress" not in data and all("stress" not in p for p in data["phrases"])
    assert all(c["generated"]["cache"].startswith("assets/generated/") for c in data["clips"])
    assert not (tmp_path / "p" / "assets" / "stressed").exists()


def test_a_build_places_the_stressed_clip_and_records_each_word_and_its_gain(tmp_path, fake_env):
    lines = [
        I.Spoken("manager", "Sit down.", "Sit down."),
        I.Spoken("candidate", "Sit down.", "Sit.", stress=("down",)),
    ]
    root = tmp_path / "p"
    out = I.build(make(lines=lines), root, engine=engine(), key="sk-test", env=fake_env, schedule=back_to_back)
    data = json.loads(out.read_text())
    [entry] = data["stress"]
    take = root / "assets" / "generated" / "line-2.wav"
    assert entry["line"] == 2 and entry["source"] == "assets/generated/line-2.wav"
    assert entry["source_sha256"] == sha256_of(take) and set(entry["words"]) == {"down"}
    assert data["phrases"][1]["stress"] == entry["words"] and "stress" not in data["phrases"][0]
    clip = next(c for c in data["clips"] if c["generated"]["id"] == "line-2")
    assert clip["generated"]["cache"] == "assets/stressed/line-2.wav" == entry["clip"]
    assert clip["sha256"] == entry["sha256"] == sha256_of(root / entry["clip"])


def test_a_line_may_aim_its_stress_higher_than_the_bar(tmp_path):
    line = I.Spoken("candidate", TEXT, TEXT, stress=("weeks",), stress_aim=5.0)
    iv = make(lines=[I.Spoken("manager", "Why here?", "Why here?"), line])
    pins, ears = pins_and_ears(tmp_path, iv)
    out, record = I.stress(iv, tmp_path, pins, ears)
    got = prosody.measure(out["line-2"].path, ears(pins["line-2"].path).words, ["weeks"]).stressed[0]
    assert got.db >= 4.5 and record[0]["aim"] == 5.0
    assert I.Spoken("x", "y z", "y z").stress_aim is None


@pytest.mark.parametrize(
    ("stress", "aim", "match"),
    [((), 5.0, "stress_aim needs stressed words"), (("weeks",), 3.0, "stress_aim"), (("weeks",), "5", "stress_aim")],
)
def test_a_stress_aim_without_stress_or_under_the_default_is_refused(stress, aim, match):
    with pytest.raises(I.InterviewError, match=match):
        make(
            lines=[
                I.Spoken("manager", "Why here?", "Why here?"),
                I.Spoken("candidate", TEXT, TEXT, stress=stress, stress_aim=aim),
            ]
        )


def test_a_stressed_line_is_placed_on_its_take_s_trim_so_the_timing_holds(tmp_path):
    # lean lifts "weeks" past the take's peak and scales the clip back down, so the quiet "A" falls under the trim
    # threshold on the derived clip: placed from its own trim, the line would start later and run shorter
    iv = stressed_interview()
    pins, ears = pins_and_ears(tmp_path, iv)
    path, transcript = take(pins["line-2"].path, TEXT, {"a": 0.005})
    pins["line-2"] = Resolved(pins["line-2"].generated, path, sha256_of(path))
    out, _ = I.stress(iv, tmp_path, pins, lambda p: transcript if p == path else ears(p))
    assert I.trim_speech(out["line-2"].path) != I.trim_speech(path)  # the derived clip trims differently

    fx = {"squeak": squeak(tmp_path, iv)}
    plain = I.place(iv, {**pins, **fx}, back_to_back)
    placed = I.place(iv, {**out, **fx}, back_to_back, takes=pins)

    assert placed.timing == plain.timing  # every start, end, trim and the duration as the take gives them
    got = {c.generated.id: c for c in placed.clips}
    was = {c.generated.id: c for c in plain.clips}
    assert got["line-2"].sha256 == out["line-2"].sha256 != was["line-2"].sha256  # the derived clip is what plays
    assert got["line-2"].placement == was["line-2"].placement  # in the take's window, at the take's level


def test_a_take_for_a_line_not_declared_is_refused(tmp_path):
    iv = stressed_interview()
    pins, ears = pins_and_ears(tmp_path, iv)
    fx = {"squeak": squeak(tmp_path, iv)}
    with pytest.raises(I.InterviewError, match="takes for line-1, not for the lines line-1, line-2"):
        I.place(iv, {**pins, **fx}, back_to_back, takes={"line-1": pins["line-1"]})
