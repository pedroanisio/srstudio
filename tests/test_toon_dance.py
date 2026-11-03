"""Toon characters dance (ADR 0190): the dog fitted to its drawing, its groove read from the drawn head against the
measured car dance, faces held by phrase, the head still within a beat, raised arms riding the body, and every way a
dance is refused."""

import math
import xml.etree.ElementTree as ET
from dataclasses import replace
from pathlib import Path

import numpy as np
import pytest
from sr_core.scene import Scene

from srstudio import PEACH, Canvas, brush, toon_head, toon_torso
from srstudio import dance as dn
from srstudio import skeleton as sk
from srstudio import toon_dance as td
from srstudio.errors import SrstudioError
from srstudio.head_motion import HeadPlan, limit
from srstudio.music import Groove
from srstudio.toon import ARMS, Pose, ToonDataError
from srstudio.toon_cast import CENTRE, SHOULDERS, _arms
from srstudio.toon_redrawn import DOG_RIG
from srstudio.toon_torso import depth_in
from support.authoring_docs import fences

GROOVE = Groove(129)
BEAT = GROOVE.beat
FIT = td.DOG_FIT
SEAT = dn.moves()["seat-groove"]
RAISED = FIT.hold(
    {
        "left_upper_arm.down_up": 1.2,
        "left_upper_arm.front_back": 0.0,
        "left_upper_arm.twist_in_out": 0.0,
        "left_lower_arm.stretch": -0.3,
    }
)

PUMP = FIT.hold(  # the pumping arm lifted to the side and unbent, so the pump rises from shoulder height
    {
        "right_upper_arm.down_up": -0.6,
        "right_upper_arm.front_back": 0.0,
        "right_upper_arm.twist_in_out": 0.0,
        "right_lower_arm.stretch": 0.0,
    }
)


def pump(bars: int = 2) -> td.ToonDance:
    """The arm pump on the dog's right arm, held up off the desk as a desk rest needs."""
    routine = dn.Routine(bars, (dn.Entry(0, bars, dn.moves()["arm-pump"], hold=PUMP),))
    return td.perform(FIT, routine, GROOVE, 0.0, 4 * bars * BEAT)


def routine() -> dn.Routine:
    return dn.Routine(
        4,
        (
            dn.Entry(0, 2, SEAT, expression="grin"),
            dn.Entry(2, 4, SEAT, transition_beats=1, expression="smirk", hold=RAISED),
        ),
    )


@pytest.fixture(scope="module")
def grooving() -> td.ToonDance:
    return td.perform(FIT, SEAT, GROOVE, 0.0, 32 * BEAT)


@pytest.fixture(scope="module")
def raised() -> td.ToonDance:
    return td.perform(FIT, routine(), GROOVE, 0.0, 16 * BEAT)


def canvas(duration: float) -> tuple[Scene, Canvas]:
    scene = Scene(version="auto")
    scene.add_project(width=1080, height=1920, fps="25", duration=duration, background=PEACH.background)
    return scene, Canvas(scene, PEACH, font_asset=None)


# --- the fit ------------------------------------------------------------------------------------------------------


def test_the_dog_is_fitted_to_its_drawing():
    world = sk.world(FIT.profile, FIT.base)
    assert FIT.screen(world["hips"].origin) == pytest.approx(FIT.seat)
    assert FIT.screen(world["head"].origin) == pytest.approx(DOG_RIG.neck, abs=0.5)  # the rig's neck pivot
    for side in ("left", "right"):  # elbows and wrists on the approved desk arm: the character's left is screen-right
        desk = FIT.desk(side)
        assert FIT.screen(world[f"{side}_lower_arm"].origin) == pytest.approx(desk.elbow, abs=td.FIT_TOLERANCE)
        assert FIT.screen(world[f"{side}_hand"].origin) == pytest.approx(desk.wrist, abs=td.FIT_TOLERANCE)
    assert FIT.desk("left").wrist == pytest.approx((246, 792)) and FIT.desk("right").wrist == pytest.approx((124, 792))
    assert FIT.radius == pytest.approx(128) and not FIT.legs and FIT.part == "toon-dog@2"


