"""The map kit: its scale formulas, its layers, its refusals, and what it writes into a scene."""

from __future__ import annotations

import hashlib
import json
import math
from importlib.resources import files
from pathlib import Path

import pytest
from sr_core.scene import Scene

from srstudio import map_kit
from srstudio.canvas import Canvas
from srstudio.map_kit import MapKitError, Move, Place
from srstudio.toon import Line

ROME = Place("Rome", 41.89193, 12.51133)
ADELAIDE = Place("Adelaide", -34.92866, 138.59863)


def measure(text: str, size: float) -> float:
    return len(text) * size * 0.6


def canvas() -> Canvas:
    scene = Scene(version="auto")
    scene.add_project(width=1080, height=1920, fps="30", duration=8, background="#ffffff")
    return Canvas(scene, map_kit.MAPS.palettes[0], font_asset="lexend", width=1080, height=1920)


def xml(cv: Canvas) -> str:
    return cv.scene.to_bytes().decode()


def test_the_scale_of_a_flat_map_is_the_frame_over_the_world():
    assert map_kit.degree_px(0.0) == 3.0
    assert map_kit.degree_px(3.0) == 24.0
    assert map_kit.zoom_for_degree(map_kit.degree_px(2.5)) == pytest.approx(2.5)
    with pytest.raises(MapKitError):
        map_kit.zoom_for_degree(0.0)


def test_a_ring_is_the_lambert_chord_of_its_great_circle_radius():
    km = 3300.0
    # zoom 0 fits the whole sphere's rim, two radii from the centre, in half the frame's width
    assert map_kit.ring_px(km, 0.0) == pytest.approx(2 * math.sin(km / (2 * map_kit.EARTH_KM)) * 270.0)
    assert map_kit.ring_px(math.pi * map_kit.EARTH_KM * 0.999999, 0.0) == pytest.approx(540.0, abs=1e-3)
    assert map_kit.ring_px(km, 1.0) == pytest.approx(2 * map_kit.ring_px(km, 0.0))
    assert map_kit.ring_px(km, map_kit.zoom_for_ring(km, 430.0)) == pytest.approx(430.0)


@pytest.mark.parametrize("km", [0.0, -1.0, 21000.0, float("nan")])
def test_a_ring_past_the_antipode_is_refused(km):
    with pytest.raises(MapKitError):
        map_kit.ring_px(km, 1.0)


def test_km_between_is_the_great_circle():
    assert map_kit.km_between((0.0, 0.0), (0.0, 1.0)) == pytest.approx(111.195, abs=0.01)
    # the gap the reel states: London over Calgary, along a meridian
    assert map_kit.km_between((51.50853, 0.0), (51.05011, 0.0)) == pytest.approx(51.0, abs=0.1)


def test_a_glide_stays_on_the_great_circle_and_ends_where_it_says():
    a, b = (21.70282, 99.34224), (ADELAIDE.lat, ADELAIDE.lon)
    lons, lats = map_kit.glide(a, b, 5.0, 7.0)
    assert (lons[0][0], lons[-1][0]) == (5.0, 7.0)
    assert (lats[0][1], lons[0][1]) == pytest.approx(a, abs=1e-4)
    assert (lats[-1][1], lons[-1][1]) == pytest.approx(b, abs=1e-4)
    whole = map_kit.km_between(a, b)
    for (_, lat), (_, lon) in zip(lats, lons, strict=True):
        assert map_kit.km_between(a, (lat, lon)) + map_kit.km_between((lat, lon), b) == pytest.approx(whole, abs=0.01)
    with pytest.raises(MapKitError):
        map_kit.glide(a, a, 0.0, 1.0)
    with pytest.raises(MapKitError):
        map_kit.glide(a, b, 2.0, 1.0)


def test_a_place_rounds_its_figure_to_one_decimal_with_its_hemisphere():
    assert ROME.latitude == "41.9°N"
    assert Place("Calgary", 51.05011, -114.08529).latitude == "51.1°N"
    assert ADELAIDE.latitude == "34.9°S"


@pytest.mark.parametrize("lat, lon", [(91.0, 0.0), (0.0, 181.0), (float("nan"), 0.0)])
def test_a_place_off_the_earth_is_refused(lat, lon):
    with pytest.raises(MapKitError):
        Place("Nowhere", lat, lon)


@pytest.mark.parametrize("name", ["", "   ", "New York", "new york"])
def test_a_place_needs_a_name_that_says_which_place(name):
    with pytest.raises(MapKitError):
        Place(name, 40.7, -74.0)


