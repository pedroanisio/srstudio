"""Instagram captions: typed limits, the ig.txt layout, the episode hook, and every shipped post is valid."""

import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

from srstudio import Episode, EpisodeSpec
from srstudio.sample import SYSTEM_FONTS
from srstudio.social import (
    CAPTION_LIMIT,
    COVER_NAME,
    HASHTAG_LIMIT,
    MANIFEST,
    CoverError,
    DeliveryError,
    InstagramPost,
    InstagramPostError,
    Item,
    check_delivery,
    probe,
    publish,
    read_manifest,
    take_frame,
)
from srstudio.thumbnail import Thumbnail

EPISODES = Path(__file__).resolve().parent.parent / "episodes"
FONT = next(f for f in SYSTEM_FONTS if f.exists())  # DejaVu Sans Bold, the fixture font

GOOD = InstagramPost(
    title="Greatest weakness? Honesty.",
    description="Episode 01.\nContains one strong word.",
    credit="Voices: ElevenLabs.",
    hashtags=("#TheInterview", "#officehumor"),
)


def test_text_layout_is_title_description_credit_hashtags():
    assert GOOD.text() == (
        "Greatest weakness? Honesty.\n\nEpisode 01.\nContains one strong word.\n\n"
        "Voices: ElevenLabs.\n\n#TheInterview #officehumor\n"
    )
    assert InstagramPost(title="t", description="d").text() == "t\n\nd\n"
    assert GOOD.validate() is GOOD


@pytest.mark.parametrize(
    "post,needle",
    [
        (InstagramPost(title="", description="d"), "title is empty"),
        (InstagramPost(title="a\nb", description="d"), "more than one line"),
        (InstagramPost(title="x" * 126, description="d"), "126 characters"),
        (InstagramPost(title="t", description="  "), "description is empty"),
        (
            InstagramPost(title="t", description="d", hashtags=tuple(f"#t{i}" for i in range(HASHTAG_LIMIT + 1))),
            "31 hashtags",
        ),
        (
            InstagramPost(title="t", description="d", hashtags=("#ok", "no-hash", "#1starts", "#with space")),
            "must be '#'",
        ),
        (InstagramPost(title="t", description="d", hashtags=("#Same", "#same")), "duplicate"),
        (InstagramPost(title="t", description="d" * CAPTION_LIMIT), f"Instagram accepts {CAPTION_LIMIT}"),
        (InstagramPost(title="t", description="d", thumbnail=Thumbnail("a", -0.5)), "thumbnail: backdrop time"),
        (InstagramPost(title="t", description="d", thumbnail=Thumbnail("a", 0, zoom=9)), "thumbnail: zoom"),
    ],
)
def test_limits_raise_a_typed_error_listing_the_problem(post, needle):
    with pytest.raises(InstagramPostError) as info:
        post.validate()
    assert any(needle in p for p in info.value.problems)


def test_write_refuses_an_invalid_post_and_leaves_no_file(tmp_path):
    with pytest.raises(InstagramPostError):
        InstagramPost(title="", description="d").write(tmp_path / "x")
    assert not (tmp_path / "x" / "ig.txt").exists()


def test_episode_writes_ig_txt_in_its_root(project):
    ep = Episode(EpisodeSpec(slug="t", title="t", description="t", root=project, seed=1, background="#D5DFDF"))
    path = ep.instagram(GOOD)
    assert path == project / "ig.txt" and path.read_text(encoding="utf-8") == GOOD.text()
    assert path.stat().st_mode & 0o777 == 0o600


def test_an_episode_hides_its_burned_in_text_in_the_cover_variant(project, tmp_path):
    ep = Episode(EpisodeSpec(slug="t", title="t", description="t", root=project, seed=1, background="#D5DFDF",
                             signature=False))  # fmt: skip
    card, words = ep.cv.group(ep.cv.comp, "card"), ep.cv.group(ep.cv.comp, "words")
    ep.hide_on_cover(card, words)
    doc = ep.finish(tmp_path / "t.scene.xml", tmp_path / "report.json").read_text(encoding="utf-8")
    assert '<variant id="cover"' in doc
    for target in ("card", "words"):
        assert f'<override target="{target}" property="visible" value="false"/>' in doc
    with pytest.raises(ValueError, match="at least one node"):
        ep.hide_on_cover()
    with pytest.raises(ValueError, match="already hidden"):
        ep.hide_on_cover(card)


