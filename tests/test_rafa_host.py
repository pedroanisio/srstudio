"""Rafa on the host's clock: a reel is a frame list of typed faces, on plates that exist, clear of everything on top."""

from __future__ import annotations

import numpy as np
import pytest

from srstudio import clay, host_kit, layout, plates, rafa, rafa_host
from srstudio.canvas import Canvas
from srstudio.head_motion import Channel, HeadPlan
from srstudio.rafa import NODS, TURNS, Face
from srstudio.rafa_host import RafaHostError, faces, project


def head_points(turn: float, nod: float) -> np.ndarray:
    """His head's surface in the scene at a pose, turned as the engine turns the placed mesh."""
    m = clay.Model()
    rafa.skull(m)
    verts = np.concatenate([mesh.vertices for mesh in m.meshes()])
    return rafa_host.posed(verts, turn, nod) + np.array(rafa.NECK)


def test_the_lens_matches_the_board_frame():
    points = project(np.array([rafa_host.CAMERA.target]))
    assert points[0] == pytest.approx((540.0, 960.0))
    left, right = project(np.array([(-10.0, -291.0, 0.0), (10.0, -291.0, 0.0)]))
    assert left[0] < 540.0 < right[0]


@pytest.mark.parametrize("turn", (TURNS[0], 0.0, TURNS[-1]))
@pytest.mark.parametrize("nod", (NODS[0], 0.0, NODS[-1]))
def test_at_every_extreme_his_head_is_inside_the_safe_area_and_over_the_captions(turn, nod):
    box = project(head_points(turn, nod))
    region = layout.VERTICAL.region(rafa_host.WIDTH, rafa_host.HEIGHT)
    top = region.y1 - host_kit.CAPTION_LOOK.block
    assert box[:, 0].min() >= region.x0 and box[:, 0].max() <= region.x1
    assert box[:, 1].min() >= region.y0
    assert box[:, 1].max() < top


def test_a_face_patch_box_holds_his_face_at_every_extreme():
    left, up, right, down = rafa_host.HEAD_BOX
    for turn in (TURNS[0], TURNS[-1]):
        for nod in (NODS[0], NODS[-1]):
            box = project(head_points(turn, nod))
            assert left <= box[:, 0].min() and box[:, 0].max() <= right
            assert up <= box[:, 1].min() and box[:, 1].max() <= down


@pytest.mark.parametrize("prop", rafa.PROPS)
def test_every_prop_stands_in_the_safe_area_above_the_captions_and_off_his_face(prop):
    m = clay.Model()
    x, y, z, yaw, scale = rafa_host.PLACES[prop]
    with m.at(x, y, z, yaw=yaw, scale=scale):
        rafa.PROPS[prop](m)
    box = project(np.concatenate([mesh.vertices for mesh in m.meshes()]))
    region = layout.VERTICAL.region(rafa_host.WIDTH, rafa_host.HEIGHT)
    assert box[:, 0].min() >= region.x0
    assert box[:, 1].max() < region.y1 - host_kit.CAPTION_LOOK.block
    face = project(head_points(0.0, 0.0))
    (left, up), (right, down) = box.min(axis=0), box.max(axis=0)
    inside = (left <= face[:, 0]) & (face[:, 0] <= right) & (up <= face[:, 1]) & (face[:, 1] <= down)
    assert not inside.any(), "a prop stands beside or under his face, never over it"


def foreground_points(prop: str) -> np.ndarray:
    m = clay.Model()
    kind, (x, y, z) = rafa_host.GRIPS[prop]
    (rafa.hold if kind == "hold" else rafa.rest)(m, x, y, z)
    return project(np.concatenate([mesh.vertices for mesh in m.meshes()]))


def test_every_prop_has_a_hand():
    assert set(rafa_host.GRIPS) == set(rafa.PROPS) == set(rafa_host.PLACES)


