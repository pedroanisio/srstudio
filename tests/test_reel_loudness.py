"""A sketch reel may master at its own loudness; unset, it keeps its style's, so a published reel builds the same."""

from __future__ import annotations

import os
import shutil
import sys
import xml.etree.ElementTree as ET
from dataclasses import replace
from pathlib import Path

import pytest

from srstudio import TOON, collage_sketch, toon_sketch

EPISODES = Path(__file__).resolve().parent.parent / "episodes"


def project(tmp_path: Path, slug: str) -> Path:
    env = os.environ.get("SRSTUDIO_EPISODES")
    if not env or not (Path(env) / slug / "narration.json").is_file():
        pytest.skip("set SRSTUDIO_EPISODES to the folder of generated episode projects")
    root = tmp_path / slug
    shutil.copytree(Path(env) / slug, root, ignore=shutil.ignore_patterns("*.scene.xml", "*.srt"))
    return root


def master(ep) -> str | None:
    node = ET.fromstring(ep.cv.scene.to_bytes(layout="pretty")).find(".//audioMix/master")
    assert node is not None
    return node.get("loudness") or node.get("targetLoudness")


@pytest.mark.parametrize(("loudness", "expected"), [(None, TOON.mix.loudness), ("-14", "-14")])
def test_a_toon_reel_masters_at_its_own_loudness_or_its_styles(tmp_path, loudness, expected):
    root = project(tmp_path, "the-report")
    sys.path.insert(0, str(EPISODES))
    try:
        import the_report_data as data
    finally:
        sys.path.pop(0)
    staging = toon_sketch.Staging(
        data.SKETCH, data.SEED, data.DESCRIPTION, data.ACCESSIBILITY, data.NARRATION, data.TINTS,
        lambda shot: None, {}, loudness=loudness,
    )  # fmt: skip
    assert master(toon_sketch.build(root, staging, {"--voice"})) == expected


@pytest.mark.parametrize(("loudness", "expected"), [(None, "-16"), ("-14", "-14")])
def test_a_collage_reel_masters_at_its_own_loudness_or_its_styles(tmp_path, loudness, expected):
    root = project(tmp_path, "family-size")
    sys.path.insert(0, str(EPISODES))
    try:
        import family_size_data as reel
    finally:
        sys.path.pop(0)
    staging = replace(reel.STAGING, loudness=loudness)
    assert master(collage_sketch.build(root, staging, {"--voice"})) == expected
