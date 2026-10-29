"""Engine-native features: caption tracks with word timing, transitions between shots, effects and text animators,
built by the library instead of drawn by hand."""

from __future__ import annotations

import os
import shutil
import subprocess
import xml.etree.ElementTree as ET
from pathlib import Path

import pytest
from sr_core.scene import Scene, SchemaValueError

from srstudio import VERTICAL, Canvas, Timeline, native
from srstudio.native import CaptionLook, Cue, NativeError, Word
from srstudio.sample import SYSTEM_FONTS
from test_ink_layout import takes_data

FONT = next((f for f in SYSTEM_FONTS if f.exists()), Path("DejaVuSans-Bold.ttf"))


def canvas(duration=4.0, width=1080, height=1920, safe=True) -> tuple[Scene, Canvas, object]:
    scene = Scene(version="auto")
    project = scene.add_project(width=width, height=height, fps="30", duration=duration, background="#20303A")
    if safe:
        VERTICAL.declare(scene, project)
    output = scene.add_output(id="main", path="out.mp4", codec="h264", width=width, height=height, fps="30")
    cv = Canvas(scene, width=width, height=height)
    cv.assets.add_font(id="caption-font", src=FONT.name, family="DejaVu Sans", weight="700")
    return scene, cv, output


def root(scene: Scene) -> ET.Element:
    return ET.fromstring(scene.to_bytes())


CUES = [
    Cue(0.2, 1.8, "Where do you see", (Word("Where", 0.2, 0.6), Word("do", 0.6, 0.9), Word("you", 0.9, 1.2),
                                         Word("see", 1.2, 1.8))),
    Cue(2.0, 3.6, "In your chair.", (Word("In", 2.0, 2.6), Word("your", 2.6, 2.9), Word("chair.", 2.9, 3.6))),
]  # fmt: skip


# -- cues -------------------------------------------------------------------------------------------------------------
def test_cues_from_takes_place_each_word_on_the_scene_clock_and_skip_effects():
    t = Timeline.from_takes(takes_data())
    cues = native.cues_from_takes(t.takes)
    assert [c.text for c in cues] == ["Okay. Come on. Come on!", "Magenta!", "Aaargh!"]
    assert cues[0].words[0] == Word("Okay.", 0.02, 0.54)
    assert cues[1].start == pytest.approx(3.5) and cues[1].words == (Word("Magenta!", 3.5, 4.45),)
    assert cues[1].end == pytest.approx(4.45)


def long_take(text="Why are the walls of this trash compactor closing in on us today?", start=10.0):
    from srstudio.timeline import Take

    words = tuple({"text": w, "start": i * 0.3, "end": i * 0.3 + 0.25} for i, w in enumerate(text.split()))
    return Take("01", "narrator", "", text, start, 6.0, words=words)


def test_cues_fitted_to_a_look_split_a_long_take_at_words_into_cues_that_wrap_inside_it():
    look = CaptionLook(max_chars=24, max_lines=2)
    take = long_take()
    cues = native.cues_from_takes([take], look=look)
    assert len(cues) > 1
    assert " ".join(c.text for c in cues) == take.text  # every word, once, in order
    assert all(len(native.wrap(c.text, look.max_chars, look.max_words)) <= look.max_lines for c in cues)
    assert [w for c in cues for w in c.words] == list(native.cues_from_takes([take])[0].words)
    for c in cues:
        assert (c.start, c.end) == (c.words[0].start, c.words[-1].end)
    assert all(a.end <= b.start for a, b in zip(cues, cues[1:], strict=False))


def test_a_take_that_fits_stays_one_cue_and_without_a_look_nothing_is_split():
    short = long_take("Stop the walls!")
    assert native.cues_from_takes([short], look=CaptionLook()) == native.cues_from_takes([short])
    assert len(native.cues_from_takes([long_take()])) == 1


def test_a_take_without_word_timings_cannot_be_split_to_fit():
    from srstudio.timeline import Take

    bare = Take("01", "narrator", "", "Why are the walls of this trash compactor closing in on us today?", 0, 4.0)
    with pytest.raises(NativeError, match="word timings"):
        native.cues_from_takes([bare], look=CaptionLook())


