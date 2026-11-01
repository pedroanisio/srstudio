"""Instagram captions: typed limits, the ig.txt layout, the episode hook, and every shipped post is valid."""

import fcntl
import hashlib
import importlib
import json
import os
import re
import subprocess
import sys
from dataclasses import asdict, replace
from pathlib import Path

import pytest

from srstudio import Episode, EpisodeSpec, frame_gates, parts, sketch, social, thumbnail
from srstudio.comedy_floor import ComedyError, Scores
from srstudio.releases import Release, ReleaseError, Tags
from srstudio.social import (
    CAPTION_LIMIT,
    COVER_NAME,
    HASHTAG_LIMIT,
    LEGACY_LAYOUT_7CDAFF4,
    LEGACY_LAYOUT_F7C86D3,
    LEGACY_LAYOUTS,
    MANIFEST,
    MANIFEST_VERSION,
    PUBLISHED_HASHTAG_LIMIT,
    CoverError,
    DeliveryError,
    Drift,
    HashtagError,
    InstagramPost,
    InstagramPostError,
    Item,
    ManifestVersionError,
    check_delivery,
    fingerprint,
    migrate_manifest,
    probe,
    publish,
    read_manifest,
    take_frame,
    video_size,
)
from srstudio.thumbnail import Thumbnail
from support import bible_docs
from support.social import FONT, engine, post, tall, video

EPISODES = Path(__file__).resolve().parent.parent / "episodes"

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
            InstagramPost(
                title="t", description="d", hashtags=tuple(f"#t{i}" for i in range(PUBLISHED_HASHTAG_LIMIT + 1))
            ),
            "31 hashtags",
        ),
        (
            InstagramPost(title="t", description="d", hashtags=("#ok", "no-hash", "#1starts", "#with space")),
            "must be '#'",
        ),
        (InstagramPost(title="t", description="d", hashtags=("#ok", "#trailing\n")), "must be '#'"),
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


def test_deliver_refuses_a_headline_over_a_face_and_writes_nothing(tmp_path):
    with pytest.raises(thumbnail.ThumbnailError, match="headline or kicker covers"):
        post().deliver(tmp_path / "ig" / "v", tall(tmp_path / "v.mp4"), font=FONT, engine=engine(),
                       keep_clear=[(0.0, 0.0, 540.0, 960.0)])  # fmt: skip
    assert not (tmp_path / "ig" / "v").exists()


def test_deliver_draws_the_cover_when_the_faces_are_clear(tmp_path):
    clip = tall(tmp_path / "v.mp4")
    caption, cover = post().deliver(tmp_path / "ig" / "v", clip, font=FONT, engine=engine(),
                                    keep_clear=[(0.0, 0.0, 10.0, 10.0)])  # fmt: skip
    assert caption.exists() and cover.exists()


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


def test_a_cover_scene_that_was_never_built_is_refused_and_leaves_no_folder(tmp_path):
    with pytest.raises(CoverError, match="no scene"):
        post().deliver(tmp_path / "ig" / "v", tall(tmp_path / "v.mp4"), font=FONT, engine=engine(),
                       scene=tmp_path / "unbuilt.scene.xml")  # fmt: skip
    assert not (tmp_path / "ig" / "v").exists()


def test_deliver_leaves_no_folder_whatever_fails(tmp_path, monkeypatch):
    def broken(*args, **kwargs):
        raise OSError("disk full")

    monkeypatch.setattr(social, "render", broken)
    with pytest.raises(OSError, match="disk full"):
        post().deliver(tmp_path / "ig" / "v", tall(tmp_path / "v.mp4"), font=FONT, engine=engine())
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
        "a": Item(post("A2"), renders / "a.mp4"),
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
    changed = {**items, "b": Item(post("B2"), renders / "b.mp4"), "new": Item(post("N"), renders / "new.mp4")}
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


# -- a frozen video is current at the drawing the operator accepted (ADR 0040) -------------------------------------
@pytest.fixture
def redrawn(delivered):
    """``a``'s post changed after it was published; returns the items now, the out folder and ``a``'s new drawing."""
    items, out, renders = delivered
    now = {**items, "a": Item(post("A2"), renders / "a.mp4")}
    return now, out, fingerprint(post("A2"), renders / "a.mp4", FONT)


def test_a_frozen_video_is_current_only_at_the_drawing_it_was_frozen_at(redrawn):
    items, out, accepted = redrawn
    assert [str(d) for d in check_delivery(items, out, font=FONT, frozen={"a": accepted})] == []
    assert [str(d) for d in check_delivery(items, out, font=FONT, frozen={"a": "0" * 64})] == [
        "a: the post, its thumbnail, its scene, the font or the layout changed since delivery"
    ]


def test_a_frozen_video_still_drifts_when_its_render_or_its_files_change(redrawn):
    items, out, accepted = redrawn
    (out / "a" / "ig.txt").write_text("edited by hand\n", encoding="utf-8")
    items["a"].video.write_bytes(items["a"].video.read_bytes() + b"\0")
    assert [str(d) for d in check_delivery(items, out, font=FONT, frozen={"a": accepted})] == [
        "a: the video was re-rendered after its cover was made",
        "a: ig.txt was changed after delivery",
    ]


def test_frozen_must_name_published_videos(delivered):
    items, out, _ = delivered
    with pytest.raises(DeliveryError, match="frozen names a video that is not published: gone"):
        check_delivery(items, out, font=FONT, frozen={"gone": "0" * 64})
    with pytest.raises(DeliveryError, match="frozen names a video that is not published: gone"):
        publish(items, out, font=FONT, engine="unused", frozen={"gone": "0" * 64})


def test_a_full_delivery_leaves_a_frozen_video_and_its_manifest_entry_as_published(redrawn):
    items, out, accepted = redrawn
    entry = read_manifest(out)["a"]
    cover = (out / "a" / COVER_NAME).read_bytes()
    assert publish(items, out, font=FONT, engine="unused", frozen={"a": accepted}) == []
    assert read_manifest(out)["a"] == entry and (out / "a" / COVER_NAME).read_bytes() == cover
    assert check_delivery(items, out, font=FONT, frozen={"a": accepted}) == []


def test_every_frozen_release_names_the_drawing_its_post_makes_now():
    """A release is frozen at the fingerprint of its post now, so the pin goes stale (and the gate goes red) when
    anything that draws its cover changes; the shipped ones are checked against the published delivery above."""
    posts = shipped_posts()
    assert posts.FROZEN == {r.video_name: r.frozen for r in posts.RELEASES.values() if r.frozen}


# -- the post fingerprint is the drawing (ADR 0037) ----------------------------------------------------------------
def test_an_edit_to_the_layout_source_alone_changes_no_fingerprint(tmp_path, monkeypatch):
    clip = tall(tmp_path / "v.mp4")
    before = fingerprint(post(), clip, FONT)
    edited = tmp_path / "thumbnail.py"
    source = Path(thumbnail.__file__).read_text(encoding="utf-8")
    edited.write_text(source.replace('"""The designed thumbnail', '"""Edited. The designed thumbnail', 1), "utf-8")
    monkeypatch.setattr(thumbnail, "__file__", str(edited))  # a docstring, a base class: the drawing is the same
    assert fingerprint(post(), clip, FONT) == before


