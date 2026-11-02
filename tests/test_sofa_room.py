"""The sofa-room study (examples/paintover_proof): one lounge seen by several cameras and by a camera that moves.

The study builds on blank plates with a made-up room record. Each camera draws its own far, back and front plates; a
pushed plate shows on the one frame it was rendered for; the rigs ride a group whose every key is the room's projection
of the seat, and they are the approved rigs. The 2D side moves on the same curve over the same frames. A record that
does not describe the room is refused, and the measures catch a base in view and a dot off its mark. The plates need
srlocations' interpreter, so `lounge_plates.py` runs outside this suite.
"""

import json
import os
import shutil
import subprocess
import sys
from collections import Counter
from pathlib import Path
from xml.etree import ElementTree

import numpy as np
import pytest
from PIL import Image

from srstudio import TOON, sketch, toon_everyday

ROOT = Path(__file__).resolve().parent.parent
FOLDER = ROOT / "examples" / "paintover_proof"
SCRIPT = FOLDER / "sofa_room_study.py"
FONT = Path("/usr/share/fonts/truetype/dejavu/DejaVuSansCondensed.ttf")  # stands in for Comic Neue: captions must fit
SPOTS = {"cactus": [900.0, 1270.0, 100.0], "code": [1030.0, 1410.0, 120.0]}


@pytest.fixture(scope="module")
def kit():
    """The study's modules, imported without keeping the umask and the search path they set for a script."""
    path, mask = list(sys.path), os.umask(0)
    os.umask(mask)
    sys.path[:0] = [str(FOLDER), str(ROOT / "episodes")]
    try:
        import _lounge_set
        import plate_fronts
        import room_compare
        import sofa_room_study

        import it_autoplayed_data
    finally:
        sys.path[:] = path
        os.umask(mask)
    return dict(
        lounge=_lounge_set, fronts=plate_fronts, compare=room_compare, study=sofa_room_study, reel=it_autoplayed_data
    )


@pytest.fixture
def lounge(kit):
    return kit["lounge"]


@pytest.fixture
def study(kit):
    return kit["study"]


def room_record(lounge) -> dict:
    frames = lounge.PUSH_FRAMES
    take = dict(eye=[0.0, 1.0, -3.0], look_at=[0.0, 0.5, 0.0], lens=28.0, spots=SPOTS)
    return dict(
        engine="scene-render",
        engine_sha256="a" * 64,
        srlocations_commit=lounge.SRLOCATIONS_COMMIT,
        size=[lounge.WIDTH, lounge.HEIGHT],
        seconds={},
        takes=dict(two=take, mae=take, bruno=take),
        rig=[360.0, 1310.0, 300.0],
        push=dict(
            frames=frames,
            seconds=dict(far=1.0, back=1.0, near=1.0, track=1.0),
            rig=[[360.0 - n, 1310.0 + n, 300.0 + 2 * n] for n in range(frames)],
            spots=[{"cactus": [900.0 + n, 1270.0, 100.0], "code": [1030.0, 1410.0 + n, 120.0]} for n in range(frames)],
            eye=[[0.0, 1.0, -3.0 + n / frames] for n in range(frames)],
        ),
    )


def run(root: Path, *flags: str) -> None:
    env = {**os.environ, "PYTHONPATH": str(ROOT / "src")}
    done = subprocess.run([sys.executable, str(SCRIPT), str(root), *flags], env=env, capture_output=True, text=True)
    assert done.returncode == 0, done.stderr


@pytest.fixture(scope="module")
def project(kit, tmp_path_factory) -> Path:
    assert FONT.exists(), f"the test needs {FONT}"
    lounge, reel = kit["lounge"], kit["reel"]
    root = tmp_path_factory.mktemp("sofa-room")
    sk = reel.SKETCH
    (root / "assets").mkdir()
    (root / "script.json").write_text(json.dumps(sketch.cues(sk.beats, sk.end, sk.lines)))
    (root / "assets" / "poses.json").write_text(json.dumps(sketch._appearance_data(sk.beats, sk.end)))
    font = root / TOON.font.src
    font.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy(FONT, font)
    plates = root / "plates"
    plates.mkdir()
    (plates / "room.json").write_text(json.dumps(room_record(lounge)))
    dot = Image.new("RGBA", (lounge.WIDTH, lounge.HEIGHT))
    for offset, colour in enumerate(lounge.TRACK_COLOURS.values()):
        dot.paste(Image.new("RGBA", (10, 10), colour), (300 + 300 * offset, 1300))
    track = plates / lounge.push_plate(0, "track")
    track.parent.mkdir(parents=True)
    dot.save(track)
    for flags in ((), ("--push",), ("--control",), ("--cast",), ("--cast", "--push"), ("--marks",)):
        run(root, "--silent", *flags)
    return root


