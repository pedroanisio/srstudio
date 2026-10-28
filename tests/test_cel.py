"""The Cel style: traced drawings held per run, a measured camera, boxed lettering, and a silent build."""

import json
import os
import re
import shutil
import subprocess
import xml.etree.ElementTree as ET
from pathlib import Path

import pytest
from sr_core.scene import Scene

from srstudio import CEL, LINEN, Canvas, Episode, EpisodeSpec, StyleError, Timeline, cel, flat_counter, registry

D = 1.5
CAM = [
    {"time": 0.0, "bbox": [240.0, 912.0, 407.0, 1047.0], "scale": 1.0, "tx": 0.0, "ty": 0.0},
    {"time": 0.5, "bbox": [240.0, 912.0, 407.0, 1047.0], "scale": 1.1, "tx": -20.0, "ty": -30.0},
    {"time": 1.0, "bbox": [240.0, 912.0, 407.0, 1047.0], "scale": 1.25, "tx": -40.123456, "ty": -60.0},
]
ROOM = [
    {"time": 0.0, "scale": 1.0, "tx": 0.0, "ty": 0.0},
    {"time": 0.5, "scale": 1.05, "tx": -10.0, "ty": -15.0},
    {"time": 1.0, "scale": 1.1, "tx": -20.0, "ty": -30.0},
]
RUNS = {
    "poses": [{"name": "a", "time": 0, "feature": [1.0, 2.0, 0.1], "raised": True}],
    "runs": [{"name": "a", "start": 0.0, "end": 0.5}, {"name": "b", "start": 0.5, "end": D}],
    "features": [[1.0, 2.0, 0.1]],
}
POSE_A = [{"fill": "#240102", "path": "M 0 0 L 10 0 L 10 10 Z"}, {"fill": "#c73a2f", "path": "M 2 2 L 8 2 L 8 8 Z"}]
POSE_B = [{"fill": "#240102", "path": "M 0 0 L 12 0 L 12 12 Z"}]
CAPTIONS = [
    {
        "id": "c1",
        "start": 0.0833,
        "end": 0.75,
        "text": "Hello there...",
        "phase": "opening",
        "sample_time": 0.4,
        "boxes": [{"x": 100, "y": 200, "w": 300, "h": 60, "fill": "#2b87ab", "glyphs": "M 1 1 L 2 2 Z"}],
    },
    {
        "id": "c2",
        "start": 0.8,
        "end": D,
        "text": "Second line.",
        "caption": "Second\nline",
        "phase": "test",
        "sample_time": 1.0,
        "boxes": [
            {"x": 100, "y": 200, "w": 300, "h": 60, "fill": "#2b87ab", "glyphs": "M 1 1 L 2 2 Z"},
            {"x": 100, "y": 270, "w": 200, "h": 60, "glyphs": "M 3 3 L 4 4 Z"},
        ],
    },
]


def silent_project(root: Path) -> Path:
    assets = root / "assets"
    assets.mkdir(exist_ok=True)
    (root / "script.json").write_text(json.dumps(CAPTIONS))
    (assets / "camera.json").write_text(json.dumps(CAM))
    (assets / "room-camera.json").write_text(json.dumps(ROOM))
    (assets / "poses.json").write_text(json.dumps(RUNS))
    (assets / "a.json").write_text(json.dumps(POSE_A))
    (assets / "b.json").write_text(json.dumps(POSE_B))
    return root


def canvas():
    scene = Scene(version="auto")
    scene.add_project(width=1080, height=1920, fps="24", duration=D)
    return Canvas(scene, LINEN, font_asset=None, namer=flat_counter("v"), signature=None)


def keys_of(node, prop):
    for a in node.findall("animate"):
        if a.get("property") == prop:
            return a, [(float(k.get("time")), k.get("value")) for k in a.findall("key")]
    raise AssertionError(f"no animate {prop}")


# -- the style and its input -----------------------------------------------------------------------------


