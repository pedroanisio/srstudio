"""Releases: one file per published episode declares its post, its video name and whether its cover is drawn from
the scene's cover variant; :func:`srstudio.releases.load` finds them, and :func:`srstudio.releases.items` refuses a
declaration that disagrees with the built scene."""

import textwrap
from dataclasses import replace
from pathlib import Path

import pytest

from srstudio import parts, releases
from srstudio.releases import Release, ReleaseError
from srstudio.social import InstagramPost, Item
from srstudio.thumbnail import Thumbnail

POST = InstagramPost(title="A title", description="A description.", thumbnail=Thumbnail("Two\nlines", 1.0))

HEADER = "from srstudio.releases import Release\nfrom srstudio.social import InstagramPost\n"


def folder(tmp_path: Path, files: dict[str, str]) -> Path:
    root = tmp_path / "posts"
    root.mkdir()
    (root / "__init__.py").write_text("")
    for name, body in files.items():
        (root / name).write_text(textwrap.dedent(body))
    return root


def release_file(slug: str, extra: str = "") -> str:
    return HEADER + f'RELEASE = Release("{slug}", InstagramPost(title="T {slug}", description="D."){extra})\n'


def scene(tmp_path: Path, slug: str, name: str = "", cover: bool = True) -> Path:
    project = tmp_path / "episodes" / slug
    project.mkdir(parents=True)
    variant = '<parameters><variant id="cover"><override target="a" property="visible" value="false"/></variant>'
    body = f"<scene>{variant + '</parameters>' if cover else ''}<project/></scene>"
    (project / (name or f"{slug}.scene.xml")).write_text(body)
    return project.parent


def test_a_release_names_its_video_and_scene_after_its_slug_unless_told_otherwise():
    plain = Release("going-down", POST)
    assert (plain.video_name, plain.scene_file, plain.script) == ("going-down", "going-down.scene.xml", "going_down")
    assert plain.builder_name == "going_down"
    told = Release(
        "scene", POST, video="Printer_Recreation", scene="scene.xml", cover=True, builder="printer_recreation"
    )
    assert (told.video_name, told.scene_file, told.builder_name) == (
        "Printer_Recreation",
        "scene.xml",
        "printer_recreation",
    )


def test_a_release_is_frozen_at_one_cover_fingerprint_or_not_at_all():
    assert Release("ok", POST).frozen == ""
    assert Release("ok", POST, frozen="0f" * 32).frozen == "0f" * 32


@pytest.mark.parametrize(
    ("kw", "match"),
    [
        (dict(slug="Going Down"), "slug"),
        (dict(slug=""), "slug"),
        (dict(video="a/b"), "video"),
        (dict(scene="../x.scene.xml"), "scene"),
        (dict(scene="x.json"), "scene"),
        (dict(post="not a post"), "post"),
        (dict(builder="printer-recreation"), "builder"),
        (dict(frozen="abc"), "frozen"),
        (dict(frozen="A" * 64), "frozen"),
    ],
)
def test_a_release_refuses_what_it_cannot_publish(kw, match):
    args = dict(slug="ok", post=POST) | kw
    with pytest.raises(ReleaseError, match=match):
        Release(**args)


def test_load_finds_every_release_keyed_by_slug(tmp_path):
    root = folder(
        tmp_path,
        {
            "going_down.py": release_file("going-down"),
            "scene.py": release_file("scene", ', video="Printer_Recreation"'),
            "_shared.py": "NOT_A_RELEASE = 1\n",
        },
    )
    found = releases.load(root)
    assert list(found) == ["going-down", "scene"]
    assert found["scene"].video_name == "Printer_Recreation"


def test_a_release_file_can_share_constants_with_its_siblings(tmp_path):
    root = folder(
        tmp_path,
        {
            "_series.py": 'TAGS = ("#a", "#b")\n',
            "one.py": HEADER + "from ._series import TAGS\n"
            'RELEASE = Release("one", InstagramPost(title="T", description="D.", hashtags=TAGS))\n',
        },
    )
    assert releases.load(root)["one"].post.hashtags == ("#a", "#b")


