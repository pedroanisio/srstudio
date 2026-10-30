"""Build feedback, artifact isolation and sample input contracts for automated callers."""

import json
import re
from pathlib import Path

import pytest

from srstudio import Episode, EpisodeSpec, sample, signature
from srstudio.episode import EpisodeArgumentError
from srstudio.sample import SampleError


def test_signature_failure_is_in_the_machine_readable_report(project, tmp_path):
    ep = Episode(EpisodeSpec(slug="signed", title="t", description="t", root=project, seed=1))
    report, out = tmp_path / "report.json", tmp_path / "scene.xml"
    with pytest.raises(signature.SignatureError, match="sig-cactus, sig-code") as error:
        ep.finish(out=out, report=report)
    findings = json.loads(report.read_text())
    assert findings == [{"severity": "error", "code": "srstudio:signature", "message": str(error.value)}]
    assert not out.exists()


@pytest.mark.parametrize("alias", ["identical", "relative", "symlink", "hardlink"])
def test_overlapping_report_and_scene_paths_are_rejected_before_writing(project, tmp_path, alias):
    ep = Episode(EpisodeSpec(slug="t", title="t", description="t", root=project, seed=1, signature=False))
    ep.comp.add_group(id="dup")
    ep.comp.add_group(id="dup")
    out = tmp_path / "scene.xml"
    out.write_text("existing scene")
    report = out
    if alias == "relative":
        report = tmp_path / "other" / ".." / "scene.xml"
    elif alias == "symlink":
        report = tmp_path / "report.json"
        report.symlink_to(out)
    elif alias == "hardlink":
        report = tmp_path / "report.json"
        report.hardlink_to(out)
    with pytest.raises(EpisodeArgumentError, match="different"):
        ep.finish(out=out, report=report)
    assert out.read_text() == "existing scene"
    assert not (tmp_path / "other").exists()


@pytest.mark.parametrize(
    "line,field",
    [
        (sample.Line("", "hello"), "role"),
        (sample.Line("  ", "hello"), "role"),
        (sample.Line("a", ""), "text"),
        (sample.Line("a", "  "), "text"),
        (sample.Line("a", 123), "text"),
        (sample.Line("a", "hello", caption=123), "caption"),
    ],
)
def test_invalid_dialogue_is_refused_before_any_project_write(tmp_path, line, field):
    root = tmp_path / "project"
    with pytest.raises(SampleError, match=rf"line 0\.{field}"):
        sample.write_sample_project(root, [line])
    assert not root.exists()


def test_sdk_dependency_is_pinned_to_a_git_commit():
    config = (Path(__file__).resolve().parents[1] / "pyproject.toml").read_text()
    assert re.search(r'sr-core @ git\+https://github\.com/pedroanisio/sr-core@[0-9a-f]{40}', config)
