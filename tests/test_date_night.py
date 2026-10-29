"""Date Night as data: the hook, the toasts that escalate on Mae's phone, the calendar that jumps to the end date,
the holds before the punchline and the button, and the dressing of both rooms (the shared Toon build is tested in
test_toon_sketches.py)."""

import sys
import xml.etree.ElementTree as ET
from dataclasses import replace
from pathlib import Path

import pytest
from sr_core.scene import Scene

from srstudio import PEACH, Canvas, flat_counter, sketch, toon

EPISODES = Path(__file__).resolve().parent.parent / "episodes"


@pytest.fixture(scope="module")
def mods():
    sys.path.insert(0, str(EPISODES))
    try:
        import date_night_data
        from srstudio import toon_sketch

        return toon_sketch, date_night_data
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
    assert sk.lines[0].text.endswith("?") and sk.beats[0].start == 0 and sk.beats[1].start <= 2.6
    assert len({s.voice.id for s in sk.speakers}) == 2
    apps = sketch.appearances(sk.beats, sk.end)
    assert {a.who for a in apps} == {"rabbit", "bear"} and len(apps) >= 8
    spoken = [b for b in sk.beats if b.spoken]
    june = next(b for b in spoken if b.caption == "June.")
    before_june = sk.beats[sk.beats.index(june) - 2]
    assert june.start - before_june.start >= 1.2 and june.event == "page:JUN 30"
    last, before = sk.beats.index(spoken[-1]), sk.beats.index(spoken[-2])
    assert spoken[-1].start - sk.beats[before + 1].start >= 1.2 and last - before >= 2
    assert any(b.event == "hangup" and b.start > spoken[-1].start for b in sk.beats)
    assert sk.beats[-1].event == "toast:3"  # the button: the spreadsheet after the sting
    assert sk.end - sk.beats[-1].start >= sketch.TAIL_AFTER_LAST
    assert toon.parse_script(sketch.cues(sk.beats, sk.end, sk.lines))


def test_the_toasts_escalate_and_each_waits_for_the_next(mods):
    _, data = mods
    sk = data.SKETCH
    assert [int(arg) for _, arg in sketch.events(sk.beats, "toast")] == [0, 1, 2, 3]
    first = next(a for a in sketch.appearances(sk.beats, sk.end) if a.who == "rabbit")
    toasts = data.toasts_in(sk.beats, first)
    assert [t.text for t in toasts] == ["Invite: Date night"] and toasts[0].start == 0 and toasts[0].end == first.end
    assert data.pages(sk.beats) == [(0.0, "OCT 29"), (21.6, "JUN 30")]


def test_the_sketch_refuses_events_its_props_cannot_show(mods):
    _, data = mods
    sk = data.SKETCH
    beats = list(sk.beats)
    on_mae = next(k for k, b in enumerate(beats) if b.event == "toast:1")
    on_otto = next(k for k, b in enumerate(beats) if b.event.startswith("page"))
    for k, event, match in (
        (on_mae, "toast:9", "not one of"),
        (on_mae, "wave", "unknown events"),
        (on_mae, "page:JUN 30", "Otto's shot"),
        (on_otto, "toast:1", "Mae's shot"),
        (on_otto, "page:JUNE 30", "calendar"),
    ):
        bad = beats[:k] + [replace(beats[k], event=event)] + beats[k + 1 :]
        with pytest.raises(sketch.SketchError, match=match):
            data.validate(replace(sk, beats=tuple(bad)))
    no_sting = [replace(b, event="") if b.event == "hangup" else b for b in beats]
    with pytest.raises(sketch.SketchError, match="exactly once"):
        data.validate(replace(sk, beats=tuple(no_sting)))


def test_mae_shots_carry_the_fridge_and_toasts_and_otto_shots_the_calendar(mods):
    build, data = mods
    sk = data.SKETCH
    seen: set[str] = set()
    for app in sketch.appearances(sk.beats, sk.end):
        cv = canvas(sk.end)
        back, front = cv.group(cv.comp, "back"), cv.group(cv.comp, "front")
        data.dress(build.Shot(cv, app, back, front, sk.beats, sk.end, lambda text, size: 0.5 * size * len(text)))
        texts = [a.get("text") for a in ET.fromstring(cv.scene.to_bytes(layout="pretty")).iter("text")]
        if app.who == "rabbit":
            assert data.FRIDGE in texts
            toasts = {text for _, text in data.TOASTS}
            assert [t.text for t in data.toasts_in(sk.beats, app)] == [x for x in texts if x in toasts]
        else:
            assert {"OCT", "29"} <= set(texts)
        seen.update(texts)
    assert {t for _, t in data.TOASTS} <= seen and {"JUN", "30"} <= seen
    assert {"OTTO, NEXT ROOM", "MAE, IN THE KITCHEN", "CALL ENDED"} <= seen
