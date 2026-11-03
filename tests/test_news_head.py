"""Vera's and Gus's heads: the rig on version 2 of the News kit, which follows the speech and never sways.

The head is the kit's default, on a rig whose record must be approved, and a reel that must stay still can say so.
What a still build draws is pinned here by digest.
"""

from __future__ import annotations

import hashlib
import inspect
import math
import re
import xml.etree.ElementTree as ET
from dataclasses import replace
from itertools import pairwise
from pathlib import Path
from types import SimpleNamespace

import pytest
from sr_core.scene import Scene

from srstudio import Canvas, head_motion, news_head, news_inked, news_kit, parts, specimens, toon_head, toon_rigs
from srstudio.head_motion import Speech, Word
from srstudio.news_head import Hold
from srstudio.news_kit import Act, NewsKitError, Pose
from support.spring_curve import peak, sample

ANCHORS = ("vera", "gus")
anchors = pytest.mark.parametrize("who", ANCHORS)

# What perform draws with no rig, on the tree the seven reels were delivered from: the head on one group over the body.
STILL = {
    "vera": "3b3b23cb0f3f623986ab1053fbd8f4287187a5342b0f102b2c2764ca3215892f",
    "gus": "e3a4ca113864576dad36268e2a5d222fd0f8677f9554d061f214289e4e06e0ba",
}


def canvas(seconds: float = 12.0) -> Canvas:
    scene = Scene(version="auto")
    scene.add_project(width=1080, height=1920, fps="30", duration=seconds, background=news_kit.PLUM_DEEP)
    return Canvas(scene, news_kit.NEWS.palette(), font_asset="barlow-condensed")


def speech(at: float, *words: str) -> Speech:
    rows, t = [], at
    for word in words:
        step = 0.4 / len(word)
        chars = tuple((t + k * step, t + (k + 1) * step) for k in range(len(word)))
        rows.append(Word(word, t, t + 0.4, chars, False))
        t += 0.5
    samples = int((t - at) * head_motion.LOUD_RATE) + 2
    return Speech(
        at, tuple(rows), tuple(-30.0 + 10.0 * (int(k * 2 / head_motion.LOUD_RATE) % 3 == 0) for k in range(samples))
    )


# Vera says a line, Gus answers, Vera says the last one
SAID = (
    ("vera", speech(0.5, "seabirds", "get", "jet", "lag")),
    ("gus", speech(3.5, "what", "airline", "exactly")),
    ("vera", speech(7.0, "the", "study", "says", "nothing")),
)


def still_digest(who: str) -> str:
    cv = canvas()
    acts = ((0.0, Pose("level", "talk", head=3.0)), (2.0, Pose("over", "smirk")), (4.0, Pose("side", "flat")))
    visemes = ((0.1, "open"), (0.4, "closed"), (0.8, "wide"), (1.2, "closed"))
    over = cv.group(cv.comp, "front")
    news_inked.perform(cv, cv.comp, who, 262.0, acts, 0.0, 6.0, visemes, scale=1.1, over=over)
    return hashlib.sha256(cv.scene.to_bytes(layout="pretty")).hexdigest()


def rigged(who: str, spans=(), said=SAID, seconds: float = 10.0, acts=None):
    cv = canvas(seconds)
    rig = news_inked.RIGS[f"news-{who}@2"]
    plan = news_head.plan_of(who, rig, said, (), seconds).during(0.0, seconds)
    rows = acts or ((0.0, Pose(mouth="talk")),)
    over = cv.group(cv.comp, "front")
    news_inked.perform(
        cv, cv.comp, who, 262.0, rows, 0.0, seconds, ((0.1, "open"), (0.4, "closed")), over=over,
        motion=(rig, plan), looks=spans,
    )  # fmt: skip
    return cv


def tree(cv: Canvas) -> ET.Element:
    return ET.fromstring(cv.scene.to_bytes(layout="pretty"))


def group(root: ET.Element, prefix: str) -> list[ET.Element]:
    return [g for g in root.iter("group") if str(g.get("id", "")).startswith(prefix)]


