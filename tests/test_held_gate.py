"""The first-delivery gate on held changes that land after the frame meant to show them (ADR 0216).

The engine draws frame k at ``t = k / fps`` and shows a held change from its time on, so a change keyed for frame k
that the engine reaches a hair after ``k / fps`` shows one frame late. :func:`srstudio.held_gate.late_changes` finds
them from the scene alone, doing the engine's own arithmetic: its sequence placement, its clocks and its time bases.
The engine cases check that it names the frames ``scene-render eval`` shows stalling, and no others.
"""

from __future__ import annotations

import json
import subprocess
from pathlib import Path

import pytest
from sr_core.scene import Scene

from srstudio import Canvas, held_gate
from srstudio.frame_gates import FrameGateError
from srstudio.releases import Release
from srstudio.social import InstagramPost


def scene(body: str, fps: str = "30", duration: str = "2") -> bytes:
    return (
        '<scene version="1.1">'
        f'<project width="100" height="100" fps="{fps}" duration="{duration}" background="#ffffff"/>'
        f"<composition>{body}</composition></scene>"
    ).encode()


def held(times: list[str], base: str = "", default: str = "hold") -> str:
    """An opacity animate that turns its node on and off at ``times``, held between keys."""
    on = "".join(f'<key time="{t}" value="{i % 2}"/>' for i, t in enumerate(["0", *times]))
    timebase = f' timeBase="{base}"' if base else ""
    return f'<animate property="opacity" defaultInterpolation="{default}"{timebase}>{on}</animate>'


def box(node: str, inner: str = "", **attrs: str) -> str:
    said = "".join(f' {k}="{v}"' for k, v in attrs.items())
    shape = f'<shape id="{node}-s" shape="rect" width="10" height="10" fill="#000000"/>'
    return f'<group id="{node}"{said}>{shape}{inner}</group>'


def frames(document: bytes) -> list[int]:
    return sorted({late.frame for late in held_gate.late_changes(document)})


# -- keys -----------------------------------------------------------------------------------------------------------
def test_a_rounded_frame_time_after_its_frame_is_late():
    """``round(2 / 30, 6)`` is 0.066667, after frame 2's 0.0666...: frame 2 repeats frame 1."""
    late = held_gate.late_changes(scene(box("a", held(["0.066667"]))))
    assert [(x.frame, x.node, x.what) for x in late] == [(2, "a", "opacity key 0.066667")]
    assert 0 < late[0].by < 1e-6


@pytest.mark.parametrize(
    "time",
    [
        "0.033333",  # rounded down: before frame 1, shown on it
        repr(2 / 30),  # the engine's own frame time: shown on frame 2
        "0.05",  # half a frame before frame 2: what a new canvas writes
        "0.07",  # between frames 2 and 3, meant for neither: shown on 3 as written
    ],
)
def test_a_key_at_or_before_its_frame_is_on_time(time):
    assert frames(scene(box("a", held([time])))) == []


def test_an_interpolated_key_is_not_a_held_change():
    assert frames(scene(box("a", held(["0.066667"], default="linear")))) == []


def test_a_key_that_changes_nothing_is_not_a_held_change():
    keys = '<key time="0" value="1"/><key time="0.066667" value="1"/>'
    body = box("a", f'<animate property="opacity" defaultInterpolation="hold">{keys}</animate>')
    assert frames(scene(body)) == []


def test_a_hold_named_on_the_key_before_holds_the_change():
    keys = '<key time="0" value="0" interpolation="hold"/><key time="0.066667" value="1"/><key time="1" value="0"/>'
    body = box("a", f'<animate property="opacity" defaultInterpolation="linear">{keys}</animate>')
    assert frames(scene(body)) == [2]


def test_a_change_after_the_last_frame_is_never_shown_and_never_late():
    assert frames(scene(box("a", held(["2.000001"])))) == []


def test_a_local_key_is_timed_from_its_node_start():
    body = box("a", held(["0.066667"], base="local"), start="1", end="2")
    assert frames(scene(body)) == [32]


def test_an_exact_key_under_a_clock_offset_lands_late():
    """Under ``timeOffset="1.1"`` frame 35 reads local ``0.06666666666666665``, before an exact ``2 / 30`` key."""
    body = f'<group id="shot" start="1.1" end="2" timeOffset="1.1">{box("a", held([repr(2 / 30)]))}</group>'
    assert frames(scene(body)) == [35]


