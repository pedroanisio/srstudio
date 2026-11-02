"""The dance-study runner (ADR 0203) on synthetic records: it measures a style from a pose track, checks our standing
presets against it with the misses they share ranked, refuses to write anything but a style record inside the
repository, writes its private outputs 700/600, and draws the skeleton and the page without the footage."""

import importlib.util
import json
import stat
import sys
from pathlib import Path

import pytest

from srstudio import dance, dance_style, music
from srstudio import pose_track as pt
from support.pose_records import record

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("dance_study_tool", ROOT / "tools" / "dance_study.py")
assert spec is not None and spec.loader is not None
tool = importlib.util.module_from_spec(spec)
sys.modules["dance_study_tool"] = tool
spec.loader.exec_module(tool)

GROOVE = music.Groove(120)


@pytest.fixture(scope="module")
def track():
    return pt.from_data(record(frames=300, bob=0.04, hz=2.0))


@pytest.fixture(scope="module")
def style(track):
    return tool.measure(track, GROOVE, name="bob", description="a synthetic figure bobbing on the beat")


@pytest.fixture(scope="module")
def findings(style):
    return tool.check_all(style, GROOVE, bars=4, fps=15)


def test_a_style_is_measured_from_a_track_with_its_source(style, track):
    assert style.name == "bob" and style.reference.frames == 300 and style.reference.used == 300
    assert style.reference.source_sha256 == track.source.sha256 and style.reference.bpm == 120
    hips = next(c for c in style.channels if c.name == "hips.bounce")
    assert hips.cycles_per_beat is not None and hips.cycles_per_beat[0] <= 1.0 <= hips.cycles_per_beat[1]
    assert dance_style.parse_style(dance_style.dump_style(style)) == style


def test_the_grid_comes_from_the_numbers_or_the_audio():
    assert tool.grid(None, 100.0, 0.25) == music.Groove(100.0, 4, 0.25)
    with pytest.raises(tool.StudyError, match="--audio"):
        tool.grid(None, None, None)


def test_every_standing_preset_is_checked_and_the_shared_misses_are_ranked(findings):
    standing = {n for n, m in dance.moves().items() if m.support in ("feet", "either")}
    assert {c["name"] for c in findings["candidates"]} == standing
    scores = [c["score"] for c in findings["candidates"]]
    assert scores == sorted(scores)
    weights = [m["weight"] for m in findings["shared"]]
    assert findings["shared"] and weights == sorted(weights, reverse=True)
    for miss in findings["shared"]:
        assert miss["missed_by"] == miss["below"] + miss["above"] + miss["none"] <= miss["of"] == len(standing)
    json.dumps(findings)


def test_shared_misses_count_each_way():
    def miss(ours, severity=1.0):
        return {"channel": "head.bob", "measure": "level", "ours": ours, "low": 1.0, "high": 2.0, "severity": severity,
                "trust": "good", "words": "w"}  # fmt: skip

    results = [{"misses": [miss(0.5)]}, {"misses": [miss(3.0)]}, {"misses": [miss(None, 2.0)]}, {"misses": []}]
    (only,) = tool.shared(results)
    assert (only["below"], only["above"], only["none"], only["of"]) == (1, 1, 1, 4)
    assert only["ours_median"] == 1.75 and only["weight"] == 1.0
    assert "1 abaixo" in tool._explain(only) and "sem ciclo" in tool._explain(only)
    angle = dict(only, channel="knees.bend", ours_median=None, below=0, above=0, none=1)
    assert "°" in tool._explain(angle)
    assert "não é meta" in tool._explain(only)  # head.bob's level is partly where the estimator puts the head
    assert "não é meta" not in tool._explain(dict(only, measure="peak_to_peak"))


def test_nothing_but_a_style_is_written_inside_the_repository(tmp_path):
    with pytest.raises(tool.StyleOutside, match="inside the repository"):
        tool.write_private(ROOT / "generated" / "x.json", "{}")
    out = tool.write_private(tmp_path / "deep" / "findings.json", "{}")
    assert stat.S_IMODE(out.stat().st_mode) == 0o600
    assert stat.S_IMODE(out.parent.stat().st_mode) == 0o700
    assert tool.private(ROOT / "src" / "srstudio" / "assets" / "dance" / "styles" / "x.json").name == "x.json"


def test_a_skeleton_is_drawn_and_a_lost_frame_says_so(track):
    found = tool.skeleton_frame(track.frames[0], 200, 240)
    assert found.shape == (240, 200, 3) and found.max() > 100
    lost = pt.PoseFrame(0, 0.0, None, None, None, None, None)
    assert tool.skeleton_frame(lost, 200, 240).max() < 255


def test_the_page_is_portuguese_standalone_and_names_what_it_cannot_measure(style, findings):
    text = tool.page(style, findings, footage="skeleton.mp4", views="views.mp4", closest="bounce")
    assert text.startswith("<!doctype html>") and 'lang="pt-BR"' in text
    assert "não publique" in text and "skeleton.mp4" in text and "views.mp4" in text
    assert "root.travel" in text and "<script" not in text and "http" not in text
    # The words name the colours the skeleton is drawn in (BGR): the right side blue, the left orange.
    assert "Azul é o lado direito dela, laranja o esquerdo" in text
    assert tool.RIGHT[0] > tool.RIGHT[2] and tool.LEFT[2] > tool.LEFT[0]
    for name in tool.LABELS:
        assert name in text
    bare = tool.page(style, findings, footage=None, views=None, closest="bounce")
    assert "não foi gerado" in bare
