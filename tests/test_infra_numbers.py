"""The infrastructure's numbers are numbers (ADR 0035): each case feeds ``True`` where a module took
``math.isfinite`` (or ``isinstance(int | float)``) for a number check, which takes a bool as 1."""

from __future__ import annotations

from dataclasses import replace

import pytest

from srstudio import Episode, craft, native, sketch
from srstudio.errors import SrstudioError
from srstudio.generated import Generated, Placement
from srstudio.layout import Box
from srstudio.native import CaptionLook, Cue
from srstudio.voice import Alignment, ElevenLabsClient
from support.audio import spec
from support.generated import SQUEAK
from support.native import canvas as native_canvas
from support.native import shots
from support.sketch import SK, with_beats
from support.voice import Binary


def captions(cues):
    scene, cv, _ = native_canvas()
    native.caption_track(scene, cues, font_asset=cv.font_asset, safe_area=None, width=1080, height=1920)


def transition(**kw):
    _, cv, _ = native_canvas()
    native.transition(shots(cv), "shot-a", "shot-b", "crossfade", **kw)


AL = Alignment(tuple("Pop"), (0.1, 0.2, 0.3), (0.2, 0.3, 0.4))


@pytest.mark.parametrize(
    "call",
    [
        lambda: craft.pauses([], threshold=True),
        lambda: Box(True, 0.0, 10.0, 10.0),
        lambda: sketch.check(with_beats(lambda b: [*b[:1], replace(b[1], start=True), *b[2:]])),
        lambda: sketch.check(replace(SK, end=True)),
        lambda: sketch.visemes(AL, at=True, clip_in=0.1, kept=0.3),
        lambda: sketch.visemes(AL, at=0.0, clip_in=True, kept=0.3),
        lambda: sketch.visemes(AL, at=0.0, clip_in=0.1, kept=True),
        lambda: Generated(**{**SQUEAK.__dict__, "duration": True}),
        lambda: Placement(start=True),
        lambda: Placement(start=0.0, fade_in=True),
        lambda: Placement(start=0.0, gain_db=True),
        lambda: Placement(start=0.0, clip_out=True),
        lambda: CaptionLook(size=True),
        lambda: CaptionLook(stroke_width=True),
        lambda: CaptionLook(min_seconds=True),
        lambda: captions([Cue(True, 1.5, "a")]),
        lambda: transition(duration=True),
    ],
)
def test_a_bool_is_not_a_second_a_size_or_a_level(call):
    with pytest.raises(SrstudioError):
        call()


def test_a_caption_lead_is_not_a_bool(project):
    with pytest.raises(SrstudioError, match="caption lead"):
        Episode(spec(project)).default_captions(lead=True)


def test_a_sound_effect_length_is_not_a_bool(tmp_path):
    client = ElevenLabsClient(tmp_path, key="k", binary_transport=Binary(b"x"))
    with pytest.raises(ValueError, match="seconds"):
        client.sound_effect("thud", True)
    with pytest.raises(ValueError, match="prompt_influence"):
        client.sound_effect("thud", 1.0, prompt_influence=True)
