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
PRINT_FONT = "fredoka-600.ttf"


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
        cs.render_one(cs.Plan(entry, document, 1.0, "k", False), real, tmp_path, tmp_path)


def plated_plan(name: str = "rafa-mug") -> cs.Plan:
    return cs.Plan(registry.get("prop", name), b'<scene><project width="4" height="4"/></scene>', 1.0, "k", False)


def projects_with(tmp_path: Path, font: bytes) -> Path:
    assets = tmp_path / "episodes" / "a-project" / "assets"
    assets.mkdir(parents=True)
    (assets / PRINT_FONT).write_bytes(font)
    return tmp_path / "episodes"


def only_rafa_mug(monkeypatch) -> None:
    monkeypatch.setattr(cs, "plan", lambda episodes, work: ([plated_plan()], {}))
    monkeypatch.setattr(cs.shutil, "which", lambda tool: f"/fake/{tool}")


def test_a_build_prints_plates_in_the_font_of_its_projects_with_no_fonts_variable(tmp_path, monkeypatch):
    """The catalog's service has no SRSTUDIO_FONTS, and runs from a folder that holds no font."""
    monkeypatch.delenv("SRSTUDIO_FONTS", raising=False)
    monkeypatch.chdir(tmp_path)
    (tmp_path / "engine").write_bytes(b"engine")
    episodes = projects_with(tmp_path, b"the font's bytes")
    only_rafa_mug(monkeypatch)
    seen: list[bytes] = []

    def render(plate, *, engine, cache, fonts):
        seen.append((fonts / PRINT_FONT).read_bytes())
        raise cs.plates.PlateError("the plate stops here")

    monkeypatch.setattr(cs.plates, "render", render)
    with pytest.raises(cs.SpecimenRenderError, match="the plate stops here"):
        cs.render_all(tmp_path / "engine", tmp_path / "cache", episodes)
    assert seen == [b"the font's bytes"]


def test_a_build_whose_projects_hold_no_print_font_says_so_before_any_render(tmp_path, monkeypatch):
    (tmp_path / "episodes").mkdir()
    (tmp_path / "engine").write_bytes(b"engine")
    only_rafa_mug(monkeypatch)
    monkeypatch.setattr(cs, "render_one", lambda *a: pytest.fail("rendered without its font"))
    with pytest.raises(cs.SpecimenRenderError, match=r"no project in .*episodes holds assets/fredoka-600\.ttf"):
        cs.render_all(tmp_path / "engine", tmp_path / "cache", tmp_path / "episodes")


def test_every_failed_specimen_is_named_once_and_all_of_them_fail_the_build(tmp_path, monkeypatch):
    (tmp_path / "engine").write_bytes(b"engine")
    episodes = projects_with(tmp_path, b"font")
    named, bare = plated_plan("rafa-mug"), plated_plan("rafa-phone")
    monkeypatch.setattr(cs, "plan", lambda e, w: ([named, replace(bare, key="other")], {}))
    monkeypatch.setattr(cs.shutil, "which", lambda tool: f"/fake/{tool}")

    def render_one(plan_, engine, folder, fonts):
        if plan_.entry.name == named.entry.name:
            raise cs.SpecimenRenderError("rafa-mug: the recipe drew nothing at 1 s")
        raise FileNotFoundError(2, "No such file or directory", "some-file")

    monkeypatch.setattr(cs, "render_one", render_one)
    with pytest.raises(cs.SpecimenRenderError) as failure:
        cs.render_all(tmp_path / "engine", tmp_path / "cache", episodes)
    assert str(failure.value).splitlines() == [
        "2 specimens failed:",
        "rafa-mug: the recipe drew nothing at 1 s",
        "rafa-phone: [Errno 2] No such file or directory: 'some-file'",
    ]


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


def test_a_poster_comes_from_the_spec_once_and_leaves_the_package_alone(tmp_path, monkeypatch):
    scene = package(tmp_path / "packages")
    before = sorted(p.name for p in scene.parent.iterdir())
    made = cs.poster(tmp_path / "packages", "wifi", engine(), tmp_path / "cache")
    assert made.suffix == ".jpg" and made.stat().st_size > 0
    assert sorted(p.name for p in scene.parent.iterdir()) == before
    assert [p.name for p in made.parent.iterdir()] == [made.name]  # no frame left beside it
    mtime = made.stat().st_mtime_ns
    with monkeypatch.context() as patch:
        patch.setattr(cs.subprocess, 'run', lambda *args, **kwargs: pytest.fail('warm poster invoked a process'))
        assert cs.poster(tmp_path / "packages", "wifi", engine(), tmp_path / "cache") == made
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


