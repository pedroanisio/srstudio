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
SEATS = {  # each camera's x, y, pixels per metre, depth and seat-line slope for the two seats, as the room measured
    "two": {"mae": [148.5, 1333.4, 755.8, 3.28, 0.0], "bruno": [463.7, 1333.4, 755.8, 3.28, 0.0]},
    "mae": {"mae": [297.0, 1311.0, 1142.4, 2.17, 0.031], "bruno": [773.7, 1326.0, 1183.3, 2.10, 0.031]},
    "bruno": {"mae": [-63.6, 1338.3, 1212.7, 2.05, -0.056], "bruno": [423.0, 1311.0, 1138.3, 2.18, -0.056]},
}


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
    takes = {
        name: dict(eye=[0.0, 1.0, -3.0], look_at=[0.0, 0.5, 0.0], lens=28.0, spots=SPOTS, rigs=SEATS[name])
        for name in SEATS
    }
    return dict(
        engine="scene-render",
        engine_sha256="a" * 64,
        srlocations_commit=lounge.SRLOCATIONS_COMMIT,
        size=[lounge.WIDTH, lounge.HEIGHT],
        seconds={},
        takes=takes,
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


def drawn(elements) -> Counter:
    return Counter(frozenset((k, v) for k, v in e.attrib.items() if k != "id") for e in elements if tag(e) == "shape")


def keyed(elements) -> Counter:
    return Counter(tuple(tuple(sorted(k.attrib.items())) for k in e) for e in elements if tag(e) == "animate")


def shapes(project: Path, name: str) -> Counter:
    return drawn(scene(project, name))


def moves(project: Path, name: str) -> Counter:
    return keyed(scene(project, name))


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


def test_the_rigs_on_the_room_are_the_approved_rigs(project, kit):
    """Every shape and move is the reel's, but for the other character in a close-up, which the reel left out: that one
    is the reel's own rig drawn by the reel's own drawer, at the two-shot's place, scale and acts, on the close-up's
    clock, so its gaze and its keys fall on times the reel never drew it."""
    others = [
        element
        for take, shot in close_up_shots(project, "sofa-room", kit["reel"])
        for group in seated(shot, SEATS["two"]["bruno" if take == "mae" else "mae"])
        for element in group.iter()
    ]
    assert others, "each close-up draws the other character"
    assert not shapes(project, "sofa-room") - shapes(project, "sofa-control") - drawn(others)
    assert not moves(project, "sofa-room") - moves(project, "sofa-control") - keyed(others)


def close_up_shots(project: Path, name: str, reel) -> list[tuple[str, ElementTree.Element]]:
    """Each close-up's shot in the scene, with the character it is on: of the composition's groups that start at its
    cut (a caption starts there too), the one that draws the most."""
    shots: dict[float, ElementTree.Element] = {}
    for composition in (e for e in scene(project, name) if tag(e) == "composition"):
        for e in (e for e in composition if tag(e) == "group" and "start" in e.attrib):
            start = round(float(e.attrib["start"]), 3)
            if start not in shots or len(list(e.iter())) > len(list(shots[start].iter())):
                shots[start] = e
    found = [
        (who, shots[round(app.start, 3)])
        for app in sketch.appearances(reel.SKETCH.beats, reel.SKETCH.end)
        for who, figure in (("mae", reel.MAE_C), ("bruno", reel.BRUNO_C))
        if app.who == figure and app.start < reel.SKETCH.end
    ]
    assert {who for who, _ in found} == {"mae", "bruno"}, "the scene has both close-ups"
    return found


def seated(shot: ElementTree.Element, seat: list[float]) -> list[ElementTree.Element]:
    """The groups in `shot` that take the two-shot's picture of the card on `seat` into the shot's camera."""
    return [
        e
        for e in shot.iter()
        if tag(e) == "group"
        and float(e.attrib.get("anchorX", "nan")) == pytest.approx(seat[0])
        and float(e.attrib.get("anchorY", "nan")) == pytest.approx(seat[1])
    ]


@pytest.mark.parametrize("name", ["sofa-room", "cast-room"])
def test_each_close_up_camera_holds_both_rigs_on_their_seats(project, kit, study, name):
    """Neither figure leaves the sofa for a close-up: each close-up draws both cards, each on its own seat as that
    camera sees it, sized by its pixels per metre and with its base along the seat's line."""
    for take, shot in close_up_shots(project, name, kit["reel"]):
        for who in ("mae", "bruno"):
            groups = seated(shot, SEATS["two"][who])
            assert len(groups) == 1, f"{take}'s close-up seats {who} once"
            group, here = groups[0], SEATS[take][who]
            assert float(group.attrib["x"]) == pytest.approx(here[0])
            assert float(group.attrib["y"]) == pytest.approx(here[1])
            assert float(group.attrib["scaleX"]) == pytest.approx(here[2] / SEATS["two"][who][2])
            assert float(group.attrib["skewY"]) == pytest.approx(np.degrees(np.arctan(here[4])))
            assert sum(tag(e) == "shape" for e in group.iter()) > 20, f"{who} is drawn in {take}'s close-up"
            (lifted,) = [e for e in group if tag(e) == "group"]
            assert float(lifted.attrib["y"]) == pytest.approx(-study.lift(float(group.attrib["scaleX"])))


def test_a_card_sits_the_same_screen_rows_under_the_seat_at_any_scale(study):
    for scale in (0.5, 1.0, 1.28, 1.6):
        base = (study.DROP - study.lift(scale)) * scale
        assert base == pytest.approx(study.SUNK), "the base sits SUNK screen pixels under the seat's line"
    assert 0 < study.lift(1.0) < study.DROP, "lifted, but never above the seat's line"


def test_on_the_push_the_cards_keep_their_rows_under_the_seat_on_every_frame(project, lounge, study):
    rows = json.loads((project / "plates" / "room.json").read_text())["push"]["rig"]
    (lifted,) = [e for e in rider(project, "sofa-push") if tag(e) == "group"]
    keys = animation(lifted, "y")
    assert [t for t, _ in keys] == pytest.approx([n / lounge.PUSH_FPS for n in range(lounge.PUSH_FRAMES)], abs=1e-3)
    assert [v for _, v in keys] == pytest.approx([-study.lift(row[2] / rows[0][2]) for row in rows])


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
        (lambda d: d["takes"]["mae"].update(rigs={"mae": SEATS["mae"]["mae"]}), "camera mae seats"),
        (
            lambda d: d["takes"]["bruno"].update(rigs={**SEATS["bruno"], "mae": [1.0, 2.0, 3.0, 4.0]}),
            "camera bruno seats",
        ),
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


def test_each_rig_is_measured_on_its_own_side_of_the_seats(kit):
    compare = kit["compare"]
    picture = np.zeros((10, 10), np.uint8)
    picture[:, 2] = picture[:, 8] = 255
    halves = compare.sides(picture, 5.2)
    assert np.flatnonzero(halves["mae"].any(axis=0)).tolist() == [2]
    assert np.flatnonzero(halves["bruno"].any(axis=0)).tolist() == [8]
    assert compare.split_of({"mae": [100.0, 0, 0, 0, 0], "bruno": [300.0, 0, 0, 0, 0]}) == 200.0
    assert compare.sides(picture, -40)["bruno"].sum() == picture.sum(), "a split off the picture leaves it whole"


def test_the_seat_cover_counts_the_rows_under_the_front_in_pixels_and_in_the_figure_s_units(kit, lounge, monkeypatch):
    compare = kit["compare"]
    monkeypatch.setattr(compare.lounge, "TRACK_COLOURS", {"mae": "#ff00ff"})
    near = np.zeros((100, 100), np.uint8)
    near[60:, :] = 255
    wide = [np.zeros((100, 100), np.uint8) for _ in range(2)]
    wide[0][20:70, 10:90] = wide[1][20:84, 10:90] = 255
    spots = [{"mae": (50.0, 60.0)}] * 2
    cover = compare.seat_cover(wide, [near, near], spots, [1.0, 1.2])["mae"]
    assert cover["pixels_by_frame"] == [10.0, 24.0]
    assert cover["pixels"] == dict(first=10.0, last=24.0, least=10.0, most=24.0)
    assert cover["figure_units"] == dict(first=10.0, last=20.0, least=10.0, most=20.0)
