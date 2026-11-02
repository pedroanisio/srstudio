"""The Retro Orbit sets and props (ADR 0063): plates, two locations built for 9:16, five props, lettering in the
pack's fonts and one print finish."""

import os
import xml.etree.ElementTree as ET
from pathlib import Path

import pytest
from sr_core.scene import Scene

from srstudio import (
    PEACH,
    Canvas,
    brush,
    flat_counter,
    parts,
    registry,
    specimens,
    styles,
    toon,
    toon_orbit,
    toon_plate,
)
from srstudio.toon import ToonDataError
from srstudio.toon_plate import Frame

EPISODES = Path(os.environ.get("SRSTUDIO_EPISODES", "generated/episodes"))
needs_projects = pytest.mark.skipif(not EPISODES.is_dir(), reason="needs SRSTUDIO_EPISODES")

LOCATIONS = {
    "toon-planetarium-salon": toon_orbit.planetarium_salon,
    "toon-starlight-terrace": toon_orbit.starlight_terrace,
}
PROPS = {
    "toon-telescope": toon_orbit.telescope,
    "toon-moon-globe": toon_orbit.moon_globe,
    "toon-saturn-model": toon_orbit.saturn_model,
    "toon-field-notebook": toon_orbit.field_notebook,
    "toon-signal-clicker": toon_orbit.signal_clicker,
}
ALL = {**LOCATIONS, **PROPS}
PLATES = {"salon": toon_orbit.salon_plate, "terrace": toon_orbit.terrace_plate}


def stage(font: str | None = "caption") -> Canvas:
    scene = Scene(version="auto")
    scene.add_project(width=1080, height=1920, fps="24", duration=4.0, background=PEACH.background)
    return Canvas(scene, PEACH, font_asset=font, namer=flat_counter("o"))


def tree(cv: Canvas) -> ET.Element:
    return ET.fromstring(cv.scene.to_bytes(layout="pretty"))


# -- the plate ---------------------------------------------------------------------------------------------------------
def test_a_path_becomes_a_closed_cubic_shape():
    shape = toon_plate.shape("M 0 0 L 10 0 Q 10 10 0 10 C 0 8 0 4 0 0 Z")
    assert shape[:2] == (0.0, 0.0)
    assert (len(shape) - 2) % 6 == 0
    assert shape[-2:] == (0.0, 0.0)


def test_a_frame_scales_turns_and_nests():
    frame = Frame(10.0, 20.0, 2.0)
    assert frame.point(1.0, 1.0) == (12.0, 22.0)
    turned = Frame(0.0, 0.0, 1.0, 90.0)
    x, y = turned.point(1.0, 0.0)
    assert (round(x, 6), round(y, 6)) == (0.0, 1.0)
    assert frame.then(Frame(1.0, 1.0, 3.0)).point(1.0, 0.0) == (18.0, 22.0)


@pytest.mark.parametrize("d", ["", "L 1 1", "M 0 0 A 1 1 0 0 0 2 2 Z", "M 0 0 L 1", "M 0 x L 1 1 Z", "M 0 0 l 1 1 Z"])
def test_a_path_this_parser_cannot_read_is_refused(d):
    with pytest.raises(ToonDataError):
        toon_plate.shape(d)


def test_a_frame_with_no_scale_is_refused():
    with pytest.raises(ToonDataError):
        Frame(0.0, 0.0, 0.0)


def test_a_polygon_is_clipped_to_a_convex_outline():
    square = ((0.0, 0.0), (10.0, 0.0), (10.0, 10.0), (0.0, 10.0))
    out = toon_plate.clip(((5.0, 5.0), (20.0, 5.0), (20.0, 20.0), (5.0, 20.0)), square)
    assert sorted(out) == sorted(((5.0, 5.0), (10.0, 5.0), (10.0, 10.0), (5.0, 10.0)))
    assert toon_plate.clip(((30.0, 30.0), (40.0, 30.0), (40.0, 40.0)), square) == ()


def test_a_polyline_keeps_what_lies_inside_an_outline():
    square = ((0.0, 0.0), (10.0, 0.0), (10.0, 10.0), (0.0, 10.0))
    assert toon_plate.inside(((-5.0, 5.0), (5.0, 5.0), (6.0, 5.0), (15.0, 5.0)), square) == ((5.0, 5.0), (6.0, 5.0))


# -- the finish --------------------------------------------------------------------------------------------------------
def test_the_print_finish_is_one_style_level_function_that_repeats_exactly():
    a, b = stage(), stage()
    toon_orbit.print_finish(a, a.comp)
    toon_orbit.print_finish(b, b.comp)
    assert a.scene.to_bytes() == b.scene.to_bytes()


def test_the_print_finish_is_a_dark_and_a_light_grain_at_the_opacities_it_was_drawn_with():
    cv = stage()
    toon_orbit.print_finish(cv, cv.comp)
    grains = [n for n in tree(cv).iter("shape") if n.get("shape") == "path"]
    assert [(n.get("fill"), n.get("opacity")) for n in grains] == [(toon_plate.NAVY, "0.08"), (toon_plate.CREAM, "0.2")]
    assert sum(n.get("path").count("M") for n in grains) == 1080 * 1920 // 900
    assert all(n.get("stroke") == cv.clear for n in grains)


def test_the_finish_takes_another_seed_and_refuses_a_grain_of_nothing():
    a, b = stage(), stage()
    toon_orbit.print_finish(a, a.comp)
    toon_orbit.print_finish(b, b.comp, seed=7)
    assert a.scene.to_bytes() != b.scene.to_bytes()
    with pytest.raises(ToonDataError):
        toon_orbit.print_finish(stage(), stage().comp, density=0.0)


