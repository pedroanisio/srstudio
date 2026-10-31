"""Pedro on the host's clock: a frame list of typed faces, on plates that exist, inside the frame at every pose."""

from __future__ import annotations

import numpy as np
import pytest
from sr_core.scene import Scene

from srstudio import head_motion, layout, pedro, pedro_host, plate_host, plates
from srstudio.canvas import Canvas
from srstudio.head_motion import Channel, HeadPlan
from srstudio.pedro import NODS, TURNS, Face
from srstudio.pedro_host import PedroHostError, faces, project
from srstudio.plates import Patch


def head_points(turn: float, nod: float) -> np.ndarray:
    verts = np.concatenate([mesh.vertices for mesh in (*pedro.cap(), *pedro.skull())])
    return pedro_host.posed(verts, turn, nod) + np.array(pedro.NECK)


def test_the_lens_aims_at_the_middle_of_the_frame():
    assert project(np.array([pedro_host.CAMERA.target]))[0] == pytest.approx((540.0, 960.0))


@pytest.mark.parametrize("turn", (TURNS[0], TURNS[-1]))
@pytest.mark.parametrize("nod", (NODS[0], NODS[-1]))
def test_at_every_extreme_his_head_stays_in_the_safe_area_and_inside_the_patch_box(turn, nod):
    box = project(head_points(turn, nod))
    region = layout.VERTICAL.region(pedro_host.WIDTH, pedro_host.HEIGHT)
    assert box[:, 0].min() >= region.x0 and box[:, 0].max() <= region.x1
    assert box[:, 1].min() >= region.y0
    left, up, right, down = pedro_host.HEAD_BOX
    assert left <= box[:, 0].min() and box[:, 0].max() <= right
    assert up <= box[:, 1].min() and box[:, 1].max() <= down


def test_a_turn_to_the_right_brings_his_nose_to_the_frames_right():
    nose = np.array([[0.0, -2.0, -14.0]]) + (0.0, 0.0, 0.0)
    right = project(pedro_host.posed(nose, 8.0, 0.0) + np.array(pedro.NECK))
    left = project(pedro_host.posed(nose, -8.0, 0.0) + np.array(pedro.NECK))
    assert left[0, 0] < 540.0 < right[0, 0]


def test_every_frame_of_a_reel_is_a_typed_face():
    rows = faces(2.0)
    assert len(rows) == 2 * pedro_host.FPS
    assert all(isinstance(face, Face) for face in rows)
    assert {face.lid for face in rows} >= {"open", "half", "shut"}


def test_a_reel_needs_a_mood_from_its_first_frame():
    with pytest.raises(PedroHostError, match="mood"):
        faces(1.0, moods=((0.5, "smile"),))


def test_an_unknown_mouth_in_a_track_is_refused():
    with pytest.raises(pedro.PedroError, match="mouth"):
        faces(1.0, mouths=((0.0, "scream"),))


def test_a_change_of_mood_runs_through_every_share_and_lands():
    rows = faces(1.0, moods=((0.0, "neutral"), (0.5, "smile")), blink=False)
    at = round(0.5 * pedro_host.FPS)
    shares = [rows[at + i].share for i in range(0, 2 * len(pedro.SHARES), pedro_host.BLEND_STEP)]
    assert shares[:3] == [0.25, 0.5, 0.75]
    assert rows[at + 6].mood == "smile" and not rows[at + 6].toward
    assert rows[at - 1] == Face()


def test_the_head_holds_on_twos_and_lands_on_plate_steps():
    plan = HeadPlan(turn=Channel(((0.0, 0.0), (1.0, 6.0))), nod=Channel(((0.0, 0.0), (1.0, 4.0))))
    rows = faces(1.0, plan=plan, blink=False)
    assert all(rows[i].turn == rows[i + 1].turn for i in range(0, 28, 2))
    assert all(face.turn in TURNS and face.nod in NODS for face in rows)
    assert rows[-1].turn > 0.0


