"""An interview episode's audio: the script's checks, its declarations, the schedule's checks, placement, the build."""

from __future__ import annotations

import json
import math
from dataclasses import fields, replace
from pathlib import Path

import pytest

from fakes import ffmpeg_required
from srstudio import interview as I
from srstudio import sketch
from srstudio.errors import MissingKeyError
from srstudio.generated import PLACEHOLDER, Resolved, ResolveError, sha256_of
from srstudio.provider import parse_voice
from srstudio.timeline import Phrase
from srstudio.voice import ElevenLabsClient, parse_transcript
from support.interview import ERIC, WILL, make
from support.song import engine, tone


def back_to_back(speech, effect) -> I.Schedule:
    """Each line 0.3 s after the last; the squeak in the first gap."""
    starts, cursor = [], 0.5
    for length in speech:
        starts.append(cursor)
        cursor += length + 0.3
    return I.Schedule(starts, {"squeak": starts[0] + speech[0] + 0.05})


def pins_for(tmp_path: Path, iv: I.Interview, speech: list[float]) -> dict[str, Resolved]:
    lines, effects = I.declarations(iv)
    out = {}
    for item, seconds in zip(lines, speech, strict=True):
        p = tone(tmp_path / f"{item.id}.wav", seconds)
        out[item.id] = Resolved(item, p, sha256_of(p))
    for item in effects:
        p = tone(tmp_path / f"{item.id}.wav", 0.2, lead=0.02)
        out[item.id] = Resolved(item, p, sha256_of(p))
    return out


# -- the script -------------------------------------------------------------------------------------------------
@pytest.mark.parametrize(
    "changes, match",
    [
        (dict(lines=[]), "at least one line"),
        (dict(lines=[I.Spoken("boss", "Hi.", "Hi.")]), "no voice for role 'boss'"),
        (dict(voices={"manager": ERIC, "candidate": WILL, "extra": WILL}), "never speaks"),
        (dict(lines=[I.Spoken("manager", " ", "x"), I.Spoken("candidate", "Hi.", "Hi.")]), "no text"),
        (dict(lines=[I.Spoken("manager", "Hi.", "Hi.", 1.5), I.Spoken("candidate", "Hi.", "Hi.")]), "speed"),
        (dict(effects=[make().effects[0], make().effects[0]]), "unique"),
        (dict(effects=[I.Sound("line-1", "x", 1.0, 0.5, 0.5)]), "line-"),
        (dict(effects=[I.Sound("fx", "x", 1.0, 1.5, 0.5)]), "longest"),
        (dict(effects=[I.Sound("fx", "x", 1.0, 0.5, 1.5)]), "peak"),
        (dict(effects=[I.Sound("fx", "x", 0.4, 0.3, 0.5)]), r"seconds 0\.4 must lie in \(0\.5, 22\.0\)"),
        (dict(effects=[I.Sound("fx", "x", 22.5, 0.5, 0.5)]), r"seconds 22\.5 must lie in \(0\.5, 22\.0\)"),
        (dict(effects=[I.Sound("fx", "x", float("nan"), 0.5, 0.5)]), "seconds nan must lie in"),
        (dict(lines=[I.Spoken("manager", "Hi.", "Hi.", gain=1.0), I.Spoken("candidate", "Hi.", "Hi.")]), "gain"),
        (dict(lines=[I.Spoken("manager", "Hi.", "Hi.", gain=-13.0), I.Spoken("candidate", "Hi.", "Hi.")]), "gain"),
        (
            dict(lines=[I.Spoken("manager", "Hi.", "Hi.", gain=float("nan")), I.Spoken("candidate", "Hi.", "Hi.")]),
            "gain",
        ),
        (dict(reaction_hold=-1.0), "reaction_hold"),
        (dict(end_card=float("nan")), "end_card"),
    ],
)
def test_a_script_the_build_cannot_use_is_refused_when_made(changes, match):
    with pytest.raises(I.InterviewError, match=match):
        make(**changes)


def test_declarations_name_every_line_and_effect_and_pin_the_voice():
    lines, effects = I.declarations(make(effects=[I.Sound("squeak", "x", 0.8, 0.5, 0.5, seed=99)]))
    assert [g.id for g in lines] == ["line-1", "line-2"] and [g.id for g in effects] == ["squeak"]
    assert lines[1].voice.startswith(WILL.id) and "speed=0.95" in lines[1].voice and lines[0].seed == 11
    assert effects[0].seed == 99 and I.declarations(make())[1][0].seed is None
    assert lines[0].license.endswith("Eric")


