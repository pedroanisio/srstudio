"""Vera's and Gus's faces stay on the skin (moved from the episodes repository, ADR 0225): every mark and every mouth
state, drawn through the code a reel draws it with, measured against the skin's contour with the turn and the nod at
the rig's limits, on each version of the News kit's anchors.
"""

from __future__ import annotations

import math
import re
import xml.etree.ElementTree as ET
from itertools import pairwise

import pytest
from sr_core.scene import Scene

from srstudio import Canvas, head_motion, news_inked, news_kit, parts, specimens
from srstudio.news_kit import Pose

ANCHORS = ("vera", "gus")
anchors = pytest.mark.parametrize("who", ANCHORS)


def canvas(seconds: float = 12.0) -> Canvas:
    scene = Scene(version="auto")
    scene.add_project(width=1080, height=1920, fps="30", duration=seconds, background=news_kit.PLUM_DEEP)
    return Canvas(scene, news_kit.NEWS.palette(), font_asset="barlow-condensed")


def tree(cv: Canvas) -> ET.Element:
    return ET.fromstring(cv.scene.to_bytes(layout="pretty"))


def group(root: ET.Element, prefix: str) -> list[ET.Element]:
    return [g for g in root.iter("group") if str(g.get("id", "")).startswith(prefix)]


@anchors
def test_the_face_stays_on_the_skin_at_the_widest_slide(who):
    rig = news_inked.RIGS[f"news-{who}@2"]
    face = news_inked.VERA_INKED if who == "vera" else news_inked.GUS_INKED
    slide = head_motion.limit(rig.style, "face_x")
    edge = max(x for x, _ in rig.skin)
    assert face.eye_x + face.eye_r + slide <= edge
    assert face.mouth_w * 0.58 + slide <= edge - 20.0


CUBIC = re.compile(r"[MLQCZ]|-?\d+\.?\d*(?:e-?\d+)?")


def traced(d: str, steps: int = 6) -> list[tuple[float, float]]:
    """The points of a drawn path, its curves walked: what is on the frame, not a control point off it."""
    tokens, at, points, here, op = CUBIC.findall(d), 0, [], (0.0, 0.0), "M"

    def point() -> tuple[float, float]:
        nonlocal at
        at += 2
        return float(tokens[at - 2]), float(tokens[at - 1])

    while at < len(tokens):
        if tokens[at] in "MLQCZ":
            op, at = tokens[at], at + 1
            continue
        if op in "ML":
            here = point()
            points.append(here)
        else:
            controls = [point() for _ in range(2 if op == "Q" else 3)]
            hull = [here, *controls]
            for k in range(1, steps + 1):
                u, row = k / steps, hull
                while len(row) > 1:
                    row = [(a[0] + (b[0] - a[0]) * u, a[1] + (b[1] - a[1]) * u) for a, b in pairwise(row)]
                points.append(row[0])
            here = controls[-1]
    return points


def span_at(contour: list[tuple[float, float]], y: float) -> tuple[float, float] | None:
    """Where the closed ``contour`` is at height ``y``: its left and right edge there, or None above and below it."""
    edges = [
        ax + (y - ay) * (bx - ax) / (by - ay)
        for (ax, ay), (bx, by) in zip(contour, (*contour[1:], contour[0]), strict=True)
        if (ay > y) != (by > y)
    ]
    return (min(edges), max(edges)) if edges else None


def on_skin(contour, x: float, y: float) -> bool:
    span = span_at(contour, y)
    return span is not None and span[0] <= x <= span[1]


def face_of(who: str, number: int):
    """The head of a version as the rig's specimen draws it, every eye, brow and mouth state: the skin's fill as a
    contour, and each distinct shape that slides over it with its colour."""
    rig = news_inked.RIGS[f"news-{who}@{number}"]
    cv = canvas(4.0)
    news_inked.rig_specimen(cv, who, 4.0, number)
    nod = group(tree(cv), "head-nod")[0]
    colour = (news_inked.VERA_SKIN if who == "vera" else news_inked.GUS_SKIN).lower()
    skins = [traced(s.attrib["path"]) for s in nod if s.get("path") and s.get("fill", "").lower() == colour]
    contour = max(skins, key=lambda c: max(x for x, _ in c) - min(x for x, _ in c))
    shapes = {s.attrib["path"]: s.get("fill") for f in group(nod, "head-face") for s in f.iter() if s.get("path")}
    return rig, contour, [(fill or "", traced(d)) for d, fill in shapes.items()]