def test_cel_is_silent_portrait_without_a_font_and_numbers_every_node_alike():
    s = EpisodeSpec(slug="t", title="t", description="t", root=".", seed=1, style=CEL)
    assert s.palette is LINEN and s.background == "#c5bbb0" and (s.width, s.height, s.fps) == (1080, 1920, 24)
    assert (s.dialogue, s.audio, s.font, s.font_id, s.font_policy, s.mouth_style) == (
        "script.json",
        None,
        None,
        None,
        None,
        None,
    )
    assert [s.namer("g"), s.namer("path"), s.namer("rect")] == ["v1", "v2", "v3"]
    assert s.accessibility == dict(flashCheck="error", contrastCheck="warn", legibilityCheck="warn")
    assert CEL.facts()["font"] is None and CEL.silent
    with pytest.raises(StyleError, match="silent"):
        CEL.mouth()
    assert {e.name for e in registry.entries(style="cel")} >= {"cel-room", "cel-traced", "cel-lettering"}


def test_timeline_reads_a_caption_script(tmp_path):
    t = Timeline.load(silent_project(tmp_path) / "script.json")
    assert t.duration == D and t.roles() == ["caption"] and t.cuts == [] and t.takes == []
    assert [p.caption for p in t.phrases] == ["Hello there", "Second\nline"]  # a missing caption drops the ellipsis
    assert (t.phrases[0].start, t.phrases[1].end) == (0.0833, D)
    for bad in ([], [{"start": 0, "end": 1}], [{"start": 1, "end": 0.5, "text": "x"}], ["x"]):
        with pytest.raises(ValueError):
            Timeline.from_dict(bad)
    with pytest.raises(ValueError, match="overlap"):
        Timeline.from_dict([{"start": 0, "end": 1, "text": "a"}, {"start": 0.5, "end": 2, "text": "b"}])


# -- the measured data --------------------------------------------------------------------------------------


def test_loaders_parse_the_package_files_and_refuse_bad_ones(tmp_path):
    root = silent_project(tmp_path)
    cam = cel.load_camera(root / "assets" / "camera.json")
    assert [k.time for k in cam] == [0.0, 0.5, 1.0] and cam[2].tx == -40.123456
    runs = cel.load_runs(root / "assets" / "poses.json")
    assert [(r.name, r.start, r.end) for r in runs] == [("a", 0.0, 0.5), ("b", 0.5, D)]
    drawings = cel.load_drawings(root / "assets", runs)
    assert [f.fill for f in drawings["a"]] == ["#240102", "#c73a2f"] and len(drawings["b"]) == 1
    captions = cel.load_captions(root / "script.json")
    assert [c.id for c in captions] == ["c1", "c2"] and captions[1].boxes[1].fill is None
    assert captions[0].caption == "Hello there" and captions[1].caption == "Second\nline"
    assert [c.phase for c in captions] == ["opening", "test"]

    def refused(loader, data, match, path=tmp_path / "bad.json"):
        path.write_text(json.dumps(data))
        with pytest.raises(cel.CelDataError, match=match):
            loader(path)

    refused(cel.load_camera, CAM[:1] + [{**CAM[1], "time": 0.0}], "increas")
    refused(cel.load_camera, [{**CAM[0], "scale": 0}], "scale")
    refused(cel.load_camera, [{**CAM[0], "zoom": 1}], "unknown")
    refused(cel.load_camera, [{"time": 0, "scale": 1}], "missing")
    refused(cel.load_camera, {"keys": []}, "list")
    refused(
        cel.load_runs, {"runs": [{"name": "a", "start": 0.0, "end": 0.5}, {"name": "b", "start": 0.6, "end": 1}]}, "gap"
    )
    refused(cel.load_runs, {"runs": [{"name": "a", "start": 0.1, "end": 0.5}]}, "start at 0")
    refused(cel.load_runs, {"runs": [{"name": "a", "start": 0.0, "end": 0.0}]}, "end")
    refused(
        cel.load_captions, [{**CAPTIONS[0], "boxes": [{"x": 1, "y": 1, "w": 1, "h": 1, "glyphs": "L 1 1"}]}], "path"
    )
    refused(
        cel.load_captions,
        [{**CAPTIONS[0], "boxes": [{"x": 1, "y": 1, "w": 1, "h": 1, "fill": "red", "glyphs": "M 1 1"}]}],
        "colour",
    )
    refused(cel.load_captions, [{**CAPTIONS[0], "boxes": []}], "box")
    refused(cel.load_captions, [{**CAPTIONS[0], "end": 0.01}], "end")
    refused(cel.load_captions, [{**CAPTIONS[0], "caption": 3}], "caption must be a str")
    refused(cel.load_captions, [{**CAPTIONS[0], "phase": 3}], "phase must be a str")
    refused(cel.load_captions, [CAPTIONS[0], {**CAPTIONS[1], "start": 0.5}], "overlap")
    refused(cel.load_runs, {"runs": ["a"]}, "expected an object")
    refused(cel.load_runs, {"runs": [{"name": 1, "start": 0.0, "end": 1.0}]}, "name must be a str")
    refused(cel.load_runs, {"runs": [{"name": "a", "start": True, "end": 1.0}]}, "start must be a number")
    (tmp_path / "bad.json").write_text("{")
    with pytest.raises(cel.CelDataError, match="not JSON"):
        cel.load_camera(tmp_path / "bad.json")
    with pytest.raises(cel.CelDataError, match="missing"):
        cel.load_camera(tmp_path / "absent.json")
    with pytest.raises(cel.CelDataError, match="c.json"):
        cel.load_drawings(root / "assets", runs + [cel.Run("c", D, D + 1)])
    (root / "assets" / "a.json").write_text(json.dumps([{"fill": "#240102"}]))
    with pytest.raises(cel.CelDataError, match="missing"):
        cel.load_drawings(root / "assets", runs)


