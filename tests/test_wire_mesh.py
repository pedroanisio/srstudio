"""The wire car and the wire jet as real meshes (srstudio.wire_mesh): welded, smooth where the surface is, outward."""

from __future__ import annotations

import math

import numpy as np
import pytest
from scipy.sparse import coo_matrix
from scipy.sparse.csgraph import connected_components

from srstudio import wire_mesh
from srstudio.wire_mesh import CREASE, WireMeshError, car_model, jet_model, smooth_mesh, to_scene


def cube(size: float = 1.0):
    """Six quads (metres, y up) of a cube about the origin."""
    h = size / 2
    corners = [(-h, -h, -h), (h, -h, -h), (h, h, -h), (-h, h, -h), (-h, -h, h), (h, -h, h), (h, h, h), (-h, h, h)]
    faces = [(0, 1, 2, 3), (4, 5, 6, 7), (0, 1, 5, 4), (3, 2, 6, 7), (0, 3, 7, 4), (1, 2, 6, 5)]
    return [[corners[i] for i in face] for face in faces]


def away(centre):
    return np.asarray(centre, float)


def facing_out(mesh) -> np.ndarray:
    """For each triangle, the dot of its wound normal with the direction from the origin to its middle."""
    v, t = mesh.vertices, mesh.triangles
    normal = np.cross(v[t[:, 1]] - v[t[:, 0]], v[t[:, 2]] - v[t[:, 0]])
    return np.einsum("ij,ij->i", normal, v[t].mean(axis=1))


def test_a_scene_point_is_in_units_with_y_down_and_z_away():
    assert to_scene((1.0, 2.0, 3.0)) == (100.0, -200.0, -300.0)


def test_a_cube_keeps_its_edges_and_faces_out_whichever_way_its_quads_were_wound():
    quads = cube()
    wound = [quad[::-1] if i % 2 else quad for i, quad in enumerate(quads)]  # half of them wound the other way
    mesh = smooth_mesh(wound, "paint", away)
    assert (facing_out(mesh) > 0).all()
    assert np.allclose(np.linalg.norm(mesh.normals, axis=1), 1.0)
    # faces meet at 90 degrees, beyond the crease: every corner keeps the normal of its own face
    assert {tuple(np.abs(n).round(3)) for n in mesh.normals} == {(1.0, 0.0, 0.0), (0.0, 1.0, 0.0), (0.0, 0.0, 1.0)}


def test_faces_inside_the_crease_share_one_smooth_normal_at_their_edge():
    tilt = math.radians(CREASE / 2)
    a = [(0, 0, 0), (1, 0, 0), (1, 1, 0), (0, 1, 0)]
    b = [(1, 0, 0), (2, 0.0, math.sin(tilt)), (2, 1, math.sin(tilt)), (1, 1, 0)]
    mesh = smooth_mesh([a, b], "paint", lambda c: np.array([0.0, 0.0, -1.0]))
    own = np.array([0.0, 0.0, -1.0])  # the near face's own normal: the lens-facing side
    seam = np.isclose(mesh.vertices[:, 0], 100.0)  # the shared edge's corners, in scene units
    assert seam.sum() == 4  # two corners, once from each face
    for y in {round(float(v), 3) for v in mesh.vertices[seam][:, 1]}:
        here = mesh.normals[seam & np.isclose(mesh.vertices[:, 1], y)]
        assert np.allclose(here[0], here[1], atol=1e-6)  # welded: both faces agree at the edge
        assert not np.allclose(here[0], own, atol=1e-3)  # and the edge is bent between them, not either face's own
    far_edge = mesh.normals[np.isclose(mesh.vertices[:, 0], 0.0)]
    assert np.allclose(far_edge, own, atol=1e-6)  # the open edge keeps its face's normal


def test_the_same_quads_make_the_same_mesh():
    one, two = smooth_mesh(cube(), "paint", away), smooth_mesh(cube(), "paint", away)
    assert one.sha256 == two.sha256


