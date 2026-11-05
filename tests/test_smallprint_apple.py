"""Small Print's apple bench (ADR 0240): a knife opens the cells it passes and only those, oxygen drifts over the cut
until it lands on a spilled enzyme, an open cell browns a shade at a time and grows its pigment, and a bare half browns
rim first while the half under lemon juice stays pale. Bad poses are refused."""

from __future__ import annotations

import math

import numpy as np
import pytest

from srstudio import smallprint_apple as ap
from srstudio.clay import Model


def _model(build) -> Model:
    m = Model()
    build(m)
    return m


def _meshes(build) -> dict[str, np.ndarray]:
    out: dict[str, list[np.ndarray]] = {}
    for mesh in _model(build).meshes():
        out.setdefault(mesh.material, []).append(mesh.vertices)
    return {name: np.concatenate(parts) for name, parts in out.items()}


def _slab(**pose) -> dict[str, np.ndarray]:
    full = {"knife": None, "cells": (ap.INTACT,) * ap.CELLS, **pose}
    return _meshes(lambda m: ap.slab_parts(m, ap.SlabPose(**full)))


def _halves(**pose) -> dict[str, np.ndarray]:
    full = {"bare": (0, 0, 0), "kept": (0, 0, 0), **pose}
    return _meshes(lambda m: ap.halves_parts(m, ap.HalvesPose(**full)))


SLAB_POSES = [
    ap.SlabPose(knife=None, cells=(ap.INTACT,) * ap.CELLS),
    ap.SlabPose(knife=0.0, cells=(0, 0, ap.INTACT, ap.INTACT, ap.INTACT) * 3, oxygen=(ap.Wisp((0.0, -300.0, -126.0)),)),
    ap.SlabPose(knife=None, cells=tuple(k % (ap.LEVELS + 1) for k in range(ap.CELLS)), stir=0.5),
]
HALVES_POSES = [
    ap.HalvesPose(bare=(0, 0, 0), kept=(0, 0, 0)),
    ap.HalvesPose(bare=(2, 1, 0), kept=(0, 0, 0), squeeze=0.6, drops=(0.0, 0.5, 1.0), wet=0.4, sand=0.6),
    ap.HalvesPose(bare=(5, 4, 3), kept=(1, 0, 0), wet=1.0, sand=0.0),
]


@pytest.mark.parametrize(
    "build",
    [ap.slab, ap.halves]
    + [lambda m, p=p: ap.slab_parts(m, p) for p in SLAB_POSES]
    + [lambda m, p=p: ap.halves_parts(m, p) for p in HALVES_POSES],
)
def test_every_part_is_drawn_in_a_material_the_bench_has_and_its_surface_is_laid_on(build):
    have = ap.materials()
    for mesh in _model(build).meshes():
        assert mesh.material in have, mesh.material
        done = ap.finished(mesh)
        assert np.isfinite(done.vertices).all()
        if mesh.material in ap.OWN and ap.OWN[mesh.material][3]:
            assert done.uvs is not None


def test_a_shade_runs_pale_to_brown_and_each_step_is_darker():
    colours = [ap.materials()[ap.shade(k)].color for k in range(ap.LEVELS + 1)]
    light = [sum(int(c[i : i + 2], 16) for i in (1, 3, 5)) for c in colours]
    assert light == sorted(light, reverse=True) and len(set(light)) == len(light)


def test_browning_starts_at_its_second_goes_a_step_at_a_time_and_stops_at_the_last_shade():
    levels = [ap.brown_level(t, 2.0, 1.0) for t in np.arange(0.0, 5.0, 0.05)]
    assert levels[0] == 0 and levels[-1] == ap.LEVELS
    assert all(b - a in (0, 1) for a, b in zip(levels, levels[1:], strict=False))
    assert ap.brown_level(1.99, 2.0, 1.0) == 0 and ap.brown_level(3.0, 2.0, 1.0) == ap.LEVELS


@pytest.mark.parametrize("args", [(math.nan, 0.0, 1.0), (1.0, 0.0, 0.0), (1.0, 0.0, -1.0), ("1", 0.0, 1.0)])
def test_a_browning_that_is_not_numbers_or_takes_no_time_is_refused(args):
    with pytest.raises(ap.AppleError, match="browning"):
        ap.brown_level(*args)


def test_the_knife_comes_in_from_the_left_goes_out_at_the_right_and_is_gone_either_side():
    xs = [ap.knife_x(t, 1.0, 2.0) for t in np.arange(0.7, 2.31, 0.05)]
    assert all(x is not None for x in xs)
    assert xs == sorted(xs)  # type: ignore[type-var]
    x0 = ap.SLAB[0] - ap.SLAB[2] / 2
    assert xs[0] < x0 < xs[-1]  # type: ignore[operator]
    assert ap.knife_x(0.5, 1.0, 2.0) is None and ap.knife_x(2.5, 1.0, 2.0) is None
    with pytest.raises(ap.AppleError, match="slice"):
        ap.knife_x(1.0, 2.0, 2.0)


