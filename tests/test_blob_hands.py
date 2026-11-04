"""A Soft figure can draw a pair of hands: mittens with a thumb, the right the mirror of the left, on the tips of its
arms, and three seated gestures that show them (ADR 0239). Without them every rig draws byte for byte as before."""

import hashlib
import math
import xml.etree.ElementTree as ET

import pytest

from srstudio import anatomy_ledger, blob, parts, registry, soft_odds, specimens
from srstudio.anatomy import Arm, Facing, Side
from srstudio.blob import BlobError, Cue
from support.soft_props import canvas

RIGS = ("pip", "bo", "juno", "remy")
HANDED = ("pip", "bo", "juno")
GESTURES = ("shrug", "explain", "whoa")
# The poses the rig had before it had hands, in their order; a test that walks them never sees a new pose.
OLD_POSES = (
    "stand", "step", "sit", "type-a", "type-b", "nod", "lounge", "floor", "phone-a", "phone-b", "sit-show", "sit-back",
    "hug", "clasp", "lean", "walk-a", "stride", "walk-b", "cheer-a", "cheer-b", "wave-a", "wave-b", "groove-a",
    "groove-b", "groove-c",
)  # fmt: skip
# Taken on integ/sdk-nov04 a0828147, before the rig had hands: every pose, flipped every other cue and eased, with a
# prop riding between the hands (held) and one in the right hand (soft_odds.in_hand), at scale 1.3.
BEFORE = {
    "pip": "58b38c5e73efcbaf6aa0887de3d39b13ed28a0c89f1b7148a5358cc89a17cbea",
    "bo": "a3d16e12b1dde8c0f07d5b4e91d2f6361b121653ca6ecc9c674bbf3cb71ee971",
    "juno": "3d16a18f8d6bb2e5e38ba054282a0b632da57a7479d5c973d95320d6be8d5f8b",
    "remy": "b9a061d118f526417c032319b5aba25d4dbb1c308fc48edde964a31c963e2059",
}


def performance(poses=OLD_POSES):
    cues = [Cue(float(i), p, eyes="open", flip=bool(i % 2), ease=0.3 if i else 0.0) for i, p in enumerate(poses)]
    return cues, float(len(cues))


def drawn(rig: str, cues, end: float, **kw):
    cv = canvas()
    getattr(blob, rig)(cv, cv.comp, cues, end=end, scale=1.3, **kw)
    return cv


def centre(points):
    return (sum(x for x, _ in points) / len(points), sum(y for _, y in points) / len(points))


# -- off by default: nothing published moves -------------------------------------------------------------------
@pytest.mark.parametrize("rig", RIGS)
def test_a_figure_without_hands_draws_byte_for_byte_as_before(rig):
    cues, end = performance()
    cv = canvas()
    getattr(blob, rig)(cv, cv.comp, cues, end=end, scale=1.3)
    blob.held(cv, cv.comp, cues, end=end, scale=1.3, id="held")
    soft_odds.in_hand(cv, cv.comp, cues, "right", end=end, scale=1.3, id="in-hand")
    assert hashlib.sha256(cv.scene.to_bytes(layout="pretty")).hexdigest() == BEFORE[rig]


@pytest.mark.parametrize("rig", RIGS)
def test_the_looks_have_no_hands_and_record_none(rig):
    assert getattr(blob, rig.upper()).hands is False
    cues, end = performance(("sit", "shrug"))
    cv = drawn(rig, cues, end)
    assert cv.limbs == {}
    assert not [g for g in ET.fromstring(cv.scene.to_bytes()).iter("group") if "-hand-" in (g.get("id") or "")]


# -- the mitten: one drawing and its mirror ---------------------------------------------------------------------
def test_the_mitten_is_one_drawing_of_the_left_palm_with_its_thumb_inward():
    assert blob.MITTEN.side is Side.LEFT and blob.MITTEN.facing is Facing.PALM
    assert blob.MITTEN.thumb_x == 1  # the frame's left hand, palm to camera: its thumb toward the frame's right


@pytest.mark.parametrize(("side", "facing", "thumb"), [
    (Side.LEFT, Facing.PALM, 1), (Side.RIGHT, Facing.PALM, -1), (Side.LEFT, Facing.BACK, -1),
    (Side.RIGHT, Facing.BACK, 1),
])  # fmt: skip
def test_a_raised_hand_s_thumb_follows_its_side_and_its_face(side, facing, thumb):
    arm = blob.seg((0, 0), (0, -100), *blob.ARM)  # straight up: the fingers up
    palm, finger = blob.mitten(arm, side, facing)
    assert (centre(finger)[0] - centre(palm)[0]) * thumb > 5
    assert Arm(side).hand(facing).thumb_up == thumb


def test_the_right_hand_is_the_left_hand_reflected():
    left = blob.mitten(blob.seg((0, 0), (-60, -80), *blob.ARM), Side.LEFT, Facing.PALM)
    right = blob.mitten(blob.seg((0, 0), (60, -80), *blob.ARM), Side.RIGHT, Facing.PALM)
    for a, b in zip(left, right, strict=True):
        assert [c for x, y in a for c in (-x, y)] == pytest.approx([c for point in b for c in point])