def shot(cv: Canvas, who: str, said=SAID, beats=None, end: float = 10.0) -> SimpleNamespace:
    beats = beats or (SimpleNamespace(start=0.0, event=None),)
    return SimpleNamespace(
        cv=cv,
        app=SimpleNamespace(who=who, start=0.0, end=end),
        beats=beats,
        back=cv.group(cv.comp, "back"),
        front=cv.group(cv.comp, "front"),
        mouths={},
        end=end,
        said=lambda: said,
    )


def turned(spans, t: float) -> float:
    return next((side for on, off, side in spans if on <= t <= off), 0.0)


# -- how they move -----------------------------------------------------------------------------------------------------
@anchors
def test_a_style_has_no_idle_at_all(who):
    style = news_inked.RIGS[f"news-{who}@2"].style
    assert (style.idle_roll, style.idle_px, style.breath_px, style.breath_scale, style.avert) == (0, 0, 0, 0, 0)
    plan = head_motion.plan(style, [speech(1.0, "a", "line", "of", "news")], 60.0)
    assert not plan.gaze  # no eye goes anywhere on a timer
    assert {v for _, v in plan.idle_roll.keys} == {0.0} and {v for _, v in plan.idle_y.keys} == {0.0}


def test_vera_is_small_and_rare_and_gus_big_and_late():
    vera, gus = (news_inked.RIGS[f"news-{who}@2"] for who in ANCHORS)
    assert vera.style.nod_px * 3 <= gus.style.nod_px and vera.style.nod_roll * 3 <= gus.style.nod_roll
    assert vera.style.glance_face * 1.5 <= gus.style.glance_face
    assert vera.style.nod_share <= gus.style.nod_share / 2 and vera.style.min_gap >= gus.style.min_gap * 2
    assert vera.lag * 2 <= gus.lag
    line = speech(0.5, *(f"word{k}" for k in range(14)))
    assert len(head_motion.nods(line, vera.style)) < len(head_motion.nods(line, gus.style))
    assert gus.style.head.frequency < vera.style.head.frequency  # a loose neck arrives after the word does


def test_each_style_has_its_own_seed_among_every_rig():
    news = [rig for part, rig in news_inked.RIGS.items() if part.endswith("@2")]  # a later version keeps the seed
    seeds = [r.style.seed for r in (*toon_rigs.RIGS.values(), *news)]
    held = {id(r.style): r.style.seed for r in (*toon_rigs.RIGS.values(), *news)}
    assert len(set(held.values())) == len(held), seeds


@anchors
def test_a_later_rig_keeps_the_anchor_s_nods_on_the_same_takes(who):
    old, new = (news_inked.RIGS[f"news-{who}@{n}"] for n in (2, 3))
    assert new.style.seed == old.style.seed
    before = news_head.plan_of(who, old, SAID, (), 10.0)
    after = news_head.plan_of(who, new, SAID, (), 10.0)
    assert before.nod == after.nod and before.turn == after.turn and before.roll == after.roll


def test_a_plan_with_nothing_to_face_is_the_plan_it_always_was():
    style = news_inked.RIGS["news-gus@2"].style
    line = [speech(0.5, "what", "airline", "exactly")]
    assert head_motion.plan(style, line, 6.0) == head_motion.plan(style, line, 6.0, facing=())


def test_a_plan_turns_the_head_and_the_face_toward_a_side_and_holds_it():
    style = news_inked.RIGS["news-gus@2"].style
    plan = head_motion.plan(style, [], 8.0, facing=((2.0, 6.0, -1.0),))
    assert dict(plan.face_x.keys)[2.5] == -style.glance_face and dict(plan.face_x.keys)[6.0] == -style.glance_face
    assert dict(plan.turn.keys)[2.5] == -style.glance_turn and plan.turn.keys[-1][1] == 0.0


@pytest.mark.parametrize(
    "facing", [((2.0, 2.2, 1.0),), ((2.0, 4.0, 1.0), (3.0, 5.0, 1.0)), ((2.0, 4.0, 2.0),), ((5.0, 3.0, 1.0),)]
)
def test_a_plan_refuses_a_turn_it_cannot_finish(facing):
    with pytest.raises(head_motion.HeadMotionError):
        head_motion.plan(news_inked.RIGS["news-gus@2"].style, [], 8.0, facing=facing)