@pytest.mark.parametrize("name", ["rafa", "pedro"])
def test_a_character_on_plates_repeats_no_id_and_still_draws_what_was_approved(name):
    """Rafa's social-battery face is the same plate at mouth rest and closed: one picture, one asset, two layers."""
    document = specimens.SPECIMENS[name](registry.get("character", name)).scene.to_bytes()
    ids = [node.get("id") for node in ET.fromstring(document).iter() if node.get("id")]
    assert len(ids) == len(set(ids))
    assert specimens.fingerprint(document) == parts.get(name).version(1).drawing


def opacity_at(node: ET.Element, second: float) -> float:
    """A node's opacity at ``second``: stepped when its track holds, and between its keys when it fades."""
    value = float(node.get("opacity", "1"))
    for track in node.findall("animate"):
        if track.get("property") == "opacity":
            keys = [(float(key.get("time", "0")), float(key.get("value", "1"))) for key in track.findall("key")]
            stepped = track.get("defaultInterpolation") == "hold"
            held = next((value for time, value in reversed(keys) if time <= second), keys[0][1])
            value = held if stepped else float(np.interp(second, *zip(*keys, strict=True)))
    return value


def something_shows(node: ET.Element, second: float) -> bool:
    """Whether a drawn node under ``node`` is on at ``second``: inside its span and not gated off."""
    if node.tag in ("animate", "expression") or second < float(node.get("start", "0")):
        return False
    if ("end" in node.attrib and second >= float(node.attrib["end"])) or opacity_at(node, second) <= 0:
        return False
    return node.tag not in ("group", "composition") or any(something_shows(child, second) for child in node)


def shown_at(document: bytes, second: float) -> bool:
    composition = ET.fromstring(document).find("composition")
    assert composition is not None
    return something_shows(composition, second)


def drawn_by_itself(name: str, tmp_path: Path, monkeypatch) -> cs.Plan:
    """A part that needs no font and no project, as a build plans it."""
    monkeypatch.setattr(cs, "font_of", lambda style, episodes: None)
    entry = next(e for e in registry.entries() if e.name == name)
    recipe = cs.recipe_of(entry)
    built = cs.document(entry, recipe, None, tmp_path, tmp_path)
    return cs.Plan(entry, built, recipe.at, cs.key(entry, cs.drawing_of(entry, built), recipe.at), False)


@pytest.mark.parametrize("name", ["collage-eye-twitch", "location-chip", "map-far-side"])
def test_a_part_that_is_on_for_a_moment_is_shown_in_that_moment_and_keeps_its_digest(name, tmp_path, monkeypatch):
    """The engine draws nothing for these at the default second, which fails the whole build."""
    plan_ = drawn_by_itself(name, tmp_path, monkeypatch)
    assert shown_at(plan_.document, plan_.at)
    assert specimens.fingerprint(plan_.document) == parts.get(name).version(1).drawing


def test_the_reader_of_a_document_sees_a_gate_a_span_and_its_end():
    document = b"""<scene><composition>
      <group id="a"><animate property="opacity" defaultInterpolation="hold">
        <key time="0" value="0"/><key time="1" value="1"/><key time="2" value="0"/></animate><shape id="s"/></group>
      <group id="b" start="3" end="4"><shape id="t"/></group>
    </composition></scene>"""
    assert [shown_at(document, second) for second in (0.5, 1.5, 2.5, 3.5, 4.0)] == [False, True, False, True, False]


@needs_projects
def test_every_part_is_on_at_the_second_its_specimen_shows(planned):
    """A dark moment is a failed build, and the engine is the only other thing that would say so."""
    assert [p.entry.name for p in planned.values() if not shown_at(p.document, p.at)] == []


def test_the_splash_is_shown_while_its_beads_are_in_the_air():
    # a bead flies for 0.32 s at the least: the recipe's default second shows an empty frame, which a render refuses
    assert cs.RECIPES["water-splash"].at < 0.32
