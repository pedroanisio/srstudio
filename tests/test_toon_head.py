"""The Toon figure in nested groups (ADR 0050): a head that turns about its neck behind a body whose ruff hides the
seam, one kind of motion per group, and the flat figure every published reel was drawn with left byte for byte."""

import hashlib
import math
import xml.etree.ElementTree as ET
from dataclasses import replace

import pytest
from sr_core.scene import Scene

import srstudio
from srstudio import PEACH, Canvas, flat_counter, head_motion, toon_cast, toon_critters, toon_head
from srstudio.head_motion import HeadMotionError, HeadPlan, limit
from srstudio.toon import Pose, ToonDataError, fh, fx, fy
from support.spring_curve import sample
from support.toon_contour import inside

RIG = toon_critters.SLOTH_RIG
STYLE = toon_critters.SLOTH_MOTION
POSES = [
    Pose(0.0, "sleepy", "flat", "desk"),
    Pose(2.0, "half", "smirk", "type", ("glasses",)),
    Pose(4.0, "wide", "yawn", "sigh"),
    Pose(5.0, "shock", "o", "lean", ("sweat", "flush")),
    Pose(6.0, "hearts", "kiss", "face"),
]
MOUTHS = [(0.4, "open"), (0.6, "round"), (0.9, "teeth"), (1.2, "closed"), (2.3, "open"), (2.6, "closed")]
TAPS = (2.2, 2.4, 2.9)
PINS = {
    "sloth": "711eec1f46d89602b625549f1a0ae92f56548561c1f41a54b3228415ab4936e0",
    "dog": "71a10718403490ee97635a2c8faecccb1fa0b83f2ef1b693a2b08cd1ee52cd7e",
}
HEAD_TOP = 170.0  # reference pixels from the neck to the crown


def stage() -> tuple[Scene, Canvas]:
    scene = Scene(version="auto")
    scene.add_project(width=1080, height=1920, fps="24", duration=8.0, background=PEACH.background)
    return scene, Canvas(scene, PEACH, font_asset=None)


def drawn(plan: HeadPlan | None = None, poses=POSES, rig=RIG, **kw) -> ET.Element:
    scene, cv = stage()
    plan = hm_plan() if plan is None else plan
    toon_head.figure(cv, cv.comp, rig, poses, 8.0, plan, **kw)
    return ET.fromstring(scene.to_bytes(layout="pretty"))


def hm_plan(duration: float = 8.0) -> HeadPlan:
    return head_motion.plan(STYLE, [], duration)


def group(root: ET.Element, name: str) -> ET.Element:
    return next(node for node in root.iter("group") if node.get("id", "").startswith(f"{name}-"))


def animates(node: ET.Element) -> dict[str, ET.Element]:
    return {a.get("property"): a for a in node.findall("animate")}


# -- the published figure ----------------------------------------------------------------------------------------------
@pytest.mark.parametrize("name, look", (("sloth", toon_critters.SLOTH), ("dog", toon_cast.DOG)))
def test_the_flat_figure_is_byte_identical(name, look):
    scene = Scene(version="auto")
    scene.add_project(width=1080, height=1920, fps="24", duration=8.0, background=PEACH.background)
    cv = Canvas(scene, PEACH, font_asset=None, namer=flat_counter("k"))
    toon_cast.figure(cv, cv.comp, look, POSES, 8.0, TAPS, 0.0, (), MOUTHS)
    assert hashlib.sha256(scene.to_bytes(layout="pretty")).hexdigest() == PINS[name]


def test_the_rig_is_opt_in_the_sloth_itself_keeps_its_tilted_vertices():
    assert toon_critters.SLOTH_CRITTER.tilt == RIG.tilt != 0.0
    assert RIG.look.drawing is not None
    assert RIG.look != toon_critters.SLOTH


# -- the nesting -------------------------------------------------------------------------------------------------------
def test_each_group_carries_one_kind_of_motion_and_the_head_goes_behind_the_body():
    root = drawn()
    lean, breath = group(root, "lean"), group(root, "breath")
    assert breath in list(lean)
    children = [node.get("id", "").split("-")[0] for node in breath.findall("group")]
    assert children == ["turn", "trunk", "front"]  # the trunk paints over the head chain
    assert group(group(root, "turn"), "nod") is group(root, "nod")
    assert group(group(root, "nod"), "idle") is group(root, "idle")
    assert group(group(root, "idle"), "lift") is group(root, "lift")
    assert [n.get("id", "").split("-")[0] for n in group(root, "lift").findall("group")] == ["skull", "face"]
    for name in ("lean", "breath", "turn", "nod", "idle", "lift", "face"):
        kinds = list(animates(group(root, name)))
        assert len(kinds) == len(set(kinds))  # never two sources on one property


