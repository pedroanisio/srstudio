"""The five office Toon sketches (Password Expired, The Card, Friday Sync, Like Family, Reply All) as data: the
hook, the hold before the punchline, the sting after it, the events their props can show and the dressing of their
shots (the shared Toon build is tested in test_toon_sketches.py)."""

import importlib
import sys
import xml.etree.ElementTree as ET
from dataclasses import replace
from pathlib import Path

import pytest
from sr_core.scene import Scene

from srstudio import PEACH, Canvas, flat_counter, sketch, toon

EPISODES = Path(__file__).resolve().parent.parent / "episodes"
NAMES = ("password_expired", "the_card", "friday_sync", "like_family", "reply_all")
# the words each sketch must put on screen somewhere: its gag's evidence
SHOWN = {
    "password_expired": {"SECURITY WEEK!", "PASSWORDS.XLSX", "HONEY4", "Password expired.", "Expired again."},
    "the_card": {"SIGN THE CARD", "FAREWELL FERN!", "FAREWELL DRINKS 5PM"},
    "friday_sync": {"WELCOME, NEW HIRE!", "Your job, 30% less pay.", "Applications closed.", "SYNC?"},
    "like_family": {"WE ARE FAMILY", "WE ARE A TEAM", "WE ARE FAMILY!", "RENT"},
    "reply_all": {"Agreed.", "Your job: also an email.", "4,812"},
}


def measure(text: str, size: float) -> float:
    return 0.5 * size * len(text)


@pytest.fixture(scope="module")
def mods():
    sys.path.insert(0, str(EPISODES))
    try:
        build = importlib.import_module("_toon_sketch")
        return build, {n: importlib.import_module(f"{n}_data") for n in NAMES}
    finally:
        sys.path.pop(0)


def canvas(duration: float) -> Canvas:
    scene = Scene(version="auto")
    scene.add_project(width=1080, height=1920, fps="24", duration=duration, background=PEACH.background)
    return Canvas(scene, PEACH, font_asset="comic-neue", namer=flat_counter("k"))


def swap(sk, i: int, event: str):
    return replace(sk, beats=tuple(replace(b, event=event) if k == i else b for k, b in enumerate(sk.beats)))


def test_the_sketches_are_distinct(mods):
    _, data = mods
    assert len({d.SLUG for d in data.values()}) == len({d.SEED for d in data.values()}) == len(NAMES)
    assert all(d.SLUG == n.replace("_", "-") for n, d in data.items())


@pytest.mark.parametrize("name", NAMES)
def test_each_sketch_hooks_on_a_question_and_holds_before_its_punchline(mods, name):
    _, data = mods
    d = data[name]
    d.validate()
    sk = d.SKETCH
    assert sk.lines[0].text.endswith("?") and sk.beats[0].start == 0 and sk.beats[0].line == 0
    assert sk.beats[1].start <= 2.5
    assert len({s.voice.id for s in sk.speakers}) == len(sk.speakers) == 2
    apps = sketch.appearances(sk.beats, sk.end)
    assert {a.who for a in apps} == {s.character for s in sk.speakers} and len(apps) >= 6
    spoken = [b for b in sk.beats if b.spoken]
    last, before = sk.beats.index(spoken[-1]), sk.beats.index(spoken[-2])
    assert last - before >= 2 and spoken[-1].start - sk.beats[before + 1].start >= 1.2
    assert any(b.event == "hangup" and b.start > spoken[-1].start for b in sk.beats)
    assert sk.end - sk.beats[-1].start >= sketch.TAIL_AFTER_LAST
    assert 11 <= sk.end <= 35
    cues = sketch.cues(sk.beats, sk.end, sk.lines)
    assert {c["speaker"] for c in cues} == set(d.TINTS)
    assert toon.parse_script(cues)


@pytest.mark.parametrize("name", NAMES)
def test_every_line_is_plain_words_speech_to_text_can_hear(mods, name):
    _, data = mods
    for line in data[name].SKETCH.lines:
        assert not any(c.isdigit() for c in line.text), line.text


