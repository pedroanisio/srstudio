"""Small Print's Great Wall set (ADR 0240): the wall is built in nearly its land's earth and sits on its hills, the arm
carries the station round its pivot, the parts refuse poses they do not have, and the set's sounds are its own."""

from __future__ import annotations

import math

import numpy as np
import pytest

from srstudio import smallprint_wall as wall
from srstudio.clay import Model
from srstudio.foley import Burst


def _meshes(build) -> dict[str, np.ndarray]:
    m = Model()
    build(m)
    out: dict[str, list[np.ndarray]] = {}
    for mesh in m.meshes():
        out.setdefault(mesh.material, []).append(np.asarray(mesh.vertices))
    return {k: np.concatenate(v) for k, v in out.items()}


def _rgb(hex_colour: str) -> np.ndarray:
    return np.array([int(hex_colour[i : i + 2], 16) for i in (1, 3, 5)], float)


def test_every_material_the_set_draws_is_in_its_palette():
    names = set(wall.materials())
    for build in (wall.board, wall.earth_still, wall.window_still, wall.colour_still,
                  lambda m: wall.orbit_parts(m, (10.0, 30.0)), lambda m: wall.earth(m, 20.0),
                  lambda m: wall.moon(m, wall.MOON_FROM), lambda m: wall.astronaut(m, 10.0, 20.0),
                  lambda m: wall.colour_parts(m, 12.0)):  # fmt: skip
        assert set(_meshes(build)) <= names


def test_the_wall_and_the_dirt_are_nearly_the_colour_of_the_land_and_the_snow_is_not():
    palette = wall.materials()
    land = _rgb(palette["land"].color)
    for near in ("wallstone", "dirt", "hillshade"):
        assert np.abs(_rgb(palette[near].color) - land).max() <= 24, near
    assert np.abs(_rgb(palette["snow"].color) - land).max() >= 60


def test_the_wall_stands_on_its_hills_and_inside_the_board():
    parts = _meshes(wall.board)
    stone = parts["wallstone"]
    bx, by, bz = wall.BOARD
    w, h, d = wall.BOARD_SIZE
    assert stone[:, 0].min() >= bx - w / 2 - 3.0 and stone[:, 0].max() <= bx + w / 2 + 3.0
    assert stone[:, 2].min() >= bz - d / 2 - 3.0 and stone[:, 2].max() <= bz + d / 2 + 3.0
    assert stone[:, 1].max() <= by - h + 0.5  # nothing of it sinks under the board's land
    assert stone[:, 1].min() < by - h - 20.0  # the wall rides over the hills: some of it is high up


@pytest.mark.parametrize("swing", [-58.0, 0.0, 30.0, 46.0])
def test_the_arm_carries_the_station_round_its_pivot_at_its_reach(swing):
    x, y, z = wall.station_at(swing)
    px, py, pz = wall.PIVOT
    assert math.hypot(x - px, z - pz) == pytest.approx(wall.ARM)
    assert y - py == pytest.approx(wall.DROP)
    assert (x > px) == (swing > 0) or swing == 0.0


def test_keys_ease_between_them_and_hold_outside():
    keys = ((1.0, 0.0), (2.0, 10.0))
    assert wall.keyed(0.0, keys) == 0.0 and wall.keyed(3.0, keys) == 10.0
    assert wall.keyed(1.5, keys) == pytest.approx(5.0)
    assert wall.keyed(1.1, keys) < 1.0  # eased in
    with pytest.raises(wall.WallError):
        wall.keyed(1.0, ((2.0, 0.0), (1.0, 1.0)))


REFUSED = (
    lambda m: wall.lamp(m, 80.0),
    lambda m: wall.astronaut(m, 50.0, 0.0),
    lambda m: wall.astronaut(m, 0.0, 60.0),
    lambda m: wall.colour_parts(m, 45.0),
)


@pytest.mark.parametrize("call", REFUSED)
def test_a_pose_the_set_does_not_have_is_refused(call):
    with pytest.raises(wall.WallError):
        call(Model())


def test_the_knife_pushes_the_block_into_the_dirt():
    before, after = _meshes(lambda m: wall.colour_parts(m, 0.0)), _meshes(lambda m: wall.colour_parts(m, 30.0))
    dirt = _meshes(wall.dirt)["dirt"]
    assert after["wallstone"][:, 0].max() - before["wallstone"][:, 0].max() == pytest.approx(30.0)
    assert before["wallstone"][:, 0].max() < dirt[:, 0].min() < after["wallstone"][:, 0].max()  # meets it, goes in
    assert before["blade"][:, 0].max() <= before["wallstone"][:, 0].min() + 0.5  # the blade is at the block's end


def test_the_moon_is_drawn_smaller_and_the_globe_turns():
    small, big = (
        _meshes(lambda m: wall.moon(m, (0.0, -300.0, -200.0), 0.5)),
        _meshes(lambda m: wall.moon(m, (0.0, -300.0, -200.0))),
    )
    assert np.ptp(small["moonclay"][:, 0]) == pytest.approx(np.ptp(big["moonclay"][:, 0]) / 2)
    a, b = _meshes(lambda m: wall.earth(m, 0.0)), _meshes(lambda m: wall.earth(m, 40.0))
    assert not np.allclose(a["green"], b["green"])


def test_the_window_shows_space_and_the_earth_under_him():
    parts = _meshes(wall.window_still)
    x, y, _ = wall.WINDOW
    for name in ("porthole", "sea", "desert"):
        p = parts[name]
        assert np.hypot(p[:, 0] - x, p[:, 1] - y).max() <= wall.WINDOW_R + 1e-6, name
    assert parts["sea"][:, 1].min() >= y + wall.WINDOW_R * 0.35 - 1e-6  # the Earth's curve is in the window's foot


def test_the_servo_runs_only_while_the_arm_swings():
    keys = ((0.0, -50.0), (1.0, -50.5), (2.0, 10.0), (3.0, 40.0))
    assert wall.servo_spans(keys) == [(1.0, 2.0), (2.0, 3.0)]


def test_the_sets_sounds_are_its_own_bursts():
    assert all(isinstance(s, Burst) for s in (wall.SERVO, wall.SWITCH, wall.SCRAPE))
    assert wall.SWITCH.seconds < 0.1 < wall.SERVO.seconds  # a click and a whirr