def test_the_head_turns_about_the_neck_with_its_drawn_tilt_at_rest():
    turn = group(drawn(), "turn")
    assert float(turn.get("anchorX")) == pytest.approx(fx(RIG.neck[0]), abs=0.01)
    assert float(turn.get("anchorY")) == pytest.approx(fy(RIG.neck[1]), abs=0.01)
    assert float(turn.get("rotation")) == RIG.tilt
    keys = animates(turn)["rotation"].findall("key")
    assert float(keys[0].get("value")) == pytest.approx(RIG.tilt)


def test_spring_keys_are_the_engine_s_own_and_carry_their_momentum_after_the_first():
    speech = head_motion.Speech(1.0, head_motion.words_of(_take(), 1.0), (-20.0,) * 300)
    plan = head_motion.plan(STYLE, [speech], 8.0)
    a = animates(group(drawn(plan), "nod"))["y"]
    assert a.get("defaultInterpolation") == "spring"
    keys = a.findall("key")
    assert len(keys) == len(plan.nod.keys)
    assert keys[0].get("carry") is None
    assert all(k.get("carry") == "true" for k in keys[1:])
    assert keys[1].get("stiffness") == STYLE.head.attributes()["stiffness"]


def _take():
    text = "Everyone knows I rested"
    return head_motion.Alignment(
        tuple(text), *zip(*((i * 0.08, (i + 1) * 0.08) for i in range(len(text))), strict=True)
    )


def test_a_still_plan_draws_the_same_figure_with_nothing_moving_on_the_head():
    root = drawn(HeadPlan.still())
    for name in ("lean", "breath", "turn", "nod", "idle", "lift", "face"):
        assert animates(group(root, name)) == {}


def test_the_face_slides_further_than_the_skull_on_a_nod():
    speech = head_motion.Speech(1.0, head_motion.words_of(_take(), 1.0), (-20.0,) * 300)
    plan = head_motion.plan(STYLE, [speech], 8.0)
    root = drawn(plan)
    skull = [float(k.get("value")) - fy(RIG.neck[1]) for k in animates(group(root, "nod"))["y"].findall("key")]
    face = [float(k.get("value")) for k in animates(group(root, "face"))["y"].findall("key")]
    biggest = max(range(len(skull)), key=lambda i: abs(skull[i]))
    assert face[biggest] == pytest.approx(skull[biggest] * toon_head.FACE_SLIDE, abs=0.05)
    assert skull[biggest] == pytest.approx(max(v for _, v in plan.nod.keys) * fh(1.0), abs=0.05)


# -- the seam ----------------------------------------------------------------------------------------------------------
def _posed(point, degrees, drop):
    """A reference point of the head with the head turned ``degrees`` about the neck and moved down ``drop``."""
    a = math.radians(degrees)
    dx, dy = point[0] - RIG.neck[0], point[1] - RIG.neck[1]
    return RIG.neck[0] + dx * math.cos(a) - dy * math.sin(a), RIG.neck[1] + dx * math.sin(a) + dy * math.cos(a) + drop


def _shape_of(layers, index: int = 0):
    return layers[index][0]


def _ruff_y(x: float) -> float:
    ruff = toon_critters._SLOTH_RUFF
    for a, b in zip(ruff, ruff[1:], strict=False):
        if min(a[0], b[0]) <= x <= max(a[0], b[0]) and a[0] != b[0]:
            return a[1] + (b[1] - a[1]) * (x - a[0]) / (b[0] - a[0])
    raise AssertionError(x)


@pytest.mark.parametrize("sign", (-1.0, 1.0))
@pytest.mark.parametrize("name", ("up", "down"))
def test_the_ruff_covers_the_seam_with_the_head_at_every_bound(sign, name):
    swing = limit(STYLE, "turn") + limit(STYLE, "roll") + limit(STYLE, "idle_roll")
    drop = limit(STYLE, "nod") + STYLE.idle_px if name == "down" else -(STYLE.breath_px + STYLE.idle_px)
    outline = _shape_of(toon_critters._sloth_skull())
    undo = RIG.tilt + sign * swing
    for x in range(100, 271, 5):
        over_ruff = (x, _ruff_y(x) - 2.0)  # just above the ruff line, on the screen: the head must be behind it
        back = _posed((over_ruff[0], over_ruff[1] - drop), -undo, 0.0)
        assert inside(outline, *back), (x, undo, drop)


def test_the_head_stays_inside_its_bounds_with_every_channel_at_the_limit():
    assert limit(STYLE, "turn") + limit(STYLE, "roll") + limit(STYLE, "idle_roll") < 12.0
    assert limit(STYLE, "nod") < 30.0


# -- the idle ----------------------------------------------------------------------------------------------------------
def test_the_sloth_never_sits_stock_still():
    plan = hm_plan(12.0)

    def crown(t: float) -> tuple[float, float]:
        across = HEAD_TOP * math.radians(sample(plan.idle_roll, t))
        return across, sample(plan.idle_y, t) - STYLE.breath_px * sample(plan.breath, t)

    for start in range(11):
        seen = [crown(start + k * 0.1) for k in range(11)]
        assert max(max(axis) - min(axis) for axis in zip(*seen, strict=True)) >= 0.5, start


