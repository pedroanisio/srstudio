"""Interactive corrections and normal output layouts work without rebuilding the Episode."""

import json
import xml.etree.ElementTree as ET

import pytest

from srstudio import Episode, EpisodeSpec, Timeline
from srstudio.episode import SceneCheckError


def episode(project):
    return Episode(
        EpisodeSpec(slug="recovery", title="Recovery", description="test", root=project, seed=1, signature=False)
    )


def test_caption_keyword_error_can_be_corrected_on_the_same_episode(project, tmp_path):
    ep = episode(project)
    before = ep.scene.to_bytes()
    with pytest.raises(TypeError, match="colour"):
        ep.captions(colour="#ffffff")
    assert ep.caption_specs == []
    assert ep.scene.to_bytes() == before
    ep.captions(color="#ffffff")
    ep.markers()
    assert len(ep.caption_specs) == len(ep.phrases)
    assert ep.check() == []
    assert ep.finish(tmp_path / "corrected.scene.xml").is_file()


def test_one_shot_name_matches_the_whole_name_and_merges_adjacent_cuts():
    timeline = Timeline.from_dict(
        {
            "duration": 4,
            "phrases": [],
            "camera_cuts": [
                {"time": 0, "angle": "wide"},
                {"time": 1, "angle": "wide"},
                {"time": 2, "angle": "w"},
                {"time": 3, "angle": "wide"},
            ],
        }
    )
    assert timeline.shots("wide") == [(0.0, 2.0), (3.0, 4.0)]
    assert timeline.shots("wide") == timeline.shots({"wide"})
    assert timeline.shots("unknown") == []


def test_finish_creates_separate_nested_scene_and_report_directories(project, tmp_path):
    ep = episode(project)
    out = tmp_path / "scenes" / "nested" / "scene.xml"
    report = tmp_path / "reports" / "nested" / "checks.json"
    assert ep.finish(out=out, report=report) == out
    assert ET.parse(out).getroot().tag == "scene"
    assert json.loads(report.read_text()) == []


def test_failed_finish_writes_the_report_without_creating_scene_directory(project, tmp_path):
    ep = episode(project)
    ep.comp.add_group(id="duplicate")
    ep.comp.add_group(id="duplicate")
    out = tmp_path / "scenes" / "scene.xml"
    report = tmp_path / "reports" / "checks.json"
    with pytest.raises(SceneCheckError):
        ep.finish(out=out, report=report)
    assert not out.parent.exists()
    assert any(finding["severity"] == "error" for finding in json.loads(report.read_text()))


def test_failed_finish_keeps_an_empty_directory_it_did_not_create(project, tmp_path):
    ep = episode(project)
    ep.comp.add_group(id="duplicate")
    ep.comp.add_group(id="duplicate")
    out = tmp_path / "scenes" / "scene.xml"
    out.parent.mkdir()
    with pytest.raises(SceneCheckError):
        ep.finish(out=out, report=tmp_path / "reports" / "checks.json")
    assert out.parent.is_dir()