@pytest.mark.parametrize(
    "module, name, value",
    [
        (thumbnail, "OUTLINE", thumbnail.OUTLINE + 1),  # compose draws something else
        (thumbnail, "ENGINE_ARGS", ("-f", "1")),
        (thumbnail, "ENCODER_ARGS", ("-q:v", "3")),
        (social, "BACKDROP_ARGS", ("-frames:v", "1")),
        (social, "FRAME_SLACK", 0.0),
        (social, "COVER_VARIANT", "poster"),
    ],
)
def test_a_change_to_the_drawing_or_a_render_step_changes_the_fingerprint(tmp_path, monkeypatch, module, name, value):
    clip = tall(tmp_path / "v.mp4")
    before = fingerprint(post(), clip, FONT)
    monkeypatch.setattr(module, name, value)
    assert fingerprint(post(), clip, FONT) != before


def test_the_fingerprint_draws_the_cover_at_the_video_size(tmp_path):
    square = InstagramPost(title="t", description="d", thumbnail=Thumbnail("Hi", 0.3))
    portrait, flat = tall(tmp_path / "p.mp4"), video(tmp_path / "s.mp4", fps=4, size="540x540")
    assert fingerprint(square, portrait, FONT) != fingerprint(square, flat, FONT)
    assert fingerprint(square, portrait, FONT) == fingerprint(square, tall(tmp_path / "q.mp4", lum="Y/2"), FONT)


def test_the_video_size_is_read_from_the_container_as_probe_reads_it(tmp_path):
    clips = [video(tmp_path / f"v{size}.mp4", size=size) for size in ("64x112", "540x960", "540x540")]
    fast = tmp_path / "fast.mp4"  # the index (moov) before the media, as a streaming encoder writes it
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", str(clips[0]), "-c", "copy", "-movflags", "+faststart",
                    str(fast)], check=True)  # fmt: skip
    for clip in [*clips, fast]:
        info = probe(clip)
        assert video_size(clip) == (info.width, info.height), clip.name


@pytest.mark.parametrize(
    "data",
    [
        b"",
        b"not a video at all",
        b"\x00\x00\x00\x04moov",  # a box shorter than its own header
        b"\x00\x00\x00\x10ftypisom\x00\x00\x00\x00",  # no index
        b"\x00\x00\x00\x08moov",  # an index without a video track
        b"\x00\x00\x01\x00moov\x00\x00\x00\x08trak",  # a box that runs past the end of the file
    ],
)
def test_a_file_without_a_readable_video_size_is_refused(tmp_path, data):
    bad = tmp_path / "bad.mp4"
    bad.write_bytes(data)
    with pytest.raises(CoverError, match="cannot read the size of bad.mp4"):
        video_size(bad)


def box(kind: bytes, payload: bytes = b"") -> bytes:
    return (8 + len(payload)).to_bytes(4, "big") + kind + payload


def track(handler: bytes, entry: bytes) -> bytes:
    """A track whose handler is ``handler`` and whose one sample entry is ``entry``."""
    stsd = box(b"stsd", bytes(4) + (1).to_bytes(4, "big") + entry)
    return box(b"trak", box(b"mdia", box(b"hdlr", bytes(8) + handler + bytes(12)) + box(b"minf", box(b"stbl", stsd))))


def visual(width: int, height: int) -> bytes:
    """A visual sample entry: reserved, data reference and pre-defined fields, then the width and height."""
    return box(b"avc1", bytes(24) + width.to_bytes(2, "big") + height.to_bytes(2, "big") + bytes(50))


@pytest.mark.parametrize(
    "data, size",
    [
        (box(b"ftyp", b"isom") + box(b"moov", track(b"soun", b"") + track(b"vide", visual(320, 240))), (320, 240)),
        (b"\x00\x00\x00\x01moov" + (16 + 8).to_bytes(8, "big") + box(b"free"), None),  # a 64-bit size: no track
        (b"\x00\x00\x00\x00moov" + box(b"free"), None),  # a size of 0 runs to the end: no track
    ],
)
def test_the_video_size_follows_the_index_to_the_first_video_track(tmp_path, data, size):
    clip = tmp_path / "v.mp4"
    clip.write_bytes(data)
    if size is not None:
        assert video_size(clip) == size
    else:
        with pytest.raises(CoverError, match="no video track"):
            video_size(clip)


@pytest.mark.parametrize(
    "data, needle",
    [
        (box(b"ftyp", b"isom") + b"abc", "cut short"),  # a header shorter than 8 bytes after the last box
        (b"\x00\x00\x00\x01moov\x00\x00", "cut short"),  # a 64-bit size cut short
        (box(b"moov", track(b"vide", b"")), "sample entry is cut short"),
        (box(b"moov", track(b"vide", visual(0, 240))), "sample entry has no size"),
    ],
)
def test_a_video_index_without_a_whole_video_sample_entry_is_refused(tmp_path, data, needle):
    clip = tmp_path / "v.mp4"
    clip.write_bytes(data)
    with pytest.raises(CoverError, match=needle):
        video_size(clip)


def test_a_post_without_a_thumbnail_is_fingerprinted_without_its_video(tmp_path):
    bare = InstagramPost(title="t", description="d")
    assert fingerprint(bare, tmp_path / "absent.mp4", FONT) == fingerprint(bare, tmp_path / "other.mp4", FONT)


def test_a_truncated_video_is_refused(tmp_path):
    clip = video(tmp_path / "v.mp4")
    cut = tmp_path / "cut.mp4"
    cut.write_bytes(clip.read_bytes()[: clip.stat().st_size - 200])  # ffmpeg writes the index last
    with pytest.raises(CoverError, match="cannot read the size of cut.mp4"):
        video_size(cut)


def test_deliver_refuses_a_video_whose_index_names_another_size_than_it_decodes_at(tmp_path):
    clip = tall(tmp_path / "v.mp4")
    data = bytearray(clip.read_bytes())
    entry = data.index(b"stsd") + 12  # the first sample entry, after the type, version, flags and entry count
    data[entry + 32 : entry + 34] = (600).to_bytes(2, "big")  # its width; the stream still decodes 540 wide
    clip.write_bytes(bytes(data))
    assert video_size(clip) == (600, 960) and probe(clip).width == 540
    with pytest.raises(CoverError, match="decodes at 540x960, but its index says 600x960"):
        post().deliver(tmp_path / "ig" / "v", clip, font=FONT, engine="unused")
    assert not (tmp_path / "ig" / "v").exists()


def test_check_never_runs_the_engine_ffmpeg_or_ffprobe(delivered, monkeypatch):
    items, out, _ = delivered

    def refuse(cmd, *args, **kw):
        raise AssertionError(f"check ran {cmd}")

    monkeypatch.setattr(subprocess, "run", refuse)
    monkeypatch.setattr(subprocess, "Popen", refuse)
    assert reasons(items, out) == []