def test_a_fit_that_misses_the_drawing_is_refused():
    with pytest.raises(td.ToonFitError, match="neck"):
        replace(FIT, scale=380.0)
    with pytest.raises(td.ToonFitError, match="scale"):
        replace(FIT, scale=0)
    with pytest.raises(td.ToonFitError, match="faces"):
        replace(FIT, faces=(("grin", td.Face("wide", "grin")), ("grin", td.Face("half", "grin"))))
    with pytest.raises(td.ToonFitError, match="rest face"):
        replace(FIT, rest_face="wide")
    armless = sk.SkeletonProfile("armless", FIT.profile.proportions, hands=("none", "mitten"), omit=("left_upper_arm",))
    with pytest.raises(td.ToonFitError, match="both arms"):
        replace(FIT, profile=armless)
    rest = dict(FIT.profile.rest) | {"left_lower_arm.stretch": -0.5}
    with pytest.raises(td.ToonFitError, match="desk arm"):
        replace(FIT, profile=replace(FIT.profile, rest=tuple(rest.items())))
    wide = replace(FIT.profile.proportions, lengths=(*FIT.profile.proportions.lengths[:2], ("clavicle", 0.4)))
    with pytest.raises(td.ToonFitError, match="inside"):
        replace(FIT, profile=replace(FIT.profile, proportions=wide))
    with pytest.raises(td.ToonFitError, match="torso"):
        replace(FIT, rig=replace(DOG_RIG, look=replace(DOG_RIG.look, drawing=None)))  # no torso to draw arms from


@pytest.mark.parametrize(
    ("kw", "match"),
    [
        ({"eyes": "squint", "mouth": "grin"}, "eyes"),
        ({"eyes": "wide", "mouth": "beak"}, "mouth"),
        ({"eyes": "wide", "mouth": "grin", "wear": ("hat",)}, "wear"),
        ({"eyes": "wide", "mouth": "grin", "wear": ["glasses"]}, "wear"),
    ],
)
def test_a_face_names_only_toon_parts(kw, match):
    with pytest.raises(td.ToonFitError, match=match):
        td.Face(**kw)


def test_a_hold_reaches_absolute_values_from_the_rest():
    hold = dict(RAISED)
    rest = dict(FIT.profile.rest)
    assert hold["left_upper_arm.down_up"] == pytest.approx(1.2 - rest["left_upper_arm.down_up"])
    with pytest.raises(td.ToonFitError, match="not a control"):
        FIT.hold({"left_upper_leg.front_back": 0.3})  # the dog has no legs
    with pytest.raises(td.ToonFitError, match="number"):
        FIT.hold({"left_upper_arm.down_up": "up"})


def test_every_error_is_a_srstudio_error():
    for error in (td.ToonFitError, td.ExpressionError, td.SupportError, td.HeadReachError):
        assert issubclass(error, td.ToonDanceError)
    assert issubclass(td.ToonDanceError, SrstudioError) and issubclass(td.ToonDanceError, ValueError)


# --- the groove, read from the drawn head ------------------------------------------------------------------------


def test_the_drawn_head_bobs_like_the_reel(grooving):
    reading = grooving.measure("bob", hit="min")
    assert dn.SEAT_GROOVE_BOB.misses(reading) == ()
    assert reading.fall == pytest.approx(0.19, abs=0.02) and reading.rise == pytest.approx(0.26, abs=0.02)
    assert abs(reading.hit_offset) * BEAT <= 0.02  # the drop lands on the beat


def test_the_drawn_head_sways_like_the_reel(grooving):
    reading = grooving.measure("sway")
    assert dn.SEAT_GROOVE_SWAY.misses(reading) == ()
    assert reading.onto == pytest.approx(0.12, abs=0.025)


def test_the_head_holds_its_angle_and_moves_only_with_the_body(grooving):
    assert all(p.turn == p.nod == p.face_x == 0 or max(abs(p.turn), abs(p.nod), abs(p.face_x)) < 1e-9
               for p in grooving.pictures)  # fmt: skip
    assert grooving.plan() == HeadPlan()
    assert {p.lean for p in grooving.pictures} == {0.0}  # seat-groove leaves the spine alone
    first = grooving.pictures[0]
    bob = grooving.series("bob")[0] * FIT.radius
    assert first.shift[1] == pytest.approx(-bob)  # the head is carried by the body's own shift
    assert len(grooving.pictures) == math.ceil(32 * BEAT * 25 - 1e-9)


