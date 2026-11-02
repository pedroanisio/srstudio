"""The shared Collage build with a group shot: a staging's casting is made from the beats the build draws (scripted
or voiced), every group-shot appearance draws the whole lineup in the same places, and a zoom lands on the
speaker's face in its place; the ``timer`` and ``flash`` events are known, and a flash is heard as a shutter."""

import os
import shutil
import xml.etree.ElementTree as ET
from dataclasses import replace
from pathlib import Path

import pytest

from srstudio import COLLAGE, collage, collage_sets, collage_sketch, foley, sketch
from srstudio.collage_group import Lineup, Place
from srstudio.collage_sketch import Staging, check_staging, make_sketch, solo, sound_effects, timed

PLACES = {"gary": Place(240.0, 1800.0, 0.55), "kai": Place(845.0, 1800.0, 0.56), "rosa": Place(540.0, 1800.0, 0.6)}
LINES = (
    sketch.Line("gary", "Natural, everyone!"),
    sketch.Line("rosa", "I am natural."),
    sketch.Line("gary", "Kai, headset off."),
)
BEATS, END = timed(
    LINES,
    (
        (1.6, "gary", 0, "open", "grin", "point", "timer"),
        (1.4, "rosa", 1, "half", "smug", "hold"),
        (1.8, "gary", 2, "wide", "o", "shrug", "zoom"),
        (0.8, "gary", "", "wide", "o", "shrug", "flash"),
    ),
    tail=1.0,
)


def still(eyes, mouth, arms):
    return ({"start": 0.0, "eyes": eyes, "mouth": mouth, "arms": arms},)


def casting(beats, end):
    """The whole sketch is one group shot; the lineup is made from the beats it is given."""
    return Lineup(
        PLACES,
        {
            "gary": still("open", "grin", "point"),
            "rosa": still("half", "flat", "hold"),
            "kai": still("side", "flat", "down"),
        },
        spans=((0.0, end),),
    )


def staging(cast=casting) -> Staging:
    sk = make_sketch("lineup-test", "Lineup test", ("gary", "rosa"), LINES, BEATS, END)
    return Staging(
        sk, 7, "d", "a", "n", collage_sketch.TINTS, {"gary": "living-room", "rosa": "living-room"}, cast=cast
    )


@pytest.fixture(scope="module")
def pinned_fonts() -> Path:
    """The pinned fonts folder of a generated Collage project (``SRSTUDIO_EPISODES``), or skip: the build measures
    its captions in the real font, and fetching it is network. With the pin in place, installing fetches nothing."""
    env = os.environ.get("SRSTUDIO_EPISODES")
    if not env:
        pytest.skip("set SRSTUDIO_EPISODES to the folder of generated episode projects")
    folder = Path(env) / "the-will" / "assets" / "fonts"
    if COLLAGE.font is None or not (folder / Path(COLLAGE.font.src).name).is_file():
        pytest.skip(f"no pinned Collage font in {folder}")
    return folder


def built(root: Path, st: Staging, fonts: Path):
    shutil.copytree(fonts, root / "assets" / "fonts")
    assert collage_sketch.build(root, st, ["--init"]) is None  # the script, not the library, ends the process
    ep = collage_sketch.build(root, st, [])
    assert ep is not None
    return ep


def test_a_staging_asks_for_bleed_and_is_built_without_it_by_default(pinned_fonts, tmp_path):
    assert built(tmp_path / "off", staging(), pinned_fonts).cv.bleed is False
    ep = built(tmp_path / "on", replace(staging(), bleed=True), pinned_fonts)
    assert ep.cv.bleed is True and b'threeD="true"' in ep.scene.to_bytes()


def test_every_group_shot_draws_the_whole_lineup_in_fixed_places_and_zooms_on_the_speaker(pinned_fonts, tmp_path):
    ep = built(tmp_path, staging(), pinned_fonts)
    root = ET.fromstring(ep.scene.to_bytes(layout="pretty"))
    shots = sketch.appearances(BEATS, END)

    def at(g, place) -> bool:
        x, y = place.transform()
        return (
            g.get("x") is not None
            and float(g.get("x")) == pytest.approx(x)
            and float(g.get("y")) == pytest.approx(y)
            and float(g.get("scaleX") or 1) == pytest.approx(place.scale)
        )

    for name, place in PLACES.items():
        # in every appearance, whoever speaks, and always in the same place
        assert sum(at(g, place) for g in root.iter("group")) == len(shots), name
    zoomed = [
        g
        for g in root.iter("group")
        if g.get("anchorX") is not None and g.find("animate[@property='scaleX']") is not None
    ]
    assert len(zoomed) == 1
    fx, fy = collage.face(collage.LOOKS["gary"])
    p = PLACES["gary"]
    x, y = p.transform()
    assert float(zoomed[0].get("anchorX")) == pytest.approx(x + fx * p.scale)
    assert float(zoomed[0].get("anchorY")) == pytest.approx(y + fy * p.scale)