def test_a_cover_that_cannot_be_drawn_now_drifts(delivered):
    items, out, renders = delivered
    wide = {**items, "a": Item(post("A headline far too wide to fit"), renders / "a.mp4")}
    (drift,) = check_delivery(wide, out, font=FONT)
    assert drift.name == "a" and "cannot be drawn" in drift.reason and "wider than" in drift.reason


def test_a_font_that_cannot_be_read_is_drift_not_a_crash_of_the_gate(delivered, tmp_path):
    items, out, _ = delivered
    drift = check_delivery(items, out, font=tmp_path / "gone.ttf")
    assert [d.name for d in drift] == ["a", "b"]
    assert all("cannot be drawn" in d.reason and "gone.ttf" in d.reason for d in drift)
    with pytest.raises(CoverError, match="font"):
        fingerprint(InstagramPost(title="t", description="d"), tmp_path / "unread.mp4", tmp_path / "gone.ttf")


def test_reading_the_font_once_keeps_every_fingerprint(delivered):
    items, out, _ = delivered
    entries = json.loads((out / "delivery.json").read_text())["videos"]
    assert all(fingerprint(i.post, i.video, FONT, i.scene) == entries[name]["post"] for name, i in items.items())


# -- the one-time migration of a 1.0.0 manifest ---------------------------------------------------------------------
def legacy(item: Item, layout: str = LEGACY_LAYOUT_7CDAFF4) -> str:
    """The 1.0.0 post fingerprint as it was delivered: the layout code was the SHA-256 of thumbnail.py's source."""
    p = item.post
    data = {"text": p.text(), "thumbnail": asdict(p.thumbnail) if p.thumbnail else None, "layout": layout,
            "font": hashlib.sha256(FONT.read_bytes()).hexdigest()}  # fmt: skip
    if item.scene is not None:
        data["scene"] = hashlib.sha256(Path(item.scene).read_bytes()).hexdigest()
    return hashlib.sha256(json.dumps(data, sort_keys=True, ensure_ascii=False).encode()).hexdigest()


@pytest.fixture
def old_delivery(tmp_path):
    """A 1.0.0 manifest: a and c were delivered with the posts they have now (a by the thumbnail.py of 7cdaff4, c by
    that of f7c86d3), b with another headline, and gone is no longer published. Returns the items, the out folder and
    the entries as written."""
    renders = tmp_path / "renders"
    renders.mkdir()
    items = {
        "a": Item(post("A"), tall(renders / "a.mp4")),
        "b": Item(post("B"), tall(renders / "b.mp4")),
        "c": Item(post("C"), tall(renders / "c.mp4"), scene_doc(tmp_path / "c.scene.xml")),
    }
    other = legacy(Item(post("B before"), renders / "b.mp4"))  # b was delivered with another headline
    entries = {
        "a": {"render": "1" * 64, "post": legacy(items["a"]), "ig": "2" * 64, "cover": "3" * 64},
        "b": {"render": "4" * 64, "post": other, "ig": "5" * 64, "cover": "6" * 64},
        "c": {"render": "7" * 64, "post": legacy(items["c"], LEGACY_LAYOUT_F7C86D3), "ig": "8" * 64, "cover": "9" * 64},
        "gone": {"render": "a" * 64, "post": "b" * 64, "ig": "c" * 64, "cover": "d" * 64},
    }
    out = tmp_path / "ig"
    out.mkdir()
    (out / MANIFEST).write_text(json.dumps({"version": "1.0.0", "videos": entries}, indent=2) + "\n", "utf-8")
    return items, out, entries


def test_the_legacy_layouts_are_the_two_sources_every_1_0_0_delivery_hashed_and_no_other():
    assert LEGACY_LAYOUTS == {  # closed (ADR 0037): no later source is ever added
        "cee600d0102510c78586d39ac0c449c6a0a5959af04c6f97bfcd509971b86c09",  # thumbnail.py at f7c86d3^
        "96dfe994aa02fb4eb4028ffd5030aa7721463a810e7624de25d46737acee4f64",  # thumbnail.py at f7c86d3
    }
    assert isinstance(LEGACY_LAYOUTS, frozenset)


def test_an_entry_hashed_with_either_legacy_layout_migrates_and_one_with_another_source_is_kept(old_delivery):
    items, out, entries = old_delivery
    data = json.loads((out / MANIFEST).read_text(encoding="utf-8"))
    data["videos"]["a"]["post"] = legacy(items["a"], LEGACY_LAYOUT_F7C86D3)
    data["videos"]["c"]["post"] = legacy(items["c"], "0" * 64)  # a source no 1.0.0 delivery hashed
    (out / MANIFEST).write_text(json.dumps(data), encoding="utf-8")
    result = migrate_manifest(items, out, font=FONT, dry_run=True)
    assert result.migrated == ["a"]
    assert "not the 1.0.0 fingerprint" in dict(result.kept)["c"]


def test_an_old_manifest_is_refused_by_name_and_is_drift(old_delivery):
    items, out, _ = old_delivery
    with pytest.raises(ManifestVersionError, match="1.0.0.*instagram_posts.py migrate"):
        read_manifest(out)
    (drift,) = check_delivery(items, out, font=FONT)
    assert drift.name == "*" and "migrate" in drift.reason


def test_publish_refuses_to_replace_a_manifest_of_another_version(old_delivery):
    items, out, _ = old_delivery
    before = (out / MANIFEST).read_bytes()
    for version in ("1.0.0", "2.0.0"):
        (out / MANIFEST).write_bytes(before.replace(b'"1.0.0"', f'"{version}"'.encode()))
        with pytest.raises(ManifestVersionError, match=version):
            publish(items, out, font=FONT, engine="unused")
    assert sorted(p.name for p in out.iterdir()) == [MANIFEST]  # nothing delivered over it


def test_migrate_rewrites_only_the_post_of_an_entry_that_holds_the_old_fingerprint_of_the_post_now(old_delivery):
    items, out, entries = old_delivery
    result = migrate_manifest(items, out, font=FONT)
    assert result.migrated == ["a", "c"]
    assert [name for name, _ in result.kept] == ["b", "gone"]
    assert "not the 1.0.0 fingerprint" in dict(result.kept)["b"] and "no longer published" in dict(result.kept)["gone"]
    data = json.loads((out / MANIFEST).read_text(encoding="utf-8"))
    assert data["version"] == MANIFEST_VERSION == "1.1.0"
    for name in ("a", "c"):
        item = items[name]
        assert data["videos"][name] == entries[name] | {"post": fingerprint(item.post, item.video, FONT, item.scene)}
    assert data["videos"]["b"] == entries["b"] and data["videos"]["gone"] == entries["gone"]
    assert (out / MANIFEST).stat().st_mode & 0o777 == 0o600
    assert read_manifest(out) == data["videos"]
    assert sorted(p.name for p in out.iterdir()) == [MANIFEST, MANIFEST + ".lock"]  # no temporary file left


