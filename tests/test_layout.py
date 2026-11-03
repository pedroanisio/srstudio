"""Safe areas and the overlay bounds check: path geometry, eval transforms, the engine audit."""

import json
import math
import os
import shutil
import subprocess
import xml.etree.ElementTree as ET
from pathlib import Path

import pytest
from sr_core.scene import Scene

from srstudio import Episode, EpisodeSpec, graphics
from srstudio.layout import (
    VERTICAL,
    Box,
    Crossing,
    LayoutError,
    PathError,
    SafeArea,
    check_overlays,
    crossings_at,
    path_bounds,
    shape_bounds,
)


def engine() -> Path:
    found = os.environ.get("SRSTUDIO_ENGINE") or shutil.which("scene-render")
    if not found or not Path(found).exists():
        pytest.skip("set SRSTUDIO_ENGINE to a scene-render binary")
    return Path(found)


def close(box: Box, expected: tuple[float, float, float, float], tol: float = 1e-9) -> bool:
    return all(math.isclose(a, b, abs_tol=tol) for a, b in zip(box.as_tuple(), expected, strict=True))


# -- safe areas ---------------------------------------------------------------------------------------


def test_vertical_region_is_the_engine_documented_production_box():
    region = VERTICAL.region(1080, 1920)
    assert close(region, (80, 220, 920, 1420), tol=0.1)
    assert VERTICAL.enforce == "error"


@pytest.mark.parametrize(
    "kw",
    [
        dict(id="1bad"),
        dict(id=""),
        dict(top=-0.1),
        dict(left=1.0),
        dict(top=0.6, bottom=0.4),
        dict(left=0.5, right=0.5),
        dict(top=float("nan")),
        dict(enforce="loud"),
    ],
)
def test_safe_area_rejects_bad_values(kw):
    base = dict(id="s", top=0.1, right=0.1, bottom=0.1, left=0.1, enforce="error")
    with pytest.raises(ValueError):
        SafeArea(**{**base, **kw})


def test_declare_writes_the_safe_area_and_points_the_project_at_it():
    scene = Scene(version="auto")
    project = scene.add_project(width=100, height=100, fps="30", duration=1)
    scene.add_assets()
    VERTICAL.declare(scene, project)
    root = ET.fromstring(scene.to_bytes())
    assert [c.tag for c in root] == ["project", "safeAreas", "assets"]
    area = root.find("safeAreas/safeArea")
    assert area is not None and area.get("id") == VERTICAL.id and area.get("enforce") == "error"
    assert float(area.get("bottom", "nan")) == VERTICAL.bottom
    assert root.find("project").get("safeArea") == VERTICAL.id


# -- boxes ----------------------------------------------------------------------------------------------


def test_box_transform_rotates_every_corner():
    c, s = math.cos(math.pi / 2), math.sin(math.pi / 2)
    rotated = Box(0, 0, 10, 20).transformed((c, s, -s, c, 100, 0))
    assert close(rotated, (80, 0, 100, 10))
    assert close(Box(0, 0, 10, 20).transformed((2, 0, 0, 3, 5, 7)), (5, 7, 25, 67))


def test_box_rejects_inverted_extents():
    with pytest.raises(ValueError):
        Box(10, 0, 0, 10)


# -- path bounds ----------------------------------------------------------------------------------------