def test_room_keys_are_expressed_inside_the_world_camera():
    cam, room = cel.parse_camera(CAM), cel.parse_camera(ROOM)
    comp = cel.compensate(cam, room)
    assert comp["scaleX"] == comp["scaleY"] and [round(v, 6) for _, v in comp["scaleX"]] == [1.0, 0.954545, 0.88]
    assert [round(v, 6) for _, v in comp["x"]] == [0.0, 9.090909, 16.098765]
    assert [t for t, _ in comp["y"]] == [0.0, 0.5, 1.0]
    with pytest.raises(cel.CelDataError, match="same times"):
        cel.compensate(cam, room[:2])
    with pytest.raises(cel.CelDataError, match="same times"):
        cel.compensate(cam, [cel.CameraKey(0.0, 1, 0, 0), cel.CameraKey(0.6, 1, 0, 0), cel.CameraKey(1.0, 1, 0, 0)])
    for empty in (lambda: cel.camera_tracks([], D), lambda: cel.compensate([], [])):
        with pytest.raises(cel.CelDataError, match="no keys"):
            empty()
    with pytest.raises(cel.CelDataError, match="after the project ends"):
        cel.camera_tracks(cam, 0.75)
    assert cel.camera_tracks(cam, 1.0)["x"][-1] == (1.0, -40.123456)  # a project ending on the last key adds none


# -- the parts ------------------------------------------------------------------------------------------------