# -- who they face -----------------------------------------------------------------------------------------------------
@pytest.mark.parametrize(("who", "side"), [("vera", 1.0), ("gus", -1.0)])
def test_an_anchor_turns_to_the_other_when_they_speak(who, side):
    spans = news_head.facing(who, news_inked.RIGS[f"news-{who}@2"], SAID, (), 10.0)
    if who == "vera":
        assert turned(spans, 4.5) == side  # gus's line
        assert turned(spans, 1.0) == 0.0  # her own
    else:
        assert turned(spans, 1.5) == side and turned(spans, 8.0) == side  # hers
        assert turned(spans, 4.5) == 0.0  # his


@anchors
def test_the_own_line_is_said_to_camera(who):
    rig = news_inked.RIGS[f"news-{who}@2"]
    for on, off, _ in news_head.facing(who, rig, SAID, (), 10.0):
        for by, line in SAID:
            if by == who:
                assert not on <= line.words[0].start - rig.back + 0.001 <= off - 0.002


def test_the_turn_comes_after_the_other_starts_and_gus_is_later():
    vera, gus = (news_inked.RIGS[f"news-{who}@2"] for who in ANCHORS)
    assert news_head.facing("vera", vera, SAID, (), 10.0)[0][0] == pytest.approx(3.5 + vera.lag)
    assert news_head.facing("gus", gus, SAID, (), 10.0)[0][0] == pytest.approx(0.5 + gus.lag)


def beats(*events):
    return tuple(SimpleNamespace(start=at, event=name) for at, name in events)


def test_a_hold_keeps_her_turned_across_her_own_line():
    # the came-in-for shape: she turns in a hold, says one line to him, and only the later beat turns her back
    said = (*SAID[:2], ("vera", speech(6.0, "to", "get", "away", "from", "you")), ("vera", speech(9.5, "goodnight")))
    row = beats((0.0, None), (5.0, "turn"), (6.0, "reason"), (9.5, "close"))
    acts = (Act(), Act(holds=(Hold("vera", "gus", "close"),)), Act(), Act())
    holds = news_head.holds_of(acts, row)
    rig = news_inked.RIGS["news-vera@2"]
    spans = news_head.facing("vera", rig, said, holds, 12.0)
    assert turned(spans, 5.8) == 1.0  # in the hold, before the line
    assert turned(spans, 7.0) == 1.0  # through the line, said to him
    assert turned(spans, 8.9) == 1.0  # and on
    assert turned(spans, 9.6) == 0.0  # the line that turns her back


def test_without_the_hold_the_same_line_goes_to_camera():
    said = (*SAID[:2], ("vera", speech(6.0, "to", "get", "away", "from", "you")))
    assert turned(news_head.facing("vera", news_inked.RIGS["news-vera@2"], said, (), 10.0), 7.0) == 0.0


def test_a_hold_can_keep_an_anchor_on_camera_through_the_other_s_line():
    row = beats((0.0, None), (3.0, None), (6.0, "back"))
    acts = (Act(), Act(holds=(Hold("vera", "camera", "back"),)), Act())
    spans = news_head.facing("vera", news_inked.RIGS["news-vera@2"], SAID, news_head.holds_of(acts, row), 10.0)
    assert turned(spans, 4.5) == 0.0


@pytest.mark.parametrize(
    ("hold", "needle"),
    [
        (lambda: Hold("bo", "gus", "close"), "bo"),
        (lambda: Hold("vera", "vera", "close"), "vera"),
        (lambda: Hold("vera", "lamp", "close"), "lamp"),
        (lambda: Hold("vera", "gus", ""), "until"),
    ],
)
def test_a_bad_hold_is_refused_by_name(hold, needle):
    with pytest.raises(NewsKitError, match=needle):
        hold()


def test_a_hold_names_a_later_beat():
    row = beats((0.0, "first"), (3.0, None))
    with pytest.raises(NewsKitError, match="later beat"):
        news_head.holds_of((Act(), Act(holds=(Hold("vera", "gus", "first"),))), row)
    with pytest.raises(NewsKitError, match="later beat"):
        news_head.holds_of((Act(), Act(holds=(Hold("vera", "gus", "nowhere"),))), row)


