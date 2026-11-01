"""What a figure and a set look like on the frame, measured on the engine's frames (ADR 0073).

The minimal frames carry the geometry measured on the reels the full-size review caught: the hamster of one-more-taste,
the barista of headphones, Priya of book-a-table on her stool, the head of seat-belt-sign and the lawn of the-tongs.
"""

import json
import math
import stat
from pathlib import Path

import pytest

from srstudio import figure_record
from srstudio.figure_gates import COVER_DEPTH, Cut, cut_of, figure_defects, figures_on, head_offset, run_out
from srstudio.figure_record import Figure
from srstudio.frame_gates import FrameGateError
from srstudio.framegraph import Drawing, Frame, Node
from srstudio.releases import Release
from srstudio.social import InstagramPost

POST = InstagramPost(title="t", description="d")
PLACE = (1.0, 0.0, 0.0, 1.0, 0.0, 0.0)


def box(left: float, top: float, right: float, bottom: float) -> tuple[tuple[float, float], ...]:
    return ((left, top), (right, top), (right, bottom), (left, bottom))


def circle(x: float, y: float, r: float) -> tuple[tuple[float, float], ...]:
    return tuple((x + r * math.cos(i * math.tau / 90), y + r * math.sin(i * math.tau / 90)) for i in range(90))


def frame(*shapes: tuple[str, tuple]) -> tuple[Frame, dict[str, Drawing]]:
    """A 1080x1920 frame of ``shapes`` in draw order, each placed where its outline says."""
    nodes = tuple(Node(name, None, "shape", PLACE, 1.0, True) for name, _ in shapes)
    return Frame(1.0, 1080.0, 1920.0, nodes), {name: Drawing((outline,), True) for name, outline in shapes}


HAMSTER = box(300, 841, 789, 1406)


def test_the_hamster_s_flat_cut_above_the_counter_is_refused():
    shown, drawn = frame(("body", HAMSTER), ("counter", box(0, 1500, 1080, 1920)))
    cut = cut_of(shown, [0], drawn)
    assert cut is not None and cut.refused
    assert (cut.width, cut.y, cut.hidden, cut.depth) == (489.0, 1406.0, 0.0, 0.0)


def test_a_cut_is_hidden_behind_a_deep_counter():
    shown, drawn = frame(("body", HAMSTER), ("counter", box(0, 1380, 1080, 1920)))
    assert not cut_of(shown, [0], drawn).refused


def test_a_counter_that_hides_only_part_of_the_cut_leaves_it_showing():  # the fox of the-noise, half behind the car
    shown, drawn = frame(("body", box(100, 852, 412, 1368)), ("car", box(260, 1300, 1000, 1700)))
    cut = cut_of(shown, [0], drawn)
    assert cut.refused and cut.hidden == pytest.approx(0.5, abs=0.03)


def test_priya_behind_the_seat_of_her_stool_is_a_bust_on_a_stool():
    shown, drawn = frame(("body", box(300, 953, 660, 1753)), ("seat", box(280, 1740, 680, 1777)))
    cut = cut_of(shown, [0], drawn)
    assert cut.hidden == 1.0 and cut.depth < COVER_DEPTH and cut.refused


def test_a_figure_sits_on_the_ledge_drawn_in_front_of_it():  # the fixed cat of call-your-mother
    shown, drawn = frame(("body", box(100, 719, 673, 1330)), ("ledge", box(0, 1335, 1080, 1920)))
    cut = cut_of(shown, [0], drawn)
    assert cut.hidden == 1.0 and not cut.refused


def test_a_figure_sits_on_the_ledge_drawn_behind_it():
    shown, drawn = frame(("ledge", box(0, 1335, 1080, 1920)), ("body", box(100, 719, 673, 1330)))
    assert not cut_of(shown, [1], drawn).refused


def test_the_cat_s_gap_above_the_table_is_no_ledge():  # the 25 px of call-your-mother
    for order in (((1, 0), [1]), ((0, 1), [0])):
        shapes = [("body", box(100, 494, 856, 1306)), ("table", box(0, 1331, 1080, 1920))]
        shown, drawn = frame(*(shapes[i] for i in order[0]))
        assert cut_of(shown, order[1], drawn).refused


def test_legs_behind_a_hem_hold_it():  # Deb in book-a-table, the fix
    body = ("body", box(500, 894, 890, 1621))
    legs = [("far", box(616, 1559, 690, 1868)), ("near", box(790, 1559, 864, 1868))]
    shown, drawn = frame(("floor", box(-22, 1584, 1102, 1958)), *legs, body)
    cut = cut_of(shown, [3], drawn)
    assert cut.held == pytest.approx(148 / 390, abs=0.02) and not cut.refused