def test_world_room_traced_and_lettering_draw_the_cel_conventions():
    cv = canvas()
    cam, roomcam = cel.parse_camera(CAM), cel.parse_camera(ROOM)
    world = cel.world(cv, cv.comp, cam, D)
    room = cel.room(cv, world, cam, roomcam, D)
    runs = [cel.Run("a", 0.0, 0.5), cel.Run("b", 0.5, D)]
    drawings = {"a": cel.parse_drawing(POSE_A), "b": cel.parse_drawing(POSE_B)}
    groups = cel.traced(cv, world, runs, drawings)
    boxes = cel.lettering(cv, cv.comp, cel.parse_captions(CAPTIONS)[1])
    assert room is not None and len(groups) == 2 and boxes is not None
    root = ET.fromstring(cv.scene.to_bytes(layout="pretty"))
    comp = root.find("composition")
    assert "assets" not in {e.tag for e in root} and "paints" not in {e.tag for e in root}
    top = list(comp)
    assert [g.get("id") for g in top] == ["v1", "v42"]  # the world, then the lettering group
    ids = [e.get("id") for e in comp.iter() if e.get("id")]
    assert ids == [f"v{i + 1}" for i in range(len(ids))]  # one counter, every node, document order
    w = top[0]
    a, keys = keys_of(w, "x")
    assert (a.get("timeBase"), a.get("defaultInterpolation")) == ("local", "linear")
    assert keys == [
        (0.0, "0.0"),
        (0.5, "-20.0"),
        (1.0, "-40.12346"),
        (D, "-40.12346"),
    ]  # five decimals, held to the end
    assert keys_of(w, "scaleX")[1] == keys_of(w, "scaleY")[1]
    r = w.find("group")
    assert r.get("id") == "v2" and keys_of(r, "scaleX")[1][1] == (0.5, "0.95455")
    shapes = r.findall("shape")
    rects = [s for s in shapes if s.get("shape") == "rect"]
    paths = [s for s in shapes if s.get("shape") == "path"]
    assert len(rects) == 8 and len(paths) == 26 and all("radius" not in s.attrib for s in rects)
    assert all(s.get("fillRule") == "evenodd" and s.get("width") == "1080" for s in paths)
    outlined = [s for s in paths if s.get("strokeWidth") != "0"]
    assert all(s.get("strokeCap") == "round" for s in outlined) and {s.get("stroke") for s in outlined} == {
        "#240102",
        "#b8835e",
    }
    assert all(s.get("stroke") == "#00000000" for s in paths if s.get("strokeWidth") == "0")
    assert rects[0].attrib["fill"] == "#c5bbb0" and rects[0].get("stroke") == "#00000000"
    assert rects[2].get("stroke") == "#240102" and rects[2].get("strokeWidth") == "9"
    runs_xml = w.findall("group")[1:]
    assert [(g.get("start"), g.get("end")) for g in runs_xml] == [("0", "0.5"), ("0.5", "1.5")]
    assert [s.get("fill") for s in runs_xml[0]] == ["#240102", "#c73a2f"] and runs_xml[0][0].get("path") == POSE_A[0][
        "path"
    ]
    cap = top[1]
    assert (cap.get("start"), cap.get("end")) == ("0.8", "1.5")
    assert [(s.get("shape"), s.get("fill")) for s in cap] == [
        ("rect", "#2b87ab"),
        ("path", "#fffaf5"),
        ("rect", LINEN.shade),
        ("path", "#fffaf5"),
    ]


FEATURES = {
    "poses": [
        {"name": "a", "time": 0, "feature": [100.0, 200.0, 0.0], "raised": True},
        {"name": "b", "time": 0.5, "feature": [110.0, 205.0, 0.0], "raised": False},
    ],
    "runs": [{"name": "a", "start": 0.0, "end": 0.5}, {"name": "b", "start": 0.5, "end": D}],
    # every 0.25 s: still, still, the hand reaches 30 px left and 4 px down at 0.75 s, back at 1.0, a bad sample
    "features": [
        [100.0, 200.0, 0.0],
        [100.0, 200.0, 0.0],
        [110.0, 205.0, 0.0],
        [80.0, 209.0, -0.05],
        [110.0, 205.0, 0.0],
        [900.0, 205.0, 0.0],
    ],
}


def test_features_are_the_tracked_point_per_sample_and_per_pose(tmp_path):
    base, samples, raised = cel.parse_features(FEATURES, step=0.25)
    assert base == {"a": (100.0, 200.0), "b": (110.0, 205.0)} and raised == {"a"}
    assert [(f.time, f.x, f.y) for f in samples[:4]] == [
        (0.0, 100.0, 200.0),
        (0.25, 100.0, 200.0),
        (0.5, 110.0, 205.0),
        (0.75, 80.0, 209.0),
    ]
    (tmp_path / "poses.json").write_text(json.dumps(FEATURES))
    assert cel.load_features(tmp_path / "poses.json") == (base, samples, raised)
    bad = dict(FEATURES, features=[[1.0, 2.0]])
    with pytest.raises(cel.CelDataError, match="three numbers"):
        cel.parse_features(bad)
    with pytest.raises(cel.CelDataError, match="step"):
        cel.parse_features(FEATURES, step=0)
    with pytest.raises(cel.CelDataError, match="feature"):
        cel.parse_features(dict(FEATURES, poses=[{"name": "a", "time": 0, "feature": "no", "raised": True}]))


