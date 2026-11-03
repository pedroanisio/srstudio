"""The wire jet: a seeded fighter, seen from a named side with its hidden lines removed, and the prop that draws it."""

from __future__ import annotations

import math
import xml.etree.ElementTree as ET

import pytest
from sr_core.scene import Scene

from srstudio import PEACH, Canvas, flat_counter, registry, specimens, wire_jet, wire_jet_prop
from srstudio.wire_jet import AIRFRAMES, INKS, MAX_WIDTH, MIN_WIDTH, VIEWS, WireJetError
from srstudio.wire_view import BANDS, DARK, LEATHER, NO_CEL, PAINT, TRIM, WireError

SMALL = 320  # a small raster keeps each projection a fraction of a second


def points(drawing):
    return [p for lines in drawing.strokes.values() for line in lines for p in line]


def canvas() -> Canvas:
    scene = Scene(version="auto")
    scene.add_project(width=1080, height=1920, fps="24", duration=12.0, background=PEACH.background)
    return Canvas(scene, PEACH, font_asset="comic-neue", namer=flat_counter("k"))


def shapes(cv: Canvas):
    return list(ET.fromstring(cv.scene.to_bytes(layout="pretty")).iter("shape"))


def test_a_seed_gives_the_same_jet_and_a_seed_as_a_number_is_read_as_typed():
    a, b = wire_jet.make_jet("night sortie"), wire_jet.make_jet("night sortie")
    assert a.lines == b.lines and a.masks == b.masks
    assert wire_jet.make_jet(42).lines == wire_jet.make_jet("42").lines
    assert wire_jet.make_jet("night sortie").lines != wire_jet.make_jet("day sortie").lines


def test_a_bare_seed_keeps_one_of_the_first_three_families_and_auto_reaches_all_nine():
    bare = {wire_jet.make_jet(s).style for s in range(30)}
    assert bare <= set(list(AIRFRAMES)[:3]) and len(bare) == 3
    assert {wire_jet.make_jet(s, model="auto").style for s in range(80)} == set(AIRFRAMES)


def test_a_named_model_is_that_airframe_in_metres_whatever_its_case():
    jet = wire_jet.make_jet(3, model="PETREL")
    assert jet.style == "Petrel" and 12.0 < jet.length < 15.0 and 11.0 < jet.wingspan < 15.0
    xs = [p[0] for paths in jet.lines.values() for path in paths for p in path]
    assert min(xs) < 0 < max(xs) and max(xs) - min(xs) < jet.length * 1.2


def test_a_model_that_is_not_a_name_is_refused():
    with pytest.raises(WireJetError, match="model is a name"):
        wire_jet.make_jet(1, model=7)


def test_an_unknown_model_is_refused_and_the_choices_named():
    with pytest.raises(WireJetError, match="unknown model 'zeppelin'.*auto, kestrel"):
        wire_jet.make_jet(1, model="zeppelin")


@pytest.mark.parametrize("sweep", [19.9, 62.1, 0, "40"])
def test_a_sweep_outside_the_switchblades_range_is_refused(sweep):
    with pytest.raises(WireJetError, match="sweep"):
        wire_jet.make_jet(1, model="switchblade", sweep=sweep)


def test_a_sweep_is_only_for_the_switchblade_and_changes_its_wing():
    with pytest.raises(WireJetError, match="Switchblade"):
        wire_jet.make_jet(1, model="kestrel", sweep=40)
    swept = wire_jet.make_jet(1, model="switchblade", sweep=55)
    assert swept.sweep_deg == 55.0
    assert swept.lines != wire_jet.make_jet(1, model="switchblade", sweep=25).lines


def test_every_named_view_draws_something_and_stays_inside_its_picture():
    jet = wire_jet.make_jet("night sortie", model="auto")
    drawn = {view: wire_jet.project(jet, view, width=SMALL) for view in VIEWS}
    for drawing in drawn.values():
        xs, ys = zip(*points(drawing), strict=True)
        assert (
            drawing.width == SMALL and 0 <= min(xs) and max(xs) <= SMALL and 0 <= min(ys) and max(ys) <= drawing.height
        )
        assert set(drawing.strokes) <= set(INKS)
    assert drawn["side"].height < drawn["top"].height  # a fighter is long and low, and wide seen from above
    assert drawn["side"].strokes != drawn["front"].strokes


def test_the_cockpit_view_shows_the_cockpit_alone_so_much_less_than_the_whole_jet():
    jet = wire_jet.make_jet("night sortie")
    whole, tub = wire_jet.project(jet, "front-quarter", width=SMALL), wire_jet.project(jet, "cockpit", width=SMALL)
    assert 0 < len(points(tub)) < len(points(whole))