# -- the drawing -------------------------------------------------------------------------------------------------------
@anchors
def test_no_rig_draws_what_was_delivered(who):
    assert still_digest(who) == STILL[who]


@anchors
def test_a_still_build_draws_no_motion(who):
    cv = canvas()
    news_inked.perform(cv, cv.comp, who, 262.0, ((0.0, Pose()),), 0.0, 6.0)
    assert not group(tree(cv), "head-")


@anchors
def test_the_head_is_nested_one_motion_a_group_over_the_body(who):
    root = tree(rigged(who))
    tilt = group(root, "head-tilt")[0]
    turn = group(root, "head-turn")[0]
    nod = group(root, "head-nod")[0]
    assert turn in list(tilt) and nod in list(turn)
    assert len(group(nod, "head-face")) == 2  # one under the front hair, one over it


@anchors
def test_the_collar_and_tie_stay_on_the_body_and_the_head_goes_alone(who):
    root = tree(rigged(who))
    tilt = group(root, "head-tilt")[0]
    moving = set(tilt.iter())
    still = {n.get("fill") for n in root.iter() if n not in moving}
    hair, jacket = (news_inked.SILVER, news_inked.TEAL) if who == "vera" else (news_inked.HAIR, news_inked.ORANGE)
    head = {n.get("fill") for n in tilt.iter()}
    assert hair in head and hair not in still
    assert jacket in still and jacket not in head


@anchors
def test_the_body_and_the_hands_have_no_motion_of_their_own(who):
    assert news_inked.RIGS[f"news-{who}@2"].style.lean == 0.0
    root = tree(rigged(who))
    moving = set(group(root, "head-tilt")[0].iter())
    keyed = [a.get("property") for g in root.iter("group") if g not in moving for a in g.findall("animate")]
    assert set(keyed) <= {"opacity"}


def viseme_gates(cv: Canvas) -> list[list[tuple[str | None, str | None]]]:
    return [
        [(k.get("time"), k.get("value")) for k in a.iter("key")]
        for a in tree(cv).iter("animate")
        if a.get("property") == "opacity"
    ]


@anchors
def test_the_mouth_keeps_the_viseme_track_exactly(who):
    rows = ((0.0, Pose(mouth="talk")),)
    visemes = ((0.1, "open"), (0.4, "closed"), (0.8, "wide"), (1.2, "closed"))
    still = canvas()
    news_inked.perform(still, still.comp, who, 262.0, rows, 0.0, 6.0, visemes)
    moved = canvas()
    rig = news_inked.RIGS[f"news-{who}@2"]
    plan = news_head.plan_of(who, rig, SAID, (), 10.0).during(0.0, 6.0)
    news_inked.perform(moved, moved.comp, who, 262.0, rows, 0.0, 6.0, visemes, motion=(rig, plan))
    assert viseme_gates(still) == viseme_gates(moved)


def test_the_eyes_go_to_the_side_when_the_head_does_and_only_from_level():
    rows = ((0.0, Pose()), (4.0, Pose("wide")))
    looked = news_inked.side_eyes(rows, [(1.0, 2.0), (3.0, 5.0)], 6.0)
    assert [(at, p.eyes) for at, p in looked] == [
        (0.0, "level"), (1.0, "side"), (2.0, "level"), (3.0, "side"), (4.0, "wide"), (5.0, "wide"),
    ]  # fmt: skip


@anchors
def test_the_seam_stays_shut_at_every_corner_the_style_can_reach(who):
    assert toon_head.open_seam(news_inked.RIGS[f"news-{who}@2"]) == []


def test_a_seam_check_that_cannot_fail_is_no_check():
    rig = news_inked.RIGS["news-gus@2"]
    assert toon_head.open_seam(replace(rig, style=replace(rig.style, nod_px=400.0)))


@anchors
def test_the_plan_never_leaves_what_the_seam_was_proved_for(who):
    rig = news_inked.RIGS[f"news-{who}@2"]
    plan = news_head.plan_of(who, rig, SAID, (), 10.0)
    for name, channel in (("nod", plan.nod), ("roll", plan.roll), ("turn", plan.turn), ("face_x", plan.face_x)):
        assert peak(channel) <= head_motion.limit(rig.style, name) + 1e-6, name


