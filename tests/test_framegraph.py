"""The engine's frame and the scene's drawings, read together: where things land and what stands in front of them."""

import json
import stat
from pathlib import Path

import numpy as np
import pytest

from srstudio import framegraph
from srstudio.framegraph import (
    Box,
    Drawing,
    Frame,
    FrameGraphError,
    Node,
    drawings,
    evaluate,
    fill,
    flatten,
    read_frame,
)

SQUARE = (((0.0, 0.0), (10.0, 0.0), (10.0, 10.0), (0.0, 10.0)),)


def node(name: str, parent: int | None = None, x: float = 0.0, y: float = 0.0, *, scale: float = 1.0, kind="shape"):
    return Node(name, parent, kind, (scale, 0.0, 0.0, scale, x, y), 1.0, True)


def test_a_path_is_flattened_with_its_curves_in_straight_pieces():
    [line] = flatten("M 0 0 L 10 0 Q 20 0 20 10 Z")
    assert line[:2] == ((0.0, 0.0), (10.0, 0.0)) and line[-1] == (20.0, 10.0) and len(line) == 10


def test_relative_commands_and_implied_lines_follow_the_pen():
    [line] = flatten("m 1 1 l 2 0 3 0 v 4 h -5")
    assert line == ((1.0, 1.0), (3.0, 1.0), (6.0, 1.0), (6.0, 5.0), (1.0, 5.0))


def test_smooth_curves_reflect_the_last_control_point():
    [line] = flatten("M 0 0 Q 5 10 10 0 T 20 0")
    assert line[-1] == (20.0, 0.0) and min(y for _, y in line[9:]) < -4  # the reflected half bends the other way


def test_an_arc_stays_on_its_circle():
    [line] = flatten("M 0 0 A 10 10 0 0 1 20 0")
    assert line[-1] == pytest.approx((20.0, 0.0)) and min(y for _, y in line) == pytest.approx(-10.0, abs=0.1)


def test_each_subpath_stands_alone():
    assert len(flatten("M 0 0 L 1 0 L 1 1 Z M 5 5 L 6 5 L 6 6 Z")) == 2


def test_a_path_that_cannot_be_read_is_refused_not_measured_in_part():
    with pytest.raises(FrameGraphError, match="cannot be measured"):
        flatten("M 0 0 B 3 3")
    with pytest.raises(FrameGraphError, match="cannot be measured"):
        flatten("M 0 0 L 3")


def test_the_drawings_of_a_scene_say_what_hides_what_is_behind_them():
    found = drawings(
        b'<scene><assets><text id="t" width="30" height="20"/></assets>'
        b'<shape id="r" shape="rect" width="4" height="5" fill="#123456"/>'
        b'<shape id="e" shape="ellipse" width="4" height="4" fill="#12345680"/>'
        b'<shape id="p" shape="path" path="M 0 0 L 1 1" fill="#00000000"/>'
        b'<layer id="l" asset="t"/></scene>'
    )
    assert found["r"] == Drawing((((0.0, 0.0), (4.0, 0.0), (4.0, 5.0), (0.0, 5.0)),), True)
    assert (found["e"].solid, found["p"].solid, found["l"].solid) == (False, False, False)
    assert found["l"].outlines[0][2] == (30.0, 20.0)


def test_a_gradient_hides_what_is_behind_it_only_where_every_stop_is_opaque():
    found = drawings(
        b'<scene><linearGradient id="wall"><stop color="#102030"/><stop color="#405060"/></linearGradient>'
        b'<radialGradient id="lamp"><stop color="#ffffff40"/><stop color="#ffffff00"/></radialGradient>'
        b'<shape id="w" shape="rect" width="1" height="1" fill="url(#wall)"/>'
        b'<shape id="l" shape="rect" width="1" height="1" fill="url(#lamp)"/>'
        b'<shape id="u" shape="rect" width="1" height="1" fill="url(#unknown)"/>'
        b'<shape id="b" shape="rect" width="1" height="1" fill="#102030" blendMode="multiply"/>'
        b'<group blend="multiply"><group>'
        b'<shape id="g" shape="rect" width="1" height="1" fill="#102030"/>'
        b"</group></group></scene>"
    )
    assert [found[k].solid for k in "wlubg"] == [True, False, False, False, False]


def test_a_shape_kind_no_one_can_measure_is_refused():
    with pytest.raises(FrameGraphError, match="cannot be measured"):
        drawings(b'<scene><shape id="s" shape="star"/></scene>')
    with pytest.raises(FrameGraphError, match="not a scene"):
        drawings(b"<scene")