@pytest.mark.parametrize("prop", rafa.PROPS)
def test_his_hand_stays_in_the_safe_area_above_the_captions(prop):
    box = foreground_points(prop)
    region = layout.VERTICAL.region(rafa_host.WIDTH, rafa_host.HEIGHT)
    assert box[:, 0].max() <= region.x1
    assert box[:, 1].max() < region.y1 - host_kit.CAPTION_LOOK.block


@pytest.mark.parametrize("prop", rafa.PROPS)
@pytest.mark.parametrize("where", rafa.ROOMS)
def test_the_foreground_carries_the_prop_his_hand_and_the_near_edge_of_the_room(prop, where):
    plate = rafa_host.foreground(prop, where)
    names = {mesh.material for item in plate.placed for mesh in item.meshes}
    assert {"flesh", "teal", "teallight"} <= names


def test_the_worktop_runs_out_of_the_frame_with_no_front_face_in_it():
    m = clay.Model()
    rafa.counter(m)
    top = next(mesh for mesh in m.meshes() if mesh.material == "oak").vertices
    edge = project(np.array([(0.0, top[:, 1].min(), top[:, 2].min())]))
    assert edge[0, 1] > rafa_host.HEIGHT, "the near edge of the worktop is below the bottom of the frame"


def test_a_mouth_plate_sits_on_the_skull_its_mouth_pressed():
    plain, spoken = rafa_host.mouth_plate(Face(mouth="closed")), rafa_host.mouth_plate(Face(mouth="open"))
    skin = [next(mesh for mesh in plate.placed[1].meshes if mesh.material == "skin") for plate in (plain, spoken)]
    assert skin[0].sha256 != skin[1].sha256


def test_his_figure_has_the_rim_and_his_room_does_not():
    lights = {light.id for light in rafa_host.pose_plate(Face()).lights}
    assert "rim" in lights
    assert "rim" not in {light.id for light in rafa_host.room("rafa-kitchen").lights}
    keys = {plate_light.at for plate in (rafa_host.pose_plate(Face()), rafa_host.room("rafa-kitchen"),
            rafa_host.foreground("rafa-mug")) for plate_light in plate.lights if plate_light.id == "key"}  # fmt: skip
    assert len(keys) == 1, "one key direction across every plate"


def test_a_frame_list_covers_the_reel_with_a_face_for_every_frame():
    rows = faces(2.0)
    assert len(rows) == 60
    assert all(isinstance(row, Face) for row in rows)


def test_his_head_moves_on_twos_and_only_on_plate_steps():
    plan = HeadPlan(turn=Channel(((0.0, 0.0), (1.0, 4.9))), nod=Channel(((0.0, 0.0), (1.0, 3.1))))
    rows = faces(1.2, plan=plan)
    assert all(row.turn in TURNS and row.nod in NODS for row in rows)
    assert {rows[1].turn, rows[1].nod} == {rows[0].turn, rows[0].nod}
    assert any(row.turn != 0.0 for row in rows) and any(row.nod != 0.0 for row in rows)
    pairs = [(rows[i], rows[i + 1]) for i in range(0, len(rows) - 1, 2)]
    assert all((a.turn, a.nod) == (b.turn, b.nod) for a, b in pairs)


def test_he_blinks_through_half_and_shut():
    lids = [row.lid for row in faces(6.0)]
    assert "shut" in lids and "half" in lids
    at = lids.index("shut")
    assert lids[at - 1] == "half" and lids[at + 1] == "half"
    assert lids.count("shut") >= 2


def test_he_glances_when_the_plan_says_so():
    plan = HeadPlan(gaze=((0.0, "ahead"), (0.5, "left"), (1.0, "up"), (1.5, "right")))
    rows = faces(2.0, plan=plan, blink=False)
    assert rows[0].gaze == "ahead" and rows[20].gaze == "left" and rows[50].gaze == "right"
    assert rows[35].gaze == "ahead", "he has no plate looking up, so he holds ahead"