def test_a_line_sits_at_its_own_level_without_asking_for_a_new_take(tmp_path):
    plain = make(lines=[I.Spoken("manager", "Why here?", "Why here?"), I.Spoken("candidate", "The chair.", "x")])
    quiet = make(
        lines=[I.Spoken("manager", "Why here?", "Why here?"), I.Spoken("candidate", "The chair.", "x", level=-6)]
    )
    assert I.declarations(plain) == I.declarations(quiet)
    before = I.place(plain, pins_for(tmp_path, plain, [1.0, 0.8]), back_to_back)
    after = I.place(quiet, pins_for(tmp_path, quiet, [1.0, 0.8]), back_to_back)
    gains = [[clip.placement.gain_db for clip in placed.clips] for placed in (before, after)]
    assert gains[1][0] == gains[0][0] and gains[1][1] == pytest.approx(gains[0][1] - 6)
    starts = [[clip.placement.start for clip in placed.clips] for placed in (before, after)]
    assert starts[0] == starts[1]


@pytest.mark.parametrize("level", [0.5, -12.5, float("nan"), float("inf")])
def test_a_level_outside_the_mix_is_refused_when_made(level):
    with pytest.raises(I.InterviewError, match="level"):
        make(lines=[I.Spoken("manager", "Hi.", "Hi.", level=level), I.Spoken("candidate", "Hi.", "Hi.")])


def test_a_line_may_carry_its_own_seed_so_only_its_take_is_requested_again():
    """A re-take changes one line's request: its own seed; every other line keeps the interview's."""
    retake = make(
        lines=[I.Spoken("manager", "Why here?", "Why here?"), I.Spoken("candidate", "The chair.", "x", seed=7)]
    )
    before, after = I.declarations(make())[0], I.declarations(retake)[0]
    assert [g.seed for g in after] == [11, 7] and before[0] == after[0] and before[1].seed == 11


@pytest.mark.parametrize("seed", [-1, True, 1.5, 2**32])
def test_a_line_seed_is_a_whole_number_the_provider_accepts(seed):
    with pytest.raises(I.InterviewError, match="line 1: seed"):
        make(lines=[I.Spoken("manager", "Why here?", "Why here?", seed=seed)], voices={"manager": ERIC})


def test_heard_reaches_only_its_own_line_and_leaves_the_other_requests_unchanged():
    lines = [I.Spoken("manager", "Why here?", "Why here?"), I.Spoken("candidate", "S-R.", "S-R.", 0.95, heard=("SAR",))]
    before, after = I.declarations(make())[0], I.declarations(make(lines=lines))[0]
    assert after[0] == before[0] and parse_voice(after[0].voice).heard == ()
    assert parse_voice(after[1].voice).heard == ("SAR",) and after[1].voice.startswith(before[1].voice + "&")


@pytest.mark.parametrize("heard", [("",), (" ",), (1028,), "SAR", ["SAR"]])
def test_a_hearing_is_a_tuple_of_non_empty_strings(heard):
    with pytest.raises(I.InterviewError, match="line 1: heard"):
        make(lines=[I.Spoken("manager", "S-R.", "S-R.", heard=heard)], voices={"manager": ERIC})


def transcript_of(text: str):
    return parse_transcript({"language_code": "en", "language_probability": 1.0, "text": text, "words": []})


def test_the_hearing_check_accepts_a_line_s_own_approval_and_nothing_else(tmp_path):
    lines = [I.Spoken("manager", "S-R.", "S-R.", heard=("SAR",)), I.Spoken("candidate", "S-R.", "S-R.")]
    iv = make(lines=lines)
    pins = {g.id: Resolved(g, tmp_path / f"{g.id}.wav", "0" * 64) for g in I.declarations(iv)[0]}
    said = {"line-1": "SAR", "line-2": "SAR"}
    report, failures = I.hear(iv, pins, lambda path: transcript_of(said[path.stem]))
    assert len(failures) == 1 and "S-R." in failures[0]  # the approval is line 1's alone
    assert report["lines"][0]["accepted"] == ["SAR"] and "accepted" not in report["lines"][1]
    said["line-1"] = "SAR 1028"
    assert len(I.hear(iv, pins, lambda path: transcript_of(said[path.stem]))[1]) == 2  # an unlisted hearing


# -- placement --------------------------------------------------------------------------------------------------


