"""``srstudio.catalog_specimens``: each registered part alone, through its real builder and the real engine."""

import inspect
import os
import shutil
import xml.etree.ElementTree as ET
from dataclasses import replace
from pathlib import Path

import numpy as np
import pytest

from srstudio import catalog_specimens as cs
from srstudio import parts, registry, specimens, usage
from srstudio.specimens import DrawingChangedError
from srstudio.styles import STYLES

specimens.load_parts()
EPISODES = Path(os.environ.get("SRSTUDIO_EPISODES", "generated/episodes"))
needs_projects = pytest.mark.skipif(not EPISODES.is_dir(), reason="needs SRSTUDIO_EPISODES")


def engine() -> Path:
    found = os.environ.get("SRSTUDIO_ENGINE") or shutil.which("scene-render")
    if not found or not Path(found).exists() or not shutil.which("ffmpeg"):
        pytest.skip("needs SRSTUDIO_ENGINE and ffmpeg")
    return Path(found).resolve()


NAMES = {e.name for e in registry.entries()}


def test_every_registered_part_has_a_recipe_or_a_typed_refusal_and_never_both():
    assert {e.name for e in registry.entries() if e.name not in cs.REFUSED and not cs.drawn_by_some_recipe(e)} == set()
    assert not (set(cs.RECIPES) - NAMES) and not (set(cs.REFUSED) - NAMES)
    assert not set(cs.RECIPES) & set(cs.REFUSED)
    assert all(isinstance(r, cs.Refused) and isinstance(r.reason, cs.Reason) and r.detail for r in cs.REFUSED.values())


def test_characters_have_no_recipe_here_they_are_drawn_by_the_versions_module():
    assert not {e.name for e in registry.entries("character")} & set(cs.RECIPES)
    assert not ({e.name for e in registry.entries("character")} - set(cs.REFUSED) - set(specimens.SPECIMENS))


def test_a_part_with_neither_stops_the_plan(tmp_path, monkeypatch):
    monkeypatch.setattr(cs, "REFUSED", {})
    monkeypatch.setattr(cs, "RECIPES", {})
    with pytest.raises(cs.SpecimenRenderError, match="no specimen recipe and no typed refusal"):
        cs.plan(tmp_path, tmp_path)


@needs_projects
@pytest.mark.parametrize("name", sorted(e.name for e in registry.entries("location") if e.name not in cs.REFUSED))
def test_a_set_has_nobody_in_it(name, tmp_path):
    entry = registry.get("location", name)
    with usage.trace() as used:
        cs.document(entry, cs.recipe_of(entry), cs.font_of(cs.style_of(entry), EPISODES), EPISODES, tmp_path)
    assert not used & ({e.name for e in registry.entries("character")} | {"candidate-back"})


def test_a_new_part_that_needs_only_a_place_and_a_clock_needs_no_entry():
    def bare(cv, g, x, y, *, end, tint="#fff"): ...
    def own_data(cv, g, label): ...

    assert cs.auto(registry.Entry("prop", "bare", bare)) is not None
    assert cs.auto(registry.Entry("prop", "own-data", own_data)) is None


# Approved at the stage's corner: its drawing is immutable, and a new recipe would change what was approved.
AT_THE_CORNER = {"soft-phone"}


def test_a_part_with_no_recipe_of_its_own_is_not_left_at_the_stages_corner():
    """``auto`` fills only what a builder demands, so a builder that defaults ``x`` and ``y`` to 0 draws its card
    clipped at the top left, and only someone looking at the catalog sees it."""
    cornered = set()
    for entry in registry.entries():
        place = inspect.signature(entry.builder).parameters
        if entry.kind != "character" and entry.name not in cs.RECIPES and cs.auto(entry) is not None:
            if any(name in place and place[name].default == 0 for name in ("x", "y")):
                cornered.add(entry.name)
    assert cornered == AT_THE_CORNER


def test_bounds_finds_what_differs_from_the_background():
    grey = (231, 228, 221)
    frame = np.full((100, 80, 3), grey, np.uint8)
    assert cs.bounds(frame, grey) is None
    frame[20:40, 10:30] = (0, 0, 0)
    assert cs.bounds(frame, grey) == (10, 20, 30, 40)
    frame[20:40, 10:30] = (grey[0] + 5, grey[1], grey[2])  # noise under the threshold is not drawing
    assert cs.bounds(frame, grey) is None
    frame[50:54, 40:44] = (0, 0, 0)  # a crumb is a drawing, and one stray pixel is not
    assert cs.bounds(frame, grey) == (40, 50, 44, 54)
    frame[50:54, 40:44] = grey
    frame[50, 40] = (0, 0, 0)
    assert cs.bounds(frame, grey) is None