def needs_ffmpeg():
    if not (shutil.which("ffmpeg") and shutil.which("ffprobe")):
        pytest.skip("needs ffmpeg and ffprobe")


def video(path: Path, *, seconds: float = 1, fps: int = 10, size: str = "64x112", lum: str = "X*2+N*10") -> Path:
    """A small lossless video whose frame n has a horizontal ramp brightened by 10 per frame (or ``lum``)."""
    needs_ffmpeg()
    subprocess.run(
        ["ffmpeg", "-v", "error", "-y", "-f", "lavfi", "-i", f"nullsrc=s={size}:r={fps}:d={seconds}",
         "-vf", f"geq=lum='{lum}':cb=128:cr=128", "-c:v", "libx264", "-qp", "0", "-pix_fmt", "yuv420p", str(path)],
        check=True,
    )  # fmt: skip
    return path


def mean_luma(image: Path) -> float:
    raw = subprocess.run(
        ["ffmpeg", "-v", "error", "-i", str(image), "-vf", "format=gray", "-f", "rawvideo", "-"],
        check=True, capture_output=True,
    ).stdout  # fmt: skip
    return sum(raw) / len(raw)


def ramp(n: int) -> float:
    """The mean luma of frame ``n`` of :func:`video` once in a JPEG: video levels 16-235 map to 0-255."""
    return sum(min(255.0, max(0.0, (2 * x + 10 * n - 16) * 255 / 219)) for x in range(64)) / 64


def test_probe_reads_the_video_it_is_given(tmp_path):
    info = probe(video(tmp_path / "v.mp4", seconds=2, fps=10))
    assert (info.width, info.height, info.fps, info.frames) == (64, 112, 10.0, 20)
    assert info.duration == pytest.approx(2.0, abs=0.05)
    with pytest.raises(CoverError, match="cannot read"):
        probe(tmp_path / "missing.mp4")


def test_the_frame_is_the_one_shown_at_its_time(tmp_path):
    clip = video(tmp_path / "v.mp4")
    path = tmp_path / "f5.jpg"
    info = take_frame(clip, 0.55, path)  # frame 5 is on screen from 0.5 s to 0.6 s
    assert info.frames == 10 and path.stat().st_mode & 0o777 == 0o600
    assert probe(path).width == 64 and probe(path).height == 112  # the video's own size
    assert mean_luma(path) == pytest.approx(ramp(5), abs=3)  # not frame 4 nor frame 6, 11.6 away either side
    take_frame(clip, 0.0, tmp_path / "first.jpg")
    take_frame(clip, 0.99, tmp_path / "last.jpg")
    assert mean_luma(tmp_path / "first.jpg") == pytest.approx(ramp(0), abs=3)
    assert mean_luma(tmp_path / "last.jpg") == pytest.approx(ramp(9), abs=3)


@pytest.mark.parametrize(
    "at, match", [(1.0, "after the last frame"), (5.0, "after the last frame"), (-1, "frame time")]
)
def test_a_frame_outside_the_video_is_refused(tmp_path, at, match):
    with pytest.raises(CoverError, match=match):
        take_frame(video(tmp_path / "v.mp4"), at, tmp_path / "f.png")
    assert sorted(p.name for p in tmp_path.iterdir()) == ["v.mp4"]


def test_a_blank_frame_is_refused(tmp_path):
    flat = video(tmp_path / "flat.mp4", lum="16")  # a black frame, as at a fade
    with pytest.raises(CoverError, match="blank"):
        take_frame(flat, 0.2, tmp_path / "f.png")
    assert sorted(p.name for p in tmp_path.iterdir()) == ["flat.mp4"]


def engine() -> str:
    found = os.environ.get("SRSTUDIO_ENGINE") or shutil.which("scene-render")
    if not found:
        pytest.skip("needs SRSTUDIO_ENGINE")
    return found


