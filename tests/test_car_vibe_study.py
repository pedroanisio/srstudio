"""The Car Vibe study (examples/car_vibe): ten seconds redrawn from scratch, the default drawing method end to end.

The study builds in a project holding the caption font and a one-cue script, draws four shots in order, carries no
picture but the car's own plates, and leaves the engine's validation without a finding. The plates' parts stay apart
through the engine's tone mapping, and the people stand in front of the seats and behind the near side of the car.
The wheels are apart from the body: they stay on the road and turn while the body rides the music's beat over them.
"""

import importlib
import json
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path
from xml.etree import ElementTree

import numpy as np
import pytest

from srstudio import proxy

ROOT = Path(__file__).resolve().parent.parent
SCRIPT = ROOT / "examples" / "car_vibe" / "car_vibe_study.py"
FONT = Path("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf")
SHOTS = ("wide", "windshield", "driver", "again")
MEDIA_ELEMENTS = ("video", "audio", "lottie")
PLATES = {
    f"plates/{shot}-{layer}.png" for shot in ("wide", "windshield", "driver") for layer in ("back", "front", "under")
}


@pytest.fixture(scope="module")
def cel():
    sys.path.insert(0, str(SCRIPT.parent))
    yield importlib.import_module("_car_cel")
    sys.path.remove(str(SCRIPT.parent))


@pytest.fixture(scope="module")
def project(tmp_path_factory) -> Path:
    assert FONT.exists(), f"the test needs {FONT}"
    root = tmp_path_factory.mktemp("car-vibe")
    (root / "assets").mkdir()
    shutil.copy(FONT, root / "assets" / "Inter-Bold.ttf")
    cue = dict(start=0.0, end=10.0, text="The playlist understood the vibe", speaker="narrator")
    (root / "script.json").write_text(json.dumps([cue]))
    env = {**os.environ, "PYTHONPATH": str(ROOT / "src")}
    done = subprocess.run([sys.executable, str(SCRIPT), str(root)], env=env, capture_output=True, text=True)
    assert done.returncode == 0, done.stderr
    return root


def test_the_study_builds_a_ten_second_scene_with_the_four_shots_in_order(project):
    scene = (project / "car-vibe-study.scene.xml").read_text()
    starts = [scene.index(f'id="shot-{name}"') for name in SHOTS]
    assert starts == sorted(starts)
    assert re.search(r'duration="10(\.0+)?"', scene)


def test_the_study_embeds_no_video_or_audio_and_no_picture_but_its_plates(project):
    tree = ElementTree.parse(project / "car-vibe-study.scene.xml")
    tags = {element.tag.rpartition("}")[2] for element in tree.iter()}
    assert not tags.intersection(MEDIA_ELEMENTS)
    pictures = {e.attrib["src"] for e in tree.iter() if e.tag.rpartition("}")[2] == "image" and "src" in e.attrib}
    assert pictures == PLATES


def test_the_engine_validation_of_the_study_has_no_finding(project):
    report = json.loads((project / "qa" / "sdk-validation.json").read_text())
    assert report == []


def test_every_part_keeps_a_colour_of_its_own(cel):
    colours = [cel.RECIPE.ids[name] for name in cel.RECIPE.names]
    assert len(set(colours)) == len(colours)
    assert max(max(colour) for colour in colours) * proxy.ID_GAIN < 200  # far from the tone curve's shoulder


def test_a_blended_edge_pixel_is_refilled_from_its_neighbours(cel):
    body, seat, stray = (np.array(cel.RECIPE.ids[n]) * proxy.ID_GAIN for n in ("body", "seat", "tire"))
    ids = np.zeros((12, 12, 4), np.uint8)
    ids[..., 3] = 255
    ids[:, :6, :3], ids[:, 6:, :3] = body, seat
    ids[5, 6, :3] = stray
    part = proxy.read_parts(ids, cel.RECIPE)
    assert set(np.unique(part)) == {cel.RECIPE.names.index("body"), cel.RECIPE.names.index("seat")}


def test_the_people_stand_in_front_of_the_seats_and_behind_the_near_side(cel):
    assert {"seat", "tub", "far-pillar"} <= cel.BEHIND
    assert not {"body", "pillar", "mirror", "dash"} & cel.BEHIND


def test_the_far_side_of_the_car_is_split_from_the_near_side(cel):
    parts = {mesh.material: mesh for mesh in cel.build()}
    assert parts["far-pillar"].vertices[parts["far-pillar"].triangles].mean(axis=1)[:, 2].min() > 40
    assert parts["pillar"].vertices[parts["pillar"].triangles].mean(axis=1)[:, 2].max() <= 40
    assert set(parts) <= set(cel.RECIPE.names)


