"""The Stick rig's feet along ankle -> toe (``stick.RigPose.toes``): a frontal stance splays its feet, a turned body
points both feet the way it faces, a planted foot keeps its direction, and a pose with no toes draws the legacy run."""

import math
import re
from dataclasses import replace

import pytest
from sr_core.scene import Scene

from srstudio import DAYLIGHT, Canvas, dance, flat_counter, stick
from srstudio import stick_dance as sd
from srstudio.music import Groove

STAND = stick.STANDING["stand"]
FACE = stick.Face()
NUMBER = r"(-?\d+(?:\.\d+)?)"


def canvas() -> Canvas:
    scene = Scene(version="auto")
    scene.add_project(width=1080, height=1920, fps="25", duration=1.0, background="#bda77a")
    return Canvas(scene, DAYLIGHT, font_asset=None, namer=flat_counter("n"))


def drawn(pose: stick.RigPose, *, swing: stick.Swing | None = None) -> bytes:
    cv = canvas()
    stick.rig(cv, cv.comp, [stick.RigKey(0, "p", FACE)], 1.0, poses={"p": pose}, swing=swing)
    return cv.scene.to_bytes(layout="pretty")


def foot_ends(pose: stick.RigPose, *, swing: stick.Swing | None = None) -> list[tuple[float, float]]:
    """Where each leg's stroke ends, far then near: the last point of each path that passes through an ankle."""
    text = drawn(pose, swing=swing).decode()
    ends = []
    for i, ankle in enumerate(pose.feet):
        mark = f"{ankle[0]:g} {ankle[1]:g}" if swing is None else f"{ankle[0]:.1f} {ankle[1]:.1f}"
        paths = [d for d in re.findall(r'path="([^"]+)"', text) if mark in d]
        assert paths, f"no leg passes through the ankle {ankle}"
        path = paths[i] if pose.feet[0] == pose.feet[1] else paths[0]  # far leg first, as drawn
        x, y = re.findall(rf"{NUMBER} {NUMBER}", path)[-1]
        ends.append((float(x), float(y)))
    return ends


def with_toes(pose: stick.RigPose, run: tuple[tuple[float, float], tuple[float, float]]) -> stick.RigPose:
    toes = tuple((f[0] + r[0], f[1] + r[1]) for f, r in zip(pose.feet, run, strict=True))
    return replace(pose, toes=toes)


# The legacy run


@pytest.mark.parametrize("swing", [None, stick.Swing()])
def test_a_pose_with_no_toes_draws_the_legacy_run_of_46_forward_and_4_down(swing):
    for (ax, ay), (ex, ey) in zip(STAND.feet, foot_ends(STAND, swing=swing), strict=True):
        assert (ex - ax, ey - ay) == pytest.approx(stick.FOOT_RUN, abs=0.06)


def test_the_published_poses_carry_no_toes():
    for poses in (stick.SEATED, stick.STANDING):
        assert all(p.toes is None for p in poses.values())


# The drawn direction


@pytest.mark.parametrize("swing", [None, stick.Swing()])
def test_a_frontal_standing_pose_aimed_at_the_lens_draws_its_feet_pointing_away_from_each_other(swing):
    pose = replace(with_toes(STAND, ((0.0, 4.0), (0.0, 4.0))), feet=((520.0, 1700.0), (560.0, 1700.0)))
    pose = replace(pose, toes=((520.0, 1704.0), (560.0, 1704.0)))
    (lx, _), (rx, _) = foot_ends(pose, swing=swing)
    assert lx < 520.0 - 15 and rx > 560.0 + 15


def test_feet_on_one_x_still_splay_both_ways_never_the_same_way():
    pose = replace(STAND, feet=((540.0, 1700.0), (540.0, 1700.0)), toes=((540.0, 1704.0), (540.0, 1704.0)))
    (a, _), (b, _) = foot_ends(pose)
    assert (a - 540.0) * (b - 540.0) < 0


def test_a_foot_aimed_at_the_lens_is_drawn_no_shorter_than_the_floor():
    pose = replace(STAND, feet=((500.0, 1700.0), (580.0, 1700.0)), toes=((500.0, 1701.0), (580.0, 1701.0)))
    for (ax, ay), (ex, ey) in zip(pose.feet, foot_ends(pose), strict=True):
        assert math.hypot(ex - ax, ey - ay) >= stick.FOOT_MIN - 0.06


@pytest.mark.parametrize("sign", [-1, 1])
def test_a_three_quarter_yaw_of_35_degrees_draws_both_feet_toward_the_facing_side(sign):
    run = (sign * stick.FOOT_RUN[0] * math.sin(math.radians(35)), stick.FOOT_RUN[1])
    pose = with_toes(replace(STAND, feet=((510.0, 1700.0), (570.0, 1700.0))), (run, run))
    for (ax, _), (ex, _) in zip(pose.feet, foot_ends(pose), strict=True):
        assert (ex - ax) * sign > 10