@pytest.mark.parametrize(
    ("files", "match"),
    [
        ({"one.py": "X = 1\n"}, "RELEASE"),
        ({"one.py": HEADER + "RELEASE = 3\n"}, "Release"),
        ({"two.py": release_file("one")}, "file"),
        ({"one.py": release_file("one"), "uno.py": release_file("uno", ', video="one"')}, "video"),
        ({"one.py": "raise RuntimeError('boom')\n"}, "one.py"),
    ],
)
def test_load_refuses_a_folder_it_cannot_trust(tmp_path, files, match):
    with pytest.raises(ReleaseError, match=match):
        releases.load(folder(tmp_path, files))


def test_a_package_that_fails_to_import_is_refused_every_time_until_it_is_fixed(tmp_path):
    root = folder(tmp_path, {"one.py": release_file("one")})
    (root / "__init__.py").write_text("raise RuntimeError('broken shared constants')\n")
    for _ in range(2):  # not half-imported on the second try, where it would silently hold no release
        with pytest.raises(ReleaseError, match="__init__.py cannot be imported: broken shared constants"):
            releases.load(root)
    (root / "__init__.py").write_text("")
    assert list(releases.load(root)) == ["one"]


def test_load_twice_gives_the_same_releases(tmp_path):
    root = folder(tmp_path, {"one.py": release_file("one")})
    assert releases.load(root) == releases.load(root)


def test_load_needs_a_package_folder(tmp_path):
    with pytest.raises(ReleaseError, match="__init__"):
        releases.load(tmp_path)


def test_items_pair_each_post_with_its_render_and_its_cover_scene(tmp_path):
    episodes = scene(tmp_path, "covered")
    scene(tmp_path, "plain", cover=False)
    found = {"covered": Release("covered", POST, cover=True), "plain": Release("plain", POST, video="Plain_Video")}
    got = releases.items(found, tmp_path / "renders", episodes)
    assert got == {
        "covered": Item(POST, tmp_path / "renders" / "covered.mp4", episodes / "covered" / "covered.scene.xml"),
        "Plain_Video": Item(POST, tmp_path / "renders" / "Plain_Video.mp4", None),
    }


@pytest.mark.parametrize(("cover", "has_variant", "match"), [(False, True, "hides"), (True, False, "no cover variant")])
def test_items_refuse_a_cover_declaration_the_scene_contradicts(tmp_path, cover, has_variant, match):
    episodes = scene(tmp_path, "one", cover=has_variant)
    with pytest.raises(ReleaseError, match=match):
        releases.items({"one": Release("one", POST, cover=cover)}, tmp_path / "renders", episodes)


def test_items_trust_the_declaration_when_the_project_is_not_built_here(tmp_path):
    got = releases.items({"one": Release("one", POST, cover=True)}, tmp_path / "renders", tmp_path / "episodes")
    assert got["one"].scene == tmp_path / "episodes" / "one" / "one.scene.xml"


def test_items_refuse_a_scene_that_is_not_xml(tmp_path):
    project = tmp_path / "episodes" / "one"
    project.mkdir(parents=True)
    (project / "one.scene.xml").write_text("<scene>")
    with pytest.raises(ReleaseError, match="cannot read"):
        releases.items({"one": Release("one", POST)}, tmp_path / "renders", tmp_path / "episodes")


def test_a_new_release_carries_tags_and_a_published_one_need_not():
    tags = releases.Tags("family", "protagonist", "embarrassment", recurring=("gary", "kai"), test="opening", arm="a")
    assert Release("the-family-photo", POST, tags=tags).tags == tags
    assert Release("going-down", POST).tags is None
    assert releases.Tags("everyday-tech", "institution", "recognition").recurring == ()


def test_the_posting_jobs_hook_motion_test_is_a_known_test():
    tags = releases.Tags("everyday-tech", "institution", "recognition", test="sp-hook_motion", arm="b")
    assert (tags.test, tags.arm) == ("sp-hook_motion", "b")


def test_tags_take_the_speakers_test_on_either_arm():
    for arm in releases.ARMS:
        tags = releases.Tags("job-hunting", "institution", "recognition", test="sp-speakers", arm=arm)
        assert (tags.test, tags.arm) == ("sp-speakers", arm)
    with pytest.raises(releases.ReleaseError, match="arm"):
        releases.Tags("job-hunting", "institution", "recognition", test="sp-speakers", arm="c")


