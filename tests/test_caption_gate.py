"""The caption gate (ADR 0048): a new reel's captions must use a look the operator approved for its style, and the
rendered frames must keep the letters' counters open. A plain contrast ratio passes dark letters that close up, so
the frames are measured by the counters themselves; published reels are grandfathered in a closed list."""

import hashlib
import importlib.util
import os
import shutil
import subprocess
from pathlib import Path

import numpy as np
import pytest

from srstudio import caption_gate, native
from srstudio.caption_gate import Approval, ApprovedLook, CaptionGateError, Legibility
from srstudio.releases import Release, ReleaseError, grandfathered
from srstudio.social import InstagramPost

INK, WHITE, GOLD, FLOOR = (0x12, 0x14, 0x15), (255, 255, 255), (0xF4, 0xD4, 0x92), (0xA8, 0x9B, 0xC0)
OK = Approval("operator", "2026-10-30", "shipped in the test reel")
WHITE_LOOK = ApprovedLook("Test", "white", ("#FFFFFF",), "#F4D492", "#121415", 8, (100, 300), "proof", OK)
DARK_LOOK = ApprovedLook("Test", "dark", ("#121415",), None, None, 0, (100, 300), "proof", OK)
POST = InstagramPost(title="A title", description="A description.")


def glyphs(fill, outer=22, counter=9, halo=None, halo_width=0, floor=FLOOR, count=8, size=(150, 1000)):
    """A band of letter-like rings on ``floor``: each ``outer`` px in radius around a counter of ``counter`` px, with
    a ``halo`` ring of ``halo_width`` px outside the letter that also fills the counter."""
    h, w = size
    frame = np.full((h, w, 3), floor, dtype=np.uint8)
    ys, xs = np.mgrid[0:h, 0:w]
    for i in range(count):
        d = np.hypot(xs - (80 + i * 110), ys - h / 2)
        if halo is not None:
            frame[d <= outer + halo_width] = halo
        frame[d <= outer] = fill
        frame[d <= counter] = halo if halo is not None else floor
    return frame


def many(frame, n=4):
    return [frame] * n


# -- the measure --------------------------------------------------------------------------------------------------
def test_open_dark_letters_pass_and_the_same_letters_fattened_shut_fail():
    open_letters = caption_gate.measure_frames(many(glyphs(INK, 22, 9)), DARK_LOOK)
    shut_letters = caption_gate.measure_frames(many(glyphs(INK, 24, 3)), DARK_LOOK)
    assert open_letters.ratio > caption_gate.MIN_COUNTERS
    assert shut_letters.ratio < caption_gate.MIN_COUNTERS
    assert open_letters.frames == 4


def test_white_letters_with_a_dark_halo_pass_on_a_pale_floor():
    pale = (0xE6, 0xDD, 0xF0)
    measured = caption_gate.measure_frames(many(glyphs(WHITE, 22, 8, INK, 8, floor=pale)), WHITE_LOOK)
    assert measured.ratio > caption_gate.MIN_COUNTERS


def test_the_counter_of_a_letter_needs_contrast_with_the_letter():
    """A counter closed to a smear of nearly the letter's own tone is not an open counter."""
    smear = (0x40, 0x42, 0x44)
    measured = caption_gate.measure_frames(many(glyphs(INK, 22, 9, floor=smear)), DARK_LOOK)
    assert measured.counters == 0


def test_the_floor_is_not_letters_even_when_it_is_nearly_the_fill_colour():
    frame = glyphs(WHITE, 22, 8, INK, 8)
    frame[:, 600:] = (0xF0, 0xF0, 0xF4)  # a pale tile reaching the band's edges
    measured = caption_gate.measure_frames(many(frame), WHITE_LOOK)
    assert measured.ratio > caption_gate.MIN_COUNTERS


def test_a_large_enclosure_is_a_panel_not_a_counter():
    frame = np.full((150, 1000, 3), (250, 250, 250), dtype=np.uint8)
    frame[30:120, 100:900] = INK
    frame[36:114, 106:894] = (250, 250, 250)  # a dark-bordered pale card, as Collage draws its pill
    measured = caption_gate.measure_frames(many(frame), DARK_LOOK)
    assert measured.counters == 0


