"""Releases: one file per published episode declares its post, its video name and whether its cover is drawn from
the scene's cover variant; :func:`srstudio.releases.load` finds them, and :func:`srstudio.releases.items` refuses a
declaration that disagrees with the built scene."""

import textwrap
from pathlib import Path

import pytest

from srstudio import releases
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
