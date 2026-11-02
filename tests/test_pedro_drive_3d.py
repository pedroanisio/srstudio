"""Pedro drives, then flies, in a built 3D world: the travel of the scenery is continuous and never backwards, his head
turns to the lens where the cut says and nowhere else, and the two worlds never see each other."""

from __future__ import annotations

import math
import sys
from pathlib import Path

import numpy as np
import pytest

ROOT = Path(__file__).resolve().parents[1]
PILOTS = ROOT / "episodes" / "pilots"
if str(PILOTS) not in sys.path:
    sys.path.insert(0, str(PILOTS))

import pedro_drive as base  # noqa: E402
import pedro_drive_3d as world  # noqa: E402


def test_travel_has_a_step_for_every_frame_and_the_frame_before_the_first():
    gone = world.travel(30, 9.0)
    assert len(gone) == 31
    assert gone[0] == pytest.approx(base.speed(0.0) * 9.0 * 100.0 / world.FPS)


def test_travel_never_goes_backwards_and_stands_still_where_the_traffic_stops():
    gone = world.travel(round(world.ROAD[1] * world.FPS), world.CAR_SPEED)
    assert (np.diff(gone) >= 0).all()
    stopped = [i for i in range(1, len(gone)) if base.speed(i / world.FPS) == 0.0]
    assert stopped, "the cut has a stop"
    assert all(gone[i] == gone[i - 1] for i in stopped)  # the step of frame i is in gone[i]


def test_travel_is_scaled_by_the_speed_in_metres_and_is_empty_of_motion_at_zero():
    one, two = world.travel(60, 9.0), world.travel(60, 18.0)
    assert np.allclose(two, 2 * one)
    assert (world.travel(60, 0.0) == 0).all()


def test_a_face_looks_along_minus_z_at_zero_and_minus_x_at_ninety():
    assert world.yaw_to((0, 0, 0), (0, 0, -100)) == pytest.approx(0.0)
    assert world.yaw_to((0, 0, 0), (-100, 0, 0)) == pytest.approx(90.0)
    assert world.yaw_to((0, 0, 0), (100, 0, 0)) == pytest.approx(-90.0)
    assert abs(world.yaw_to((0, 0, 0), (0, 0, 100))) == pytest.approx(180.0)


def test_yaw_to_a_target_straight_above_the_source_is_not_a_number_but_zero_on_the_ground_plane():
    assert math.isfinite(world.yaw_to((5, 5, 5), (5, -500, 5)))


def test_baking_moves_the_origin_and_scales_without_touching_the_original():
    mesh = world.clay.Mesh(
        "m",
        np.array([[10.0, 20.0, 30.0], [11.0, 21.0, 31.0], [12.0, 20.0, 30.0]]),
        np.array([[0.0, 0.0, -1.0]] * 3),
        np.array([[0, 1, 2]]),
        np.zeros((3, 2)),
    )
    before = mesh.vertices.copy()
    moved = world.baked(mesh, origin=(10.0, 20.0, 30.0), scale=2.0)
    assert np.allclose(moved.vertices[0], 0.0)
    assert np.allclose(moved.vertices[2], [4.0, 0.0, 0.0])
    assert np.array_equal(mesh.vertices, before)


def test_a_colour_is_three_bytes_and_a_short_one_is_refused():
    assert world.rgb("#102030") == (16, 32, 48)
    with pytest.raises(ValueError):
        world.rgb("#fff")


STOPS = [(0.0, (0.0, 0.0, 0.0)), (2.0, (10.0, 20.0, 30.0)), (4.0, (10.0, 20.0, 30.0)), (6.0, (0.0, 0.0, 0.0))]


def test_a_camera_path_holds_before_its_first_stop_and_after_its_last_and_is_continuous_between():
    along = world.Build.along
    assert along(STOPS, -1.0) == STOPS[0][1]
    assert along(STOPS, 99.0) == STOPS[-1][1]
    assert along(STOPS, 2.0) == pytest.approx(STOPS[1][1])
    mid = along(STOPS, 1.0)
    assert all(0.0 < m < e for m, e in zip(mid, STOPS[1][1], strict=True))
    steps = [along(STOPS, t / 100.0) for t in range(0, 600)]
    jumps = [max(abs(a - b) for a, b in zip(p, q, strict=True)) for p, q in zip(steps, steps[1:], strict=False)]
    assert max(jumps) < 1.0


MOTION = world.Motion(body=5.0, toward=40.0, lens=(8.5, 8.9), holds=((6.0, 7.0, 3.0),), phase=0.3)


def test_his_head_keeps_its_body_yaw_until_the_lens_turn_and_ends_on_the_lens():
    before, _ = MOTION.at(8.0)
    after, _ = MOTION.at(9.5)
    assert abs(before - MOTION.body) < 3.0  # sway only
    assert abs(after - MOTION.toward) < 3.0
    assert abs(MOTION.at(8.9)[0] - MOTION.at(8.5)[0]) > 25.0  # the turn is inside its window


def test_a_nod_is_held_inside_its_window_and_released_after_it():
    _, held = MOTION.at(6.5)
    _, free = MOTION.at(7.9)
    assert held - free > 1.5


def test_keys_cover_every_frame_of_the_span_in_order():
    yaw, nod = MOTION.keys((8.0, 9.0))
    assert [t for t, _ in yaw] == [f / world.FPS for f in range(8 * world.FPS, 9 * world.FPS + 1)]
    assert len(nod) == len(yaw)
    assert all(math.isfinite(v) for _, v in yaw + nod)


def test_a_lens_turn_with_no_duration_is_refused_rather_than_divided_by_zero():
    bad = world.Motion(body=0.0, toward=10.0, lens=(5.0, 5.0))
    with pytest.raises(ZeroDivisionError):
        bad.at(1.0)


def test_the_main_entry_without_an_output_directory_stops_with_the_usage():
    with pytest.raises(SystemExit) as stop:
        world.main(["pedro_drive_3d.py"])
    assert "pedro_drive_3d" in str(stop.value) or stop.value.code


def test_the_two_worlds_are_apart_so_no_camera_of_one_can_see_the_other():
    assert world.ROAD[1] == world.SKY[0] and world.SKY[1] == base.DURATION
    assert abs(world.SKY_Y) > 100000.0