def scene(project: Path, name: str) -> list[ElementTree.Element]:
    return list(ElementTree.parse(project / f"{name}.scene.xml").iter())


def tag(element: ElementTree.Element) -> str:
    return element.tag.rpartition("}")[2]


def shapes(project: Path, name: str) -> Counter:
    elements = scene(project, name)
    return Counter(frozenset((k, v) for k, v in e.attrib.items() if k != "id") for e in elements if tag(e) == "shape")


def moves(project: Path, name: str) -> Counter:
    return Counter(
        tuple(tuple(sorted(k.attrib.items())) for k in e) for e in scene(project, name) if tag(e) == "animate"
    )


def plates_in_order(project: Path, name: str) -> list[str]:
    return [
        e.attrib["asset"] if tag(e) == "layer" else "shape"
        for e in scene(project, name)
        if tag(e) == "shape" or (tag(e) == "layer" and e.attrib.get("asset", "").startswith("plate-"))
    ]


def test_each_camera_has_plates_of_its_own(project):
    images = {e.attrib["src"] for e in scene(project, "sofa-room") if tag(e) == "image"}
    expected = {f"plates/{layer}.png" for layer in ("far", "back", "front")}
    expected |= {f"plates/{take}/{layer}.png" for take in ("mae", "bruno") for layer in ("far", "back", "front")}
    assert images == expected


@pytest.mark.parametrize("take", ["two", "mae", "bruno"])
def test_a_camera_draws_far_back_rigs_front(project, take):
    prefix = "plate-" if take == "two" else f"plate-{take}-"
    order = plates_in_order(project, "sofa-room")
    start = order.index(f"{prefix}far")
    shot = order[start:]
    front = shot.index(f"{prefix}front")
    assert shot[1] == f"{prefix}back"
    assert "shape" in shot[2:front], "a rig draws between the back plate and the front plate"


def test_the_rigs_on_the_room_are_the_approved_rigs(project):
    assert not shapes(project, "sofa-room") - shapes(project, "sofa-control")
    assert not moves(project, "sofa-room") - moves(project, "sofa-control")


def test_the_rigs_on_the_push_are_the_rigs_on_the_room(project):
    assert not shapes(project, "sofa-push") - shapes(project, "sofa-room")
    assert not moves(project, "sofa-room") - moves(project, "sofa-push")


def test_only_the_far_plates_are_blurred(project):
    for name in ("sofa-room", "sofa-push"):
        elements = scene(project, name)
        parents = {child: parent for parent in elements for child in parent}
        blurred = {id(e) for e in elements if e.attrib.get("effects") == "sofa-room-far"}
        assert blurred
        for layer in (e for e in elements if tag(e) == "layer" and e.attrib.get("asset", "").startswith("plate-")):
            above, chain = parents[layer], set()
            while above in parents:
                chain.add(id(above))
                above = parents[above]
            assert bool(chain & blurred) == ("far" in layer.attrib["asset"]), layer.attrib["asset"]


def held(project: Path, layer: str) -> dict[int, tuple[float, float]]:
    """Each pushed plate of `layer`: frame number → the times its group shows."""
    elements = scene(project, "sofa-push")
    parents = {child: parent for parent in elements for child in parent}
    spans = {}
    for e in elements:
        asset = e.attrib.get("asset", "") if tag(e) == "layer" else ""
        if asset.startswith(f"plate-push-{layer}-"):
            group = parents[e]
            spans[int(asset.rpartition("-")[2])] = (float(group.attrib["start"]), float(group.attrib["end"]))
    return spans