@pytest.mark.parametrize("name", NAMES)
def test_each_sketch_refuses_events_its_props_cannot_show(mods, name):
    _, data = mods
    d = data[name]
    sk = d.SKETCH
    with pytest.raises(sketch.SketchError, match="unknown events"):
        d.validate(swap(sk, 0, "fireworks"))
    with pytest.raises(sketch.SketchError, match="exactly once"):
        d.validate(replace(sk, beats=tuple(replace(b, event="") if b.event == "hangup" else b for b in sk.beats)))
    # every prop event moved into the other character's shot is refused: the prop is not there
    for b in sk.beats:
        if b.event and b.event != "hangup":
            other = next(k for k, o in enumerate(sk.beats) if o.who != b.who and not o.event)
            with pytest.raises(sketch.SketchError, match="off screen"):
                d.validate(swap(sk, other, b.event))


@pytest.mark.parametrize("name", NAMES)
def test_each_shot_is_dressed_with_the_gag_on_screen(mods, name):
    build, data = mods
    d = data[name]
    sk = d.SKETCH
    shown = set()
    for app in sketch.appearances(sk.beats, sk.end):
        cv = canvas(sk.end)
        back, front = cv.group(cv.comp, "back"), cv.group(cv.comp, "front")
        d.dress(build.Shot(cv, app, back, front, sk.beats, sk.end, measure))
        shown.update(a.get("text") for a in ET.fromstring(cv.scene.to_bytes(layout="pretty")).iter("text"))
    assert SHOWN[name] <= shown, SHOWN[name] - shown


def test_toasts_and_boards_hold_until_the_next_or_the_shot_ends(mods):
    _, data = mods
    pw = data["password_expired"]
    assert pw.spans(pw.boards(pw.SKETCH.beats), 0.0, 20.0) == [
        (0.0, 13.8, "SECURITY WEEK!"),
        (13.8, 20.0, "PASSWORDS.XLSX"),
    ]
    assert pw.spans(pw.boards(pw.SKETCH.beats), 2.4, 4.0) == [(2.4, 4.0, "SECURITY WEEK!")]
    ra = data["reply_all"]
    app = sketch.Appearance("bear", 8.6, 12.2, [])
    assert [(t.start, t.end, t.text) for t in ra.toasts_in(ra.SKETCH.beats, app)] == [(9.8, 12.2, "Agreed.")]
    app = sketch.Appearance("bear", 14.0, 19.4, [])
    assert [(t.start, t.end) for t in ra.toasts_in(ra.SKETCH.beats, app)] == [(15.4, 19.4)]
    fs = data["friday_sync"]
    app = sketch.Appearance("rabbit", 10.4, 12.8, [])
    assert [(t.start, t.end, t.sender) for t in fs.toasts_in(fs.SKETCH.beats, app)] == [(10.4, 12.8, "Job alert")]
    with pytest.raises(sketch.SketchError, match="not one of"):
        fs.validate(swap(fs.SKETCH, next(i for i, b in enumerate(fs.SKETCH.beats) if b.event == "toast:0"), "toast:7"))


def test_the_clocks_and_notes_refuse_what_their_props_cannot_do(mods):
    _, data = mods
    lf = data["like_family"]
    i = next(i for i, b in enumerate(lf.SKETCH.beats) if b.event.startswith("clock:"))
    with pytest.raises(sketch.SketchError, match="backwards"):
        lf.validate(swap(lf.SKETCH, i, "clock:16:30"))
    j = next(i for i, b in enumerate(lf.SKETCH.beats) if b.event.startswith("board:"))
    with pytest.raises(sketch.SketchError, match="does not fit"):
        lf.validate(swap(lf.SKETCH, j, "board:" + "X" * 41))
    card = data["the_card"]
    k = next(i for i, b in enumerate(card.SKETCH.beats) if b.event.startswith("note:"))
    with pytest.raises(sketch.SketchError, match="does not fit"):
        card.validate(swap(card.SKETCH, k, "note:" + "X" * 15))
    with pytest.raises(sketch.SketchError, match="written twice"):
        card.validate(swap(card.SKETCH, k, "note:" + card.FIRST_NOTE))
    assert card.inserts(card.SKETCH.beats, 0.0, 1.0) == []
    cut = card.inserts(card.SKETCH.beats, 0.0, card.SKETCH.end)
    assert [text for *_, text in cut] == ["FAREWELL FERN!"] and cut[0][1] == 13.0