def test_cues_from_phrases_carry_the_caption_text_without_words(project):
    t = Timeline.load(project / "dialogue.json")
    cues = native.cues_from_phrases(t.phrases)
    assert [c.text for c in cues] == [p.caption.replace("\n", " ") for p in t.phrases]
    assert all(not c.words for c in cues) and cues[0].start == t.phrases[0].start


# -- caption tracks ---------------------------------------------------------------------------------------------------
def test_a_caption_track_is_styled_placed_in_the_safe_area_and_burned():
    scene, cv, output = canvas()
    track = native.caption_track(scene, CUES, font_asset=cv.font_asset, safe_area=VERTICAL, width=1080, height=1920,
                                 output=output)  # fmt: skip
    doc = root(scene)
    el = doc.find("captions/captionTrack")
    assert track.id == el.get("id") == "captions" and el.get("preset") == "karaoke" and el.get("language") == "en-US"
    assert doc.find("output").get("burnCaptions") == "captions" and doc.find("output").get("captions") is None
    styles = {s.get("id"): s for s in doc.iterfind("styles/textStyle")}
    base, active = styles[el.get("style")], styles[el.get("activeStyle")]
    assert base.get("fontAsset") == "caption-font" and base.get("strokePosition") == "outside"
    assert active.get("basedOn") == base.get("id") and active.get("color") == CaptionLook().active
    region = VERTICAL.region(1080, 1920)
    centre, width = float(el.get("x").rstrip("%")) / 100 * 1080, float(el.get("width").rstrip("%")) / 100 * 1080
    assert centre == pytest.approx((region.x0 + region.x1) / 2, abs=1)
    assert centre - width / 2 >= region.x0 - 0.01 and centre + width / 2 <= region.x1 + 0.01
    look = CaptionLook()
    top = float(el.get("y").rstrip("%")) / 100 * 1920
    block = look.max_lines * look.size * look.line_height + 2 * look.stroke_width
    assert region.y0 <= top and top + block <= region.y1
    cues = el.findall("cue")
    assert [(c.get("start"), c.get("end"), c.get("text")) for c in cues] == [
        ("0.2", "1.8", "Where do you see"),
        ("2", "3.6", "In your chair."),
    ]
    assert [w.get("text") for w in cues[1].findall("word")] == ["In", "your", "chair."]


@pytest.mark.parametrize(
    "mode, burn, sidecar", [("burn", "captions", None), ("sidecar", None, "captions"), ("both", "captions", "captions")]
)
def test_the_mode_burns_writes_a_sidecar_or_both(mode, burn, sidecar):
    scene, cv, output = canvas()
    native.caption_track(scene, CUES, font_asset=cv.font_asset, safe_area=VERTICAL, width=1080, height=1920,
                         output=output, mode=mode)  # fmt: skip
    out = root(scene).find("output")
    assert (out.get("burnCaptions"), out.get("captions")) == (burn, sidecar)
    assert root(scene).find("captions/captionTrack").get("mode") == mode


def test_a_look_sets_the_preset_the_case_and_the_line_limits():
    scene, cv, output = canvas()
    look = CaptionLook(preset="pop", upper=True, max_words=3, max_chars=20, max_lines=1)
    native.caption_track(scene, CUES, look=look, font_asset=cv.font_asset, safe_area=None, width=1080, height=1920)
    el = root(scene).find("captions/captionTrack")
    assert (el.get("preset"), el.get("maxWordsPerLine"), el.get("maxCharsPerLine"), el.get("maxLines")) == (
        "pop", "3", "20", "1",
    )  # fmt: skip
    assert root(scene).find("styles/textStyle").get("textTransform") == "uppercase"
    assert el.get("safeArea") is None and el.get("x") is None  # the engine's own placement


def test_a_preset_the_engine_does_not_know_is_refused():
    scene, cv, output = canvas()
    with pytest.raises(SchemaValueError, match="preset"):
        native.caption_track(scene, CUES, look=CaptionLook(preset="sparkle"), font_asset=cv.font_asset,
                             safe_area=VERTICAL, width=1080, height=1920)  # fmt: skip