def test_a_shut_mouth_goes_back_to_the_moods_own():
    rows = faces(1.0, mouths=((0.0, "open"), (0.2, "closed")), blink=False)
    assert rows[0].mouth == "open"
    assert rows[10].mouth == "rest"


def test_the_camera_and_light_never_change_between_his_plates():
    a, b = pedro_host.pose_plate(Face()), pedro_host.eye_plate(Face(turn=4.0))
    assert a.camera == b.camera and a.lights == b.lights


def test_a_plate_is_named_by_what_it_draws():
    a = plates.digest(pedro_host.pose_plate(Face()))
    assert a == plates.digest(pedro_host.pose_plate(Face(mood="smile")))
    assert a != plates.digest(pedro_host.pose_plate(Face(turn=2.0)))
    assert a != plates.digest(pedro_host.mouth_plate(Face()))


def test_the_body_stands_still_when_his_head_turns():
    plate = pedro_host.pose_plate(Face(turn=4.0, nod=3.0))
    still, head = plate.placed
    assert (still.rotation_x, still.rotation_y) == (0.0, 0.0)
    assert (head.rotation_x, head.rotation_y) == (3.0, -4.0)


def fake_sheet(rows, tmp_path) -> pedro_host.Sheet:
    png = tmp_path / "a.png"
    png.write_bytes(b"x")
    cut = Patch(png, 10, 20, 30, 40)
    return pedro_host.Sheet(
        {(f.turn, f.nod): png for f in rows},
        {pedro_host.eye_key(f): cut for f in rows},
        {pedro_host.mouth_key(f): cut for f in rows},
    )


def canvas() -> tuple[Scene, Canvas]:
    scene = Scene(version="auto")
    scene.add_project(width=1080, height=1920, fps="30", duration=1, background="#303945")
    return scene, Canvas(scene, font_asset=None)


def test_perform_lays_each_picture_once_and_gates_it(tmp_path):
    rows = faces(0.5, blink=False)
    scene, cv = canvas()
    pedro_host.perform(cv, cv.comp, rows, fake_sheet(rows, tmp_path), tmp_path / "project")
    assert scene.to_bytes().decode().count("<image ") == 1
    assert len(list((tmp_path / "project" / "assets" / "pedro").iterdir())) == 1


def test_perform_refuses_a_face_the_sheet_does_not_hold(tmp_path):
    rows = faces(0.5, blink=False)
    _, cv = canvas()
    made = fake_sheet(rows, tmp_path)
    with pytest.raises(PedroHostError, match="no plate"):
        pedro_host.perform(cv, cv.comp, (Face(mouth="open"),), made, tmp_path / "project")


def test_a_runs_list_keeps_every_frame():
    spans = plate_host.runs(["a", "a", "b", "a"], 10)
    assert spans["a"] == [(0.0, 0.2), (0.3, 0.4)]
    assert spans["b"] == [(0.2, 0.3)]


def test_the_catalog_shows_every_mood_mouth_lid_and_gaze():
    assert len(pedro_host.part_plates("pedro")) == 3 + 6 + 2 + 2
    assert pedro_host.part_plates("rafa") == ()


def test_his_nods_on_speech_cross_more_than_one_plate_step():
    """A head that rounds to one plate a nod does not move, which is how a first cut of him stood still."""
    letters = "the group chat has rules and nobody tells you what they are".split()
    words, t = [], 0.3
    for word in letters:
        chars = tuple((t + i * 0.07, t + (i + 1) * 0.07) for i in range(len(word)))
        words.append(head_motion.Word(word, chars[0][0], chars[-1][1], chars, False))
        t = chars[-1][1] + 0.12
    speech = head_motion.Speech(0.0, tuple(words), (-20.0,) * round((t + 1) * head_motion.LOUD_RATE))
    plan = head_motion.plan(pedro_host.MOTION, [speech], t + 1)
    rows = faces(t + 1, plan=plan)
    assert len({face.nod for face in rows}) >= 3
