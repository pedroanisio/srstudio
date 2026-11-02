"""A dance on the floor (ADR 0194): planted feet that hold while the body travels and turns, the centre of mass kept
over the feet that carry it, a shared pass any style can run on its dance frames, and an ensemble in a formation.

Bounds, not lengths: the presets' proportions may change, and every check here holds by a bound on any of them."""

import math
from functools import cache

import pytest

from srstudio import body, dance, dance_floor
from srstudio import skeleton as sk
from srstudio._floor_body import ball_of, centre_of_mass, floor_of, margin, sole, support, toes_offset
from srstudio.dance import Entry, Floor, Key, Phrase, Routine
from srstudio.dance_floor import (
    BalanceError,
    BalanceFinding,
    Dancer,
    FloorError,
    FloorFrame,
    FloorLimitError,
    Performance,
    Slip,
    Spot,
    ensemble,
    formation,
    ground,
    knee_bend,
    perform,
    plant,
    seated,
    stance,
)
from srstudio.dance_pose import dance_pose
from srstudio.errors import SrstudioError
from srstudio.music import Groove

FEET = frozenset({"left_foot", "right_foot"})
LEFT = frozenset({"left_foot"})
CLASS = Groove(122.65)
FPS = 50
SLIP_M = 0.002  # a planted foot's ball and ankle hold within 2 mm at 50 pictures a second
UP = sk.Vec3(0.0, 1.0, 0.0)


@cache
def performed(name: str, preset: str) -> Performance:
    run = perform(dance.phrases()[name], sk.preset(preset), CLASS)
    run.frames(FPS)
    return run


# --- the support polygon: body's public geometry -----------------------------------------------------------------


def _set(pose, up=0.0, values=None):
    """``pose`` raised by ``up`` metres (y points down), with ``values`` in place of its own."""
    root = sk.Frame(pose.root.origin - sk.Vec3(0.0, up, 0.0), pose.root.rotation)
    return sk.SkeletonPose(root, pose.values if values is None else values)


def test_the_support_is_the_skeleton_bridges_support_on_the_floor():
    profile = sk.preset("realistic")
    rest = sk.rest_pose(profile)
    floor = floor_of(profile, rest)
    expected = sk.to_body_pose(profile, _set(rest, floor), planted=("left", "right")).support_polygon
    found, sides = support(profile, rest, floor, ("left", "right"))
    assert sides == ("left", "right")
    assert [c for p in found for c in p] == pytest.approx([c for p in expected for c in p])
    point = sk.Vec3(0.0, -0.9, 0.0)
    assert margin(found, point) == body.support_margin(found, point) > 0
    left, sides = support(profile, rest, floor, ("left",))
    expected = sk.to_body_pose(profile, _set(rest, floor), planted=("left",)).support_polygon
    assert sides == ("left",) and [c for p in left for c in p] == pytest.approx([c for p in expected for c in p])


def test_only_a_foot_that_lies_flat_holds_the_body_up():
    profile = sk.preset("realistic")
    rest = sk.rest_pose(profile)
    floor = floor_of(profile, rest)
    assert support(profile, _set(rest, 0.01), floor, ("left", "right")) is None  # both feet off the floor
    assert support(profile, rest, floor, ()) is None  # no foot named
    tipped = _set(rest, values=rest.values + (("right_foot.up_down", 0.3),))
    found, sides = support(profile, tipped, floor, ("left", "right"))
    assert sides == ("left",)  # the tipped foot holds nothing up
    alone, _ = support(profile, rest, floor, ("left",))
    assert [c for p in found for c in p] == pytest.approx([c for p in alone for c in p])


@pytest.mark.parametrize("preset", sk.PRESETS)
def test_a_standing_body_stands_inside_its_feet(preset):
    profile = sk.preset(preset)
    com = dance_floor.centre_of_mass(profile, sk.rest_pose(profile))
    assert com.x == pytest.approx(0.0, abs=1e-9)  # the rest pose is symmetric
    floor = floor_of(profile, sk.rest_pose(profile))
    assert 0.3 * profile.stature < floor - com.y < 0.7 * profile.stature  # about the middle of the body
    both, _ = support(profile, sk.rest_pose(profile), floor, ("left", "right"))
    one, _ = support(profile, sk.rest_pose(profile), floor, ("left",))
    assert margin(both, com) > max(0.0, margin(one, com))  # a stick's broad soles overlap, so one may hold it too
    half, heel, toe = sole(profile)
    assert 0 < half and 0 < heel < toe  # a footprint on any profile, with toes or without