def heard_take(root: Path, line: int, words: list[tuple[str, float, float]]) -> None:
    """``line``'s pinned take and the transcript ``hear`` cached for it, as a build leaves them."""
    take = root / "assets" / "generated" / f"line-{line}.wav"
    take.parent.mkdir(parents=True)
    take.write_bytes(f"take {line}".encode())
    said = [{"text": w, "start": a, "end": b, "type": "word"} for w, a, b in words]
    body = {"language_code": "en", "language_probability": 1.0, "text": " ".join(w for w, *_ in words), "words": said}
    ElevenLabsClient(root / "assets" / "elevenlabs", key="k", multipart_transport=lambda *a: (body, "r")).transcribe(
        take
    )


SAID = Phrase(index=0, role="manager", text="Has this always been here?", caption="", start=0.8, end=1.84,
              trim_seconds=0.05)  # fmt: skip


def test_a_word_is_placed_on_the_episode_clock_from_the_cached_hearing_without_a_key(tmp_path):
    heard_take(tmp_path, 1, [("Has", 0.1, 0.2), ("this", 0.24, 0.36), ("always", 0.44, 0.66), ("this.", 0.9, 1.0)])
    assert I.said(tmp_path, SAID, "this") == pytest.approx(0.8 + 0.24 - 0.05)
    assert I.said(tmp_path, SAID, "This", which=1) == pytest.approx(0.8 + 0.9 - 0.05)  # its reading, not its spelling


@pytest.mark.parametrize(
    "word, which, match",
    [
        ("chair", 0, "not heard"),
        ("this", 2, "not heard"),
        ("this", -1, "which"),
        ("", 0, "word"),
        ("always", 0, "outside"),
    ],
)
def test_a_word_the_take_does_not_say_or_says_outside_its_phrase_is_refused(tmp_path, word, which, match):
    heard_take(tmp_path, 1, [("this", 0.24, 0.36), ("this", 0.5, 0.6), ("always", 1.5, 1.7)])  # past the phrase's end
    with pytest.raises(I.InterviewError, match=match):
        I.said(tmp_path, SAID, word, which=which)


def test_a_take_never_heard_is_refused_without_a_request(tmp_path):
    (tmp_path / "assets" / "generated").mkdir(parents=True)
    (tmp_path / "assets" / "generated" / "line-1.wav").write_bytes(b"never heard")
    with pytest.raises(MissingKeyError):
        I.said(tmp_path, SAID, "this")


def test_a_lines_gain_sits_it_under_the_others_in_the_mix(tmp_path):
    iv = make()
    plain = I.place(iv, pins_for(tmp_path, iv, [1.0, 0.8]), back_to_back).clips
    quiet = replace(iv.lines[1], gain=-6.0)
    lowered = replace(iv, lines=[iv.lines[0], quiet, *iv.lines[2:]])
    mixed = I.place(lowered, pins_for(tmp_path, lowered, [1.0, 0.8]), back_to_back).clips
    assert mixed[0].placement.gain_db == plain[0].placement.gain_db
    assert mixed[1].placement.gain_db == pytest.approx(plain[1].placement.gain_db - 6.0)
    assert I.declarations(lowered)[0] == I.declarations(iv)[0]  # the take stays the same


def test_lines_and_effects_land_where_the_schedule_puts_them(tmp_path):
    iv = make()
    placed = I.place(iv, pins_for(tmp_path, iv, [1.0, 0.8]), back_to_back)
    t = placed.timing
    first = t.phrases[0]["end"] - t.phrases[0]["start"]  # the trimmed clip: the tone plus the trim's lead and tail
    assert first == pytest.approx(1.0, abs=0.1)
    assert [p["start"] for p in t.phrases] == pytest.approx([0.5, 0.5 + first + 0.3], abs=1e-6)
    assert t.last_end == pytest.approx(t.phrases[1]["end"], abs=1e-6)
    assert t.reaction == pytest.approx(t.last_end + 0.3) and t.ending == pytest.approx(t.reaction + 1.0)
    assert t.duration == math.ceil((t.ending + 2.0) * I.FPS) / I.FPS
    assert t.effects == {"squeak": pytest.approx(0.5 + first + 0.05)}
    assert [c.generated.id for c in placed.clips] == ["line-1", "line-2", "squeak"]
    assert {c.placement.role for c in placed.clips} == {"dialogue", "effects"}
    assert [e["name"] for e in placed.sound_effects] == ["squeak"]