def test_a_floor_that_starts_above_a_hem_does_not_hold_it():  # Deb in book-a-table, the defect
    shown, drawn = frame(("floor", box(-22, 1584, 1102, 1958)), ("body", box(500, 894, 890, 1621)))
    cut = cut_of(shown, [1], drawn)
    assert cut.held == 0.0 and cut.refused


def test_things_on_a_shelf_behind_a_hem_do_not_hold_it():  # the barista of headphones
    shown, drawn = frame(("book", box(520, 1180, 560, 1300)), ("body", box(504, 826, 627, 1256)))
    cut = cut_of(shown, [1], drawn)
    assert cut.held == 0.0 and cut.refused


def test_the_frame_s_lower_edge_crops_a_figure():
    shown, drawn = frame(("body", box(300, 1000, 800, 1960)))
    assert cut_of(shown, [0], drawn) is None


def test_a_figure_past_the_frame_measures_nothing():
    shown, drawn = frame(("body", box(-500, 1000, -100, 1400)))
    assert cut_of(shown, [0], drawn) is None


def test_a_sole_is_flat_and_a_figure_stands_on_it():  # Rosa's 144 px shoe on a 1471 px figure
    shown, drawn = frame(("leg", box(400, 300, 440, 1700)), ("shoe", box(400, 1700, 544, 1771)))
    cut = cut_of(shown, [0, 1], drawn)
    assert cut.width == pytest.approx(144, abs=3) and not cut.refused


def test_a_round_head_is_not_a_cut_however_wide_its_chin():
    shown, drawn = frame(("head", circle(540, 900, 180)))
    cut = cut_of(shown, [0], drawn)
    assert cut.width >= 90 and cut.bow >= 3 and not cut.refused


def test_a_leaning_cut_is_still_a_cut():
    shown, drawn = frame(("body", ((100, 850), (412, 850), (412, 1371), (100, 1365))))
    assert cut_of(shown, [0], drawn).refused


def test_a_short_cut_is_nothing_the_frame_can_tell_from_a_foot():
    assert not Cut(89.0, 200.0, 900.0, 0.0, 0.0, 0.0).refused


def test_shapes_that_do_not_hide_what_is_behind_them_are_no_body():
    shown, _ = frame(("body", HAMSTER))
    assert cut_of(shown, [0], {"body": Drawing((HAMSTER,), False)}) is None


def group_frame() -> Frame:
    names = [("milo", None), ("milo-body", 0), ("milo-head", 0), ("milo-eye", 2), ("ann", None), ("ann-body", 4)]
    return Frame(0.0, 1080.0, 1920.0, tuple(Node(n, p, "shape", PLACE, 1.0, True) for n, p in names))


def test_a_part_called_for_the_body_and_again_inside_it_is_one_figure():
    figures = [Figure("barista", ("milo-body",)), Figure("barista", ("milo-eye",)), Figure("rosa", ("ann-body",))]
    assert figures_on(group_frame(), figures) == [("barista", [1, 3]), ("rosa", [5])]


def test_two_figures_of_one_part_in_one_group_stay_two():
    figures = [Figure("toon-fox", ("milo-body",)), Figure("toon-fox", ("milo-head",))]
    assert figures_on(group_frame(), figures) == [("toon-fox", [1]), ("toon-fox", [2])]


def test_a_figure_not_on_the_frame_is_left_out():
    assert figures_on(group_frame(), [Figure("rosa", ("gone",))]) == []


def rig(head: tuple[float, float], neck=(722.0, 940.0), hip=(765.0, 1360.0), radius=133.0):
    names = {"torso": ((*neck,), (*hip,)), "head": circle(*head, radius)}
    nodes = tuple(Node(name, None, "shape", PLACE, 1.0, True) for name in names)
    drawn = {"torso": Drawing((names["torso"],), False), "head": Drawing((names["head"],), True, ellipse=True)}
    return Frame(0.0, 1080.0, 1920.0, nodes), drawn


def test_the_head_of_seat_belt_sign_sits_off_its_neck():
    shown, drawn = rig((591.0, 838.0))
    assert head_offset(shown, [0, 1], drawn) == pytest.approx(0.9, abs=0.1)


def test_a_head_over_its_torso_is_on_its_neck():
    shown, drawn = rig((706.2, 785.0))
    assert head_offset(shown, [0, 1], drawn) == pytest.approx(0.0, abs=0.01)


