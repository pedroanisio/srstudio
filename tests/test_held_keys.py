"""Held changes are keyed half a frame before the frame that first shows them (ADR 0216).

The engine draws frame k at t = k / fps and shows a held key from its time on. A held change keyed at a frame's own
time is one rounding away from a stall: ``round(2 / 30, 6)`` is after frame 2, so frame 2 repeats frame 1, and a
clock offset does the same by one unit in the last place. These tests feed every path that writes held keys on a
frame grid and refuse any key closer to a frame's sample time than a quarter of a frame.
"""

from __future__ import annotations

import json
import math
import os
import shutil
import subprocess
from fractions import Fraction
from pathlib import Path

import pytest
from sr_core.scene import Scene

from srstudio import Canvas, acting, body, gaze, held_keys, stick_door
from srstudio.face_blends import FaceBlend, FacePose, FaceTrack, segments
from srstudio.limbs import Camera, Frame, Vec3
from srstudio.stick import Face
from srstudio.toon import Pose

ENGINE = os.environ.get("SRSTUDIO_ENGINE") or shutil.which("scene-render")
MARGIN = 0.25  # of a frame: the least distance a held key keeps from any frame's sample time


def off_frame(times, fps: float) -> list[float]:
    """The key times in ``times`` (after 0) that sit within :data:`MARGIN` of a frame's sample time."""
    return [t for t in times if t > 0 and abs(t * fps - round(t * fps)) < MARGIN]


def walking() -> body.BodyPlan:
    return body.compile_body(
        body.BodyScore(
            duration=4,
            roots=(
                body.BodyKey(0, Frame(Vec3(0, -0.88, 0))),
                body.BodyKey(1, Frame(Vec3(-0.15, -0.88, 0))),
                body.BodyKey(2.5, Frame(Vec3(-0.15, -0.88, 0))),
                body.BodyKey(4, Frame(Vec3(0, -0.88, 0.1))),
            ),
            stance=(
                body.FootAnchor("left", Frame(Vec3(-0.12, 0, 0))),
                body.FootAnchor("right", Frame(Vec3(0.12, 0, 0))),
            ),
            steps=(body.Step("right", 1.25, 2.25, Frame(Vec3(0.12, 0, 0.2))),),
        )
    )


def body_canvas(fps: int = 30) -> Canvas:
    scene = Scene(version="auto")
    scene.add_project(width=360, height=640, fps=str(fps), duration=2, background="#FFFFFF")
    return Canvas(scene, font_asset=None)


def body_frames(fps: int = 30, drawn: int = 30, at: float = 0.0):
    cv = body_canvas(fps)
    group = walking().window(0, 2).place(cv, cv.comp, at=at, camera=Camera(origin=(180, 600), scale=300), fps=drawn)
    return cv, [g for g in group.iter("group") if g.id.startswith("body-frame")]


# -- the helper ---------------------------------------------------------------------------------------------------


@pytest.mark.parametrize("fps", [24, 25, 30, 60])
def test_a_change_meant_for_a_frame_is_keyed_half_a_frame_before_it(fps):
    for frame in range(1, 600):
        assert held_keys.held_key(frame / fps, fps) == pytest.approx((frame - 0.5) / fps, abs=1e-12)
    assert held_keys.held_key(0.0, fps) == 0.0


@pytest.mark.parametrize("digits", [6, 4])
def test_a_rounded_frame_time_keys_the_same_frame(digits):
    """``round(i / 30, 6)`` is after frame i for every third i; it still names frame i."""
    late = [i for i in range(300) if round(i / 30, digits) > i / 30]
    assert late, "the rounding this guards against no longer rounds any frame time up"
    for i in range(300):
        assert held_keys.frame_of(round(i / 30, digits), 30) == i
        assert held_keys.held_key(round(i / 30, digits), 30) == held_keys.held_key(i / 30, 30)