def test_a_centred_key_under_a_clock_offset_is_on_time():
    body = f'<group id="shot" start="1.1" end="2" timeOffset="1.1">{box("a", held(["0.05"]))}</group>'
    assert frames(scene(body)) == []


# -- windows --------------------------------------------------------------------------------------------------------
@pytest.mark.parametrize("edge", ["start", "end"])
def test_a_window_edge_after_its_frame_is_late(edge):
    attrs = {"start": "0.066667", "end": "1"} if edge == "start" else {"start": "0", "end": "0.066667"}
    late = held_gate.late_changes(scene(box("a", **attrs)))
    assert [(x.frame, x.node, x.what) for x in late] == [(2, "a", f"{edge} 0.066667")]


def test_a_sequence_places_its_shots_end_to_end():
    """A shot's local keys run from where the sequence puts it: shot b starts at 1.0 and keys a frame late there."""
    shots = box("a", end="1") + box("b", held(["0.066667"], base="local"), end="1")
    assert frames(scene(f'<sequence id="shots">{shots}</sequence>')) == [32]


def test_a_shot_off_the_frame_grid_moves_its_keys_off_it():
    """Keys meant for a shot's own frames land between the reel's frames when the shot starts between them."""
    shots = box("a", end="1.0125") + box("b", held(["0.066667"], base="local"), end="0.9")
    assert frames(scene(f'<sequence id="shots">{shots}</sequence>')) == []


def test_a_key_off_its_shots_grid_that_sums_to_a_frame_time_is_late():
    """Shot b starts at 0.02 and keys 0.28 on its own clock, neither on a frame, but together frame 9's 0.3; the
    engine reads frame 9 at local ``0.3 - 0.02 = 0.27999999999999997``, before the key, and shows it on frame 10."""
    shots = box("a", end="0.02") + box("b", held(["0.28"], base="local"), end="1")
    assert frames(scene(f'<sequence id="shots">{shots}</sequence>')) == [9]


def test_a_key_off_its_shots_grid_that_lands_just_after_a_frame_is_not_meant_for_it():
    """0.021 + 0.28 lands 0.001 s after frame 9: a change keyed after the frame, shown on the next one as written."""
    shots = box("a", end="0.021") + box("b", held(["0.28"], base="local"), end="1")
    assert frames(scene(f'<sequence id="shots">{shots}</sequence>')) == []


def test_a_cut_just_after_its_frame_is_late_on_both_sides():
    shots = box("a", end="1.033334") + box("b", end="0.9125")
    late = held_gate.late_changes(scene(f'<sequence id="shots">{shots}</sequence>'))
    assert sorted((x.frame, x.node, x.what) for x in late) == [(31, "a", "end 1.033334"), (31, "b", "start 1.033334")]


# -- what the gate cannot read --------------------------------------------------------------------------------------
@pytest.mark.parametrize(
    "body",
    [
        box("a", held(["0.5"], base="normalized"), start="0", end="1"),
        f'<sequence id="s">{box("a", end="1", startMarker="m")}</sequence>',
        f'<group id="g" timeScale="0">{box("a")}</group>',
    ],
    ids=["normalized time", "a start marker", "a stopped clock"],
)
def test_a_timing_the_gate_cannot_follow_is_refused(body):
    with pytest.raises(FrameGateError, match="held"):
        held_gate.late_changes(scene(body))


@pytest.mark.parametrize(
    "document",
    [b"<scene", b"<scene/>", scene("").replace(b' fps="30"', b""), scene("").replace(b'"30"', b'"0"')],
    ids=["not xml", "no project", "no frame rate", "a zero frame rate"],
)
def test_a_scene_the_gate_cannot_read_is_refused(document):
    with pytest.raises(FrameGateError):
        held_gate.late_changes(document)


# -- a canvas -------------------------------------------------------------------------------------------------------
def gated(held_frames: bool, at: float = 0.0) -> bytes:
    """Thirty drawings gated one frame each, on the composition clock or under an ``at`` second clock offset."""
    scene = Scene(version="auto")
    scene.add_project(width=360, height=640, fps="30", duration=3, background="#FFFFFF")
    cv = Canvas(scene, font_asset=None, held_frames=held_frames)
    shot = cv.group(cv.comp, "shot", start=at, end=at + 1.5, timeOffset=at) if at else cv.comp
    for k in range(30):
        g = cv.group(shot, f"body-frame-{k:04d}", opacity=0.0)
        cv.rect(g, 0, 0, 10, 10, "#000000")
        cv.gate(g, [(k / 30, (k + 1) / 30)])
    return cv.scene.to_bytes(layout="pretty")