def test_a_rig_with_no_torso_on_the_frame_measures_nothing():
    shown, drawn = rig((591.0, 838.0))
    assert head_offset(shown, [1], drawn) is None


def test_the_lawn_of_the_tongs_runs_out_above_the_frame_s_bottom():
    shown, drawn = frame(("set", box(-100, -100, 1180, 1810)))
    found = run_out(shown, drawn)
    assert found is not None and found.edge == "bottom" and found.share == 1.0


def test_a_set_past_every_edge_has_not_run_out():
    shown, drawn = frame(("set", box(-100, -100, 1180, 2100)))
    assert run_out(shown, drawn) is None


def test_a_frame_with_no_set_shows_the_background_on_every_edge():  # free-shipping's flat colour
    shown, drawn = frame(("desk", box(300, 900, 800, 1400)))
    assert run_out(shown, drawn) is None


def printed(*nodes: dict) -> str:
    return json.dumps({"result": {"time": 0.0, "size": [1080, 1920], "nodes": list(nodes)}})


def project(
    tmp_path: Path, bottom: int = 1406, *, record: bool = True, top: int = -10, x: int = 300
) -> tuple[dict, Path, Path]:
    """A one-second reel of one figure ending at ``bottom``, and an engine that prints its frame."""
    root = tmp_path / "ep" / "a-b"
    root.mkdir(parents=True)
    shapes = '<shape id="bg" shape="rect" width="1200" height="2100" fill="#101010"/>'
    shapes += f'<shape id="k1" shape="rect" width="489" height="{bottom - 841}" fill="#ff0000"/>'
    (root / "a-b.scene.xml").write_text(f'<scene><project duration="1"/>{shapes}</scene>')
    if record:
        figure_record.write(root, [Figure("toon-hamster", ("k1",))])
    common: dict = {"kind": "shape", "parent": None, "world_opacity": 1.0, "draw": True}
    (tmp_path / "frames.json").write_text(
        printed(
            {"id": "bg", "world": [1, 0, 0, 1, -10, top], **common},
            {"id": "k1", "world": [1, 0, 0, 1, x, 841], **common},
        )
    )
    engine = tmp_path / "engine"
    engine.write_text(f"#!/bin/sh\ncat {tmp_path / 'frames.json'}\n")
    engine.chmod(engine.stat().st_mode | stat.S_IEXEC)
    return {"a-b": Release("a-b", POST, video="The_Video")}, tmp_path / "ep", engine


def test_a_first_delivery_showing_a_cut_figure_is_refused_with_the_measure(tmp_path):
    releases, episodes, engine = project(tmp_path)
    [drift] = figure_defects(releases, episodes, {"a-b": "The_Video"}, engine)
    assert drift.name == "The_Video"
    assert "toon-hamster ends in a straight cut 489 px wide at y=1406 from 0 s" in drift.reason


def test_a_first_delivery_cropped_by_the_frame_passes(tmp_path):
    releases, episodes, engine = project(tmp_path, bottom=1960)
    assert figure_defects(releases, episodes, {"a-b": "The_Video"}, engine) == []


def test_a_set_that_runs_out_is_refused_by_name(tmp_path):
    releases, episodes, engine = project(tmp_path, top=-400, x=-2000)
    [drift] = figure_defects(releases, episodes, {"a-b": "The_Video"}, engine)
    assert "the set runs out at the bottom of the frame from 0 s" in drift.reason


def test_a_delivered_reel_is_never_measured(tmp_path):
    releases, episodes, _ = project(tmp_path)
    assert figure_defects(releases, episodes, {}, tmp_path / "no-engine") == []


def test_a_new_reel_with_no_record_was_not_built_by_the_command(tmp_path):
    releases, episodes, engine = project(tmp_path, record=False)
    [drift] = figure_defects(releases, episodes, {"a-b": "The_Video"}, engine)
    assert drift.name == "The_Video" and "figures.json is missing: build it with srstudio build" in drift.reason


def test_a_project_with_no_scene_has_nothing_to_measure(tmp_path):
    assert figure_defects({"a-b": Release("a-b", POST)}, tmp_path, {"a-b": "a-b"}, tmp_path / "no-engine") == []


def test_an_engine_that_cannot_measure_the_reel_refuses_it(tmp_path):
    releases, episodes, _ = project(tmp_path)
    with pytest.raises(FrameGateError, match="The_Video: cannot run the engine"):
        figure_defects(releases, episodes, {"a-b": "The_Video"}, tmp_path / "no-engine")
