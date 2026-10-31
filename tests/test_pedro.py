"""Pedro, the operator's likeness: one sculpt, every state a continuous change of it, nothing swapped in as a static."""

from __future__ import annotations

import numpy as np
import pytest

from srstudio import clay, parts, pedro, pedro_sculpt
from srstudio.pedro import GAZES, LIDS, MOODS, MOUTHS, NODS, TURNS, Face, PedroError


def centres(mesh: clay.Mesh) -> np.ndarray:
    return mesh.vertices[mesh.triangles].mean(axis=1)


def named(meshes: tuple[clay.Mesh, ...], material: str) -> clay.Mesh:
    return next(mesh for mesh in meshes if mesh.material == material)


def test_the_sculpts_three_expressions_are_his_three_moods():
    assert tuple(MOODS) == ("neutral", "smile", "raised-brow")


@pytest.mark.parametrize(
    ("field", "value"),
    (
        ("mood", "furious"),
        ("gaze", "up"),
        ("lid", "droopy"),
        ("mouth", "scream"),
        ("turn", 3.0),
        ("nod", 1.0),
        ("toward", "furious"),
        ("share", 0.4),
    ),
)
def test_a_face_outside_the_vocabulary_is_refused(field, value):
    with pytest.raises(PedroError, match=field):
        Face(**{field: value})


def test_a_share_with_no_mood_to_move_toward_is_refused():
    with pytest.raises(PedroError, match="toward"):
        Face(share=0.5)


def test_a_blend_runs_through_every_number_of_the_expression():
    a, b = pedro.mood("neutral"), pedro.mood("smile")
    half = pedro.expression(Face(mood="neutral", toward="smile", share=0.5))
    assert half.top_left == pytest.approx((a.top_left + b.top_left) / 2)
    assert half.curve == pytest.approx((a.curve + b.curve) / 2)
    assert pedro.expression(Face(mood="smile")) == b


def test_the_raised_brow_is_his_own_left_only():
    plain, raised = pedro.mood("neutral"), pedro.mood("raised-brow")
    assert raised.brow_left < plain.brow_left
    assert raised.brow_right == plain.brow_right
    assert raised.top_left > plain.top_left


def test_the_sculpts_outline_is_kept_in_the_rebuilt_interpolant():
    assert pedro_sculpt.width(np.array([25.0]))[0] == pytest.approx(18.7)
    assert pedro_sculpt.width(np.array([35.0]))[0] == pytest.approx(17.2)
    points = pedro_sculpt.width(np.linspace(0.0, 50.0, 200))
    assert points.max() <= 18.7 + 1e-9  # a monotone interpolant does not overshoot the sculpt


def test_the_skin_is_the_same_bytes_on_every_build():
    first = pedro.skull()
    pedro_sculpt.grid.cache_clear()
    pedro.skull.cache_clear()
    assert [mesh.sha256 for mesh in first] == [mesh.sha256 for mesh in pedro.skull()]


@pytest.mark.parametrize("name", MOODS)
def test_rest_is_a_closed_mouth_on_whole_skin(name):
    whole = len(named(pedro.skull(), "skin").triangles)
    assert len(named(pedro.mouth(name, "rest"), "skin").triangles) == whole


@pytest.mark.parametrize("shape", ("open", "round", "wide", "teeth"))
def test_a_speaking_mouth_cuts_the_skin_along_the_lips_only(shape):
    whole = named(pedro.skull(), "skin")
    cut = named(pedro.mouth("neutral", shape), "skin")
    gone = len(whole.triangles) - len(cut.triangles)
    assert 0 < gone < 0.02 * len(whole.triangles)


@pytest.mark.parametrize("shape", ("open", "round", "wide", "teeth", "lip"))
def test_a_speaking_mouth_has_an_inside(shape):
    made = {mesh.material for mesh in pedro.mouth("neutral", shape)}
    assert {"throat", "tooth"} <= made


def test_rest_keeps_nothing_of_the_inside():
    made = {mesh.material for mesh in pedro.mouth("neutral", "rest")}
    assert not made & {"throat", "tooth", "tongue"}


def lowest(meshes: tuple[clay.Mesh, ...], material: str) -> float:
    return float(named(meshes, material).vertices[:, 1].max())


def test_the_jaw_carries_the_goatee_with_it():
    rest, wide_open = pedro.mouth("neutral", "rest"), pedro.mouth("neutral", "open")
    for material in ("skin", "goatee", "hair-dark"):
        assert lowest(wide_open, material) > lowest(rest, material) + 1.0