def test_the_series_axis_is_bob_or_sway(grooving):
    with pytest.raises(td.ToonDanceError, match="axis"):
        grooving.series("roll")


# --- faces by phrase ---------------------------------------------------------------------------------------------


def test_faces_switch_where_the_phrases_do(raised):
    poses = raised.poses()
    assert [(round(p.start, 6), p.eyes, p.mouth, p.arms) for p in poses] == [
        (0.0, "wide", "grin", "desk"),
        (round(math.ceil(8 * BEAT * 25 - 1e-9) / 25, 6), "half", "smirk", "desk"),
    ]
    assert poses[1].start == pytest.approx(8 * BEAT, abs=1 / 25)  # the first picture of bar 2


def test_a_rest_with_no_expression_holds_the_rest_face():
    poses = td.perform(FIT, SEAT, GROOVE, 0.0, 4 * BEAT).poses()
    assert poses == (Pose(0.0, "wide", "flat", "desk"),)


def test_an_unknown_expression_is_refused_before_dancing():
    sour = dn.Routine(8, (dn.Entry(0, 4, SEAT), dn.Entry(4, 8, SEAT, expression="sulk")))
    with pytest.raises(td.ExpressionError, match="sulk"):
        td.perform(FIT, sour, GROOVE, 0.0, 4 * BEAT)  # the face is past the span, still refused
    with pytest.raises(td.ExpressionError):
        FIT.face("sulk")


# --- the arms: the approved v2 arm, posed on the skeleton --------------------------------------------------------
#
# The approved still is toon-dog@2 with its desk arms, drawn by the critter's own torso (toon_cast._arms through
# Critter.limb). Every threshold below is measured on that art at test time, never typed in.

SIDES = ("left", "right")  # anatomical: the character's left is screen-right


def polygon(shape, steps: int = 8) -> list[tuple[float, float]]:
    """A brush shape (a start point, then cubic segments) as a polygon."""
    points = [(shape[0], shape[1])]
    for i in range(2, len(shape), 6):
        (x0, y0), (x1, y1, x2, y2, x3, y3) = points[-1], shape[i : i + 6]
        for k in range(1, steps + 1):
            t = k / steps
            a, b, c, d = (1 - t) ** 3, 3 * (1 - t) ** 2 * t, 3 * (1 - t) * t**2, t**3
            points.append((a * x0 + b * x1 + c * x2 + d * x3, a * y0 + b * y1 + c * y2 + d * y3))
    return points


def mask(layers, shift=(0.0, 0.0), zoom: int = 4) -> np.ndarray:
    """Where ``layers`` draw anything, at ``zoom`` pixels to the reference pixel, over the arms' region."""
    from PIL import Image, ImageDraw

    picture = Image.new("1", (380 * zoom, 260 * zoom), 0)
    pen = ImageDraw.Draw(picture)
    for shape, _ in layers:
        pen.polygon([((x + shift[0]) * zoom, (y + shift[1] - 620) * zoom) for x, y in polygon(shape)], fill=1)
    return np.asarray(picture, dtype=bool)


def iou(a: np.ndarray, b: np.ndarray) -> float:
    return float((a & b).sum()) / float((a | b).sum())


def approved_arms() -> list:
    """The approved still's desk arms, as the v2 drawing draws them."""
    under, over = _arms(DOG_RIG.look, "desk", 0)
    assert over == []
    return under


def width(shape, a, b) -> float:
    """The width of a stroke ``shape`` across the middle of the segment ``a``-``b``, along its normal."""
    mx, my = (a[0] + b[0]) / 2, (a[1] + b[1]) / 2
    length = math.dist(a, b)
    nx, ny = -(b[1] - a[1]) / length, (b[0] - a[0]) / length
    hits = []
    edge = polygon(shape)
    for (x0, y0), (x1, y1) in zip(edge, [*edge[1:], edge[0]], strict=True):
        dx, dy = x1 - x0, y1 - y0
        den = nx * dy - ny * dx
        if abs(den) < 1e-12:
            continue
        t = ((x0 - mx) * dy - (y0 - my) * dx) / den  # along the normal
        u = ((x0 - mx) * ny - (y0 - my) * nx) / den  # along the edge
        if 0 <= u <= 1:
            hits.append(t)
    return min(t for t in hits if t > 0) - max(t for t in hits if t < 0)


