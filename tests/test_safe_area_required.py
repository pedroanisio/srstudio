"""Every scene declares its safe area (ADR 0218). arc4d3, Slack 1793678456.387679: "Every scene declares its safe area,
not only multi-character dances, and the overlay check refuses a scene without one."

Three places hold it: an episode built by the library declares the style's safe area unless it names its own; the
overlay check refuses a document with none, with a typed error; and a reel's first delivery is refused when its scene
declares none. A published reel built without one is frozen as it went out, so it stays on a closed list."""

from __future__ import annotations

import ast
import dataclasses
import io
import re
import zipfile
from pathlib import Path

import pytest

from srstudio import (
    INK,
    STICK,
    TOON,
    Episode,
    EpisodeSpec,
    collage_sketch,
    layout,
    safe_area_gate,
    safe_areas,
    series,
    stick_reel,
    styles,
    toon_sketch,
)
from srstudio.episode import FROM_STYLE
from srstudio.layout import SQUARE, VERTICAL, LayoutError, UndeclaredSafeAreaError, check_overlays
from srstudio.releases import Release
from srstudio.social import Drift, InstagramPost
from srstudio.thumbnail import Thumbnail

REPO = Path(__file__).resolve().parent.parent
SA = re.compile(rb"<project[^>]*\ssafeArea=")
DECLARES = re.compile(r"\b(VERTICAL|SQUARE|safe_area)\.declare\(")


def spec(root: Path, slug: str = "t-new-reel", **kw) -> EpisodeSpec:
    """A spec on the sample project, whatever the style: it reads the sample's dialogue and mix."""
    kw = {"dialogue": "dialogue.json", "audio": "assets/dialogue.wav", **kw}
    return EpisodeSpec(slug=slug, title="t", description="t", root=root, seed=1, signature=False, **kw)


# -- the overlay check ---------------------------------------------------------------------------------------------
def test_the_overlay_check_refuses_a_scene_with_no_safe_area_with_a_typed_error(tmp_path):
    doc = tmp_path / "plain.scene.xml"
    doc.write_text('<scene><project width="100" height="100" fps="10" duration="0.2"/></scene>')
    with pytest.raises(UndeclaredSafeAreaError, match="declares no safe area"):
        check_overlays(doc, ["mark"], engine=tmp_path / "unused")  # refused before any engine is asked


def test_an_undeclared_safe_area_is_a_layout_error_so_existing_handlers_still_catch_it():
    assert issubclass(UndeclaredSafeAreaError, LayoutError)


def test_a_safe_area_that_names_no_declared_element_is_still_a_layout_error_and_not_the_undeclared_one(tmp_path):
    doc = tmp_path / "dangling.scene.xml"
    doc.write_text('<scene><project safeArea="gone" width="10" height="10" fps="10" duration="1"/></scene>')
    with pytest.raises(LayoutError, match="no <safeArea") as caught:
        check_overlays(doc, ["mark"], engine=tmp_path / "unused")
    assert not isinstance(caught.value, UndeclaredSafeAreaError)


def test_declared_safe_area_reads_the_area_a_document_declares(tmp_path, project):
    ep = Episode(spec(project))
    ep.captions()
    out = ep.finish(tmp_path / "t.scene.xml", strict=False)
    assert layout.declared_safe_area(out.read_bytes()) == VERTICAL


def test_declared_safe_area_refuses_a_document_with_none_and_one_that_is_not_xml():
    with pytest.raises(UndeclaredSafeAreaError):
        layout.declared_safe_area(b'<scene><project width="10" height="10" fps="10" duration="1"/></scene>')
    with pytest.raises(LayoutError, match="not a scene document"):
        layout.declared_safe_area(b"<scene")


# -- the library's builders declare one ----------------------------------------------------------------------------
@pytest.mark.parametrize("style", sorted(styles.STYLES.values(), key=lambda s: s.slug), ids=lambda s: s.slug)
def test_every_style_has_a_safe_area_of_its_own_frame(style):
    expected = SQUARE if style.width == style.height else VERTICAL
    assert style.safe_area == expected


def test_the_square_area_is_title_safe():
    """SMPTE ST 2046-1 title-safe: the middle 90 % of each side."""
    assert (SQUARE.top, SQUARE.right, SQUARE.bottom, SQUARE.left) == (0.05, 0.05, 0.05, 0.05)
    assert SQUARE.enforce == "error"


@pytest.mark.parametrize("style", [TOON, STICK, INK], ids=lambda s: s.slug)
def test_a_new_episode_declares_its_styles_safe_area_unless_it_names_one(project, style):
    assert spec(project, style=style).safe_area == style.safe_area


def test_a_new_episode_writes_the_declaration_into_its_scene(project):
    ep = Episode(spec(project))
    assert ep.spec.safe_area == VERTICAL
    assert SA.search(ep.scene.to_bytes())


def test_an_episode_that_names_its_own_safe_area_keeps_it(project):
    own = layout.SafeArea("own", top=0.2, right=0.1, bottom=0.2, left=0.1)
    assert Episode(spec(project, safe_area=own)).spec.safe_area == own