def tall(path: Path, lum: str = "X/3+Y/5+N*10") -> Path:
    """A portrait clip big enough for a headline in the fixture font."""
    return video(path, seconds=1, fps=4, size="540x960", lum=lum)


def post(headline: str = "Hi", at: float = 0.3, **kw) -> InstagramPost:
    return InstagramPost(title="t", description="d", thumbnail=Thumbnail(headline, at, kicker="K"), **kw)


def test_deliver_writes_the_caption_and_the_designed_cover_together(tmp_path):
    clip = tall(tmp_path / "v.mp4")
    caption, cover = post().deliver(tmp_path / "ig" / "v", clip, font=FONT, engine=engine())
    assert caption.name == "ig.txt" and cover.name == COVER_NAME and caption.parent == cover.parent
    assert sorted(p.name for p in cover.parent.iterdir()) == [COVER_NAME, "ig.txt"]  # no backdrop left behind
    assert (probe(cover).width, probe(cover).height) == (540, 960)
    assert abs(mean_luma(cover) - mean_luma(take_frame(clip, 0.3, tmp_path / "f.jpg") and tmp_path / "f.jpg")) > 5
    with pytest.raises(InstagramPostError, match="thumbnail is missing"):
        InstagramPost(title="t", description="d").deliver(tmp_path / "none", clip, font=FONT, engine=engine())
    assert not (tmp_path / "none").exists()  # nothing is written for a post that cannot be delivered


def test_deliver_leaves_no_folder_when_the_backdrop_is_blank(tmp_path):
    flat = tall(tmp_path / "flat.mp4", lum="16")
    with pytest.raises(CoverError, match="blank"):
        post().deliver(tmp_path / "ig" / "flat", flat, font=FONT, engine="scene-render-not-needed")
    assert not (tmp_path / "ig" / "flat").exists()  # neither ig.txt nor cover.jpg


def test_deliver_leaves_no_folder_when_the_engine_fails(tmp_path):
    fake = tmp_path / "engine"
    fake.write_text("#!/bin/sh\nexit 1\n")
    fake.chmod(0o700)
    with pytest.raises(ValueError, match="engine"):
        post().deliver(tmp_path / "ig" / "v", tall(tmp_path / "v.mp4"), font=FONT, engine=fake)
    assert not (tmp_path / "ig" / "v").exists()