def test_the_goatee_stays_on_the_skin_when_the_jaw_drops():
    """Every goatee point stays in front of the skin it covers: the two move by the same field."""
    meshes = pedro.mouth("neutral", "open")
    skin, goatee = named(meshes, "skin"), named(meshes, "goatee")
    pick = goatee.vertices[::97]
    tree = skin.vertices[::1]
    for point in pick:
        near = tree[np.abs(tree[:, 0] - point[0]) + np.abs(tree[:, 1] - point[1]) < 0.6]
        assert len(near), f"no skin under {point}"
        assert point[2] <= near[:, 2].max() + 0.2


def test_a_smile_lifts_the_corners_and_not_the_middle():
    rest, smile = pedro.mouth("neutral", "rest"), pedro.mouth("smile", "rest")
    a, b = named(rest, "lip").vertices, named(smile, "lip").vertices
    corner = np.abs(a[:, 0]).argmax()
    middle = np.abs(a[:, 0]).argmin()
    assert b[corner, 1] < a[corner, 1] - 0.3
    assert b[middle, 1] == pytest.approx(a[middle, 1], abs=0.05)


def test_a_round_mouth_narrows_and_a_wide_one_widens():
    rest = np.ptp(named(pedro.mouth("neutral", "rest"), "lip").vertices[:, 0])
    assert np.ptp(named(pedro.mouth("neutral", "round"), "lip").vertices[:, 0]) < 0.85 * rest
    assert np.ptp(named(pedro.mouth("neutral", "wide"), "lip").vertices[:, 0]) > 1.05 * rest


def test_a_blink_is_a_lid_that_comes_down_over_a_whole_eye():
    assert "lid" not in {mesh.material for mesh in pedro.eyes(Face())}
    half = named(pedro.eyes(Face(lid="half")), "lid")
    shut = named(pedro.eyes(Face(lid="shut")), "lid")
    assert shut.vertices[:, 1].max() > half.vertices[:, 1].max()


def test_a_glance_moves_the_iris_and_nothing_else():
    ahead = pedro.eyes(Face())
    right = pedro.eyes(Face(gaze="right"))
    assert named(right, "iris").vertices[:, 0].mean() > named(ahead, "iris").vertices[:, 0].mean() + 0.5
    assert named(right, "brow").sha256 == named(ahead, "brow").sha256


@pytest.mark.parametrize("gaze", GAZES)
@pytest.mark.parametrize("lid", LIDS)
def test_every_eye_is_geometry(gaze, lid):
    assert all(len(mesh.triangles) for mesh in pedro.eyes(Face(gaze=gaze, lid=lid)))


@pytest.mark.parametrize("name", MOODS)
@pytest.mark.parametrize("shape", MOUTHS)
def test_every_mouth_is_geometry(name, shape):
    assert all(len(mesh.triangles) for mesh in pedro.mouth(name, shape))


def test_every_pose_is_a_plate_step():
    assert 0.0 in TURNS and 0.0 in NODS
    assert TURNS == tuple(sorted(TURNS)) and NODS == tuple(sorted(NODS))


def test_the_head_is_built_about_the_neck_so_a_pose_is_two_rotations():
    chin = named(pedro.skull(), "skin").vertices
    assert chin[:, 1].max() > 0.0 > chin[:, 1].min()


def test_the_goatee_picture_is_made_in_code_and_is_stable():
    first = pedro.goatee_picture()
    pedro.goatee_picture.cache_clear()
    assert pedro.goatee_picture().sha256 == first.sha256


def test_the_library_carries_no_photograph_and_no_pack():
    import importlib.resources

    source = importlib.resources.files("srstudio")
    for name in ("pedro.py", "pedro_sculpt.py", "pedro_wardrobe.py", "pedro_host.py"):
        text = source.joinpath(name).read_text()
        assert "portrait" not in text.lower()
        assert "photo-character" not in text


def test_his_part_is_proposed_with_a_proof_and_no_approval():
    record = parts.load()["pedro"]
    latest = record.versions[-1]
    assert latest.number == 1
    assert latest.status == "proposed"
    assert latest.proof == "generated/character-proofs/pedro/index.html"
    assert latest.approval is None


def test_a_lid_coming_down_leaves_no_highlight_above_it():
    """The upper highlight stands proud of the eye: a half lid would wear it as a white dot."""

    def highest(lid: str) -> float:
        return float(named(pedro.eyes(Face(lid=lid)), "glint").vertices[:, 1].min())

    assert highest("half") > highest("open") + 0.5