def test_a_dry_run_reports_the_same_plan_and_writes_nothing(old_delivery):
    items, out, _ = old_delivery
    files = {p.name: p.read_bytes() for p in out.iterdir()}
    result = migrate_manifest(items, out, font=FONT, dry_run=True)
    assert result.migrated == ["a", "c"] and [name for name, _ in result.kept] == ["b", "gone"]
    assert {p.name: p.read_bytes() for p in out.iterdir()} == files  # not even the lock file


def test_migrate_keeps_an_entry_without_a_render_or_whose_cover_cannot_be_drawn_now(old_delivery):
    items, out, _ = old_delivery
    renders = items["a"].video.parent
    absent, wide = (
        Item(post("A"), renders / "absent.mp4"),
        Item(post("A headline far too wide to fit"), renders / "b.mp4"),
    )
    data = json.loads((out / MANIFEST).read_text(encoding="utf-8"))
    data["videos"]["b"]["post"] = legacy(wide)  # delivered from this very post, which no longer lays out
    (out / MANIFEST).write_text(json.dumps(data), encoding="utf-8")
    result = migrate_manifest({**items, "a": absent, "b": wide}, out, font=FONT, dry_run=True)
    kept = dict(result.kept)
    assert result.migrated == ["c"]
    assert kept["a"] == f"no render at {renders / 'absent.mp4'}"
    assert kept["b"].startswith("the cover cannot be drawn now:") and "wider than" in kept["b"]


@pytest.mark.parametrize("dry_run", [True, False])
def test_migrate_refuses_a_font_it_cannot_read_and_writes_nothing(old_delivery, tmp_path, dry_run):
    """Kept for want of a font, every entry would land in a 1.1.0 manifest, which is never migrated again."""
    items, out, _ = old_delivery
    before = (out / MANIFEST).read_bytes()
    with pytest.raises(DeliveryError, match="gone.ttf"):
        migrate_manifest(items, out, font=tmp_path / "gone.ttf", dry_run=dry_run)
    assert (out / MANIFEST).read_bytes() == before and sorted(p.name for p in out.iterdir()) == [MANIFEST]


def test_migrate_reads_the_manifest_it_rewrites_under_the_delivery_lock(old_delivery, monkeypatch):
    items, out, entries = old_delivery
    real, held = fcntl.flock, []

    def flock(fd, operation):  # another delivery rewrote a's entry while this migration waited for the lock
        real(fd, operation)
        if operation == fcntl.LOCK_EX:
            held.append(Path(fd.name).name)
            data = json.loads((out / MANIFEST).read_text(encoding="utf-8"))
            data["videos"]["a"]["post"] = "f" * 64
            (out / MANIFEST).write_text(json.dumps(data), encoding="utf-8")

    monkeypatch.setattr(fcntl, "flock", flock)
    result = migrate_manifest(items, out, font=FONT)
    assert held == [MANIFEST + ".lock"]
    assert result.migrated == ["c"] and read_manifest(out)["a"]["post"] == "f" * 64  # the newer entry is kept


@pytest.mark.parametrize(
    "manifest, needle",
    [
        (None, "no delivery.json to migrate"),
        ("not json", "cannot be read"),
        ('{"version": "1.1.0", "videos": {}}', "already version 1.1.0"),
        ('{"version": "2.0.0", "videos": {}}', "version '2.0.0'"),
        ('{"version": "1.0.0", "videos": {"a": {"render": "x"}}}', "entry 'a'"),
    ],
)
def test_migrate_refuses_a_manifest_that_is_not_a_1_0_0_one(tmp_path, manifest, needle):
    if manifest is not None:
        (tmp_path / MANIFEST).write_text(manifest, encoding="utf-8")
    for dry_run in (True, False):
        with pytest.raises(DeliveryError, match=needle):
            migrate_manifest({}, tmp_path, font=FONT, dry_run=dry_run)
    assert (tmp_path / MANIFEST).read_text(encoding="utf-8") == manifest if manifest else not any(tmp_path.iterdir())


def test_the_migrate_command_prints_its_plan_and_writes_only_without_dry_run(old_delivery, monkeypatch, capsys):
    items, out, _ = old_delivery
    posts = shipped_posts()
    monkeypatch.setattr(posts, "font_file", lambda folder: FONT)
    monkeypatch.setattr(posts, "items", lambda renders, episodes=None: items)
    before = (out / MANIFEST).read_bytes()
    args = ["migrate", str(out), str(out), "--fonts", str(out)]
    assert posts.main([*args, "--dry-run"]) == 0
    printed = capsys.readouterr().out.splitlines()
    assert printed[:2] == ["migrate a", "migrate c"] and printed[2].startswith("keep b: ")
    assert printed[3].startswith("keep gone: ") and printed[4:] == ["2 migrated, 2 kept (dry run: nothing written)"]
    assert (out / MANIFEST).read_bytes() == before
    assert posts.main(args) == 0
    assert capsys.readouterr().out.splitlines()[-1] == f"2 migrated, 2 kept; {out / MANIFEST} is now version 1.1.0"
    with pytest.raises(SystemExit, match="migrate: .* already version 1.1.0"):
        posts.main(args)


def shipped_posts():
    sys.path.insert(0, str(EPISODES))
    try:
        import instagram_posts as posts
    finally:
        sys.path.pop(0)
    return posts


def tags(n: int) -> tuple[str, ...]:
    return tuple(f"#tag{i}" for i in range(n))


def test_the_limit_is_instagrams_five():
    assert HASHTAG_LIMIT == 5


def test_a_published_post_over_the_limit_stays_valid_so_a_rebuild_writes_its_caption(tmp_path):
    post = InstagramPost(title="t", description="d", hashtags=tags(8))
    assert post.problems() == []
    assert post.write(tmp_path).is_file()


@pytest.mark.parametrize(
    "caption, count",
    [
        ("", 0),
        ("Title\n\nNo tags, and a #1 rule, and ## nothing.\n", 0),
        (InstagramPost(title="t", description="d", hashtags=tags(5)).text(), 5),
        (InstagramPost(title="t", description="d", hashtags=tags(6)).text(), 6),
        (InstagramPost(title="t", description="One #inline tag.", hashtags=tags(5)).text(), 6),
        ("#one#two", 1),
        ("#é_1 #a1 #1a", 3),
        ("see x.com/page#fragment #real", 1),
    ],
)
def test_the_whole_caption_is_counted(caption, count):
    says = social.hashtag_excess(caption)
    assert says == (f"{count} hashtags; Instagram accepts 5" if count > 5 else "")


def test_a_hashtag_refusal_is_typed_and_names_every_slug_and_its_reason():
    with pytest.raises(HashtagError) as e:
        social.refuse_hashtags({"a": "6 hashtags", "b": "", "c": "7 hashtags"})
    assert isinstance(e.value, DeliveryError)
    assert str(e.value) == "the hashtag limit refuses: a: 6 hashtags; c: 7 hashtags"


