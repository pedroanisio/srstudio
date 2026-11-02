"""``stick.rig(swing=...)``: each limb and the body line drawn as one curve through its joints, bowed against the
joints' travel within a cap; without it the rig draws exactly what it always drew."""

import hashlib
import math
import re
import xml.etree.ElementTree as ET
from dataclasses import replace

import pytest
from sr_core.scene import Scene

from srstudio import DAYLIGHT, Canvas, dance, flat_counter, stick
from srstudio import stick_dance as sd
from srstudio.music import Groove

STAND = stick.STANDING["stand"]
SHOULDER = (STAND.neck[0] - 4, STAND.neck[1] + 34)
NUMBER = r"-?\d+(?:\.\d+)?"


def canvas() -> Canvas:
    scene = Scene(version="auto")
    scene.add_project(width=1080, height=1920, fps="25", duration=2.0, background="#bda77a")
    return Canvas(scene, DAYLIGHT, font_asset="inter", namer=flat_counter("n"))


def shifted(pose: stick.RigPose, dx: float) -> stick.RigPose:
    """``pose`` moved ``dx`` pixels right, every joint alike."""

    def move(p):
        return (p[0] + dx, p[1])

    pairs = (pose.knees, pose.feet, pose.elbows, pose.hands)
    return stick.RigPose(move(pose.head), move(pose.neck), move(pose.hip), *(tuple(map(move, p)) for p in pairs))


def bodies(cv: Canvas, rig) -> list[list[str]]:
    """Each key's body group: the ``path`` of every stroke in it, in drawing order."""
    root = ET.fromstring(cv.scene.to_bytes(layout="pretty")).find(f".//*[@id='{rig.id}']")
    assert root is not None
    groups = [g for g in root.findall("group") if g.find("shape[@shape='ellipse']") is None]
    return [[s.get("path") for s in g.findall("shape[@shape='path']")] for g in groups if g.find("shape") is not None]


def points(path: str) -> list[tuple[float, float]]:
    """Every number pair in ``path``, in order: the start, then each curve's two handles and its end."""
    values = [float(v) for v in re.findall(NUMBER, path)]
    return list(zip(values[::2], values[1::2], strict=True))


def drawn(poses: dict, names: list[str], *, swing=None, look=stick.PLAIN, step=0.04):
    cv = canvas()
    keys = [stick.RigKey(round(i * step, 6), name) for i, name in enumerate(names)]
    rig = stick.rig(cv, cv.comp, keys, round(len(names) * step, 6), poses=poses, look=look, swing=swing)
    return cv, bodies(cv, rig)


# The rig's scene bytes before swing existed, for a seated and a standing performance with a neck, a tie, a blink
# and held faces: the off path must keep drawing exactly these.
BEFORE = {
    "seated": "0f57ccde29c570f2a5236aa306b801596b127321fb5379d1873f771a54feb6ee",
    "standing": "32de58110f176a1efa6e6a62682a4a65c875e139d7b131f98ea455c9767da800",
}


@pytest.mark.parametrize("which", ["seated", "standing"])
@pytest.mark.parametrize("explicit", [False, True])
def test_without_swing_the_rig_draws_exactly_what_it_drew_before(which, explicit):
    poses = stick.SEATED if which == "seated" else stick.STANDING
    names = list(poses)
    keys = [stick.RigKey(round(i * 0.04, 6), names[i % len(names)], stick.Face()) for i in range(12)]
    cv = canvas()
    extra = {"swing": None} if explicit else {}
    stick.rig(cv, cv.comp, keys, 0.6, poses=poses, look=stick.Look(neck=True, tie="#aa3333"), blinks=(0.1,),
              held_faces=True, **extra)  # fmt: skip
    assert hashlib.sha256(cv.scene.to_bytes()).hexdigest() == BEFORE[which]