def test_the_knife_opens_the_cells_it_has_passed_left_to_right_and_only_those():
    xs = [c[0] for c in ap.cell_centres()]
    seen = [ap.opened(ap.knife_x(t, 0.0, 1.0), passed=False) for t in np.arange(-0.4, 1.4, 0.02)]
    for before, after in zip(seen, seen[1:], strict=False):
        assert all(a or not b for b, a in zip(before, after, strict=True))  # once open, open
    for state in seen:
        open_x = [x for x, o in zip(xs, state, strict=True) if o]
        shut_x = [x for x, o in zip(xs, state, strict=True) if not o]
        assert not open_x or not shut_x or max(open_x) < min(shut_x)
    assert not any(seen[0]) and all(seen[-1])
    assert ap.opened(None, passed=True) == (True,) * ap.CELLS and ap.opened(None, passed=False) == (False,) * ap.CELLS


def test_a_whole_cell_keeps_its_enzyme_inside_and_an_open_one_spills_it_with_the_polyphenols():
    whole = _slab()
    assert "polyphenol" not in whole and "enzyme" in whole
    assert whole["enzyme"][:, 1].min() > whole[ap.shade(0)][:, 1].min()  # under its cell's dome
    cut = _slab(cells=(0,) * ap.CELLS)
    assert "polyphenol" in cut
    assert cut["enzyme"][:, 1].min() < cut[ap.shade(0)][:, 1].min()  # out on the cut, over the sap


def test_an_open_cell_grows_brown_pigment_as_it_browns_and_uses_its_polyphenols_up():
    fresh, brown = _slab(cells=(0,) * ap.CELLS), _slab(cells=(ap.LEVELS,) * ap.CELLS)
    assert "melanin" not in fresh and "melanin" in brown
    assert len(brown["polyphenol"]) < len(fresh["polyphenol"])
    assert ap.shade(ap.LEVELS) in brown and ap.shade(ap.LEVELS) not in fresh


def test_the_cut_cells_spill_and_jiggle_as_the_stir_turns():
    a, b = _slab(cells=(1,) * ap.CELLS, stir=0.0), _slab(cells=(1,) * ap.CELLS, stir=0.25)
    assert not np.allclose(a["enzyme"], b["enzyme"])


def test_the_knife_is_drawn_only_while_in_shot_and_lies_where_its_edge_is():
    assert "blade" not in _slab()
    left, right = _slab(knife=-20.0)["bladeedge"], _slab(knife=20.0)["bladeedge"]
    assert right[:, 0].max() - left[:, 0].max() == pytest.approx(40.0)
    assert {"blade", "bladeedge", "handle", "rivet"} <= set(_slab(knife=0.0))


def test_drifting_oxygen_stays_over_the_cut_and_a_landing_one_reaches_its_cells_enzyme_by_its_second():
    _, cut, _ = ap.cell_centres()[0]
    for k in range(12):
        for t in np.arange(0.0, 6.0, 0.25):
            wisp = ap.oxygen_at(float(t), k)
            assert wisp.at[1] < cut - 4.0 - 8.0
    cell = 7
    lx, ly, lz = ap.cell_centres()[cell]
    early, landed, after = (ap.oxygen_at(t, 3, lands=(5.0, cell)) for t in (3.0, 5.0, 6.0))
    assert early == ap.oxygen_at(3.0, 3)
    assert landed.at == after.at
    assert math.dist(landed.at, (lx, ly, lz)) < ap.SLAB[2] / ap.COLS
    path = [ap.oxygen_at(t, 3, lands=(5.0, cell)).at[1] for t in np.arange(4.1, 5.01, 0.05)]
    assert path[-1] > path[0]  # it comes down


def test_oxygen_landing_on_a_cell_the_cut_does_not_have_is_refused():
    with pytest.raises(ap.AppleError, match="cells"):
        ap.oxygen_at(1.0, 0, lands=(2.0, ap.CELLS))


@pytest.mark.parametrize(
    ("pose", "match"),
    [
        ({"cells": (ap.INTACT,) * (ap.CELLS - 1)}, "cells"),
        ({"cells": (ap.LEVELS + 1,) * ap.CELLS}, "shade"),
        ({"cells": (True,) * ap.CELLS}, "shade"),
        ({"knife": 500.0}, "knife"),
        ({"knife": math.nan}, "knife"),
        ({"stir": math.inf}, "stir"),
        ({"oxygen": ((0.0, 0.0, 0.0),)}, "oxygen"),
    ],
)
def test_a_slab_pose_out_of_bounds_is_refused(pose, match):
    with pytest.raises(ap.AppleError, match=match):
        ap.SlabPose(**{"knife": None, "cells": (ap.INTACT,) * ap.CELLS, **pose})