@pytest.mark.parametrize(
    "d, expected",
    [
        ("M0 0 L10 20", (0, 0, 10, 20)),
        ("m5 5 l10 0 l0 10 z", (5, 5, 15, 15)),
        ("M0 0 H30 V-4 h-40 v10", (-10, -4, 30, 6)),
        ("M0 0 10 10 20 -5", (0, -5, 20, 10)),  # implicit lineto after moveto
        ("m1 1 2 2", (1, 1, 3, 3)),  # relative implicit lineto
        ("M0 0 Q50 100 100 0", (0, 0, 100, 50)),  # the curve, not its control point
        ("M0 0 Q50 100 100 0 T200 0", (0, -50, 200, 50)),  # T reflects the control point
        ("M0 0 C0 100 100 100 100 0", (0, 0, 100, 75)),
        ("M0 0 C0 100 100 100 100 0 S200 -100 200 0", (0, -75, 200, 75)),
        ("M0 0 c0 100 100 100 100 0 s100 -100 100 0", (0, -75, 200, 75)),
        ("M0 0 A50 50 0 0 1 100 0", (0, -50, 100, 0)),
        ("M0 0 A50 50 0 0 0 100 0", (0, 0, 100, 50)),
        ("M0 0 a50 50 0 1 1 100 0", (0, -50, 100, 0)),
        ("M0 0 A10 10 0 0 1 100 0", (0, -50, 100, 0)),  # radii too small are scaled up
        ("M0 0 A0 10 0 0 1 100 0", (0, 0, 100, 0)),  # a zero radius is a straight line
        ("M0 0 A50 25 90 0 1 0 100", (0, 0, 25, 100)),  # rotated ellipse
        ("M0 0a5 5 0 1010 10", (5 - 5 * math.sqrt(2), 0, 10, 5 + 5 * math.sqrt(2))),  # compact flags, radii scaled
        ("M-.5.5L1e1 -2E0", (-0.5, -2, 10, 0.5)),
        ("M0 0 L10 0 Z M20 20 L30 30", (0, 0, 30, 30)),
        ("M0 0 L10 10 z l5 0", (0, 0, 10, 10)),  # after z the pen is back at the subpath start
    ],
)
def test_path_bounds(d, expected):
    assert close(path_bounds(d), expected, tol=1e-6)


@pytest.mark.parametrize(
    "d",
    [
        "",
        "   ",
        "L0 0",
        "M0",
        "M0 0 Q1",
        "M0 0 X1 1",
        "M0 0 A5 5 0 2 0 1 1",
        "M0 0 L1 nan",
        "M0 0 L1 1,",
        "M0 0 L--1 2",
    ],
)
def test_path_bounds_rejects_malformed_data(d):
    with pytest.raises(PathError):
        path_bounds(d)


def test_shape_bounds_pads_by_half_the_stroke():
    path = ET.fromstring('<shape shape="path" path="M0 0 L10 0" stroke="#000" strokeWidth="4" strokeJoin="round"/>')
    assert close(shape_bounds(path, (1080, 1920)), (-2, -2, 12, 2))
    mitred = ET.fromstring('<shape shape="path" path="M0 0 L10 0 L0 1" stroke="#000" strokeWidth="4"/>')
    assert close(shape_bounds(mitred, (1080, 1920)), (-8, -8, 18, 9))  # a miter reaches miterLimit × half the width
    rect = ET.fromstring('<shape shape="rect" x="40" y="50" stroke="#000" strokeWidth="2"/>')
    assert close(shape_bounds(rect, (30, 20)), (-1, -1, 31, 21))  # eval's world already holds x and y
    bare = ET.fromstring('<shape shape="ellipse" fill="#000"/>')
    assert close(shape_bounds(bare, (8, 6)), (0, 0, 8, 6))
    clear = ET.fromstring('<shape shape="rect" stroke="#00000000" strokeWidth="9"/>')
    assert close(shape_bounds(clear, (8, 6)), (0, 0, 8, 6))  # a transparent stroke draws nothing


def test_shape_bounds_rejects_an_unknown_shape():
    with pytest.raises(LayoutError):
        shape_bounds(ET.fromstring('<shape shape="star"/>'), (10, 10))


# -- crossings from one evaluated frame ----------------------------------------------------------------


def node(id, kind, world, parent=None, size=(10, 10), draw=True, opacity=1.0):
    n = {"id": id, "kind": kind, "world": list(world), "size": list(size), "draw": draw, "world_opacity": opacity}
    if parent is not None:
        n["parent"] = parent
    return n


IDENTITY = (1, 0, 0, 1, 0, 0)
GEOMETRY = {"edge-mark": Box(0, 0, 50, 10), "inner": Box(0, 0, 10, 10)}