@pytest.mark.parametrize("preset", sk.PRESETS)
def test_the_footprint_is_the_skeletons_sole(preset):
    profile = sk.preset(preset)
    body = sk.body_profile(profile)
    half, heel, toe = sole(profile)
    assert (2 * half, heel, toe) == pytest.approx((body.foot_width, body.heel, body.toe))
    assert 2 * half / profile.stature == pytest.approx(
        sk.JOINT_TABLE.sole_width, rel=0.5
    )  # a foot's width, not the hips'


def test_the_mannequins_footprint_is_srlocations_foot():
    half, heel, _ = sole(sk.preset("realistic"))
    assert (2 * half, heel) == pytest.approx((0.119, 0.077), abs=0.001)


def test_the_centre_of_mass_skips_a_joint_a_character_lacks():
    profile = sk.preset("stick")
    frames = sk.world(profile, sk.rest_pose(profile))
    assert "right_toes" not in frames and toes_offset(profile, "right") == sk.Vec3()
    crown = frames["head"].origin
    assert centre_of_mass(profile, frames, crown).y == pytest.approx(
        dance_floor.centre_of_mass(profile, sk.rest_pose(profile)).y, abs=0.05
    )
    assert ball_of(profile, frames, "right") == frames["right_foot"].origin


# --- the class phrases on every preset ------------------------------------------------------------------------------


CASES = [(name, preset) for name in dance.phrases() for preset in sk.PRESETS]


@pytest.mark.parametrize("name, preset", CASES)
def test_planted_feet_hold_within_the_bound(name, preset):
    slip = performed(name, preset).slip(FPS)
    assert isinstance(slip, Slip)
    assert slip.ball_m <= SLIP_M and slip.ankle_m <= SLIP_M


@pytest.mark.parametrize("name, preset", CASES)
def test_the_body_stays_over_its_feet(name, preset):
    run = performed(name, preset)
    assert run.balance(FPS) == ()
    run.check(FPS)  # nothing to refuse
    frames = run.frames(FPS)
    assert all(f.margin_m is not None and f.margin_m >= run.margin_m for f in frames)
    assert all(isinstance(f, FloorFrame) and not f.airborne and f.planted for f in frames)


@pytest.mark.parametrize("name, preset", CASES)
def test_no_foot_goes_through_the_floor(name, preset):
    run = performed(name, preset)
    profile = sk.preset(preset)
    for f in run.frames(FPS)[::5]:
        world = sk.world(profile, f.pose)
        for side in ("left", "right"):
            sole_y = world[f"{side}_foot"].origin.y + profile.length("ankle")
            assert sole_y <= run.floor_y + 1e-6  # y points down


def test_a_planted_foot_lies_flat_on_the_floor():
    run = performed("kick-ball-change", "realistic")
    profile = sk.preset("realistic")
    on_both = [f for f in run.frames(FPS) if f.planted == FEET]
    for f in on_both[::7]:
        world = sk.world(profile, f.pose)
        for side in ("left", "right"):
            foot = world[f"{side}_foot"]
            assert foot.origin.y + profile.length("ankle") == pytest.approx(run.floor_y, abs=1e-6)
            assert foot.rotation.rotate(UP).y == pytest.approx(1.0, abs=1e-6)  # the sole faces the floor


def _heading(pose):
    ahead = pose.root.rotation.rotate(sk.Vec3(0.0, 0.0, 1.0))
    return math.atan2(ahead.x, ahead.z)


def test_the_turn_reads_on_the_floor_and_comes_back_to_the_front():
    run = performed("turn-travel", "cartoon")
    third = run.pose(CLASS.offset + 2.0 * CLASS.beat)
    assert _heading(third) == pytest.approx(-math.pi / 2, abs=0.02)  # a quarter turn to the left by 3
    assert _heading(run.pose(run.end_s)) == pytest.approx(0.0, abs=0.02)


def test_the_groove_step_travels_right_and_back():
    run = performed("groove-step", "stick")
    height = sk.preset("stick").pelvis_height
    start = run.pose(run.start_s).root.origin.x
    far = run.pose(CLASS.offset + 4.0 * CLASS.beat).root.origin.x
    assert far - start >= 0.25 * height and abs(run.pose(run.end_s).root.origin.x - start) <= 0.1 * height