def test_each_limb_and_the_body_line_is_one_curve_through_its_joints():
    _, [straight] = drawn({"stand": STAND}, ["stand"])
    _, [curved] = drawn({"stand": STAND}, ["stand"], swing=stick.Swing())
    assert len(curved) == len(straight) == 5  # two legs, two arms and the body line, one stroke each
    assert all(" C " not in p for p in straight)
    far_leg, far_arm, spine, near_leg, near_arm = (points(p) for p in curved)
    assert far_leg[0] == STAND.hip and far_leg[3] == STAND.knees[0] and far_leg[6] == STAND.feet[0]
    assert far_leg[7] == (STAND.feet[0][0] + 46, STAND.feet[0][1] + 4)  # the foot is still a short straight run
    assert near_leg[3] == STAND.knees[1] and near_leg[6] == STAND.feet[1]
    assert far_arm[0] == SHOULDER and far_arm[3] == STAND.elbows[0] and far_arm[6] == STAND.hands[0]
    assert near_arm[3] == STAND.elbows[1] and near_arm[6] == STAND.hands[1]
    assert spine[0] == STAND.neck and spine[-1] == STAND.hip and len(spine) == 4


def test_with_a_neck_the_body_line_runs_from_under_the_head_through_the_neck_to_the_hips():
    _, [curved] = drawn({"stand": STAND}, ["stand"], swing=stick.Swing(), look=stick.Look(neck=True))
    spine = points(curved[2])
    under = STAND.head[1] + stick.HEAD_R - stick.NECK_SINK
    assert spine[0] == (STAND.head[0], under) and spine[3] == STAND.neck and spine[6] == STAND.hip


def test_a_still_figure_does_not_bow():
    _, [first, second] = drawn({"stand": STAND}, ["stand", "stand"], swing=stick.Swing())
    assert first == second
    spine = points(first[2])
    assert {x for x, _ in spine} == {STAND.neck[0]}  # head, neck and hips on one vertical: the line stays straight


def test_a_moving_figure_bows_against_its_travel_by_the_drag():
    dx, step = 8.0, 0.04
    swing = stick.Swing(drag=0.1, cap=0.3)
    _, [_, moved] = drawn({"a": STAND, "b": shifted(STAND, dx)}, ["a", "b"], swing=swing, step=step)
    spine = points(moved[2])
    speed = dx / step  # one-sided at the last key: 200 px a second to the right
    x = STAND.neck[0] + dx
    assert spine[0][0] == x and spine[3][0] == x
    for hx, _ in spine[1:3]:  # both handles trail to the left by drag * speed
        assert hx == pytest.approx(x - swing.drag * speed, abs=0.06)


def test_a_fast_move_bows_no_further_than_the_cap():
    dx, step = 200.0, 0.04  # 5000 px a second
    swing = stick.Swing(drag=0.1, cap=0.3)
    _, [_, moved] = drawn({"a": STAND, "b": shifted(STAND, dx)}, ["a", "b"], swing=swing, step=step)
    spine = points(moved[2])
    bone = math.dist(STAND.neck, STAND.hip)
    for hx, _ in spine[1:3]:
        assert hx == pytest.approx(STAND.neck[0] + dx - swing.cap * bone, abs=0.06)


def test_no_drag_draws_the_plain_curve_through_the_joints():
    dx = 30.0
    _, [_, still] = drawn({"a": STAND, "b": shifted(STAND, dx)}, ["a", "b"], swing=stick.Swing(drag=0.0))
    _, [plain] = drawn({"b": shifted(STAND, dx)}, ["b"], swing=stick.Swing())
    assert still == plain


@pytest.mark.parametrize("dx", [8.0, 60.0])
def test_a_bowed_limb_bends_at_its_joints_without_a_kink(dx):
    _, [_, moved] = drawn({"a": STAND, "b": shifted(STAND, dx)}, ["a", "b"], swing=stick.Swing())
    for stroke in (moved[0], moved[1], moved[3], moved[4]):  # both legs and both arms
        p = points(stroke)
        (ax, ay), (jx, jy), (bx, by) = p[2], p[3], p[4]  # the handle into the knee or elbow, the joint, the one out
        into, out = (jx - ax, jy - ay), (bx - jx, by - jy)
        sine = (into[0] * out[1] - into[1] * out[0]) / (math.hypot(*into) * math.hypot(*out))
        assert abs(sine) < 0.01  # one tangent through the joint, up to the path's 0.1 px rounding
        assert into[0] * out[0] + into[1] * out[1] > 0


def test_a_long_hold_barely_drags():
    poses = {"a": STAND, "b": shifted(STAND, 8.0)}
    _, [_, held, _] = drawn(poses, ["a", "b", "b"], swing=stick.Swing(), step=1.0)
    spine = points(held[2])
    for hx, _ in spine[1:3]:  # 8 px over two seconds is 4 px a second: 0.4 px of drag
        assert hx == pytest.approx(STAND.neck[0] + 8.0 - 0.4, abs=0.06)


