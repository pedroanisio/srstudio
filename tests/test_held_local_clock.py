"""A held key on a shot's clock lands half a frame before the reel's frame that first shows it (ADR 0223).

A sequence places its shots end to end, so a shot whose take is not a whole number of frames starts between the
reel's frames. Keyed half a frame before a frame of the shot's own clock, a change in such a shot lands anywhere
between the reel's frames and shows up to a frame early or a frame late. ``Canvas.place_held`` keys each held change
through its node's clock instead: half a frame before the first reel frame at or after its time, and
``Episode.finish`` calls it before it checks and writes the scene.
"""

from __future__ import annotations

import json
import math
import os
import shutil
import subprocess
import xml.etree.ElementTree as ET
from fractions import Fraction

import pytest
from sr_core.scene import Scene

from srstudio import Canvas, Episode, EpisodeSpec, held_gate

ENGINE = os.environ.get("SRSTUDIO_ENGINE") or shutil.which("scene-render")


def sequenced(fps: str, lead: float, *, held_frames: bool = True, length: float = 6.0) -> tuple[Canvas, object]:
    """A canvas on the shot clock with two shots: ``lead`` seconds of a first shot, then the shot under test."""
    scene = Scene(version="auto")
    scene.add_project(width=360, height=640, fps=fps, duration=lead + length, background="#FFFFFF")
    cv = Canvas(scene, font_asset=None, local_time=True, held_frames=held_frames)
    shots = cv.comp.add_sequence(id="shots")
    cv.group(shots, "lead", end=lead)
    return cv, cv.group(shots, "shot", end=length)


def changes(animate) -> list[tuple[float, str]]:
    return [(float(k.time), k.value) for k in animate.iter("key")]


def shown_on(key: float, start: float, rate: Fraction) -> int:
    """The frame the engine first shows a key at ``key`` on the clock of a shot placed at ``start``: the first frame
    whose sample time ``k / fps``, less the shot's start, the engine's float subtraction, is at or after it."""
    k = max(0, math.floor((Fraction(key) + Fraction(start)) * rate) - 2)
    while float(k * rate.denominator / rate.numerator) - start < key:
        k += 1
    return k


def first_frame(time: Fraction, rate: Fraction) -> int:
    """The first frame whose sample time is at or after ``time`` on the reel's clock."""
    return math.ceil(time * rate)


def test_the_cut_meant_for_frame_165_stays_on_frame_165():
    """cant-afford-to-save: shot 4 starts at 4.613271 s, frame 110.72 at 24 fps, and cuts at 2.255875 s on its own
    clock, frame 164.86 of the reel, which the published scene shows on frame 165. Keyed half a frame before the
    shot's own frame 55 it landed at reel frame 165.22 and showed on frame 166."""
    cv, shot = sequenced("24", 4.613271)
    gate = cv.gate(cv.group(shot, "close"), [(0, 2.255875)])
    cv.place_held()
    (_, on), (cut, off) = changes(gate)
    assert (on, off) == ("1", "0")
    assert shown_on(cut, 4.613271, Fraction(24)) == 165
    assert (Fraction(cut) + Fraction(4.613271)) * 24 == pytest.approx(164.5, abs=1e-9)


def test_a_change_just_after_a_reel_frame_stays_on_the_next_frame():
    """saga-take-home: shot 9 starts at 9.20025 s and blinks 1.05 s into it, 10.25025 s in the reel, a quarter of a
    millisecond (0.006 of a frame) after frame 246, so the published scene shows it on 247. That is a time after the
    frame, not a frame time rounded up: it stays on 247. Only a sum within float noise of a frame is that frame:
    saga-friday-deploy's 8.715 + 1.91 is 10.625 s, frame 255 at 24 fps, which the engine reached a hair late."""
    rate = Fraction(24)
    cv, shot = sequenced("24", 9.20025)
    after = cv.gate(cv.group(shot, "after"), [(0, 1.05)])
    cv2, shot2 = sequenced("24", 8.715)
    noise = cv2.gate(cv2.group(shot2, "noise"), [(0, 1.91)])
    cv.place_held()
    cv2.place_held()
    assert shown_on(changes(after)[1][0], 9.20025, rate) == 247
    assert shown_on(changes(noise)[1][0], 8.715, rate) == 255


@pytest.mark.parametrize("fps", ["24", "30", "30000/1001"])
@pytest.mark.parametrize("between", [0.1, 0.5, 0.72, 0.99])
def test_a_shot_that_starts_between_frames_shows_each_change_on_its_own_frame(fps, between):
    """Changes a twentieth of a frame after, well after and just before a reel frame (a hundredth after is the frame
    itself, as six-decimal times are: ``held_keys.SLACK``), in a shot that starts ``between`` of a frame past
    a reel frame: each shows on the first reel frame at or after its time, keyed half a frame before it."""
    rate = Fraction(fps)
    lead = float((40 + Fraction(between)) / rate)
    cv, shot = sequenced(fps, lead)
    start = Fraction(lead)
    meant = {}
    keys = []
    for frame in range(45, 160, 7):
        for after in (Fraction(1, 20), Fraction(3, 10), Fraction(-1, 100)):
            reel = (frame + after) / rate
            keys.append((float(reel - start), len(keys) + 1))
            meant[len(keys)] = first_frame(reel, rate)
    animate = cv.keys(cv.group(shot, "g"), "x", [(0, 0), *keys])
    cv.place_held()
    for key, value in changes(animate)[1:]:
        assert shown_on(key, lead, rate) == meant[int(value)]
        half = (Fraction(key) + start) * rate
        assert half - math.floor(half) == pytest.approx(0.5, abs=1e-6)  # half a frame before the frame
    # of two changes one frame shows, the later stays
    shown = [int(v) for _, v in changes(animate)[1:]]
    assert all(meant[a] < meant[b] for a, b in zip(shown, shown[1:], strict=False))


