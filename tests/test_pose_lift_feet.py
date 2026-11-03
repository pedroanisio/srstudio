"""Foot headings for a track that ends at the ankle (``pose_lift.foot_headings``): the pelvis' facing from the picture's
hip-line width, its direction from both knees' bow, held per plant. Every track here is synthetic."""

import math

import pytest

from srstudio import pose_lift
from srstudio._retarget_feet import Plant

HIP_W = 80.0  # the full hip width of the synthetic dancer, picture px
LEG = 200.0  # hip to knee and knee to ankle, picture px


def frame(width: float = HIP_W, bows: tuple[float, float] = (0.0, 0.0), x: float = 500.0) -> tuple:
    """One picture of a standing dancer: hips ``width`` apart (left hip on the picture's right when facing the
    camera), each knee ``bows`` px off its straight hip-ankle line (left, right)."""
    lh, rh = (x + width / 2, 500.0), (x - width / 2, 500.0)
    lk, rk = (lh[0] + bows[0], 500.0 + LEG), (rh[0] + bows[1], 500.0 + LEG)
    la, ra = (lh[0], 500.0 + 2 * LEG), (rh[0], 500.0 + 2 * LEG)
    head, neck = (x, 150.0), (x, 220.0)
    ls, rs = (x + 60, 240.0), (x - 60, 240.0)
    return (head, neck, ls, (x + 70, 330.0), (x + 70, 420.0), rs, (x - 70, 330.0), (x - 70, 420.0),
            lh, lk, la, rh, rk, ra, (x, 500.0))  # fmt: skip


def take(*runs: tuple[int, dict]) -> list:
    """A track of runs: (frames, frame() keywords)."""
    return [frame(**kw) for count, kw in runs for _ in range(count)]


def both(first: int, last: int) -> list[Plant]:
    return [Plant(side, first, last, first / 30, last / 30) for side in ("left", "right")]


BOW = 0.1 * 2 * LEG  # a knee bowed 10% of the leg, over KNEE_BOW


# Facing from the hip line's width


def test_a_hip_line_at_full_width_faces_the_camera_and_points_both_feet_at_it():
    track = take((40, {}))
    h = pose_lift.foot_headings(track, both(0, 39))
    assert h.left == h.right == (0.0,) * 40


def test_half_hip_width_and_both_knees_bowing_over_4_percent_of_the_leg_to_the_right_turn_both_feet_60_degrees_right():
    track = take((40, {}), (40, {"width": HIP_W / 2, "bows": (BOW, BOW)}))
    h = pose_lift.foot_headings(track, both(0, 39) + both(50, 79))
    assert h.left[60] == pytest.approx(math.radians(60), abs=1e-9)
    assert h.right[60] == pytest.approx(math.radians(60), abs=1e-9)
    assert all(h.signed[48:])


def test_both_knees_bowing_over_4_percent_of_the_leg_to_picture_left_turn_the_feet_left_by_the_same_rule():
    track = take((40, {}), (40, {"width": HIP_W / 2, "bows": (-BOW, -BOW)}))
    h = pose_lift.foot_headings(track, both(50, 79))
    assert h.left[60] == pytest.approx(-math.radians(60), abs=1e-9)


def test_a_narrow_hip_line_with_the_knees_bowing_apart_reads_no_direction_and_invents_no_twist():
    """Knees bowing outward is a frontal plié, not a turn: the width says 60 degrees, but no way is read."""
    track = take((40, {}), (40, {"width": HIP_W / 2, "bows": (BOW, -BOW)}))
    h = pose_lift.foot_headings(track, both(50, 79))
    assert h.turn[60] == pytest.approx(math.radians(60), abs=1e-9)
    assert not any(h.read) and not any(h.signed)
    assert h.left[60] == h.right[60] == 0.0


def test_a_narrow_hip_line_with_straight_knees_reads_no_direction_either():
    track = take((40, {}), (40, {"width": HIP_W / 2}))
    h = pose_lift.foot_headings(track, both(50, 79))
    assert h.left[60] == 0.0 and not any(h.signed)


def test_a_hip_line_seen_from_behind_turns_past_90_degrees():
    track = take((40, {}), (40, {"width": -HIP_W / 2, "bows": (BOW, BOW)}))
    h = pose_lift.foot_headings(track, both(50, 79))
    assert h.left[60] == pytest.approx(math.radians(120), abs=1e-9)


def test_a_one_frame_spike_in_hip_width_is_removed_by_the_7_frame_running_median():
    track = take((40, {}), (1, {"width": HIP_W / 4, "bows": (BOW, BOW)}), (40, {}))
    h = pose_lift.foot_headings(track, [])
    assert h.turn[40] == 0.0


# The thresholds: 4% of the leg, reads within 8 frames, two to one


