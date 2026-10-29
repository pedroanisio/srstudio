"""The seven Collage sketches as data: each is cast from the Collage cast with the shared voices, staged on known
sets, opens on a question, holds a silent beat of at least 1.2 s before its button, and lands a zoom and a sting;
the shared build's helpers (timing, prop spans, effects, staging checks) are tested on them (ADR 0026)."""

import importlib
import sys
from dataclasses import replace
from pathlib import Path

import pytest
from sr_core.scene import Scene

from srstudio import Canvas, collage, collage_sets, flat_counter, sketch
from srstudio.canvas import Signature

EPISODES = Path(__file__).resolve().parent.parent / "episodes"
NAMES = (
    "brand_refresh",
    "book_report",
    "first_date",
    "the_lore",
    "gritty_reboot",
    "breaking_news",
    "therapy_session",
    "the_will",
    "intervention",
    "goldfish_funeral",
    "thought_leader",
    "final_broadcast",
)


@pytest.fixture(scope="module")
def mods():
    sys.path.insert(0, str(EPISODES))
    try:
        builder = importlib.import_module("_collage_sketch")
        return builder, {n: importlib.import_module(f"{n}_data") for n in NAMES}
    finally:
        sys.path.pop(0)


def test_the_sketches_are_distinct_and_checked(mods):
    builder, data = mods
    slugs = [d.STAGING.sketch.slug for d in data.values()]
    assert len(set(slugs)) == len(NAMES) and all(s == n.replace("_", "-") for s, n in zip(slugs, NAMES, strict=True))
    seeds = [d.STAGING.seed for d in data.values()]
    assert len(set(seeds)) == len(NAMES)
    for d in data.values():
        builder.check_staging(d.STAGING)


@pytest.mark.parametrize("name", NAMES)
def test_each_sketch_has_the_comic_beats(mods, name):
    builder, data = mods
    sk = data[name].STAGING.sketch
    assert sk.lines[0].text.endswith("?")  # the hook is a question
    assert 11 <= sk.end <= 35
    assert sketch.events(sk.beats, "zoom") and sketch.events(sk.beats, "sting")
    last_spoken = max(i for i, b in enumerate(sk.beats) if b.line is not None)
    silent = [(b, nxt) for b, nxt in zip(sk.beats, sk.beats[1:], strict=False) if b.line is None and b.caption == ""]
    assert any(nxt.start - b.start >= 1.0 for b, nxt in silent)  # an awkward pause with no caption
    assert sk.beats[last_spoken].line == len(sk.lines) - 1  # the button is the last line


def test_every_character_keeps_one_voice_across_episodes(mods):
    builder, data = mods
    ids = {}
    for d in data.values():
        for s in d.STAGING.sketch.speakers:
            assert s is builder.SPEAKERS[s.name]
            ids.setdefault(s.voice.id, set()).add(s.name)
    assert all(len(names) == 1 for names in ids.values())
    assert set(builder.SPEAKERS) == set(collage.LOOKS) == set(builder.TINTS)


def test_staging_refuses_another_cast_an_unknown_set_or_event(mods):
    builder, data = mods
    st = data["the_lore"].STAGING
    with pytest.raises(builder.StagingError, match="Collage cast"):
        builder.check_staging(replace(st, sketch=replace(st.sketch, cast=sketch.TOON_CAST)))
    with pytest.raises(builder.StagingError, match="no set"):
        builder.check_staging(replace(st, sets={"gary": "living-room"}))
    with pytest.raises(builder.StagingError, match="unknown sets"):
        builder.check_staging(replace(st, sets={"gary": "moon", "kai": "living-room"}))
    beats = list(st.sketch.beats)
    beats[0] = replace(beats[0], event="explode")
    with pytest.raises(builder.StagingError, match="unknown events"):
        builder.check_staging(replace(st, sketch=replace(st.sketch, beats=tuple(beats))))