def test_the_shoulders_sit_inside_the_drawn_body():
    torso = DOG_RIG.look.drawing.torso
    # Every approved arm leaves the body at one root per side, whatever its pose: that root's depth is the bar.
    roots = [torso.arm_path([shoulder, (CENTRE, 800.0)])[0] for shoulder in SHOULDERS]
    deepest = min(depth_in(torso.contour, root)[0] for root in roots)
    assert deepest > 0
    world = sk.world(FIT.profile, FIT.base)
    for side in SIDES:
        ball = FIT.screen(world[f"{side}_upper_arm"].origin)
        assert depth_in(torso.contour, ball)[0] >= deepest, (side, ball)
        assert depth_in(torso.contour, FIT.arm(FIT.base, side).root)[0] >= deepest - 1e-9


def test_at_rest_the_arms_are_the_approved_still():
    approved = mask(approved_arms())
    # What one reference pixel of drift (the fit's own tolerance) costs the approved art against itself: the bar.
    bar = min(iou(approved, mask(approved_arms(), shift)) for shift in ((1, 0), (0, 1), (0.7, 0.7)))
    rest = [layer for side in SIDES for layer in FIT.arm_layers(FIT.arm(FIT.base, side))]
    assert 0.8 < bar < 1.0
    assert iou(approved, mask(rest)) >= bar
    for side in SIDES:
        arm, desk = FIT.arm(FIT.base, side), FIT.desk(side)
        for got, want in zip(
            (arm.root, arm.elbow, arm.wrist, arm.paw), (desk.root, desk.elbow, desk.wrist, desk.paw), strict=True
        ):
            assert got == pytest.approx(want, abs=td.FIT_TOLERANCE)


def approved_bones(monkeypatch) -> tuple[float, list[tuple[float, float]]]:
    """Every bone the approved drawing draws in a two-bone arm, in every arm pose it has: the shortest one's drawn
    length, and the coat's width across the middle of the upper arm and of the forearm, (least, most) in head radii."""
    seen: list[tuple[list, list]] = []
    drawn = toon_torso.Torso.drawn

    def spy(self, path, *args, **kwargs):
        out = drawn(self, path, *args, **kwargs)
        seen.append((list(path), out[0]))
        return out

    monkeypatch.setattr(toon_torso.Torso, "drawn", spy)
    for pose in ARMS:
        for frame in (0, 1):
            _arms(DOG_RIG.look, pose, frame)
    monkeypatch.undo()
    bones: list[list[float]] = [[], []]
    shortest = math.inf
    for path, layers in seen:
        if len(path) != 3:  # an arm bent twice (typing, crossed) has no single upper arm and forearm
            continue
        for bone, (a, b) in enumerate(zip(path, path[1:], strict=False)):
            shortest = min(shortest, math.dist(a, b))
            bones[bone].append(width(layers[1][0], a, b) / FIT.radius)
    return shortest, [(min(bone), max(bone)) for bone in bones]


def test_the_arm_is_as_thick_as_the_approved_arm(raised, monkeypatch):
    # The bar is the approved drawing itself: across all its two-bone arm poses, its upper arm measures between the
    # least and the most of these widths, and its forearm the same. A bone drawn shorter than any the approved drawing
    # draws (foreshortened, pointing at the camera) has no approved width to hold it to: its middle lies in the bend.
    shortest, (upper, forearm) = approved_bones(monkeypatch)
    assert upper[1] < forearm[0]  # the approved arm widens from the body to the paw
    measured = 0
    for performance in (raised, pump()):
        for side in SIDES:
            for arm in performance.arms(side):
                coat = FIT.arm_layers(arm)[1][0]
                for (low, high), (a, b) in zip(
                    (upper, forearm), ((arm.root, arm.elbow), (arm.elbow, arm.wrist)), strict=True
                ):
                    if math.dist(a, b) < shortest:
                        continue
                    measured += 1
                    assert low <= width(coat, a, b) / FIT.radius <= high, (side, arm)
    assert measured > 1000
    # The old arm, one even tube 29 px wide, is outside both: no taper from the body to the paw.
    assert not upper[0] <= 29 / FIT.radius <= upper[1]


