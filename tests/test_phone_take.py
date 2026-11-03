"""An interview line heard through a phone: the engine's telephone effect on that line's track, and only on that one."""

from __future__ import annotations

import pytest
from sr_core.scene import Scene

from srstudio import interview
from srstudio.generated import GeneratedError, PlacedClip, Placement
from srstudio.interview import Interview, Schedule, Spoken
from srstudio.song import Singer
from support.generated import SPEECH, write_wav


def _mix():
    scene = Scene(version="auto")
    scene.add_project(width=16, height=16, fps="30", duration=1, background="#000000")
    return scene.add_audioMix()


def _effects(track):
    return [e.type for e in track.find_all("audioEffect")]


def test_a_line_is_not_on_the_phone_unless_it_says_so():
    assert Spoken("a", "Hello.", "Hello.").phone is False
    assert Placement(start=0.0).phone is False


def test_a_phone_placement_plays_through_the_telephone_effect():
    track = Placement(start=0.5, phone=True).track(_mix(), "track-a", "a")
    assert _effects(track) == ["telephone"]


def test_a_plain_placement_adds_no_effect_so_a_built_reel_does_not_change():
    track = Placement(start=0.5).track(_mix(), "track-a", "a")
    assert _effects(track) == []


def test_a_clip_recorded_before_the_field_still_loads():
    body = PlacedClip(SPEECH, "0" * 64, Placement(start=1.0)).to_dict()
    del body["placement"]["phone"]
    assert PlacedClip.from_dict(body).placement.phone is False


def test_a_phone_placement_survives_the_timeline():
    body = PlacedClip(SPEECH, "0" * 64, Placement(start=1.0, phone=True)).to_dict()
    assert PlacedClip.from_dict(body).placement.phone is True


@pytest.mark.parametrize("value", ["yes", 1, None])
def test_phone_is_true_or_false(value):
    with pytest.raises(GeneratedError, match="phone"):
        Placement(start=0.0, phone=value)


def test_place_puts_only_the_phone_line_on_the_phone(tmp_path):
    voice = {"a": Singer("cjVigY5qzO86Huf0OWal", "Eric", dict(stability=0.5, similarity_boost=0.75, style=0.2))}
    lines = [Spoken("a", "One.", "One."), Spoken("a", "Two.", "Two.", phone=True)]
    iv = Interview(
        slug="x",
        title="X",
        seed=1,
        voices=voice,
        lines=lines,
        effects=[],
        voice_note="n",
        room_tone_seed=2,
        reaction_after=0.1,
        reaction_hold=0.1,
        end_card=0.0,
    )
    declared, _ = interview.declarations(iv)
    pins = {}
    for k, item in enumerate(declared):
        wav = write_wav(tmp_path / f"{k}.wav", [0.4] * 9600)
        pins[item.id] = type("Pin", (), {"path": wav, "sha256": "0" * 64})
    placed = interview.place(iv, pins, lambda speech, effects: Schedule([0.1, 1.0], {}))
    assert [c.placement.phone for c in placed.clips] == [False, True]