def test_a_new_episode_that_declares_no_safe_area_is_refused_with_a_typed_error(project):
    with pytest.raises(UndeclaredSafeAreaError, match="t-new-reel"):
        spec(project, safe_area=None)


@pytest.mark.parametrize("given", [FROM_STYLE, None], ids=["default", "none"])
def test_a_published_reel_built_without_one_keeps_its_scene_as_it_went_out(project, given):
    slug = "the-report"
    assert slug in safe_areas.PUBLISHED_WITHOUT
    ep = Episode(spec(project, slug=slug, **({} if given is FROM_STYLE else {"safe_area": given})))
    assert ep.spec.safe_area is None
    assert not SA.search(ep.scene.to_bytes())


def test_a_published_reel_may_still_name_a_safe_area(project):
    assert Episode(spec(project, slug="the-report", safe_area=VERTICAL)).spec.safe_area == VERTICAL


def test_the_toon_staging_leaves_the_safe_area_to_the_style():
    field = {f.name: f for f in dataclasses.fields(toon_sketch.Staging)}["safe_area"]
    assert field.default is FROM_STYLE


def test_a_series_declares_the_vertical_area_by_default():
    field = {f.name: f for f in dataclasses.fields(series.Series)}["safe_area"]
    assert field.default == VERTICAL


def test_a_stick_reel_declares_the_stick_styles_area(tmp_path):
    made = stick_reel.spec(tmp_path, "t-stick", "", "t", "t", 1)
    assert made.safe_area == STICK.safe_area == VERTICAL


def _calls(path: Path, names: set[str]) -> list[ast.Call]:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    return [
        n
        for n in ast.walk(tree)
        if isinstance(n, ast.Call) and (getattr(n.func, "id", None) in names or getattr(n.func, "attr", None) in names)
    ]


def test_no_library_builder_passes_an_undeclared_safe_area():
    """A builder in the library cannot opt a reel out: only a published reel on the closed list is built without one."""
    found = []
    for path in sorted((REPO / "src" / "srstudio").glob("*.py")):
        for call in _calls(path, {"EpisodeSpec", "Staging", "Series"}):
            for kw in call.keywords:
                if kw.arg == "safe_area" and isinstance(kw.value, ast.Constant) and kw.value.value is None:
                    found.append(f"{path.name}:{call.lineno}")
    assert found == []


def test_collage_sketch_leaves_the_safe_area_to_the_style():
    calls = _calls(REPO / "src" / "srstudio" / "collage_sketch.py", {"EpisodeSpec"})
    assert calls and all("safe_area" not in {k.arg for k in c.keywords} for c in calls)
    assert collage_sketch.COLLAGE.safe_area == VERTICAL


# -- the closed lists ----------------------------------------------------------------------------------------------
def test_the_published_list_is_sorted_unique_slugs_and_closed():
    """The list closes at 164: every reel delivered before ADR 0218 whose scene declared none. It can only shrink."""
    listed = list(safe_areas.PUBLISHED_WITHOUT_ORDER)
    assert listed == sorted(set(listed))
    assert frozenset(listed) == safe_areas.PUBLISHED_WITHOUT
    assert all(re.fullmatch(r"[a-z0-9]+(-[a-z0-9]+)*", s) for s in listed)
    assert len(listed) == 164


def _scene_builders() -> set[str]:
    """Every file in the repository's code that writes a scene project itself instead of through Episode."""
    found = set()
    for top in ("src", "episodes", "examples", "tools"):
        for path in sorted((REPO / top).rglob("*.py")):
            if _calls(path, {"add_project"}):
                found.add(path.relative_to(REPO).as_posix())
    return found - {"src/srstudio/episode.py"}


def test_every_scene_written_outside_episode_declares_one_or_is_listed_as_never_delivered():
    builders = _scene_builders()
    listed = {u.path for u in safe_areas.UNDELIVERED}
    declaring = {p for p in builders if DECLARES.search((REPO / p).read_text(encoding="utf-8"))}
    assert builders - declaring == listed, "a scene builder outside Episode declares its safe area or is listed"
    assert not listed & declaring, "a listed builder that declares one is no longer an exemption"


def test_each_never_delivered_scene_says_what_it_is_and_why():
    kinds = set(safe_areas.UndeliveredKind.__args__)  # type: ignore[attr-defined]
    for u in safe_areas.UNDELIVERED:
        assert u.kind in kinds
        assert u.why.strip() and u.why == u.why.strip()
        assert (REPO / u.path).is_file()
    paths = [u.path for u in safe_areas.UNDELIVERED]
    assert paths == sorted(set(paths))


