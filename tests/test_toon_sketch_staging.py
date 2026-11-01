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

from srstudio import TOON, camera, craft, look, parts, sketch, toon, toon_sketch, usage
from srstudio.layout import VERTICAL
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


def test_the_opening_push_moves_the_first_shot_and_no_other(pinned_fonts, tmp_path):
    sk = Sketch("push-test", "Push test", SPEAKERS, LINES, STILL, END)
    _, xml = built(tmp_path, replace(silent(sk), camera=toon_sketch.opening_push(1.08)), pinned_fonts)
    shots = xml.findall(".//group[@id]")
    moved = [g.get("id") for g in shots if g.get("id", "").startswith("shot-") and g.find("animate") is not None]
    assert moved == ["shot-001"]
    with pytest.raises(toon_sketch.StagingError, match="above 1"):
        toon_sketch.opening_push(1.0)


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


def test_a_staging_asks_for_bleed_and_is_built_without_it_by_default(pinned_fonts, tmp_path):
    sk = Sketch("bleed-test", "Bleed test", SPEAKERS, LINES, STILL, END)
    far_plane = lambda shot: look.depth(shot.cv, shot.back, shot.cv.uid("far"), 5.0, overscan=True)  # noqa: E731
    off, _ = built(tmp_path / "off", replace(silent(sk), dress=far_plane), pinned_fonts)
    on, xml = built(tmp_path / "on", replace(silent(sk), dress=far_plane, bleed=True), pinned_fonts)
    assert off.cv.bleed is False
    assert b'threeD="true"' not in off.scene.to_bytes()
    assert on.cv.bleed is True
    far = [g for g in xml.iter("group") if g.get("threeD") == "true"]
    assert len(far) == len(sketch.appearances(STILL, END))  # every shot's far plane is on a sheet past the frame's edge
    assert all(float(g.get("scaleX")) > 1 for g in far)


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


def stage_sketch() -> Sketch:
    beats = (
        Beat(0.0, "rabbit", "She is still typing.", "wide", "flat", "desk", 0, 0),
        Beat(3.0, "bear", "Pepperoni.", "half", "smirk", "desk", 1, 0),
    )
    return Sketch("still-test", "Still test", SPEAKERS, LINES, beats, END)


def test_the_defaults_of_a_staging_change_nothing_for_a_toon_reel():
    st = silent(stage_sketch())
    assert (st.style, st.bare, st.captions, st.finish, st.output, st.crf) == (TOON, (), None, None, None, "17")


def test_a_bare_who_gets_no_figure(pinned_fonts, tmp_path):
    drawn, skipped = [], []

    def dress(shot):
        (skipped if shot.app.who == "bear" else drawn).append(shot.app.who)

    st = replace(silent(stage_sketch()), dress=dress, bare=("bear",))
    (tmp_path / "full").mkdir()
    (tmp_path / "bare").mkdir()
    full = built(tmp_path / "full", replace(st, bare=()), pinned_fonts)[1]
    bare = built(tmp_path / "bare", st, pinned_fonts)[1]
    assert drawn and skipped  # the dress still runs: it draws the whole frame of a bare shot
    assert len(list(bare.iter())) < len(list(full.iter()))


def test_a_sketch_can_name_its_bare_shots_itself(pinned_fonts, tmp_path):
    st = replace(silent(stage_sketch()), dress=lambda shot: None)
    declared = replace(st, sketch=replace(st.sketch, bare=("bear",)))
    (tmp_path / "staging").mkdir()
    (tmp_path / "sketch").mkdir()
    on_staging = built(tmp_path / "staging", replace(st, bare=("bear",)), pinned_fonts)[1]
    on_sketch = built(tmp_path / "sketch", declared, pinned_fonts)[1]
    assert len(list(on_sketch.iter())) == len(list(on_staging.iter()))


def test_an_overlay_is_drawn_once_over_every_shot_and_under_the_captions(pinned_fonts, tmp_path):
    order, seen = [], []

    def overlay(cv, parent, beats, end, measure):
        order.append("overlay")
        seen.append((parent, tuple(beats), end, measure("x", 10.0)))
        cv.group(parent, "over-every-shot")

    def captions(cv, parent, lines, measure, tints):
        order.append("captions")

    st = replace(silent(stage_sketch()), overlay=overlay, captions=captions, finish=lambda cv, node: None)
    ep, xml = built(tmp_path, st, pinned_fonts)
    assert order == ["overlay", "captions"]
    parent, beats, end, width = seen[0]
    assert parent is ep.comp and end == END and width > 0 and len(beats) == 2
    assert [n for n in xml.iter() if n.get("id") == "over-every-shot"]


def test_a_dress_is_handed_the_mouths_of_the_recording_only_when_there_is_one(pinned_fonts, tmp_path):
    seen = []
    st = replace(silent(stage_sketch()), dress=lambda shot: seen.append(shot.mouths))
    built(tmp_path, st, pinned_fonts)
    assert seen and all(mouths == {} for mouths in seen)


def test_a_staging_can_declare_the_safe_area_a_show_keeps_its_text_in(pinned_fonts, tmp_path):
    ep, _ = built(tmp_path, replace(silent(stage_sketch()), safe_area=VERTICAL), pinned_fonts)
    assert ep.spec.safe_area is VERTICAL


def test_a_staging_can_bring_its_own_captions_grade_output_and_frame_rate(pinned_fonts, tmp_path):
    seen = []
    graded = []
    st = replace(
        silent(stage_sketch()),
        style=replace(TOON, fps=30),
        captions=lambda cv, parent, lines, measure, tints: seen.extend(line.text for line in lines),
        finish=lambda cv, node: graded.append(node),
        output="renders/pilots/still-test.mp4",
        crf="21",
    )
    _, xml = built(tmp_path, st, pinned_fonts)
    assert seen == [q.text for q in LINES] and len(graded) == 2
    outputs = [n for n in xml.iter() if n.tag.endswith("output")]
    assert len(outputs) == 1
    assert (outputs[0].get("path"), outputs[0].get("fps"), outputs[0].get("crf")) == (
        "renders/pilots/still-test.mp4",
        "30",
        "21",
    )


def test_captions_a_staging_brings_stay_off_the_cover(pinned_fonts, tmp_path):
    def captions(cv, parent, lines, measure, tints):
        return cv.group(parent, "my-captions")

    ep, _ = built(tmp_path, replace(silent(stage_sketch()), captions=captions), pinned_fonts)
    assert ("my-captions", "visible", "false") in ep._cover_hidden  # written into the cover variant by finish()


def test_a_move_keys_the_body_of_that_character_on_every_shot_of_theirs(pinned_fonts, tmp_path):
    """A figure can bend about its seat while the set stays still; the other character is left alone."""
    calls = []

    def bend(cv, body, app, beats):
        calls.append(app.who)
        cv.keys(body, "rotation", [(app.start, 0.0), (app.end, 20.0)], hold=False, local=False)

    sk = Sketch("moved", "Moved", SPEAKERS, LINES, STILL, END)
    _, moved = built(tmp_path / "moved", silent(sk, moves={"bear": bend}), pinned_fonts)
    _, still = built(tmp_path / "still", silent(sk), pinned_fonts)
    assert set(calls) == {"bear"}
    assert ET.tostring(moved).count(b"rotation") > ET.tostring(still).count(b"rotation")
