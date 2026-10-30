"""The Toon sketch build's staging options: a sketch may hold a silent, uncaptioned first beat (a still opening)
and caption its first line later, and a staging may move a camera on every shot under an id ``srstudio.craft``
counts as camera."""

import json
import os
import shutil
import xml.etree.ElementTree as ET
from dataclasses import replace
from pathlib import Path

import pytest

from srstudio import TOON, camera, craft, parts, sketch, toon, toon_sketch, usage
from srstudio.sketch import Beat, Line, Sketch, Speaker
from srstudio.voice import Voice, VoiceSettings

SPEAKERS = (
    Speaker("bo", Voice(role="bo", id="a1", name="Roger"), VoiceSettings(0.5, 0.75, 0.3), "bear"),
    Speaker("mo", Voice(role="mo", id="b2", name="River"), VoiceSettings(0.5, 0.75, 0.3), "rabbit"),
)
LINES = (Line("bo", "She is still typing."), Line("mo", "Pepperoni."))
STILL = (
    Beat(0.0, "bear", "", "wide", "flat", "desk"),  # the still opening: nobody speaks, nothing is captioned
    Beat(1.2, "bear", "She is still typing.", "wide", "flat", "desk", 0, 0),
    Beat(3.0, "rabbit", "Pepperoni.", "half", "smirk", "desk", 1, 0),
    Beat(4.4, "rabbit", "", "half", "smirk", "crossed"),
)
END = 6.0


def silent(sk: Sketch, versions=None, **kw) -> toon_sketch.Staging:
    tints = {"bo": "#ffe3b3", "mo": "#d6f5dc"}
    return toon_sketch.Staging(sk, 3, "d", "a", "n", tints, lambda shot: None, versions or {}, **kw)


@pytest.fixture(scope="module")
def pinned_fonts() -> Path:
    """The pinned fonts folder of a generated Toon project (``SRSTUDIO_EPISODES``), or skip: the build measures its
    captions in the real font, and fetching it is network."""
    env = os.environ.get("SRSTUDIO_EPISODES")
    if not env:
        pytest.skip("set SRSTUDIO_EPISODES to the folder of generated episode projects")
    folder = Path(env) / "the-report" / "assets" / "fonts"
    if TOON.font is None or not (folder / Path(TOON.font.src).name).is_file():
        pytest.skip(f"no pinned Toon font in {folder}")
    return folder


def built(root: Path, staging: toon_sketch.Staging, fonts: Path):
    shutil.copytree(fonts, root / "assets" / "fonts")
    assert toon_sketch.build(root, staging, {"--init"}) is None
    ep = toon_sketch.build(root, staging, set())
    assert ep is not None
    return ep, ET.fromstring(ep.scene.to_bytes(layout="pretty"))


def test_a_staging_must_say_which_versions_it_draws():
    sk = Sketch("still-test", "Still test", SPEAKERS, LINES, STILL, END)
    with pytest.raises(TypeError, match="versions"):
        toon_sketch.Staging(sk, 3, "d", "a", "n", {}, lambda shot: None)


def fox_sketch() -> Sketch:
    speakers = (SPEAKERS[0], Speaker("mo", SPEAKERS[1].voice, SPEAKERS[1].settings, "fox"))
    beats = tuple(replace(b, who="fox") if b.who == "rabbit" else b for b in STILL)
    return Sketch("fox-test", "Fox test", speakers, LINES, beats, END)


@pytest.mark.parametrize(("pins", "drew"), [({"toon-fox": 1}, 1), ({"toon-fox": 2}, 2), ({}, 2)])
def test_a_build_draws_the_pinned_version_or_the_default_and_records_it(pinned_fonts, tmp_path, pins, drew):
    with usage.recorded(tmp_path):
        built(tmp_path, silent(fox_sketch(), versions=pins), pinned_fonts)
    assert {"toon-bear": 2, "toon-fox": drew}.items() <= parts.read_record(tmp_path).items()
    expected = {1: "toon_cast", 2: "toon_inked"}[drew]
    assert sketch.drawer("fox", {"toon-fox": drew}).__module__ == f"srstudio.{expected}"


def test_a_pin_changes_what_a_build_draws(pinned_fonts, tmp_path):
    drawings = []
    for number in (1, 2):
        root = tmp_path / str(number)
        root.mkdir()
        _, xml = built(root, silent(fox_sketch(), versions={"toon-fox": number}), pinned_fonts)
        drawings.append(ET.tostring(xml))
    assert drawings[0] != drawings[1]