# --- balance findings and limits ------------------------------------------------------------------------------------


STORK = Phrase(
    "stork",
    1,
    (
        Key(0.0, FEET),
        Key(1.0, LEFT, (("right_upper_leg.front_back", -0.5), ("right_lower_leg.stretch", -1.0))),
        Key(3.0, LEFT, (("right_upper_leg.front_back", -0.5), ("right_lower_leg.stretch", -1.0))),
        Key(4.0, FEET),
    ),
)


def test_a_body_left_over_a_lifted_foot_is_found_off_balance():
    run = perform(STORK, sk.preset("realistic"), CLASS, balance=False)
    found = run.balance(25)
    assert found and all(isinstance(f, BalanceFinding) and f.margin_m < run.margin_m for f in found)
    assert {f.planted for f in found} == {LEFT}
    with pytest.raises(BalanceError, match="off balance") as caught:
        run.check(25)
    assert caught.value.count == len(found) and caught.value.to_dict()["code"] == "dance.floor.balance"
    with pytest.raises(BalanceError):
        perform(STORK, sk.preset("realistic"), CLASS, balance=False, strict=True, fps=25)


def test_the_balance_pass_moves_the_body_over_the_standing_foot():
    run = perform(STORK, sk.preset("realistic"), CLASS, strict=True, fps=25)
    assert run.balance(25) == ()
    mid = run.sample(CLASS.offset + 2.0 * CLASS.beat)
    assert mid.planted == LEFT and mid.com.x < 0  # the weight moved over the left foot


SQUAT = Phrase("squat", 1, (Key(0.0, FEET), Key(2.0, FEET, floor=Floor(up=-0.48)), Key(4.0, FEET)))


def test_a_planted_foot_that_breaks_a_limit_is_refused_unless_clamped():
    profile = sk.preset("realistic")
    with pytest.raises(FloorLimitError, match="pass their limits") as caught:
        perform(SQUAT, profile, CLASS).frames(10)
    assert caught.value.count >= 1 and caught.value.to_dict()["code"] == "dance.floor.limit"
    assert perform(SQUAT, profile, CLASS, clamp=True).frames(10)


def test_floor_errors_are_typed_srstudio_errors():
    for kind in (FloorError, FloorLimitError, BalanceError):
        assert issubclass(kind, dance.DanceError) and issubclass(kind, SrstudioError)


# --- the shared pass any style calls --------------------------------------------------------------------------------


def test_plant_holds_the_feet_of_any_dance_frames():
    profile = sk.preset("cartoon")
    frames = list(dance.frames(dance.phrases()["groove-step"], CLASS, 0.0, 8 * CLASS.beat, 25))
    planted = plant(profile, frames)
    assert len(planted) == len(frames) and [f.time for f in planted] == [f.time for f in frames]
    first = [f for f in planted if "left_foot" in f.planted]
    spots = {(round(ball_of(profile, sk.world(profile, f.pose), "left").x, 3)) for f in first[:5]}
    assert len(spots) == 1  # the left ball holds its spot over the first plant


def test_plant_carries_a_move_and_a_seated_base():
    profile = sk.preset("stick")
    seat = dance.moves()["seat-groove"]
    frames = list(dance.frames(seat, CLASS, 0.0, 2.0, 10))
    out = plant(profile, frames, base=seated(profile))
    rest_floor = floor_of(profile, sk.rest_pose(profile))
    for f in out:
        assert f.support == "seat" and f.margin_m is None  # a seat holds the body: no balance check
        world = sk.world(profile, f.pose)
        assert world["left_foot"].origin.y + profile.length("ankle") == pytest.approx(rest_floor, abs=1e-6)


@pytest.mark.parametrize("preset", sk.PRESETS)
def test_seated_puts_the_hips_at_the_knees_and_the_feet_on_the_floor(preset):
    profile = sk.preset(preset)
    pose = seated(profile)
    world = sk.world(profile, pose)
    assert floor_of(profile, pose) == pytest.approx(floor_of(profile, sk.rest_pose(profile)), abs=1e-9)
    assert world["hips"].origin.y == pytest.approx(world["left_lower_leg"].origin.y, abs=0.05 * profile.stature)