@pytest.mark.parametrize(
    ("kw", "match"),
    [
        (dict(territory="work"), "territory"),
        (dict(cause="fate"), "cause"),
        (dict(emotion="joy"), "emotion"),
        (dict(recurring=["gary"]), "recurring"),
        (dict(recurring=("Gary",)), "recurring"),
        (dict(recurring=("gary", "gary")), "recurring"),
        (dict(test="opening"), "arm"),
        (dict(arm="a"), "test"),
        (dict(test="caption", arm="a"), "test"),
        (dict(test="opening", arm="c"), "arm"),
    ],
)
def test_tags_refuse_a_value_outside_their_closed_sets(kw, match):
    base = dict(territory="family", cause="protagonist", emotion="embarrassment")
    with pytest.raises(ReleaseError, match=match):
        releases.Tags(**(base | kw))


def test_a_release_refuses_tags_of_the_wrong_type():
    with pytest.raises(ReleaseError, match="tags"):
        Release("the-family-photo", POST, tags={"territory": "family"})


def test_a_release_pins_the_character_versions_it_draws():
    assert Release("a-b", POST).parts is None  # a reel being written has no pins yet
    pinned = Release("a-b", POST, parts={"toon-fox": 2, "toon-bear": 1})
    assert pinned.parts == {"toon-fox": 2, "toon-bear": 1}
    assert Release("a-b", POST, parts={}).parts == {}  # it draws no character


@pytest.mark.parametrize(
    ("pins", "match"),
    [
        ({"nobody": 1}, "a-b: no part 'nobody'"),
        ({"toon-fox": 3}, "a-b: toon-fox has no version 3; it has 1, 2"),
        ({"toon-fox": True}, "a-b: toon-fox's pin True is not a version number"),
        ({"toon-fox": "2"}, "a-b: toon-fox's pin '2' is not a version number"),
        (["toon-fox"], "a-b: parts maps a part to its version"),
    ],
)
def test_a_release_refuses_a_pin_that_is_not_a_version(pins, match):
    with pytest.raises(ReleaseError, match=match):
        Release("a-b", POST, parts=pins)


def test_a_release_refuses_to_pin_an_unapproved_version(monkeypatch):
    fox = parts.get("toon-fox")
    proposed = replace(fox.versions[-1], number=3, status="proposed", approval=None)
    table = {**parts.load(), "toon-fox": replace(fox, versions=(*fox.versions, proposed))}
    monkeypatch.setattr(parts, "load", lambda: table)
    with pytest.raises(ReleaseError, match="a-b: toon-fox version 3 is proposed"):
        Release("a-b", POST, parts={"toon-fox": 3})


def built(tmp_path: Path, drawn: dict[str, int] | None) -> Path:
    (tmp_path / "a-b").mkdir()
    if drawn is not None:
        parts.write_record(tmp_path / "a-b", drawn)
    return tmp_path


def test_a_release_without_pins_is_refused_whatever_it_draws(tmp_path):
    drift = releases.unpinned({"a-b": Release("a-b", POST)}, built(tmp_path, None))
    assert [(d.name, d.reason) for d in drift] == [
        ("a-b", "pins no part versions; add parts={...} with what it draws, {} if it draws none")
    ]


def test_the_refusal_gives_the_pin_a_built_reel_needs(tmp_path):
    drift = releases.unpinned({"a-b": Release("a-b", POST)}, built(tmp_path, {"toon-fox": 2, "toon-bear": 1}))
    assert [d.reason for d in drift] == ["pins no part versions; add parts={'toon-bear': 1, 'toon-fox': 2}"]


def test_a_pin_must_cover_what_the_build_drew(tmp_path):
    pinned = Release("a-b", POST, parts={"toon-bear": 1})
    drift = releases.unpinned({"a-b": pinned}, built(tmp_path, {"toon-bear": 1, "toon-fox": 2}))
    assert [d.reason for d in drift] == ["its build drew toon-fox version 2, which it does not pin"]


def test_a_build_of_another_version_than_the_pin_is_refused(tmp_path):
    pinned = Release("a-b", POST, parts={"toon-fox": 1})
    drift = releases.unpinned({"a-b": pinned}, built(tmp_path, {"toon-fox": 2}))
    assert [d.reason for d in drift] == ["its build drew toon-fox version 2 but it pins version 1; rebuild it"]