# an ink-like fill: a square with a hole, and a filled island inside the hole (nesting depths 0, 1, 2)
INK = "M0 0 L100 0 L100 100 L0 100 Z M40 40 L60 40 L60 60 L40 60 Z M45 45 L55 45 L55 55 L45 55 Z"
# a keyboard-like fill: a square inside the box with its own hole (depths 0 and 1)
KEYS = "M40 40 L60 40 L60 60 L40 60 Z M45 45 L55 45 L55 55 L45 55 Z"
BOX = (40.0, 40.0, 60.0, 60.0)


def test_pressed_parts_move_filled_regions_with_their_holes_and_leave_the_ink_frame():
    stay, sink = cel.pressed_parts(INK, BOX)
    assert stay == "M0 0 L100 0 L100 100 L0 100 Z M40 40 L60 40 L60 60 L40 60 Z"  # the frame and its hole stay
    assert sink == "M45 45 L55 45 L55 55 L45 55 Z"  # the island inside the hole sinks
    assert cel.pressed_parts(KEYS, BOX) == ("", KEYS)  # the square sinks and carries its hole
    assert cel.pressed_parts(INK, (0.0, 0.0, 10.0, 10.0)) == (INK, "")
    with pytest.raises(cel.CelDataError, match="absolute"):
        cel.pressed_parts("M0 0 l10 0 l0 10 z", BOX)
    for box in ((10, 10, 5, 20), (0, 0, 10, 0), (0, 0, float("nan"), 1)):
        with pytest.raises(cel.CelDataError, match="box"):
            cel.Pressed(box, ())
    with pytest.raises(cel.CelDataError, match="positive"):
        cel.Pressed(BOX, (), press=0)
    with pytest.raises(cel.CelDataError, match="taps"):
        cel.Pressed(BOX, (0.5, -1))


def test_traced_sinks_the_pressed_parts_on_each_keystroke_of_the_run():
    cv = canvas()
    runs = [cel.Run("a", 0.0, 0.5), cel.Run("b", 0.5, D)]
    drawing = cel.parse_drawing([{"fill": "#240102", "path": INK}, {"fill": "#fffaf5", "path": KEYS}])
    drawings = {"a": drawing, "b": drawing}
    cel.traced(cv, cv.comp, runs, drawings, pressed=cel.Pressed(BOX, taps=(0.6, 1.4), press=4.0, press_seconds=0.125))
    root = ET.fromstring(cv.scene.to_bytes(layout="pretty"))
    run_a, run_b = [g for g in root.find("composition").iter("group") if g.get("start") is not None]
    assert [e.tag for e in run_a] == ["shape", "shape"]  # no keystroke in run a: drawn plain
    # run b: the ink frame, then its island in a sinking group, then the keys (whole) in a sinking group
    assert [e.tag for e in run_b] == ["shape", "group", "group"]
    island, keys = run_b.findall("group")
    assert [e.tag for e in island] == ["animate", "shape"] and [e.tag for e in keys] == ["animate", "shape"]
    assert (
        island.find("shape").get("path") == "M45 45 L55 45 L55 55 L45 55 Z" and keys.find("shape").get("path") == KEYS
    )
    for grp in (island, keys):
        a = grp.find("animate")
        # on the composition clock (the nested group has no start of its own): down 4 px by 0.6625, back at 0.725;
        # the 1.4 s press is still releasing when the run ends at 1.5
        assert (a.get("property"), a.get("timeBase")) == ("y", None)
        y = [(float(k.get("time")), float(k.get("value"))) for k in a.iter("key")]
        assert y == [(0.5, 0), (0.6, 0), (0.6625, 4), (0.725, 0), (1.4, 0), (1.4625, 4), (1.5, 1.6)]
    with pytest.raises(cel.CelDataError, match="nothing inside"):
        cel.traced(canvas(), cv.comp, runs, drawings, pressed=cel.Pressed((0.0, 0.0, 5.0, 5.0), taps=(0.6,)))
    # without keystrokes the output is the plain one
    plain, still = canvas(), canvas()
    cel.traced(plain, plain.comp, runs, drawings)
    cel.traced(still, still.comp, runs, drawings, pressed=cel.Pressed(BOX, taps=()))
    assert plain.scene.to_bytes(layout="pretty") == still.scene.to_bytes(layout="pretty")