def anchors_of_the_zoom(ep) -> tuple[float, float]:
    root = ET.fromstring(ep.scene.to_bytes(layout="pretty"))
    zoomed = [
        g
        for g in root.iter("group")
        if g.get("anchorX") is not None and g.find("animate[@property='scaleX']") is not None
    ]
    assert len(zoomed) == 1
    return float(zoomed[0].get("anchorX")), float(zoomed[0].get("anchorY"))


def test_a_staging_that_keeps_the_signature_pivots_its_zoom_inside_it(pinned_fonts, tmp_path):
    p = PLACES["gary"]
    x, y = p.transform()
    fx, fy = collage.face(collage.LOOKS["gary"])
    speaker = (x + fx * p.scale, y + fy * p.scale)
    scale = collage_sketch.ZOOM_SCALE
    expected = collage_sets.zoom_pivot("living-room", speaker, scale, height=collage.CAPTION_TOP)
    assert expected != speaker  # the speaker's own face would crop the shelf: the test has to tell them apart
    front = collage_sets.marks_box("living-room")[3]
    assert expected[1] + (front - expected[1]) * scale <= collage.CAPTION_TOP  # the shelf lands above the pill
    left = replace(staging(), keep_signature=True)
    assert anchors_of_the_zoom(built(tmp_path / "kept", left, pinned_fonts)) == pytest.approx(expected)
    assert anchors_of_the_zoom(built(tmp_path / "face", staging(), pinned_fonts)) == pytest.approx(speaker)


def test_the_casting_is_made_from_the_beats_the_build_draws(pinned_fonts, tmp_path):
    seen = []

    def spy(beats, end):
        seen.append((tuple(beats), end))
        return solo

    built(tmp_path, staging(spy), pinned_fonts)
    assert seen == [(tuple(BEATS), END)]


def test_the_default_casting_is_the_speaker_alone():
    st = Staging(staging().sketch, 7, "d", "a", "n", {}, {"gary": "living-room", "rosa": "living-room"})
    assert st.cast(BEATS, END) is solo


def test_timer_and_flash_are_known_events_and_a_flash_is_heard_as_a_shutter(tmp_path):
    check_staging(staging())  # the timer and flash beats pass
    effects = sound_effects(BEATS, END, tmp_path, 7)
    assert [e["id"] for e in effects] == ["whoosh", "shutter"]
    assert (tmp_path / effects[-1]["audio"]).is_file()


# -- the still opening (the sp-hook_motion test's arm a) --------------------------------------------------------------
STILL_LINES = (sketch.Line("gary", "I hike."), sketch.Line("rosa", "Where?"))
STILL_BEATS, STILL_END = timed(
    STILL_LINES,
    (
        (1.2, "rosa", "", "half", "smug", "hold"),  # the still frame: nobody speaks, nothing moves
        (1.4, "gary", 0, "open", "grin", "shrug"),
        (1.2, "rosa", 1, "half", "flat", "hold", "zoom"),
    ),
)


def still_staging(beats=STILL_BEATS, still=1.0, **kw) -> Staging:
    sk = make_sketch("still-test", "Still test", ("gary", "rosa"), STILL_LINES, beats, STILL_END)
    sets = {"gary": "cafe", "rosa": "cafe"}
    return Staging(sk, 7, "d", "a", "n", collage_sketch.TINTS, sets, still=still, **kw)


def test_a_push_runs_from_the_first_frame_across_the_cuts_inside_it(pinned_fonts, tmp_path):
    ep = built(tmp_path, still_staging(STILL_BEATS, 0.0, push=(2.0, 1.05)), pinned_fonts)
    xml = ep.scene.to_bytes(layout="pretty")
    assert xml.count(b'property="scaleX"') >= 2


@pytest.mark.parametrize(("push", "match"), [((-1.0, 1.1), "seconds"), ((1.0, 0.9), "scale")])
def test_a_push_refuses_what_is_no_push(push, match):
    with pytest.raises(collage_sketch.StagingError, match=match):
        collage_sketch.check_push(push, STILL_BEATS, "x")


def test_a_push_keeps_clear_of_a_zoom():
    beats = (sketch.Beat(0.0, "gary", "", "h", "f", "d"), sketch.Beat(1.0, "gary", "", "h", "f", "d", event="zoom"))
    with pytest.raises(collage_sketch.StagingError, match="inside the push"):
        collage_sketch.check_push((2.0, 1.1), beats, "x")
    collage_sketch.check_push((1.0, 1.1), beats, "x")