def test_a_release_named_by_its_video_is_reported_by_its_video(tmp_path):
    release = Release("a-b", POST, video="Other_Name")
    assert [d.name for d in releases.unpinned({"a-b": release}, built(tmp_path, None))] == ["Other_Name"]


def test_pins_that_match_the_build_or_a_project_with_no_record_pass(tmp_path):
    pinned = Release("a-b", POST, parts={"toon-fox": 2, "toon-bear": 1})
    assert releases.unpinned({"a-b": pinned}, built(tmp_path, {"toon-fox": 2})) == []
    assert releases.unpinned({"c-d": Release("c-d", POST, parts={})}, tmp_path) == []


def test_a_record_that_cannot_be_read_is_reported_not_passed(tmp_path):
    root = built(tmp_path, None)
    (root / "a-b" / parts.RECORD).write_text("not json")
    drift = releases.unpinned({"a-b": Release("a-b", POST, parts={})}, root)
    assert len(drift) == 1 and "parts.json" in drift[0].reason


def test_a_published_project_with_no_record_passes_while_it_is_not_being_delivered(tmp_path):
    assert releases.unpinned({"a-b": Release("a-b", POST, parts={})}, built(tmp_path, None)) == []


def test_a_release_being_delivered_needs_the_record_of_its_build(tmp_path):
    pinned = Release("a-b", POST, video="Other_Name", parts={"toon-fox": 2})
    drift = releases.unpinned({"a-b": pinned}, built(tmp_path, None), delivering={"Other_Name"})
    assert [d.name for d in drift] == ["Other_Name"] and "srstudio build" in drift[0].reason
    parts.write_record(tmp_path / "a-b", {"toon-fox": 2})
    assert releases.unpinned({"a-b": pinned}, tmp_path, delivering={"Other_Name"}) == []


def test_a_reel_carries_the_recipient_test_beside_the_first_second_test():
    plain = releases.Tags("family", "other-person", "recognition", test="sp-hook_motion", arm="a", recipient="a")
    written = releases.Tags(
        "family", "other-person", "recognition", test="sp-hook_motion", arm="b", recipient="b", to="best friend"
    )
    assert (plain.recipient, plain.to) == ("a", "")
    assert (written.recipient, written.to) == ("b", "best friend")


@pytest.mark.parametrize(
    ("kw", "match"),
    [
        ({"test": "sp-hook_motion", "arm": "a", "recipient": "c"}, "recipient"),
        ({"recipient": "a"}, "first-second"),
        ({"test": "sp-hook_motion", "arm": "a", "recipient": "b"}, "names who"),
        ({"test": "sp-hook_motion", "arm": "a", "recipient": "a", "to": "family"}, "names who"),
        ({"test": "sp-hook_motion", "arm": "a", "to": "family"}, "names who"),
        ({"test": "sp-hook_motion", "arm": "a", "recipient": "b", "to": "sister"}, "to 'sister'"),
    ],
)
def test_the_recipient_test_is_refused_when_incomplete(kw, match):
    with pytest.raises(releases.ReleaseError, match=match):
        releases.Tags("family", "other-person", "recognition", **kw)


def test_a_delivery_is_told_which_captions_print_over_each_other(tmp_path):
    release = Release("a-b", POST)
    project = tmp_path / "a-b"
    project.mkdir()
    (project / "a-b.scene.xml").write_text(
        '<scene><layer id="x-caption" start="1" end="2.2" y="9"/>'
        '<layer id="y-caption" start="2" end="3" y="9"/></scene>'
    )
    drift = releases.doubled_captions({"a-b": release}, tmp_path, {"a-b"})
    assert [(d.name, d.reason) for d in drift] == [("a-b", "x-caption and y-caption share the band for 0.20 s")]


def test_a_published_video_is_not_read_for_doubled_captions(tmp_path):
    assert releases.doubled_captions({"a-b": Release("a-b", POST)}, tmp_path, {"a-b"}) == []
    project = tmp_path / "a-b"
    project.mkdir()
    (project / "a-b.scene.xml").write_text("<scene")
    assert releases.doubled_captions({"a-b": Release("a-b", POST)}, tmp_path, ()) == []