@pytest.mark.parametrize("lead", [0.0, 10 / 24, 4.5])
def test_a_shot_on_the_reels_frames_keeps_the_keys_it_was_given(lead):
    """A shot that starts on a reel frame keeps the keys a new canvas already wrote: shower-argument and big-font
    rebuild byte for byte."""
    cv, shot = sequenced("24", lead) if lead else sequenced("24", 1.0)
    if not lead:
        shot = cv.group(cv.comp, "top")
    gate = cv.gate(cv.group(shot, "g"), [(0.07, 0.5), (1.0, 2.255875)])
    before = cv.scene.to_bytes()
    cv.place_held()
    assert cv.scene.to_bytes() == before
    assert [t for t, _ in changes(gate)][1] == 1.5 / 24


def test_placing_twice_changes_nothing():
    cv, shot = sequenced("24", 4.613271)
    cv.gate(cv.group(shot, "g"), [(0.3, 2.255875)])
    cv.place_held()
    once = cv.scene.to_bytes()
    cv.place_held()
    assert cv.scene.to_bytes() == once


def test_a_published_canvas_places_nothing():
    cv, shot = sequenced("24", 4.613271, held_frames=False)
    gate = cv.gate(cv.group(shot, "g"), [(0, 2.255875)])
    cv.place_held()
    assert changes(gate) == [(0.0, "1"), (2.255875, "0")]


def test_keys_someone_rewrote_after_the_canvas_are_left_alone():
    """A frozen shot (``staging``) rewrites or removes the animates it holds still: placing leaves them as they are."""
    cv, shot = sequenced("24", 4.613271)
    g = cv.group(shot, "g")
    gate = cv.gate(g, [(0, 2.255875)])
    for key in list(gate.elements()):
        gate.remove(key)
    gate.add_key(time=0, value="1")
    gone = cv.gate(cv.group(shot, "h"), [(0, 1.0)])
    gone._owner.remove(gone)
    cv.place_held()
    assert changes(gate) == [(0.0, "1")]


def test_the_gate_passes_a_placed_canvas_and_refuses_one_keyed_on_its_shots_frames():
    cv, shot = sequenced("24", 4.613271)
    for k in range(20):
        cv.gate(cv.group(shot, f"g{k}", opacity=0.0), [(0.13 * k, 0.13 * k + 0.13)])
    unplaced = cv.scene.to_bytes()
    cv.place_held()
    assert held_gate.late_changes(cv.scene.to_bytes()) == []
    assert held_gate.late_changes(unplaced) != []


def test_an_episode_places_its_held_keys_when_it_finishes(project, tmp_path):
    ep = Episode(
        EpisodeSpec(
            slug="placed", title="t", description="d", root=project, seed=1, signature=False, held_frames=True,
            local_time=True,
        )
    )  # fmt: skip
    shots = ep.cv.comp.add_sequence(id="shots")
    ep.cv.group(shots, "lead", end=4.613271)
    shot = ep.cv.group(shots, "shot", end=3.0)
    ep.cv.gate(ep.cv.group(shot, "close"), [(0, 2.255875)])
    out = ep.finish(out=tmp_path / "placed.scene.xml", report=tmp_path / "report.json")
    root = ET.parse(out).getroot()
    rate = Fraction(root.find("project").get("fps"))
    close = next(g for g in root.iter("group") if g.get("id") == "close")
    cut = float(list(close.iter("key"))[-1].get("time"))
    assert shown_on(cut, 4.613271, rate) == first_frame(Fraction(4.613271) + Fraction(2.255875), rate)
    assert held_gate.late_changes(out.read_bytes()) == []


@pytest.mark.skipif(ENGINE is None, reason="needs the engine")
@pytest.mark.parametrize("fps", ["24", "30000/1001"])
def test_the_engine_shows_each_change_on_the_frame_its_time_first_shows(tmp_path, fps):
    """One drawing per reel frame, gated from a tenth of a frame before it, in a shot that starts 0.72 of a frame
    past a reel frame: frame k of the reel shows drawing k and no other."""
    rate = Fraction(fps)
    lead = float((12 + Fraction(72, 100)) / rate)
    cv, shot = sequenced(fps, lead, length=2.0)
    start = Fraction(lead)
    for k in range(14, 40):
        on, off = (k - Fraction(1, 10)) / rate - start, (k + Fraction(9, 10)) / rate - start
        g = cv.group(shot, f"body-frame-{k:04d}", opacity=0.0)
        cv.rect(g, 0, 0, 10, 10, "#000000")
        cv.gate(g, [(float(on), float(off))])
    cv.place_held()
    path = tmp_path / "placed.scene.xml"
    path.write_bytes(cv.scene.to_bytes(layout="pretty"))
    for k in range(14, 40):
        run = subprocess.run(
            [str(ENGINE), "eval", path.name, "--frame", str(k), "--format", "json"],
            cwd=path.parent,
            capture_output=True,
            text=True,
            check=True,
        )
        nodes = json.loads(run.stdout)["result"]["nodes"]
        seen = [
            n["id"]
            for n in nodes
            if str(n.get("id", "")).startswith("body-frame") and n.get("draw") and n.get("world_opacity", 0) > 0.5
        ]
        assert seen == [f"body-frame-{k:04d}"], f"frame {k}"