def test_a_published_canvas_is_late_where_its_keys_round_up():
    assert frames(gated(False)) == [k for k in range(1, 31) if k % 3 == 2]


@pytest.mark.parametrize("at", [0.0, 1.1])
def test_a_new_canvas_is_never_late(at):
    assert frames(gated(True, at)) == []


# -- the gate -------------------------------------------------------------------------------------------------------
def release(slug: str) -> Release:
    return Release(slug, InstagramPost(title="t", description="d"), video=f"{slug}-video")


def project(root: Path, slug: str, document: bytes) -> None:
    (root / slug).mkdir(parents=True)
    (root / slug / f"{slug}.scene.xml").write_bytes(document)


def test_a_first_delivery_with_a_late_change_is_refused(tmp_path):
    project(tmp_path, "late", scene(box("a", held(["0.066667", "0.166667"]))))
    project(tmp_path, "fine", scene(box("a", held(["0.05"]))))
    releases = {s: release(s) for s in ("late", "fine")}
    drift = held_gate.late_defects(releases, tmp_path, {"late": "late-video", "fine": "fine-video"})
    assert [d.name for d in drift] == ["late-video"]
    assert "frames 2, 5" in drift[0].reason and "held_frames=True" in drift[0].reason


def test_a_delivered_reel_is_not_read(tmp_path):
    project(tmp_path, "late", scene(box("a", held(["0.066667"]))))
    assert held_gate.late_defects({"late": release("late")}, tmp_path, {}) == []


def test_a_project_with_no_scene_has_nothing_to_judge(tmp_path):
    assert held_gate.late_defects({"gone": release("gone")}, tmp_path, {"gone": "gone-video"}) == []


def test_a_first_delivery_the_gate_cannot_read_is_refused(tmp_path):
    project(tmp_path, "odd", scene(box("a", held(["0.5"], base="normalized"), end="1")))
    drift = held_gate.late_defects({"odd": release("odd")}, tmp_path, {"odd": "odd-video"})
    assert [d.name for d in drift] == ["odd-video"] and "cannot" in drift[0].reason


# -- the engine agrees ----------------------------------------------------------------------------------------------
def _state(scene: Path, *at: str) -> dict:
    run = subprocess.run(
        [*at[:1], "eval", scene.name, *at[1:], "--format", "json"], cwd=scene.parent, capture_output=True, text=True
    )
    nodes = json.loads(run.stdout)["result"]["nodes"]
    return {n["id"]: round(n.get("world_opacity", 0), 3) for n in nodes if n.get("draw") and n.get("id")}


ENGINE_CASES = {
    "composition": box("a", held(["0.066667", "0.166667", "0.2", "0.433333"])),
    "local": box("a", held(["0.066667", "0.1"], base="local"), start="1", end="2"),
    "offset": f'<group id="shot" start="1.1" end="2" timeOffset="1.1">{box("a", held([repr(2 / 30), "0.15"]))}</group>',
    "sequence": '<sequence id="shots">'
    + box("p", end="1.033334")
    + box("q", held(["0.066667"], base="local"), end="0.3")
    + box("r", held(["0.066667"], base="local"), end="0.5")
    + "</sequence>",
    "windows": box("w", start="0.066667", end="0.766667"),
    "float sum": '<sequence id="shots">'
    + box("p", end="0.02")
    + box("q", held(["0.28", "0.68"], base="local"), end="1.5")
    + "</sequence>",
}


@pytest.mark.parametrize("case", ENGINE_CASES)
def test_the_late_frames_are_the_ones_the_engine_shows_stalling(tmp_path, scene_render, case):
    """Every frame the gate names repeats the frame before on ``eval --frame``, against ``eval --time`` a hair after
    the frame's time, and no other frame does."""
    path = tmp_path / "case.scene.xml"
    path.write_bytes(scene(ENGINE_CASES[case]))
    engine = str(scene_render)
    stalled = [
        k
        for k in range(60)
        if _state(path, engine, f"--frame={k}") != _state(path, engine, f"--time={k / 30 + 2e-6!r}")
    ]
    assert stalled  # each case holds a stall
    assert frames(path.read_bytes()) == stalled