def test_nothing_over_is_nothing_refused():
    social.refuse_hashtags({"a": "", "b": ""})


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


def test_every_shipped_release_pins_its_characters():
    posts = shipped_posts()
    assert [slug for slug, r in posts.RELEASES.items() if r.parts is None] == []


def toon_scripts() -> list[Path]:
    return [p for p in sorted(EPISODES.glob("*.py")) if "from srstudio.toon_sketch import Staging" in p.read_text()]


def test_every_toon_script_draws_the_versions_its_release_pins():
    scripts = toon_scripts()
    assert len(scripts) >= 19
    missing = [p.name for p in scripts if "versions=PINS[SKETCH.slug]" not in p.read_text(encoding="utf-8")]
    assert missing == []


@pytest.mark.parametrize("script", toon_scripts(), ids=lambda p: p.stem)
def test_a_toon_sketch_pins_every_character_it_shows(script):
    posts = shipped_posts()
    sys.path.insert(0, str(EPISODES))
    try:
        sk = importlib.import_module(f"{script.stem}_data").SKETCH
    finally:
        sys.path.pop(0)
    shown = {sketch.part_of(beat.who) for beat in sk.beats if beat.who not in sk.bare}
    assert shown <= set(posts.RELEASES[sk.slug].parts)


def test_a_toon_reel_outside_the_sketch_builder_stays_on_version_one():
    """Only ``toon_sketch.build`` reads a pin, so a script that draws for itself draws version 1 by code."""
    posts = shipped_posts()
    routed = {p.stem for p in toon_scripts()}
    outside = {
        r.builder_name: r.parts
        for r in posts.RELEASES.values()
        if r.builder_name not in routed and any(parts.get(n).style == "toon" for n in r.parts)
    }
    assert set(outside) == {"employee_survey"}
    assert all(number == 1 for pins in outside.values() for number in pins.values())


ON_THE_FLOOR = Scores(15, 14)


def unpinned_release(posts, monkeypatch, tmp_path) -> Path:
    """The shipped delivery with one release added that pins nothing, and nothing else to compare."""
    post = next(iter(posts.POSTS.values()))
    monkeypatch.setattr(posts, "RELEASES", {"new-reel": Release("new-reel", post, video="New_Reel")})
    monkeypatch.setattr(posts, "items", lambda *a, **kw: {})
    monkeypatch.setattr(posts, "font_file", lambda folder: tmp_path / "font.ttf")
    monkeypatch.setattr(posts, "check_delivery", lambda *a, **kw: [])
    monkeypatch.setattr(posts, "caption_drift", lambda *a, **kw: [])
    monkeypatch.setattr(posts, "FROZEN", {})
    renders = tmp_path / "renders"
    renders.mkdir()
    return renders


def test_the_check_gate_reports_a_release_with_a_missing_pin(monkeypatch, tmp_path):
    posts = shipped_posts()
    renders = unpinned_release(posts, monkeypatch, tmp_path)
    drift = posts.check_all(renders / "ig", renders, fonts_dir=tmp_path)
    assert [d.name for d in drift] == ["New_Reel"] and "pins no part versions" in drift[0].reason


def test_the_deliver_gate_refuses_a_release_with_a_missing_pin_before_it_writes(monkeypatch, tmp_path):
    posts = shipped_posts()
    renders = unpinned_release(posts, monkeypatch, tmp_path)

    def wrote(*a, **kw):
        raise AssertionError("a release with a missing pin reached publish")

    monkeypatch.setattr(posts, "publish", wrote)
    with pytest.raises(DeliveryError, match="New_Reel: pins no part versions"):
        posts.write_all(renders / "ig", renders, fonts_dir=tmp_path, engine="engine")
    args = ["deliver", str(renders / "ig"), str(renders), "--fonts", str(tmp_path), "--engine", "engine"]
    with pytest.raises(SystemExit, match="deliver: New_Reel: pins no part versions"):
        posts.main(args)


def test_delivering_one_video_answers_only_for_its_own_pins(monkeypatch, tmp_path):
    posts = shipped_posts()
    renders = unpinned_release(posts, monkeypatch, tmp_path)
    monkeypatch.setattr(posts, "publish", lambda *a, **kw: [])
    assert posts.write_all(renders / "ig", renders, fonts_dir=tmp_path, engine="e", only=["Other"]) == []


def test_the_deliver_gate_refuses_a_stale_video_whose_build_left_no_record(monkeypatch, tmp_path):
    posts = shipped_posts()
    renders = unpinned_release(posts, monkeypatch, tmp_path)
    post = next(iter(posts.POSTS.values()))
    monkeypatch.setattr(posts, "RELEASES", {"new-reel": Release("new-reel", post, video="New_Reel", parts={})})
    monkeypatch.setattr(posts, "check_delivery", lambda *a, **kw: [Drift("New_Reel", "never delivered")])
    with pytest.raises(DeliveryError, match="New_Reel: no record of what its build drew"):
        posts.write_all(renders / "ig", renders, fonts_dir=tmp_path, engine="engine")


def test_the_deliver_gate_leaves_a_current_published_video_with_no_record_alone(monkeypatch, tmp_path):
    posts = shipped_posts()
    renders = unpinned_release(posts, monkeypatch, tmp_path)
    post = next(iter(posts.POSTS.values()))
    monkeypatch.setattr(posts, "RELEASES", {"new-reel": Release("new-reel", post, video="New_Reel", parts={})})
    monkeypatch.setattr(posts, "publish", lambda *a, **kw: [])
    assert posts.write_all(renders / "ig", renders, fonts_dir=tmp_path, engine="engine") == []


def test_an_unreadable_manifest_means_every_video_is_being_delivered(monkeypatch, tmp_path):
    posts = shipped_posts()
    renders = unpinned_release(posts, monkeypatch, tmp_path)
    post = next(iter(posts.POSTS.values()))
    monkeypatch.setattr(posts, "RELEASES", {"new-reel": Release("new-reel", post, video="New_Reel", parts={})})
    monkeypatch.setattr(posts, "check_delivery", lambda *a, **kw: [Drift("*", "unreadable")])
    with pytest.raises(DeliveryError, match="New_Reel: no record of what its build drew"):
        posts.write_all(renders / "ig", renders, fonts_dir=tmp_path, engine="engine")


def _new_reel(posts, monkeypatch, tmp_path, repo, comedy=ON_THE_FLOOR, hashtags=("#everydaylife",)):
    renders = unpinned_release(posts, monkeypatch, tmp_path)
    post = replace(next(iter(posts.POSTS.values())), hashtags=hashtags)
    release = Release("new-reel", post, video="New_Reel", parts={}, comedy=comedy)
    monkeypatch.setattr(posts, "RELEASES", {"new-reel": release})
    monkeypatch.setattr(posts, "REPO", repo)
    monkeypatch.setattr(posts, "BIBLE_DIR", bible_docs.locked(tmp_path / "bible"))
    monkeypatch.setattr(posts.releases, "unpinned", lambda *a, **kw: [])
    monkeypatch.setattr(posts.releases, "doubled_captions", lambda *a, **kw: [])
    monkeypatch.setattr(posts.releases, "caption_on_cover", lambda *a, **kw: [])
    monkeypatch.setattr(posts, "publish", lambda *a, **kw: ["written"])
    return renders