def test_crossings_report_the_edge_and_the_overshoot():
    nodes = [
        node("overlay", "group", IDENTITY),
        node("edge-mark", "shape", (1, 0, 0, 1, 70, 5), parent=0),
        node("inner", "shape", (1, 0, 0, 1, 20, 20), parent=0),
        node("elsewhere", "shape", (1, 0, 0, 1, 500, 500)),
    ]
    found = crossings_at(nodes, GEOMETRY | {"elsewhere": Box(0, 0, 1, 1)}, Box(10, 10, 100, 100), ["overlay"], 1.5)
    assert found == [
        Crossing("overlay", "edge-mark", 1.5, "top", 5.0),
        Crossing("overlay", "edge-mark", 1.5, "right", 20.0),
    ]
    assert "edge-mark" in str(found[0]) and "1.500 s" in str(found[0])


def test_crossings_skip_hidden_and_undrawn_nodes():
    nodes = [
        node("overlay", "group", IDENTITY),
        node("edge-mark", "shape", (1, 0, 0, 1, 200, 0), parent=0, opacity=0.0),
        node("inner", "shape", (1, 0, 0, 1, 200, 0), parent=0, draw=False),
    ]
    assert crossings_at(nodes, GEOMETRY, Box(0, 0, 100, 100), ["overlay"], 0) == []


@pytest.mark.parametrize(
    "nodes, roots",
    [
        ([node("overlay", "group", IDENTITY)], ["missing"]),
        ([{"id": "overlay", "kind": "group"}], ["overlay"]),
        ([node("overlay", "group", (1, 0, 0))], ["overlay"]),
        ([node("overlay", "group", IDENTITY), node("x", "shape", IDENTITY, parent=7)], ["overlay"]),
        (
            [node("overlay", "group", IDENTITY), node("edge-mark", "shape", IDENTITY, parent=0) | {"draw": "yes"}],
            ["overlay"],
        ),
        ([node("overlay", "group", IDENTITY), node("nogeom", "shape", IDENTITY, parent=0)], ["overlay"]),
    ],
)
def test_crossings_reject_malformed_eval_output(nodes, roots):
    with pytest.raises(LayoutError):
        crossings_at(nodes, GEOMETRY, Box(0, 0, 100, 100), roots, 0)


# -- the engine audit ----------------------------------------------------------------------------------


def overlay_scene(path: Path, mark_x: float, *, rotation: float = 0, hide_after: float | None = None) -> Path:
    """A 1080 × 1920 scene with the vertical safe area and one overlay group ``mark`` at (``mark_x``, 600)."""
    scene = Scene(version="auto")
    project = scene.add_project(width=1080, height=1920, fps="10", duration=0.5, background="#FFFFFF")
    VERTICAL.declare(scene, project)
    group = scene.add_composition().add_group(id="mark", x=mark_x, y=600, rotation=rotation)
    if hide_after is not None:
        fade = group.add_animate(property="opacity", defaultInterpolation="hold")
        fade.add_key(time=0, value="1")
        fade.add_key(time=hide_after, value="0")
    group.add_shape(
        id="arc",
        shape="path",
        width=1080,
        height=1920,
        path="M0 0 Q60 -80 120 0",
        fill="#00000000",
        stroke="#111314",
        strokeWidth=6,
    )
    group.add_shape(id="plate", shape="rect", x=0, y=10, width=120, height=40, fill="#203638")
    path.write_bytes(scene.to_bytes(layout="pretty"))
    return path


@pytest.fixture
def scenes(tmp_path):
    return tmp_path


def test_check_overlays_passes_inside_the_region(scenes):
    doc = overlay_scene(scenes / "inside.scene.xml", 400)
    assert check_overlays(doc, ["mark"], engine=engine()) == []


def test_check_overlays_reports_a_crossing_graphic(scenes):
    doc = overlay_scene(scenes / "outside.scene.xml", 860)
    found = check_overlays(doc, ["mark"], engine=engine())
    edges = {(c.root, c.shape, c.edge) for c in found}
    assert ("mark", "arc", "right") in edges and ("mark", "plate", "right") in edges
    plate = next(c for c in found if c.shape == "plate")
    assert math.isclose(plate.by, 860 + 120 - VERTICAL.region(1080, 1920).x1, abs_tol=0.01)
    assert {c.time for c in found} == {0.0}  # one crossing per shape and edge: the first frame, the worst amount