@pytest.mark.parametrize("preset", sk.PRESETS)
def test_stance_stands_wide_on_bent_knees_with_the_feet_flat(preset):
    profile = sk.preset(preset)
    rest, pose = sk.rest_pose(profile), stance(profile)
    world, height = sk.world(profile, pose), profile.pelvis_height
    assert floor_of(profile, pose) == pytest.approx(floor_of(profile, rest), abs=1e-6)  # the same floor
    for side in ("left", "right"):
        foot = world[f"{side}_foot"].origin
        assert foot.y + profile.length("ankle") == pytest.approx(floor_of(profile, rest), abs=1e-6)  # flat on it
    across = world["right_foot"].origin.x - world["left_foot"].origin.x
    assert across == pytest.approx(dance_floor.STANCE_WIDTH * height, rel=1e-3)
    assert knee_bend(profile, pose) == pytest.approx(dance_floor.STANCE_BEND, abs=0.01)
    assert world["hips"].origin.y > sk.world(profile, rest)["hips"].origin.y + 0.02 * height  # the hips sit lower
    com = dance_floor.centre_of_mass(profile, pose)
    assert margin(support(profile, pose, floor_of(profile, pose), ("left", "right"))[0], com) > 0
    ahead = [world[f"{side}_foot"].rotation.rotate(sk.Vec3(0.0, 0.0, 1.0)).x for side in ("left", "right")]
    assert ahead[0] < 0 < ahead[1]  # the toes turn out


def test_stance_takes_its_width_and_bend():
    profile = sk.preset("realistic")
    narrow, deep = stance(profile, width=0.3, bend=0.3), stance(profile, width=0.6, bend=0.9, turnout=0.0)
    assert knee_bend(profile, narrow) == pytest.approx(0.3, abs=0.01)
    assert knee_bend(profile, deep) == pytest.approx(0.9, abs=0.01)
    low = [sk.world(profile, p)["hips"].origin.y for p in (narrow, deep)]
    assert low[1] > low[0]
    assert knee_bend(profile, sk.rest_pose(profile)) == pytest.approx(0.0, abs=1e-6)


@pytest.mark.parametrize(
    "kwargs, match",
    [
        ({"width": -0.1}, "width"),
        ({"width": 1.5}, "width"),
        ({"width": "wide"}, "width"),
        ({"bend": 1.6}, "bend"),
        ({"turnout": 0.9}, "turnout"),
    ],
)
def test_stance_refuses_a_shape_out_of_bounds(kwargs, match):
    with pytest.raises(FloorError, match=match):
        stance(sk.preset("realistic"), **kwargs)


def test_stance_refuses_feet_straight_legs_cannot_reach():
    with pytest.raises(FloorError, match="bend") as caught:
        stance(sk.preset("realistic"), width=1.0, bend=0.0)  # straight legs do not reach feet that far apart
    assert isinstance(caught.value, SrstudioError) and not isinstance(caught.value, FloorLimitError)


def test_stance_refuses_a_foot_past_its_limits_unless_clamped():
    profile = sk.preset("realistic")
    with pytest.raises(FloorLimitError, match="pass their limits"):
        stance(profile, width=1.0, bend=1.2)
    assert knee_bend(profile, stance(profile, width=1.0, bend=1.2, clamp=True)) == pytest.approx(1.2, abs=0.01)


SINK = Phrase("sink", 1, (Key(0.0, FEET), Key(4.0, FEET, floor=Floor(up=-0.1)), Key(7.5, FEET)))


@pytest.mark.parametrize("preset", sk.PRESETS)
@pytest.mark.parametrize("phrase, wide", [("turn-travel", False), ("sink", True)])
def test_dance_frames_dance_the_floor_pass_through_dance_pose(preset, phrase, wide):
    profile = sk.preset(preset)
    base, spot = (stance(profile) if wide else sk.rest_pose(profile)), Spot(1.0, -0.5, 0.4)
    source = SINK if phrase == "sink" else dance.phrases()[phrase]
    run = perform(source, profile, CLASS, base=base if wide else None, spot=spot)
    solved, danced = run.frames(10), run.dance_frames(10)
    assert len(solved) == len(danced)
    for floor, frame in zip(solved, danced, strict=True):
        assert isinstance(frame, dance.DanceFrame) and frame.time == floor.time
        assert frame.planted == floor.planted and frame.floor.up == 0.0
        again = sk.world(profile, dance_pose(profile, frame, base=base).pose)
        there = sk.world(profile, floor.pose)
        for name in ("hips", "head", "left_foot", "right_foot", "left_hand", "right_lower_leg"):
            moved = spot.frame().inverse_point(there[name].origin)
            assert again[name].origin.distance(moved) < 1e-6  # the same body, at the centre of the floor


