"""Small Print's soda bench (ADR 0240): a can with a window whose drink, bubbles and rings stay inside it, foam that
runs down the sides and never across the window, a shaker tray, a scale's needle, a timer that turns and his
tapping hand. Bad states are refused."""

from __future__ import annotations

import math

import numpy as np
import pytest

from srstudio import smallprint_soda as soda
from srstudio.clay import Model

FOOT = (0.0, soda.TOP, -197.0)
SPEC = soda.Can(FOOT, "beerpaint")


def _meshes(build) -> dict[str, np.ndarray]:
    m = Model()
    build(m)
    out: dict[str, list[np.ndarray]] = {}
    for mesh in m.meshes():
        out.setdefault(mesh.material, []).append(mesh.vertices)
    return {name: np.concatenate(parts) for name, parts in out.items()}


def test_every_part_has_a_material_and_the_clay_parts_take_his_clay():
    mats = soda.materials()
    assert set(soda.OWN) <= set(mats)
    for name in ("beer", "fizz", "site", "shakerbody", "scalebody", "timerbody", "flesh", "teal", "foam", "steel"):
        assert name in mats
    assert mats["shakerbody"].normal_map and not mats["beer"].normal_map


def test_the_window_is_cut_in_the_front_and_the_paint_is_on_the_back():
    parts = _meshes(lambda m: soda.can(m, SPEC))
    paint = parts["beerpaint"]
    cx, _, cz = FOOT
    mid = (paint[:, 1] > SPEC.lintel + 1) & (paint[:, 1] < SPEC.sill - 1)
    angles = np.degrees(np.arctan2(paint[mid, 0] - cx, -(paint[mid, 2] - cz)))
    assert np.all(np.abs(angles) >= math.degrees(soda.WINDOW) - 0.01)
    assert "canedge" in parts and "tin" in parts


def test_the_window_and_the_drinks_face_lie_inside_the_can():
    assert SPEC.lid < SPEC.lintel < SPEC.sill < FOOT[1]
    assert FOOT[2] - soda.CAN_R < SPEC.face < FOOT[2]
    assert 0 < SPEC.half < soda.CAN_R


@pytest.mark.parametrize("level", [0.0, 0.5, 1.0])
def test_the_drink_stays_inside_the_window_at_any_level(level):
    parts = _meshes(lambda m: soda.drink(m, SPEC, "beer", level))
    for name in ("beer", "beertop"):
        v = parts[name]
        assert np.all(np.abs(v[:, 0] - FOOT[0]) <= SPEC.half + 1e-6)
        assert np.all(v[:, 1] <= SPEC.sill + 1e-6) and np.all(v[:, 1] >= SPEC.lintel - 1e-6)
        assert np.all(np.hypot(v[:, 0] - FOOT[0], v[:, 2] - FOOT[2]) <= soda.CAN_R - soda.WALL + 1e-6)


def test_the_drink_rises_with_its_level_and_its_tab_lifts_when_opened():
    low = _meshes(lambda m: soda.drink(m, SPEC, "cola", 0.2))["colatop"][:, 1].mean()
    high = _meshes(lambda m: soda.drink(m, SPEC, "cola", 0.9))["colatop"][:, 1].mean()
    assert high < low
    shut = _meshes(lambda m: soda.drink(m, SPEC, "beer", 0.8, 0.0))
    opened = _meshes(lambda m: soda.drink(m, SPEC, "beer", 0.8, 1.0))
    assert "black" not in shut and "black" in opened
    assert opened["steel"][:, 1].min() < shut["steel"][:, 1].min()