def off_skin(who: str, number: int) -> list[str]:
    """Every shape that leaves the skin with the turn and the nod at their limits together, each of them measured
    against the contour at its own height. Skull and face turn and roll in the same groups, so what parts them is the
    slide and the drop alone. What the drawing lays past the skin at rest is the drawing's: a test below names it."""
    rig, contour, marks = face_of(who, number)
    slide = head_motion.limit(rig.style, "face_x")
    drop = head_motion.limit(rig.style, "nod") * rig.face_slide
    corners = [(side * slide, d) for side in (-1.0, 1.0) for d in (0.0, drop)]
    return [
        f"{fill} at {points[0]} by {corner}"
        for fill, points in marks
        if all(on_skin(contour, x, y) for x, y in points)
        for corner in corners
        if not all(on_skin(contour, x + corner[0], y + corner[1]) for x, y in points)
    ]


MARKS = {  # what each face must show the check, by colour: blush, freckles, the open mouth, the brows
    "vera": {"blush": "#b3603c50", "mouth": "#4a1420", "brow": "#6f6b92"},
    "gus": {"blush": "#f0805a40", "freckle": "#c9875a", "mouth": "#4a1420", "brow": "#3a2112"},
}
FLOOR_SLIDE = 8.0  # the least a full turn slides the face across the head, frame pixels at the two-shot's scale
FLOOR_TRAVEL = 12.0  # the least the eyes travel on the frame in a full turn, the rotation and the slide together


@anchors
def test_every_face_mark_stays_on_the_skin_with_the_turn_and_the_nod_at_their_limits(who):
    assert off_skin(who, 3) == []


@anchors
def test_the_mark_check_sees_every_kind_of_mark(who):
    _, contour, marks = face_of(who, 3)
    seen = {fill.lower() for fill, points in marks if all(on_skin(contour, x, y) for x, y in points)}
    assert set(MARKS[who].values()) <= seen


def test_what_the_drawing_lays_past_the_skin_at_rest_is_only_her_spectacle_arms():
    for who in ANCHORS:
        _, contour, marks = face_of(who, 3)
        past = [fill for fill, points in marks if not all(on_skin(contour, x, y) for x, y in points)]
        assert past == (["#160a30", "#160a30"] if who == "vera" else [])


@pytest.mark.parametrize(
    ("who", "kind"), [("gus", "#f0805a40"), ("gus", "#c9875a"), ("gus", "#4a1420"), ("vera", "#b3603c50")]
)
def test_the_mark_check_fails_on_the_rig_that_slid_them_off(who, kind):
    assert any(row.startswith(kind) for row in off_skin(who, 2))


def mouth_of(who: str, state: str, number: int = 3) -> list[tuple[float, float]]:
    """The outline a mouth state draws, through the code a reel draws it with: its largest shape, walked, an ellipse
    all the way round."""
    cv = canvas(1.0)
    drawn = cv.group(cv.comp, "mouth-check", opacity=0.0)
    news_inked._mouths(cv, drawn, news_inked.inked(who, number), ((0.0, state),), 0.0, 1.0)
    shape = next(group(tree(cv), "mouth-check")[0].iter("shape"))
    if path := shape.get("path"):
        return traced(path)
    x, y, wide, tall = (float(shape.attrib[k]) for k in ("x", "y", "width", "height"))
    turns = [2 * math.pi * k / 36 for k in range(36)]
    return [(x + wide / 2 * (1 + math.cos(a)), y + tall / 2 * (1 + math.sin(a))) for a in turns]


