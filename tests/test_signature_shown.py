"""Both signature marks are seen for most of a new reel's running time, measured on the engine's frames (ADR 0073)."""

import json
import math
import stat
from fractions import Fraction
from pathlib import Path

import pytest

from srstudio import frame_gates, held_keys
from srstudio.frame_gates import FrameGateError, Shown, sample_times, signature_hidden, signature_shown
from srstudio.framegraph import Drawing, Frame, Node
from srstudio.releases import Release
from srstudio.social import InstagramPost

POST = InstagramPost(title="t", description="d")
BOX = (((0.0, 0.0), (100.0, 0.0), (100.0, 100.0), (0.0, 100.0)),)
DRAWN = {"cactus-leaf": Drawing(BOX, True), "code-leaf": Drawing(BOX, False), "wall": Drawing(BOX, True)}


def mark(nodes: list[Node], name: str, leaf: str, x: float, y: float, *, draw: bool = True) -> list[Node]:
    place = (1.0, 0.0, 0.0, 1.0, x, y)
    nodes.append(Node(name, None, "group", place, 1.0, draw))
    nodes.append(Node(leaf, len(nodes) - 1, "shape", place, 1.0, draw))
    return nodes


def scene_frame(cactus=(100.0, 100.0), code=(300.0, 100.0), *, front=None) -> Frame:
    nodes = mark(mark([], "sig-cactus-3", "cactus-leaf", *cactus), "sig-code", "code-leaf", *code)
    if front is not None:
        nodes.append(Node("wall", None, "shape", (1.0, 0.0, 0.0, 1.0, *front), 1.0, True))
    return Frame(0.0, 1080.0, 1920.0, tuple(nodes))


def test_marks_on_the_frame_are_seen():
    assert signature_shown([scene_frame()] * 2, DRAWN) == Shown(2, 2, 2, 2)


def test_a_mark_past_the_frame_is_not_seen_though_it_was_drawn():
    assert signature_shown([scene_frame(code=(-85.0, 2221.0))], DRAWN) == Shown(1, 1, 0, 0)


def test_a_mark_mostly_cut_by_the_frame_is_not_seen():
    assert signature_shown([scene_frame(cactus=(1020.0, 100.0))], DRAWN) == Shown(1, 0, 1, 0)


def test_a_mark_behind_something_solid_is_not_seen():
    assert signature_shown([scene_frame(front=(100.0, 100.0))], DRAWN) == Shown(1, 0, 1, 0)


def test_a_mark_a_little_covered_is_still_seen():
    assert signature_shown([scene_frame(front=(180.0, 100.0))], DRAWN) == Shown(1, 1, 1, 1)


def test_a_frame_with_no_marks_shows_neither():
    assert signature_shown([Frame(0.0, 1080.0, 1920.0, ())], DRAWN) == Shown(1, 0, 0, 0)


def test_the_marks_need_not_be_seen_in_the_same_shot_for_each_count_but_both_counts_only_together():
    frames = [scene_frame(code=(0.0, 3000.0)), scene_frame(cactus=(0.0, 3000.0))]
    assert signature_shown(frames, DRAWN) == Shown(2, 1, 1, 0)


def test_the_samples_cover_the_reel_and_close_on_its_last_frame():
    assert sample_times(1.2, fps=24) == [0.0, 0.5, 1.0, 28 / 24]  # 1.2 s is 28.8 frames: the last is frame 28
    assert sample_times(1.0, fps=30) == [0.0, 0.5, 29 / 30]
    assert sample_times(27.083333333333332, fps=24)[-2:] == [27.0, 649 / 24]  # 650 frames, to a nanosecond


@pytest.mark.parametrize("fps", [24, 30, Fraction(30000, 1001), 25])
@pytest.mark.parametrize("duration", [0.01, 1.0, 2.5, 10.05, 27.083333333333332])
def test_every_sample_is_a_frame_the_reel_renders(fps, duration):
    """Each sample is the time of the frame shown then, ``k / fps`` as the engine divides it, and the last is the
    reel's own last frame: a time between frames, or after the last, is never rendered."""
    times = sample_times(duration, fps=fps)
    last = math.ceil(Fraction(duration) * Fraction(fps) - Fraction(1, 10**9)) - 1
    frames = [round(Fraction(t) * Fraction(fps)) for t in times]
    assert times == [held_keys.frame_time(k, Fraction(fps)) for k in frames]
    assert frames == sorted(set(frames)) and frames[0] == 0 and frames[-1] == last