@pytest.mark.parametrize(
    "swing",
    [
        stick.Swing(drag=-0.01),
        stick.Swing(drag=0.51),
        stick.Swing(cap=-0.1),
        stick.Swing(cap=0.6),
        stick.Swing(drag=True),
        stick.Swing(cap=float("nan")),
        stick.Swing(drag="0.1"),
        "curves",
        0.1,
    ],
)
def test_a_swing_the_rig_cannot_draw_is_refused(swing):
    cv = canvas()
    with pytest.raises(stick.StickDataError, match="swing"):
        stick.rig(cv, cv.comp, [stick.RigKey(0, "stand")], 0.1, poses=stick.STANDING, swing=swing)


def test_the_contract_describes_swing():
    from srstudio import registry

    described = registry.describe("character", "stick-rig")["contract"]["arguments"]["properties"]["swing"]
    assert described["default"] is None and "curve" in described["description"]


def test_a_stick_dance_turns_swing_on_through_draw():
    performance = sd.perform(dance.moves()["bob"], Groove(129), 0.0, 1.0)
    plain, default, curved = canvas(), canvas(), canvas()
    sd.draw(plain, plain.comp, performance)
    sd.draw(default, default.comp, performance, swing=None)
    rig = sd.draw(curved, curved.comp, performance, swing=sd.SWING)
    assert plain.scene.to_bytes() == default.scene.to_bytes()
    assert sd.SWING == stick.Swing()
    strokes = [p for body in bodies(curved, rig) for p in body]
    assert strokes and all(" C " in p for p in strokes)


def test_a_folded_arm_and_a_bone_of_no_length_still_draw_through_their_joints():
    elbow = (SHOULDER[0], SHOULDER[1] + 150)
    folded = replace(STAND, elbows=(SHOULDER, elbow), hands=((502, 1195), SHOULDER))
    moved_pose = shifted(folded, 8.0)  # carried sideways whole: the folded forearm's handles meet on one side
    _, [_, moved] = drawn({"a": folded, "b": moved_pose}, ["a", "b"], swing=stick.Swing())
    far_arm, near_arm = points(moved[1]), points(moved[4])
    shoulder, hand = moved_pose.elbows[0], moved_pose.hands[0]
    assert far_arm[0] == far_arm[3] == shoulder and far_arm[6] == hand  # the upper arm has no length
    assert near_arm[3] == moved_pose.elbows[1] and near_arm[6] == shoulder  # the forearm folds back to the shoulder
    assert near_arm[2] == near_arm[4]  # a fold has no one tangent: both handles stay where the drag put them
    _, [still] = drawn({"a": folded}, ["a"], swing=stick.Swing())
    near_still = points(still[4])
    assert near_still[2] == near_still[3] == near_still[4] == elbow  # no tangent at a still fold: nothing to turn
    assert all(math.isfinite(v) for p in far_arm + near_arm for v in p)


def test_the_tie_and_the_apron_hang_as_they_always_did():
    look = stick.Look(tie="#aa3333", apron="#3366aa")
    _, [straight] = drawn({"stand": STAND}, ["stand"], look=look)
    _, [curved] = drawn({"stand": STAND}, ["stand"], look=look, swing=stick.Swing())
    assert straight[3:6] == curved[3:6]  # the apron's strap and bib, then the tie, after the body line


def test_an_arm_a_limb_track_replaces_is_not_drawn_as_a_curve():
    from srstudio.limbs import HUMAN, ArmProfile, Camera
    from srstudio.limbs.compile import BakeOptions
    from srstudio.limbs.integration import LimbTrack
    from srstudio.limbs.motion import Action, Motion

    track = LimbTrack(
        Motion(ArmProfile(), HUMAN, (Action("point", duration=2),)),
        style="stick",
        camera=Camera(origin=(62, 712), scale=100),
        options=BakeOptions(fps=2),
    )
    cv = canvas()
    stick.rig(cv, cv.comp, (stick.RigKey(0, "type-a"),), 2, limbs=(track,), swing=stick.Swing())
    curves = [n.attributes().get("path", "") for n in cv.scene.iter("shape")]
    assert sum(" C " in p and p.startswith("M ") for p in curves) == 4  # two legs, the body line, one arm
    assert cv.scene.check(schema=True) == []