def test_framed_moves_the_whole_composition_and_sets_the_background():
    doc = b'<scene><project background="#fff"/><composition><group id="a"/><shape id="b"/></composition></scene>'
    root = ET.fromstring(cs.framed(doc, background="#123456", x=10, y=20, scale=2))
    assert root.find("project").get("background") == "#123456"
    (group,) = root.find("composition")
    assert (group.get("x"), group.get("y"), group.get("scaleX"), group.get("scaleY")) == ("10", "20", "2", "2")
    assert [c.get("id") for c in group] == ["a", "b"]
    with pytest.raises(cs.SpecimenRenderError, match="cannot be framed"):
        cs.framed(b"<scene/>")


def test_a_key_follows_the_drawing_and_not_the_ids_of_a_character():
    entry = registry.get("character", "pip")
    doc = specimens.SPECIMENS["pip"](entry).scene.to_bytes()
    renamed = doc.replace(b'id="pip', b'id="other')
    assert cs.key(entry, cs.drawing_of(entry, doc), 0.0) == cs.key(entry, cs.drawing_of(entry, renamed), 0.0)
    moved = doc.replace(b'x="540"', b'x="541"', 1)
    assert moved != doc and cs.key(entry, cs.drawing_of(entry, moved), 0.0) != cs.key(
        entry, cs.drawing_of(entry, doc), 0.0
    )


def test_a_key_changes_with_the_moment_shown():
    entry = registry.get("prop", "coffee-cup")
    assert cs.key(entry, "drawing", 0.0) != cs.key(entry, "drawing", 1.0)


@needs_projects
def test_a_rendered_part_is_not_rendered_again_and_a_drawn_part_fills_the_image(tmp_path, monkeypatch):
    real = engine()
    only = {"coffee-cup", "park", "pip", "captions"}
    every = registry.entries()
    monkeypatch.setattr(cs.registry, "entries", lambda *a: [e for e in every if e.name in only])
    shelf = cs.render_all(real, tmp_path, EPISODES)
    done, refused = shelf.done, shelf.refused
    assert shelf.made == 3  # the captions are refused
    assert set(done) == {"coffee-cup", "park", "pip"} and set(refused) == {"captions"}
    assert refused["captions"].reason is cs.Reason.OVERLAY
    side = cs.SIZE
    assert (done["coffee-cup"].width, done["coffee-cup"].height) == (side, side)
    pixels = cs.pixels_of(done["coffee-cup"].png, side, side)
    x0, y0, x1, y1 = cs.bounds(pixels, cs.rgb(cs.BACKGROUND))
    assert max(x1 - x0, y1 - y0) > side * 0.8  # the cup fills the frame, not 64 px in the middle of it
    assert done["park"].height == round(side * STYLES["cutout"].height / STYLES["cutout"].width / 2) * 2
    first = done["pip"].png.stat().st_mtime_ns
    monkeypatch.setattr(cs, "render_one", lambda *a: pytest.fail("rendered again"))
    again = cs.render_all(real, tmp_path, EPISODES)
    assert again.made == 0 and again.done["pip"].png.stat().st_mtime_ns == first


@needs_projects
def test_a_recipe_that_draws_nothing_is_an_error_not_an_empty_card(tmp_path, monkeypatch):
    real = engine()
    entry = registry.get("prop", "coffee-cup")
    nothing = cs.Recipe(lambda cv, g, e, ctx: None)
    work = tmp_path / "work" / "cutout"
    document = cs.document(entry, nothing, cs.font_of(cs.style_of(entry), EPISODES), EPISODES, work)
    with pytest.raises(cs.SpecimenRenderError, match="drew nothing"):
        cs.render_one(cs.Plan(entry, document, 1.0, "k", False), real, tmp_path)


# -- package posters --------------------------------------------------------------------------------------
PACKAGE = """<?xml version="1.0" encoding="UTF-8"?>
<scene version="1.1">
  <project width="108" height="192" fps="10" duration="2" background="#336699"/>
  <composition/>
</scene>
"""


