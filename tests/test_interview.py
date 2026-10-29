"""An interview episode's audio: the script's checks, its declarations, the schedule's checks, placement, the build."""

from __future__ import annotations

import json
import math
from pathlib import Path

import pytest

from fakes import ffmpeg_required
from srstudio import interview as I
from srstudio.generated import PLACEHOLDER, Resolved, ResolveError, sha256_of
from srstudio.song import Singer
from test_song import engine, fake_env, tone  # noqa: F401  (fake_env is a fixture)

WILL = Singer("bIHbv24MWmeRgasZH58o", "Will", {"stability": 0.4, "similarity_boost": 0.75, "style": 0.2})
ERIC = Singer("cjVigY5qzO86Huf0OWal", "Eric", {"stability": 0.55, "similarity_boost": 0.75, "style": 0.1})


def make(**changes) -> I.Interview:
    kw: dict = dict(
        slug="test-interview",
        title="Test Interview",
        seed=11,
        voices={"manager": ERIC, "candidate": WILL},
        lines=[I.Spoken("manager", "Why here?", "Why here?"), I.Spoken("candidate", "The chair.", "The chair.", 0.95)],
        effects=[I.Sound("squeak", "a chair squeak", seconds=0.8, longest=0.5, peak=0.5)],
        voice_note="test voices",
        room_tone_seed=12,
        reaction_after=0.3,
        reaction_hold=1.0,
        end_card=2.0,
    )
    kw.update(changes)
    return I.Interview(**kw)


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


# -- placement --------------------------------------------------------------------------------------------------
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
def test_build_resolves_hears_places_and_writes_the_dialogue(tmp_path, fake_env):  # noqa: F811
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
def test_build_stops_when_a_line_is_misheard(tmp_path, fake_env):  # noqa: F811
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