def test_a_pushed_first_shot_is_checked():
    check_staging(still_staging(still=0.0, first_shot_push=1.06))
    for kw, match in (
        ({"still": 0.0, "first_shot_push": 0.9}, "grow"),
        ({"still": 0.0, "first_shot_push": float("nan")}, "grow"),
        ({"still": 1.0, "first_shot_push": 1.06}, "not both"),
        ({"still": 0.0, "first_shot_push": 1.06, "push": (2.0, 1.05)}, "same keys"),
    ):
        with pytest.raises(collage_sketch.StagingError, match=match):
            check_staging(still_staging(**kw))
    zoomed = (replace(STILL_BEATS[0], event="zoom"), *STILL_BEATS[1:])
    with pytest.raises(collage_sketch.StagingError, match="crash zoom"):
        check_staging(still_staging(beats=zoomed, still=0.0, first_shot_push=1.06))


def test_a_still_opening_is_checked():
    check_staging(still_staging())
    check_staging(still_staging(still=0.0))  # no still opening: any first beat
    for beats, still, match in (
        (STILL_BEATS, -1.0, "still"),
        (STILL_BEATS, float("nan"), "still"),
        (STILL_BEATS, 1.5, "1.2"),  # the next beat starts inside the still second
        ((replace(STILL_BEATS[0], event="zoom"), *STILL_BEATS[1:]), 1.0, "silent"),
        ((replace(STILL_BEATS[0], caption="Hi"), *STILL_BEATS[1:]), 1.0, "silent"),
        ((replace(STILL_BEATS[0], who="gary"), *STILL_BEATS[1:]), 1.0, "cut"),
    ):
        with pytest.raises(collage_sketch.StagingError, match=match):
            check_staging(still_staging(beats, still))


def test_the_still_opening_draws_no_grain_and_no_keys_and_the_rest_keeps_both(pinned_fonts, tmp_path):
    seen = []

    def opening(cv, parent, app, mouths):
        seen.append(app.start)
        return collage_sketch.stilled(cv, parent, app, mouths)

    ep = built(tmp_path, still_staging(opening=opening), pinned_fonts)
    root = ET.fromstring(ep.scene.to_bytes(layout="pretty"))
    comp = next(root.iter("composition"))
    shots = [  # one group per appearance; the others are the caption pills
        g for g in comp.findall("group") if g.get("start") is not None and "caption" not in (g.get("effects") or "")
    ]
    assert len(shots) == len(sketch.appearances(STILL_BEATS, STILL_END))
    first = next(g for g in shots if float(g.get("start")) == 0.0)
    assert "collage-grain" not in (first.get("effects") or "")
    assert not list(first.iter("animate"))  # no breath, no blink, no lips, no camera: the first second is a still
    rest = [g for g in shots if float(g.get("start")) > 0.0]
    assert rest and all("collage-grain" in (g.get("effects") or "") for g in rest)
    assert all(list(g.iter("animate")) for g in rest)
    assert seen == [0.0]  # the staging's opening drawer drew the still shot, and only it


def test_a_staging_may_set_a_two_pass_bitrate_and_the_published_ones_do_not(pinned_fonts, tmp_path):
    def output(ep) -> dict:
        return dict(next(ET.fromstring(ep.scene.to_bytes(layout="pretty")).iter("output")).attrib)

    plain = output(built(tmp_path / "default", still_staging(), pinned_fonts))
    assert plain["crf"] == "17" and not {"bitrate", "twoPass", "maxBitrate"} & set(plain)  # every published reel
    sized = output(built(tmp_path / "sized", still_staging(bitrate=5_800_000), pinned_fonts))
    assert (sized["bitrate"], sized["twoPass"]) == ("5800000", "true") and "maxBitrate" not in sized
    for bad in (-1, 2.5, "5M", True):
        with pytest.raises(collage_sketch.StagingError, match="bitrate"):
            check_staging(still_staging(bitrate=bad))


def test_a_staging_s_own_sound_is_written_once_and_skipped_when_it_has_no_cue(tmp_path):
    burst = foley.Burst(0.2, 800.0)
    own = (collage_sketch.Sound("knock", burst, (1.0,), -6.0), collage_sketch.Sound("none", burst, ()))
    effects = sound_effects(BEATS, END, tmp_path, 7, own)
    assert [e["id"] for e in effects][-1] == "knock"
    assert "none" not in [e["id"] for e in effects]
    assert (tmp_path / effects[-1]["audio"]).is_file()