def test_the_sung_words_colour_and_its_fade_are_letters_too():
    between = tuple((a + b) // 2 for a, b in zip(WHITE, GOLD, strict=True))
    frames = [glyphs(c, 22, 8, INK, 8) for c in (WHITE, GOLD, between)]
    measured = caption_gate.measure_frames(frames, WHITE_LOOK)
    assert measured.frames == 3 and measured.ratio > caption_gate.MIN_COUNTERS


def test_a_band_without_letters_measures_nothing_and_cannot_pass():
    blank = caption_gate.measure_frames(many(np.full((150, 1000, 3), FLOOR, dtype=np.uint8)), DARK_LOOK)
    assert blank == Legibility(0, 4, 0, 0) and blank.ratio == 0.0
    assert not blank.passes
    assert not Legibility(caption_gate.MIN_FRAMES - 1, 9, 1000, 900).passes  # too few frames to judge
    assert Legibility(caption_gate.MIN_FRAMES, 9, 1000, 100).passes


# -- the record ---------------------------------------------------------------------------------------------------
@pytest.mark.parametrize(
    "kw",
    [
        dict(fills=("#121415",), stroke="#121415"),  # the defect: a stroke in the letters' own colour
        dict(fills=("#FFFFFF", "#12141a"), stroke="#12141A"),  # in another case
        dict(fills=()),
        dict(fills=("white",)),
        dict(stroke="ink"),
        dict(stroke=None),  # a width without a colour
        dict(stroke_width=-1),
        dict(zone=(300, 100)),
        dict(proof=""),
        dict(style=""),
        dict(name=""),
    ],
)
def test_a_look_that_is_not_recordable_is_refused(kw):
    good = dict(style="Test", name="x", fills=("#FFFFFF",), active=None, stroke="#121415", stroke_width=8,
                zone=(100, 300), proof="p")  # fmt: skip
    with pytest.raises(CaptionGateError):
        ApprovedLook(**{**good, **kw})


def test_an_approval_names_who_and_when():
    with pytest.raises(CaptionGateError):
        Approval("", "2026-10-30", "x")
    with pytest.raises(CaptionGateError):
        Approval("operator", "yesterday", "x")


def test_the_recorded_looks_are_unique_and_none_is_the_black_look():
    named = [(look.style, look.name) for look in caption_gate.LOOKS]
    assert len(named) == len(set(named))
    assert not any(look.stroke in look.fills for look in caption_gate.LOOKS)


def test_a_native_look_with_a_stroke_in_the_letters_colour_is_refused_for_new_reels():
    with pytest.raises(native.NativeError, match="stroke"):
        native.CaptionLook(color="#121415", active="#F4D492", stroke="#121415", stroke_width=2)
    with pytest.raises(native.NativeError, match="stroke"):
        native.CaptionLook(color="#FFFFFF", active="#121415", stroke="#121415")  # the sung word disappears
    native.CaptionLook(color="#121415", active="#121415", stroke="#121415", stroke_width=0)  # no stroke at all
    native.CaptionLook(color="#121415", active="#121415", stroke="#121415", stroke_width=2, published=True)


def test_the_black_look_stays_only_for_the_reels_published_with_it():
    from srstudio import gloss_reel

    assert gloss_reel.LOOK_INK.published
    assert gloss_reel.LOOK_INK.color == gloss_reel.LOOK_INK.stroke  # byte for byte what G8 and G9 were built with


# -- the scene ----------------------------------------------------------------------------------------------------
NATIVE_SCENE = """<scene version="1.1">
  <project width="1000" height="1000" fps="24" duration="10"/>
  <styles>
    <textStyle id="captions-text" size="50" color="{fill}" lineHeight="1.14"
      strokeColor="{stroke}" strokeWidth="{width}"/>
    <textStyle id="captions-active" basedOn="captions-text" color="{active}"/>
  </styles>
  <output id="main" burnCaptions="captions"/>
  <composition/>
  <captions>
    <captionTrack id="captions" style="captions-text" activeStyle="captions-active" maxLines="2" y="15%"/>
  </captions>
</scene>"""
LAYER_SCENE = """<scene version="1.1">
  <project width="1000" height="1000" fps="24" duration="10"/>
  <assets>
    <text id="a" text="One" width="1000" height="80" size="50" color="#121415"/>
    <text id="b" text="Two" width="1000" height="80" size="50" color="#121415"/>
    <text id="c" text="SIGN" width="100" height="30" size="20" color="#121415"/>
  </assets>
  <composition>
    <layer id="a-l" asset="a" x="0" y="120"/>
    <group id="g"><layer id="b-l" asset="b" x="0" y="200"/></group>
    <layer id="c-l" asset="c" x="0" y="700"/>
  </composition>
</scene>"""


def native_scene(tmp_path, fill="#FFFFFF", active="#F4D492", stroke="#121415", width=8):
    path = tmp_path / "s.scene.xml"
    path.write_text(NATIVE_SCENE.format(fill=fill, active=active, stroke=stroke, width=width))
    return path


def test_the_look_of_a_burned_track_is_read_from_the_scene_and_gives_the_band(tmp_path):
    band = caption_gate.band_of(native_scene(tmp_path), WHITE_LOOK)
    assert band == (150 - caption_gate.BAND_PAD, round(150 + 2 * 50 * 1.14 + 16) + caption_gate.BAND_PAD)


def test_another_track_look_is_not_the_recorded_one(tmp_path):
    assert caption_gate.band_of(native_scene(tmp_path, fill="#FFEEDD"), WHITE_LOOK) is None
    assert caption_gate.band_of(native_scene(tmp_path, width=6), WHITE_LOOK) is None
    assert caption_gate.band_of(native_scene(tmp_path, stroke="#000000"), WHITE_LOOK) is None
    assert caption_gate.band_of(native_scene(tmp_path, active="#00FF00"), WHITE_LOOK) is None


def test_a_track_outside_the_looks_zone_is_not_that_look(tmp_path):
    moved = ApprovedLook("Test", "low", ("#FFFFFF",), "#F4D492", "#121415", 8, (600, 900), "proof", OK)
    assert caption_gate.band_of(native_scene(tmp_path), moved) is None


def test_caption_layers_are_found_by_their_paint_inside_the_zone(tmp_path):
    path = tmp_path / "s.scene.xml"
    path.write_text(LAYER_SCENE)
    assert caption_gate.band_of(path, DARK_LOOK) == (120 - caption_gate.BAND_PAD, 280 + caption_gate.BAND_PAD)


def test_a_drawn_look_is_lettering_in_a_scene_without_text(tmp_path):
    drawn = ApprovedLook("Test", "drawn", ("#FFFFFF",), None, None, 0, (100, 300), "proof", OK, drawn=True)
    plain = tmp_path / "plain.scene.xml"
    plain.write_text('<scene><composition><shape id="a"/></composition></scene>')
    assert caption_gate.band_of(plain, drawn) == (100, 300)
    assert caption_gate.band_of(native_scene(tmp_path), drawn) is None
    layered = tmp_path / "layered.scene.xml"
    layered.write_text(LAYER_SCENE)
    assert caption_gate.band_of(layered, drawn) is None


def test_a_scene_that_cannot_be_read_is_a_gate_error(tmp_path):
    path = tmp_path / "s.scene.xml"
    path.write_text("<scene")
    with pytest.raises(CaptionGateError):
        caption_gate.band_of(path, WHITE_LOOK)


# -- one reel -----------------------------------------------------------------------------------------------------
def fake_frames(frames):
    return lambda video, band, **kw: iter(frames)


def reel(tmp_path, **kw):
    video = tmp_path / "v.mp4"
    video.write_bytes(b"mp4")
    return dict(scene=native_scene(tmp_path, **kw), video=video, looks=(WHITE_LOOK,))


def test_an_approved_look_with_open_counters_passes(tmp_path):
    frames = fake_frames(many(glyphs(WHITE, 22, 8, INK, 8)))
    assert caption_gate.check_reel("Test", **reel(tmp_path), read=frames) == []


def test_a_reel_that_declares_no_style_or_an_unrecorded_one_fails(tmp_path):
    assert "declares no style" in caption_gate.check_reel("", **reel(tmp_path))[0]
    assert "no caption look is approved" in caption_gate.check_reel("Other", **reel(tmp_path))[0]


def test_an_unapproved_look_fails_before_anything_is_decoded(tmp_path):
    def never(*a, **kw):
        raise AssertionError("no frame is read for a look that is not approved")

    problems = caption_gate.check_reel("Test", **reel(tmp_path, fill="#FFEEDD"), read=never)
    assert len(problems) == 1 and "not an approved look" in problems[0]


def test_a_proposed_look_is_no_look_until_the_operator_approves_it(tmp_path):
    proposed = ApprovedLook("Test", "new", ("#FFFFFF",), "#F4D492", "#121415", 8, (100, 300), "proof")
    assert not proposed.approved
    args = {**reel(tmp_path), "looks": (proposed,)}
    assert "not been approved" in caption_gate.check_reel("Test", **args)[0]


def test_a_burned_stroke_in_the_letters_own_colour_is_refused_by_name(tmp_path):
    problems = caption_gate.check_reel("Test", **reel(tmp_path, fill="#121415", active="#121415", width=2))
    assert any("the letters' own colour" in p for p in problems)


def test_closed_counters_fail_with_the_number(tmp_path):
    dark = ApprovedLook("Test", "dark", ("#FFFFFF",), "#F4D492", "#121415", 8, (100, 300), "proof", OK)
    frames = fake_frames(many(glyphs(WHITE, 24, 3, INK, 8)))
    args = {**reel(tmp_path), "looks": (dark,)}
    problems = caption_gate.check_reel("Test", **args, read=frames)
    assert len(problems) == 1 and "counters" in problems[0] and f"{caption_gate.MIN_COUNTERS}" in problems[0]


def test_too_few_measured_frames_fail(tmp_path):
    frames = fake_frames([np.full((150, 1000, 3), FLOOR, dtype=np.uint8)] * 9)
    problems = caption_gate.check_reel("Test", **reel(tmp_path), read=frames)
    assert len(problems) == 1 and "0 of 9 frames" in problems[0]


def test_a_missing_scene_or_video_fails(tmp_path):
    args = reel(tmp_path)
    assert "no scene" in caption_gate.check_reel("Test", args["scene"].with_name("x"), args["video"])[0]
    assert "no render" in caption_gate.check_reel("Test", args["scene"], args["video"].with_name("x"))[0]


def test_frames_are_read_from_the_video_with_ffmpeg(tmp_path):
    if shutil.which("ffmpeg") is None:
        pytest.skip("needs ffmpeg")
    video = tmp_path / "v.mp4"
    subprocess.run(["ffmpeg", "-v", "error", "-f", "lavfi", "-i", "color=c=white:s=64x64:d=2:r=10", "-pix_fmt",
                    "yuv420p", str(video)], check=True)  # fmt: skip
    frames = list(caption_gate.read_frames(video, (11, 31), width=64))  # snapped to even rows
    assert len(frames) == 2 and frames[0].shape == (22, 64, 3) and frames[0].min() > 240


# -- the releases -------------------------------------------------------------------------------------------------
def project(tmp_path, slug, **kw):
    folder = tmp_path / "episodes" / slug
    folder.mkdir(parents=True)
    (folder / f"{slug}.scene.xml").write_text(native_scene(tmp_path, **kw).read_text())
    (tmp_path / "renders").mkdir(exist_ok=True)
    (tmp_path / "renders" / f"{slug}.mp4").write_bytes(b"mp4")


def test_a_grandfathered_release_is_not_gated_and_a_new_one_is(tmp_path):
    black = dict(fill="#121415", active="#121415", width=2)
    project(tmp_path, "old-black", **black)
    project(tmp_path, "new-black", **black)
    releases = {slug: Release(slug, POST, style="Test") for slug in ("old-black", "new-black")}
    drift = caption_gate.check_releases(
        releases, tmp_path / "renders", tmp_path / "episodes", grandfathered=frozenset({"old-black"}),
        looks=(WHITE_LOOK,),
    )  # fmt: skip
    assert {d.name for d in drift} == {"new-black"}
    assert any("own colour" in d.reason for d in drift)


def test_only_narrows_the_gate_to_the_videos_being_delivered(tmp_path):
    project(tmp_path, "one", fill="#FFEEDD")
    project(tmp_path, "two", fill="#FFEEDD")
    releases = {slug: Release(slug, POST, style="Test") for slug in ("one", "two")}
    drift = caption_gate.check_releases(
        releases, tmp_path / "renders", tmp_path / "episodes", grandfathered=frozenset(), looks=(WHITE_LOOK,),
        only=["two"],
    )  # fmt: skip
    assert {d.name for d in drift} == {"two"}


def _instagram_posts():
    path = Path(__file__).resolve().parents[1] / "episodes" / "instagram_posts.py"
    spec = importlib.util.spec_from_file_location("instagram_posts_for_gate", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_every_published_release_is_grandfathered_or_gated_and_the_list_is_closed():
    """The list is closed: it holds the reels published when the gate arrived, and a new reel never joins it."""
    posts = _instagram_posts()
    assert set(posts.GRANDFATHERED) <= set(posts.RELEASES)
    assert {"gloss-notifications", "gloss-fewer-meetings", "gloss-terms"} <= set(posts.GRANDFATHERED)
    digest = hashlib.sha256("\n".join(sorted(posts.GRANDFATHERED)).encode()).hexdigest()
    assert digest == GRANDFATHERED_SHA256
    for slug, release in posts.RELEASES.items():
        if slug not in posts.GRANDFATHERED:
            assert release.style, f"{slug} is new: declare its style"


def test_the_deliver_path_refuses_a_new_reel_before_writing_anything(tmp_path, monkeypatch):
    posts = _instagram_posts()
    project(tmp_path, "new-reel", fill="#FFEEDD")
    monkeypatch.setattr(posts, "RELEASES", {"new-reel": Release("new-reel", POST, style="Saga")})
    monkeypatch.setattr(posts, "publish", lambda *a, **kw: pytest.fail("the gate must refuse before delivering"))
    out = tmp_path / "ig"
    with pytest.raises(posts.DeliveryError, match="caption gate"):
        posts.write_all(out, tmp_path / "renders", fonts_dir=tmp_path, engine="engine")
    assert not out.exists()


def test_the_check_path_reports_a_new_reel(tmp_path, monkeypatch):
    posts = _instagram_posts()
    project(tmp_path, "new-reel", fill="#FFEEDD")
    release = Release("new-reel", POST, style="Saga", characters={})
    monkeypatch.setattr(posts, "RELEASES", {"new-reel": release})
    monkeypatch.setattr(posts, "check_delivery", lambda *a, **kw: [])
    monkeypatch.setattr(posts, "font_file", lambda folder: folder)
    monkeypatch.setattr(posts, "items", lambda renders: {})
    drift = posts.check_all(tmp_path / "ig", tmp_path / "renders", fonts_dir=tmp_path)
    assert [d.name for d in drift] == ["new-reel"] and "not an approved look" in drift[0].reason


def test_a_release_folder_without_the_closed_list_cannot_be_trusted(tmp_path):
    (tmp_path / "__init__.py").write_text("")
    with pytest.raises(ReleaseError, match="_grandfathered"):
        grandfathered(tmp_path)


def test_the_publish_gate_stays_clean_for_the_grandfathered_reels_including_the_two_black_ones(tmp_path):
    posts = _instagram_posts()
    published = {s: r for s, r in posts.RELEASES.items() if s in posts.GRANDFATHERED}
    assert published
    assert caption_gate.check_releases(published, tmp_path, tmp_path, grandfathered=posts.GRANDFATHERED) == []


GRANDFATHERED_SHA256 = "6165cfea9448f97fd0f019973450ceff93ae1457a80f414222eabb9f8ff9b29f"


# -- the acceptance numbers, on the real masters --------------------------------------------------------------------
@pytest.mark.parametrize(
    "slug, style, passes",
    [
        ("gloss-notifications", None, False),
        ("gloss-fewer-meetings", None, False),
        ("gloss-terms", None, True),
        ("gloss-orientation", None, True),
        ("saga-the-code", "Saga", True),
        ("friday-sync", "Toon", True),
        ("the-lore", "Collage", True),
        ("the-cactus", "Cutout", True),
        ("the-router", "Ink", True),
        ("the-cake", "Soft", True),
        ("cancel-anytime", "Stick", True),
    ],
)
def test_the_measure_fails_the_black_masters_and_passes_the_white_and_toon_ones(slug, style, passes):
    renders, episodes = os.environ.get("SRSTUDIO_RENDERS"), os.environ.get("SRSTUDIO_EPISODES")
    if not (renders and episodes):
        pytest.skip("set SRSTUDIO_RENDERS and SRSTUDIO_EPISODES to measure the real masters")
    video, scene = Path(renders) / f"{slug}.mp4", Path(episodes) / slug / f"{slug}.scene.xml"
    if not (video.is_file() and scene.is_file()):
        pytest.skip(f"{slug} is not built here")
    look = next((lk for lk in caption_gate.LOOKS if lk.style == style), None)
    assert caption_gate.measure_reel(scene, video, look).passes is passes


# -- the split outline --------------------------------------------------------------------------------------------
def split_scene_file(tmp_path, stroke="#121415", width=8):
    scene = NATIVE_SCENE.format(fill="#FFFFFF", active="#F4D492", stroke="", width=0)
    scene = scene.replace(' strokeColor="" strokeWidth="0"', "").replace(
        "<composition/>",
        f"""<assets><text id="captions-outline-1" text="Hi" width="800" height="130" size="50" color="{stroke}"
        strokeColor="{stroke}" strokeWidth="{width}"/></assets>
        <composition><group id="captions-outline" isolate="true"><group id="c1" start="0" end="1">
        <layer id="captions-outline-1-layer" asset="captions-outline-1" x="100" y="150"/></group></group>
        </composition>""",
    )
    path = tmp_path / "split.scene.xml"
    path.write_text(scene)
    return path


def test_a_split_outline_is_read_as_the_outline_of_the_track(tmp_path):
    assert caption_gate.band_of(split_scene_file(tmp_path), WHITE_LOOK) == caption_gate.band_of(
        native_scene(tmp_path), WHITE_LOOK
    )
    assert caption_gate.band_of(split_scene_file(tmp_path, stroke="#FF0000"), WHITE_LOOK) is None
    assert caption_gate.band_of(split_scene_file(tmp_path, width=3), WHITE_LOOK) is None


def test_the_gloss_look_is_recorded_with_its_proof_and_the_operators_approval():
    gloss = [look for look in caption_gate.LOOKS if look.style == "Gloss"]
    assert [look.name for look in gloss] == ["white-split-outline"]
    (look,) = gloss
    assert (look.fills, look.active, look.stroke) == (("#FFFFFF",), "#F4D492", "#121415")
    assert look.proof == "generated/character-proofs/gloss-captions/index.html"
    assert look.approved
    assert look.approval is not None and look.approval.by == "operator"


def test_the_gloss_look_for_new_reels_is_the_house_look_with_its_outline_split():
    from dataclasses import replace

    from srstudio import gloss_reel

    assert gloss_reel.LOOK_SPLIT.outline == "layer" and not gloss_reel.LOOK_SPLIT.published
    assert replace(gloss_reel.LOOK_SPLIT, outline="stroke") == gloss_reel.LOOK