@pytest.mark.parametrize("layer", ["far", "back", "front"])
def test_a_pushed_plate_shows_on_its_own_frame_only(project, lounge, layer):
    spans = held(project, layer)
    assert sorted(spans) == list(range(lounge.PUSH_FRAMES))
    for frame in range(lounge.PUSH_FRAMES):
        at = frame / lounge.PUSH_FPS
        assert [n for n, (start, end) in spans.items() if start <= at < end] == [frame]


def test_the_last_pushed_plate_holds_to_the_end_of_its_shot(study):
    assert study.frame_span(3, 4, 24, 9.0) == {"start": round(2.5 / 24, 5), "end": 9.0}
    assert study.frame_span(0, 4, 24, 9.0) == {"start": 0.0, "end": round(0.5 / 24, 5)}


def animation(element: ElementTree.Element, prop: str) -> list[tuple[float, float]]:
    for child in element:
        if tag(child) == "animate" and child.attrib.get("property") == prop:
            return [(float(k.attrib["time"]), float(k.attrib["value"])) for k in child]
    return []


def rider(project: Path, name: str) -> ElementTree.Element:
    """The group that takes the rig's place on every frame: the one anchored at its first row."""
    x, y, _ = room_record_rig(project)
    groups = [
        e
        for e in scene(project, name)
        if tag(e) == "group" and float(e.attrib.get("anchorX", -1)) == x and float(e.attrib.get("anchorY", -1)) == y
    ]
    assert len(groups) == 1
    return groups[0]


def room_record_rig(project: Path) -> list[float]:
    return json.loads((project / "plates" / "room.json").read_text())["push"]["rig"][0]


@pytest.mark.parametrize("name", ["sofa-push", "cast-push", "marks"])
def test_the_rigs_group_takes_every_frame_from_the_room(project, lounge, name):
    rows = json.loads((project / "plates" / "room.json").read_text())["push"]["rig"]
    group = rider(project, name)
    for prop, value in (
        ("x", lambda row: row[0]),
        ("y", lambda row: row[1]),
        ("scaleX", lambda row: row[2] / rows[0][2]),
        ("scaleY", lambda row: row[2] / rows[0][2]),
    ):
        keys = animation(group, prop)
        assert [t for t, _ in keys] == pytest.approx([n / lounge.PUSH_FPS for n in range(lounge.PUSH_FRAMES)], abs=1e-3)
        assert [v for _, v in keys] == pytest.approx([value(row) for row in rows], abs=1e-3)


def test_the_dots_start_on_the_middle_of_the_tracker_s_pixels(project, lounge):
    middles = {
        e.attrib["fill"].lower(): (
            float(e.attrib["x"]) + float(e.attrib["width"]) / 2,
            float(e.attrib["y"]) + float(e.attrib["height"]) / 2,
        )
        for e in scene(project, "marks")
        if tag(e) == "shape"
    }
    assert middles[lounge.TRACK_COLOURS["mae"]] == pytest.approx((305.0, 1305.0))
    assert middles[lounge.TRACK_COLOURS["bruno"]] == pytest.approx((605.0, 1305.0))


def test_the_marks_ride_the_floor_not_the_rigs(project):
    rows = json.loads((project / "plates" / "room.json").read_text())["push"]["spots"]
    for name in ("cactus", "code"):
        x, y, _ = rows[0][name]
        carriers = [
            e
            for e in scene(project, "sofa-push")
            if tag(e) == "group" and float(e.attrib.get("anchorX", -1)) == x and float(e.attrib.get("anchorY", -1)) == y
        ]
        assert len(carriers) == 1
        assert [v for _, v in animation(carriers[0], "x")] == pytest.approx([row[name][0] for row in rows], abs=1e-3)


def test_the_2d_push_moves_on_the_same_curve_over_the_same_frames(project, lounge):
    group = next(e for e in scene(project, "sofa-control") if e.attrib.get("id") == "shot-001")
    assert (float(group.attrib["anchorX"]), float(group.attrib["anchorY"])) == (lounge.WIDTH / 2, lounge.HEIGHT / 2)
    keys = animation(group, "scaleX")
    assert [t for t, _ in keys] == pytest.approx([n / lounge.PUSH_FPS for n in range(lounge.PUSH_FRAMES)], abs=1e-3)
    assert [v for _, v in keys] == pytest.approx([lounge.magnification(n) for n in range(lounge.PUSH_FRAMES)], abs=1e-3)
    assert animation(group, "scaleY") == keys


