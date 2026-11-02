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

from srstudio import PEACH, Canvas, toon_head
from srstudio import dance as dn
from srstudio import skeleton as sk
from srstudio import toon_dance as td
from srstudio.errors import SrstudioError
from srstudio.head_motion import HeadPlan, limit
from srstudio.music import Groove
from srstudio.toon import Pose, ToonDataError
from srstudio.toon_redrawn import DOG_RIG
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
    assert FIT.screen(world["right_upper_arm"].origin) == pytest.approx((62, 712), abs=1)  # the drawn shoulders
    assert FIT.screen(world["left_upper_arm"].origin) == pytest.approx((308, 712), abs=1)
    assert FIT.screen(world["right_hand"].origin) == pytest.approx((124, 792), abs=1)  # resting at the desk paws
    assert FIT.screen(world["left_hand"].origin) == pytest.approx((246, 792), abs=1)
    assert FIT.radius == pytest.approx(128) and not FIT.legs and FIT.part == "toon-dog@2"


def test_a_fit_that_misses_the_drawing_is_refused():
    with pytest.raises(td.ToonFitError, match="neck"):
        replace(FIT, scale=380.0)
    with pytest.raises(td.ToonFitError, match="scale"):
        replace(FIT, scale=0)
    with pytest.raises(td.ToonFitError, match="arm width"):
        replace(FIT, arm_width=-1.0)
    with pytest.raises(td.ToonFitError, match="faces"):
        replace(FIT, faces=(("grin", td.Face("wide", "grin")), ("grin", td.Face("half", "grin"))))
    with pytest.raises(td.ToonFitError, match="rest face"):
        replace(FIT, rest_face="wide")
    armless = sk.SkeletonProfile("armless", FIT.profile.proportions, hands=("none", "mitten"), omit=("left_upper_arm",))
    with pytest.raises(td.ToonFitError, match="both arms"):
        replace(FIT, profile=armless)


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


# --- the arms ----------------------------------------------------------------------------------------------------


def test_a_raised_arm_rides_the_body_with_no_lag(raised):
    tracks = raised.tracks()
    left = next(t for t in tracks if t.motion.arm.side == "left")
    span = [i for i, p in enumerate(raised.pictures) if p.time >= 12 * BEAT]  # bars 3..4: the arm is up
    wrists = [left.motion.sample(i / 25).arm.wrist for i in span]
    shoulders = [left.motion.sample(i / 25).arm.shoulder for i in span]
    assert all(w.y < s.y for w, s in zip(wrists, shoulders, strict=True))  # above the shoulder: raised
    drawn = []
    for i, w in zip(span, wrists, strict=True):
        p = raised.pictures[i]
        x, y = FIT.screen(w)
        drawn.append((p.time, y + p.shift[1]))
    hand = [-(y - drawn[0][1]) / FIT.radius for _, y in drawn]
    head = [raised.series("bob")[i] for i in span]
    start = raised.pictures[span[0]].time
    on_hand = dn.measure_dance(hand, 25, GROOVE, start=start, hit="min")
    on_head = dn.measure_dance(head, 25, GROOVE, start=start, hit="min")
    assert abs(on_hand.hit_beats - on_head.hit_beats) * BEAT <= 0.02  # the hand drops with the head
    assert on_hand.cycles_per_beat == pytest.approx(1, abs=0.02)


def test_the_tracks_play_the_skeleton_exactly_from_the_first_picture(raised):
    for track in raised.tracks():
        side = track.motion.arm.side
        for i in (0, 1, len(raised.pictures) - 1):
            sample = track.motion.sample(i / 25)
            arm = sk.to_arm_pose(FIT.profile, raised.pictures[i].pose, side)
            assert sample.arm.wrist == arm.wrist and sample.time == i / 25
        assert track.options.offset == 0.0 and track.options.fps == 25
        assert track.motion.sample(1e6).arm == track.motion.sample((len(raised.pictures) - 1) / 25).arm
    left = next(t for t in raised.tracks() if t.motion.arm.side == "left")
    assert left.occlusion and all(o.layer == "front" for o in left.occlusion)  # the raised hand draws over the head
    right = next(t for t in raised.tracks() if t.motion.arm.side == "right")
    assert right.occlusion == ()


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
    pumping = td.perform(FIT, dn.moves()["arm-pump"], GROOVE, 0.0, 4 * BEAT)
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
    assert any(i.endswith("-left-front") for i in ids)  # the raised left hand drawn in front
    assert sum(1 for i in ids if "-frame-" in i) >= len(raised.pictures)  # one drawing per picture per arm layer


def test_a_still_body_animates_nothing():
    still = dn.Move("still", "either", (dn.Pattern("left_hand.in_out", 0.05),))
    scene, cv = canvas(2 * BEAT)
    body = td.draw(cv, cv.comp, td.perform(FIT, still, GROOVE, 0.0, 2 * BEAT))
    root = ET.fromstring(scene.to_bytes())
    node = next(e for e in root.iter() if e.get("id") == body.id)
    assert not [a for a in node if a.tag.endswith("animate")]


def test_a_figure_with_tracks_holds_the_desk_arms(raised):
    scene, cv = canvas(16 * BEAT)
    with pytest.raises(ToonDataError, match="desk poses only"):
        toon_head.figure(
            cv, cv.comp, DOG_RIG, (Pose(0.0, "wide", "flat", "crossed"),), 16 * BEAT, HeadPlan(), limbs=raised.tracks()
        )


def test_a_figure_with_tracks_records_one_hand_per_arm(raised):
    from srstudio import anatomy_ledger

    scene, cv = canvas(16 * BEAT)
    td.draw(cv, cv.comp, raised)
    runs = len(raised.poses())
    hands = [limb for limb in cv.limbs.values() if limb.owner == DOG_RIG.look.name]
    assert len(hands) == 2 * runs  # the two tracks' hands in every pose run, no drawn arm's hand beside them
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