def test_the_projection_is_deterministic_and_an_explicit_camera_overrides_the_name():
    jet = wire_jet.make_jet("night sortie")
    assert wire_jet.project(jet, "side", width=SMALL) == wire_jet.project(jet, "side", width=SMALL)
    assert wire_jet.project(jet, "front", width=SMALL, yaw=0.0, elevation=0.0).strokes == (
        wire_jet.project(jet, "side", width=SMALL).strokes
    )


def test_hidden_lines_are_removed_so_the_drawing_keeps_less_than_the_jet_has():
    jet = wire_jet.make_jet("night sortie")
    every = sum(len(path) for paths in jet.lines.values() for path in paths)
    kept = sum(
        len(line) for lines in wire_jet.project(jet, "front-quarter", width=SMALL).strokes.values() for line in lines
    )
    assert 0 < kept < every


@pytest.mark.parametrize("width", [100, MAX_WIDTH + 1, 300.5, "300", True, None])
def test_a_width_the_raster_cannot_hold_is_refused(width):
    with pytest.raises(WireJetError, match="width"):
        wire_jet.project(wire_jet.make_jet("x"), "side", width=width)
    assert MIN_WIDTH <= SMALL


def test_an_unknown_view_is_refused_and_named():
    with pytest.raises(WireJetError, match="unknown view 'under'.*side"):
        wire_jet.project(wire_jet.make_jet("x"), "under", width=SMALL)


def test_the_prop_is_registered():
    specimens.load_parts()
    assert registry.get("prop", "wire-jet").builder is wire_jet_prop.wire_jet


def test_the_prop_draws_one_stroked_unfilled_path_per_ink_in_the_palette():
    cv = canvas()
    wire_jet_prop.wire_jet(cv, cv.comp, seed="night sortie", width=400, palette="paper", id="jet")
    drawn = shapes(cv)
    assert 1 < len(drawn) <= len(INKS)
    assert {s.get("stroke") for s in drawn} <= set(wire_jet_prop.PALETTES["paper"].values())
    assert all(s.get("fill") == cv.clear and s.get("shape") == "path" for s in drawn)
    assert [g.get("id") for g in ET.fromstring(cv.scene.to_bytes(layout="pretty")).iter("group")].count("jet") == 1


def test_the_prop_passes_the_model_and_sweep_through_to_the_jet():
    a, b = canvas(), canvas()
    wire_jet_prop.wire_jet(a, a.comp, seed=1, width=400, model="switchblade", sweep=25)
    wire_jet_prop.wire_jet(b, b.comp, seed=1, width=400, model="switchblade", sweep=55)
    assert [s.get("path") for s in shapes(a)] != [s.get("path") for s in shapes(b)]


def test_the_prop_centres_the_jet_on_its_point_and_scales_the_strokes_with_its_size():
    cv = canvas()
    wire_jet_prop.wire_jet(cv, cv.comp, at=(300.0, 700.0), seed="night sortie", width=400, id="jet")
    group = next(g for g in ET.fromstring(cv.scene.to_bytes(layout="pretty")).iter("group") if g.get("id") == "jet")
    assert (float(group.get("x")), float(group.get("y"))) == (300.0, 700.0)
    numbers = [float(n) for s in shapes(cv) for n in s.get("path").replace("M", " ").replace("L", " ").split()]
    assert -210 < min(numbers) < 0 < max(numbers) < 210
    small, big = canvas(), canvas()
    wire_jet_prop.wire_jet(small, small.comp, seed="night sortie", width=1200)
    wire_jet_prop.wire_jet(big, big.comp, seed="night sortie", width=2400)
    ratio = max(float(s.get("strokeWidth")) for s in shapes(big)) / max(
        float(s.get("strokeWidth")) for s in shapes(small)
    )
    assert math.isclose(ratio, 2.0, rel_tol=0.02)


@pytest.mark.parametrize(
    ("kwargs", "message"),
    [
        ({"palette": "neon"}, "unknown palette 'neon'"),
        ({"view": "under"}, "unknown view 'under'"),
        ({"model": "zeppelin"}, "unknown model"),
        ({"sweep": "40"}, "sweep is a number"),
        ({"sweep": True}, "sweep is a number"),
        ({"width": 50}, "width must be from"),
        ({"width": math.nan}, "width must be a finite number"),
        ({"at": (1.0,)}, "at is an"),
        ({"at": (0.0, math.inf)}, "at y must be a finite number"),
        ({"weight": -1}, "weight must be above 0"),
        ({"seed": ""}, "seed is a non-empty"),
        ({"seed": None}, "seed is a non-empty"),
    ],
)
def test_the_prop_refuses_what_it_cannot_draw_and_draws_nothing(kwargs, message):
    cv = canvas()
    with pytest.raises(WireJetError, match=message):
        wire_jet_prop.wire_jet(cv, cv.comp, **{"width": 400, **kwargs})
    assert shapes(cv) == []