def test_a_root_drop_folds_the_planted_legs_in_the_dance_frames():
    profile = sk.preset("realistic")
    run = perform(SINK, profile, CLASS)
    frames = run.dance_frames(10)
    low = min(frames, key=lambda f: f.root[1])
    pose = dance_pose(profile, low).pose
    assert knee_bend(profile, pose) > 0.3  # the knees fold under the hips
    world = sk.world(profile, pose)
    ankle = world["left_foot"].origin.y
    rest = sk.world(profile, sk.rest_pose(profile))
    assert ankle == pytest.approx(rest["left_foot"].origin.y, abs=1e-6)  # the feet stay on the floor
    assert world["hips"].origin.y - rest["hips"].origin.y == pytest.approx(0.1 * profile.pelvis_height, rel=0.05)


@pytest.mark.parametrize("frames, match", [([], "1..100000"), ("frames", "DanceFrame"), ([1, 2], "DanceFrame")])
def test_plant_refuses_frames_it_cannot_hold(frames, match):
    with pytest.raises(FloorError, match=match):
        plant(sk.preset("stick"), frames)


def test_plant_refuses_frames_out_of_order():
    one = dance.sample(dance.moves()["bob"], CLASS, 0.5)
    with pytest.raises(FloorError, match="rising"):
        plant(sk.preset("stick"), [one, one])


@pytest.mark.parametrize("preset", sk.PRESETS)
def test_ground_lays_each_foot_flat_where_its_ball_is(preset):
    profile = sk.preset(preset)
    lifted = sk.add(
        profile,
        sk.rest_pose(profile),
        {"left_upper_leg.front_back": -0.3, "left_lower_leg.stretch": -0.5, "left_foot.up_down": 0.3},
    )
    before = ball_of(profile, sk.world(profile, lifted), "left")
    laid = ground(profile, lifted, ("left",), floor_y=-0.05)
    world = sk.world(profile, laid)
    assert world["left_foot"].origin.y + profile.length("ankle") == pytest.approx(-0.05, abs=1e-6)
    assert world["left_foot"].rotation.rotate(UP).y == pytest.approx(1.0, abs=1e-6)
    after = ball_of(profile, world, "left")
    assert (after.x, after.z) == pytest.approx((before.x, before.z), abs=1e-6)


@pytest.mark.parametrize(
    "kw, match",
    [
        ({"pose": "rest"}, "SkeletonPose"),
        ({"feet": ("left", "left")}, "once"),
        ({"feet": ("tail",)}, "once"),
        ({"floor_y": math.nan}, "floor_y"),
        ({"clamp": 1}, "clamp"),
    ],
)
def test_ground_refuses_bad_settings(kw, match):
    profile = sk.preset("stick")
    with pytest.raises(FloorError, match=match):
        ground(profile, **{"pose": sk.rest_pose(profile), **kw})


# --- a performance and its settings ---------------------------------------------------------------------------------


def test_a_routine_of_phrases_is_performed_from_where_each_left_the_body():
    phrases = dance.phrases()
    routine = Routine(4, (Entry(0, 2, phrases["groove-step"]), Entry(2, 4, phrases["kick-ball-change"])))
    run = perform(routine, sk.preset("stick"), CLASS, spot=Spot(1.0, -0.5, 0.3))
    assert run.end_s == pytest.approx(CLASS.offset + 16 * CLASS.beat)
    assert run.slip(25).ball_m <= SLIP_M and run.balance(25) == ()
    assert _heading(run.pose(run.start_s)) == pytest.approx(0.3)  # facing where the spot faces