@pytest.mark.parametrize(
    "cues, match",
    [
        ([], "no cues"),
        ([Cue(1.0, 1.0, "x")], "ends"),
        ([Cue(-0.1, 1.0, "x")], "before 0"),
        ([Cue(0.0, 1.0, "  ")], "text"),
        ([Cue(0.0, 2.0, "a"), Cue(1.5, 3.0, "b")], "overlaps"),
        ([Cue(0.0, 1.0, "a"), Cue(0.5, 0.8, "b")], "overlaps"),
        ([Cue(0.0, 1.0, "a b", (Word("a", 0.0, 0.5), Word("b", 0.6, 1.4)))], "outside"),
        ([Cue(0.0, 1.0, "a b", (Word("a", 0.5, 0.9), Word("b", 0.1, 0.4)))], "order"),
        ([Cue(0.0, 1.0, "a", (Word("a", 0.4, 0.4),))], "ends"),
        ([Cue(0.0, 1.0, "a", (Word("", 0.1, 0.4),))], "text"),
        ([Cue(0.0, float("nan"), "a")], "finite"),
    ],
)
def test_cues_that_cannot_be_shown_are_refused(cues, match):
    scene, cv, _ = canvas()
    with pytest.raises(NativeError, match=match):
        native.caption_track(scene, cues, font_asset=cv.font_asset, safe_area=VERTICAL, width=1080, height=1920)
    assert root(scene).find("captions") is None  # nothing half-written


def test_a_caption_track_needs_a_font_and_an_output_to_burn_into():
    scene, cv, _ = canvas()
    with pytest.raises(NativeError, match="font"):
        native.caption_track(scene, CUES, font_asset=None, safe_area=VERTICAL, width=1080, height=1920)
    with pytest.raises(NativeError, match="output"):
        native.caption_track(scene, CUES, font_asset=cv.font_asset, safe_area=VERTICAL, width=1080, height=1920,
                             mode="sidecar")  # fmt: skip
    with pytest.raises(NativeError, match="mode"):
        native.caption_track(scene, CUES, font_asset=cv.font_asset, safe_area=VERTICAL, width=1080, height=1920,
                             mode="print")  # fmt: skip


@pytest.mark.parametrize(
    "changes, match",
    [(dict(size=0), "size"), (dict(max_lines=0), "max_lines"), (dict(stroke_width=-1), "stroke_width"),
     (dict(line_height=float("inf")), "line_height"), (dict(max_words=0), "max_words")],
)  # fmt: skip
def test_a_look_that_cannot_be_laid_out_is_refused(changes, match):
    with pytest.raises(NativeError, match=match):
        CaptionLook(**changes)


def test_a_look_too_tall_for_the_safe_area_is_refused():
    scene, cv, _ = canvas()
    with pytest.raises(NativeError, match="taller"):
        native.caption_track(scene, CUES, look=CaptionLook(size=400, max_lines=3), font_asset=cv.font_asset,
                             safe_area=VERTICAL, width=1080, height=1920)  # fmt: skip


# -- transitions ------------------------------------------------------------------------------------------------------
def shots(cv: Canvas):
    seq = cv.comp.add_sequence(id="shots")
    a = seq.add_group(id="shot-a", end=2.2)
    cv.rect(a, 70, 200, 400, 300, "#E6AA92")
    b = seq.add_group(id="shot-b", end=4.0)
    cv.ellipse(b, 120, 200, 300, 300, "#BFCFCA")
    return seq


def test_a_transition_joins_two_neighbouring_shots():
    scene, cv, _ = canvas()
    seq = shots(cv)
    native.transition(seq, "shot-a", "shot-b", "whip-pan", duration=0.4, direction="left")
    children = [c for c in root(scene).find("composition/sequence")]
    assert [c.tag for c in children] == ["group", "transition", "group"]
    t = children[1]
    assert (t.get("type"), t.get("from"), t.get("to"), t.get("duration"), t.get("direction")) == (
        "whip-pan", "shot-a", "shot-b", "0.4", "left",
    )  # fmt: skip