def test_the_jet_has_a_pilots_head_as_an_anchor_and_a_two_seater_has_a_second():
    assert "pilot-head" in wire_jet.make_jet("night sortie").anchors
    drawing = wire_jet.project(wire_jet.make_jet("night sortie"), "side", width=SMALL)
    assert drawing.scale > 0 and "pilot-head" in drawing.anchors
    two = [wire_jet.make_jet(s, model="auto") for s in range(80)]
    assert any("rear-pilot-head" in jet.anchors for jet in two)
    assert all("pilot-head" in jet.anchors for jet in two)


def test_a_close_up_goes_round_the_pilot_at_a_scale_the_whole_jet_does_not_have():
    jet = wire_jet.make_jet("night sortie", model="kestrel")
    whole = wire_jet.project(jet, "side", width=SMALL)
    close = wire_jet.project(jet, "side", width=SMALL, around="pilot-head", span=1.25, height=400)
    assert (close.width, close.height) == (SMALL, 400)
    assert close.scale == pytest.approx(SMALL / 1.25) and close.scale > whole.scale
    assert close.anchors["pilot-head"] == pytest.approx((SMALL / 2, 200.0))


@pytest.mark.parametrize(
    ("kwargs", "message"),
    [
        ({"around": "tail", "span": 1.0, "height": 300}, "unknown anchor 'tail'.*pilot-head"),
        ({"around": "pilot-head", "height": 300}, "span is a number of metres"),
        ({"around": "pilot-head", "span": 1.0}, "height is a whole number of pixels"),
        ({"height": 300}, "name the anchor"),
    ],
)
def test_a_close_up_that_cannot_be_framed_is_refused_for_the_jet(kwargs, message):
    with pytest.raises(WireJetError, match=message):
        wire_jet.project(wire_jet.make_jet("night sortie", model="kestrel"), "side", width=SMALL, **kwargs)


def test_the_prop_gives_the_anchor_where_the_drawn_jet_puts_it():
    shot = {"at": (500.0, 900.0), "width": SMALL, "seed": "tuesday", "view": "side", "model": "kestrel"}
    found = wire_jet_prop.anchor("pilot-head", **shot, around="pilot-head", span=1.25, height=400)
    assert found.scale == pytest.approx(SMALL / 1.25)
    assert (found.x, found.y) == pytest.approx((500.0, 900.0))
    assert wire_jet_prop.anchor("pilot-head", **shot).scale < found.scale


def test_the_prop_refuses_an_anchor_the_jet_does_not_have():
    with pytest.raises(WireJetError, match="unknown anchor 'tail'"):
        wire_jet_prop.anchor("tail", width=SMALL)


def test_the_prop_draws_a_close_up_and_keeps_only_the_rows_asked_for():
    shot = {"width": SMALL, "seed": "tuesday", "view": "side", "model": "kestrel", "around": "pilot-head"}
    shot |= {"span": 1.25, "height": 400}
    whole, upper = canvas(), canvas()
    wire_jet_prop.wire_jet(whole, whole.comp, **shot)
    wire_jet_prop.wire_jet(upper, upper.comp, **shot, rows=(-200.0, 0.0))
    numbers = [float(n) for s in shapes(upper) for n in s.get("path").replace("M", " ").replace("L", " ").split()]
    assert shapes(upper) and max(numbers[1::2]) <= 0.5 and len(shapes(upper)) <= len(shapes(whole))


def test_the_prop_refuses_rows_that_are_not_a_top_above_a_bottom():
    cv = canvas()
    with pytest.raises(WireJetError, match="rows"):
        wire_jet_prop.wire_jet(cv, cv.comp, width=SMALL, rows=(10.0, -10.0))
    assert shapes(cv) == []


def test_a_frame_on_empty_space_is_refused_by_the_shared_view_error():
    with pytest.raises(WireError, match="frame shows no line"):
        wire_jet.project(
            wire_jet.make_jet("night sortie", model="kestrel"),
            "side",
            width=SMALL,
            around="pilot-head",
            span=0.01,
            height=300,
        )