@pytest.mark.parametrize(
    "kw, match",
    [
        ({"source": dance.moves()["bob"]}, "Phrase or a Routine"),
        ({"profile": "stick"}, "SkeletonProfile"),
        ({"groove": 120}, "Groove"),
        ({"delay_beats": -1}, "delay_beats"),
        ({"spot": (0, 0)}, "Spot"),
        ({"base": "seated"}, "SkeletonPose"),
        ({"clamp": "no"}, "clamp"),
        ({"strict": 0}, "strict"),
        ({"margin_m": 0.5}, "margin_m"),
    ],
)
def test_perform_refuses_bad_settings(kw, match):
    args = {"source": STORK, "profile": sk.preset("stick"), "groove": CLASS, **kw}
    with pytest.raises(FloorError, match=match):
        perform(args.pop("source"), args.pop("profile"), args.pop("groove"), **args)


def test_a_performance_refuses_a_bad_time_or_rate():
    run = performed("groove-step", "stick")
    with pytest.raises(FloorError, match="time"):
        run.sample(math.inf)
    for fps in (0, 241, 2.5):
        with pytest.raises(FloorError, match="fps"):
            run.frames(fps)


@pytest.mark.parametrize("kw", [{"x": 101.0}, {"z": math.nan}, {"facing": 20.0}])
def test_a_spot_off_the_floor_is_refused(kw):
    with pytest.raises(FloorError, match="spot"):
        Spot(**kw)


# --- an ensemble ----------------------------------------------------------------------------------------------------


def test_a_line_is_centred_and_a_wedge_puts_the_first_dancer_in_front():
    line = formation("line", 3, 1.0)
    assert [s.x for s in line] == [-1.0, 0.0, 1.0] and {s.z for s in line} == {0.0}
    wedge = formation("wedge", 3, 1.0)
    assert wedge[0].x == 0.0 and wedge[0].z > wedge[1].z == wedge[2].z
    assert wedge[1].x == -wedge[2].x != 0


@pytest.mark.parametrize(
    "args, match",
    [
        (("circle", 3, 1.0), "formation"),
        (("line", 0, 1.0), "count"),
        (("line", 17, 1.0), "count"),
        (("line", 3, 0.0), "spacing_m"),
    ],
)
def test_a_formation_outside_its_bounds_is_refused(args, match):
    with pytest.raises(FloorError, match=match):
        formation(*args)


def _trio(**kw):
    spots = formation("line", 3, 1.2)
    dancers = [
        Dancer(sk.preset(p), spot, delay_beats=i * 0.5)
        for i, (p, spot) in enumerate(zip(sk.PRESETS, spots, strict=True))
    ]
    return ensemble(STORK, dancers, CLASS, **kw)


def test_an_ensemble_is_the_same_for_one_seed_and_varies_with_another():
    first, again, other = _trio(seed=7), _trio(seed=7), _trio(seed=8)
    assert [(r.delay_s, r.size) for r in first] == [(r.delay_s, r.size) for r in again]
    assert [(r.delay_s, r.size) for r in first] != [(r.delay_s, r.size) for r in other]
    for run in first:
        assert abs(run.size - 1) <= dance_floor.MAX_SIZE_VARIATION
    t = CLASS.offset + 2.0 * CLASS.beat
    assert first[1].pose(t) == again[1].pose(t)


def test_an_ensemble_without_variation_dances_a_canon_in_exact_unison():
    runs = _trio(seed=1, variation=0.0)
    assert [r.delay_s for r in runs] == pytest.approx([0.0, 0.5 * CLASS.beat, CLASS.beat])
    assert all(r.size == 1.0 for r in runs)
    t = CLASS.offset + 1.5 * CLASS.beat
    lead, follow = runs[0].frame(t), runs[2].frame(t + CLASS.beat)
    assert dict(lead.joints) == pytest.approx(dict(follow.joints)) and lead.planted == follow.planted
    assert runs[2].pose(t + CLASS.beat).root.origin.x > 1.0  # the third dancer stands on the right of the line


@pytest.mark.parametrize(
    "kw, match",
    [
        ({"dancers": []}, "1..16"),
        ({"dancers": ["stick"]}, "Dancer"),
        ({"seed": -1}, "seed"),
        ({"variation": 2.0}, "variation"),
        ({"groove": None}, "Groove"),
        ({"dancers": [Dancer(sk.preset("stick"), delay_beats=99)]}, "delay_beats"),
    ],
)
def test_an_ensemble_refuses_bad_settings(kw, match):
    args = {"dancers": [Dancer(sk.preset("stick"))], "groove": CLASS, "seed": 0, **kw}
    with pytest.raises(FloorError, match=match):
        ensemble(STORK, args.pop("dancers"), args.pop("groove"), **args)