@pytest.mark.parametrize("gain", [float("nan"), -30.0, 3.0, "quiet", None])
def test_a_line_s_gain_is_a_drop_the_mix_can_play(gain):
    with pytest.raises(I.InterviewError, match="gain must be"):
        make(lines=[I.Spoken("manager", "A short line.", "A short line.", gain=gain)])


def test_a_quiet_line_drops_alone_and_leaves_the_level_of_the_others(tmp_path):
    loud = make(lines=[I.Spoken("manager", "One.", "One."), I.Spoken("candidate", "Two.", "Two.")])
    quiet = make(lines=[I.Spoken("manager", "One.", "One."), I.Spoken("candidate", "Two.", "Two.", gain=-12.0)])
    pins = pins_for(tmp_path, loud, [1.0, 1.0])
    level = [c.placement.gain_db for c in I.place(loud, pins, back_to_back).clips]
    dropped = [c.placement.gain_db for c in I.place(quiet, pins, back_to_back).clips]
    assert dropped[0] == level[0]
    assert dropped[1] == pytest.approx(level[1] - 12.0)
    assert dropped[2] == level[2]  # the effect is not a line


@pytest.mark.parametrize(
    "schedule, match",
    [
        (lambda s, e: I.Schedule([0.5], {"squeak": 0.1}), "2 lines"),
        (lambda s, e: I.Schedule([0.5, 1.0], {"squeak": 3.0}), "line 1 'Why here\\?' runs to"),
        (lambda s, e: I.Schedule([0.5, 3.0], {}), "squeak"),
        (lambda s, e: I.Schedule([0.5, 3.0], {"squeak": 1.6, "door": 0.0}), "door"),
        (lambda s, e: I.Schedule([-0.5, 3.0], {"squeak": 1.6}), "negative"),
        (lambda s, e: I.Schedule([0.5, 3.0], {"squeak": 60.0}), "after the end"),
    ],
)
def test_a_schedule_that_overlaps_or_misses_an_item_stops_the_build(tmp_path, schedule, match):
    iv = make()
    with pytest.raises(I.InterviewError, match=match):
        I.place(iv, pins_for(tmp_path, iv, [1.0, 0.8]), schedule)


def test_a_near_silent_line_stops_the_build_instead_of_being_boosted(tmp_path):
    iv = make()
    pins = pins_for(tmp_path, iv, [1.0, 0.8])
    for item in I.declarations(iv)[0]:
        whisper = tone(tmp_path / f"quiet-{item.id}.wav", 0.4, amplitude=0.02)
        pins[item.id] = Resolved(item, whisper, sha256_of(whisper))
    with pytest.raises(I.InterviewError, match="near-silent"):
        I.place(iv, pins, back_to_back)


# -- the build, through the engine and a fake ElevenLabs ---------------------------------------------------------
@ffmpeg_required
def test_build_resolves_hears_places_and_writes_the_dialogue(tmp_path, fake_env):
    iv = make(lines=[I.Spoken("manager", "Sit down.", "Sit down."), I.Spoken("candidate", "Sit down.", "Sit.")])
    root = tmp_path / "project"
    out = I.build(
        iv,
        root,
        engine=engine(),
        key="sk-test",
        env=fake_env,
        schedule=back_to_back,
        extra=lambda t: {"reaction_start": t.reaction, "squeak_start": t.effects["squeak"]},
    )
    data = json.loads(out.read_text())
    assert out == root / "dialogue.json" and list(data)[:9] == [
        "title",
        "language",
        "tts_engine",
        "model",
        "voice_note",
        "duration",
        "phrases",
        "sound_effects",
        "clips",
    ]
    assert data["squeak_start"] > data["phrases"][0]["end"] and data["reaction_start"] > data["phrases"][1]["end"]
    assert all(c["sha256"] != PLACEHOLDER for c in data["clips"]) and len(data["clips"]) == 3
    assert (root / "assets" / "room-tone.wav").exists() and (root / "assets" / "DejaVuSans-Bold.ttf").exists()
    heard = json.loads((root / "voice-transcript.json").read_text())
    assert heard["passed"] is True and {"role", "expected", "heard", "language_code"} <= set(heard["lines"][0])
    assert "sk-test" not in out.read_text() and "sk-test" not in (root / "test-interview.audio.scene.xml").read_text()