def test_the_finish_plugs_into_a_shot_as_a_staging_finish():
    assert toon_orbit.print_finish.__code__.co_varnames[:2] == ("cv", "parent")


def test_no_set_or_prop_applies_a_finish_of_its_own():
    for builder in ALL.values():
        cv = stage()
        builder(cv, cv.comp)
        opacities = [n.get("opacity") for n in tree(cv).iter("shape") if n.get("opacity")]
        assert "0.08" not in opacities


# -- the sets ----------------------------------------------------------------------------------------------------------
@pytest.mark.parametrize("plate", PLATES.values(), ids=PLATES)
def test_a_set_covers_the_whole_nine_by_sixteen_frame(plate):
    edges = [brush.bounds(s) for s, _ in plate()]
    assert min(e[0] for e in edges) <= 0.0
    assert max(e[2] for e in edges) >= toon.REF_W
    assert min(e[1] for e in edges) <= toon.REF_TOP
    assert max(e[3] for e in edges) >= toon.REF_TOP + 1920.0 / toon.SCALE


@pytest.mark.parametrize("builder", LOCATIONS.values(), ids=LOCATIONS)
def test_a_set_draws_no_lettering_unasked_and_no_signature_of_its_own(builder):
    cv = stage()
    builder(cv, cv.comp)
    assert not list(tree(cv).iter("text"))
    assert b"cactus" not in cv.scene.to_bytes()


def test_the_stars_repeat_by_seed():
    assert toon_orbit.stars(592.0, 400.0, 31) == toon_orbit.stars(592.0, 400.0, 31)
    assert toon_orbit.stars(592.0, 400.0, 31) != toon_orbit.stars(592.0, 400.0, 30)


def test_a_sky_with_no_room_is_refused():
    with pytest.raises(ToonDataError):
        toon_orbit.stars(0.0, 400.0, 1)


# -- the lettering -----------------------------------------------------------------------------------------------------
def test_lettering_goes_in_the_fonts_it_names_and_nowhere_when_none_is_given():
    plain, lettered = stage(), stage()
    toon_orbit.planetarium_salon(plain, plain.comp)
    toon_orbit.planetarium_salon(lettered, lettered.comp, toon_orbit.Lettering("bebas", "dm"))
    assert b'fontAsset="bebas"' not in plain.scene.to_bytes()
    assert b'fontAsset="bebas"' in lettered.scene.to_bytes()
    assert b'fontAsset="dm"' in lettered.scene.to_bytes()
    assert b"TODAY: SATURN" in lettered.scene.to_bytes()


def test_the_terrace_and_the_notebook_letter_their_signs():
    terrace, book = stage(), stage()
    toon_orbit.starlight_terrace(terrace, terrace.comp, toon_orbit.Lettering("bebas", "dm"))
    toon_orbit.field_notebook(book, book.comp, lettering=toon_orbit.Lettering("bebas", "dm"))
    assert b"FIELD" in terrace.scene.to_bytes() and b"STATION" in terrace.scene.to_bytes()
    assert b"FIELD" in book.scene.to_bytes() and b"NOTES" in book.scene.to_bytes()


def test_the_lettering_is_refused_without_its_font_ids():
    with pytest.raises(ToonDataError):
        toon_orbit.Lettering("", "dm")


def test_the_pack_s_fonts_are_the_google_fonts_named():
    assert (toon_orbit.DISPLAY_FONT.family, toon_orbit.DISPLAY_FONT.weight) == ("Bebas Neue", 400)
    assert (toon_orbit.BODY_FONT.family, toon_orbit.BODY_FONT.weight) == ("DM Sans", 700)


# -- the props and the record ------------------------------------------------------------------------------------------
@pytest.mark.parametrize("builder", PROPS.values(), ids=PROPS)
def test_a_prop_grows_about_its_foot(builder):
    small, big = stage(), stage()
    builder(small, small.comp, at=(300.0, 800.0), scale=0.5)
    builder(big, big.comp, at=(300.0, 800.0), scale=1.0)
    assert small.scene.to_bytes() != big.scene.to_bytes()


@pytest.mark.parametrize("builder", PROPS.values(), ids=PROPS)
def test_a_prop_refuses_a_scale_of_nothing(builder):
    cv = stage()
    with pytest.raises(ToonDataError):
        builder(cv, cv.comp, scale=0.0)


@pytest.mark.parametrize("name", ALL)
def test_each_part_is_registered_proposed_with_no_approval(name):
    specimens.load_parts()
    kind = "location" if name in LOCATIONS else "prop"
    entry = registry.get(kind, name)
    assert entry.builder is ALL[name]
    assert entry.style == "toon"
    version = parts.get(name).version(1)
    assert version.status == "proposed"
    assert version.approval is None
    assert version.proof == "generated/character-proofs/lyra/index.html"


@needs_projects
@pytest.mark.parametrize("name", ALL)
def test_each_digest_is_the_one_on_record(name):
    assert specimens.digest(name) == parts.get(name).version(1).drawing


def test_a_set_is_refused_to_a_reel_while_proposed():
    with pytest.raises(parts.NotApprovedError):
        parts.resolved("toon-planetarium-salon")


def test_the_toon_style_knows_the_plate_modules():
    assert "toon_orbit" in styles.STYLES["toon"].parts