def test_the_2d_push_touches_only_the_first_shot(project):
    groups = [e for e in scene(project, "sofa-control") if e.attrib.get("id", "").startswith("shot-")]
    assert len(groups) > 1
    assert [g.attrib["id"] for g in groups if animation(g, "scaleX")] == ["shot-001"]


def test_the_measuring_scenes_draw_no_plate(project):
    for name in ("cast-room", "cast-push", "marks"):
        assert not [e for e in scene(project, name) if tag(e) == "image"]
        assert not [e for e in scene(project, name) if e.attrib.get("asset", "").startswith("plate-")]


def test_the_engine_validation_of_every_scene_has_no_finding(project):
    for name in ("sofa-room", "sofa-push", "sofa-control", "marks", "cast-room", "cast-push"):
        assert json.loads((project / "qa" / f"{name}-validation.json").read_text()) == []


def test_the_push_starts_on_the_two_shot_and_eases_to_its_scale(lounge):
    steps = np.diff([lounge.magnification(n) for n in range(lounge.PUSH_FRAMES)])
    assert lounge.magnification(0) == pytest.approx(1.0)
    assert lounge.magnification(lounge.PUSH_FRAMES - 1) == pytest.approx(lounge.PUSH_SCALE)
    assert (steps > 0).all()
    assert steps[0] < steps[lounge.PUSH_FRAMES // 2] and steps[-1] < steps[lounge.PUSH_FRAMES // 2]


def test_the_speaker_s_lid_is_the_approved_speaker_s(lounge):
    assert lounge.SPEAKER_CAP == toon_everyday.CAP


def test_the_plate_names_keep_the_cameras_apart(lounge):
    assert lounge.plate("two", "far") == "far.png"
    assert lounge.plate("bruno", "front") == "bruno/front.png"
    assert lounge.push_plate(7, "near") == "push/near/0007.png"


def edited(lounge, change) -> dict:
    record = room_record(lounge)
    change(record)
    return record


@pytest.mark.parametrize(
    ("change", "message"),
    [
        (lambda d: d.update(guess=True), "expected the fields"),
        (lambda d: d.pop("takes"), "expected the fields"),
        (lambda d: d.update(srlocations_commit="0" * 40), "drawn by srlocations"),
        (lambda d: d.update(engine_sha256="abc"), "no sha256"),
        (lambda d: d.update(size=[1080, 1080]), "the plates are"),
        (lambda d: d["takes"].pop("mae"), "the cameras are"),
        (lambda d: d["takes"]["two"].update(guess=1), "camera two has"),
        (lambda d: d["takes"].update(bruno={**d["takes"]["bruno"], "spots": {}}), "camera bruno places"),
        (lambda d: d["push"].pop("eye"), "the push has"),
        (lambda d: d["push"].update(frames=3), "frames, not"),
        (lambda d: d["push"]["rig"].pop(), "the push's rig has"),
        (lambda d: d["push"]["spots"][4].pop("code"), "frame 4 of the push"),
    ],
)
def test_a_room_record_that_does_not_describe_the_room_is_refused(lounge, study, tmp_path, change, message):
    path = tmp_path / "room.json"
    path.write_text(json.dumps(edited(lounge, change)))
    with pytest.raises(study.PlateError, match=message):
        study.Room.load(path)


def test_a_room_drawn_without_the_push_cannot_stage_it(lounge, study, tmp_path):
    path = tmp_path / "room.json"
    path.write_text(json.dumps(edited(lounge, lambda d: d.update(push={}))))
    with pytest.raises(study.PlateError, match="without --push"):
        study.Room.load(path).pushed()


def test_a_plate_with_no_dot_is_refused(study, lounge, tmp_path):
    path = tmp_path / "empty.png"
    Image.new("RGBA", (20, 20)).save(path)
    with pytest.raises(study.PlateError, match="no #"):
        study.centroid(path, lounge.TRACK_COLOURS["mae"])


def test_the_centroid_of_a_dot_is_its_middle(study, lounge, tmp_path):
    path = tmp_path / "dot.png"
    picture = Image.new("RGBA", (40, 40))
    picture.paste(Image.new("RGBA", (10, 4), lounge.TRACK_COLOURS["bruno"]), (11, 21))
    picture.save(path)
    assert study.centroid(path, lounge.TRACK_COLOURS["bruno"]) == pytest.approx((15.5, 22.5))
    with pytest.raises(study.PlateError):
        study.centroid(path, lounge.TRACK_COLOURS["mae"])


def test_the_front_plate_is_the_back_plate_inside_the_near_shape_and_inked_on_its_edge(kit):
    fronts = kit["fronts"]
    back = np.full((60, 60, 4), 200, np.uint8)
    back[..., 3] = 255
    near = np.zeros((60, 60), np.uint8)
    near[30:, :] = 255
    front = fronts.front_of(back, near)
    assert (front[50, 30] == [200, 200, 200, 255]).all(), "inside the shape: the back plate's own pixel"
    assert (front[10, 30] == [0, 0, 0, 0]).all() or front[10, 30, 3] == 0, "outside the shape: nothing, the rigs show"
    assert front[29, 30, 3] == 255 and front[29, 30, :3].max() == 0, "on the edge: the line, solid and black"
    assert front[30, 30, 3] == 255 and front[30, 30, :3].max() == 0
    line = front[:, 30, 3] > 0
    assert np.flatnonzero(line)[0] == 26, "the line stands half its width out of the shape"


def test_the_spans_of_the_cameras_cover_the_picture_without_a_gap(kit):
    compare = kit["compare"]
    assert [compare.take_of(frame) for frame in (0, 110, 111, 159, 160, 189)] == [
        "two",
        "two",
        "mae",
        "mae",
        "bruno",
        "bruno",
    ]
    assert {compare.take_of(frame) for frame in range(compare.FRAMES)} == {"two", "mae", "bruno"}


def test_the_camera_spans_are_the_reel_s_cuts(kit):
    compare, reel = kit["compare"], kit["reel"]
    fps = compare.FPS
    apps = sketch.appearances(reel.SKETCH.beats, reel.SKETCH.end)
    frames = {app.who: (app.start, app.end) for app in reversed(apps)}
    for take, who in (("mae", reel.MAE_C), ("bruno", reel.BRUNO_C)):
        first, last = compare.TAKES[take]
        start, end = frames[who]
        assert (first - 1) / fps < start <= first / fps
        assert last / fps < end
    assert compare.TAKES["mae"][1] + 1 == compare.TAKES["bruno"][0]


def figure(bottom: int) -> np.ndarray:
    picture = np.zeros((100, 100), np.uint8)
    picture[20:bottom, 30:70] = 255
    return picture


def test_the_base_cover_counts_every_frame_and_names_the_worst(kit):
    near = np.zeros((100, 100), np.uint8)
    near[60:, :] = 255
    held_frames = kit["compare"].base_cover([figure(80), figure(50), figure(80)], [near, near, near])
    assert held_frames["frames"] == 3
    assert held_frames["base_columns_exposed"] == 40
    assert held_frames["frames_with_a_column_exposed"] == 1
    assert held_frames["frame_of_least_cover"] == 1
    assert held_frames["least_rows_of_cover"] < 0


def test_the_drift_reads_the_distance_between_the_dots(kit, lounge, tmp_path, monkeypatch):
    compare = kit["compare"]
    monkeypatch.setattr(compare.lounge, "PUSH_FRAMES", 2)
    track, marks = tmp_path / "track", tmp_path / "marks"
    track.mkdir(), marks.mkdir()
    for frame, shift in enumerate((0, 3)):
        for folder, x in ((track, 10), (marks, 10 + shift)):
            picture = Image.new("RGBA", (60, 40))
            for offset, colour in enumerate(lounge.TRACK_COLOURS.values()):
                picture.paste(Image.new("RGBA", (5, 5), colour), (x, 5 + 20 * offset))
            picture.save(folder / f"{frame:04d}.png")
    drift = compare.drift(track, marks)
    assert drift["mae"] == {"mean_px": 1.5, "max_px": 3.0, "worst_frame": 1, "first_frame_px": 0.0}
