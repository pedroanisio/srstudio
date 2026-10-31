"""Pedro, the operator's likeness: one sculpt, every state a continuous change of it, nothing swapped in as a static."""

from __future__ import annotations

import math

import numpy as np
import pytest

from srstudio import clay, parts, pedro, pedro_sculpt, pedro_wardrobe
from srstudio.pedro import GAZES, LIDS, MOODS, MOUTHS, NODS, TURNS, Face, PedroError


def centres(mesh: clay.Mesh) -> np.ndarray:
    return mesh.vertices[mesh.triangles].mean(axis=1)


def named(meshes: tuple[clay.Mesh, ...], material: str) -> clay.Mesh:
    return next(mesh for mesh in meshes if mesh.material == material)


def test_the_sculpts_three_expressions_lead_his_moods_and_the_furrow_follows():
    assert tuple(MOODS) == ("neutral", "smile", "raised-brow", "furrow")


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


def test_the_outline_is_held_by_a_monotone_interpolant():
    assert pedro_sculpt.width(np.array([25.0]))[0] == pytest.approx(19.0)
    assert pedro_sculpt.width(np.array([35.0]))[0] == pytest.approx(17.9)
    points = pedro_sculpt.width(np.linspace(0.0, 50.0, 200))
    assert points.max() <= 19.0 + 1e-9  # a monotone interpolant does not overshoot its numbers


def test_his_face_tapers_from_the_cheekbones_to_the_chin():
    assert pedro_sculpt.width(np.array([44.0]))[0] < 0.8 * pedro_sculpt.width(np.array([25.0]))[0]


def scene_of(mesh_names: tuple[str, ...], meshes) -> np.ndarray:
    return np.concatenate([mesh.vertices for mesh in meshes if mesh.material in mesh_names]) + np.array(pedro.NECK)


def test_his_face_is_clearly_longer_than_it_is_wide():
    """A lean face at a glance: hairline to beard tip against the widest he is across the cheekbones."""
    skin = scene_of(("skin", "scalp"), (*pedro.cap(), *pedro.skull()))
    cheeks = 2.0 * np.abs(skin[:, 0]).max()
    beard = scene_of(("goatee",), pedro.mouth("neutral", "rest"))
    hairline = pedro._SEAT[1] + pedro._hairline(np.array(0.0)) * pedro.SCALE
    assert 1.3 <= (beard[:, 1].max() - hairline) / cheeks <= 1.6


def test_a_real_neck_shows_between_his_beard_and_his_tee():
    beard = scene_of(("goatee",), pedro.mouth("neutral", "rest"))
    crew_front = pedro_wardrobe._neckline()[:, 1].max()
    assert crew_front - beard[:, 1].max() > 2.0
    assert pedro_wardrobe._NECK[1][0] < 0.7 * pedro_sculpt.width(np.array([25.0]))[0] * pedro.LEAN * pedro.SCALE


def test_the_goatee_leaves_his_cheeks_bare_and_runs_past_the_chin():
    outline = pedro._BEARD_OUT
    on_skin = outline[outline[:, 1] < pedro._BEARD_HANGS_FROM]
    assert (on_skin[:, 0] < 0.76 * pedro_sculpt.width(on_skin[:, 1])).all()
    assert outline[:, 1].max() > 50.0  # the chin is 50
    assert outline[-2, 0] < outline[5, 0] / 3.0  # it ends in a soft point


def test_his_forehead_carries_no_lines():
    ys = np.linspace(8.0, 16.0, 81)
    bend = np.diff(pedro_sculpt.front(np.full_like(ys, 3.0), ys), n=2)
    assert np.count_nonzero(np.diff(np.sign(bend))) <= 3  # a line across it would bend the surface both ways


def test_his_eyes_sit_deeper_than_the_ridge_over_them():
    assert pedro_sculpt.front(7.7, 19.4) < pedro_sculpt.front(7.7, 24.1) - 1.0


def test_his_iris_stands_round_on_a_lean_head():
    iris = next(mesh for mesh in pedro.eyes(Face()) if mesh.material == "iris-rim").vertices
    left = iris[iris[:, 0] > 0.0]
    # the opening cuts its height, so the round disk shows in its width against the size it was drawn at
    assert np.ptp(left[:, 0]) == pytest.approx(2 * 1.88 * pedro.SCALE, rel=0.04)


@pytest.mark.parametrize("name", MOODS)
def test_his_brows_are_never_level(name):
    look = pedro.mood(name)
    assert abs(look.brow_right - look.brow_left) > 0.3