@anchors
def test_a_head_never_jumps_between_two_frames(who):
    rig = news_inked.RIGS[f"news-{who}@2"]
    said = ((who, speech(1.0, *(f"word{k}" for k in range(16)))),)  # a long line, its accents as close as they come
    plan = news_head.plan_of(who, rig, said, (), 12.0)
    nods = [sample(plan.nod, k / 30) for k in range(12 * 30)]
    assert max(abs(b - a) for a, b in zip(nods, nods[1:], strict=False)) <= 5.5
    assert min(nods) >= -0.35 * rig.style.nod_px  # a head goes down on a word, and comes back to rest


@anchors
def test_a_close_up_stays_clear_of_a_two_line_cue_at_the_top_of_the_nod(who):
    rig = news_inked.RIGS[f"news-{who}@2"]
    top = min(y for _, y in rig.outline)
    _, scale = news_inked.FRAMING[who]
    up = head_motion.limit(rig.style, "nod") * 0.45  # the rebound of a nod, the only way a head rises here
    drawn = news_inked.DESK_Y + scale * (top + news_inked.NECK_Y - news_kit.CHIN_Y - up)
    cue = news_kit.CAPTION_TOP + 2 * news_kit.CAPTION_SIZE * news_kit.CAPTION_LEADING + news_kit.CAPTION_PAD
    assert drawn >= cue


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


@pytest.mark.parametrize("reel", ["seabird_jet_lag", "missing_lid"])
def test_a_delivered_reel_names_the_version_it_went_out_on(reel):
    source = (Path(__file__).parents[1] / "episodes" / "pilots" / f"{reel}.py").read_text()
    assert "news_inked.stage(ACTS, version=3)" in source


def test_only_a_published_reel_stays_on_a_version_before_the_hands():
    pinned = sorted(
        path.stem
        for path in (Path(__file__).parents[1] / "episodes" / "pilots").glob("*.py")
        for number in re.findall(r"news_inked\.stage\(ACTS, version=(\d+)\)", path.read_text())
        if int(number) < 6
    )
    assert pinned == ["missing_lid", "seabird_jet_lag"]


@anchors
def test_a_new_version_redraws_nothing_but_the_limits(who):
    name = f"news-{who}"
    assert parts.get(name).version(3).drawing == parts.get(name).version(2).drawing
    assert specimens.digest(name, 3) == specimens.digest(name, 2)
    assert specimens.rig_digest(name, 3) != specimens.rig_digest(name, 2)


@pytest.mark.parametrize(("version", "number"), [(None, 6), (6, 6), (5, 5), (4, 4), (3, 3), (2, 2)])
def test_a_reel_takes_the_latest_rig_and_a_delivered_reel_can_stay_on_its_own(version, number):
    used = []
    real = news_head.plan_of

    def spy(who, rig, *rest):
        used.append(rig)
        return real(who, rig, *rest)

    with pytest.MonkeyPatch.context() as patch:
        patch.setattr(news_head, "plan_of", spy)
        cv = canvas(10.0)
        beats = (SimpleNamespace(start=0.0, event=None),)
        news_inked.stage((Act(Pose(), Pose()),), heads=True, version=version)(shot(cv, "gus", beats=beats))
    assert used == [news_inked.RIGS[f"news-gus@{number}"]]


@pytest.mark.parametrize("number", [3, 4, 5, 6])
def test_a_rig_not_approved_stops_the_stage_on_its_version(monkeypatch, number):
    monkeypatch.setattr(news_head, "approved", lambda who, asked=2: asked != number)
    cv = canvas(10.0)
    beats = (SimpleNamespace(start=0.0, event=None),)
    with pytest.raises(NewsKitError, match=f"news-gus@{number}"):
        news_inked.stage((Act(Pose(), Pose()),), version=number)(shot(cv, "gus", beats=beats))


@anchors
def test_the_same_takes_draw_the_same_head(who):
    assert tree(rigged(who)).find(".//group") is not None
    assert rigged(who).scene.to_bytes(layout="pretty") == rigged(who).scene.to_bytes(layout="pretty")