def test_fill_is_inside_the_outline_by_the_even_odd_rule():
    ring = (((0.0, 0.0), (10.0, 0.0), (10.0, 10.0), (0.0, 10.0)), ((3.0, 3.0), (7.0, 3.0), (7.0, 7.0), (3.0, 7.0)))
    mask = fill(ring, Box(0, 0, 10, 10), 1.0)
    assert mask.shape == (10, 10) and mask[1, 1] and not mask[5, 5] and mask.sum() == 100 - 16


def test_fill_reads_the_frame_at_the_scale_asked():
    mask = fill(SQUARE, Box(-10, -10, 10, 10), 2.0)
    assert mask.shape == (10, 10) and mask.sum() == 25 and mask[5:, 5:].all()


def frame(*nodes: Node) -> Frame:
    return Frame(1.0, 100.0, 200.0, nodes)


DRAWN = {"s": Drawing(SQUARE, True), "t": Drawing(SQUARE, True), "thin": Drawing(SQUARE, False)}


def test_a_group_lands_where_its_children_are_drawn_by_the_world_matrices():
    f = frame(node("g", kind="group"), node("s", 0, 5, 7, scale=2.0))
    assert f.box(0, DRAWN) == Box(5, 7, 25, 27)


def test_a_node_not_drawn_or_at_no_opacity_lands_nowhere():
    gone = Node("s", None, "shape", (1.0, 0.0, 0.0, 1.0, 0.0, 0.0), 1.0, False)
    clear = Node("s", None, "shape", (1.0, 0.0, 0.0, 1.0, 0.0, 0.0), 0.0, True)
    assert frame(gone).box(0, DRAWN) is None and frame(clear).box(0, DRAWN) is None


def test_only_a_solid_shape_drawn_after_stands_in_front():
    after = frame(node("s"), node("t", None, 5, 0))
    assert after.in_front([0], DRAWN, Box(0, 0, 10, 10), 1.0)[:, 5:].all()
    assert not after.in_front([1], DRAWN, Box(0, 0, 10, 10), 1.0).any()  # the square is behind it
    thin = frame(node("s"), node("thin"))
    assert not thin.in_front([0], DRAWN, Box(0, 0, 10, 10), 1.0).any()


def printed(time=1.0, nodes=None) -> str:
    nodes = nodes or [
        {"id": "g", "kind": "group", "world": [1, 0, 0, 1, 0, 0], "world_opacity": 1.0, "draw": True, "parent": None}
    ]
    return json.dumps({"result": {"time": time, "size": [1080, 1920], "nodes": nodes}})


def test_a_frame_is_read_from_what_the_engine_prints():
    read = read_frame(printed())
    assert (read.time, read.width, read.height) == (1.0, 1080.0, 1920.0) and read.nodes[0].id == "g"


@pytest.mark.parametrize("bad", ["not json", "{}", '{"result": {"size": [1], "nodes": []}}'])
def test_what_is_not_a_frame_is_refused(bad):
    with pytest.raises(FrameGraphError, match="not a FrameGraph"):
        read_frame(bad)


def fake_engine(tmp_path: Path, body: str) -> Path:
    engine = tmp_path / "engine"
    engine.write_text(f"#!/bin/sh\n{body}\n")
    engine.chmod(engine.stat().st_mode | stat.S_IEXEC)
    return engine


def test_each_time_is_one_frame_from_the_scenes_folder(tmp_path):
    (tmp_path / "out").write_text(printed())
    engine = fake_engine(tmp_path, 'test -f s.scene.xml && case "$4" in 0.500000|1.000000) cat ../out;; esac')
    project = tmp_path / "p"
    project.mkdir()
    (project / "s.scene.xml").write_text("<scene/>")
    assert len(list(evaluate(engine, project / "s.scene.xml", [0.5, 1.0]))) == 2


def test_an_engine_that_refuses_a_frame_is_a_typed_error(tmp_path):
    engine = fake_engine(tmp_path, "echo refused; exit 2")
    with pytest.raises(FrameGraphError, match="at 0.000 s: refused"):
        list(evaluate(engine, tmp_path / "s.scene.xml", [0.0]))
    with pytest.raises(FrameGraphError, match="cannot run the engine"):
        list(evaluate(tmp_path / "no-engine", tmp_path / "s.scene.xml", [0.0]))


def test_the_module_says_what_it_does_not_read():
    assert "Effects are not read" in (framegraph.__doc__ or "")
    assert np.array_equal(fill((), Box(0, 0, 2, 2), 1.0), np.zeros((2, 2), dtype=bool))
