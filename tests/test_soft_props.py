"""Soft props: the status badge that shows what a call or a calendar says, one state at a time."""

import xml.etree.ElementTree as ET

import pytest
from sr_core.scene import Scene

from srstudio import SOFT, WARM, Canvas, flat_counter, registry, soft_props
from srstudio.soft_props import BadgeState, SoftPropError


def canvas() -> Canvas:
    scene = Scene(version="auto")
    scene.add_project(width=1080, height=1920, fps="30", duration=10.0, background=WARM.background)
    return Canvas(scene, WARM, font_asset="caption-font", namer=flat_counter("k"))


def tree(cv: Canvas):
    return ET.fromstring(cv.scene.to_bytes(layout="pretty"))


STATES = [
    BadgeState("relax", "RELAX 15 MIN", "#9A938C", 0.0, 2.0),
    BadgeState("accepted", "ACCEPTED", "#4CB36B", 2.0, 5.0),
    BadgeState("ended", "ENDED", "#E0503F", 5.0, 10.0, struck=True),
]


def test_the_badge_is_registered_for_the_soft_style():
    assert "soft_props" in SOFT.parts
    entry = {e.name: e for e in registry.entries()}["soft-status-badge"]
    assert entry.kind == "graphic" and entry.style == "soft"


def test_each_state_is_a_gated_pill_with_its_label():
    cv = canvas()
    soft_props.status_badge(cv, cv.comp, STATES, (500, 560, 420, 92))
    t = tree(cv)
    assert [x.get("text") for x in t.iter("text")] == ["RELAX 15 MIN", "ACCEPTED", "ENDED"]
    groups = {g.get("id"): g for g in t.iter("group")}
    for s in STATES:
        g = groups[f"status-badge-{s.name}"]
        assert float(g.get("x")) == 710 and float(g.get("y")) == 606  # the pill's centre
    shapes = {s.name: len(list(groups[f"status-badge-{s.name}"].iter("shape"))) for s in STATES}
    assert shapes["ended"] == shapes["accepted"] + 1 == shapes["relax"] + 1  # only the struck dot gets a stroke


def test_a_badge_takes_its_own_id():
    cv = canvas()
    soft_props.status_badge(cv, cv.comp, STATES[:1], (500, 560, 420, 92), id="calendar")
    ids = [g.get("id") for g in tree(cv).iter("group")]
    assert "calendar" in ids and "calendar-relax" in ids


@pytest.mark.parametrize(
    "states, box, message",
    [
        ([], (500, 560, 420, 92), "at least one"),
        ([BadgeState("a", "A", "#000000", 2.0, 1.0)], (500, 560, 420, 92), "start < end"),
        ([BadgeState("a", "A", "#000000", -1.0, 1.0)], (500, 560, 420, 92), "start < end"),
        (
            [BadgeState("a", "A", "#000000", 0.0, 2.0), BadgeState("b", "B", "#000000", 1.0, 3.0)],
            (500, 560, 420, 92),
            "overlap",
        ),
        (
            [BadgeState("a", "A", "#000000", 0.0, 1.0), BadgeState("a", "B", "#000000", 1.0, 2.0)],
            (0, 0, 9, 9),
            "unique",
        ),
        ([BadgeState("A b", "A", "#000000", 0.0, 1.0)], (500, 560, 420, 92), "name"),
        ([BadgeState("a", "", "#000000", 0.0, 1.0)], (500, 560, 420, 92), "label"),
        ([BadgeState("a", "A" * 15, "#000000", 0.0, 1.0)], (500, 560, 420, 92), "label"),
        ([BadgeState("a", "A", "red", 0.0, 1.0)], (500, 560, 420, 92), "colour"),
        ([BadgeState("a", "A", "#000000", 0.0, 1.0)], (500, 560, 0, 92), "box"),
        ([BadgeState("a", "A", "#000000", 0.0, 1.0)], (500, 560, 420, float("nan")), "box"),
    ],
)
def test_bad_badges_are_refused(states, box, message):
    cv = canvas()
    with pytest.raises(SoftPropError, match=message):
        soft_props.status_badge(cv, cv.comp, states, box)
