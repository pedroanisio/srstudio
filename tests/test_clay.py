"""Clay: procedural geometry baked to meshes, the same bytes on every build, with faces that point outward."""

from __future__ import annotations

import math

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


def test_a_revolved_profile_is_round_and_faces_out():
    model = clay.Model()
    model.revolve("hub", [(10.0, -5.0), (10.0, 5.0)])
    mesh = model.meshes()[0]
    assert np.hypot(*mesh.vertices[:, :2].T) == pytest.approx(10.0)
    assert (mesh.normals[:, :2] * mesh.vertices[:, :2]).sum(1).min() > 0


def test_a_loft_caps_its_ends_and_names_each_panel():
    model = clay.Model()

    def ring(x):
        z, y = clay.superellipse(32, 2.0)
        return z * 10, y * 10

    model.loft(np.linspace(0, 40, 5), ring, lambda centre, normal, i, j: "nose" if centre[0] > 20 else "tail")
    parts = {mesh.material: mesh for mesh in model.meshes()}
    assert set(parts) == {"nose", "tail"}
    assert parts["nose"].vertices[:, 0].max() == pytest.approx(40.0)
    assert parts["tail"].vertices[parts["tail"].triangles].mean(1)[:, 0].max() <= 20.0


def test_a_panel_left_out_of_a_loft_stays_open():
    model = clay.Model()

    def ring(x):
        z, y = clay.superellipse(16, 2.0)
        return z, y

    model.loft(np.linspace(0, 1, 3), ring, lambda centre, normal, i, j: None if centre[1] > 0 else "top")
    mesh = model.meshes()[0]
    assert mesh.vertices[mesh.triangles].mean(1)[:, 1].max() < 0.1


def test_a_strut_follows_its_path_with_its_face_out():
    model = clay.Model()
    model.strut("bar", [(0, 0, 0), (50, 0, 0), (100, 0, 0)], 10.0, 4.0, (0, -1, 0))
    mesh = model.meshes()[0]
    assert mesh.vertices[:, 0].min() == pytest.approx(0.0, abs=1e-6)
    assert mesh.vertices[:, 0].max() == pytest.approx(100.0, abs=1e-6)
    assert np.ptp(mesh.vertices[:, 2]) == pytest.approx(10.0, abs=0.01)
    assert np.ptp(mesh.vertices[:, 1]) == pytest.approx(4.0, abs=0.01)


@pytest.mark.parametrize("bad", [[(1.0, 2.0)], [(-1.0, 0.0), (1.0, 2.0)]])
def test_a_profile_that_cannot_revolve_is_refused(bad):
    with pytest.raises(clay.ClayError):
        clay.Model().revolve("hub", bad)


def test_a_strut_needs_a_path_and_a_face():
    with pytest.raises(clay.ClayError):
        clay.Model().strut("bar", [(0, 0, 0)], 1.0, 1.0, (0, 0, 1))
    with pytest.raises(clay.ClayError):
        clay.Model().strut("bar", [(0, 0, 0), (1, 0, 0)], 1.0, 1.0, (0, 0, 0))


def test_a_strut_turns_its_face_toward_out():
    model = clay.Model()
    model.strut("bar", [(0, 0, 0), (50, 0, 0), (100, 0, 0)], 10.0, 4.0, (0, -1, 0))
    mesh = model.meshes()[0]
    middle = np.abs(mesh.vertices[:, 0] - 50) < 1
    top, under = mesh.vertices[:, 1] < -1.9, mesh.vertices[:, 1] > 1.9
    assert mesh.normals[middle & top, 1].max() < -0.9
    assert mesh.normals[middle & under, 1].min() > 0.9


@pytest.mark.parametrize(
    "bad",
    [
        dict(path=[(0, 0, 0), (0, 0, 0), (1, 0, 0)], out=(0, 0, 1)),  # stands still at its end
        dict(path=[(0, 0, 0), (0, 0, 1)], out=(0, 0, 1)),  # runs along its own face
        dict(path=[(0, 0, 0), (1, 0, 0)], out=(0, 0, 1), width=[1.0, 2.0, 3.0]),
        dict(path=[(0, 0, 0), (1, 0, 0)], out=(0, 0, 1), n=0.0),
    ],
)
def test_a_strut_that_has_no_shape_is_refused(bad):
    with pytest.raises(clay.ClayError):
        clay.Model().strut("bar", bad["path"], bad.get("width", 1.0), 1.0, bad["out"], bad.get("n", 4.0))


@pytest.mark.parametrize(
    ("profile", "sides"),
    [([(1.0, 0.0, 9.0), (1.0, 1.0, 9.0)], 64), ([(1.0, 0.0), (1.0, 1.0)], 0), ([(math.nan, 0.0), (1.0, 1.0)], 64)],
)
def test_a_revolved_profile_of_the_wrong_shape_is_refused(profile, sides):
    with pytest.raises(clay.ClayError):
        clay.Model().revolve("hub", profile, sides)


def test_a_loft_of_no_rings_is_refused():
    with pytest.raises(clay.ClayError):
        clay.Model().loft([], lambda x: None, lambda *a: "body")


@pytest.mark.parametrize("args", [(2, 2.0), (28, 0.0), (28, 2.0, 0.0), (28, -1.0)])
def test_a_superellipse_with_no_shape_is_refused(args):
    with pytest.raises(clay.ClayError):
        clay.superellipse(*args)


def test_a_surface_that_is_not_a_number_is_refused():
    with pytest.raises(clay.ClayError, match="not a number"):
        clay.Model().surface("bar", [(math.nan, 0, 0)], [(0, 0, 1)], [])