@ffmpeg_required
def test_build_stops_when_a_line_is_misheard(tmp_path, fake_env):
    iv = make(lines=[I.Spoken("manager", "Sit down.", "x"), I.Spoken("candidate", "Sit down.", "x")], effects=[])
    root = tmp_path / "project"
    with pytest.raises(ResolveError, match="heard"):
        I.build(
            iv,
            root,
            engine=engine(),
            key="sk-test",
            env={**fake_env, "FAKE_HEARD": "Sit town."},
            schedule=lambda s, e: I.Schedule([0.5, 2.0], {}),
        )
    assert not (root / "dialogue.json").exists()


def test_main_needs_an_engine(tmp_path, monkeypatch):
    monkeypatch.delenv("SRSTUDIO_ENGINE", raising=False)
    monkeypatch.setenv("PATH", str(tmp_path))
    with pytest.raises(SystemExit, match="no scene-render engine"):
        I.main(make(), back_to_back, argv=[str(tmp_path / "p")])


def test_five_years_times_its_reaction_and_end_card_from_the_published_rounded_line_end():
    """Five Years was published before the interview pipeline (frozen): its beats follow the last line's end as
    written to the microsecond, not the unrounded sum the pipeline carries in ``Timing.last_end``."""
    import importlib
    import sys

    sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "episodes"))
    try:
        five_years = importlib.import_module("five_years_audio")
    finally:
        sys.path.pop(0)
    spans = [(0.62, 2.124), (2.424, 3.370146), (3.710146, 4.895646), (5.865646, 6.956708)]  # published phrases
    last_end = 6.956708499999999  # start + recorded length, before rounding
    t = I.Timing(
        phrases=[{"start": a, "end": b} for a, b in spans],
        effects={"chair-squeak": 0.14, "chair-squeak-loud": 5.155646, "swivel-spin": 8.486708},
        last_end=last_end,
        reaction=last_end + 0.38,
        ending=last_end + 0.38 + 1.05,
        duration=11.0,
    )
    fields = five_years.extra(t)
    assert (fields["reaction_start"], fields["end_card_start"]) == (7.336708, 8.386708)
    cuts = {c["angle"]: c["time"] for c in fields["camera_cuts"]}
    assert (cuts["manager-reaction"], cuts["candidate-ending"]) == (7.336708, 8.386708)


def test_a_spoken_line_and_a_sketch_line_share_one_gain_field_in_db():
    """One name and one unit on both: a second level field beside it is how two scales came to sit side by side."""
    for kind in (I.Spoken, sketch.Line):
        names = {f.name for f in fields(kind)}
        assert "gain" in names and not names & {"level", "level_db"}
    assert I.LEVELS == sketch.LINE_LEVELS == (-12.0, 0.0)
def test_beats_lays_lines_end_to_end_with_their_gaps():
    schedule = I.beats([1.0, 2.0, 0.5], 0.5, [0.25, 1.5])
    assert schedule.lines == pytest.approx([0.5, 1.75, 5.25])
    assert schedule.effects == {}


def test_a_slow_take_moves_every_line_after_it():
    fast, slow = I.beats([1.0, 1.0, 1.0], 0.0, [0.5, 0.5]), I.beats([1.0, 1.5, 1.0], 0.0, [0.5, 0.5])
    assert slow.lines[1] == fast.lines[1] and slow.lines[2] == fast.lines[2] + 0.5


@pytest.mark.parametrize(
    ("start", "gaps", "match"),
    [
        (0.0, [0.1], "2 gaps between them, got 1"),
        (0.0, [0.1, 0.1, 0.1], "2 gaps between them, got 3"),
        (-0.1, [0.1, 0.1], "non-negative seconds"),
        (0.0, [0.1, -0.1], "non-negative seconds"),
        (float("nan"), [0.1, 0.1], "non-negative seconds"),
    ],
)
def test_beats_refuses_a_column_that_does_not_add_up(start, gaps, match):
    with pytest.raises(I.InterviewError, match=match):
        I.beats([1.0, 1.0, 1.0], start, gaps)


def test_a_chain_of_beats_reads_as_a_column_of_offsets():
    assert I.chain(10.0, book=0.0, snore=0.5, wave=2.0) == {"book": 10.0, "snore": 10.5, "wave": 12.5}


@pytest.mark.parametrize(
    ("start", "gaps"),
    [(float("nan"), {"a": 1.0}), (-1.0, {"a": 1.0}), (1.0, {"a": -0.1}), (1.0, {"a": float("inf")}), (1.0, {})],
)
def test_a_chain_refuses_what_is_not_a_time(start, gaps):
    with pytest.raises(I.InterviewError):
        I.chain(start, **gaps)