# A gesture's timing and acceleration. The drawn hand must move as the skeleton's hand moves, picture by picture: the
# curves pass through the joints the skeleton put there, so the drag bends the limb between them and never delays,
# smooths or resamples the hand. The only difference allowed is the path's 0.1 px rounding: 0.05 px a picture in
# position, so 2.5 px/s in speed and 125 px/s² in acceleration at 25 pictures a second; the tolerances add a margin.
SPEED_TOLERANCE = 3.0  # px/s
ACCELERATION_TOLERANCE = 130.0  # px/s²


def skeleton_hands(move: str, start: float, end: float) -> dict[str, list[tuple[float, float]]]:
    """Each hand's (x, y) in Stick pixels, picture by picture, straight from the skeleton's forward kinematics."""
    from srstudio import skeleton as sk
    from srstudio.dance_pose import dance_pose

    profile = sd.PROFILE
    base = sk.add(profile, sk.rest_pose(profile), sd.STANDING_BASE, clamp=False)
    px = stick.HEAD_R / profile.proportions.head_radius_m
    rest = sk.world(profile, base)
    far, near = sorted(("left", "right"), key=lambda side: rest[f"{side}_upper_arm"].origin.x)
    hands: dict[str, list[tuple[float, float]]] = {"far": [], "near": []}
    for frame in dance.frames(dance.moves()[move], Groove(129), start, end, 25):
        world = sk.world(profile, dance_pose(profile, frame, base=base, clamp=True).pose)
        for name, side in (("far", far), ("near", near)):
            o = world[f"{side}_hand"].origin
            hands[name].append((o.x * px, o.y * px))
    return hands


def drawn_hands(cv: Canvas, rig) -> dict[str, list[tuple[float, float]]]:
    """Each arm stroke's last point, body by body: the hands as the scene draws them."""
    arms = [(points(body[1])[-1], points(body[4])[-1]) for body in bodies(cv, rig)]
    return {"far": [far for far, _ in arms], "near": [near for _, near in arms]}


def profile_of(track: list[tuple[float, float]], fps: int = 25) -> tuple[list[float], list[float]]:
    """Speed and acceleration magnitudes from finite differences, one picture apart."""
    dt = 1 / fps
    velocity = [((b[0] - a[0]) / dt, (b[1] - a[1]) / dt) for a, b in zip(track, track[1:], strict=False)]
    speed = [math.hypot(*v) for v in velocity]
    acceleration = [
        math.hypot((w[0] - v[0]) / dt, (w[1] - v[1]) / dt) for v, w in zip(velocity, velocity[1:], strict=False)
    ]
    return speed, acceleration


@pytest.mark.parametrize("move", ["arm-pump", "clap", "hand-wave-side"])
@pytest.mark.parametrize("swing", [None, stick.Swing(), stick.Swing(drag=0.5, cap=0.5)])
def test_a_drawn_hand_keeps_the_skeleton_s_speed_and_acceleration_over_a_beat(move, swing):
    groove = Groove(129)
    start = groove.beat  # the gesture's second beat, past any blend in
    end = start + groove.beat
    performance = sd.perform(dance.moves()[move], groove, start, end, seated=False)
    cv = canvas()
    rig = sd.draw(cv, cv.comp, performance, begin=0.0, swing=swing)  # keyed from 0: no held picture before it
    ours, theirs = drawn_hands(cv, rig), skeleton_hands(move, start, end)
    assert len(ours["near"]) == len(theirs["near"]) >= 11  # one drawn hand a picture, none resampled or dropped
    assert max(max(profile_of(theirs[side])[0]) for side in theirs) > 300  # the gesture swings a hand
    for side in ("far", "near"):  # the hand the gesture leaves still must stay as still
        speed, acceleration = profile_of(ours[side])
        want_speed, want_acceleration = profile_of(theirs[side])
        assert speed == pytest.approx(want_speed, abs=SPEED_TOLERANCE)
        assert acceleration == pytest.approx(want_acceleration, abs=ACCELERATION_TOLERANCE)
        if max(want_speed) > 50:  # a moving hand's fastest picture is the skeleton's, not delayed
            assert speed.index(max(speed)) == want_speed.index(max(want_speed))