def test_check_overlays_raises_when_asked(scenes):
    doc = overlay_scene(scenes / "outside.scene.xml", 860)
    with pytest.raises(LayoutError) as err:
        check_overlays(doc, ["mark"], engine=engine(), strict=True)
    assert err.value.crossings and "mark" in str(err.value)


def test_check_overlays_ignores_frames_where_the_graphic_is_hidden(scenes):
    doc = overlay_scene(scenes / "hidden.scene.xml", 860, hide_after=0)
    assert check_overlays(doc, ["mark"], engine=engine()) == []


def test_check_overlays_follows_the_world_transform(scenes):
    # At x 860 the 120-wide mark crosses the right edge (920); turned a quarter it is 50 wide and fits.
    assert check_overlays(overlay_scene(scenes / "a.scene.xml", 860), ["mark"], engine=engine())
    assert check_overlays(overlay_scene(scenes / "b.scene.xml", 860, rotation=90), ["mark"], engine=engine()) == []


def test_check_overlays_requires_a_declared_safe_area(scenes):
    scene = Scene(version="auto")
    scene.add_project(width=100, height=100, fps="10", duration=0.2)
    doc = scenes / "plain.scene.xml"
    doc.write_bytes(scene.to_bytes())
    with pytest.raises(LayoutError, match="safe area"):
        check_overlays(doc, ["mark"], engine=engine())


def test_check_overlays_reports_an_engine_failure(scenes, tmp_path):
    broken = tmp_path / "broken-engine"
    broken.write_text("#!/bin/sh\necho '{\"ok\": false}'\nexit 3\n")
    broken.chmod(0o700)
    doc = overlay_scene(scenes / "inside.scene.xml", 400)
    with pytest.raises(LayoutError, match="eval"):
        check_overlays(doc, ["mark"], engine=broken)


def test_check_overlays_rejects_an_unknown_root(scenes):
    doc = overlay_scene(scenes / "inside.scene.xml", 400)
    with pytest.raises(LayoutError, match="nope"):
        check_overlays(doc, ["nope"], engine=engine())


# -- episodes ------------------------------------------------------------------------------------------


def test_episode_declares_its_safe_area_and_the_engine_enforces_it(project, tmp_path):
    root = shutil.copytree(project, tmp_path / "project")  # the scene's asset paths are relative to it
    ep = Episode(
        EpisodeSpec(
            slug="t-safe",
            title="t",
            description="t",
            root=root,
            seed=1,
            background="#D5DFDF",
            safe_area=VERTICAL,
            signature=False,  # a layout test, not a set: no location draws the marks
        )
    )
    graphics.episode_slate(ep.cv, ep.comp, "T1", "TEST")  # at y 65: above the region's top edge
    ep.captions()
    out = ep.finish()
    assert ET.fromstring(out.read_bytes()).find("project").get("safeArea") == VERTICAL.id
    run = subprocess.run([str(engine()), "validate", "--json", str(out)], capture_output=True, text=True, check=False)
    codes = {d["code"] for f in json.loads(run.stdout)["result"]["files"] for d in f["diagnostics"]}
    assert run.returncode != 0 and "SA01" in codes


def test_episode_that_names_no_safe_area_declares_its_styles(project, tmp_path):
    """Every scene declares its safe area (ADR 0218): one that names none gets its style's."""
    ep = Episode(
        EpisodeSpec(
            slug="t-plain", title="t", description="t", root=project, seed=1, background="#D5DFDF", signature=False
        )
    )
    ep.captions()
    out = ep.finish(out=tmp_path / "plain.scene.xml", report=tmp_path / "report.json")
    root = ET.fromstring(out.read_bytes())
    assert root.find("project").get("safeArea") == VERTICAL.id
    assert root.find("safeAreas/safeArea").get("id") == VERTICAL.id


# -- failure paths -------------------------------------------------------------------------------------


