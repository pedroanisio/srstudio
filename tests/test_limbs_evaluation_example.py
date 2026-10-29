"""The comparison packet keeps its implementation key outside the public review material."""

import importlib.util
import json
from pathlib import Path

import pytest

from srstudio.limbs.geometry import project_pose


def test_evaluation_example_produces_schema_valid_pairs_and_blinded_packet(tmp_path):
    path = Path(__file__).resolve().parents[1] / "examples/limbs_evaluate.py"
    spec = importlib.util.spec_from_file_location("limbs_evaluate", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    result = module.build(tmp_path / "evaluation", repeats=1)
    report = json.loads(result.read_text())
    assert len(report["measurements"]) == 6
    assert report["review"]["status"] == "awaiting_ratings"
    assert report["human_authoring_seconds"] is None
    public = result.parent / "review"
    manifest = json.loads((public / "trials.json").read_text())
    assert len(manifest["trials"]) == 3
    assert "legacy" not in str(manifest) and "spatial" not in str(manifest)
    private = json.loads((result.parent / "private-key.json").read_text())
    assert len(private["trials"]) == 3
    for item in report["measurements"]:
        assert item["xml_bytes"] > 0 and item["nodes"] > 0
        assert (result.parent / "scenes" / (item["name"] + ".scene.xml")).is_file()


def test_comparison_spatial_targets_match_the_legacy_gesture_endpoints(monkeypatch):
    path = Path(__file__).resolve().parents[1] / "examples/limbs_evaluate.py"
    spec = importlib.util.spec_from_file_location("limbs_evaluate", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    original = module._track
    endpoints = []

    def capture(*args, **kwargs):
        track = original(*args, **kwargs)
        action = track.motion.actions[0]
        sample = track.motion.sample(action.stroke_at)
        wrist = sample.arm.wrist
        if args[0] == "toon":
            pose = project_pose(sample, track.camera, width=track.motion.arm.width)
            xs = [p[0] for part in pose.parts if part.role == "skin" for p in part.polygon]
            assert min(xs) > 185 if args[1] == "right" else max(xs) < 185
        endpoints.append((args[0], args[1], track.camera.project(wrist).xy))
        return track

    monkeypatch.setattr(module, "_track", capture)
    module.spatial_toon()
    module.spatial_gloss()
    expected = {
        ("toon", "right"): (229, 664),
        ("toon", "left"): (141, 664),
        ("gloss", "right"): (186, -400),
        ("gloss", "left"): (-186, -400),
    }
    for style, side, xy in endpoints:
        assert xy == pytest.approx(expected[style, side], abs=1e-6)