def test_a_build_refuses_a_pin_it_cannot_draw(pinned_fonts, tmp_path):
    with pytest.raises(parts.UnknownVersionError, match="toon-fox has no version 9"):
        built(tmp_path, silent(fox_sketch(), versions={"toon-fox": 9}), pinned_fonts)


def test_a_sketch_may_open_on_a_still_uncaptioned_beat_and_caption_its_first_line_later(pinned_fonts, tmp_path):
    sk = Sketch("still-test", "Still test", SPEAKERS, LINES, STILL, END)
    sketch.check(sk)
    ep, xml = built(tmp_path, silent(sk), pinned_fonts)
    assert ep.t.phrases[0].start == 1.2
    shots = sketch.appearances(sk.beats, sk.end)
    pills = list(xml.find("composition"))[len(shots) :]  # each shot's group, then one group per caption
    assert [float(g.get("start")) for g in pills] == [1.2, 3.0]
    # a caption script that no longer matches the sketch is still refused
    cues = json.loads((tmp_path / "script.json").read_text())
    cues[0]["start"] = 0.0
    (tmp_path / "script.json").write_text(json.dumps(cues))
    with pytest.raises(toon_sketch.StagingError, match="run --init again"):
        toon_sketch.build(tmp_path, silent(sk), set())


def test_a_staging_camera_moves_every_shot_under_an_id_craft_counts(pinned_fonts, tmp_path):
    sk = Sketch("camera-test", "Camera test", SPEAKERS, LINES, STILL, END)
    seen = []

    def push(shot, setup) -> None:
        app = shot.app
        seen.append((app.who, app.start, app.end, shot.beats))
        camera.anchor(setup, 540, 900, place=True)
        camera.push_in(shot.cv, setup, scale=[(app.start, 1.0), (app.start + 1.0, 1.05)])

    ep, xml = built(tmp_path, silent(sk, camera=push), pinned_fonts)
    apps = sketch.appearances(sk.beats, sk.end)
    assert seen == [(a.who, a.start, a.end, sk.beats) for a in apps]
    shots = [g for g in xml.find("composition") if craft.CAMERA.fullmatch(g.get("id", ""))]
    assert [(float(g.get("start")), float(g.get("end"))) for g in shots] == [(a.start, a.end) for a in apps]
    assert all(g.find("animate[@property='scaleX']") is not None for g in shots)


def test_without_a_camera_the_shots_keep_their_anonymous_ids(pinned_fonts, tmp_path):
    sk = Sketch("plain-test", "Plain test", SPEAKERS, LINES, STILL, END)
    _, xml = built(tmp_path, silent(sk), pinned_fonts)
    assert not [g for g in xml.iter("group") if craft.CAMERA.fullmatch(g.get("id", ""))]


def test_a_staging_scales_a_figure_about_its_seat_and_leaves_the_others_alone(pinned_fonts, tmp_path):
    sk = Sketch("figure-test", "Figure test", SPEAKERS, LINES, STILL, END)
    plain = silent(sk)
    framed = replace(plain, figures={"rabbit": (1.4, 6.0)})
    _, xml = built(tmp_path, framed, pinned_fonts)
    x, y = toon.fx(toon_sketch.SEAT[0]), toon.fy(toon_sketch.SEAT[1])
    scaled = [g for g in xml.iter("group") if g.get("scaleX") == "1.4"]
    assert len(scaled) == 1  # the rabbit's one shot, none of the bear's
    assert float(scaled[0].get("anchorX")) == pytest.approx(x)
    assert float(scaled[0].get("anchorY")) == pytest.approx(y)
    assert float(scaled[0].get("x")) == pytest.approx(x + toon.fh(6.0))


@pytest.mark.parametrize("framing", [(0.0, 0.0), (-1.0, 0.0), (float("nan"), 0.0), (1.2, float("inf"))])
def test_a_staging_refuses_a_framing_it_cannot_draw(pinned_fonts, tmp_path, framing):
    sk = Sketch("figure-test", "Figure test", SPEAKERS, LINES, STILL, END)
    staging = replace(silent(sk), figures={"rabbit": framing})
    with pytest.raises(toon_sketch.StagingError, match="framing"):
        built(tmp_path, staging, pinned_fonts)