@pytest.mark.parametrize("angle", [0, 45, 90, 135, 180, 225, 270, 315])
def test_the_mitten_grows_from_the_arm_s_tip_along_it(angle):
    a = math.radians(angle)
    arm = blob.seg((0, 0), (100 * math.cos(a), 100 * math.sin(a)), *blob.ARM)
    palm, _ = blob.mitten(arm, Side.LEFT, Facing.PALM)
    tip = arm.p3
    cx, cy = centre(palm)
    out = ((cx - tip[0]) * math.cos(a) + (cy - tip[1]) * math.sin(a)) / blob.HAND[1]
    assert 0.3 < out < 0.7  # its centre half a hand on along the arm, so the wrist sits on the tip
    assert min(math.dist(p, tip) for p in palm) < blob.ARM[1]


def test_a_hand_is_on_the_frame_s_side_of_its_shoulder_whichever_way_the_figure_faces():
    sit = blob.POSES["sit"]
    assert blob.arm_sides(sit.placed(0, 0)) == {"arm_l": Side.LEFT, "arm_r": Side.RIGHT}
    assert blob.arm_sides(sit.placed(0, 0, flip=True)) == {"arm_l": Side.RIGHT, "arm_r": Side.LEFT}


# -- the gestures --------------------------------------------------------------------------------------------------
def test_the_gestures_are_new_poses_so_no_approved_specimen_walks_them():
    assert set(GESTURES) <= set(blob.POSES) and set(GESTURES) <= blob.POSES_SINCE_APPROVAL
    assert set(blob.PALMS) <= set(blob.POSES)


@pytest.mark.parametrize("pose", GESTURES)
def test_a_gesture_keeps_its_hands_off_the_face_and_its_arms_their_length(pose):
    p = blob.POSES[pose]
    sides = blob.arm_sides(p)
    for arm in blob.ARMS:
        palm, thumb = blob.mitten(p.limbs[arm], sides[arm], blob.facing(pose, arm))
        nearest = min(math.dist(pt, p.head) for pt in palm + thumb)
        assert nearest > blob.HEAD + blob.OUTLINE, f"{pose} {arm}: a hand through the face"
        reach = math.dist(p.limbs[arm].p0, p.limbs[arm].p3)
        assert 50 < reach < 185, f"{pose} {arm}: an arm {reach:.0f} long"  # bent at the elbow, or out straight


# Two seated marks a medium two-shot apart (Juno & Pip's flat: 520 px at scale 1.6) leave each figure half of it.
HALF_A_TWO_SHOT = 520 / 1.6 / 2


@pytest.mark.parametrize("pose", GESTURES)
def test_a_gesture_s_hands_stay_on_their_own_side_of_a_two_shot(pose):
    p = blob.POSES[pose]
    sides = blob.arm_sides(p)
    for arm in blob.ARMS:
        palm, thumb = blob.mitten(p.limbs[arm], sides[arm], blob.facing(pose, arm))
        forward = -min(x for x, _ in palm + thumb)  # the rig faces left: forward is -x from the hip
        assert forward < HALF_A_TWO_SHOT - 10, f"{pose} {arm}: a hand {forward:.0f} forward, into the partner's half"


def _folds(stroke, samples: int = 14) -> bool:
    """Whether a side of ``stroke``'s inked outline runs backward against the centreline anywhere: the bend is
    tighter than half the arm is wide, and the outline crosses itself there."""
    s = stroke.widened(2 * blob.OUTLINE)
    for sign in (1, -1):
        side = []
        for i in range(samples + 1):
            t = i / samples
            (cx, cy), (tx, ty) = s.point(t), s.tangent(t)
            h = (s.w0 + (s.w1 - s.w0) * t) / 2
            side.append(((cx - sign * ty * h, cy + sign * tx * h), (tx, ty)))
        if any(
            (b[0] - a[0]) * tx + (b[1] - a[1]) * ty < 0 for (a, (tx, ty)), (b, _) in zip(side, side[1:], strict=False)
        ):
            return True
    return False


def test_the_fold_check_sees_an_elbow_folded_shut():
    assert _folds(blob.Stroke((0, 0), (0, 80), (20, 80), (20, 0), *blob.ARM))
    assert not _folds(blob.seg((0, 0), (0, -100), *blob.ARM))


@pytest.mark.parametrize("pose", GESTURES)
def test_a_gesture_s_arms_bend_without_folding_their_outline(pose):
    for arm in blob.ARMS:
        assert not _folds(blob.POSES[pose].limbs[arm]), f"{pose} {arm}: the outline folds over itself at the bend"