def test_a_thud_beat_plays_a_thud(tmp_path):
    beats = [
        sketch.Beat(0.0, "gary", "", "open", "flat", "down"),
        sketch.Beat(1.0, "gary", "", "open", "flat", "down", event="thud"),
    ]
    assert [e["id"] for e in sound_effects(beats, 3.0, tmp_path, 7)] == ["thud"]


def output(ep) -> dict:
    return dict(next(ET.fromstring(ep.scene.to_bytes(layout="pretty")).iter("output")).attrib)


def test_a_staging_may_set_its_keyframes_and_the_published_ones_do_not(pinned_fonts, tmp_path):
    assert "keyframeInterval" not in output(built(tmp_path / "default", still_staging(), pinned_fonts))
    set_ = output(built(tmp_path / "set", still_staging(keyframes=52 / 24), pinned_fonts))
    assert set_["keyframeInterval"] == "2.1667"
    for bad in (-1, "2", float("nan")):
        with pytest.raises(collage_sketch.StagingError, match="keyframes"):
            check_staging(still_staging(keyframes=bad))


def test_a_staging_may_turn_off_b_frames_and_the_published_ones_do_not(pinned_fonts, tmp_path):
    """0 is a setting here, not the unset value: the engine's default is the encoder's three."""
    assert "bFrames" not in output(built(tmp_path / "default", still_staging(), pinned_fonts))
    assert output(built(tmp_path / "set", still_staging(bframes=0), pinned_fonts))["bFrames"] == "0"
    for bad in (-1, 1.5, "0", True):
        with pytest.raises(collage_sketch.StagingError, match="bframes"):
            check_staging(still_staging(bframes=bad))


def test_an_overlay_is_drawn_once_over_every_shot_out_of_the_cameras_reach_and_under_the_captions(
    pinned_fonts, tmp_path
):
    seen = []

    def overlay(layer):
        seen.append(layer)
        g = layer.cv.group(layer.parent, "over-it-all")
        layer.cv.rect(g, 100.0, 240.0, 300.0, 84.0, "#15131f")
        return g

    st = replace(staging(), overlay=overlay)
    ep = built(tmp_path, st, pinned_fonts)
    assert len(seen) == 1
    layer = seen[0]
    assert layer.parent is ep.comp and layer.cv is ep.cv
    assert layer.beats == tuple(BEATS) and layer.end == END
    assert layer.first_line_end == sketch.line_spans(st.sketch)[0][1]
    assert layer.measure("HI", 54) > 0
    root = ET.fromstring(ep.scene.to_bytes(layout="pretty"))
    comp = root.find("composition")
    ids = [g.get("id") for g in comp.findall("group")]
    shots = sketch.appearances(BEATS, END)
    at = ids.index("over-it-all")  # a child of the composition, never of a shot and its zoom
    assert at >= len(shots)
    words = {t.get("id") for t in root.iter("text") if t.get("text")}
    later = {
        layer.get("asset")
        for g in list(comp)[list(comp).index(comp.findall("group")[at]) + 1 :]
        for layer in g.iter("layer")
    }
    assert words & later  # the captions come after it, so they stay on top
    assert "over-it-all" in [node for node, _, _ in ep._cover_hidden]


def test_no_overlay_draws_nothing_and_reads_nothing(pinned_fonts, tmp_path):
    assert collage_sketch.Staging.overlay is None
    ep = built(tmp_path, staging(), pinned_fonts)
    assert not (tmp_path / "voiced").exists()
    assert ep._cover_hidden == []


def test_the_first_line_ends_where_its_take_stops_speaking_and_not_where_the_file_does(tmp_path):
    st = staging()
    letters = tuple("Natural, everyone!")
    starts = tuple(0.05 * i for i in range(len(letters)))
    ends = tuple(s + 0.05 for s in starts)
    takes = [
        sketch.Take("01", "gary", 0.25, 1.4, sketch.Alignment(letters, starts, ends)),
        sketch.Take("02", "rosa", 1.6, 1.0, sketch.Alignment(tuple("I"), (0.0,), (0.1,))),
    ]
    sketch.write_speech(tmp_path, takes, 3.0)
    assert collage_sketch.first_line_end(tmp_path, st.sketch, voiced=True) == pytest.approx(0.25 + 0.9)
    assert collage_sketch.first_line_end(tmp_path, st.sketch, voiced=False) == sketch.line_spans(st.sketch)[0][1]


def test_a_recording_with_no_first_take_is_refused(tmp_path):
    sketch.write_speech(tmp_path, [], 3.0)
    with pytest.raises(sketch.SketchError):
        collage_sketch.first_line_end(tmp_path, staging().sketch, voiced=True)