def test_check_copy_refuses_a_word_the_channel_keeps_off_screen():
    assert map_kit.check_copy("Which is further north?") == "Which is further north?"
    with pytest.raises(MapKitError):
        map_kit.check_copy("Comment below if you guessed right")


def test_check_labels_counts_what_is_on_screen_at_once():
    spans = [(float(i), float(i) + 1.5, f"label {i}") for i in range(12)]
    map_kit.check_labels(spans)
    crowded = [(0.0, 5.0, f"label {i}") for i in range(7)]
    with pytest.raises(MapKitError, match="7 labels"):
        map_kit.check_labels(crowded)
    with pytest.raises(MapKitError):
        map_kit.check_labels([(2.0, 1.0, "backwards")])


def test_layers_install_byte_for_byte_and_declare_their_digest(tmp_path: Path):
    map_kit.install(tmp_path)
    for name in map_kit.LAYERS:
        path = tmp_path / "assets/maps" / f"{name}.geojson"
        assert path.read_bytes() == (files("srstudio") / "assets/maps" / f"{name}.geojson").read_bytes()
    cv = canvas()
    map_kit.flat(cv, cv.comp, 0.0, 40.0, 2.0, 0.0, 8.0)
    digest = hashlib.sha256((tmp_path / "assets/maps/land.geojson").read_bytes()).hexdigest()
    assert digest in xml(cv)
    assert xml(cv).count('src="assets/maps/land.geojson"') == 1


def test_the_shipped_layers_stay_small_and_match_their_record():
    folder = files("srstudio") / "assets/maps"
    record = json.loads((folder / "layers.json").read_text())
    total = 0
    for name in map_kit.LAYERS:
        data = (folder / f"{name}.geojson").read_bytes()
        assert hashlib.sha256(data).hexdigest() == record["layers"][name]["sha256"]
        total += len(data)
    assert total < 2_000_000


def test_every_zone_holds_its_total_in_dots_rounded_to_the_million():
    assert len(map_kit.dots("inside")) == 3954
    assert len(map_kit.dots("adelaide")) == 44
    assert len(map_kit.dots("rest")) == 4194
    with pytest.raises(MapKitError):
        map_kit.dots("mars")


def test_the_dots_of_a_zone_lie_in_its_circle():
    centre = (21.70282, 99.34224)
    far = max(map_kit.km_between(centre, (lat, lon)) for lon, lat in map_kit.dots("inside"))
    assert (
        far <= 3300.0 + 12.0
    )  # a dot sits on a 0.1 degree cell, whose centre is at most this far from the one counted


def test_antarctica_closes_around_the_pole_without_a_line_across_the_ice():
    land = json.loads((files("srstudio") / "assets/maps/land.geojson").read_text())

    def points(value):
        if isinstance(value[0], float):
            yield value
        else:
            for part in value:
                yield from points(part)

    assert min(p[1] for f in land["features"] for p in points(f["geometry"]["coordinates"])) > -90.0


def test_a_view_names_its_projection_honestly():
    cv = canvas()
    map_kit.globe(cv, cv.comp, -20.0, 25.0, 0.0, 8.0, spin=[(0.0, -20.0), (8.0, 0.0)], id="a")
    map_kit.flat(cv, cv.comp, 0.0, 40.0, 2.0, 0.0, 8.0, id="b")
    map_kit.equal_area(cv, cv.comp, 99.0, 21.0, 1.6, 0.0, 8.0, id="c")
    text = xml(cv)
    assert 'projection="orthographic"' in text
    assert 'projection="equirectangular"' in text
    assert 'projection="azimuthal-equal-area"' in text


def test_a_camera_flies_only_forward():
    cv = canvas()
    moves = [Move(1.0, 2.0, -74.0, 41.0, 4.0), Move(4.0, 1.0, -73.0, 45.0, 3.0)]
    view = map_kit.flat(cv, cv.comp, 12.0, 42.0, 5.0, 0.0, 8.0, moves=moves)
    assert len(view.find_all("flyTo")) == 2
    overlapping = [Move(1.0, 2.0, -74.0, 41.0, 4.0), Move(2.0, 1.0, -73.0, 45.0, 3.0)]
    with pytest.raises(MapKitError, match="overlap"):
        map_kit.flat(cv, cv.comp, 12.0, 42.0, 5.0, 0.0, 8.0, moves=overlapping, id="other")