def test_no_joint_caps_are_drawn(raised):
    shapes = [colour for _, colour in FIT.arm_layers(FIT.desk("left"))]
    assert shapes == [colour for _, colour in approved_arms()[: len(shapes)]]  # the approved arm's own layers
    for side in SIDES:
        for arm in raised.arms(side):
            assert [colour for _, colour in FIT.arm_layers(arm)] == shapes  # no ball at a joint, no fingers
    scene, cv = canvas(16 * BEAT)
    td.draw(cv, cv.comp, raised)
    root = ET.fromstring(scene.to_bytes())
    arms = [e for e in root.iter() if (e.get("id") or "").startswith("arm-")]
    assert arms and all(sum(1 for c in e if not c.tag.endswith("animate")) == len(shapes) for e in arms)


def test_the_drawn_paw_keeps_the_skeletons_speed_and_acceleration():
    pumping = pump()
    beat = [i for i, p in enumerate(pumping.pictures) if 5 * BEAT <= p.time < 6 * BEAT]
    side = "right"
    _, carried = FIT.carried(side)
    on_skeleton, drawn = [], []
    arms = pumping.arms(side)
    for i in beat:
        hand = sk.world(FIT.profile, pumping.pictures[i].pose)[f"{side}_hand"]
        on_skeleton.append(FIT.screen(hand.origin + hand.rotation.rotate(carried)))
        coat = FIT.arm_layers(arms[i])[4][0]  # the paw's fill, a symmetric oval round the paw
        x0, y0, x1, y1 = brush.bounds(coat)
        drawn.append(((x0 + x1) / 2, (y0 + y1) / 2))
    a, b = np.asarray(on_skeleton), np.asarray(drawn)
    speed = np.gradient(a, 1 / 25, axis=0)
    assert np.linalg.norm(speed, axis=1).max() > 100  # the pump moves: reference pixels a second
    # A drawn coordinate is rounded to 0.01 px: that rounding, differenced, is all the drawing may add.
    q = 0.005
    assert np.abs(np.gradient(b, 1 / 25, axis=0) - speed).max() <= 2 * q * 25
    accel = np.gradient(speed, 1 / 25, axis=0)
    assert np.abs(np.gradient(np.gradient(b, 1 / 25, axis=0), 1 / 25, axis=0) - accel).max() <= 4 * q * 25**2


def test_every_picture_draws_its_own_arm_on_its_own_frame(raised):
    scene, cv = canvas(16 * BEAT)
    td.draw(cv, cv.comp, raised)
    root = ET.fromstring(scene.to_bytes())
    arms = raised.arms("left")
    starts = sorted(float(e.get("start")) for e in root.iter() if (e.get("id") or "").startswith("arm-left-"))
    changes = [round(p.time, 6) for i, (p, a) in enumerate(zip(raised.pictures, arms, strict=True))
               if i == 0 or a != arms[i - 1]]  # fmt: skip
    assert starts == pytest.approx(changes, abs=1e-6)  # a new drawing exactly where the skeleton moved, never held


def test_a_raised_arm_rides_the_body_with_no_lag(raised):
    arms = raised.arms("left")
    span = [i for i, p in enumerate(raised.pictures) if p.time >= 12 * BEAT]  # bars 3..4: the arm is up
    assert all(arms[i].raised and arms[i].wrist[1] < arms[i].root[1] for i in span)
    drawn = [arms[i].paw[1] + raised.pictures[i].shift[1] for i in span]
    hand = [-(y - drawn[0]) / FIT.radius for y in drawn]
    head = [raised.series("bob")[i] for i in span]
    start = raised.pictures[span[0]].time
    on_hand = dn.measure_dance(hand, 25, GROOVE, start=start, hit="min")
    on_head = dn.measure_dance(head, 25, GROOVE, start=start, hit="min")
    assert abs(on_hand.hit_beats - on_head.hit_beats) * BEAT <= 0.02  # the paw drops with the head
    assert on_hand.cycles_per_beat == pytest.approx(1, abs=0.02)
    assert not any(a.raised for a in raised.arms("right"))


def test_the_arms_play_the_skeleton_exactly_from_the_first_picture(raised):
    for side in SIDES:
        arms = raised.arms(side)
        assert len(arms) == len(raised.pictures)
        for i in (0, 1, len(raised.pictures) - 1):
            world = sk.world(FIT.profile, raised.pictures[i].pose)
            assert arms[i].elbow == FIT.screen(world[f"{side}_lower_arm"].origin)
            assert arms[i].wrist == FIT.screen(world[f"{side}_hand"].origin)


