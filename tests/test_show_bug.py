"""The show bug: drawn by a numbered build, above the camera, and nowhere else (ADR 0074)."""

import json
import os
import shutil
import textwrap
import xml.etree.ElementTree as ET
from pathlib import Path

import pytest

from srstudio import cli, framegraph, parts, registry, show
from srstudio.episode import Episode, EpisodeSpec
from srstudio.styles import CEL

ENGINE = os.environ.get("SRSTUDIO_ENGINE") or shutil.which("scene-render")


@pytest.fixture
def spec(tmp_path):
    (tmp_path / "script.json").write_text(json.dumps([{"start": 0, "end": 1, "text": "hi"}]))
    return EpisodeSpec(slug="num", title="num", description="num", root=tmp_path, seed=1, style=CEL, signature=False)


def build(spec, number=None) -> bytes:
    ep = Episode(spec)
    ep.cv.rect(ep.comp, 0, 0, 10, 10, fill="#000000")
    with show.stamping(number):
        return ep.finish().read_bytes()


def children(document: bytes) -> list[str]:
    composition = ET.fromstring(document).find(".//composition")
    return [c.get("id") or "" for c in composition]


def test_a_numbered_build_draws_the_bug_last_so_nothing_stands_in_front_of_it(spec):
    assert children(build(spec, 212))[-1] == "show-bug-212"


def test_a_build_with_no_number_is_the_document_it_was(spec):
    plain = Episode(spec)
    plain.cv.rect(plain.comp, 0, 0, 10, 10, fill="#000000")
    assert build(spec) == plain.finish().read_bytes()


def test_the_bug_hides_on_the_cover_which_says_the_number_on_its_band(spec):
    root = ET.fromstring(build(spec, 7))
    rules = [
        (o.get("target"), o.get("property"), o.get("value")) for o in root.findall(".//variant[@id='cover']/override")
    ]
    assert rules == [("show-bug-7", "visible", "false")]


def test_finishing_twice_draws_one_bug(spec):
    ep = Episode(spec)
    with show.stamping(9):
        ep.finish()
        document = ep.finish().read_bytes()
    assert children(document).count("show-bug-9") == 1


def test_the_number_stops_at_the_end_of_the_block():
    with show.stamping(3):
        assert show.active() == 3
    assert show.active() is None


@pytest.mark.parametrize("number", [0, -1, 1.5, True])
def test_the_bug_refuses_a_number_that_is_not_one(spec, number):
    ep = Episode(spec)
    with pytest.raises(show.ShowError):
        show.bug(ep.cv, ep.comp, number)


def test_each_number_draws_its_own_digits(spec):
    ep = Episode(spec)
    show.bug(ep.cv, ep.comp, 12)
    show.bug(ep.cv, ep.comp, 13)
    paths = [
        p.get("path")
        for g in ET.fromstring(ep.scene.to_bytes()).iter("group")
        if g.get("id", "").endswith("-n-2")
        for p in g
    ]
    assert len(paths) == 2 and paths[0] != paths[1]


def test_the_bug_needs_no_font_and_adds_no_text_layer(spec):
    assert not ET.fromstring(build(spec, 212)).findall(".//layer")


def test_the_bug_is_a_shared_part_waiting_for_its_approval():
    assert registry.get("graphic", "show-bug").style == ""
    version = parts.get("show-bug").versions[-1]
    assert version.status == "proposed" and version.approval is None
    with pytest.raises(parts.NotApprovedError):
        parts.pin("show-bug", 1)


@pytest.mark.parametrize("number", [1, 212, 1000, 99999])
@pytest.mark.skipif(ENGINE is None, reason="needs the engine")
def test_every_point_of_the_bug_stays_inside_its_box(spec, number):
    build(spec, number)
    scene = Path(spec.root) / "num.scene.xml"
    document = scene.read_bytes()
    shown = next(iter(framegraph.evaluate(ENGINE, scene, [0.0])))
    index = next(i for i, n in enumerate(shown.nodes) if n.id == show.bug_id(number))
    box = shown.box(index, framegraph.drawings(document))
    left, top, right, bottom = show.BUG_BOX
    assert box is not None
    assert left <= box.left and top <= box.top and box.right <= right and box.bottom <= bottom


def test_a_build_by_slug_stamps_a_show_release_and_only_it(tmp_path, monkeypatch):
    scripts = tmp_path / "episodes"
    (scripts / "posts").mkdir(parents=True)
    (scripts / "posts" / "__init__.py").write_text("")
    release = """
        from srstudio.releases import Release
        from srstudio.social import InstagramPost
        from srstudio.thumbnail import {kind}
        POST = InstagramPost("Is this fine?", "Words.", thumbnail={kind}("GOOD", 1.0{more}))
        RELEASE = Release("{slug}", POST, cover={cover})
    """
    script = """
        from pathlib import Path
        import sys
        from srstudio.episode import Episode, EpisodeSpec
        from srstudio.styles import CEL
        root = Path(sys.argv[1])
        spec = EpisodeSpec(slug="{slug}", title="t", description="d", root=root, seed=1, style=CEL, signature=False)
        Episode(spec).finish()
    """
    for slug, kind, more, cover in (("shown", "ShowCover", ", number=212", True), ("plain", "Thumbnail", "", False)):
        (scripts / "posts" / f"{slug}.py").write_text(
            textwrap.dedent(release.format(slug=slug, kind=kind, more=more, cover=cover))
        )
        (scripts / f"{slug}.py").write_text(textwrap.dedent(script.format(slug=slug)))
    monkeypatch.syspath_prepend(str(tmp_path))
    for slug, count in (("shown", 1), ("plain", 0)):
        root = tmp_path / slug
        root.mkdir()
        (root / "script.json").write_text(json.dumps([{"start": 0, "end": 1, "text": "hi"}]))
        assert cli.main(["build", "--scripts", str(scripts), slug, str(root)]) == 0
        assert (root / f"{slug}.scene.xml").read_text().count('id="show-bug-212"') == count