def test_a_pin_rides_the_map_and_shows_its_figure_only_when_asked():
    cv = canvas()
    view = map_kit.globe(cv, cv.comp, 12.0, 42.0, 0.0, 8.0)
    map_kit.pin(cv, cv.comp, view.id, ROME, 0.0, 8.0, measure, figure=False, id="asked")
    text = xml(cv)
    assert "geo(&apos;map-globe&apos;" in text or "geo('map-globe'" in text
    assert "41.9" not in text
    map_kit.pin(cv, cv.comp, view.id, ROME, 3.0, 8.0, measure, id="told")
    assert "41.9°N" in xml(cv)
    with pytest.raises(MapKitError, match="right, left"):
        map_kit.pin(cv, cv.comp, view.id, ROME, 3.0, 8.0, measure, side="up", id="bad")


def test_a_parallel_is_a_dense_line_at_one_latitude():
    cv = canvas()
    view = map_kit.flat(cv, cv.comp, 0.0, 40.0, 2.0, 0.0, 8.0)
    map_kit.parallel(cv, cv.comp, view, ROME, 1.0, 8.0, tag_from=2.0, measure=measure)
    west, east = view.find_all("route")
    for route in (west, east):
        rows = [p.split(",") for p in route.points.split()]
        assert {lat for _, lat in rows} == {"41.89193"}
        assert len(rows) > 40  # a route's edges are great circles, so the points must be close to stay on the parallel
    assert "Rome 41.9°N" in xml(cv)


def test_a_parallel_refuses_a_tag_it_cannot_letter_or_time():
    cv = canvas()
    view = map_kit.flat(cv, cv.comp, 0.0, 40.0, 2.0, 0.0, 8.0)
    with pytest.raises(MapKitError):
        map_kit.parallel(cv, cv.comp, view, ROME, 1.0, 8.0, tag_from=2.0, id="a")
    with pytest.raises(MapKitError):
        map_kit.parallel(cv, cv.comp, view, ROME, 1.0, 8.0, tag_from=9.0, measure=measure, id="b")
    with pytest.raises(MapKitError):
        map_kit.parallel(cv, cv.comp, view, ROME, 1.0, 2.0, drawn=5.0, id="c")


def test_population_filters_each_wave_by_its_key():
    cv = canvas()
    view = map_kit.equal_area(cv, cv.comp, 99.0, 21.0, 1.6, 0.0, 8.0)
    map_kit.population(cv, view, {"inside": (1.0, 2.0), "adelaide": (3.0, 5.0)})
    layers = [g for g in view.find_all("geoLayer") if str(g.id or "").startswith("map-population")]
    assert sum(1 for g in layers if g.filter.startswith("k=inside")) == 6
    assert sum(1 for g in layers if g.filter.startswith("k=adelaide")) == 44


@pytest.mark.parametrize("waves", [{}, {"mars": (0.0, 1.0)}, {"inside": (2.0, 1.0)}])
def test_population_refuses_a_zone_it_cannot_draw(waves):
    cv = canvas()
    view = map_kit.equal_area(cv, cv.comp, 99.0, 21.0, 1.6, 0.0, 8.0)
    with pytest.raises(MapKitError):
        map_kit.population(cv, view, waves)


def test_a_ring_refuses_no_radius():
    cv = canvas()
    with pytest.raises(MapKitError):
        map_kit.ring(cv, cv.comp, 0.0, 0.0, 1.0)


def test_a_stamp_shrinks_to_two_lines_and_then_refuses():
    cv = canvas()
    map_kit.stamp(cv, cv.comp, "Inside 3.95 bn. Outside 4.24 bn. GHS-POP 2025.", 0.0, 5.0, measure)
    assert "GHS-POP 2025." in xml(cv)
    with pytest.raises(MapKitError, match="lines"):
        map_kit.stamp(cv, cv.comp, "word " * 80, 0.0, 5.0, measure, id="long")
    with pytest.raises(MapKitError):
        map_kit.stamp(cv, cv.comp, "Comment below", 0.0, 5.0, measure, id="bait")


def test_captions_refuse_a_cue_of_four_lines():
    cv = canvas()
    fine = [Line(id="a", text="Which is further north?", start=0.0, end=1.0, speaker="narrator")]
    assert map_kit.captions(cv, cv.comp, fine, measure) is not None
    long = [Line(id="b", text="word " * 60, start=0.0, end=1.0, speaker="narrator")]
    with pytest.raises(MapKitError, match="lines"):
        map_kit.captions(cv, cv.comp, long, measure, id="other")


def test_the_narrator_is_the_channels_own_constant():
    assert map_kit.NARRATOR.voice.name == "Bella"
    assert map_kit.NARRATOR.settings.stability == 0.60
    assert map_kit.CARD in map_kit.MAPS_CAST.characters
    assert map_kit.MAPS.fps == 30 and map_kit.MAPS.mix.loudness == "-14"