def test_the_body_undone_keeps_the_hips_at_the_seat(raised):
    for p in raised.pictures[::17]:
        hips = sk.world(FIT.profile, p.pose)["hips"].origin
        assert FIT.screen(hips) == pytest.approx(FIT.seat, abs=1e-6)


# --- the head beyond the body ------------------------------------------------------------------------------------


def test_a_nod_drives_the_rig_within_its_envelope():
    nodding = td.perform(FIT, dn.moves()["head-nod"], GROOVE, 0.0, 8 * BEAT)
    nods = [p.nod for p in nodding.pictures]
    assert max(nods) > 5 and max(abs(n) for n in nods) <= limit(DOG_RIG.style, "nod")
    assert all(abs(p.turn) < 1e-6 for p in nodding.pictures)  # a nod pitches; it does not tilt the head
    plan = nodding.plan()
    assert plan.nod.curve == "hold" and plan.nod.keys[0][0] == 0.0 and plan.turn.keys == ()
    plan.check_bounds(DOG_RIG.style)
    assert nodding.measure("bob").cycles_per_beat == pytest.approx(1, abs=0.02)  # the drawn skull drops on the beat


def test_a_head_past_the_envelope_is_refused_or_clamped_when_asked():
    tilt = dn.Move("tilt", "either", (dn.Pattern("head.tilt_left_right", 0.3),))
    with pytest.raises(td.HeadReachError, match="turn"):
        td.perform(FIT, tilt, GROOVE, 0.0, 4 * BEAT)
    held = td.perform(FIT, tilt, GROOVE, 0.0, 4 * BEAT, clamp=True)
    bound = limit(DOG_RIG.style, "turn")
    assert held.clamped > 0 and max(abs(p.turn) for p in held.pictures) == pytest.approx(bound)
    held.plan().check_bounds(DOG_RIG.style)


def test_a_spine_lean_turns_the_whole_body_about_the_seat():
    lean = dn.Move("lean", "either", (dn.Pattern("spine.left_right", 0.1),))
    leaning = td.perform(FIT, lean, GROOVE, 0.0, 4 * BEAT)
    assert max(abs(p.lean) for p in leaning.pictures) > 3
    # The drawn trunk is rigid from the seat to the neck, so it turns by the chord; the head adds the rest of the
    # spine's bend, which starts above the seat: together they turn the head by the whole bend.
    assert max(abs(p.turn) for p in leaning.pictures) < 1
    assert max(abs(p.lean + p.turn) for p in leaning.pictures) == pytest.approx(math.degrees(0.1), abs=0.05)


# --- refusals ----------------------------------------------------------------------------------------------------


def test_a_standing_move_is_refused_on_a_seated_dog():
    with pytest.raises(td.SupportError, match="standing"):
        td.perform(FIT, dn.moves()["bob"], GROOVE, 0.0, 4 * BEAT)
    standing = dn.Routine(2, (dn.Entry(0, 2, dn.moves()["step-touch"]),))
    with pytest.raises(td.SupportError):
        td.perform(FIT, standing, GROOVE, 0.0, 4 * BEAT)


@pytest.mark.parametrize(("kw", "match"), [({"fps": 0}, "fps"), ({"fps": 25.0}, "fps"), ({"clamp": 1}, "clamp")])
def test_bad_arguments_are_refused(kw, match):
    with pytest.raises(td.ToonDanceError, match=match):
        td.perform(FIT, SEAT, GROOVE, 0.0, BEAT, **kw)


def test_a_dance_needs_a_fit():
    with pytest.raises(td.ToonDanceError, match="ToonFit"):
        td.perform(DOG_RIG, SEAT, GROOVE, 0.0, BEAT)


def test_a_dance_drops_what_the_dog_has_no_joint_for():
    pumping = pump(1)
    assert "right_index_proximal.stretched" in pumping.dropped  # a mitten has no index finger


# --- drawing -----------------------------------------------------------------------------------------------------


