"""Whose Milk? as data: the hook, the note on the fridge that follows the milk, the hold before the punchline, and
the dressing of the kitchen shots (the shared Toon build is tested in test_toon_sketches.py)."""

import sys
import xml.etree.ElementTree as ET
from dataclasses import replace
from pathlib import Path

import pytest
from sr_core.scene import Scene

from srstudio import PEACH, Canvas, flat_counter, sketch, toon, toon_sets

EPISODES = Path(__file__).resolve().parent.parent / "episodes"


@pytest.fixture(scope="module")
def mods():
    sys.path.insert(0, str(EPISODES))
    try:
        import whose_milk_data
        from srstudio import toon_sketch

        return toon_sketch, whose_milk_data
    finally:
        sys.path.pop(0)


def canvas(duration: float) -> Canvas:
    scene = Scene(version="auto")
    scene.add_project(width=1080, height=1920, fps="24", duration=duration, background=PEACH.background)
    return Canvas(scene, PEACH, font_asset="comic-neue", namer=flat_counter("k"))


def test_the_sketch_hooks_on_a_question_and_holds_before_its_punchline(mods):
    _, data = mods
    data.validate()
    sk = data.SKETCH
    assert sk.lines[0].text.endswith("?") and sk.beats[0].start == 0 and sk.beats[1].start <= 2.5
    assert len({s.voice.id for s in sk.speakers}) == 2
    apps = sketch.appearances(sk.beats, sk.end)
    assert {a.who for a in apps} == {"frog", "dog"} and len(apps) >= 6
    spoken = [b for b in sk.beats if b.spoken]
    last, before = sk.beats.index(spoken[-1]), sk.beats.index(spoken[-2])
    assert spoken[-1].start - sk.beats[before + 1].start >= 1.2 and last - before >= 2
    assert any(b.event == "hangup" and b.start > spoken[-1].start for b in sk.beats)
    assert sk.end - sk.beats[-1].start >= sketch.TAIL_AFTER_LAST
    assert toon.parse_script(sketch.cues(sk.beats, sk.end, sk.lines))


def test_the_note_escalates_from_the_milk_to_the_yogurt(mods):
    _, data = mods
    beats = data.SKETCH.beats
    assert [text for _, text in data.notes_by_time(beats)] == ["WHOSE MILK?", "IT MOVED.", "WHOSE YOGURT?"]
    assert data.note_at(beats, 0.0) == "WHOSE MILK?" and data.note_at(beats, 30.0) == "WHOSE YOGURT?"
    # a shot that spans a new note shows the old one until it is written, then the new one
    at = data.notes_by_time(beats)[-1][0]
    assert data.note_spans(beats, at - 1, at + 1) == [(at - 1, at, "IT MOVED."), (at, at + 1, "WHOSE YOGURT?")]
    assert data.note_spans(beats, 0.0, 1.0) == [(0.0, 1.0, "WHOSE MILK?")]


def test_the_sketch_refuses_notes_and_events_the_kitchen_cannot_show(mods):
    _, data = mods
    sk = data.SKETCH
    beats = list(sk.beats)
    i = next(k for k, b in enumerate(beats) if b.event.startswith("note"))
    for event, match in (
        ("note:" + "X" * (toon_sets.NOTE_MAX + 1), "does not fit"),
        ("note:WHOSE MILK?", "written twice"),
        ("wave", "unknown events"),
    ):
        bad = beats[:i] + [replace(beats[i], event=event)] + beats[i + 1 :]
        with pytest.raises(sketch.SketchError, match=match):
            data.validate(replace(sk, beats=tuple(bad)))
    on_rex = next(k for k, b in enumerate(beats) if b.who == "dog")
    bad = list(beats)
    bad[on_rex] = replace(beats[on_rex], event="note:PLEASE.")
    with pytest.raises(sketch.SketchError, match="Fern's shot"):
        data.validate(replace(sk, beats=tuple(bad)))
    no_sting = [replace(b, event="") if b.event == "hangup" else b for b in beats]
    with pytest.raises(sketch.SketchError, match="exactly once"):
        data.validate(replace(sk, beats=tuple(no_sting)))


def test_fern_shots_carry_the_note_of_their_moment_and_rex_shots_the_brewing_coffee(mods):
    build, data = mods
    sk = data.SKETCH
    seen = set()
    for app in sketch.appearances(sk.beats, sk.end):
        cv = canvas(sk.end)
        back, front = cv.group(cv.comp, "back"), cv.group(cv.comp, "front")
        data.dress(build.Shot(cv, app, back, front, sk.beats, sk.end, lambda text, size: 0.5 * size * len(text)))
        t = ET.fromstring(cv.scene.to_bytes(layout="pretty"))
        texts = [a.get("text") for a in t.iter("text")]
        if app.who == "frog":
            spans = data.note_spans(sk.beats, app.start, app.end)
            cut_in = data.inserts(sk.beats, app.start, app.end)
            assert texts == [text for *_, text in spans] + [text for *_, text in cut_in]
            assert spans[0][0] == app.start and spans[-1][1] == app.end
            seen.update(texts)
        else:
            assert texts == [] and any(a.get("property") == "opacity" for a in t.iter("animate"))
    assert seen == {"WHOSE MILK?", "IT MOVED.", "WHOSE YOGURT?"}


def test_each_new_note_is_cut_in_full_frame_for_its_beat(mods):
    _, data = mods
    beats = data.SKETCH.beats
    cut_in = data.inserts(beats, 0.0, data.SKETCH.end)
    assert [text for *_, text in cut_in] == ["IT MOVED.", "WHOSE YOGURT?"]
    moved = cut_in[0]
    assert moved[1] == next(b.start for b in beats if b.start > moved[0])  # until the next beat
    assert cut_in[-1][1] == data.SKETCH.end  # the button holds on the note to the end
    assert data.inserts(beats, 0.0, 1.0) == []