@pytest.mark.parametrize("at", [(0.0, 0.0), (0.0, math.nan, 0.0)])
def test_an_oxygen_molecule_nowhere_is_refused(at):
    with pytest.raises(ap.AppleError, match="somewhere"):
        ap.Wisp(at)


def test_the_cells_sit_in_rows_on_the_cut_inside_the_block():
    centres = np.array(ap.cell_centres())
    x, z, w, _, d = ap.SLAB
    assert len(centres) == ap.CELLS
    assert np.ptp(centres[:, 1]) == 0
    assert (abs(centres[:, 0] - x) < w / 2).all() and (abs(centres[:, 2] - z) < d / 2).all()


@pytest.mark.parametrize(
    ("pose", "match"),
    [
        ({"bare": (0, 1, 2)}, "rim in"),
        ({"kept": (0, 0)}, "rings"),
        ({"bare": (6, 0, 0)}, "shade"),
        ({"squeeze": 1.5}, "squeeze"),
        ({"drops": (0.5,)}, "lemon"),
        ({"squeeze": 0.5, "drops": (1.2,)}, "drop"),
        ({"wet": -0.1}, "wet"),
        ({"sand": 2.0}, "sand"),
    ],
)
def test_a_halves_pose_out_of_bounds_is_refused(pose, match):
    with pytest.raises(ap.AppleError, match=match):
        ap.HalvesPose(**{"bare": (0, 0, 0), "kept": (0, 0, 0), **pose})


def test_the_bare_face_browns_its_rim_first():
    rim_first = _halves(bare=(3, 1, 0), kept=(2, 2, 2))
    assert {ap.shade(3), ap.shade(1), ap.shade(0)} <= set(rim_first)
    bx, _, bz = ap.bare_centre()

    def near(v):
        return v[np.hypot(v[:, 0] - bx, v[:, 2] - bz) < ap.HALF_R * 1.2]

    outer, inner = near(rim_first[ap.shade(3)]), near(rim_first[ap.shade(0)])
    assert np.hypot(outer[:, 0] - bx, outer[:, 2] - bz).max() > np.hypot(inner[:, 0] - bx, inner[:, 2] - bz).max()


def test_the_two_halves_and_the_hourglass_stand_apart_on_the_board():
    bare, kept = ap.bare_centre(), ap.kept_centre()
    assert math.dist(bare, kept) > 2 * ap.HALF_R
    board = _meshes(ap.halves)["cuttingboard"]
    for x, _, z in (bare, kept):
        assert board[:, 0].min() < x - ap.HALF_R and x + ap.HALF_R < board[:, 0].max()
        assert board[:, 2].min() < z - ap.HALF_R and z + ap.HALF_R < board[:, 2].max()


def test_a_drop_leaves_the_lemon_and_lands_on_the_kept_face():
    lx, ly, lz = ap.lemon_centre(1.0)
    start, end = ap.drop_at(0.0), ap.drop_at(1.0)
    assert math.dist(start, (lx, ly, lz)) < 3.0
    kx, ky, kz = ap.kept_centre()
    assert math.hypot(end[0] - kx, end[2] - kz) < ap.HALF_R and abs(end[1] - ky) < 2.0
    ys = [ap.drop_at(f)[1] for f in np.linspace(0, 1, 11)]
    assert ys == sorted(ys)  # falling, y down


def test_his_hand_holds_the_lemon_over_the_kept_half_and_puts_it_down_after():
    held, down = _halves(squeeze=0.0), _halves()
    assert held["lemon"][:, 1].min() < down["lemon"][:, 1].min()
    assert len(_meshes(lambda m: ap.halves_parts(m, HALVES_POSES[1]))) > len(down)
    assert down["lemon"][:, 1].max() <= ap.TOP - 4.0 + 0.5  # on the board, not in it


def test_squeezing_presses_the_lemon_down_toward_the_face():
    assert ap.lemon_centre(1.0)[1] > ap.lemon_centre(0.0)[1]


def test_the_juice_spreads_over_the_kept_face_as_it_lands():
    assert "juice" not in _halves()
    little, much = _halves(wet=0.2)["juice"], _halves(wet=1.0)["juice"]
    assert np.ptp(much[:, 0]) > np.ptp(little[:, 0])


def test_the_hourglass_runs_its_sand_from_the_top_to_the_heap_below():
    full, empty = _halves(sand=1.0)["sand"], _halves(sand=0.0)["sand"]
    assert full[:, 1].min() < empty[:, 1].min()  # sand stands high in the top bulb only while it is there
    assert np.ptp(empty[:, 1]) > 0