def test_the_thresholds_are_4_percent_of_the_leg_8_frames_and_a_7_frame_median():
    assert (pose_lift.KNEE_BOW, pose_lift.TURN_WINDOW, pose_lift.TURN_MEDIAN) == (0.04, 8, 7)


@pytest.mark.parametrize("share, read", [(0.035, False), (0.045, True)])
def test_both_knees_must_bow_more_than_4_percent_of_the_leg_for_a_direction_read(share, read):
    bow = share * 2 * LEG
    h = pose_lift.foot_headings(take((40, {}), (40, {"width": HIP_W / 2, "bows": (bow, bow)})), [])
    assert any(h.read) is read


def test_one_knee_bowing_alone_reads_no_direction():
    h = pose_lift.foot_headings(take((40, {}), (40, {"width": HIP_W / 2, "bows": (BOW, 0.0)})), [])
    assert not any(h.read)


def test_a_read_signs_frames_within_8_frames_of_it_and_no_farther():
    track = take((40, {"width": HIP_W / 2}), (1, {"width": HIP_W / 2, "bows": (BOW, BOW)}), (40, {"width": HIP_W / 2}))
    h = pose_lift.foot_headings(track, [])
    assert [i for i, s in enumerate(h.signed) if s] == list(range(40 - 8, 40 + 8 + 1))


@pytest.mark.parametrize("against, signed", [(3, True), (4, False)])
def test_a_frame_takes_a_direction_only_when_its_reads_within_8_frames_win_two_to_one(against, signed):
    """Six reads to picture right just before frame 40, then reads to the left from frame 40: three against are still
    two to one, four are not, and a foot planted at frame 40 then faces the camera."""
    runs = [(34, {}), (6, {"width": HIP_W / 2, "bows": (BOW, BOW)})]
    runs += [(against, {"width": HIP_W / 2, "bows": (-BOW, -BOW)}), (40, {"width": HIP_W / 2})]
    h = pose_lift.foot_headings(take(*runs), both(40, 41))
    assert h.signed[40] is signed
    assert h.left[40] == (pytest.approx(math.radians(60), abs=1e-9) if signed else 0.0)


# Held per plant


def test_a_planted_foot_holds_the_heading_of_its_plant_s_first_frame_while_the_body_turns_on_it():
    track = take((40, {}), (20, {"width": HIP_W / 2, "bows": (BOW, BOW)}), (20, {"bows": (BOW, BOW)}))
    h = pose_lift.foot_headings(track, both(45, 79))
    assert h.left[45] == pytest.approx(math.radians(60), abs=1e-9)
    assert set(h.left[45:80]) == {h.left[45]}


def test_a_foot_in_the_air_keeps_the_heading_it_had_when_planted():
    track = take((40, {"width": HIP_W / 2, "bows": (BOW, BOW)}), (40, {}))
    plants = [Plant("left", 10, 20, 10 / 30, 20 / 30), Plant("right", 0, 79, 0.0, 79 / 30)]
    h = pose_lift.foot_headings(track, plants)
    assert set(h.left[21:]) == {h.left[10]}
    assert h.left[10] == pytest.approx(math.radians(60), abs=1e-9)


def test_a_foot_before_its_first_plant_takes_the_take_s_first_frame_heading():
    track = take((40, {}), (40, {"width": HIP_W / 2, "bows": (BOW, BOW)}))
    h = pose_lift.foot_headings(track, [Plant("left", 60, 79, 2.0, 79 / 30)])
    assert set(h.left[:60]) == {0.0}
    assert h.left[60] != 0.0


# Malformed input


@pytest.mark.parametrize(
    "plants, match",
    [
        ("left", "sequence of Plant"),
        ([("left", 0, 3)], "is a Plant"),
        ([Plant("middle", 0, 3, 0.0, 0.1)], "left or the right"),
        ([Plant("left", 5, 2, 0.0, 0.1)], "forward"),
        ([Plant("left", 0, 40, 0.0, 1.0)], "forward"),
        ([Plant("left", -1, 3, 0.0, 0.1)], "forward"),
    ],
)
def test_malformed_plants_are_refused(plants, match):
    with pytest.raises(pose_lift.PoseLiftError, match=match):
        pose_lift.foot_headings(take((40, {})), plants)


@pytest.mark.parametrize(
    "track",
    [
        [],
        [frame()],
        [frame(), frame()[:14]],
        [frame(), (frame()[0], (float("nan"), 1.0)) + frame()[2:]],
        [frame(), ((True, 1.0),) + frame()[1:]],
        "not a track",
    ],
)
def test_a_malformed_track_is_refused(track):
    with pytest.raises(pose_lift.PoseLiftError):
        pose_lift.foot_headings(track, [])


def test_hips_that_never_stand_apart_are_refused():
    with pytest.raises(pose_lift.PoseLiftError, match="never stand apart"):
        pose_lift.foot_headings(take((10, {"width": 0.0})), [])