def test_a_foot_seen_in_full_side_view_keeps_the_canon_length_and_direction():
    pose = with_toes(STAND, (stick.FOOT_RUN, stick.FOOT_RUN))
    for (ax, ay), (ex, ey) in zip(pose.feet, foot_ends(pose), strict=True):
        assert (ex - ax, ey - ay) == pytest.approx(stick.FOOT_RUN, abs=0.06)


def test_a_toe_farther_than_a_full_foot_is_refused():
    pose = with_toes(STAND, ((120.0, 0.0), stick.FOOT_RUN))
    with pytest.raises(stick.StickDataError, match="toe"):
        drawn(pose)


@pytest.mark.parametrize("bad", [(float("nan"), 1700.0), ("540", 1700.0)])
def test_a_toe_that_is_not_a_finite_point_is_refused(bad):
    pose = replace(STAND, toes=(bad, (560.0, 1704.0)))
    with pytest.raises(stick.StickDataError, match="toe"):
        drawn(pose)


# The skeleton solve: toe = ankle + R (0, 0.024, 0.146)

GROOVE = Groove(129)


def standing(move: str = "step-touch", bars: float = 2) -> sd.StickDance:
    return sd.perform(dance.moves()[move], GROOVE, 0.0, bars * GROOVE.bar, seated=False)


def test_perform_gives_every_picture_a_toe_per_foot_within_a_full_foot_of_its_ankle():
    for pose in standing().poses:
        assert pose.toes is not None
        for (ax, ay), (tx, ty) in zip(pose.feet, pose.toes, strict=True):
            assert math.hypot(tx - ax, ty - ay) <= math.hypot(*stick.FOOT_RUN) + 1e-6


def test_perform_s_front_camera_sees_a_level_forward_foot_aimed_at_the_lens_so_the_rig_splays_it():
    pose = standing("head-nod", 0.25).poses[0]
    for (ax, _), (tx, _) in zip(pose.feet, pose.toes, strict=True):
        assert abs(tx - ax) < stick.FOOT_MIN
    (lx, _), (rx, _) = foot_ends(pose)
    order = sorted(range(2), key=lambda i: pose.feet[i][0])
    ends = [(lx, _), (rx, _)]
    assert ends[order[0]][0] < pose.feet[order[0]][0] and ends[order[1]][0] > pose.feet[order[1]][0]


TURNED_OUT = {**sd.STANDING_BASE, "left_foot.twist_in_out": 0.45, "right_foot.twist_in_out": 0.45}


def sway_turned_out(bars: float = 2) -> sd.StickDance:
    """Both feet planted the whole time, turned out, the hips swaying on the beat: the foot bones turn every picture."""
    return sd.perform(dance.moves()["hip-sway"], GROOVE, 0.0, bars * GROOVE.bar, seated=False, base=TURNED_OUT)


def test_a_turned_out_planted_foot_keeps_its_direction_while_planted():
    poses = sway_turned_out().poses
    for i in range(2):
        runs = {(p.toes[i][0] - p.feet[i][0], p.toes[i][1] - p.feet[i][1]) for p in poses}
        assert len({(round(x, 6), round(y, 6)) for x, y in runs}) == 1
        ((x, _),) = list(runs)[:1]
        assert abs(x) > 1.0, "a turned-out foot does not aim at the lens"


def test_a_turned_out_stance_points_each_foot_away_from_the_other():
    pose = sway_turned_out(0.25).poses[0]
    left, right = sorted(range(2), key=lambda i: pose.feet[i][0])
    assert pose.toes[left][0] < pose.feet[left][0] and pose.toes[right][0] > pose.feet[right][0]


def test_the_planted_toe_is_held_because_the_unheld_foot_bone_turns_during_the_sway():
    """The control for the hold: the same dance's foot frames in the world change from picture to picture."""
    from srstudio import skeleton as sk
    from srstudio.dance_pose import dance_pose
    from srstudio.limbs.math3d import Vec3

    base = sk.add(sd.PROFILE, sk.rest_pose(sd.PROFILE), TURNED_OUT, clamp=False)
    seen = set()
    for frame in list(dance.frames(dance.moves()["hip-sway"], GROOVE, 0.0, 2 * GROOVE.bar, 25))[::5]:
        world = sk.world(sd.PROFILE, dance_pose(sd.PROFILE, frame, base=base).pose)
        toe = world["left_foot"].rotation.rotate(Vec3(0, 0.024, 0.146))
        seen.add((round(toe.x, 4), round(toe.y, 4), round(toe.z, 4)))
    assert len(seen) > 1