def test_a_change_between_frames_shows_on_the_next_frame():
    assert held_keys.frame_of(0.05, 30) == 2  # 1.5 frames
    assert held_keys.held_key(0.05, 30) == pytest.approx(1.5 / 30)
    assert held_keys.held_key(1.01, 24) == pytest.approx(24.5 / 24)


def test_frame_time_is_the_engines_own_division():
    assert [held_keys.frame_time(k, 30) for k in range(90)] == [k / 30 for k in range(90)]


@pytest.mark.parametrize(
    "time, fps",
    [(-0.1, 30), (math.nan, 30), (math.inf, 30), ("1", 30), (True, 30), (1.0, 0), (1.0, -30), (1.0, True),
     (1.0, math.nan), (1.0, 30.5), (1.0, 241)],
)  # fmt: skip
def test_bad_times_and_rates_are_refused(time, fps):
    with pytest.raises(held_keys.HeldKeyError) as caught:
        held_keys.held_key(time, fps)
    assert caught.value.to_dict()["code"].startswith("held_key.")
    with pytest.raises(held_keys.HeldKeyError):
        held_keys.frame_of(time, fps)


def test_off_frame_finds_a_rounded_frame_key():
    """The test's own detector: it flags the six-decimal key of frame 2 and passes a frame-centre key."""
    assert off_frame([round(2 / 30, 6)], 30) == [round(2 / 30, 6)]
    assert off_frame([1.5 / 30], 30) == []


def test_a_body_on_a_project_without_a_frame_rate_is_refused_before_drawing():
    scene = Scene(version="auto")
    with pytest.raises(held_keys.HeldKeyError) as rate:
        held_keys.project_fps(scene)
    assert rate.value.to_dict()["code"] == "held_key.fps"
    cv = Canvas(scene, font_asset=None)
    before = cv.scene.to_bytes()
    with pytest.raises(body.BodyError) as caught:
        walking().window(0, 2).place(cv, cv.comp, camera=Camera())
    assert caught.value.to_dict()["path"] == "canvas"
    assert cv.scene.to_bytes() == before


def test_a_ratio_frame_rate_keys_half_a_frame_before_each_frame():
    scene = Scene(version="auto")
    scene.add_project(width=360, height=640, fps="30000/1001", duration=2)
    rate = held_keys.project_fps(scene)
    assert rate == Fraction(30000, 1001)
    assert held_keys.held_key(float(2 / rate), rate) == pytest.approx(float(Fraction(3, 2) / rate))
    cv = Canvas(scene, font_asset=None)
    group = walking().window(0, 1).place(cv, cv.comp, camera=Camera(origin=(180, 600), scale=300), fps=30)
    starts = [float(g.start) for g in group.iter("group") if g.id.startswith("body-frame")]
    assert [s for s in starts if s > 0 and abs(s * rate - round(s * rate)) < MARGIN] == []


@pytest.mark.parametrize("bad", [-1, 1.5, True, "1"])
def test_a_bad_frame_is_refused(bad):
    with pytest.raises(held_keys.HeldKeyError) as caught:
        held_keys.frame_time(bad, 30)
    assert caught.value.to_dict()["code"] == "held_key.frame"


# -- the paths that write held keys on a frame grid ----------------------------------------------------------------


@pytest.mark.parametrize("drawn", [30, 24, 15])
def test_body_drawings_change_half_a_frame_before_their_frame(drawn):
    _, frames = body_frames(drawn=drawn)
    edges = [float(g.start) for g in frames] + [float(frames[-1].end)]
    assert off_frame(edges[:-1], 30) == []
    assert all(a < b for a, b in zip(edges, edges[1:], strict=False))


def test_a_body_drawing_on_twos_spans_two_project_frames():
    _, frames = body_frames(fps=30, drawn=15)
    spans = [round((float(g.end) - float(g.start)) * 30, 9) for g in frames[1:-1]]
    assert set(spans) == {2.0}


