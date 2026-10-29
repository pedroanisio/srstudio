"""Out of Office as data: the hook, the calendar that tears through the week in Bruno's shots, the toasts on his
phone, the hold before the punchline and the auto-reply button (the shared Toon build is tested in
test_toon_sketches.py)."""

import sys
from dataclasses import replace
from pathlib import Path

import pytest

from srstudio import sketch, toon

EPISODES = Path(__file__).resolve().parent.parent / "episodes"


@pytest.fixture(scope="module")
def data():
    sys.path.insert(0, str(EPISODES))
    try:
        import out_of_office_data

        return out_of_office_data
    finally:
        sys.path.pop(0)


def test_the_sketch_hooks_on_a_question_and_holds_before_its_punchline(data):
    data.validate()
    sk = data.SKETCH
    assert sk.lines[0].text.endswith("?") and sk.beats[0].start == 0 and sk.beats[1].start <= 2.5
    assert len({s.voice.id for s in sk.speakers}) == 2
    spoken = [b for b in sk.beats if b.spoken]
    before = sk.beats.index(spoken[-2])
    assert spoken[-1].start - sk.beats[before + 1].start >= 1.2
    hangup = sketch.events(sk.beats, "hangup")[0][0]
    assert hangup > spoken[-1].start and sketch.events(sk.beats, "toast")[-1][0] > hangup  # the button
    assert sk.end - sk.beats[-1].start >= sketch.TAIL_AFTER_LAST
    assert toon.parse_script(sketch.cues(sk.beats, sk.end, sk.lines))


def test_the_calendar_tears_through_the_week_and_the_toasts_land_in_order(data):
    beats = data.SKETCH.beats
    assert [text for _, text in data.pages(beats)] == ["OCT 27", "OCT 29", "NOV 1"]
    bear = [a for a in sketch.appearances(beats, data.SKETCH.end) if a.who == "bear"]
    toasts = [t for app in bear for t in data.toasts_in(beats, app)]
    assert [(t.sender, t.text) for t in toasts] == list(data.TOASTS)
    assert all(t.start < t.end for t in toasts)


@pytest.mark.parametrize(
    "event, match", [("page:OCT 99", "calendar"), ("toast:7", "not one of"), ("wave", "unknown events")]
)
def test_the_sketch_refuses_what_the_props_cannot_show(data, event, match):
    sk = data.SKETCH
    i = next(k for k, b in enumerate(sk.beats) if b.event.startswith("page"))
    bad = sk.beats[:i] + (replace(sk.beats[i], event=event),) + sk.beats[i + 1 :]
    with pytest.raises(sketch.SketchError, match=match):
        data.validate(replace(sk, beats=bad))


def test_props_change_only_in_brunos_shot_and_the_call_ends_once(data):
    sk = data.SKETCH
    on_pip = next(k for k, b in enumerate(sk.beats) if b.who == "rabbit" and b.start > 0 and not b.event)
    for event in ("page:NOV 2", "toast:0"):
        bad = sk.beats[:on_pip] + (replace(sk.beats[on_pip], event=event),) + sk.beats[on_pip + 1 :]
        with pytest.raises(sketch.SketchError, match="Bruno's shot"):
            data.validate(replace(sk, beats=bad))
    no_sting = tuple(replace(b, event="") if b.event == "hangup" else b for b in sk.beats)
    with pytest.raises(sketch.SketchError, match="exactly once"):
        data.validate(replace(sk, beats=no_sting))