@pytest.mark.parametrize(
    ("part", "material"),
    [
        ("Cockpit seat 1", LEATHER),
        ("Cockpit tub", TRIM),
        ("Canopy frames", TRIM),
        ("Exhaust centre", DARK),
        ("Fuselage", PAINT),
        ("Wing port", PAINT),
    ],
)
def test_each_part_of_the_jet_is_made_of_what_its_name_says(part, material):
    assert wire_jet._material(part) == material


LIGHT = (-0.55, 0.46, 0.70)


def test_a_jet_seen_with_a_light_has_its_surfaces_by_material_and_the_same_strokes():
    jet = wire_jet.make_jet("tuesday", model="kestrel")
    plain = wire_jet.project(jet, "side", width=SMALL)
    lit = wire_jet.project(jet, "side", width=SMALL, light=LIGHT)
    assert plain.cel == b"" and plain.strokes == lit.strokes
    codes = {c // BANDS for c in set(lit.cel) if c != NO_CEL}
    assert {PAINT, DARK} <= codes and codes <= {PAINT, DARK, LEATHER, TRIM}
    with pytest.raises(WireError, match="light is a direction"):
        wire_jet.project(jet, "side", width=SMALL, light=(0, 0, 0))


def test_the_plate_of_a_jet_lies_where_its_strokes_do_and_shares_their_projection():
    shot = {"at": (500.0, 900.0), "width": SMALL, "seed": "plate", "view": "side", "model": "kestrel"}
    wire_jet_prop._drawing.cache_clear()
    plate = wire_jet_prop.plate(LIGHT, **shot)
    cv = canvas()
    wire_jet_prop.wire_jet(cv, cv.comp, light=LIGHT, **shot)
    wire_jet_prop.anchor("pilot-head", light=LIGHT, **shot)
    assert (plate.x, plate.y) == (500.0 - plate.width / 2, 900.0 - plate.height / 2)
    info = wire_jet_prop._drawing.cache_info()
    assert (info.misses, info.hits) == (1, 2)


def test_a_jet_plate_keeps_only_the_rows_asked_for_and_refuses_what_it_cannot_paint():
    shot = {"at": (500.0, 900.0), "width": SMALL, "seed": "tuesday", "view": "side", "model": "kestrel"}
    assert wire_jet_prop.plate(LIGHT, rows=(-1e5, 0.0), **shot).png != wire_jet_prop.plate(LIGHT, **shot).png
    with pytest.raises(WireJetError, match="unknown palette 'day'"):
        wire_jet_prop.plate(LIGHT, palette="day", **shot)


def test_a_jet_seen_in_perspective_differs_from_the_flat_view_and_a_bad_distance_or_one_inside_is_refused():
    jet = wire_jet.make_jet("tuesday", model="kestrel")
    flat = wire_jet.project(jet, "front-quarter", width=SMALL)
    seen = wire_jet.project(jet, "front-quarter", width=SMALL, distance=30.0)
    assert flat.strokes != seen.strokes and seen.strokes
    for bad in (0, -5.0, math.nan, True, "9"):
        with pytest.raises(WireError, match="distance"):
            wire_jet.project(jet, "front-quarter", width=SMALL, distance=bad)
    with pytest.raises(WireError, match="inside"):
        wire_jet.project(jet, "front-quarter", width=SMALL, distance=2.0)


def test_the_jet_prop_in_perspective_gives_the_pilots_head_scale_where_the_head_is():
    shot = {"at": (540.0, 960.0), "width": SMALL, "seed": "tuesday", "view": "side", "model": "kestrel"}
    flat = wire_jet_prop.anchor("pilot-head", **shot)
    seen = wire_jet_prop.anchor("pilot-head", distance=40.0, **shot)
    assert flat.scale > 0 and seen.scale > 0 and flat.scale != seen.scale


def test_the_edge_of_the_coaming_is_found_under_the_pilots_head():
    shot = {
        "at": (540.0, 980.0),
        "width": 1080,
        "seed": "tuesday",
        "view": "side",
        "model": "kestrel",
        "around": "pilot-head",
        "span": 1.25,
        "height": 1920,
        "distance": 14.0,
        "light": (-0.5, 0.7, 0.5),
    }
    head = wire_jet_prop.anchor("pilot-head", **shot)
    row, slope = wire_jet_prop.edge("pilot-head", 0.3, 0.6, **shot)
    assert 0 < row + 980.0 - head.y < 0.5 * head.scale and slope != 0.0
    with pytest.raises(WireJetError, match="no paint"):
        wire_jet_prop.edge("pilot-head", 5.0, 0.6, **shot)