def test_timed_beats_and_prop_spans(mods):
    builder, _ = mods
    lines = (sketch.Line("gary", "Hi?"), sketch.Line("kai", "No."))
    beats, end = builder.timed(
        lines,
        (
            (1.0, "gary", 0, "open", "flat", "down"),
            (1.5, "kai", "", "half", "flat", "down", "reveal"),
            (1.0, "kai", 1, "half", "flat", "down"),
        ),
        tail=1.0,
    )
    assert [(b.start, b.who, b.line, b.event) for b in beats] == [
        (0.0, "gary", 0, ""),
        (1.0, "kai", None, "reveal"),
        (2.5, "kai", 1, ""),
    ]
    assert end == 3.5
    kai = sketch.appearances(beats, end)[1]
    assert builder.until(beats, "reveal", kai, before=False) == [(1.0, 3.5)]
    assert builder.until(beats, "reveal", kai, before=True) == []
    assert builder.until(beats, "nothing", kai, before=True) == [(1.0, 3.5)]
    assert builder.until(beats, "nothing", kai, before=False) == []
    assert builder.zooms(beats, kai) == []


def test_sound_effects_follow_the_events(mods, tmp_path):
    builder, data = mods
    sk = data["first_date"].STAGING.sketch
    effects = builder.sound_effects(sk.beats, sk.end, tmp_path, 7)
    assert [e["id"] for e in effects] == ["whoosh", "sting", "beep"]
    assert all((tmp_path / e["audio"]).is_file() for e in effects)
    zoom = sketch.events(sk.beats, "zoom")[0][0]
    assert builder.zooms(sk.beats, next(a for a in sketch.appearances(sk.beats, sk.end) if a.start <= zoom < a.end))


def test_recording_needs_consent(mods, tmp_path):
    builder, data = mods
    with pytest.raises(SystemExit, match="SRSTUDIO_ALLOW_CLOUD"):
        builder.record_episode(data["book_report"].STAGING, tmp_path, {}, "ffmpeg", "note")


TILT_MARGIN = 24.0  # a card turned a few degrees reaches this far past its box


@pytest.mark.parametrize("name", NAMES)
def test_no_prop_covers_the_signature_on_its_set(mods, name, monkeypatch):
    builder, data = mods
    st = data[name].STAGING
    placed: list[tuple[str, tuple[float, float, float, float]]] = []

    def record(kind, box):
        placed.append((kind, box))

    monkeypatch.setattr(
        collage_sets, "sign", lambda cv, parent, text, x, y, w, h, **kw: record(text, (x, y, x + w, y + h))
    )
    monkeypatch.setattr(
        collage_sets, "chart", lambda cv, parent, x, y, w, h, values, *a, **kw: record("chart", (x, y, x + w, y + h))
    )
    monkeypatch.setattr(collage_sets, "tv", lambda cv, parent, x, y, w: record("tv", (x, y, x + w, y + w * 0.66)))
    scene = Scene(version="auto")
    scene.add_project(width=1080, height=1920, fps="24", duration=st.sketch.end, background=collage.PAPER.background)
    cv = Canvas(scene, collage.PAPER, namer=flat_counter("k"), signature=Signature())
    for app in sketch.appearances(st.sketch.beats, st.sketch.end):
        placed.clear()
        g = cv.group(cv.comp, cv.uid("g"))
        st.dress(builder.Shot(cv, app, g, g, st.sketch.beats, st.sketch.end, lambda text, size: 10.0 * len(text)))
        sx0, sy0, sx1, sy1 = collage_sets.signature_box(st.sets[app.who])
        for kind, (x0, y0, x1, y1) in placed:
            m = TILT_MARGIN
            clear = x1 + m <= sx0 or x0 - m >= sx1 or y1 + m <= sy0 or y0 - m >= sy1
            assert clear, (name, app.who, kind)


def test_signature_box_names_a_known_set():
    with pytest.raises(collage.CollageError, match="no set"):
        collage_sets.signature_box("moon")