def corners_of(who: str, number: int) -> list[tuple[float, float]]:
    rig, *_ = face_of(who, number)
    slide = head_motion.limit(rig.style, "face_x")
    drop = head_motion.limit(rig.style, "nod") * rig.face_slide
    return [(side * slide, d) for side in (-1.0, 1.0) for d in (0.0, drop)]


def mouths_past_the_skin(who: str, number: int, *corners: tuple[float, float]) -> list[str]:
    _, contour, _ = face_of(who, number)
    return [
        state
        for state in news_kit.EXPRESSIONS
        if not all(on_skin(contour, x + dx, y + dy) for x, y in mouth_of(who, state, number) for dx, dy in corners)
    ]


def enclosed(outline: list[tuple[float, float]], x: float, y: float) -> bool:
    """Whether the point lies inside a shape that may be concave, as the top lip of a grin is."""
    edges = [
        ax + (y - ay) * (bx - ax) / (by - ay)
        for (ax, ay), (bx, by) in zip(outline, (*outline[1:], outline[0]), strict=True)
        if (ay > y) != (by > y)
    ]
    return sum(edge > x for edge in edges) % 2 == 1


def nose_of(who: str, number: int) -> list[tuple[float, float]]:
    """The nose as drawn, its ink's width with it: the long line of the face's own colour, below the eyes' top."""
    _, _, marks = face_of(who, number)
    deep = (news_inked.VERA_DEEP if who == "vera" else news_inked.GUS_DEEP).lower()
    long = [p for f, p in marks if f.lower() == deep and max(x for x, _ in p) - min(x for x, _ in p) > 25]
    return [point for points in long if min(y for _, y in points) < -140 for point in points]


MOUTH_INK = 2.5  # half the width of the line round a mouth


def mouths_over_the_nose(who: str, number: int) -> list[str]:
    """Every mouth whose line reaches the nose's ink, the slide being shared: a fault of the drawing alone."""
    nose = nose_of(who, number)
    return [
        state
        for state in news_kit.EXPRESSIONS
        if any(enclosed(mouth_of(who, state, number), x, y + MOUTH_INK) for x, y in nose)
    ]


def area_of(points: list[tuple[float, float]]) -> float:
    return abs(sum(ax * by - bx * ay for (ax, ay), (bx, by) in zip(points, (*points[1:], points[0]), strict=True))) / 2


# Past the skin or over the nose on a version: not a pass, the open defects by name. A change that fixes one fails here
# until it comes off the list, and a mouth that joins a list fails here too.
MOUTHS_PAST_AT_THE_LIMITS = {3: {"vera": ["grin", "gape"], "gus": ["gape"]}, 4: {"vera": [], "gus": []}}
MOUTHS_OVER_THE_NOSE = {
    3: {"vera": [], "gus": ["gape", "open", "round", "teeth"]},
    4: {"vera": [], "gus": ["gape", "teeth"]},
}
SHOUT_ABOVE_TALK = 1.25  # how much more mouth a shout shows than a word, so that it stays a shout at phone size


@anchors
@pytest.mark.parametrize("number", [3, 4])
def test_only_the_named_mouths_leave_the_skin_with_the_turn_and_the_nod_at_their_limits(who, number):
    assert mouths_past_the_skin(who, number, *corners_of(who, number)) == MOUTHS_PAST_AT_THE_LIMITS[number][who]


@anchors
@pytest.mark.parametrize(("number", "past"), [(2, ["gape"]), (3, ["gape"]), (4, [])])
def test_the_chin_holds_the_mouth_at_rest_from_version_4(who, number, past):
    assert mouths_past_the_skin(who, number, (0.0, 0.0)) == past


@pytest.mark.slow  # measured over the gate's bound on the run that moved it here (ADR 0225)
@anchors
@pytest.mark.parametrize("number", [3, 4])
def test_only_the_named_mouths_reach_the_nose(who, number):
    assert mouths_over_the_nose(who, number) == MOUTHS_OVER_THE_NOSE[number][who]