def test_a_first_delivery_without_an_enhancement_is_refused_before_it_writes(monkeypatch, tmp_path):
    posts = shipped_posts()
    renders = _new_reel(posts, monkeypatch, tmp_path, tmp_path)
    monkeypatch.setattr(
        posts.auto_enhance, "refused", lambda videos, repo: [Drift(videos["new-reel"], "no enhancement")]
    )
    monkeypatch.setattr(posts, "publish", lambda *a, **kw: pytest.fail("the gate must refuse before delivering"))
    with pytest.raises(DeliveryError, match="New_Reel: no enhancement"):
        posts.write_all(renders / "ig", renders, fonts_dir=tmp_path, engine="engine", only=["New_Reel"])


def test_auto_enhance_off_just_delivers(monkeypatch, tmp_path):
    posts = shipped_posts()
    renders = _new_reel(posts, monkeypatch, tmp_path, tmp_path)
    posts.auto_enhance.set_mode(tmp_path, on=False)
    assert posts.write_all(renders / "ig", renders, fonts_dir=tmp_path, engine="engine", only=["New_Reel"]) == [
        "written"
    ]


def test_a_video_already_delivered_owes_no_enhancement(monkeypatch, tmp_path):
    posts = shipped_posts()
    renders = _new_reel(posts, monkeypatch, tmp_path, tmp_path)
    monkeypatch.setattr(posts, "read_manifest", lambda out: {"New_Reel": {}})
    assert posts.write_all(renders / "ig", renders, fonts_dir=tmp_path, engine="engine", only=["New_Reel"]) == [
        "written"
    ]


@pytest.mark.parametrize(
    "scores, says",
    [
        (None, "new-reel: no comedy scores"),
        (Scores(13, 13), "new-reel: comedy score 13 "),
        (Scores(20, 13), "new-reel: comedy score 13 "),
        (Scores(13, 20), "new-reel: comedy score 13 "),
        (Scores(21, 15), "new-reel: comedy-author 21 is not between 0 and 20"),
        (Scores(15, -1), "new-reel: comedy-reviewer -1 is not between 0 and 20"),
        (Scores("15", 15), "new-reel: comedy-author '15' is not a whole number"),
    ],
)
def test_a_first_delivery_short_of_the_comedy_floor_is_refused_before_it_writes(monkeypatch, tmp_path, scores, says):
    posts = shipped_posts()
    renders = _new_reel(posts, monkeypatch, tmp_path, tmp_path, scores)
    posts.auto_enhance.set_mode(tmp_path, on=False)  # the floor has no mode: turning auto-enhance off does not lift it
    monkeypatch.setattr(posts, "publish", lambda *a, **kw: pytest.fail("the gate must refuse before delivering"))
    with pytest.raises(ComedyError, match="comedy floor refuses.*" + re.escape(says)):
        posts.write_all(renders / "ig", renders, fonts_dir=tmp_path, engine="engine", only=["New_Reel"])
    argv = ["deliver", str(renders / "ig"), str(renders), "--fonts", str(tmp_path), "--engine", "engine"]
    with pytest.raises(SystemExit, match="deliver: the comedy floor refuses.*" + re.escape(says)):
        posts.main([*argv, "--only", "New_Reel"])


def _run_together(tmp_path: Path, slug: str = "new-reel") -> None:
    """A built project beside the renders, whose burned caption runs two sentences together."""
    project = tmp_path / "episodes" / slug
    project.mkdir(parents=True)
    (project / f"{slug}.scene.xml").write_bytes(
        b'<scene><assets><text id="t" text="Take it Whatever"/></assets><layer id="l" asset="t"/></scene>'
    )
    (project / "voice-transcript.json").write_text('{"lines": [{"expected": "Take it. Whatever I say."}]}')


def test_a_first_delivery_with_a_run_together_caption_is_refused_before_it_writes(monkeypatch, tmp_path):
    posts = shipped_posts()
    renders = _new_reel(posts, monkeypatch, tmp_path, tmp_path, ON_THE_FLOOR)
    posts.auto_enhance.set_mode(tmp_path, on=False)
    _run_together(tmp_path)
    monkeypatch.setattr(posts.frame_gates, "signature_hidden", lambda *a, **kw: [])
    monkeypatch.setattr(posts.figure_gates, "figure_defects", lambda *a, **kw: [])
    monkeypatch.setattr(posts, "publish", lambda *a, **kw: pytest.fail("the gate must refuse before delivering"))
    with pytest.raises(frame_gates.FrameGateError, match="New_Reel: the caption 'Take it Whatever' runs 'it'"):
        posts.write_all(renders / "ig", renders, fonts_dir=tmp_path, engine="engine", only=["New_Reel"])
    argv = ["deliver", str(renders / "ig"), str(renders), "--fonts", str(tmp_path), "--engine", "engine"]
    with pytest.raises(SystemExit, match="deliver: the frame gates refuse: New_Reel"):
        posts.main([*argv, "--only", "New_Reel"])


def test_a_published_reel_with_a_run_together_caption_stays_as_it_went_out(monkeypatch, tmp_path):
    posts = shipped_posts()
    renders = _new_reel(posts, monkeypatch, tmp_path, tmp_path, ON_THE_FLOOR)
    posts.auto_enhance.set_mode(tmp_path, on=False)
    _run_together(tmp_path)
    monkeypatch.setattr(posts, "read_manifest", lambda out: {"New_Reel": {}})
    monkeypatch.setattr(posts, "publish", lambda *a, **kw: ["written"])
    assert posts.write_all(renders / "ig", renders, fonts_dir=tmp_path, engine="engine", only=["New_Reel"]) == [
        "written"
    ]


def test_a_first_delivery_that_hides_its_signature_is_refused_before_it_writes(monkeypatch, tmp_path):
    posts = shipped_posts()
    renders = _new_reel(posts, monkeypatch, tmp_path, tmp_path, ON_THE_FLOOR)
    posts.auto_enhance.set_mode(tmp_path, on=False)
    asked = []

    def hidden(releases, episodes, first, engine):
        asked.append((dict(first), engine))
        return [Drift("New_Reel", "both signature marks are seen in 0%")]

    monkeypatch.setattr(posts.frame_gates, "signature_hidden", hidden)
    monkeypatch.setattr(posts, "publish", lambda *a, **kw: pytest.fail("the gate must refuse before delivering"))
    with pytest.raises(frame_gates.FrameGateError, match="New_Reel: both signature marks are seen in 0%"):
        posts.write_all(renders / "ig", renders, fonts_dir=tmp_path, engine="the-engine", only=["New_Reel"])
    assert asked == [({"new-reel": "New_Reel"}, "the-engine")]