@pytest.mark.parametrize("crease", [0.0, 90.0, -3.0, 120.0])
def test_a_crease_is_an_angle_between_zero_and_ninety(crease):
    with pytest.raises(WireMeshError, match="crease"):
        smooth_mesh(cube(), "paint", away, crease=crease)


def test_a_mesh_needs_a_material_and_surfaces():
    with pytest.raises(WireMeshError, match="material"):
        smooth_mesh(cube(), "", away)
    with pytest.raises(WireMeshError, match="no quads"):
        smooth_mesh([], "paint", away)


def test_a_corner_that_is_not_a_number_is_refused():
    bad = [[(0, 0, 0), (1, 0, 0), (1, 1, 0), (math.nan, 1, 0)]]
    with pytest.raises(WireMeshError, match="finite"):
        smooth_mesh(bad, "paint", away)


def test_quads_with_no_area_are_refused():
    flat = [[(0, 0, 0), (1, 0, 0), (2, 0, 0), (3, 0, 0)]]
    with pytest.raises(WireMeshError, match="no area"):
        smooth_mesh(flat, "paint", away)


@pytest.fixture(scope="module")
def car():
    return car_model("monday")


def test_a_car_has_a_body_and_a_tyre_and_a_rim_for_each_of_its_wheels(car):
    assert {"Wheel front L", "Wheel front R", "Wheel rear L", "Wheel rear R"} <= set(car.wheels)
    for wheel in car.wheels:
        names = [p.name for p in car.parts if p.name.startswith(wheel)]
        assert f"{wheel}-tyre" in names and any("-rim" in n for n in names)
    assert any(p.name.startswith("body-") for p in car.parts)


def test_a_wheel_is_made_about_its_hub_and_sits_at_it(car):
    for wheel, (hub, radius, side) in car.wheels.items():
        for part in (p for p in car.parts if p.name.startswith(wheel)):
            assert part.at == hub
            reach = np.linalg.norm(part.mesh.vertices[:, :2], axis=1).max()
            assert reach <= radius * 1.02  # about its own origin: nothing is further from the axle than the tyre
        assert side in (-1.0, 1.0)


def test_the_rim_stands_at_the_tyre_face_not_inside_the_tyre(car):
    wheel = "Wheel front L"
    tyre = next(p for p in car.parts if p.name == f"{wheel}-tyre").mesh.vertices
    spokes = [p for p in car.parts if p.name.startswith(f"{wheel}-rim")]
    outer = max(abs(p.mesh.vertices[:, 2]).max() for p in spokes)
    assert outer > 0.8 * abs(tyre[:, 2]).max()  # the rim reaches the tyre's outer face, where the camera sees it


def test_a_car_names_where_a_driver_sits(car):
    assert {"driver-head", "steering-wheel"} <= set(car.anchors)
    assert car.length > car.width > 0


def test_every_part_of_a_car_has_unit_normals_and_valid_triangles(car):
    for part in car.parts:
        mesh = part.mesh
        assert np.allclose(np.linalg.norm(mesh.normals, axis=1), 1.0, atol=1e-6)
        assert mesh.triangles.max() < len(mesh.vertices)
        assert np.isfinite(mesh.vertices).all()


@pytest.fixture(scope="module")
def jet():
    return jet_model("tuesday", model="kestrel")


def test_a_jet_is_made_of_its_parts_without_its_glass(jet):
    names = [p.name for p in jet.parts]
    assert "Fuselage" in names and "Canopy glass" not in names
    assert jet.length > 0 and jet.wingspan > 0


def test_a_jet_names_where_its_pilot_sits(jet):
    assert "pilot-head" in jet.anchors


def test_a_jet_part_is_made_of_one_of_the_jet_materials(jet):
    assert {p.material for p in jet.parts} <= set(wire_mesh.JET_MATERIAL.values())