def test_face_blend_frames_change_half_a_frame_before_their_frame():
    track = FaceTrack((FaceBlend(1, 2, FacePose("neutral", "neutral"), FacePose("concerned", "frown")),), fps=30)
    rig = acting.bento_blends().head_rig
    poses = (Pose(0, "neutral", "neutral", "tablet"), Pose(2, "concerned", "frown", "tablet"))
    frames = track.prepare(rig, poses, 3)
    assert frames[0].start == 1 and frames[-1].end == 2
    assert off_frame([f.start for f in frames[1:]], 30) == []
    assert len(frames) == 30  # one drawing per frame of the second
    assert list(segments(frames, 1, 2))[0][0] == 1


def test_named_gaze_switches_half_a_frame_before_its_frame():
    target = gaze.TargetTrack((gaze.TargetKey(0, (0, 0, 2)), gaze.TargetKey(1, (0.9, 0, 2))))
    plan = gaze.GazePlan(gaze.GazeSpec(target, 1.5, fps=30, limits=gaze.GazeLimits(head_share=0, eye_yaw=40)))
    keys = gaze.named_gaze(plan, gaze.NamedGazeMapping(("ahead", "left", "right"), max_error=0.45))
    assert len(keys) > 1
    assert off_frame([t for t, _ in keys], 30) == []


def test_shaking_swaps_half_a_frame_before_their_frame():
    keys = stick_door.shaking(0.0, 3.0, Face())
    assert off_frame([k.start for k in keys], 30) == []
    assert [k.pose for k in keys[:4]] == ["hold-a", "hold-b", "hold-a", "hold-b"]


def test_shaking_keeps_its_first_pose_at_start_and_leaves_out_swaps_no_frame_shows():
    face = Face()
    fast = stick_door.shaking(0.52, 0.6, face, rate=100)  # five swaps inside two frames
    assert fast[0].start == 0.52
    assert all(a.start < b.start for a, b in zip(fast, fast[1:], strict=False))
    assert len(fast) <= 3 and all(k.start < 0.6 for k in fast)
    assert off_frame([k.start for k in fast[1:]], 30) == []
    late = stick_door.shaking(0.0, 0.51, face, rate=12)  # the swap at 0.5 shows on frame 15, at 0.5 itself
    assert all(k.start < 0.51 for k in late)


def test_shaking_as_published_keeps_its_keys():
    """hold_the_door is published with the four-decimal keys; ``published=True`` keeps them exactly."""
    face = Face()
    for start, rate in ((0.0, 12.0), (0.3, 12.0), (0.0, 8)):
        keys = stick_door.shaking(start, 2.0, face, rate=rate, published=True)
        assert [k.start for k in keys] == [round(start + i / rate, 4) for i in range(math.ceil((2.0 - start) * rate))]


# -- the engine shows each frame its own drawing -----------------------------------------------------------------


def _shown(scene: Path, frame: int) -> list[str]:
    run = subprocess.run(
        [str(ENGINE), "eval", scene.name, "--frame", str(frame), "--format", "json"],
        cwd=scene.parent,
        capture_output=True,
        text=True,
        check=True,
    )
    found: list[str] = []

    def walk(node):
        if isinstance(node, dict):
            if str(node.get("id", "")).startswith("body-frame"):
                found.append(node["id"])
            for value in node.values():
                walk(value)
        elif isinstance(node, list):
            for value in node:
                walk(value)

    walk(json.loads(run.stdout)["result"])
    return found


@pytest.mark.skipif(ENGINE is None, reason="needs the engine")
@pytest.mark.parametrize("at", [0.0, 1.1])
def test_the_engine_shows_every_frame_its_own_body_drawing(tmp_path, at):
    """Frame k shows the k-th drawing, also under a clock offset (``at`` 1.1 s puts the window on a time offset)."""
    cv, frames = body_frames(at=at)
    scene = tmp_path / "body.scene.xml"
    scene.write_bytes(cv.scene.to_bytes(layout="pretty"))
    first = round(at * 30)
    for k in range(12):
        assert _shown(scene, first + k) == [frames[k].id], f"frame {first + k}"