# -- the shots ---------------------------------------------------------------------------------------------------------
@pytest.mark.parametrize(("who", "seen"), [("desk", 2), ("vera", 1), ("gus", 1), ("phone", 0)])
def test_every_shot_draws_the_heads_it_shows(who, seen):
    cv = canvas(10.0)
    news_inked.stage((Act(Pose(mouth="talk"), Pose(mouth="talk")),))(shot(cv, who))
    assert len(group(tree(cv), "head-nod")) == seen


def test_a_cut_lands_on_a_moving_head():
    cv = canvas(10.0)
    s = shot(cv, "gus")
    s = SimpleNamespace(**{**vars(s), "app": SimpleNamespace(who="gus", start=4.0, end=8.0)})
    news_inked.stage((Act(Pose(mouth="talk"), Pose(mouth="talk")),))(s)
    nod = group(tree(cv), "head-nod")[0]
    times = [float(k.get("time")) for a in nod.iter("animate") for k in a.iter("key")]
    assert min(times) <= 4.0 and max(times) >= 8.0


# -- the record decides ------------------------------------------------------------------------------------------------
def desk(heads: bool = True) -> bytes:
    cv = canvas(10.0)
    news_inked.stage((Act(Pose(mouth="talk"), Pose(mouth="talk")),), heads=heads)(shot(cv, "desk"))
    return cv.scene.to_bytes(layout="pretty")


def test_the_kit_moves_the_heads_by_default():
    assert b"head-nod" in desk()


def test_a_reel_can_stay_still():
    assert b"head-nod" not in desk(heads=False)


def test_a_rig_that_is_not_approved_reaches_no_reel(monkeypatch):
    monkeypatch.setattr(news_head, "approved", lambda who, number=2: False)
    with pytest.raises(NewsKitError, match="not approved"):
        desk()
    assert b"head-nod" not in desk(heads=False)


def test_version_one_of_the_kit_has_no_head_at_all():
    assert "motion" not in inspect.signature(news_kit.perform).parameters
    assert "said" not in news_kit.stage.__code__.co_names


# -- the records -------------------------------------------------------------------------------------------------------
@anchors
def test_the_rig_is_approved_in_the_operator_s_words_and_keeps_its_digest(who):
    name = f"news-{who}"
    held = parts.get(name).version(2).rig
    assert held is not None and held.status == "approved" and held.date == "2026-10-31"
    assert "1793476335.465559" in held.approval.words and "apply it" in held.approval.words
    assert held.proof == "generated/character-proofs/news-head/index.html"
    assert held.drawing == specimens.rig_digest(name, 2)
    assert news_head.approved(who)


@anchors
def test_the_rig_is_a_drawing_outside_the_version(who):
    name = f"news-{who}"
    assert specimens.rig_digest(name, 2) != parts.get(name).version(2).drawing


def test_the_first_version_has_no_rig():
    assert parts.get("news-vera").version(1).rig is None and parts.get("news-gus").version(1).rig is None


def test_every_rig_is_seen_by_the_rig_gate():
    held = {parts.part_name(n, v.number) for n, p in parts.load().items() for v in p.versions if v.rig}
    assert set(news_inked.RIGS) <= held


def test_the_angle_of_a_full_turn_stays_small_enough_to_read():
    for rig in news_inked.RIGS.values():
        assert math.fabs(head_motion.limit(rig.style, "turn")) <= 6.0


def test_a_specimen_shuts_the_mouth_at_each_beat_it_does_not_open_on():
    shown = news_inked.mouths_shown(4.0, 4, [0.0, 1.0, 2.0])
    track = news_inked.mouths_shown(4.0, 4)
    assert (0.0, "closed") not in set(shown) - set(track)  # the first mouth already opens on the first beat
    assert set(shown) - set(track) == {(1.0, "closed"), (2.0, "closed")} - set(track)
    assert [at for at, _ in shown] == sorted(at for at, _ in shown)
    rows = news_kit.mouth_track(tuple((at, Pose(news_kit.EYES[0], "talk")) for at in (0.0, 1.0, 2.0)), shown, 4.0)
    assert dict(rows)[1.0] == "closed" and dict(rows)[2.0] == "closed"  # under any reel policy, not the due state
