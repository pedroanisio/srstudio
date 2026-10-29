"""Split It as data: the hook, the evidence on the table, the reader that declines Brock and approves Mia, the hold
before the punchline on Mia's phone and the button after the sting (the shared Toon build is tested in
test_toon_sketches.py)."""

import sys
import xml.etree.ElementTree as ET
from dataclasses import replace
from pathlib import Path

import pytest
from sr_core.scene import Scene

from srstudio import PEACH, Canvas, flat_counter, sketch, toon, toon_dinner

EPISODES = Path(__file__).resolve().parent.parent / "episodes"


@pytest.fixture(scope="module")
def mods():
    sys.path.insert(0, str(EPISODES))
    try:
        import _toon_sketch
        import split_it_data

        return _toon_sketch, split_it_data
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
    assert {a.who for a in apps} == {"bear", "rabbit"} and len(apps) >= 10
    punch = next(b for b in sk.beats if b.event == "toast:2")
    k = sk.beats.index(punch)
    assert punch.start - sk.beats[k - 2].start >= 1.2 and not sk.beats[k - 1].spoken  # the wait, then the transfer
    assert sk.beats[k + 1].event == "hangup" and sk.beats[-1].event == "toast:3"  # the sting, then the button
    assert sk.end - sk.beats[-1].start >= sketch.TAIL_AFTER_LAST
    assert toon.parse_script(sketch.cues(sk.beats, sk.end, sk.lines))
    assert not any(ch.isdigit() for line in sk.lines for ch in line.text)  # speech-to-text writes numbers


def test_the_table_shows_the_evidence_and_the_phone_the_payments(mods):
    _, data = mods
    assert {kind for kind, _ in data.LAID["bear"]} >= {"shells", "wine", "glass", "check"}
    assert {kind for kind, _ in data.LAID["rabbit"]} >= {"salad", "water", "empty"}
    assert [int(arg) for _, arg in sketch.events(data.SKETCH.beats, "toast")] == [0, 1, 2, 3]
    assert data.TOASTS[1][1].endswith("$6.50") and "salad" in data.TOASTS[2][1]
    assert [s[1] for s in data.screens(data.SKETCH.beats)] == ["TAP CARD", "DECLINED", "APPROVED"]


def test_the_sketch_refuses_events_its_props_cannot_show(mods):
    _, data = mods
    sk = data.SKETCH
    beats = list(sk.beats)
    on_mia = next(k for k, b in enumerate(beats) if b.event == "toast:1")
    declined = next(k for k, b in enumerate(beats) if b.event == "reader:DECLINED")
    on_brock = next(k for k, b in enumerate(beats) if b.who == "bear" and not b.event and k > declined)
    for k, event, match in (
        (on_mia, "toast:9", "not one of"),
        (on_mia, "wave", "unknown events"),
        (on_brock, "toast:1", "Mia's shot"),
        (declined, "reader:MAYBE", "one of"),
        (declined, "", "once each"),
        (on_mia, "reader:APPROVED", "once each"),
    ):
        bad = beats[:k] + [replace(beats[k], event=event)] + beats[k + 1 :]
        with pytest.raises(sketch.SketchError, match=match):
            data.validate(replace(sk, beats=tuple(bad)))
    swapped = [replace(b, event={"reader:DECLINED": "reader:APPROVED", "reader:APPROVED": "reader:DECLINED"}.get(
        b.event, b.event)) for b in beats]  # fmt: skip
    with pytest.raises(sketch.SketchError, match="once each"):
        data.validate(replace(sk, beats=tuple(swapped)))
    early = [replace(b, event="") if b.event == "hangup" else b for b in beats]
    early[1] = replace(early[1], event="hangup")
    with pytest.raises(sketch.SketchError, match="after the last line"):
        data.validate(replace(sk, beats=tuple(early)))
    none = [replace(b, event="") if b.event == "hangup" else b for b in beats]
    with pytest.raises(sketch.SketchError, match="exactly once"):
        data.validate(replace(sk, beats=tuple(none)))


def test_each_shot_lays_its_side_of_the_table_and_mia_gets_the_toasts(mods):
    build, data = mods
    sk = data.SKETCH
    seen: set[str] = set()
    for app in sketch.appearances(sk.beats, sk.end):
        cv = canvas(sk.end)
        back, front = cv.group(cv.comp, "back"), cv.group(cv.comp, "front")
        data.dress(build.Shot(cv, app, back, front, sk.beats, sk.end, lambda text, size: 0.5 * size * len(text)))
        t = ET.fromstring(cv.scene.to_bytes(layout="pretty"))
        texts = [a.get("text") for a in t.iter("text")]
        dishes = {i.rsplit("-", 1)[-1] for i in (g.get("id", "") for g in t.iter("group"))} & set(toon_dinner.DISHES)
        assert {"SPECIALS", "TAP CARD", "DECLINED", "APPROVED"} <= set(texts)
        assert dishes == {kind for kind, _ in data.LAID[app.who]}
        toasts = {text for _, text in data.TOASTS}
        if app.who == "rabbit":
            assert [x.text for x in data.toasts_in(sk.beats, app)] == [x for x in texts if x in toasts]
        else:
            assert not toasts & set(texts)
        seen.update(texts)
    assert {t for _, t in data.TOASTS} <= seen