@pytest.mark.parametrize(
    "xml",
    [
        '<shape id="s" shape="path" stroke="#000" strokeWidth="2"/>',  # no path data
        '<shape id="s" shape="path" path="M0 0 X" strokeWidth="1"/>',  # bad path data
        '<shape id="s" shape="rect" stroke="#000" strokeWidth="wide"/>',
        '<shape id="s" shape="rect" stroke="#000" strokeWidth="-1"/>',
        '<shape id="s" shape="path" path="M0 0" stroke="#000" strokeWidth="1" miterLimit="inf"/>',
    ],
)
def test_shape_bounds_rejects_malformed_shapes(xml):
    with pytest.raises(LayoutError):
        shape_bounds(ET.fromstring(xml), (10, 10))


def test_shape_bounds_stroke_reach():
    square = ET.fromstring(
        '<shape shape="path" path="M0 0 L10 0" stroke="#000" strokeWidth="2" strokeJoin="bevel" strokeCap="square"/>'
    )
    assert close(shape_bounds(square, (0, 0)), (-math.sqrt(2), -math.sqrt(2), 10 + math.sqrt(2), math.sqrt(2)))
    for paint in ("none", "transparent", "#0000", "#11223300"):
        clear = ET.fromstring(f'<shape shape="ellipse" stroke="{paint}" strokeWidth="9"/>')
        assert close(shape_bounds(clear, (4, 4)), (0, 0, 4, 4))
    painted = ET.fromstring('<shape shape="ellipse" stroke="url(#ink)" strokeWidth="2"/>')
    assert close(shape_bounds(painted, (4, 4)), (-1, -1, 5, 5))


def test_path_bounds_curve_corner_cases():
    assert close(path_bounds("M0 0 Q0 0 10 0"), (0, 0, 10, 0))  # no interior extremum
    assert close(path_bounds("M0 0 C0 0 0 0 0 30"), (0, 0, 0, 30))  # the derivative degenerates to a line
    assert close(path_bounds("M0 0 C10 0 -10 0 0 0"), (-2.886751, 0, 2.886751, 0), tol=1e-6)
    assert close(path_bounds("M0 0 L5 5 S10 10 20 0"), (0, 0, 20, 6.25))  # S after a line: c1 is the pen
    assert close(path_bounds("M0 0 L5 5 T10 0"), (0, 0, 10, 5))  # T after a line: a straight segment
    assert close(path_bounds("M3 4 A5 5 0 0 1 3 4"), (3, 4, 3, 4))  # same end points: nothing drawn


@pytest.mark.parametrize(
    "nodes",
    [
        ["not a node"],
        [{"kind": "group"}],
        [node("overlay", "group", IDENTITY) | {"world_opacity": None}],
        [node("overlay", "group", (1, 0, 0, 1, 0, float("inf")))],
        [node("overlay", "group", IDENTITY, parent=1), node("x", "group", IDENTITY, parent=0)],  # a cycle
    ],
)
def test_crossings_reject_more_malformed_eval_output(nodes):
    with pytest.raises(LayoutError):
        crossings_at(nodes, GEOMETRY, Box(0, 0, 100, 100), ["missing-root"], 0)


def test_crossings_reject_a_parent_cycle_even_with_a_present_root():
    nodes = [
        node("a", "group", IDENTITY, parent=1),
        node("b", "group", IDENTITY, parent=0),
        node("overlay", "group", IDENTITY),
    ]
    with pytest.raises(LayoutError, match="cycle"):
        crossings_at(nodes, GEOMETRY, Box(0, 0, 100, 100), ["overlay"], 0)


def write(path: Path, xml: str) -> Path:
    path.write_text(xml)
    return path