def test_the_jets_surfaces_face_out_of_their_own_part(jet):
    fuselage = next(p for p in jet.parts if p.name == "Fuselage").mesh
    centre = fuselage.vertices.mean(axis=0)
    shifted = type(fuselage)(
        fuselage.material, fuselage.vertices - centre, fuselage.normals, fuselage.triangles, fuselage.uvs
    )
    assert (facing_out(shifted) > 0).mean() > 0.9


def welded(mesh) -> tuple[np.ndarray, np.ndarray]:
    """Each vertex's welded id, and the triangles in those ids, less any that lost a corner to the weld."""
    _, ids = np.unique(np.round(mesh.vertices, 3), axis=0, return_inverse=True)
    ids = ids.ravel()
    tris = ids[mesh.triangles]
    keep = (tris[:, 0] != tris[:, 1]) & (tris[:, 1] != tris[:, 2]) & (tris[:, 2] != tris[:, 0])
    return ids, tris[keep]


def against_their_neighbours(mesh) -> float:
    """The share of directed edges used twice: two faces sharing an edge wound the same way, one of them inside out."""
    _, tris = welded(mesh)
    edges = np.concatenate([tris[:, [0, 1]], tris[:, [1, 2]], tris[:, [2, 0]]])
    _, counts = np.unique(edges, axis=0, return_counts=True)
    return float((counts > 1).sum() / len(counts))


def inside_out(mesh) -> list[float]:
    """The signed volume of each closed piece that came out negative: a solid wound with its faces inward."""
    ids, tris = welded(mesh)
    size = ids.max() + 1
    graph = coo_matrix(
        (np.ones(len(tris) * 2), (np.r_[tris[:, 0], tris[:, 1]], np.r_[tris[:, 1], tris[:, 2]])), (size, size)
    )
    _, piece = connected_components(graph, directed=False)
    where = np.zeros((size, 3))
    where[ids] = mesh.vertices
    bad = []
    for n in np.unique(piece[tris[:, 0]]):
        own = tris[piece[tris[:, 0]] == n]
        a, b, c = where[own[:, 0]], where[own[:, 1]], where[own[:, 2]]
        middle = where[np.unique(own)].mean(axis=0)
        volume = np.einsum("ij,ij->i", np.cross(a - middle, b - middle), c - middle).sum() / 6.0
        if volume < 0:
            bad.append(float(volume))
    return bad


def test_a_cube_is_a_solid_wound_outward():
    mesh = smooth_mesh(cube(), "paint", away)
    assert against_their_neighbours(mesh) == 0.0
    assert inside_out(mesh) == []


def test_a_cube_wound_inward_reads_as_inside_out():
    assert inside_out(smooth_mesh(cube(), "paint", lambda c: -np.asarray(c, float)))


def test_each_seat_of_a_car_faces_away_from_itself_not_from_the_car():
    seats = next(p for p in car_model("monday").parts if p.material == wire_mesh.KIND_MATERIAL["leather"]).mesh
    assert against_their_neighbours(seats) < 0.002
    assert inside_out(seats) == []


def test_each_seat_of_a_jet_faces_away_from_itself():
    seats = [p.mesh for p in jet_model("monday").parts if p.material == wire_mesh.JET_MATERIAL["leather"]]
    assert seats
    for mesh in seats:
        assert against_their_neighbours(mesh) < 0.002
        assert inside_out(mesh) == []


def test_an_open_sheet_still_asks_the_rule_it_was_given():
    sheet = [[(0, 0, 0), (1, 0, 0), (1, 1, 0), (0, 1, 0)]]
    out = wire_mesh._solids(sheet, lambda c: np.array([0.0, 0.0, 7.0]))
    assert out(np.array(to_scene((0.5, 0.5, 0)))).tolist() == [0.0, 0.0, 7.0]


def test_a_cube_with_one_face_wound_backward_is_turned_round():
    faces = cube()
    faces[2] = faces[2][::-1]
    mesh = smooth_mesh(faces, "paint", wire_mesh._solids(faces, lambda c: -np.asarray(c, float)))
    assert against_their_neighbours(mesh) == 0.0
    assert inside_out(mesh) == []