@pytest.mark.parametrize(
    ("call", "match"),
    [
        (lambda m: soda.drink(m, SPEC, "milk", 0.5), "beer or cola|one of"),
        (lambda m: soda.drink(m, SPEC, "beer", 1.2), "0 to 1"),
        (lambda m: soda.drink(m, SPEC, "beer", 0.5, -0.1), "tab"),
        (lambda m: soda.bubbles(m, SPEC, [soda.Bubble(FOOT[0] + SPEC.half, SPEC.sill - 5, 1.0)]), "outside"),
        (lambda m: soda.bubbles(m, SPEC, [soda.Bubble(FOOT[0], SPEC.lintel - 2, 1.0)]), "outside"),
        (lambda m: soda.bubbles(m, SPEC, [], [(FOOT[0], SPEC.sill + 3)]), "speck"),
        (lambda m: soda.foam(m, SPEC, 0.5, [(10.0, 0.5)]), "cross the window"),
        (lambda m: soda.foam(m, SPEC, 0.5, [(-50.0, 0.5)]), "cross the window"),
        (lambda m: soda.foam(m, SPEC, 1.5), "0 to 1"),
        (lambda m: soda.foam(m, SPEC, 0.5, [(120.0, 1.4)]), "reach"),
        (lambda m: soda.tray(m, FOOT, 9.0), "8 units"),
        (lambda m: soda.needle(m, FOOT, 61.0), "-60 to 60"),
        (lambda m: soda.timer_dial(m, FOOT, math.nan), "degrees"),
        (lambda m: soda.hand(m, FOOT, (0.0, 0.0, 0.0)), "points"),
        (lambda m: soda.closed_can(m, (0.0, 1.0)), "three numbers"),
        (lambda m: soda.rings(m, SPEC, "tea", [], 0.5), "one of"),
    ],
)
def test_a_state_the_bench_does_not_have_is_refused(call, match):
    with pytest.raises(soda.SodaError, match=match):
        call(Model())


@pytest.mark.parametrize(
    ("make", "match"),
    [
        (lambda: soda.Can((0.0, 0.0)), "three numbers"),
        (lambda: soda.Can(FOOT, low=0.9, high=0.5), "0 < low < high < 1"),
        (lambda: soda.Can(FOOT, paint="gold"), "canpaint or beerpaint"),
        (lambda: soda.Bubble(0.0, 0.0, 0.0), "size"),
        (lambda: soda.Ring(0.0, 0.0, 1.0, 1.0), "fades"),
        (lambda: soda.Ring(0.0, math.inf, 1.0), "size"),
    ],
)
def test_a_part_out_of_bounds_is_refused(make, match):
    with pytest.raises(soda.SodaError, match=match):
        make()


def test_bubbles_and_specks_sit_on_the_drinks_face():
    found = [soda.Bubble(FOOT[0] - 3, SPEC.sill - 6, 1.0), soda.Bubble(FOOT[0] + 2, SPEC.sill - 15, 0.6)]
    parts = _meshes(lambda m: soda.bubbles(m, SPEC, found, [(FOOT[0] + 4, SPEC.sill - 8)]))
    assert {"fizz", "site"} <= set(parts)
    fizz = parts["fizz"]
    assert fizz[:, 2].min() < SPEC.face - 0.9  # they stand out of the face toward the lens
    assert np.all(fizz[:, 2] <= SPEC.face + 0.4)  # and sink into it no deeper than a sliver
    assert np.all(np.abs(parts["fizz"][:, 0] - FOOT[0]) <= SPEC.half + 1e-6)


def test_rings_are_drawn_only_inside_the_drink():
    waves = [soda.Ring(FOOT[0], SPEC.sill - 10, r) for r in (2.0, 5.0, 9.0, 20.0)]
    v = _meshes(lambda m: soda.rings(m, SPEC, "cola", waves, 0.8))["colawave"]
    top = SPEC.sill - (SPEC.sill - SPEC.lintel) * 0.8
    assert np.all(np.abs(v[:, 0] - FOOT[0]) <= SPEC.half + 0.5)
    assert np.all(v[:, 1] >= top - 0.5) and np.all(v[:, 1] <= SPEC.sill + 0.5)