def keys(project, node: str, prop: str) -> list[tuple[float, float]]:
    tree = ElementTree.parse(project / "car-vibe-study.scene.xml")
    group = next(e for e in tree.iter() if e.attrib.get("id") == node)
    animate = next(c for c in group if c.tag.endswith("animate") and c.attrib["property"] == prop)
    return [(float(k.attrib["time"]), float(k.attrib["value"])) for k in animate]


def test_the_body_rises_on_every_beat_of_the_music_and_more_on_the_bar(project):
    for name, (start, end) in {"wide": (0.0, 3.4), "windshield": (3.4, 6.4), "driver": (6.4, 8.0)}.items():
        path = keys(project, f"rig-{name}", "y")
        tops = [t for t, y in path if y < 0]
        assert tops == pytest.approx([0.14 + 0.465 * k for k in range(22) if start <= 0.14 + 0.465 * k < end], abs=1e-3)
        assert all(a < b for (a, _), (b, _) in zip(path, path[1:], strict=False))
    heights = dict(keys(project, "rig-windshield", "y"))
    hit, plain = (min(heights, key=lambda t: abs(t - (0.14 + k * 0.465))) for k in (11, 10))
    assert heights[hit] < heights[plain]


def test_the_wheels_stay_near_the_road_while_the_body_moves_over_them(project):
    body = [y for _, y in keys(project, "rig-windshield", "y")]
    wheels = [y for _, y in keys(project, "wheels-windshield", "y")]
    assert max(map(abs, wheels)) * 2.5 < max(map(abs, body))


def test_every_rim_turns_forward_at_a_steady_rate_through_each_shot(project, cel):
    spans = {"wide": (0.0, 3.4), "windshield": (3.4, 6.4), "driver": (6.4, 8.0), "again": (8.0, 10.0)}
    for name, (start, end) in spans.items():
        (t0, a0), (t1, a1) = keys(project, f"rim-{name}-0", "rotation")
        assert (t0, t1) == pytest.approx((start, end))
        assert (a1 - a0) / (t1 - t0) == pytest.approx(cel.SPIN)
    assert cel.SPIN > 0  # clockwise on screen: the nose points right


def test_a_rim_is_drawn_only_for_a_wheel_facing_the_camera(cel):
    for shot in cel.SHOTS.values():
        rims = cel.rims(shot)
        assert 1 <= len(rims) <= 2
        for rim in rims:
            assert 0 < rim.squash <= rim.stretch


def test_a_rim_turned_by_its_groups_lands_where_the_camera_projects_it(cel):
    shot = cel.SHOTS["windshield"]
    rim = cel.rims(shot)[0]
    a, b = np.radians((rim.tilt, rim.turn))

    def turn(r):
        return np.array([[np.cos(r), -np.sin(r)], [np.sin(r), np.cos(r)]])

    matrix = turn(a) @ np.diag((rim.stretch, rim.squash)) @ turn(b)
    x, y, z = cel.hubs()[0][0]
    for dx, dy in ((cel.RIM, 0.0), (0.0, cel.RIM), (-cel.RIM * 0.6, cel.RIM * 0.8)):
        seen = shot.project([(x + dx, y + dy, z)])[0] - (rim.x, rim.y)
        assert matrix @ (dx, dy) == pytest.approx(seen, abs=5.0)  # the lens's perspective, on a rim 350 px tall


def test_the_body_plates_leave_a_hole_for_the_wheels_with_no_ink_left_on_the_road(cel):
    part = np.full((60, 60), -1)
    part[:30] = cel.RECIPE.names.index("body")
    part[30:50, 20:40] = cel.RECIPE.names.index("tire")
    rgba = np.ones((60, 60, 4))
    back, front = proxy.split(rgba, part, cel.RECIPE)
    assert back[40, 30, 3] == 0 and front[40, 30, 3] == 0
    assert back[10, 30, 3] == 1 and front[10, 30, 3] == 1
    assert back[51, 30, 3] == 0  # the tyre's ink on the empty road belongs to the wheel plate


def test_a_sliver_of_the_car_seen_through_a_tyre_goes_with_the_wheel(cel):
    part = np.full((60, 60), -1)
    part[20:50, 20:50] = cel.RECIPE.names.index("tire")
    part[30:34, 30:34] = cel.RECIPE.names.index("well")
    back, front = proxy.split(np.ones((60, 60, 4)), part, cel.RECIPE)
    assert back[32, 32, 3] == 0 and front[32, 32, 3] == 0
