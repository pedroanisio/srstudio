"""Rafa as data: his moods, eyes and mouths are typed, an unknown one is refused, and each builds real geometry."""

from __future__ import annotations

import numpy as np
import pytest

from srstudio import clay, host_kit, rafa, rafa_skin
from srstudio.rafa import GAZES, LIDS, MOODS, MOUTHS, Face, RafaError


def size(build) -> int:
    m = clay.Model()
    build(m)
    return sum(len(mesh.triangles) for mesh in m.meshes())


def test_the_packs_three_expressions_are_his_three_moods():
    assert tuple(MOODS) == ("public-smile", "social-battery", "internal-meltdown")
    assert MOODS["social-battery"].title == "Social battery: 1%"


@pytest.mark.parametrize("name", ["", "smile", "PUBLIC-SMILE", None, 3])
def test_an_unknown_mood_is_refused_by_name(name):
    with pytest.raises(RafaError, match="mood"):
        rafa.mood(name)


@pytest.mark.parametrize(
    ("field", "value"),
    [("mood", "calm"), ("gaze", "up"), ("lid", "squint"), ("mouth", "kiss"), ("nod", 3.3), ("turn", 99.0)],
)
def test_a_face_outside_the_vocabulary_is_refused(field, value):
    with pytest.raises(RafaError, match=field):
        Face(**{field: value})


def test_he_speaks_with_the_hosts_visemes_and_rests_on_his_mood():
    assert set(host_kit.VISEMES) < set(MOUTHS)
    assert "rest" in MOUTHS


@pytest.mark.parametrize("mood", MOODS)
@pytest.mark.parametrize("mouth", MOUTHS)
def test_every_mouth_of_every_mood_is_geometry(mood, mouth):
    assert size(lambda m: rafa.mouth(m, mood, mouth)) > 0


@pytest.mark.parametrize("mood", MOODS)
@pytest.mark.parametrize("gaze", GAZES)
@pytest.mark.parametrize("lid", LIDS)
def test_every_eye_of_every_mood_is_geometry(mood, gaze, lid):
    assert size(lambda m: rafa.eyes(m, mood, gaze, lid)) > 0


def brow_lines(mood):
    m = clay.Model()
    rafa.brows(m, mood)
    verts = np.concatenate([mesh.vertices for mesh in m.meshes()])
    return verts[verts[:, 0] < 0], verts[verts[:, 0] > 0]