@pytest.mark.parametrize("pose", ("shrug", "whoa"))
def test_a_two_handed_gesture_shows_a_pair_either_side_of_the_body_palms_out(pose):
    p = blob.POSES[pose]
    xs = sorted(p.limbs[arm].p3[0] for arm in blob.ARMS)
    torso = p.limbs["torso"]
    assert xs[0] < torso.p3[0] - torso.w1 / 2 and xs[1] > torso.p3[0] + torso.w1 / 2
    assert blob.PALMS[pose] == frozenset(blob.ARMS)


@pytest.mark.parametrize(("a", "b"), [
    ("lounge", "shrug"), ("lounge", "explain"), ("lounge", "whoa"), ("shrug", "explain"), ("shrug", "whoa"),
    ("explain", "whoa"),
])  # fmt: skip
def test_the_in_betweens_from_the_rest_pose_and_between_gestures_never_fold(a, b):
    for arm in blob.ARMS:
        for k in range(51):  # an eased in-between can land anywhere along the blend
            stroke = blob.POSES[a].limbs[arm].lerp(blob.POSES[b].limbs[arm], k / 50)
            assert not _folds(stroke), f"{a} -> {b} {arm} at {k / 50}: the outline folds over itself"


# -- drawn on the rig -----------------------------------------------------------------------------------------------
@pytest.mark.parametrize("rig", HANDED)
def test_a_handed_figure_records_one_pair_of_hands(rig):
    cues, end = performance(("sit", "shrug", "whoa", "explain", "phone-a"))
    cv = canvas()
    registry.get("character", f"{rig}@2")(cv, cv.comp, cues, end=end, scale=1.3)
    hands = sorted(limb.side.value for limb in cv.limbs.values())
    assert hands == [Side.LEFT.value, Side.RIGHT.value] and {limb.owner for limb in cv.limbs.values()} == {rig}
    assert anatomy_ledger.notes(cv) == []


def _hand_groups(cv, rig):
    return {
        g.get("id"): g for g in ET.fromstring(cv.scene.to_bytes()).iter("group") if f"{rig}-hand-" in g.get("id", "")
    }


def test_a_hand_is_keyed_on_every_drawing_like_its_arm():
    cues = [Cue(0, "sit"), Cue(1.0, "shrug", ease=0.4), Cue(2.0, "sit-show", flip=True, ease=0.4)]
    cv = canvas()
    blob.blob(cv, cv.comp, cues, end=3.0, id="pip", look=blob.Look("pip", hands=True))
    frames = blob.drawings(cues, end=3.0)
    paths = [s for g in _hand_groups(cv, "pip").values() for s in g if s.get("shape") == "path"]
    assert paths and all(len(s.findall("animate")) == 1 for s in paths)
    keyed = [s.find("animate") for s in paths]
    assert all(len(a.findall("key")) == len(frames) for a in keyed)


def test_a_hand_on_an_arm_behind_the_body_is_drawn_behind_it_and_in_front_when_the_arm_is():
    cues = [Cue(0, "sit"), Cue(1.0, "stand")]  # sit: the far arm behind; stand: both arms in front
    cv = canvas()
    blob.blob(cv, cv.comp, cues, end=2.0, id="pip", look=blob.Look("pip", hands=True))
    ids = set(_hand_groups(cv, "pip"))
    assert {f"pip-hand-{a}-back-{p}" for a in blob.ARMS for p in ("outline", "fill")} <= ids
    assert {"pip-hand-arm_l-front", "pip-hand-arm_r-front", "pip-hand-arm_l-front-fill"} <= ids


def test_a_hand_is_refused_a_pose_it_does_not_know():
    with pytest.raises(BlobError, match="pose"):
        blob.facing("moonwalk", "arm_l")
    with pytest.raises(BlobError, match="arm"):
        blob.facing("sit", "leg_l")


@pytest.mark.parametrize("pose", ("phone-a", "phone-b", "sit-show"))
def test_a_held_prop_still_rides_between_the_hands(pose):
    p = blob.POSES[pose]
    sides = blob.arm_sides(p)
    hands = [blob.mitten(p.limbs[arm], sides[arm], blob.facing(pose, arm)) for arm in blob.ARMS]
    xs = [x for palm, thumb in hands for x, _ in palm + thumb]
    ys = [y for palm, thumb in hands for _, y in palm + thumb]
    held = [(p.limbs["arm_l"].p3[i] + p.limbs["arm_r"].p3[i]) / 2 for i in (0, 1)]  # where blob.held puts a prop
    assert min(xs) < held[0] < max(xs) and min(ys) <= held[1] <= max(ys)


# -- versions: a hand is a new look, proposed until it is approved ------------------------------------------------
@pytest.mark.parametrize("rig", HANDED)
def test_the_handed_drawing_is_version_2_and_proposed(rig):
    v2 = parts.get(rig).version(2)
    assert v2.status == "proposed" and v2.approval is None
    assert parts.get(rig).latest().number == 1  # never the default before it is approved
    assert parts.routed(rig, "character", "soft")
    assert f"{rig}@2" in specimens.SPECIMENS


def test_a_soft_prop_still_takes_no_second_version():
    assert not parts.routed("soft-tongs", "prop", "soft")