# -- a cover from the scene, without the video's burned-in text -------------------------------------------------
def scene_doc(path: Path, *, hide: bool = True, size=(540, 960)) -> Path:
    """A one-second picture at 4 fps: a red and dark red field (the picture) under a white band (burned-in text) at
    the top, the band hidden in the ``cover`` variant when ``hide``."""
    from sr_core.scene import Scene

    scene = Scene(version="auto")
    scene.add_project(width=size[0], height=size[1], fps="4", duration=1, background="#000000")
    comp = scene.add_composition()
    comp.add_shape(id="picture", shape="rect", width=size[0], height=size[1], fill="#c03030")
    comp.add_shape(id="shadow", shape="rect", width=size[0] // 2, height=size[1], fill="#401010")
    comp.add_shape(id="burned", shape="rect", width=size[0], height=200, fill="#ffffff")
    if hide:
        scene.add_parameters().add_variant(id="cover").add_override(target="burned", property="visible", value="false")
    path.write_bytes(scene.to_bytes())
    return path


def top_luma(image: Path) -> float:
    raw = subprocess.run(
        ["ffmpeg", "-v", "error", "-i", str(image), "-vf", "crop=iw:150:0:20,format=gray", "-f", "rawvideo", "-"],
        check=True, capture_output=True,
    ).stdout  # fmt: skip
    return sum(raw) / len(raw)


def test_a_cover_drawn_from_the_scene_leaves_out_the_burned_in_text(tmp_path):
    clip = tall(tmp_path / "v.mp4")
    _, cover = post().deliver(
        tmp_path / "ig" / "v", clip, font=FONT, engine=engine(), scene=scene_doc(tmp_path / "s.xml")
    )
    assert top_luma(cover) < 120  # the red picture, not the white band (luma 255) the video shows there
    _, shown = post().deliver(tmp_path / "ig" / "w", clip, font=FONT, engine=engine())
    assert abs(top_luma(shown) - top_luma(cover)) > 5  # without a scene, the video's own frame


def test_a_scene_without_a_cover_variant_or_of_another_size_is_refused(tmp_path):
    clip = tall(tmp_path / "v.mp4")
    for doc, match in ((scene_doc(tmp_path / "plain.xml", hide=False), "cover variant"),
                       (scene_doc(tmp_path / "small.xml", size=(270, 480)), "540x960")):  # fmt: skip
        with pytest.raises(CoverError, match=match):
            post().deliver(tmp_path / "ig" / "v", clip, font=FONT, engine=engine(), scene=doc)
        assert not (tmp_path / "ig" / "v").exists()


def test_an_edited_scene_drifts(tmp_path):
    renders = tmp_path / "renders"
    renders.mkdir()
    doc = scene_doc(tmp_path / "s.xml")
    items = {"a": Item(post("A"), tall(renders / "a.mp4"), doc)}
    publish(items, tmp_path / "ig", font=FONT, engine=engine())
    assert reasons(items, tmp_path / "ig") == []
    doc.write_bytes(doc.read_bytes().replace(b"#c03030", b"#3030c0"))
    assert reasons(items, tmp_path / "ig") == [
        "a: the post, its thumbnail, its scene, the font or the layout changed since delivery"
    ]


# -- the publish gate ---------------------------------------------------------------------------------------------
@pytest.fixture
def delivered(tmp_path):
    """Two videos published into ``tmp_path / "ig"``; returns the items, the out folder and the renders."""
    renders = tmp_path / "renders"
    renders.mkdir()
    items = {"a": Item(post("A"), tall(renders / "a.mp4")), "b": Item(post("B"), tall(renders / "b.mp4"))}
    out = tmp_path / "ig"
    written = publish(items, out, font=FONT, engine=engine())
    assert sorted(p.name for p in written) == ["a", "b"]
    return items, out, renders


def reasons(items, out) -> list[str]:
    return [str(d) for d in check_delivery(items, out, font=FONT)]


def test_a_fresh_delivery_has_no_drift_and_a_private_manifest(delivered):
    items, out, _ = delivered
    assert reasons(items, out) == []
    manifest = out / MANIFEST
    assert manifest.stat().st_mode & 0o777 == 0o600 and out.stat().st_mode & 0o777 == 0o700
    assert set(read_manifest(out)) == {"a", "b"}


def test_nothing_delivered_is_drift(tmp_path):
    items = {"a": Item(post(), tall(tmp_path / "a.mp4")), "gone": Item(post(), tmp_path / "gone.mp4")}
    assert reasons(items, tmp_path / "ig") == ["a: never delivered", f"gone: no render at {tmp_path / 'gone.mp4'}"]


def test_a_re_rendered_video_drifts_and_publish_redelivers_only_it(delivered):
    items, out, renders = delivered
    tall(renders / "a.mp4", lum="Y/4+N*20")  # a new render under the same name
    assert reasons(items, out) == ["a: the video was re-rendered after its cover was made"]
    before = (out / "b" / COVER_NAME).stat().st_mtime_ns
    assert [p.name for p in publish(items, out, font=FONT, engine=engine())] == ["a"]
    assert (out / "b" / COVER_NAME).stat().st_mtime_ns == before  # the current one is left alone
    assert reasons(items, out) == []


def test_a_changed_post_or_thumbnail_drifts(delivered):
    items, out, renders = delivered
    changed = {
        **items,
        "a": Item(post("A changed"), renders / "a.mp4"),
        "b": Item(post("B", hashtags=("#x",)), renders / "b.mp4"),
    }
    assert reasons(changed, out) == [
        "a: the post, its thumbnail, its scene, the font or the layout changed since delivery",
        "b: the post, its thumbnail, its scene, the font or the layout changed since delivery",
    ]


def test_an_edited_or_missing_file_drifts(delivered):
    items, out, _ = delivered
    (out / "a" / "ig.txt").write_text("edited by hand\n", encoding="utf-8")
    (out / "b" / COVER_NAME).unlink()
    assert reasons(items, out) == ["a: ig.txt was changed after delivery", "b: cover.jpg is missing"]


def test_a_video_no_longer_published_drifts_and_publish_drops_it(delivered):
    items, out, _ = delivered
    only_a = {"a": items["a"]}
    assert reasons(only_a, out) == ["b: delivered, but no longer published"]
    assert publish(only_a, out, font=FONT, engine=engine()) == []
    assert set(read_manifest(out)) == {"a"} and reasons(only_a, out) == []


@pytest.mark.parametrize(
    "manifest, needle",
    [
        ("not json", "cannot be read"),
        ('{"version": "2.0.0", "videos": {}}', "version"),
        ('{"version": "1.0.0", "videos": {}, "extra": 1}', "exactly"),
        ('{"version": "1.0.0", "videos": []}', "must be an object"),
        ('{"version": "1.0.0", "videos": {"a": {"render": "x"}}}', "entry 'a'"),
        ('{"version": "1.0.0", "videos": {"a": {"render": "x", "post": "x", "ig": "x", "cover": "x"}}}', "SHA-256"),
    ],
)
def test_an_untrustworthy_manifest_is_refused_and_is_drift(tmp_path, manifest, needle):
    (tmp_path / MANIFEST).write_text(manifest, encoding="utf-8")
    with pytest.raises(DeliveryError, match=needle):
        read_manifest(tmp_path)
    drift = check_delivery({}, tmp_path, font=FONT)
    assert len(drift) == 1 and drift[0].name == "*" and needle in drift[0].reason


def test_an_untrustworthy_manifest_is_replaced_by_a_full_delivery(delivered):
    items, out, _ = delivered
    (out / MANIFEST).write_text("not json", encoding="utf-8")
    assert sorted(p.name for p in publish(items, out, font=FONT, engine=engine())) == ["a", "b"]
    assert reasons(items, out) == []


def test_publish_refuses_a_missing_render_before_writing(tmp_path):
    items = {"a": Item(post(), tmp_path / "a.mp4")}
    with pytest.raises(DeliveryError, match="no render for: a"):
        publish(items, tmp_path / "ig", font=FONT, engine="unused")
    assert not (tmp_path / "ig").exists()


def test_publish_only_some_videos_leaves_the_rest_of_the_delivery_as_it_was(delivered):
    items, out, renders = delivered
    tall(renders / "a.mp4", lum="Y/4+N*20")  # both drift: a re-rendered, b's post edited
    changed = {**items, "b": Item(post("B changed"), renders / "b.mp4"), "new": Item(post("N"), renders / "new.mp4")}
    before = read_manifest(out)["b"]
    assert [p.name for p in publish(changed, out, font=FONT, engine=engine(), only={"a"})] == ["a"]
    assert read_manifest(out)["b"] == before and "new" not in read_manifest(out)
    assert reasons(changed, out) == [  # the gate still reports what was not delivered
        "b: the post, its thumbnail, its scene, the font or the layout changed since delivery",
        f"new: no render at {renders / 'new.mp4'}",
    ]


def test_two_deliveries_of_different_videos_that_overlap_both_keep_their_manifest_entries(delivered, monkeypatch):
    items, out, renders = delivered
    tall(renders / "a.mp4", lum="Y/4+N*20")
    tall(renders / "b.mp4", lum="Y/3+N*10")  # both re-rendered: each run delivers one of them
    real, other = InstagramPost.deliver, []

    def slow_cover(self, folder, *args, **kw):  # while a's cover renders, another process delivers b
        if folder.name == "a" and not other:
            other.append(None)
            other[0] = publish(items, out, font=FONT, engine=engine(), only={"b"})
        return real(self, folder, *args, **kw)

    monkeypatch.setattr(InstagramPost, "deliver", slow_cover)
    assert [p.name for p in publish(items, out, font=FONT, engine=engine(), only={"a"})] == ["a"]
    assert [p.name for p in other[0]] == ["b"]
    assert reasons(items, out) == []  # b's entry, written mid-run, was not lost


@pytest.mark.parametrize("only, needle", [({"zz"}, "not a published video: zz"), (set(), "at least one")])
def test_publish_only_refuses_names_it_cannot_deliver(delivered, only, needle):
    items, out, _ = delivered
    with pytest.raises(DeliveryError, match=needle):
        publish(items, out, font=FONT, engine="unused", only=only)


def test_publish_only_still_needs_the_named_render_and_a_readable_manifest(delivered):
    items, out, renders = delivered
    (renders / "a.mp4").unlink()
    with pytest.raises(DeliveryError, match="no render for: a"):
        publish(items, out, font=FONT, engine="unused", only={"a"})
    (out / MANIFEST).write_text("not json", encoding="utf-8")
    with pytest.raises(DeliveryError, match="cannot be read"):
        publish(items, out, font=FONT, engine="unused", only={"b"})


def shipped_posts():
    sys.path.insert(0, str(EPISODES))
    try:
        import instagram_posts as posts
    finally:
        sys.path.pop(0)
    return posts


def test_every_shipped_post_is_valid_has_a_thumbnail_and_maps_to_a_video(tmp_path):
    posts = shipped_posts()
    assert set(posts.POSTS) == set(posts.VIDEOS)
    assert len(set(posts.VIDEOS.values())) == len(posts.VIDEOS)  # one folder per video
    for slug, p in posts.POSTS.items():
        assert p.problems() == [], slug
        assert p.thumbnail is not None, slug
    items = posts.items(tmp_path / "renders", tmp_path / "episodes")
    assert {name: item.video.name for name, item in items.items()} == {n: f"{n}.mp4" for n in posts.VIDEOS.values()}
    # a post whose episode hides its burned-in text on the cover names the scene its video is encoded from
    scenes = {posts.VIDEOS[slug]: tmp_path / "episodes" / slug / name for slug, name in posts.COVER_SCENES.items()}
    assert {name: item.scene for name, item in items.items() if item.scene is not None} == scenes


def test_the_check_command_reports_drift_and_exits_1(tmp_path, capsys, monkeypatch):
    posts = shipped_posts()
    monkeypatch.setattr(posts, "font_file", lambda folder: FONT)
    assert posts.main(["check", str(tmp_path / "ig"), str(tmp_path), "--fonts", str(tmp_path)]) == 1
    out = capsys.readouterr().out
    assert f"{len(posts.POSTS)} videos, {len(posts.POSTS)} drifted" in out and "no render at" in out


def test_the_deliver_command_names_what_it_cannot_deliver_and_writes_nothing(tmp_path, monkeypatch):
    posts = shipped_posts()
    monkeypatch.setattr(posts, "font_file", lambda folder: FONT)
    with pytest.raises(SystemExit, match="deliver: not a published video: nope"):
        posts.main(["deliver", str(tmp_path / "ig"), str(tmp_path), "--fonts", str(tmp_path), "--engine", "x",
                    "--only", "nope"])  # fmt: skip
    assert not (tmp_path / "ig").exists()


def test_every_episode_script_ships_its_post():
    scripts = [p for p in sorted(EPISODES.glob("*.py")) if "ep.finish(" in p.read_text(encoding="utf-8")]
    assert scripts
    missing = [p.name for p in scripts if "ep.instagram(POSTS[" not in p.read_text(encoding="utf-8")]
    assert missing == []


def test_the_published_delivery_has_not_drifted():
    """The publish gate: with ``SRSTUDIO_RENDERS`` (the rendered videos, delivered into ``<renders>/ig``) and
    ``SRSTUDIO_FONTS`` (the pinned headline font) set, every video's ig.txt and cover must match its render and post."""
    renders, fonts_dir = os.environ.get("SRSTUDIO_RENDERS"), os.environ.get("SRSTUDIO_FONTS")
    if not renders or not fonts_dir:
        pytest.skip("set SRSTUDIO_RENDERS and SRSTUDIO_FONTS to check the published delivery")
    drift = shipped_posts().check_all(Path(renders) / "ig", Path(renders), fonts_dir=Path(fonts_dir))
    assert drift == [], "the delivery drifted; run instagram_posts.py deliver:\n" + "\n".join(map(str, drift))