@pytest.mark.parametrize(
    "a, b, kw, match",
    [
        ("shot-a", "shot-x", {}, "no shot"),
        ("shot-b", "shot-a", {}, "follow"),
        ("shot-a", "shot-b", dict(duration=0), "duration"),
        ("shot-a", "shot-b", dict(duration=2.5), "longer"),  # shot-a lasts 2.2 s, shot-b 4.0 s
    ],
)
def test_a_transition_that_cannot_join_the_shots_is_refused(a, b, kw, match):
    _, cv, _ = canvas()
    seq = shots(cv)
    with pytest.raises(NativeError, match=match):
        native.transition(seq, a, b, "crossfade", **kw)
    with pytest.raises(SchemaValueError):
        native.transition(seq, "shot-a", "shot-b", "teleport")


# -- effects and text animators ---------------------------------------------------------------------------------------
def test_an_effect_is_declared_once_and_applied_to_any_node():
    scene, cv, _ = canvas()
    layer = cv.text(cv.comp, "punch", "JUST THE CHAIR.", 100, 220, 700, 120, 80)
    assert cv.effect("shadow", "drop-shadow", offsetX=6, offsetY=8) == "shadow"
    assert cv.effect("shadow", "drop-shadow", offsetX=6, offsetY=8) == "shadow"
    cv.effect("soft", "glow", radius=12)
    cv.apply(layer, "shadow")
    cv.apply(layer, "soft", "shadow")
    doc = root(scene)
    assert [(e.get("id"), e.get("type")) for e in doc.iterfind("effects/effect")] == [
        ("shadow", "drop-shadow"),
        ("soft", "glow"),
    ]
    assert doc.find(".//layer[@id='punch-layer']").get("effects") == "shadow soft"
    with pytest.raises(NativeError, match="no effect"):
        cv.apply(layer, "missing")
    with pytest.raises(NativeError, match="already"):
        cv.effect("shadow", "glow")


def test_a_text_animator_animates_a_text_layer():
    scene, cv, _ = canvas()
    layer = cv.text(cv.comp, "punch", "JUST THE CHAIR.", 100, 220, 700, 120, 80)
    cv.animate_text(layer, "pop", presetStart=0.5, unit="word")
    a = root(scene).find(".//layer[@id='punch-layer']/textAnimator")
    assert (a.get("preset"), a.get("presetStart"), a.get("unit")) == ("pop", "0.5", "word")
    with pytest.raises(NativeError, match="text layer"):
        cv.animate_text(cv.comp.add_group(id="g"), "pop")


# -- the engine renders them ------------------------------------------------------------------------------------------
def engine() -> Path:
    found = os.environ.get("SRSTUDIO_ENGINE") or shutil.which("scene-render")
    if not found or not Path(found).exists():
        pytest.skip("set SRSTUDIO_ENGINE to a scene-render binary")
    if not shutil.which("ffmpeg"):
        pytest.skip("ffmpeg is required to read the rendered frames")
    if not FONT.exists():
        pytest.skip("DejaVu Sans Bold is required; install fonts-dejavu-core")
    return Path(found).resolve()  # the encode test runs in its own directory


def full_scene(tmp_path: Path, mode="burn") -> Path:
    scene, cv, output = canvas()
    seq = shots(cv)
    native.transition(seq, "shot-a", "shot-b", "crossfade", duration=0.4)
    layer = cv.text(cv.comp, "punch", "JUST THE CHAIR.", 100, 240, 700, 120, 70, color="#F4D492")
    cv.apply(layer, cv.effect("shadow", "drop-shadow"))
    cv.animate_text(layer, "pop")
    native.caption_track(scene, CUES, font_asset=cv.font_asset, safe_area=VERTICAL, width=1080, height=1920,
                         output=output, mode=mode)  # fmt: skip
    shutil.copy(FONT, tmp_path / FONT.name)
    path = tmp_path / "native.scene.xml"
    path.write_bytes(scene.to_bytes())
    return path