def room_at_the_limits(who: str, state: str, number: int) -> float:
    """How far the mouth's line stays from the skin's edge at the worst corner of the rig, in the face's pixels."""
    _, contour, _ = face_of(who, number)
    edges = list(zip(contour, (*contour[1:], contour[0]), strict=True))

    def apart(x: float, y: float) -> float:
        rows = []
        for (ax, ay), (bx, by) in edges:
            dx, dy = bx - ax, by - ay
            along = max(0.0, min(1.0, ((x - ax) * dx + (y - ay) * dy) / (dx * dx + dy * dy or 1.0)))
            rows.append(math.hypot(x - ax - along * dx, y - ay - along * dy))
        return min(rows)

    return min(
        apart(x + dx, y + dy) if on_skin(contour, x + dx, y + dy) else -1.0
        for x, y in mouth_of(who, state, number)
        for dx, dy in corners_of(who, number)
    )


@pytest.mark.slow  # measured over the gate's bound on the run that moved it here (ADR 0225)
@anchors
@pytest.mark.parametrize("state", ["gape", "open", "round", "grin"])
def test_the_ink_of_a_redrawn_mouth_stays_on_the_skin_too(who, state):
    assert round(room_at_the_limits(who, state, 4), 1) >= MOUTH_INK


@anchors
def test_a_shout_is_still_a_shout(who):
    gape, talk = area_of(mouth_of(who, "gape", 4)), area_of(mouth_of(who, "open", 4))
    assert gape >= SHOUT_ABOVE_TALK * talk


@anchors
def test_a_turn_still_reads_as_a_turn_on_the_smaller_limits(who):
    old, new = (news_inked.RIGS[f"news-{who}@{n}"] for n in (2, 3))
    assert FLOOR_SLIDE <= new.style.glance_face < old.style.glance_face
    assert new.style.glance_turn == old.style.glance_turn
    face = news_inked.VERA_INKED if who == "vera" else news_inked.GUS_INKED
    above = news_kit.CHIN_Y - face.eye_y
    assert above * math.sin(math.radians(new.style.glance_turn)) + new.style.glance_face >= FLOOR_TRAVEL


@anchors
def test_version_4_keeps_the_limits_and_redraws_nothing_but_the_mouths(who):
    def drawn(number: int) -> bytes:
        cv = canvas(4.0)
        poses = tuple(
            (4.0 * n / len(news_kit.ARMS), Pose(eyes, "flat", arms))
            for n, (eyes, arms) in enumerate(zip(news_kit.EYES, news_kit.ARMS, strict=False))
        )
        news_inked.perform(cv, cv.comp, who, 540.0, poses, 0.0, 4.0, number=number)
        return cv.scene.to_bytes(layout="pretty")

    assert drawn(4) == drawn(3)
    assert news_inked.RIGS[f"news-{who}@4"].style == news_inked.RIGS[f"news-{who}@3"].style
    assert news_inked.RIGS[f"news-{who}@4"].face_slide == news_inked.RIGS[f"news-{who}@3"].face_slide


@pytest.mark.parametrize(("who", "redrawn"), [("gus", {"gape", "open", "round"}), ("vera", {"gape", "grin"})])
def test_version_4_redraws_the_named_mouths_and_leaves_the_rest(who, redrawn):
    changed = {s for s in news_kit.EXPRESSIONS if mouth_of(who, s, 4) != mouth_of(who, s, 3)}
    assert changed == redrawn


@anchors
def test_version_4_is_approved_and_its_specimen_shows_every_mouth(who):
    name = f"news-{who}"
    version = parts.get(name).version(4)
    assert version.status == "approved"
    assert version.rig.status == "approved"
    assert version.approval.words == version.rig.approval.words
    assert 'Slack 1793489634.822829: "*v4 mouths: approved* for both anchors."' in version.approval.words
    assert parts.latest(name).number >= 4
    assert specimens.digest(name, 4) == parts.get(name).version(4).drawing
    assert specimens.digest(name, 4) != specimens.digest(name, 3)
    assert specimens.rig_digest(name, 4) == parts.get(name).version(4).rig.drawing
    _, _, marks = face_of(who, 4)
    outlines = {tuple(points) for _, points in marks}
    assert {tuple(mouth_of(who, s, 4)) for s in ("gape", "grin")} <= outlines