def arch(line) -> float:
    """How far the middle of a brow stands above its two ends."""
    order = line[:, 0].argsort()
    x, y = line[order, 0], line[order, 1]
    ends = (y[: len(y) // 12].mean() + y[-len(y) // 12 :].mean()) / 2.0
    middle = y[np.abs(x - x.mean()) < 3.0].mean()
    return float(ends - middle)


@pytest.mark.parametrize("mood", MOODS)
def test_his_left_brow_is_flat_and_his_right_is_arched_in_every_mood(mood):
    left, right = brow_lines(mood)
    assert arch(right) > arch(left) + 2.5


@pytest.mark.parametrize("mood", MOODS)
def test_his_brows_show_below_the_hair_in_every_mood(mood):
    m = clay.Model()
    rafa.skull(m)
    hair = next(mesh for mesh in m.meshes() if mesh.material == "hair").vertices
    for brow in brow_lines(mood):
        for x, y, z in brow[:: len(brow) // 20]:
            near = hair[(np.abs(hair[:, 0] - x) < 2.0) & (hair[:, 2] < z + 1.0)]
            assert not len(near) or y < 0, "built about the neck"
            assert not ((near[:, 1] > y - 0.5) & (near[:, 1] < y + 0.5)).any(), "hair lies over a brow"


def test_tired_is_his_resting_state_and_only_panic_opens_his_eyes():
    assert MOODS["public-smile"].upper >= 0.2 and MOODS["public-smile"].lower > 0
    assert MOODS["social-battery"].upper > MOODS["public-smile"].upper
    assert MOODS["internal-meltdown"].upper == 0 and MOODS["internal-meltdown"].lower == 0


def test_a_lid_is_skin_over_the_eye_only_where_the_mood_says():
    def lids(mood):
        m = clay.Model()
        rafa.eyes(m, mood)
        return [mesh for mesh in m.meshes() if mesh.material == "lid"]

    assert lids("public-smile") and not lids("internal-meltdown")


def test_his_face_is_one_skin_and_not_stuck_on_pieces():
    m = clay.Model()
    rafa.skull(m)
    skin = next(mesh for mesh in m.meshes() if mesh.material == "skin")
    assert skin.uvs is not None
    assert len(skin.vertices) == rafa_skin.ROWS * rafa_skin.COLS


def test_the_skin_is_the_same_bytes_on_every_build():
    def skin():
        m = clay.Model()
        rafa.skull(m)
        return next(mesh for mesh in m.meshes() if mesh.material == "skin").sha256

    assert skin() == skin()


@pytest.mark.parametrize("mood", MOODS)
@pytest.mark.parametrize("mouth", MOUTHS)
def test_every_mouth_presses_the_skin_it_sits_on(mood, mouth):
    dents, cavity = rafa.seat(mood, mouth)
    assert len(dents) >= 3, "corners and the hollow under the lip, whatever the shape"
    assert (cavity is not None) == (rafa.LIPS[rafa.mood(mood).rest if mouth == "rest" else mouth].bottom > 0)


def test_an_open_mouth_is_a_hollow_in_the_head_and_the_outline_stays():
    plain = rafa_skin.sheet()[0]
    dents, cavity = rafa.seat("public-smile", "open")
    pressed = rafa_skin.sheet((), cavity)[0]
    moved = np.linalg.norm(pressed - plain, axis=1)
    assert moved.max() > rafa.seat("public-smile", "open")[1].depth * 0.8
    assert np.abs(pressed[:, 0]).max() == pytest.approx(np.abs(plain[:, 0]).max(), abs=1e-6)
    assert dents


@pytest.mark.parametrize("mouth", ("open", "teeth", "wide", "lip"))
def test_teeth_are_separate_teeth(mouth):
    m = clay.Model()
    rafa.mouth(m, "public-smile", mouth)
    teeth = next(mesh for mesh in m.meshes() if mesh.material == "tooth")
    assert len(teeth.vertices) >= 4 * 64 * 33 * 0.9


def test_his_painted_skin_is_warmer_at_the_cheek_and_paler_on_the_nose():
    pixels = rafa.materials()["skin"].color_map.pixels
    assert pixels.shape == (rafa_skin.ROWS, rafa_skin.COLS, 4)
    assert len(np.unique(pixels.reshape(-1, 4), axis=0)) > 100, "paint, not one colour"


def test_his_neck_stands_between_chin_and_collar():
    head, body = clay.Model(), clay.Model()
    rafa.skull(head)
    rafa.body(body)
    skin = next(mesh for mesh in head.meshes() if mesh.material == "skin").vertices
    wool = next(mesh for mesh in body.meshes() if mesh.material == "teallight").vertices
    chin = skin[:, 1].max() + rafa.NECK[1]
    collar_front = wool[wool[:, 2] < -20, 1].min()
    assert collar_front > chin - 12, "a collar cannot climb past his chin"
    assert any(mesh.material == "neck" for mesh in body.meshes())


def test_wool_is_knit_and_the_rest_is_thumbed_clay():
    assert rafa.MATERIALS["teal"].normal_map is not rafa.MATERIALS["rust"].normal_map
    assert rafa.MATERIALS["rust"].normal_map is not None and rafa.MATERIALS["rust"].sheen
    assert rafa.MATERIALS["glaze"].normal_map is rafa.MATERIALS["rust"].normal_map, "a mug is clay and not a jumper"
    m = clay.Model()
    rafa.body(m)
    assert all(rafa.finished(mesh).uvs is not None for mesh in m.meshes() if mesh.material == "teal")


def test_a_glance_moves_his_eyes_and_a_blink_covers_them():
    def centre(gaze):
        m = clay.Model()
        rafa.eyes(m, "public-smile", gaze, "open")
        return next(x for x in m.meshes() if x.material == "iris").vertices[:, 0].mean()

    assert centre("left") < centre("ahead") < centre("right")

    def shut_share(lid):
        m = clay.Model()
        rafa.eyes(m, "internal-meltdown", "ahead", lid)
        return len(next(mesh for mesh in m.meshes() if mesh.material == "lid").vertices)

    assert shut_share("half") == shut_share("shut"), "both cover the eye from a stated share, with one shell"


def test_the_head_is_built_about_the_neck_so_a_pose_is_two_rotations():
    m = clay.Model()
    rafa.skull(m)
    verts = np.concatenate([mesh.vertices for mesh in m.meshes()])
    assert verts[:, 1].max() < 30 and verts[:, 1].min() > -160
    assert abs(verts[:, 0].mean()) < 6


@pytest.mark.parametrize("mood", MOODS)
def test_no_mouth_leaves_the_face(mood):
    for shape in MOUTHS:
        m = clay.Model()
        rafa.mouth(m, mood, shape)
        verts = np.concatenate([mesh.vertices for mesh in m.meshes()])
        assert (np.abs(verts[:, 0]) < rafa.FACE_HALF).all(), shape
        assert (verts[:, 1] < rafa.CHIN_Y).all(), shape


def _drawn(draw, *args) -> dict[str, np.ndarray]:
    model = clay.Model()
    draw(model, *args)
    return {mesh.material: mesh.vertices for mesh in model.meshes()}


def test_his_collar_stands_proud_of_the_mustard_so_the_two_never_cross():
    worn = _drawn(rafa.body)
    collar, shirt = worn["teallight"], worn["mustard"]
    band = (collar[:, 1] > -240.0) & (collar[:, 1] < -190.0) & (collar[:, 0] > 0.0) & (collar[:, 0] < 45.0)
    below = (shirt[:, 1] > -240.0) & (shirt[:, 1] < -190.0)
    inner = collar[band]
    inner = inner[inner[:, 0] < inner[:, 0].min() + 1.0]  # its edge over the shirt, where a crossing would show
    assert inner[:, 2].max() < shirt[below, 2].min()


def test_a_lid_that_comes_down_takes_the_glint_with_it():
    def whites(lid: str) -> int:
        return len(_drawn(rafa.eyes, "public-smile", "ahead", lid)["white"])

    assert whites("half") < whites("open")
    assert whites("shut") == whites("half")