def test_the_dance_draws_as_one_figure_with_its_arms_replaced(raised):
    scene, cv = canvas(16 * BEAT)
    body = td.draw(cv, cv.comp, raised)
    assert [f for f in scene.check() if f.severity == "error"] == []
    root = ET.fromstring(scene.to_bytes())
    node = next(e for e in root.iter() if e.get("id") == body.id)
    animated = {a.get("property") for a in node if a.tag.endswith("animate")}
    assert {"x", "y"} <= animated and "rotation" not in animated  # seat-groove shifts; nothing leans
    ids = [e.get("id") or "" for e in root.iter()]
    assert any(i.startswith("arm-left-") and i.endswith("-front") for i in ids)  # the raised left paw over the head
    assert not any(i.startswith("arm-right-") and i.endswith("-front") for i in ids)
    assert sum(1 for i in ids if i.startswith("arm-")) >= len(raised.pictures)  # the arms move on every picture


def test_a_still_body_animates_nothing():
    still = dn.Move("still", "either", (dn.Pattern("left_hand.in_out", 0.05),))
    scene, cv = canvas(2 * BEAT)
    body = td.draw(cv, cv.comp, td.perform(FIT, still, GROOVE, 0.0, 2 * BEAT))
    root = ET.fromstring(scene.to_bytes())
    node = next(e for e in root.iter() if e.get("id") == body.id)
    assert not [a for a in node if a.tag.endswith("animate")]


def test_a_figure_with_its_own_arms_holds_the_desk_arms():
    scene, cv = canvas(16 * BEAT)
    with pytest.raises(ToonDataError, match="desk poses only"):
        toon_head.figure(
            cv,
            cv.comp,
            DOG_RIG,
            (Pose(0.0, "wide", "flat", "crossed"),),
            16 * BEAT,
            HeadPlan(),
            arms=lambda body, front: None,
        )


def test_a_figure_with_its_own_arms_records_one_hand_per_arm(raised):
    from srstudio import anatomy_ledger

    scene, cv = canvas(16 * BEAT)
    td.draw(cv, cv.comp, raised)
    runs = len(raised.poses())
    hands = [limb for limb in cv.limbs.values() if limb.owner == DOG_RIG.look.name]
    assert len(hands) == 2 * runs  # the dance's two paws in every pose run, no desk arm's paw beside them
    assert anatomy_ledger.notes(cv) == []


# --- the rendered check ------------------------------------------------------------------------------------------


def disc(cx: float, cy: float, size=(120, 160)) -> np.ndarray:
    rows, cols = np.indices(size)
    picture = np.full((*size, 3), 240, dtype=np.uint8)
    picture[(cols - cx) ** 2 + (rows - cy) ** 2 <= 20**2] = (20, 20, 20)
    return picture


def test_the_silhouette_reads_bob_and_sway_in_head_radii():
    bob, sway = td.silhouette_series([disc(60, 80), disc(55, 70), disc(65, 90)], (240, 240, 240), 10.0)
    assert bob == pytest.approx([0.0, 1.0, -1.0], abs=0.02)  # up is positive
    assert sway == pytest.approx([0.0, 0.5, -0.5], abs=0.02)  # screen-left is the character's right


@pytest.mark.parametrize(
    ("pictures", "radius", "match"),
    [
        ([], 10.0, "no pictures"),
        ([disc(60, 80)], 0, "radius"),
        ([np.zeros((4, 4))], 10.0, "RGB"),
        ([np.full((4, 4, 3), 240, dtype=np.uint8)], 10.0, "nothing but the background"),
    ],
)
def test_the_silhouette_refuses_what_it_cannot_read(pictures, radius, match):
    with pytest.raises(td.ToonDanceError, match=match):
        td.silhouette_series(pictures, (240, 240, 240), radius)


def test_a_dance_is_cut_to_a_span_inside_it(grooving):
    cut = grooving.during(4 * BEAT, 12 * BEAT)
    assert cut.pictures[0].time >= 4 * BEAT - 1e-9 and cut.pictures[-1].time < 12 * BEAT
    assert dn.SEAT_GROOVE_BOB.misses(cut.measure("bob", hit="min")) == ()
    with pytest.raises(td.ToonDanceError, match="inside"):
        grooving.during(0.0, 40 * BEAT)


def test_the_guides_recipe_runs():
    guide = (Path(__file__).resolve().parents[1] / "docs" / "authoring-toon-dance.md").read_text()
    recipes = [code for language, code in fences(guide) if language == "python"]
    assert len(recipes) == 1
    exec(compile(recipes[0], "authoring-toon-dance.md", "exec"), {})