def package(root: Path, slug: str = "wifi", version: str = "1.0.0", scene: str = "scene.xml") -> Path:
    project = root / f"{slug}-{version}" / "project"
    project.mkdir(parents=True)
    (project / scene).write_text(PACKAGE)
    return project / scene


def test_the_scene_of_a_package_is_its_newest_version_under_either_name(tmp_path):
    package(tmp_path, version="1.9.0")
    newest = package(tmp_path, version="1.10.0", scene="wifi.scene.xml")
    package(tmp_path, "wifi-plus", "9.0.0")
    assert cs.scene_of(tmp_path, "wifi") == newest


def test_a_package_with_no_scene_is_named(tmp_path):
    with pytest.raises(cs.SpecimenRenderError, match="no wifi-<version>"):
        cs.scene_of(tmp_path, "wifi")
    (tmp_path / "wifi-1.0.0" / "project").mkdir(parents=True)
    with pytest.raises(cs.SpecimenRenderError, match="no scene"):
        cs.scene_of(tmp_path, "wifi")


@pytest.mark.parametrize("text", ["<scene", "<scene/>", '<scene><project duration="0"/></scene>'])
def test_a_scene_with_no_length_is_refused_before_the_engine(tmp_path, text):
    package(tmp_path).write_text(text)
    with pytest.raises(cs.SpecimenRenderError, match="wifi"):
        cs.poster(tmp_path, "wifi", tmp_path / "no-engine", tmp_path / "cache")


def test_a_poster_comes_from_the_spec_once_and_leaves_the_package_alone(tmp_path):
    scene = package(tmp_path / "packages")
    before = sorted(p.name for p in scene.parent.iterdir())
    made = cs.poster(tmp_path / "packages", "wifi", engine(), tmp_path / "cache")
    assert made.suffix == ".jpg" and made.stat().st_size > 0
    assert sorted(p.name for p in scene.parent.iterdir()) == before
    assert [p.name for p in made.parent.iterdir()] == [made.name]  # no frame left beside it
    mtime = made.stat().st_mtime_ns
    assert cs.poster(tmp_path / "packages", "wifi", tmp_path / "no-engine", tmp_path / "cache") == made  # cached
    assert made.stat().st_mtime_ns == mtime
    scene.write_text(PACKAGE.replace("#336699", "#993366"))
    assert cs.poster(tmp_path / "packages", "wifi", engine(), tmp_path / "cache") != made  # a new spec is a new poster


def test_an_engine_failure_names_the_package(tmp_path):
    package(tmp_path)
    fails = tmp_path / "engine"
    fails.write_text("#!/bin/sh\necho nope\nexit 1\n")
    fails.chmod(0o700)
    with pytest.raises(cs.SpecimenRenderError, match="wifi.*nope"):
        cs.poster(tmp_path, "wifi", fails, tmp_path / "cache")


OTHERS = [
    n
    for n, p in parts.load().items()
    if p.kind != "character" and not p.refused and p.versions[-1].status == "approved"
]


@pytest.fixture(scope="module")
def planned(tmp_path_factory) -> dict[str, cs.Plan]:
    plans, _ = cs.plan(EPISODES, tmp_path_factory.mktemp("work"))
    return {p.entry.name: p for p in plans}


@needs_projects
@pytest.mark.parametrize("name", OTHERS)
def test_an_approved_part_of_any_kind_still_draws_what_was_approved(name, planned):
    cs.check(planned[name])


@needs_projects
def test_a_changed_part_fails_and_says_to_add_a_version(planned):
    plan_ = planned["coffee-cup"]
    changed = replace(plan_, document=plan_.document.replace(b'fill="#', b'fill="#1', 1))
    with pytest.raises(DrawingChangedError, match="coffee-cup version 1 is approved.*add a version"):
        cs.check(changed)


@needs_projects
def test_the_digest_of_a_part_is_what_its_record_holds():
    assert cs.digest("coffee-cup", 1, EPISODES) == parts.get("coffee-cup").version(1).drawing
    assert cs.digest("toon-fox", 2, EPISODES) == parts.get("toon-fox").version(2).drawing


def test_a_refused_part_has_no_digest_to_ask_for():
    with pytest.raises(cs.SpecimenRenderError, match=r"captions is refused \(overlay\)"):
        cs.digest("captions", 1, EPISODES)


def test_the_splash_is_shown_while_its_beads_are_in_the_air():
    # a bead flies for 0.32 s at the least: the recipe's default second shows an empty frame, which a render refuses
    assert cs.RECIPES["water-splash"].at < 0.32