# -- gaze --------------------------------------------------------------------------------------------------------------
def test_gaze_states_are_hold_keys_with_ahead_first():
    states = toon_head.gaze_states(((1.0, "left"), (2.0, "ahead"), (3.0, "up")), 0.0, 8.0)
    assert states["ahead"] == [(0.0, 1), (1.0, 0), (2.0, 1), (3.0, 0)]
    assert states["left"] == [(0.0, 0), (1.0, 1), (2.0, 0), (3.0, 0)]
    assert states["up"] == [(0.0, 0), (1.0, 0), (2.0, 0), (3.0, 1)]


def test_a_run_that_starts_mid_glance_starts_looking_that_way_and_ignores_what_comes_after():
    states = toon_head.gaze_states(((1.0, "left"), (9.0, "right")), 2.0, 8.0)
    assert states == {"ahead": [(2.0, 0)], "left": [(2.0, 1)]}


def test_an_unknown_gaze_is_refused_by_name():
    with pytest.raises(HeadMotionError, match="sideways"):
        toon_head.gaze_states(((1.0, "sideways"),), 0.0, 8.0)


def test_a_glance_draws_one_pair_of_eyes_a_gaze_and_moves_the_pupils():
    plan = HeadPlan(gaze=((1.0, "left"), (2.0, "ahead")))
    root = drawn(plan, poses=[Pose(0.0, "half", "flat", "desk")])
    run = next(iter(group(root, "face").findall("group")))
    eyes = [g for g in run.findall("group") if "opacity" in animates(g)]
    held = [g for g in eyes if len(animates(g)["opacity"].findall("key")) == 3]
    assert len(held) == 2
    assert ET.tostring(held[0]) != ET.tostring(held[1])
    ahead = [p for p in toon_head._gazing(RIG.look, "ahead").drawing.pupil(RIG.look, 100.0, 100.0, 5.0) if len(p) == 2]
    left = [p for p in toon_head._gazing(RIG.look, "left").drawing.pupil(RIG.look, 100.0, 100.0, 5.0) if len(p) == 2]
    assert ahead != left


def test_shut_eyes_have_no_pupils_to_move():
    plan = HeadPlan(gaze=((1.0, "left"), (2.0, "ahead")))
    root = drawn(plan, poses=[Pose(0.0, "closed", "flat", "desk")])
    run = next(iter(group(root, "face").findall("group")))
    assert not any(len(animates(g).get("opacity", ET.Element("a")).findall("key")) == 3 for g in run.findall("group"))


def test_a_look_with_no_drawing_of_its_own_cannot_glance():
    with pytest.raises(ToonDataError, match="pupils"):
        toon_head._gazing(toon_cast.DOG, "left")


# -- the poses ---------------------------------------------------------------------------------------------------------
def test_every_pose_kind_draws_through_the_head_rig():
    root = drawn(mouths=MOUTHS, taps=TAPS, stickers=[toon_critters._sloth_skull()[0]])
    for name, count in (("skull", 5), ("face", 5), ("trunk", 5)):
        assert len(group(root, name).findall("group")) == count


def test_something_held_in_front_goes_over_the_face():
    root = drawn(poses=[Pose(0.0, "half", "flat", "face")])
    assert len(group(root, "front").findall("group")) == 1


def test_typing_swaps_arms_on_the_taps_and_keeps_inside_the_trunk():
    typed = drawn(poses=[Pose(0.0, "half", "flat", "type")], taps=TAPS)
    idle = drawn(poses=[Pose(0.0, "half", "flat", "type")])
    assert len(ET.tostring(group(typed, "trunk"))) > len(ET.tostring(group(idle, "trunk"))) / 2
    assert group(typed, "front").findall("group") == []


def test_lips_and_blinks_stay_on_the_face_group():
    face = group(drawn(poses=[Pose(0.0, "half", "flat", "desk")], mouths=MOUTHS), "face")
    held = [g for g in face.iter("group") if "opacity" in animates(g)]
    assert len(held) >= 4  # the visemes and the lids


def test_an_entrance_starts_the_runs_late():
    root = drawn(poses=[Pose(0.0, "half", "flat", "desk")], enter=1.5)
    assert group(root, "skull").find("group").get("start") == "1.5"
    assert group(root, "trunk").find("group").get("end") == "8"


def test_a_second_glance_at_another_rig_keeps_the_rig_s_look():
    assert replace(RIG, tilt=0.0).look is RIG.look


def test_the_modules_are_reachable_from_the_package():
    assert srstudio.head_motion is head_motion and srstudio.toon_head is toon_head
