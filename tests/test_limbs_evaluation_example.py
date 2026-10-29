"""The comparison packet keeps its implementation key outside the public review material."""

import importlib.util
import json
from pathlib import Path

import pytest

from srstudio.limbs.geometry import project_pose


@pytest.mark.parametrize("observed", [False, True])
def test_evaluation_example_produces_schema_valid_pairs_and_blinded_packet(tmp_path, observed):
    path = Path(__file__).resolve().parents[1] / "examples/limbs_evaluate.py"
    spec = importlib.util.spec_from_file_location("limbs_evaluate", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    observations = ratings = None
    if observed:
        public = tmp_path / "evaluation" / "review"
        public.mkdir(parents=True)
        observations = public.parent / "authoring-template.json"
        ratings = public / "ratings-template.json"
        ratings.write_text(
            json.dumps(
                {
                    "schema": "srstudio.limbs.ratings/1.0.0",
                    "ratings": [
                        {
                            "trial": "trial-001",
                            "reviewer": "one",
                            "preference": "tie",
                            "a": {"clarity": 3, "naturalness": 3, "style_fit": 3},
                            "b": {"clarity": 3, "naturalness": 3, "style_fit": 3},
                        }
                    ],
                }
            )
        )
        observations.write_text(
            json.dumps(
                {
                    "schema": "srstudio.limbs.authoring/1.0.0",
                    "records": [
                        {
                            "case": "point",
                            "author": "one",
                            "implementation": implementation,
                            "seconds": seconds,
                            "completed": True,
                        }
                        for implementation, seconds in (("legacy-stick", 120), ("spatial-stick", 90))
                    ],
                }
            )
        )
    result = module.build(tmp_path / "evaluation", repeats=1, authoring=observations, ratings=ratings)
    report = json.loads(result.read_text())
    assert len(report["measurements"]) == 6
    assert report["review"]["status"] == ("partial" if observed else "awaiting_ratings")
    assert report["schema"] == "srstudio.limbs.evaluation/1.1.0"
    if observed:
        assert len(json.loads(observations.read_text())["records"]) == 2
        assert len(json.loads(ratings.read_text())["ratings"]) == 1
        assert report["authoring"]["paired"]["point"]["median_candidate_minus_baseline_seconds"] == -30
    else:
        assert report["authoring"]["status"] == "awaiting_records"
    assert (result.parent / "authoring-template.json").is_file()
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


@pytest.mark.parametrize("option", ["ratings", "authoring"])
def test_evaluation_example_reads_collected_files_through_the_bounded_document_reader(tmp_path, option):
    from srstudio.limbs import LimbError

    path = Path(__file__).resolve().parents[1] / "examples/limbs_evaluate.py"
    spec = importlib.util.spec_from_file_location("limbs_evaluate", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    collected = tmp_path / "collected.json"
    collected.write_text('{"schema": "a", "schema": "b"}')
    with pytest.raises(LimbError, match="duplicate"):
        module.build(tmp_path / "evaluation", repeats=1, **{option: collected})
    collected.write_text("[" * 100 + "]" * 100)
    with pytest.raises(LimbError, match="nesting"):
        module.build(tmp_path / "evaluation", repeats=1, **{option: collected})
