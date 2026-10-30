"""Soft props: the status badge that shows what a call or a calendar says, one state at a time."""

import xml.etree.ElementTree as ET

import pytest

from srstudio import SOFT, Canvas, registry, soft_props
from srstudio.soft_props import BadgeState, SoftPropError
from support.soft_props import canvas


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


def test_the_cake_is_a_registered_prop():
    entry = {e.name: e for e in registry.entries()}["soft-cake"]
    assert entry.kind == "prop" and entry.style == "soft"


def opacity_keys(group):
    anim = next(a for a in group.iter("animate") if a.get("property") == "opacity")
    return [(float(k.get("time")), float(k.get("value"))) for k in anim.iter("key")]


def test_the_cake_reads_its_front_then_turns_to_show_its_back():
    cv = canvas()
    soft_props.cake(cv, cv.comp, "WE'LL MISS\nYOU", back="BYE PIP", turn_at=4.0, x=300, y=1250, scale=1.2)
    t = tree(cv)
    groups = {g.get("id"): g for g in t.iter("group")}
    cake = groups["soft-cake"]
    assert float(cake.get("x")) == 300 and float(cake.get("y")) == 1250 and float(cake.get("scaleX")) == 1.2
    texts = [x.get("text") for x in t.iter("text")]
    assert texts == ["WE'LL MISS\nYOU", "BYE PIP"]
    spin = next(a for a in groups["soft-cake-spin"].iter("animate") if a.get("property") == "scaleX")
    widths = [(float(k.get("time")), float(k.get("value"))) for k in spin.iter("key")]
    assert widths[0] == (0.0, 1.0) and (4.0, 1.0) in widths and widths[-1][1] == 1.0
    edge = min(widths, key=lambda kv: kv[1])
    assert 4.0 < edge[0] < widths[-1][0] <= 4.0 + soft_props.CAKE_TURN and edge[1] < 0.1
    assert opacity_keys(groups["soft-cake-front"]) == [(0.0, 1.0), (edge[0], 0.0)]
    assert opacity_keys(groups["soft-cake-back"]) == [(0.0, 0.0), (edge[0], 1.0)]


def test_a_cake_without_a_back_never_turns():
    cv = canvas()
    soft_props.cake(cv, cv.comp, "SURPRISE", id="party-cake")
    t = tree(cv)
    ids = [g.get("id") for g in t.iter("group")]
    assert "party-cake" in ids and "party-cake-front" in ids and "party-cake-back" not in ids
    assert not [a for a in t.iter("animate") if a.get("property") == "scaleX"]


@pytest.mark.parametrize(
    "front, kw, message",
    [
        ("", {}, "lettering"),
        ("A\nB\nC", {}, "lettering"),
        ("X" * 13, {}, "lettering"),
        ("OK", {"back": "BYE"}, "turn_at"),
        ("OK", {"turn_at": 2.0}, "back"),
        ("OK", {"back": "BYE", "turn_at": -1.0}, "turn_at"),
        ("OK", {"back": "BYE", "turn_at": float("nan")}, "turn_at"),
        ("OK", {"back": "X" * 13, "turn_at": 1.0}, "lettering"),
        ("OK", {"scale": 0}, "scale"),
        ("OK", {"scale": float("inf")}, "scale"),
    ],
)
def test_bad_cakes_are_refused(front, kw, message):
    cv = canvas()
    with pytest.raises(SoftPropError, match=message):
        soft_props.cake(cv, cv.comp, front, **kw)


def test_the_cake_lettering_shows_only_in_its_spans():
    cv = canvas()
    soft_props.cake(cv, cv.comp, "HI", back="BYE", turn_at=3.0, lettering=[(1.0, 5.0), (7.0, 9.0)])
    groups = {g.get("id"): g for g in tree(cv).iter("group")}
    gate = groups["soft-cake-lettering"]
    assert opacity_keys(gate) == [(0.0, 0.0), (1.0, 1.0), (5.0, 0.0), (7.0, 1.0), (9.0, 0.0)]
    inside = {g.get("id") for g in gate.iter("group")}
    assert {"soft-cake-front", "soft-cake-back"} <= inside


def test_cake_lettering_spans_must_be_in_order():
    cv = canvas()
    with pytest.raises(SoftPropError, match="lettering spans"):
        soft_props.cake(cv, cv.comp, "HI", lettering=[(2.0, 1.0)])
    with pytest.raises(SoftPropError, match="lettering spans"):
        soft_props.cake(cv, cv.comp, "HI", lettering=[(0.0, 2.0), (1.0, 3.0)])