def test_a_mood_holds_from_its_second_and_an_unknown_one_is_refused():
    rows = faces(2.0, moods=((0.0, "public-smile"), (1.0, "internal-meltdown")))
    assert rows[29].mood == "public-smile" and rows[30].mood == "internal-meltdown"
    with pytest.raises(rafa.RafaError):
        faces(1.0, moods=((0.0, "calm"),))
    with pytest.raises(RafaHostError, match="from 0"):
        faces(1.0, moods=((0.5, "public-smile"),))


def test_his_mouth_follows_the_track_and_goes_back_to_the_moods_own_in_a_silence():
    track = ((0.0, "closed"), (0.5, "open"), (0.7, "closed"), (0.8, "wide"), (1.0, "closed"))
    rows = faces(2.0, mouths=track)
    assert rows[0].mouth == "rest"
    assert rows[16].mouth == "open"
    assert rows[22].mouth == "closed", "a shut mouth inside a phrase stays a lip shape"
    assert rows[25].mouth == "wide"
    assert rows[55].mouth == "rest"


def test_an_unknown_viseme_is_refused():
    with pytest.raises(rafa.RafaError):
        faces(1.0, mouths=((0.0, "kiss"),))


def fake_sheet(rows, tmp_path) -> rafa_host.Sheet:
    png = plates.write_png(tmp_path / "p.png", np.zeros((4, 4, 4), np.uint8))
    patch = plates.Patch(png, 10, 20, 4, 4)
    return rafa_host.Sheet(
        {(f.turn, f.nod): png for f in rows},
        {rafa_host.eye_key(f): patch for f in rows},
        {rafa_host.mouth_key(f): patch for f in rows},
    )


def test_perform_lays_out_a_gated_layer_per_plate_and_copies_each_file_once(tmp_path):
    from sr_core.scene import Scene

    scene = Scene(version="auto")
    scene.add_project(width=1080, height=1920, fps="30", duration=2)
    cv = Canvas(scene, font_asset=None)
    rows = faces(2.0)
    rafa_host.perform(cv, cv.comp, rows, fake_sheet(rows, tmp_path), tmp_path / "project")
    xml = scene.to_bytes().decode()
    assert xml.count("<image ") == 1
    assert len(list((tmp_path / "project" / "assets" / "rafa").iterdir())) == 1
    assert 'x="10"' in xml and 'y="20"' in xml


def test_perform_refuses_a_face_the_sheet_does_not_hold(tmp_path):
    from sr_core.scene import Scene

    scene = Scene(version="auto")
    scene.add_project(width=1080, height=1920, fps="30", duration=2)
    cv = Canvas(scene, font_asset=None)
    rows = faces(1.0)
    sheet = fake_sheet(rows, tmp_path)
    moved = (*rows[:-1], Face(turn=2.0))
    with pytest.raises(RafaHostError, match="plate"):
        rafa_host.perform(cv, cv.comp, moved, sheet, tmp_path / "project")


def test_the_host_is_a_parameter_of_the_kit_and_lints_cast_is_untouched():
    assert rafa_host.CAST.lip_synced == ("rafa",)
    assert rafa_host.CAST.characters == ("rafa",)
    assert host_kit.HOST_CAST.lip_synced == ("lint",)
    assert "rafa" not in host_kit.FRAMES


def test_the_camera_and_light_never_change_between_his_plates():
    a, b = rafa_host.pose_plate(Face()), rafa_host.pose_plate(Face(turn=2.0, nod=1.5))
    assert a.camera == b.camera and a.lights == b.lights
    assert plates.digest(a) != plates.digest(b)


def test_he_is_on_the_last_frame_of_a_reel_that_ends_between_frames() -> None:
    """The engine writes a frame for a part of one, so a reel of 25.044 s has 752 frames at 30 fps, not 751."""
    assert len(faces(25.044)) == 752


def test_a_reel_that_ends_on_a_frame_gets_no_extra_one() -> None:
    assert len(faces(25.6)) == 768  # 25.6 * 30 is 768.0000000000001 in a float