def test_the_furrow_brings_the_inner_ends_of_his_brows_down_and_lifts_nothing_else():
    plain, cross = pedro.mood("neutral"), pedro.mood("furrow")
    assert cross.knit > plain.knit == 0.0
    inner = pedro._brow_y(3.0, 0.0, cross.knit) - pedro._brow_y(3.0, 0.0)
    outer = pedro._brow_y(13.4, 0.0, cross.knit) - pedro._brow_y(13.4, 0.0)
    assert inner > 0.4 and abs(outer) < 1e-9


def test_a_blend_towards_the_furrow_carries_the_knit():
    half = pedro.mood("neutral").towards(pedro.mood("furrow"), 0.5)
    assert half.knit == pytest.approx(pedro.mood("furrow").knit / 2.0)


def head_units(meshes) -> np.ndarray:
    """Vertices back in the sculpt's own numbers: the head 50 tall from the crown."""
    verts = np.concatenate([mesh.vertices for mesh in meshes])
    return (verts + np.array(pedro.NECK) - np.array(pedro._SEAT)) / pedro.SCALE / (pedro.LEAN, 1.0, 1.0)


def hair_points() -> np.ndarray:
    return head_units(mesh for mesh in pedro.cap() if mesh.material in ("hair-grey", "hair-silver"))


def test_his_hair_is_a_short_crop_that_stays_off_the_shaved_sides():
    hair = hair_points()
    assert -5.0 < hair[:, 1].min() < -1.0  # above the crown, which is y 0, and not far
    outer = hair[np.abs(hair[:, 0]) > 12.0]
    assert outer[:, 1].max() < 8.0  # at the sides it stops high


def test_the_hairline_peaks_at_the_front_and_tails_down_the_back_above_the_sides():
    front, side, back = pedro._hairline(np.array((0.0, math.pi / 2.0, math.pi)))
    assert front > side + 3.0 and back > side + 6.0


def test_the_hair_is_the_same_bytes_on_every_build():
    first = pedro.cap()
    pedro.cap.cache_clear()
    assert [mesh.sha256 for mesh in first] == [mesh.sha256 for mesh in pedro.cap()]


def skin_at(y: float, around: float, depth: float = 15.0) -> np.ndarray:
    return np.array((depth * math.sin(around), y, -depth * math.cos(around)))


@pytest.mark.parametrize(("y", "around"), ((12.0, 0.0), (20.0, 0.4), (24.0, 0.9), (36.0, 0.0), (32.0, 1.2)))
def test_his_face_carries_no_stubble(y, around):
    assert pedro._shaved(skin_at(y, around)) == 0.0


@pytest.mark.parametrize(("y", "around"), ((14.0, 1.9), (20.0, 2.6), (30.0, 3.0)))
def test_the_sides_and_back_of_his_head_are_shaved(y, around):
    assert pedro._shaved(skin_at(y, around)) > 0.9


def test_the_stubble_finishes_on_skin_no_expression_moves():
    """Past that line the skin is another mesh, without the picture: a shave running over it stops in a block."""
    points, tris = pedro_sculpt.grid()
    corners = points[tris[pedro._lower(tris, points)]].reshape(-1, 3)
    assert pedro._shaved(corners).max() < 0.01


def test_the_scalp_picture_is_stable_and_bare_where_his_face_is():
    picture = pedro.scalp_picture()
    assert picture.sha256 == pedro.scalp_picture.__wrapped__().sha256
    assert picture.pixels.shape == (1024, 1024, 4)
    assert len({tuple(row) for row in picture.pixels[..., :3].reshape(-1, 3)[::97]}) > 2


def test_his_moustache_is_darker_than_his_chin():
    picture = pedro.goatee_picture().pixels[..., 0].astype(float)
    height, width = picture.shape
    moustache = picture[height // 4 : height // 3, width // 3 : 2 * width // 3].mean()
    chin = picture[3 * height // 4 :, width // 3 : 2 * width // 3].mean()
    assert moustache + 15.0 < chin


def test_the_glasses_are_an_option_of_frames_alone():
    used = {mesh.material for mesh in pedro.glasses()}
    assert used == {"frame", "frame-line"}
    assert not used & {mesh.material for mesh in (*pedro.cap(), *pedro.eyes(Face()))}


def test_the_glasses_rest_on_his_head_and_never_sink_into_it():
    frame = head_units(pedro.glasses())
    assert frame[:, 2].max() > 2.0  # the arms reach his ears
    assert (pedro_sculpt.field(*frame.T) > 0.0).all()


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
    laid = named(pedro.mouth("neutral", "rest"), "goatee").vertices[:, 1] + pedro.NECK[1]
    on_skin = laid < pedro._SEAT[1] + pedro._BEARD_HANGS_FROM * pedro.SCALE  # past that it hangs off the chin
    pick = goatee.vertices[on_skin][::97]
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
