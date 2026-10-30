"""The audio family's numbers are numbers (ADR 0035): a bool is not a second, a gain or a tempo, and NaN is refused
as it always was. Each case feeds ``True`` where the module took ``math.isfinite`` for a number check."""

from __future__ import annotations

import json
from dataclasses import replace

import pytest

from srstudio import compose, dub, foley, music, narration, song, takes
from srstudio import interview as I
from srstudio.cel import Feature
from support.interview import make as interview
from support.song import make_song
from support.takes import BED_PLAN, script

BAD = [True, float("nan")]


@pytest.mark.parametrize("bad", BAD)
@pytest.mark.parametrize(
    "call",
    [
        lambda v: foley.typing_bursts([Feature(0.0, 0.0, 0.0)], threshold=v),
        lambda v: foley.keystrokes([], v),
        lambda v: foley.keystrokes([], 1.0, peak=v),
        lambda v: foley.buzz([], 1.0, length=v),
        lambda v: foley.whoosh([], v),
        lambda v: foley.tones([], 1.0, peak=v),
    ],
)
def test_foley_refuses_a_bool_or_nan_for_a_length_a_level_or_a_threshold(call, bad):
    with pytest.raises(foley.FoleyError):
        call(bad)


@pytest.mark.parametrize("bad", BAD)
@pytest.mark.parametrize(
    "call",
    [
        lambda v: music.Groove(bpm=120, offset=v),
        lambda v: dub.beat_offset(phase=0.0, bpm=120, at=1.0, near=v),
        lambda v: dub.beat_offset(phase=0.0, bpm=v, at=1.0),
        lambda v: compose.Chunk("intro", v, ("lo-fi",)),
        lambda v: narration.schedule([{"id": "01", "duration": v}]),
    ],
)
def test_music_dubbing_composing_and_scheduling_refuse_a_bool_or_nan(call, bad):
    with pytest.raises((music.MusicError, dub.DubError, compose.ComposeError, narration.NarrationError)):
        call(bad)


def test_a_narration_manifest_whose_duration_is_true_is_refused(tmp_path):
    (tmp_path / "narration.json").write_text(json.dumps({"duration": True, "items": [], "effects": []}))
    with pytest.raises(narration.NarrationError, match="positive number of seconds, got True"):
        narration.manifest_duration(tmp_path / "narration.json")


def test_songs_takes_and_interviews_refuse_a_bool_for_seconds():
    with pytest.raises(song.SongError, match="lines_end"):
        make_song(lines_end=True)
    base = make_song().effects[0]
    with pytest.raises(song.SongError, match="early"):
        make_song(effects=[replace(base, early=True)])
    with pytest.raises(I.InterviewError, match="reaction_hold"):
        interview(reaction_hold=True)


@pytest.mark.parametrize(
    "change",
    [
        lambda ts: (replace(ts[0], hold=True), *ts[1:]),
        lambda ts: (*ts[:2], replace(ts[2], seconds=True)),
        lambda ts: (*ts[:2], replace(ts[2], longest=True)),
    ],
)
def test_a_take_with_a_bool_for_seconds_fails_its_check(change):
    with pytest.raises(takes.TakesError):
        script(takes=change(script().takes)).check()


@pytest.mark.parametrize("field", ["bpm", "gain_db", "fade"])
def test_a_music_bed_with_a_bool_fails_its_check(field):
    with pytest.raises(takes.TakesError, match="bed"):
        script(bed=replace(takes.Bed(BED_PLAN, 11, 96, gain_db=-12.0), **{field: True})).check()


@pytest.mark.parametrize("field", ["seconds", "longest"])
def test_an_interview_effect_with_a_bool_for_seconds_is_refused(field):
    base = interview().effects[0]
    with pytest.raises(I.InterviewError, match=field):
        interview(effects=[replace(base, **{field: True})])


@pytest.mark.parametrize("kw", [{"lag_max": True}, {"guard": True}, {"tail": True}, {"speeches": [True]}])
def test_relaxed_narration_refuses_a_bool_for_a_length(kw):
    plan = [narration.Slot("01", "a", False, start=0.0, end=2.0)]
    with pytest.raises(narration.NarrationError):
        narration.plan_relaxed(plan, kw.pop("speeches", [1.0]), **kw)
