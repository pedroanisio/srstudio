"""Clay: procedural geometry baked to meshes, the same bytes on every build, with faces that point outward."""

from __future__ import annotations

import numpy as np
import pytest

from srstudio import clay
from srstudio.clay import ClayError, Model


def built() -> Model:
    m = Model()
    m.ell("skin", (0, -10, 0), (5, 6, 7), rotation=20)
    m.box("oak", (0, 0, 0), (10, 4, 6))
    m.box("oak", (20, 0, 0), (10, 4, 6), radius=1.0)
    m.rod("steel", (0, 0, 0), (0, -9, 3), 1.0)
    m.tube("ink", ((0, 0, 0), (5, -5, 0), (9, 0, 2)), 1.0)
    m.sweep("rust", ((0, 0, 0), (0, -8, 0), (0, -16, 2)), (3, 2), 0.9)
    m.cylinder("mug", (0, 0, 0), 5, 8)
    m.faceplate("label", (0, 0, -2), 4, 3)
    m.curved_label("label", 5.0, -4, 4)
    return m


def test_a_model_bakes_to_the_same_bytes_on_every_build():
    one, two = built().meshes(), built().meshes()
    assert [clay.obj_bytes(m) for m in one] == [clay.obj_bytes(m) for m in two]
    assert [m.material for m in one] == sorted(m.material for m in one)


def test_a_mesh_is_written_in_the_units_and_axes_the_engine_reads():
    m = Model()
    m.surface("skin", [(100, -200, 300), (200, -200, 300), (100, -100, 300)], [(0, 0, -1)] * 3, [(0, 1, 2)])
    text = clay.obj_bytes(m.meshes()[0]).decode()
    assert text.splitlines()[0] == "v 1.0000000 2.0000000 -3.0000000"
    assert "vn 0.0000000 0.0000000 1.0000000" in text and "f 1//1 2//2 3//3" in text


def test_an_ellipsoid_reaches_its_radii_and_points_outward():
    mesh = next(m for m in _alone(lambda m: m.ell("skin", (1, 2, 3), (5, 6, 7))))
    span = mesh.vertices.max(axis=0) - mesh.vertices.min(axis=0)
    assert span == pytest.approx((10, 12, 14), abs=0.05)
    assert (np.sum(mesh.normals * (mesh.vertices - (1, 2, 3)), axis=1) > 0).all()


def test_a_positive_rotation_turns_as_the_engine_turns_a_primitive():
    """y is down, so a positive rotation takes +x towards +y."""
    mesh = _alone(lambda m: m.ell("skin", (0, 0, 0), (10, 1, 1), rotation=90))[0]
    span = mesh.vertices.max(axis=0) - mesh.vertices.min(axis=0)
    assert span[1] == pytest.approx(20, abs=0.05) and span[0] == pytest.approx(2, abs=0.05)


def test_the_placed_frame_moves_turns_and_scales_what_is_built_in_it():
    m = Model()
    with m.at(x=10, y=-5, z=2, yaw=90, scale=2):
        m.surface("skin", [(1, 0, 0), (0, 1, 0), (0, 0, 1)], [(1, 0, 0)] * 3, [(0, 1, 2)])
    verts = m.meshes()[0].vertices
    assert verts[0] == pytest.approx((10, -5, 0), abs=1e-6)  # +x turns to -z, as the pack's yaw did
    assert verts[1] == pytest.approx((10, -3, 2), abs=1e-6)
    assert verts[2] == pytest.approx((12, -5, 2), abs=1e-6)


def test_a_rod_runs_from_end_to_end():
    mesh = _alone(lambda m: m.rod("steel", (0, 0, 0), (0, -9, 0), 1.0))[0]
    assert mesh.vertices[:, 1].min() == pytest.approx(-9) and mesh.vertices[:, 1].max() == pytest.approx(0)


def test_a_cap_stops_at_its_cut_and_is_the_whole_shell_at_one():
    half = _alone(lambda m: m.lid("skin", (0, 0, 0), (10, 10, 10), 0.5))[0]
    assert half.vertices[:, 1].max() == pytest.approx(0, abs=1e-6)
    assert half.vertices[:, 1].min() == pytest.approx(-10, abs=0.05)
    whole = _alone(lambda m: m.lid("skin", (0, 0, 0), (10, 10, 10), 1.0))[0]
    assert whole.vertices[:, 1].max() == pytest.approx(10, abs=0.05)


@pytest.mark.parametrize("bad", [0.0, -0.1, 1.1, float("nan")])
def test_a_lid_must_cover_a_real_share_of_the_eye(bad):
    with pytest.raises(ClayError, match="share"):
        Model().lid("skin", (0, 0, 0), (1, 1, 1), bad)


@pytest.mark.parametrize(
    "build",
    [
        lambda m: m.ell("skin", (0, 0, 0), (0, 1, 1)),
        lambda m: m.box("oak", (0, 0, 0), (1, -1, 1)),
        lambda m: m.rod("steel", (1, 1, 1), (1, 1, 1), 1.0),
        lambda m: m.tube("ink", ((0, 0, 0),), 1.0),
        lambda m: m.surface("skin", [(0, 0, 0)], [(0, 0, 1)], [(0, 1, 2)]),
        lambda m: m.ell("", (0, 0, 0), (1, 1, 1)),
    ],
)
def test_impossible_geometry_is_refused(build):
    with pytest.raises(ClayError):
        build(Model())


def test_nothing_built_is_no_mesh():
    assert Model().meshes() == ()


def _alone(build) -> tuple[clay.Mesh, ...]:
    m = Model()
    build(m)
    return m.meshes()


def test_a_lower_lid_comes_up_from_below():
    upper, lower = clay.Model(), clay.Model()
    upper.lid("x", (0, 0, 0), (2, 2, 2), 0.25)
    lower.lid("x", (0, 0, 0), (2, 2, 2), 0.25, lower=True)
    assert upper.meshes()[0].vertices[:, 1].max() < 0
    assert lower.meshes()[0].vertices[:, 1].min() > 0


def test_planar_lays_coordinates_along_the_axis_a_vertex_faces():
    m = clay.Model()
    m.box("x", (0, 0, 0), (10, 10, 10))
    laid = clay.planar(m.meshes()[0], 5.0)
    assert laid.uvs is not None and laid.uvs.shape == (len(laid.vertices), 2)
    assert np.abs(laid.uvs).max() == pytest.approx(1.0)
    with pytest.raises(clay.ClayError, match="tile"):
        clay.planar(m.meshes()[0], 0.0)


def test_a_surface_field_is_the_same_on_every_build_and_keeps_to_a_range():
    a, b = clay.thumbed(64, 7), clay.thumbed(64, 7)
    assert (a == b).all() and np.abs(a).max() == pytest.approx(1.0)
    assert not (a == clay.thumbed(64, 8)).all()
    tile = clay.normal_tile(clay.knit(64, 6), 1.0)
    assert tile.shape == (64, 64, 4) and tile.dtype == np.uint8 and (tile[..., 3] == 255).all()