def frame(path: Path, t: float, variant: str | None = None) -> tuple[bytes, int]:
    png = path.with_name(f"t{t}{variant or ''}.png")
    picked = ["--variant", variant] if variant else []
    subprocess.run(
        [str(engine()), "render", *picked, "-t", str(t), "-o", str(png), str(path)], check=True, capture_output=True
    )
    raw = subprocess.run(
        ["ffmpeg", "-loglevel", "error", "-i", str(png), "-f", "rawvideo", "-pix_fmt", "rgb24", "-"],
        check=True,
        capture_output=True,
    ).stdout
    return raw, 1080


def pixels(raw: bytes, width: int, box: tuple[int, int, int, int]) -> list[tuple[int, int, int]]:
    x0, y0, x1, y1 = box
    return [
        tuple(raw[(y * width + x) * 3 : (y * width + x) * 3 + 3]) for y in range(y0, y1, 2) for x in range(x0, x1, 2)
    ]


def near(p, colour: str, tol=24) -> bool:
    rgb = tuple(int(colour[i : i + 2], 16) for i in (1, 3, 5))
    return all(abs(a - b) <= tol for a, b in zip(p, rgb, strict=True))


def test_the_engine_validates_the_native_features_inside_the_safe_area(tmp_path):
    path = full_scene(tmp_path)
    check = subprocess.run([str(engine()), "validate", "--deny-warnings", str(path)], capture_output=True, text=True)
    assert check.returncode == 0, check.stdout + check.stderr


def test_the_engine_sings_the_words_crossfades_the_shots_and_writes_the_sidecar(tmp_path):
    path = full_scene(tmp_path, mode="both")
    caption_box = (60, 1100, 920, 1420)
    before, _ = frame(path, 0.1)
    assert not any(near(p, "#FFFFFF") or near(p, CaptionLook().active) for p in pixels(before, 1080, caption_box))
    sung, _ = frame(path, 0.7)  # "Where" sung (the preset fades each word in over its span), "see" still to come
    caption = pixels(sung, 1080, caption_box)
    assert any(near(p, CaptionLook().active) for p in caption) and any(near(p, "#FFFFFF") for p in caption)
    middle = pixels(frame(path, 2.2)[0], 1080, (300, 330, 340, 370))  # inside both shapes
    a, b = (
        pixels(frame(path, 1.5)[0], 1080, (300, 330, 340, 370)),
        pixels(frame(path, 3.0)[0], 1080, (300, 330, 340, 370)),
    )
    assert near(a[0], "#E6AA92", 4) and near(b[0], "#BFCFCA", 4)
    assert not near(middle[0], "#E6AA92", 8) and not near(middle[0], "#BFCFCA", 8)  # a mix of the two
    subprocess.run([str(engine()), "encode", str(path)], check=True, capture_output=True, cwd=tmp_path)
    vtt = (tmp_path / "out.captions.en-US.vtt").read_text()
    assert "Where do you see" in vtt and "00:00:02.000 --> 00:00:03.600" in vtt


# -- episodes ---------------------------------------------------------------------------------------------------------
def takes_episode(tmp_path: Path):
    from srstudio import INK, Episode, EpisodeSpec

    if not FONT.exists():
        pytest.skip("DejaVu Sans Bold is required; install fonts-dejavu-core")
    (tmp_path / "timeline.json").write_text(__import__("json").dumps(takes_data()))
    (tmp_path / "assets").mkdir()
    shutil.copy(FONT, tmp_path / "assets" / "caption.ttf")
    return Episode(
        EpisodeSpec(slug="router", title="t", description="t", root=tmp_path, seed=2, style=INK,
                    font="assets/caption.ttf", safe_area=VERTICAL, signature=False)
    )  # fmt: skip


def test_an_episode_burns_native_captions_from_its_takes(tmp_path):
    ep = takes_episode(tmp_path)
    shots = ep.sequence()
    for take in ep.takes:
        ep.shot(shots, take)
    track = ep.native_captions(look=CaptionLook(preset="highlight"))
    out = ep.finish(tmp_path / "scene.xml")
    doc = ET.parse(out).getroot()
    spoken = [t for t in ep.takes if not t.is_effect]
    assert track.id == "captions" and doc.find("output").get("burnCaptions") == "captions"
    assert len(doc.findall("captions/captionTrack/cue")) == len(spoken)
    assert doc.find("captions/captionTrack").get("language") == ep.spec.language
    assert ep.caption_specs == [(c.start, c.end, c.text, f"captions-{i + 1}") for i, c in
                                enumerate(native.cues_from_takes(ep.takes))]  # fmt: skip


