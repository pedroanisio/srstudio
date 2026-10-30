"""Actor defaults, bounded blink inputs, and independent repeat episode builds."""

import json
import subprocess
import sys
import xml.etree.ElementTree as ET
from dataclasses import replace

import pytest
from sr_core.scene import Scene

from srstudio import CEL, OFFICE, Canvas, Episode, EpisodeSpec, Performance, cast


@pytest.mark.parametrize("rig", [cast.Manager, cast.Candidate, cast.Barista, cast.Customer])
@pytest.mark.parametrize("performance", [None, Performance()])
def test_an_actor_without_mouth_cues_shows_only_rest(rig, performance):
    scene = Scene(version="auto")
    scene.add_project(width=1080, height=1920, fps="30", duration=1)
    actor = rig(Canvas(scene, OFFICE))
    actor.build(actor.cv.comp, 0, 0, perf=performance)
    root = ET.fromstring(scene.to_bytes())
    visible = []
    for name, shape in actor.mouths.items():
        node = next(n for n in root.iter() if n.get("id") == shape.id)
        key = node.find("./animate[@property='opacity']/key")
        opacity = float(key.get("value")) if key is not None else float(node.get("opacity", "1"))
        if opacity:
            visible.append(name)
    assert visible == ["rest"]


@pytest.mark.parametrize("period", ["0", "-1", "float('nan')", "float('inf')", "True"])
def test_invalid_blink_period_is_a_typed_error_without_hanging(period):
    code = f'''
from srstudio import SrstudioError
from srstudio.rig import blinks
try:
    blinks(None, None, 1, period={period}, phase=0, skip_empty=True)
except SrstudioError as exc:
    assert isinstance(exc, ValueError)
    assert "period" in str(exc)
else:
    raise AssertionError("invalid period accepted")
'''
    result = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True, timeout=5)
    assert result.returncode == 0, result.stdout + result.stderr


@pytest.fixture
def silent_spec(tmp_path):
    (tmp_path / "script.json").write_text(json.dumps([{"start": 0, "end": 1, "text": "hi"}]))
    return EpisodeSpec(
        slug="repeat", title="repeat", description="repeat", root=tmp_path, seed=1, style=CEL, signature=False
    )


def test_cover_rules_added_after_finish_are_written_once(silent_spec):
    ep = Episode(silent_spec)
    first = ep.cv.group(ep.comp, "first")
    second = ep.cv.group(ep.comp, "second")
    ep.hide_on_cover(first)
    ep.finish()
    ep.hide_on_cover(second)
    ep.finish()
    document = ET.parse(ep.finish()).getroot()
    assert len(document.findall(".//variant[@id='cover']")) == 1
    assert [n.get("target") for n in document.findall(".//variant[@id='cover']/override")] == ["first", "second"]


@pytest.mark.parametrize("copy_spec", [False, True])
def test_reusing_a_spec_builds_identical_documents(silent_spec, copy_spec):
    documents = []
    for spec in (silent_spec, replace(silent_spec) if copy_spec else silent_spec):
        ep = Episode(spec)
        ep.cv.rect(ep.comp, 0, 0, 10, 10, fill="#000000")
        documents.append(ep.finish().read_bytes())
    assert documents[0] == documents[1]


def test_an_explicit_namer_still_wins(silent_spec):
    ep = Episode(replace(silent_spec, namer=lambda prefix: f"custom-{prefix}"))
    assert ep.cv.uid("shape") == "custom-shape"