def test_foam_wells_over_the_lid_and_runs_down_the_sides():
    none = _meshes(lambda m: soda.foam(m, SPEC, 0.0))
    assert "foam" not in none
    head = _meshes(lambda m: soda.foam(m, SPEC, 1.0))["foam"]
    assert head[:, 1].min() < SPEC.lid
    ran = _meshes(lambda m: soda.foam(m, SPEC, 1.0, [(90.0, 0.8)]))["foam"]
    assert ran[:, 1].max() > SPEC.lid + soda.CAN_TALL * 0.7


def test_the_tray_carries_its_cans_and_rocks_them_with_it():
    feet = soda.tray_feet(FOOT, 0.0)
    assert len(feet) == soda.GRID[0] * soda.GRID[1]
    moved = soda.tray_feet(FOOT, 6.0)
    assert np.allclose(np.array(moved)[:, 0] - np.array(feet)[:, 0], 6.0)
    a = _meshes(lambda m: soda.tray(m, FOOT, -6.0))["beerpaint"]
    b = _meshes(lambda m: soda.tray(m, FOOT, 6.0))["beerpaint"]
    assert math.isclose(b[:, 0].mean() - a[:, 0].mean(), 12.0, abs_tol=1e-6)
    assert "beerpaint" not in _meshes(lambda m: soda.tray(m, FOOT, 0.0, cans=False))


def test_the_shaker_stands_on_the_worktop():
    v = np.concatenate(list(_meshes(lambda m: soda.shaker(m, FOOT)).values()))
    assert v[:, 1].max() <= soda.TOP + 0.5
    assert v[:, 1].min() >= soda.TOP - soda.SHAKER[1] - 1.0


def test_the_needle_turns_with_its_reading_and_the_full_mark_stays():
    def tip(reading: float) -> np.ndarray:
        v = _meshes(lambda m: soda.needle(m, FOOT, reading))["mark"]
        return v[np.argmin(v[:, 1])]

    full, dropped = tip(soda.FULL), tip(soda.FULL - 14.0)
    assert dropped[0] < full[0]
    assert "mark" in _meshes(lambda m: soda.scale(m, FOOT))


def test_the_timer_dial_turns():
    a = _meshes(lambda m: soda.timer_dial(m, FOOT, 0.0))
    b = _meshes(lambda m: soda.timer_dial(m, FOOT, 90.0))
    assert not np.allclose(a["white"], b["white"])
    assert not np.allclose(a["timertop"], b["timertop"])


def test_the_fingertip_is_where_the_hand_is_asked_to_be():
    tip = np.array((10.0, soda.TOP - 30.0, -200.0))
    parts = _meshes(lambda m: soda.hand(m, tip, (1.0, 0.2, 0.4)))
    flesh = parts["flesh"]
    assert np.min(np.linalg.norm(flesh - tip, axis=1)) < 1.5
    assert {"skinlight", "teal", "teallight"} <= set(parts)
    raised = _meshes(lambda m: soda.hand(m, tip, (1.0, 0.2, 0.4), wrist_up=20.0))["flesh"]
    assert not np.allclose(raised, flesh)


@pytest.mark.parametrize(
    ("build", "height"),
    [
        (lambda m: soda.closed_can(m, FOOT), soda.TOP - soda.CAN_TALL - 0.05),
        (lambda m: soda.can(m, SPEC), SPEC.lid + 0.15),
        (lambda m: soda.scale(m, FOOT), soda.TOP - soda.SCALE_BODY[1] - 1.72),
    ],
)
def test_lids_and_pans_are_flat_tops_lit_from_above(build, height):
    m = Model()
    build(m)
    (steel,) = [mesh for mesh in m.meshes() if mesh.material == "steel"]
    on = np.isclose(steel.vertices[:, 1], height)
    assert on.sum() >= 48
    assert np.allclose(steel.normals[on], (0.0, -1.0, 0.0))