def test_an_episode_refuses_a_caption_wider_than_its_safe_area(tmp_path):
    ep = takes_episode(tmp_path)
    with pytest.raises(NativeError, match="wider"):
        ep.native_captions(look=CaptionLook(size=120, max_chars=40))


def test_the_engine_accepts_an_episode_with_native_captions_in_its_safe_area(tmp_path):
    ep = takes_episode(tmp_path)
    shots = ep.sequence()
    for take in ep.takes:
        ep.shot(shots, take)
    ep.native_captions(look=CaptionLook(upper=True, max_chars=18))  # capitals are wider
    out = ep.finish(tmp_path / "scene.xml")
    check = subprocess.run([str(engine()), "validate", "--deny-warnings", str(out)], capture_output=True, text=True)
    assert check.returncode == 0, check.stdout + check.stderr
    raw, width = frame(out, 4.4)  # "MAGENTA!" sung (3.5-4.45 s)
    region = VERTICAL.region(ep.spec.width, ep.spec.height)  # the Ink frame is square
    box = (int(region.x0), int(region.y0), int(region.x1), int(region.y1))
    assert any(near(p, CaptionLook().active) for p in pixels(raw, width, box))


def test_native_captions_hidden_on_the_cover_leave_its_still_clean_and_the_video_captioned(tmp_path):
    ep = takes_episode(tmp_path)
    shots = ep.sequence()
    for take in ep.takes:
        ep.shot(shots, take)
    ep.hide_on_cover(ep.native_captions())
    out = ep.finish(tmp_path / "scene.xml")
    check = subprocess.run([str(engine()), "validate", "--deny-warnings", str(out)], capture_output=True, text=True)
    assert check.returncode == 0, check.stdout + check.stderr
    region = VERTICAL.region(ep.spec.width, ep.spec.height)
    box = (int(region.x0), int(region.y0), int(region.x1), int(region.y1))
    sung = [near(p, CaptionLook().active) for p in pixels(*frame(out, 4.4), box)]
    cover = [near(p, CaptionLook().active) for p in pixels(*frame(out, 4.4, "cover"), box)]
    assert any(sung) and not any(cover)


# -- the feature map --------------------------------------------------------------------------------------------------
def test_the_engine_feature_map_names_real_apis_and_real_tests():
    import importlib
    import json
    import re

    repo = Path(__file__).resolve().parents[1]
    data = json.loads((repo / "docs" / "engine-features.json").read_text())
    assert re.fullmatch(r"\d+\.\d+\.\d+", data["version"]) and (repo / data["decision"]).exists()
    for f in data["features"]:
        assert f["status"] in ("adopted", "hand-rolled", "not-used"), f["feature"]
        assert f["status"] != "adopted" or f["verified_by"], f"{f['feature']}: adopted without a test"
        for name in f["library"]:
            parts = name.split(".")
            for k in range(len(parts), 0, -1):  # the longest importable module, then attributes
                try:
                    obj = importlib.import_module(".".join(parts[:k]))
                except ImportError:
                    continue
                for attr in parts[k:]:
                    obj = getattr(obj, attr)
                break
            else:
                pytest.fail(f"{name} does not import")
        for test in f["verified_by"]:
            path, _, func = test.partition("::")
            assert f"def {func}(" in (repo / path).read_text(), test


def test_a_shot_end_is_its_length_so_a_transition_fits_shots_after_the_first():
    # Each child of a <sequence> lasts its own `end` (rendered: two 1 s shots show the second at 1.5 s).
    scene, cv, _ = canvas()
    seq = cv.comp.add_sequence(id="shots")
    for name, length in (("a", 1.5), ("b", 1.5), ("c", 1.0)):
        seq.add_group(id=f"shot-{name}", end=length)
    native.transition(seq, "shot-b", "shot-c", "crossfade", duration=0.3)
    with pytest.raises(NativeError, match="longer"):
        native.transition(seq, "shot-a", "shot-b", "crossfade", duration=1.6)