def test_a_first_delivery_with_a_defect_on_its_frames_is_refused_before_it_writes(monkeypatch, tmp_path):
    posts = shipped_posts()
    renders = _new_reel(posts, monkeypatch, tmp_path, tmp_path, ON_THE_FLOOR)
    posts.auto_enhance.set_mode(tmp_path, on=False)
    asked = []

    def defects(releases, episodes, first, engine):
        asked.append((dict(first), engine))
        return [Drift("New_Reel", "toon-hamster ends in a straight cut")]

    monkeypatch.setattr(posts.figure_gates, "figure_defects", defects)
    monkeypatch.setattr(posts, "publish", lambda *a, **kw: pytest.fail("the gate must refuse before delivering"))
    with pytest.raises(frame_gates.FrameGateError, match="New_Reel: toon-hamster ends in a straight cut"):
        posts.write_all(renders / "ig", renders, fonts_dir=tmp_path, engine="the-engine", only=["New_Reel"])
    assert asked == [({"new-reel": "New_Reel"}, "the-engine")]


def test_a_new_reel_owes_the_floor_even_when_the_delivery_finds_it_by_drift(monkeypatch, tmp_path):
    posts = shipped_posts()
    renders = _new_reel(posts, monkeypatch, tmp_path, tmp_path, None)
    posts.auto_enhance.set_mode(tmp_path, on=False)
    monkeypatch.setattr(posts, "check_delivery", lambda *a, **kw: [Drift("New_Reel", "never delivered")])
    with pytest.raises(ComedyError, match="new-reel"):
        posts.write_all(renders / "ig", renders, fonts_dir=tmp_path, engine="engine")


@pytest.mark.parametrize("scores", [Scores(14, 14), Scores(14, 20), Scores(20, 14)])
def test_a_first_delivery_on_the_comedy_floor_delivers(monkeypatch, tmp_path, scores):
    posts = shipped_posts()
    renders = _new_reel(posts, monkeypatch, tmp_path, tmp_path, scores)
    posts.auto_enhance.set_mode(tmp_path, on=False)
    assert posts.write_all(renders / "ig", renders, fonts_dir=tmp_path, engine="engine", only=["New_Reel"]) == [
        "written"
    ]


@pytest.mark.parametrize("scores", [None, Scores(3, 3)])
def test_a_video_already_delivered_owes_no_comedy_score(monkeypatch, tmp_path, scores):
    posts = shipped_posts()
    renders = _new_reel(posts, monkeypatch, tmp_path, tmp_path, scores)
    posts.auto_enhance.set_mode(tmp_path, on=False)
    monkeypatch.setattr(posts, "read_manifest", lambda out: {"New_Reel": {}})
    assert posts.write_all(renders / "ig", renders, fonts_dir=tmp_path, engine="engine", only=["New_Reel"]) == [
        "written"
    ]


def test_delivering_another_video_answers_for_no_comedy_score(monkeypatch, tmp_path):
    posts = shipped_posts()
    renders = _new_reel(posts, monkeypatch, tmp_path, tmp_path, None)
    posts.auto_enhance.set_mode(tmp_path, on=False)
    assert posts.write_all(renders / "ig", renders, fonts_dir=tmp_path, engine="engine", only=["Other"]) == ["written"]


def test_a_first_delivery_over_the_hashtag_limit_is_refused_before_it_writes(monkeypatch, tmp_path):
    posts = shipped_posts()
    renders = _new_reel(posts, monkeypatch, tmp_path, tmp_path, hashtags=tags(HASHTAG_LIMIT + 1))
    posts.auto_enhance.set_mode(tmp_path, on=False)  # the limit is Instagram's: no mode lifts it
    monkeypatch.setattr(posts, "publish", lambda *a, **kw: pytest.fail("the gate must refuse before delivering"))
    with pytest.raises(HashtagError, match="new-reel: 6 hashtags; Instagram accepts 5"):
        posts.write_all(renders / "ig", renders, fonts_dir=tmp_path, engine="engine", only=["New_Reel"])
    argv = ["deliver", str(renders / "ig"), str(renders), "--fonts", str(tmp_path), "--engine", "engine"]
    with pytest.raises(SystemExit, match="deliver: .*new-reel: 6 hashtags"):
        posts.main([*argv, "--only", "New_Reel"])


def test_a_new_reel_owes_the_hashtag_limit_even_when_the_delivery_finds_it_by_drift(monkeypatch, tmp_path):
    posts = shipped_posts()
    renders = _new_reel(posts, monkeypatch, tmp_path, tmp_path, hashtags=tags(HASHTAG_LIMIT + 1))
    posts.auto_enhance.set_mode(tmp_path, on=False)
    monkeypatch.setattr(posts, "check_delivery", lambda *a, **kw: [Drift("New_Reel", "never delivered")])
    with pytest.raises(HashtagError, match="new-reel"):
        posts.write_all(renders / "ig", renders, fonts_dir=tmp_path, engine="engine")


def test_a_first_delivery_at_the_hashtag_limit_delivers(monkeypatch, tmp_path):
    posts = shipped_posts()
    renders = _new_reel(posts, monkeypatch, tmp_path, tmp_path, hashtags=tags(HASHTAG_LIMIT))
    posts.auto_enhance.set_mode(tmp_path, on=False)
    assert posts.write_all(renders / "ig", renders, fonts_dir=tmp_path, engine="engine", only=["New_Reel"]) == [
        "written"
    ]


def test_a_video_already_delivered_keeps_the_hashtags_it_was_published_with(monkeypatch, tmp_path):
    posts = shipped_posts()
    renders = _new_reel(posts, monkeypatch, tmp_path, tmp_path, hashtags=tags(8))
    posts.auto_enhance.set_mode(tmp_path, on=False)
    monkeypatch.setattr(posts, "read_manifest", lambda out: {"New_Reel": {}})
    assert posts.write_all(renders / "ig", renders, fonts_dir=tmp_path, engine="engine", only=["New_Reel"]) == [
        "written"
    ]


def test_delivering_another_video_answers_for_no_hashtags(monkeypatch, tmp_path):
    posts = shipped_posts()
    renders = _new_reel(posts, monkeypatch, tmp_path, tmp_path, hashtags=tags(8))
    posts.auto_enhance.set_mode(tmp_path, on=False)
    assert posts.write_all(renders / "ig", renders, fonts_dir=tmp_path, engine="engine", only=["Other"]) == ["written"]


def test_the_check_gate_passes_a_published_post_over_the_hashtag_limit(monkeypatch, tmp_path):
    posts = shipped_posts()
    renders = _new_reel(posts, monkeypatch, tmp_path, tmp_path, hashtags=tags(8))
    assert posts.check_all(renders / "ig", renders, fonts_dir=tmp_path) == []


def test_the_check_gate_asks_no_comedy_score(monkeypatch, tmp_path):
    posts = shipped_posts()
    renders = _new_reel(posts, monkeypatch, tmp_path, tmp_path, None)
    assert posts.check_all(renders / "ig", renders, fonts_dir=tmp_path) == []


