"""In Network as data: the hook, the claims that arrive on Gil's phone, the calls-waiting board that climbs while
Dana takes her time, the hold before the punchline, the calendar that jumps to January and the callback toast (the
shared Toon build is tested in test_toon_sketches.py)."""

import sys
import xml.etree.ElementTree as ET
from dataclasses import replace
from pathlib import Path

import pytest
from sr_core.scene import Scene

from srstudio import PEACH, Canvas, flat_counter, sketch, toon, toon_cast

EPISODES = Path(__file__).resolve().parent.parent / "episodes"


@pytest.fixture(scope="module")
def mods():
    sys.path.insert(0, str(EPISODES))
    try:
        import _toon_sketch
        import in_network_data

        return _toon_sketch, in_network_data
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
    assert {a.who for a in apps} == {"frog", "dog"} and len(apps) >= 8
    spoken = [b for b in sk.beats if b.spoken]
    punch = next(b for b in spoken if b.caption == "Try again in January.")
    k = sk.beats.index(punch)
    assert punch.start - sk.beats[k - 2].start >= 1.2 and not sk.beats[k - 1].spoken  # the hold
    assert any(b.event == "hangup" and b.start > spoken[-1].start for b in sk.beats)
    assert sk.beats[-1].event == "toast:3"  # the button: a new claim, after January
    assert sk.end - sk.beats[-1].start >= sketch.TAIL_AFTER_LAST
    assert toon.parse_script(sketch.cues(sk.beats, sk.end, sk.lines))


def test_the_claims_escalate_and_the_last_one_calls_back_to_the_first(mods):
    _, data = mods
    sk = data.SKETCH
    assert [int(arg) for _, arg in sketch.events(sk.beats, "toast")] == [0, 1, 2, 3]
    assert data.TOASTS[0][1].startswith("Claim #4471") and data.TOASTS[3][1].startswith("Claim #4472")
    first = next(a for a in sketch.appearances(sk.beats, sk.end) if a.who == "frog")
    toasts = data.toasts_in(sk.beats, first)
    assert [t.text for t in toasts] == [data.TOASTS[0][1]] and toasts[0].start == 0 and toasts[0].end == first.end
    pages = data.pages(sk.beats)
    assert pages[0] == (0.0, data.FIRST_PAGE) and pages[-1][1] == "JAN 1" and len(pages) == 2


def test_the_board_climbs_while_dana_talks_and_jumps_in_the_hold(mods):
    _, data = mods
    sk = data.SKETCH
    counts = [n for _, n in data.waiting_through(sk.beats, 0.0, sk.end)]
    assert counts[0] == data.FIRST_WAITING and counts == sorted(counts) and len(counts) >= 4
    hold = sk.beats[sk.beats.index(next(b for b in sk.beats if b.caption == "Try again in January.")) - 1]
    assert hold.event.startswith("tick:")
    dog = [a for a in sketch.appearances(sk.beats, sk.end) if a.who == "dog"]
    for app in dog:
        shown = data.waiting_through(sk.beats, app.start, app.end)
        assert shown[0][0] == 0.0 and all(app.start < t < app.end for t, _ in shown[1:])


def test_the_sketch_refuses_events_its_props_cannot_show(mods):
    _, data = mods
    sk = data.SKETCH
    beats = list(sk.beats)
    on_gil = next(k for k, b in enumerate(beats) if b.event == "toast:1")
    on_dana = next(k for k, b in enumerate(beats) if b.event.startswith("tick:"))
    for k, event, match in (
        (on_gil, "toast:9", "not one of"),
        (on_gil, "wave", "unknown events"),
        (on_gil, "tick:5000", "Dana's shot"),
        (on_dana, "toast:1", "Gil's shot"),
        (on_dana, "page:JAN 1", "Gil's shot"),
        (on_dana, "tick:2", "climbs"),
        (on_dana, "tick:many", "climbs"),
        (on_gil, "page:JANUARY 1", "calendar"),
    ):
        bad = beats[:k] + [replace(beats[k], event=event)] + beats[k + 1 :]
        with pytest.raises(sketch.SketchError, match=match):
            data.validate(replace(sk, beats=tuple(bad)))
    no_sting = [replace(b, event="") if b.event == "hangup" else b for b in beats]
    with pytest.raises(sketch.SketchError, match="exactly once"):
        data.validate(replace(sk, beats=tuple(no_sting)))


def test_gil_shots_carry_the_calendar_and_claims_and_dana_shots_the_board(mods):
    build, data = mods
    sk = data.SKETCH
    seen: set[str] = set()
    for app in sketch.appearances(sk.beats, sk.end):
        cv = canvas(sk.end)
        back, front = cv.group(cv.comp, "back"), cv.group(cv.comp, "front")
        data.dress(build.Shot(cv, app, back, front, sk.beats, sk.end, lambda text, size: 0.5 * size * len(text)))
        texts = [a.get("text") for a in ET.fromstring(cv.scene.to_bytes(layout="pretty")).iter("text")]
        if app.who == "frog":
            assert {"OCT", "29"} <= set(texts) and "CALLS WAITING" not in texts
            toasts = {text for _, text in data.TOASTS}
            assert [t.text for t in data.toasts_in(sk.beats, app)] == [x for x in texts if x in toasts]
        else:
            assert "CALLS WAITING" in texts
            assert [str(n) for _, n in data.waiting_through(sk.beats, app.start, app.end)] == [
                x for x in texts if x and x.isdigit()
            ]
        seen.update(texts)
    assert {t for _, t in data.TOASTS} <= seen and {"JAN", "1"} <= seen
    assert {"DANA, CLAIMS", "GIL, MEMBER 4471", "CALL ENDED"} <= seen


def test_dana_wears_the_headset(mods):
    _, data = mods
    assert data.STICKERS == {"dog": toon_cast.headset(toon_cast.DOG)}
