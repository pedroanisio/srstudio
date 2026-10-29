"""The Saga episode harness (episodes/_saga.py) is a srstudio.series Series: Saga's style, voices, bed and reel
builder, and the house caption look with no lone word on a caption's last line (ADR 0025, ADR 0031)."""

from __future__ import annotations

import dataclasses
import importlib
import sys
from pathlib import Path

import pytest

from srstudio import SAGA, native, saga_reel, series
from srstudio.timeline import Take

EPISODES = Path(__file__).resolve().parent.parent / "episodes"


@pytest.fixture(scope="module")
def harness():
    sys.path.insert(0, str(EPISODES))
    try:
        yield importlib.import_module("_saga"), importlib.import_module("saga_known_issue_audio").REEL
    finally:
        sys.path.remove(str(EPISODES))


def test_the_saga_series_draws_in_saga_with_the_saga_reel_builder_and_its_music_bed(harness):
    saga, reel = harness
    assert isinstance(reel, series.Reel) and reel.series is saga.SERIES
    assert saga.SERIES.style is SAGA
    assert saga.SERIES.stage is saga_reel.build
    assert saga.SERIES.bed is saga.BED and saga.BED.gain_db == saga_reel.MUSIC_GAIN
    assert saga.line is series.line and saga.word_at is series.word_at


def test_saga_reels_caption_without_a_lone_last_word_unless_a_reel_names_its_own_look(harness):
    saga, reel = harness
    assert reel.captions is None
    assert reel.look() is saga.SERIES.captions
    assert (saga.SERIES.captions.min_last, saga.SERIES.captions.min_seconds) == (2, 0.84)
    plain = dataclasses.replace(saga.SERIES.captions, min_last=1, min_seconds=0.0)
    assert plain == native.CAPTION_LOOK  # only the orphans and the hold change
    look = native.CaptionLook(min_last=3)
    assert dataclasses.replace(reel, captions=look).look() is look


def test_the_script_names_the_saga_voices_it_uses(harness):
    saga, reel = harness
    script = reel.script()
    assert set(script.voices) <= set(saga.VOICES)
    assert script.bed is saga.BED and script.font == saga.FONT


REELS = sorted(p.stem.removeprefix("saga_").removesuffix("_audio") for p in EPISODES.glob("saga_*_audio.py"))


def timed(text: str) -> tuple[dict, ...]:
    return tuple({"text": w, "start": 0.1 + i * 0.3, "end": 0.35 + i * 0.3} for i, w in enumerate(text.split()))


@pytest.mark.parametrize("name", REELS)
def test_every_saga_line_is_captioned_readably_and_without_a_lone_last_word_where_a_split_allows(harness, name):
    reel = importlib.import_module(f"saga_{name}_audio").REEL
    look = reel.look()
    spoken = [
        Take(t.id, t.actor, "", t.text, 10.0 * i, 9.0, words=timed(t.text))
        for i, t in enumerate(reel.takes)
        if not t.is_effect
    ]
    whole = {t.text for t in spoken}
    for cue in native.cues_from_takes(spoken, look):
        lines = native.wrap(cue.text, look.max_chars, look.max_words)
        assert len(lines) <= look.max_lines
        assert len(lines) == 1 or len(lines[-1].split()) >= look.min_last or cue.text in whole, cue.text
        assert cue.end - cue.start >= look.min_seconds - 1e-9, cue.text