def test_a_release_holds_its_scores_typed():
    post = next(iter(shipped_posts().POSTS.values()))
    assert Release("new-reel", post, comedy=Scores(15, 14)).comedy == Scores(15, 14)
    with pytest.raises(ReleaseError, match="new-reel: comedy is a tuple, not Scores"):
        Release("new-reel", post, comedy=(15, 14))


def test_the_published_delivery_has_not_drifted():
    """The publish gate: with ``SRSTUDIO_RENDERS`` (the rendered videos, delivered into ``<renders>/ig``) and
    ``SRSTUDIO_FONTS`` (the pinned headline font) set, every video's ig.txt and cover must match its render and post."""
    renders, fonts_dir = os.environ.get("SRSTUDIO_RENDERS"), os.environ.get("SRSTUDIO_FONTS")
    if not renders or not fonts_dir:
        pytest.skip("set SRSTUDIO_RENDERS and SRSTUDIO_FONTS to check the published delivery")
    drift = shipped_posts().check_all(Path(renders) / "ig", Path(renders), fonts_dir=Path(fonts_dir))
    assert drift == [], "the delivery drifted; run instagram_posts.py deliver:\n" + "\n".join(map(str, drift))


def _naming(posts, monkeypatch, *names):
    release = posts.RELEASES["new-reel"]
    tags = Tags("money-services", "other-person", "recognition", recurring=names)
    monkeypatch.setattr(posts, "RELEASES", {"new-reel": replace(release, tags=tags)})


def test_a_first_delivery_naming_a_character_the_bible_lacks_is_refused_before_it_writes(monkeypatch, tmp_path):
    posts = shipped_posts()
    renders = _new_reel(posts, monkeypatch, tmp_path, tmp_path)
    posts.auto_enhance.set_mode(tmp_path, on=False)
    _naming(posts, monkeypatch, "rex", "bruno")
    monkeypatch.setattr(posts, "publish", lambda *a, **kw: pytest.fail("the gate must refuse before delivering"))
    with pytest.raises(DeliveryError, match="cast bible refuses.*new-reel: unknown-name: 'bruno'"):
        posts.write_all(renders / "ig", renders, fonts_dir=tmp_path, engine="engine", only=["New_Reel"])
    argv = ["deliver", str(renders / "ig"), str(renders), "--fonts", str(tmp_path), "--engine", "engine"]
    with pytest.raises(SystemExit, match="deliver: .*new-reel: unknown-name: 'bruno'"):
        posts.main([*argv, "--only", "New_Reel"])


def test_a_first_delivery_that_names_only_the_bibles_characters_delivers(monkeypatch, tmp_path):
    posts = shipped_posts()
    renders = _new_reel(posts, monkeypatch, tmp_path, tmp_path)
    posts.auto_enhance.set_mode(tmp_path, on=False)
    _naming(posts, monkeypatch, "rex", "fern")
    assert posts.write_all(renders / "ig", renders, fonts_dir=tmp_path, engine="engine", only=["New_Reel"]) == [
        "written"
    ]


def test_a_first_delivery_that_redraws_a_recurring_figures_base_rig_is_refused_before_it_writes(monkeypatch, tmp_path):
    posts = shipped_posts()
    renders = _new_reel(posts, monkeypatch, tmp_path, tmp_path)
    posts.auto_enhance.set_mode(tmp_path, on=False)
    _naming(posts, monkeypatch, "rex", "fern")
    seen = []

    def drawn(release, episodes, scripts, scratch):
        seen.append((release.slug, scripts, scratch))
        return [posts.bible_check.Finding(release.slug, "rig", "'dev' drawn with neck True")]

    monkeypatch.setattr(posts.bible_rig, "check_release", drawn)
    monkeypatch.setattr(posts, "publish", lambda *a, **kw: pytest.fail("the gate must refuse before delivering"))
    with pytest.raises(DeliveryError, match="cast bible refuses.*new-reel: rig: 'dev' drawn with neck True"):
        posts.write_all(renders / "ig", renders, fonts_dir=tmp_path, engine="engine", only=["New_Reel"])
    assert seen == [("new-reel", Path(posts.__file__).resolve().parent, tmp_path / "_tmp" / "rig")]


def test_a_rig_that_cannot_be_read_refuses_the_first_delivery_instead_of_passing_it(monkeypatch, tmp_path):
    posts = shipped_posts()
    renders = _new_reel(posts, monkeypatch, tmp_path, tmp_path)
    posts.auto_enhance.set_mode(tmp_path, on=False)
    _naming(posts, monkeypatch, "rex", "fern")

    def unreadable(*args):
        raise posts.bible_rig.RigError("new-reel: its builder failed")

    monkeypatch.setattr(posts.bible_rig, "check_release", unreadable)
    monkeypatch.setattr(posts, "publish", lambda *a, **kw: pytest.fail("the gate must refuse before delivering"))
    with pytest.raises(DeliveryError, match="new-reel: its builder failed"):
        posts.write_all(renders / "ig", renders, fonts_dir=tmp_path, engine="engine", only=["New_Reel"])


def test_a_video_already_delivered_is_never_refused_by_the_bible(monkeypatch, tmp_path):
    posts = shipped_posts()
    renders = _new_reel(posts, monkeypatch, tmp_path, tmp_path)
    posts.auto_enhance.set_mode(tmp_path, on=False)
    _naming(posts, monkeypatch, "bruno")
    monkeypatch.setattr(posts, "read_manifest", lambda out: {"New_Reel": {}})
    assert posts.write_all(renders / "ig", renders, fonts_dir=tmp_path, engine="engine", only=["New_Reel"]) == [
        "written"
    ]


def test_a_bible_that_cannot_be_read_refuses_the_first_delivery_instead_of_passing_it(monkeypatch, tmp_path):
    posts = shipped_posts()
    renders = _new_reel(posts, monkeypatch, tmp_path, tmp_path)
    posts.auto_enhance.set_mode(tmp_path, on=False)
    monkeypatch.setattr(posts, "BIBLE_DIR", tmp_path / "nowhere")
    with pytest.raises(DeliveryError, match="the cast bible cannot be read"):
        posts.write_all(renders / "ig", renders, fonts_dir=tmp_path, engine="engine", only=["New_Reel"])


def test_a_bible_edited_without_a_new_version_refuses_the_first_delivery(monkeypatch, tmp_path):
    posts = shipped_posts()
    renders = _new_reel(posts, monkeypatch, tmp_path, tmp_path)
    posts.auto_enhance.set_mode(tmp_path, on=False)
    _naming(posts, monkeypatch, "rex", "fern")
    cast = tmp_path / "bible" / "cast.json"
    cast.write_text(cast.read_text().replace("a holiday rental", "a cabin by a lake"))  # drift: no bump, no lock
    monkeypatch.setattr(posts, "publish", lambda *a, **kw: pytest.fail("the gate must refuse before delivering"))
    with pytest.raises(DeliveryError, match="cast bible cannot be read.*place:.*changed without a version bump"):
        posts.write_all(renders / "ig", renders, fonts_dir=tmp_path, engine="engine", only=["New_Reel"])