@pytest.mark.parametrize(
    "xml, message",
    [
        ("<scene/>", "no <project>"),
        ('<scene><project safeArea="s" width="10" height="10" fps="10" duration="1"/></scene>', "no <safeArea"),
        (
            '<scene><project safeArea="s" width="10" height="10" fps="10" duration="1"/>'
            '<safeAreas><safeArea id="s" preset="tiktok"/></safeAreas></scene>',
            "explicit",
        ),
        (
            '<scene><project safeArea="s" width="10" height="10" fps="10" duration="1"/>'
            '<safeAreas><safeArea id="s" top="0.1" right="0.1" bottom="0.1" left="0.1" enforce="loud"/></safeAreas>'
            "</scene>",
            "does not parse",
        ),
        (
            '<scene><project safeArea="s" width="ten" height="10" fps="10" duration="1"/>'
            '<safeAreas><safeArea id="s" top="0.1" right="0.1" bottom="0.1" left="0.1"/></safeAreas></scene>',
            "does not parse",
        ),
        ("<scene", "scene.xml"),
    ],
)
def test_check_overlays_rejects_malformed_documents(tmp_path, xml, message):
    doc = write(tmp_path / "bad.scene.xml", xml)
    with pytest.raises(LayoutError, match=message):
        check_overlays(doc, ["mark"], engine=tmp_path / "unused")


def fake_engine(tmp_path: Path, payload: dict) -> Path:
    """An engine whose eval prints ``payload`` as its envelope."""
    script = tmp_path / "fake-engine"
    script.write_text(f"#!/bin/sh\ncat <<'JSON'\n{json.dumps(payload)}\nJSON\n")
    script.chmod(0o700)
    return script


SHAPE_DOC = (
    '<scene><project safeArea="s" width="100" height="100" fps="1" duration="1"/>'
    '<safeAreas><safeArea id="s" top="0.1" right="0.1" bottom="0.1" left="0.1"/></safeAreas>'
    '<composition><group id="mark"><shape id="plate" shape="rect" fill="#000"/></group></composition></scene>'
)


def frame(*nodes) -> dict:
    return {"ok": True, "result": {"time": 0, "nodes": list(nodes)}}


def test_check_overlays_rejects_eval_output_the_document_does_not_explain(tmp_path):
    doc = write(tmp_path / "doc.scene.xml", SHAPE_DOC)
    group = node("mark", "group", IDENTITY)
    stranger = fake_engine(tmp_path, frame(group, node("ghost", "shape", IDENTITY, parent=0)))
    with pytest.raises(LayoutError, match="ghost"):
        check_overlays(doc, ["mark"], engine=stranger)
    sizeless = fake_engine(tmp_path, frame(group, node("plate", "shape", IDENTITY, parent=0) | {"size": None}))
    with pytest.raises(LayoutError, match="size"):
        check_overlays(doc, ["mark"], engine=sizeless)
    garbled = tmp_path / "garbled-engine"
    garbled.write_text("#!/bin/sh\necho not json\n")
    garbled.chmod(0o700)
    with pytest.raises(LayoutError, match="eval failed"):
        check_overlays(doc, ["mark"], engine=garbled)
    with pytest.raises(LayoutError, match="could not run"):
        check_overlays(doc, ["mark"], engine=tmp_path / "no-such-engine")


def test_check_overlays_keeps_the_worst_frame(tmp_path):
    doc = write(tmp_path / "doc.scene.xml", SHAPE_DOC.replace('duration="1"', 'duration="2"'))
    calls = tmp_path / "calls"
    frames = [
        frame(node("mark", "group", IDENTITY), node("plate", "shape", (1, 0, 0, 1, 85, 20), parent=0, size=(10, 10))),
        frame(node("mark", "group", IDENTITY), node("plate", "shape", (1, 0, 0, 1, 88, 20), parent=0, size=(10, 10))),
    ]
    script = tmp_path / "two-frames"
    script.write_text(
        "#!/bin/sh\n"
        f'n=$(cat {calls} 2>/dev/null || echo 0); echo $((n+1)) > {calls}\n'
        f"if [ \"$n\" = 0 ]; then echo '{json.dumps(frames[0])}'; else echo '{json.dumps(frames[1])}'; fi\n"
    )
    script.chmod(0o700)
    [crossing] = check_overlays(doc, ["mark"], engine=script)
    assert (crossing.edge, crossing.by, crossing.time) == ("right", 8.0, 1.0)


# -- symbols: eval reports instanced shapes by scoped id ----------------------------------------------

