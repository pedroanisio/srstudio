"""A 2D track lifted onto the shared skeleton (``pose_lift.lift``) and its foot contacts (``pose_lift.contacts``).
Every track here is synthetic: a standing dancer drawn from a few numbers."""

import math

import pytest

from srstudio import pose_lift
from srstudio import skeleton as sk
from srstudio._retarget_feet import Plant
from srstudio.pose_clean import JOINTS

THIGH = SHIN = 200.0  # picture px
FPS = 30.0


def frame(
    *, x: float = 500.0, ankle_y: float = 900.0, left_ankle_dy: float = 0.0, thigh: float = THIGH
) -> tuple[tuple[float, float], ...]:
    """A dancer facing the camera, legs straight down, the left foot ``left_ankle_dy`` px above the right; a ``thigh``
    shorter than :data:`THIGH` is a thigh turned in depth (the knee and ankle rise to meet it)."""
    hip_y = ankle_y - THIGH - SHIN
    lh, rh = (x + 40, hip_y), (x - 40, hip_y)
    lk, rk = (lh[0], hip_y + thigh), (rh[0], hip_y + THIGH)
    la, ra = (lh[0], hip_y + thigh + SHIN - left_ankle_dy), (rh[0], ankle_y)
    neck, head = (x, hip_y - 300), (x, hip_y - 380)
    ls, rs = (x + 70, hip_y - 290), (x - 70, hip_y - 290)
    le, re_ = (x + 70, hip_y - 160), (x - 70, hip_y - 160)
    lw, rw = (x + 70, hip_y - 40), (x - 70, hip_y - 40)
    return (head, neck, ls, le, lw, rs, re_, rw, lh, lk, la, rh, rk, ra, (x, hip_y))


def stand(count: int, **kw: float) -> list:
    return [frame(**kw) for _ in range(count)]


PX = pose_lift.lift(stand(2), FPS).px_per_m  # picture px per metre: every track here has the same legs


# lift


def test_a_frontal_stance_lifts_at_one_picture_leg_per_mannequin_leg():
    lifted = pose_lift.lift(stand(10), FPS)
    leg_m = sk.JOINT_TABLE.reference_height_m * (
        sk.joint("left_lower_leg").offset.length + sk.joint("left_foot").offset.length
    )
    assert lifted.px_per_m == pytest.approx((THIGH + SHIN) / leg_m)
    assert lifted.floor_px == pytest.approx(900.0)
    assert lifted.clip.frame_count == 10 and lifted.clip.fps == FPS
    assert lifted.clip.source.kind == "lifted"


def test_a_full_length_bone_reads_flat_in_the_picture_and_a_short_one_as_turned_in_depth():
    flat = pose_lift.lift(stand(10), FPS)
    assert flat.in_depth["thigh"] == 0.0
    bent = pose_lift.lift(stand(10) + stand(10, thigh=0.6 * THIGH), FPS)
    assert bent.in_depth["thigh"] == pytest.approx(10 / (20 * 2))


def test_the_hips_travel_with_the_pelvis_across_the_picture_and_never_in_depth():
    track = [frame(x=500.0 + 10 * i) for i in range(10)]
    lifted = pose_lift.lift(track, FPS)
    roots = [f.root_translation for f in lifted.clip.frames]
    assert roots[9][0] == pytest.approx(-90.0 / lifted.px_per_m)  # the picture's +x is the skeleton's -x
    assert all(r[2] == 0.0 for r in roots)


def test_the_lifted_clip_s_source_is_the_digest_of_the_points_it_was_lifted_from():
    a, b = pose_lift.lift(stand(5), FPS), pose_lift.lift(stand(5, x=501.0), FPS)
    assert a.clip.source.digest != b.clip.source.digest
    assert a.clip.source.digest == pose_lift.lift(stand(5), FPS).clip.source.digest


@pytest.mark.parametrize(
    "frames, fps",
    [
        ([], FPS),
        (stand(1), FPS),
        (stand(3), True),
        (stand(3), 0.0),
        (stand(3), float("nan")),
        (stand(3), 1e6),
        ([frame(), frame()[:14]], FPS),
        ([frame(), ((float("inf"), 0.0),) + frame()[1:]], FPS),
        ([frame(), ((1e7, 0.0),) + frame()[1:]], FPS),
        ([frame(), (("1", 0.0),) + frame()[1:]], FPS),
        ([frame(), ((False, 0.0),) + frame()[1:]], FPS),
        ("frames", FPS),
    ],
    ids=[
        "empty",
        "one-frame",
        "bool-fps",
        "zero-fps",
        "nan-fps",
        "huge-fps",
        "short-frame",
        "infinite-point",
        "off-picture-point",
        "text-coordinate",
        "bool-coordinate",
        "text-track",
    ],  # fmt: skip
)
def test_a_malformed_track_is_refused_with_a_pose_lift_error(frames, fps):
    with pytest.raises(pose_lift.PoseLiftError):
        pose_lift.lift(frames, fps)