def test_the_samples_need_a_frame_rate():
    with pytest.raises(held_keys.HeldKeyError, match="frame rate"):
        sample_times(1.0, fps=0)


def printed(*nodes: dict) -> str:
    return json.dumps({"result": {"time": 0.0, "size": [1080, 1920], "nodes": list(nodes)}})


def project(tmp_path: Path, shown: bool) -> tuple[dict, Path, Path]:
    """A one-second reel, its marks on or off the frame, and an engine that prints its frames."""
    y = 100 if shown else 3000
    root = tmp_path / "ep" / "a-b"
    root.mkdir(parents=True)
    shapes = '<shape id="c1" shape="rect" width="9" height="9" fill="#00ff00"/>'
    shapes += '<shape id="s1" shape="rect" width="9" height="9" fill="#00ff00"/>'
    (root / "a-b.scene.xml").write_text(f'<scene><project fps="24" duration="1"/>{shapes}</scene>')
    common: dict = {"world_opacity": 1.0, "draw": True}
    cactus, code = {"world": [1, 0, 0, 1, 10, y], **common}, {"world": [1, 0, 0, 1, 50, y], **common}
    frames = printed(
        {"id": "sig-cactus", "kind": "group", "parent": None, **cactus},
        {"id": "c1", "kind": "shape", "parent": 0, **cactus},
        {"id": "sig-code", "kind": "group", "parent": None, **code},
        {"id": "s1", "kind": "shape", "parent": 2, **code},
    )
    (tmp_path / "frames.json").write_text(frames)
    engine = tmp_path / "engine"
    engine.write_text(f"#!/bin/sh\ncat {tmp_path / 'frames.json'}\n")
    engine.chmod(engine.stat().st_mode | stat.S_IEXEC)
    return {"a-b": Release("a-b", POST, video="The_Video")}, tmp_path / "ep", engine


def test_a_first_delivery_that_hides_its_marks_is_refused_by_name_with_the_measure(tmp_path):
    releases, episodes, engine = project(tmp_path, shown=False)
    [drift] = signature_hidden(releases, episodes, {"a-b": "The_Video"}, engine)
    assert drift.name == "The_Video" and "seen in 0% of the running time, the least is 50%" in drift.reason


def test_a_first_delivery_that_shows_them_passes(tmp_path):
    releases, episodes, engine = project(tmp_path, shown=True)
    assert signature_hidden(releases, episodes, {"a-b": "The_Video"}, engine) == []


def test_a_delivered_reel_is_never_measured(tmp_path):
    releases, episodes, _ = project(tmp_path, shown=False)
    assert signature_hidden(releases, episodes, {}, tmp_path / "no-engine") == []


def test_a_project_with_no_scene_has_nothing_to_measure(tmp_path):
    assert signature_hidden({"a-b": Release("a-b", POST)}, tmp_path, {"a-b": "a-b"}, tmp_path / "no-engine") == []


def test_an_engine_that_cannot_measure_the_reel_refuses_it(tmp_path):
    releases, episodes, _ = project(tmp_path, shown=True)
    with pytest.raises(FrameGateError, match="The_Video: cannot run the engine"):
        signature_hidden(releases, episodes, {"a-b": "The_Video"}, tmp_path / "no-engine")


@pytest.mark.parametrize("fps", ['', ' fps="0"', ' fps="fast"'])
def test_a_scene_with_no_frame_rate_cannot_be_sampled(tmp_path, fps):
    (tmp_path / "a-b").mkdir()
    (tmp_path / "a-b" / "a-b.scene.xml").write_text(f'<scene><project duration="1"{fps}/></scene>')
    with pytest.raises(FrameGateError, match="no frame rate"):
        signature_hidden({"a-b": Release("a-b", POST)}, tmp_path, {"a-b": "a-b"}, "engine")


def test_a_scene_with_no_duration_cannot_be_sampled(tmp_path):
    (tmp_path / "a-b").mkdir()
    (tmp_path / "a-b" / "a-b.scene.xml").write_text("<scene/>")
    with pytest.raises(FrameGateError, match="no project duration"):
        signature_hidden({"a-b": Release("a-b", POST)}, tmp_path, {"a-b": "a-b"}, "engine")


def test_the_least_is_a_majority_of_the_running_time():
    assert frame_gates.MIN_SHOWN == 0.5 and Shown(10, 5, 5, 5).share == 0.5 and Shown(0, 0, 0, 0).share == 0.0