def test_traced_refuses_a_run_without_a_drawing_or_a_drawing_without_a_run():
    cv = canvas()
    with pytest.raises(cel.CelDataError, match="no drawing"):
        cel.traced(cv, cv.comp, [cel.Run("a", 0, D)], {})
    with pytest.raises(cel.CelDataError, match="never shown"):
        cel.traced(cv, cv.comp, [cel.Run("a", 0, D)], {"a": cel.parse_drawing(POSE_A), "b": cel.parse_drawing(POSE_B)})


def test_canvas_creates_assets_on_first_use_and_rect_can_omit_its_radius():
    cv = canvas()
    cv.rect(cv.comp, 0, 0, 10, 10, "#ffffff", radius=None)
    cv.rect(cv.comp, 0, 0, 10, 10, "#ffffff")
    cv.path(cv.comp, "M 0 0 L 1 1", stroke=cv.ink, sw=0)
    root = ET.fromstring(cv.scene.to_bytes(layout="pretty"))
    assert root.find("assets") is None
    rects = root.findall("composition/shape")
    assert "radius" not in rects[0].attrib and rects[1].get("radius") == "0"
    assert rects[2].get("stroke") == cv.ink and "strokeCap" not in rects[2].attrib  # a zero stroke keeps its colour
    cv.assets.add_text(id="t", text="x", width=10, height=10, size="10", fontAsset="f")
    root = ET.fromstring(cv.scene.to_bytes(layout="pretty"))
    assert [e.tag for e in root][-2:] == ["assets", "composition"]  # the SDK keeps the schema order
    namer = flat_counter("n", 10)
    assert [namer("g"), namer("p")] == ["n11", "n12"]


# -- a whole episode --------------------------------------------------------------------------------------------


def test_silent_episode_builds_without_assets_and_validates(tmp_path):
    root = silent_project(tmp_path)
    ep = Episode(
        EpisodeSpec(
            slug="scene",
            title="t",
            description="t",
            root=root,
            seed=7,
            style=CEL,
            signature=False,
            font_policy="pinned",
            output="Cel.mp4",
            output_options=dict(codec="h264", container="mp4", fps="24", crf="17", preset="medium"),
        )
    )
    cv, t = ep.cv, ep.t
    cam = cel.load_camera(root / "assets" / "camera.json")
    runs = cel.load_runs(root / "assets" / "poses.json")
    world = cel.world(cv, ep.comp, cam, t.duration)
    cel.room(cv, world, cam, cel.load_camera(root / "assets" / "room-camera.json"), t.duration)
    cel.traced(cv, world, runs, cel.load_drawings(root / "assets", runs))
    for caption in cel.load_captions(root / "script.json"):
        cel.lettering(cv, ep.comp, caption)
    with pytest.raises(TypeError, match="silent"):
        ep.mouth("caption")
    out = ep.finish(tmp_path / "scene.xml")
    assert ep.check() == []
    xml = ET.parse(out).getroot()
    assert [e.tag for e in xml] == ["project", "metadata", "output", "composition"]
    assert xml.find("project").get("fontPolicy") == "pinned" and xml.find("project").get("background") == "#c5bbb0"
    assert xml.find("metadata/accessibility").get("flashCheck") == "error"
    assert xml.find("output").get("path") == "Cel.mp4" and "audioCodec" not in xml.find("output").attrib
    assert len(xml.findall("composition/group")) == 3 and re.fullmatch(r"v\d+", xml.find("composition/group").get("id"))
    engine = os.environ.get("SRSTUDIO_ENGINE") or shutil.which("scene-render")
    if not engine:
        pytest.skip("set SRSTUDIO_ENGINE to a scene-render binary")
    run = subprocess.run([engine, "validate", str(out)], capture_output=True, text=True)
    assert run.returncode == 0, run.stdout + run.stderr