def test_the_exemptions_are_exactly_these():
    """The list a reviewer reads: what is built with no safe area, and of what kind."""
    assert {u.path: u.kind for u in safe_areas.UNDELIVERED} == {
        "examples/acting_blends.py": "example",
        "examples/acting_continuity.py": "example",
        "examples/acting_gallery.py": "example",
        "examples/acting_transitions.py": "example",
        "examples/body_steps.py": "example",
        "examples/composition_preflight.py": "example",
        "examples/drawing_figure.py": "example",
        "examples/drawing_information.py": "example",
        "examples/drawing_proof.py": "example",
        "examples/limbs_bimanual.py": "example",
        "examples/limbs_cast.py": "example",
        "examples/limbs_contact.py": "example",
        "examples/limbs_evaluate.py": "example",
        "examples/limbs_gallery.py": "example",
        "examples/limbs_quality.py": "example",
        "examples/sdk_showreel.py": "example",
        "examples/target_gaze.py": "example",
        "src/srstudio/_acting_compile.py": "proof",
        "src/srstudio/_benchmark_fixtures.py": "fixture",
        "src/srstudio/bible_diagram.py": "catalog",
        "src/srstudio/cast_card.py": "still",
        "src/srstudio/catalog_page.py": "catalog",
        "src/srstudio/catalog_specimens.py": "catalog",
        "src/srstudio/generated.py": "intermediate",
        "src/srstudio/plates.py": "intermediate",
        "src/srstudio/specimens.py": "catalog",
        "src/srstudio/thumbnail.py": "still",
        "tools/creationbot_avatar.py": "still",
    }


# -- the first delivery --------------------------------------------------------------------------------------------
DECLARED = (
    b'<scene><project safeArea="v" width="1080" height="1920" fps="24" duration="1"/>'
    b'<safeAreas><safeArea id="v" top="0.1146" right="0.1481" bottom="0.2604" left="0.0741" enforce="error"/>'
    b"</safeAreas></scene>"
)
UNDECLARED = b'<scene><project width="1080" height="1920" fps="24" duration="1"/></scene>'


def _release(slug: str) -> Release:
    post = InstagramPost(title="A title", description="A description.", thumbnail=Thumbnail("Two\nlines", 1.0))
    return Release(slug, post)


def episodes(tmp_path: Path, scenes: dict[str, bytes | None]) -> Path:
    for slug, data in scenes.items():
        (tmp_path / slug).mkdir(parents=True)
        if data is not None:
            (tmp_path / slug / f"{slug}.scene.xml").write_bytes(data)
    return tmp_path


def test_a_first_delivery_whose_scene_declares_no_safe_area_is_refused(tmp_path):
    root = episodes(tmp_path, {"new-one": UNDECLARED, "good-one": DECLARED})
    chosen = {s: _release(s) for s in ("new-one", "good-one")}
    found = safe_area_gate.undeclared(chosen, root, {"new-one": "new-one", "good-one": "Good_One"})
    assert found == [Drift("new-one", "its scene declares no safe area (ADR 0218): declare the style's or its own")]


def test_a_first_delivery_with_no_scene_to_read_is_refused_and_not_passed(tmp_path):
    root = episodes(tmp_path, {"no-scene": None})
    found = safe_area_gate.undeclared({"no-scene": _release("no-scene")}, root, {"no-scene": "no-scene"})
    assert [d.name for d in found] == ["no-scene"] and "no scene" in found[0].reason


def test_a_scene_that_is_not_a_document_is_refused_by_name(tmp_path):
    root = episodes(tmp_path, {"broken": b"<scene"})
    found = safe_area_gate.undeclared({"broken": _release("broken")}, root, {"broken": "broken"})
    assert [d.name for d in found] == ["broken"] and "not a scene document" in found[0].reason


def test_a_delivered_reel_is_never_read(tmp_path):
    """Only reels on their first delivery are passed in: a published one is frozen, safe area or none."""
    root = episodes(tmp_path, {"old-one": UNDECLARED})
    assert safe_area_gate.undeclared({"old-one": _release("old-one")}, root, {}) == []


def test_the_instagram_delivery_runs_the_gate_on_first_deliveries():
    source = (REPO / "episodes" / "instagram_posts.py").read_text(encoding="utf-8")
    assert "safe_area_gate.undeclared(chosen, _beside(renders), first)" in source


# -- the pilots' road ----------------------------------------------------------------------------------------------
def package(scene: bytes | None, slug: str) -> bytes:
    data = io.BytesIO()
    with zipfile.ZipFile(data, "w") as z:
        z.writestr("vpkg.json", "{}")
        if scene is not None:
            z.writestr(f"project/{slug}.scene.xml", scene)
    return data.getvalue()


@pytest.mark.parametrize(
    ("data", "said"),
    [
        (package(DECLARED, "p"), ""),
        (package(UNDECLARED, "p"), "its scene declares no safe area"),
        (package(None, "p"), "no project/p.scene.xml"),
        (b"vpkg.zip\n", "not a zip"),
    ],
)
def test_a_pilot_package_is_read_for_its_scene_s_safe_area(tmp_path, data, said):
    path = tmp_path / "vpkg.zip"
    path.write_bytes(data)
    found = safe_area_gate.package_defect(path, "p")
    assert (said in found) if said else found == ""


def test_the_pilot_road_runs_the_gate_on_new_pilots():
    source = (REPO / "episodes" / "publish_pilots.py").read_text(encoding="utf-8")
    assert "undeclared(ready, remote, args.rclone)" in source