SYMBOL_DOC = (
    '<scene><project safeArea="s" width="100" height="100" fps="1" duration="1"/>'
    '<safeAreas><safeArea id="s" top="0.1" right="0.1" bottom="0.1" left="0.1"/></safeAreas>'
    '<symbols><symbol id="badge"><group id="g"><shape id="plate" shape="rect" fill="#000"/>'
    '<instance id="inner" symbol="tick"/></group></symbol>'
    '<symbol id="tick"><shape id="mark" shape="path" path="M0 0 L5 0" fill="#000"/></symbol></symbols>'
    '<composition><group id="overlay"><instance id="b1" symbol="badge"/></group>'
    '<shape id="plate" shape="rect" fill="#000"/></composition></scene>'
)


def test_check_overlays_resolves_instanced_shapes_through_their_symbols(tmp_path):
    doc = write(tmp_path / "doc.scene.xml", SYMBOL_DOC)
    nodes = frame(
        node("overlay", "group", IDENTITY),
        node("b1", "instance", IDENTITY, parent=0),
        node("b1/g", "group", IDENTITY, parent=1),
        node("b1/plate", "shape", (1, 0, 0, 1, 85, 20), parent=2, size=(10, 10)),
        node("b1/inner", "instance", (1, 0, 0, 1, 0, 0), parent=2),
        node("b1/inner/mark", "shape", (1, 0, 0, 1, 2, 50), parent=4),
    )
    found = check_overlays(doc, ["overlay"], engine=fake_engine(tmp_path, nodes))
    assert [(c.shape, c.edge, c.by) for c in found] == [("b1/inner/mark", "left", 8.0), ("b1/plate", "right", 5.0)]


@pytest.mark.parametrize("scoped", ["nobody/plate", "b1/nothing", "b1/missing/mark"])
def test_check_overlays_rejects_a_scoped_id_it_cannot_resolve(tmp_path, scoped):
    doc = write(tmp_path / "doc.scene.xml", SYMBOL_DOC)
    nodes = frame(node("overlay", "group", IDENTITY), node(scoped, "shape", IDENTITY, parent=0))
    with pytest.raises(LayoutError, match="does not declare"):
        check_overlays(doc, ["overlay"], engine=fake_engine(tmp_path, nodes))


# -- the engine, found once ----------------------------------------------------------------------------


def test_the_engine_is_the_given_path_then_the_environment_then_the_path(tmp_path, monkeypatch):
    from srstudio.layout import find_engine

    binary = tmp_path / "scene-render"
    binary.write_text("#!/bin/sh\n")
    binary.chmod(0o700)
    other = tmp_path / "other"
    other.write_text("#!/bin/sh\n")
    monkeypatch.setenv("SRSTUDIO_ENGINE", str(other))
    assert find_engine(binary) == binary
    assert find_engine() == other
    monkeypatch.delenv("SRSTUDIO_ENGINE")
    monkeypatch.setenv("PATH", str(tmp_path))
    assert find_engine() == binary


def test_no_engine_anywhere_says_how_to_supply_one(tmp_path, monkeypatch):
    from srstudio.layout import find_engine

    monkeypatch.delenv("SRSTUDIO_ENGINE", raising=False)
    monkeypatch.setenv("PATH", str(tmp_path))
    with pytest.raises(LayoutError, match="SRSTUDIO_ENGINE"):
        find_engine()
    with pytest.raises(LayoutError, match="no such engine"):
        find_engine(tmp_path / "missing")


def test_an_episode_checks_its_overlays_with_the_engine_it_finds(project, tmp_path, monkeypatch):
    monkeypatch.setenv("SRSTUDIO_ENGINE", str(engine()))
    root = shutil.copytree(project, tmp_path / "project")
    ep = Episode(
        EpisodeSpec(
            slug="t-over",
            title="t",
            description="t",
            root=root,
            seed=1,
            background="#D5DFDF",
            safe_area=VERTICAL,
            signature=False,  # a layout test, not a set: no location draws the marks
        )
    )
    graphics.episode_slate(ep.cv, ep.comp, "T1", "TEST")  # at y 65: above the region's top edge
    ep.captions()
    out = ep.finish(strict=False)
    with pytest.raises(LayoutError, match="episode-slate"):
        ep.check_overlays(out, ["episode-slate"])