@pytest.mark.parametrize("kw", [{"start_s": -1.0}, {"start_s": float("nan")}, {"floor_px": float("inf")}])
def test_a_bad_start_or_floor_is_refused(kw):
    with pytest.raises(pose_lift.PoseLiftError):
        pose_lift.lift(stand(3), FPS, **kw)


def test_a_track_whose_bones_have_no_length_is_refused():
    point = ((500.0, 500.0),) * len(JOINTS)
    with pytest.raises(pose_lift.PoseLiftError, match="no length"):
        pose_lift.lift([point, point], FPS)


def test_from_clean_takes_only_a_clean_track():
    with pytest.raises(pose_lift.PoseLiftError, match="CleanTrack"):
        pose_lift.from_clean(stand(3))


# contacts: the floor is local


def test_a_dancer_who_steps_toward_the_camera_is_planted_on_both_floors_within_6_cm_of_the_local_floor():
    """Depth travel moves the feet down the picture: 3 s standing, then 3 s standing 0.2 m (in picture terms) lower.
    One floor for the take (its 95% quantile) would put the first stand 0.2 m in the air; the floor within
    CONTACT_FLOOR_S of each frame plants both."""
    track = stand(90) + stand(90, ankle_y=900.0 + 0.2 * PX)
    lifted = pose_lift.lift(track, FPS)
    plants = pose_lift.contacts(track, lifted)
    left = [p for p in plants if p.side == "left"]
    assert left[0].first == 0 and left[0].last >= 60
    assert any(p.first <= 120 and p.last == 179 for p in left)


def test_a_foot_lifted_6_cm_over_the_local_floor_is_not_planted_and_one_lifted_less_is():
    for dy, down in ((0.05 * PX, True), (0.07 * PX, False)):
        track = stand(30, left_ankle_dy=dy)
        sides = {p.side for p in pose_lift.contacts(track, pose_lift.lift(track, FPS, floor_px=900.0))}
        assert ("left" in sides) is down and "right" in sides


def test_a_foot_that_moves_faster_than_0_35_m_s_is_not_planted():
    track = [frame(x=500.0 + 0.5 * PX / FPS * i) for i in range(30)]
    assert pose_lift.contacts(track, pose_lift.lift(track, FPS)) == ()


def test_a_stand_shorter_than_0_12_s_is_no_plant():
    track = [frame(left_ankle_dy=0.0 if i in (10, 11) else 60.0) for i in range(30)]
    plants = pose_lift.contacts(track, pose_lift.lift(track, FPS, floor_px=900.0))
    assert not [p for p in plants if p.side == "left"]


def test_contacts_are_ordered_by_start_then_side_and_carry_the_clip_s_times():
    track = stand(30)
    plants = pose_lift.contacts(track, pose_lift.lift(track, FPS))
    assert [p.side for p in plants] == ["left", "right"]
    assert plants[0] == Plant("left", 0, 29, 0.0, pytest.approx(29 / FPS))


@pytest.mark.parametrize(
    "kw",
    [
        {"height_m": 0.0},
        {"height_m": True},
        {"speed_m_s": 6.0},
        {"min_s": -1.0},
        {"floor_s": 0.0},
        {"floor_s": float("nan")},
    ],  # fmt: skip
)
def test_bad_contact_thresholds_are_refused(kw):
    track = stand(10)
    with pytest.raises(pose_lift.PoseLiftError):
        pose_lift.contacts(track, pose_lift.lift(track, FPS), **kw)


def test_a_track_that_is_not_the_lifted_clip_s_length_is_refused():
    with pytest.raises(pose_lift.PoseLiftError, match="frames"):
        pose_lift.contacts(stand(9), pose_lift.lift(stand(10), FPS))


def test_the_local_floor_window_is_a_named_constant_of_1_2_s():
    assert pose_lift.CONTACT_FLOOR_S == 1.2
    assert math.isfinite(pose_lift.CONTACT_HEIGHT_M)


def test_the_local_floor_is_the_running_maximum_of_the_lower_ankle_over_the_window():
    lowest = [float((i * 37) % 23) for i in range(50)]
    for half in (0, 1, 4, 60):
        expected = [max(lowest[max(0, i - half) : i + half + 1]) for i in range(50)]
        assert pose_lift._local_floor(lowest, half) == expected
