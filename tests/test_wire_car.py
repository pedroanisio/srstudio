"""The wire car: a seeded car, seen from a named side with its hidden lines removed, and the prop that draws it."""

from __future__ import annotations

import math
import xml.etree.ElementTree as ET

import pytest
from sr_core.scene import Scene

from srstudio import PEACH, Canvas, flat_counter, registry, specimens, wire_car, wire_car_prop
from srstudio.wire_car import INKS, VIEWS, WireCarError
from srstudio.wire_view import BANDS, DARK, LEATHER, NO_CEL, PAINT, TIRE, TRIM, WireError

SMALL = 320  # a small raster keeps each projection a fraction of a second


def points(drawing):
    return [p for lines in drawing.strokes.values() for line in lines for p in line]


def canvas() -> Canvas:
    scene = Scene(version="auto")
    scene.add_project(width=1080, height=1920, fps="24", duration=12.0, background=PEACH.background)
    return Canvas(scene, PEACH, font_asset="comic-neue", namer=flat_counter("k"))


def shapes(cv: Canvas):
    return list(ET.fromstring(cv.scene.to_bytes(layout="pretty")).iter("shape"))


def test_a_seed_gives_the_same_car_and_a_seed_as_a_number_is_read_as_typed():
    a, b = wire_car.make_car("night drive"), wire_car.make_car("night drive")
    assert a.lines == b.lines and a.masks == b.masks
    assert wire_car.make_car(42).lines == wire_car.make_car("42").lines
    assert wire_car.make_car("night drive").lines != wire_car.make_car("day drive").lines


def test_the_seeds_reach_all_three_body_styles_in_metres():
    cars = {wire_car.make_car(s).style: wire_car.make_car(s) for s in range(12)}
    assert set(cars) == {"Berlinetta", "Sportback", "Shooting brake"}
    for car in cars.values():
        assert 2.4 < car.wheelbase < 3.0 and 1.7 < car.width < 2.1 and 0.3 < car.radius < 0.4
        xs = [p[0] for paths in car.lines.values() for path in paths for p in path]
        assert -3.0 < min(xs) < -1.5 and 1.5 < max(xs) < 3.0  # the nose is toward negative x


def test_a_side_view_is_longer_than_tall_and_stays_inside_its_picture():
    drawing = wire_car.project(wire_car.make_car("night drive"), "side", width=SMALL)
    assert drawing.width == SMALL and 0 < drawing.height < SMALL // 2
    xs, ys = zip(*points(drawing), strict=True)
    assert 0 <= min(xs) and max(xs) <= drawing.width and 0 <= min(ys) and max(ys) <= drawing.height
    assert set(drawing.strokes) <= set(INKS)
    assert list(drawing.strokes) == [ink for ink in INKS if ink in drawing.strokes]


def test_every_named_view_draws_something_and_two_views_differ():
    car = wire_car.make_car("night drive")
    drawn = {view: wire_car.project(car, view, width=SMALL) for view in VIEWS}
    assert all(points(d) for d in drawn.values())
    assert drawn["side"].strokes != drawn["front-quarter"].strokes
    assert drawn["front-quarter"].strokes != drawn["rear-quarter"].strokes


def test_an_explicit_yaw_and_elevation_override_the_named_view():
    car = wire_car.make_car("night drive")
    named = wire_car.project(car, "side", width=SMALL)
    assert wire_car.project(car, "side", width=SMALL, yaw=0.0, elevation=0.0).strokes == named.strokes
    assert wire_car.project(car, "side", width=SMALL, yaw=34.0, elevation=14.0).strokes != named.strokes


def test_the_projection_is_deterministic():
    car = wire_car.make_car("night drive")
    assert wire_car.project(car, "front-quarter", width=SMALL) == wire_car.project(car, "front-quarter", width=SMALL)


def test_hidden_lines_are_removed_so_the_drawing_keeps_less_than_the_car_has():
    car = wire_car.make_car("night drive")
    drawing = wire_car.project(car, "front-quarter", width=SMALL)
    every = sum(len(path) for paths in car.lines.values() for path in paths)
    kept = sum(len(line) for lines in drawing.strokes.values() for line in lines)
    assert 0 < kept < every


def test_the_cutaway_and_the_dashboard_show_the_cabin_alone():
    car = wire_car.make_car("night drive")
    outside = wire_car.project(car, "front-quarter", width=SMALL)
    assert "tire" in outside.strokes
    for view in ("cutaway", "dashboard"):
        inside = wire_car.project(car, view, width=SMALL)
        assert "tire" not in inside.strokes and points(inside)


@pytest.mark.parametrize("width", [SMALL - 1000, 100, wire_car.MAX_WIDTH + 1, 300.5, "300", True, None])
def test_a_width_the_raster_cannot_hold_is_refused(width):
    with pytest.raises(WireCarError, match="width"):
        wire_car.project(wire_car.make_car("x"), "side", width=width)


def test_an_unknown_view_is_refused_and_named():
    with pytest.raises(WireCarError, match="unknown view 'top'.*side"):
        wire_car.project(wire_car.make_car("x"), "top", width=SMALL)


def test_the_prop_is_registered():
    specimens.load_parts()
    assert registry.get("prop", "wire-car").builder is wire_car_prop.wire_car


def test_the_prop_draws_one_stroked_unfilled_path_per_ink_in_the_palette():
    cv = canvas()
    wire_car_prop.wire_car(cv, cv.comp, seed="night drive", width=400, palette="paper", id="car")
    drawn = shapes(cv)
    assert 1 < len(drawn) <= len(INKS)
    assert {s.get("stroke") for s in drawn} <= set(wire_car_prop.PALETTES["paper"].values())
    assert all(s.get("fill") == cv.clear and s.get("shape") == "path" for s in drawn)
    assert [g.get("id") for g in ET.fromstring(cv.scene.to_bytes(layout="pretty")).iter("group")].count("car") == 1


def test_the_prop_centres_the_car_on_its_point_and_scales_the_strokes_with_its_size():
    cv = canvas()
    wire_car_prop.wire_car(cv, cv.comp, at=(300.0, 700.0), seed="night drive", width=400, id="car")
    group = next(g for g in ET.fromstring(cv.scene.to_bytes(layout="pretty")).iter("group") if g.get("id") == "car")
    assert (float(group.get("x")), float(group.get("y"))) == (300.0, 700.0)
    numbers = [float(n) for s in shapes(cv) for n in s.get("path").replace("M", " ").replace("L", " ").split()]
    assert -210 < min(numbers) < 0 < max(numbers) < 210  # about the origin, no wider than the car
    small, big = canvas(), canvas()
    wire_car_prop.wire_car(small, small.comp, seed="night drive", width=1200)
    wire_car_prop.wire_car(big, big.comp, seed="night drive", width=2400)
    ratio = max(float(s.get("strokeWidth")) for s in shapes(big)) / max(
        float(s.get("strokeWidth")) for s in shapes(small)
    )
    assert math.isclose(ratio, 2.0, rel_tol=0.02)


@pytest.mark.parametrize(
    ("kwargs", "message"),
    [
        ({"palette": "neon"}, "unknown palette 'neon'"),
        ({"view": "top"}, "unknown view 'top'"),
        ({"width": 50}, "width must be from"),
        ({"width": math.nan}, "width must be a finite number"),
        ({"width": "900"}, "width must be a finite number"),
        ({"at": (1.0,)}, "at is an"),
        ({"at": (math.inf, 0.0)}, "at x must be a finite number"),
        ({"weight": 0}, "weight must be above 0"),
        ({"weight": True}, "weight must be a finite number"),
        ({"seed": ""}, "seed is a non-empty"),
        ({"seed": 1.5}, "seed is a non-empty"),
        ({"seed": True}, "seed is a non-empty"),
    ],
)
def test_the_prop_refuses_what_it_cannot_draw_and_draws_nothing(kwargs, message):
    cv = canvas()
    with pytest.raises(WireCarError, match=message):
        wire_car_prop.wire_car(cv, cv.comp, **{"width": 400, **kwargs})
    assert shapes(cv) == []


def test_the_car_has_the_drivers_head_and_the_wheel_as_anchors_and_a_view_hands_them_back_in_pixels():
    car = wire_car.make_car("monday")
    assert set(car.anchors) == {"driver-head", "steering-wheel"}
    drawing = wire_car.project(car, "side", width=SMALL)
    assert set(drawing.anchors) == set(car.anchors) | {"hub-front", "hub-rear"} and drawing.scale > 0
    head, wheel = drawing.anchors["driver-head"], drawing.anchors["steering-wheel"]
    assert 0 < head[0] < drawing.width and head[1] < wheel[1]  # the head is above the wheel's hub


def test_a_close_up_goes_round_an_anchor_at_a_scale_the_whole_car_does_not_have():
    car = wire_car.make_car("monday")
    whole = wire_car.project(car, "side", width=SMALL)
    close = wire_car.project(car, "side", width=SMALL, around="driver-head", span=1.25, height=400)
    assert (close.width, close.height) == (SMALL, 400)
    assert close.scale == pytest.approx(SMALL / 1.25) and close.scale > whole.scale
    assert close.anchors["driver-head"] == pytest.approx((SMALL / 2, 200.0))


@pytest.mark.parametrize(
    ("kwargs", "message"),
    [
        ({"around": "boot", "span": 1.0, "height": 300}, "unknown anchor 'boot'.*driver-head"),
        ({"around": "driver-head", "height": 300}, "span is a number of metres"),
        ({"around": "driver-head", "span": 1.0}, "height is a whole number of pixels"),
        ({"span": 1.0}, "name the anchor"),
    ],
)
def test_a_close_up_that_cannot_be_framed_is_refused_for_the_car(kwargs, message):
    with pytest.raises(WireCarError, match=message):
        wire_car.project(wire_car.make_car("monday"), "side", width=SMALL, **kwargs)


def test_the_prop_gives_the_anchor_where_the_drawn_car_puts_it():
    shot = {"at": (500.0, 900.0), "width": SMALL, "seed": "monday", "view": "side"}
    found = wire_car_prop.anchor("driver-head", **shot, around="driver-head", span=1.25, height=400)
    assert found.scale == pytest.approx(SMALL / 1.25)
    assert (found.x, found.y) == pytest.approx((500.0, 900.0))  # a close-up round the head puts it on the centre
    far = wire_car_prop.anchor("steering-wheel", **shot)
    assert far.scale < found.scale


def test_the_prop_refuses_an_anchor_the_car_does_not_have_and_a_seed_it_cannot_read():
    with pytest.raises(WireCarError, match="unknown anchor 'roof'"):
        wire_car_prop.anchor("roof", width=SMALL)
    with pytest.raises(WireCarError, match="seed is a non-empty text"):
        wire_car_prop.anchor("driver-head", width=SMALL, seed="")


def test_the_prop_draws_a_close_up_and_keeps_only_the_rows_asked_for():
    shot = {"width": SMALL, "seed": "monday", "view": "side", "around": "driver-head", "span": 1.25, "height": 400}
    whole, upper = canvas(), canvas()
    wire_car_prop.wire_car(whole, whole.comp, **shot)
    wire_car_prop.wire_car(upper, upper.comp, **shot, rows=(-200.0, 0.0))
    numbers = [float(n) for s in shapes(upper) for n in s.get("path").replace("M", " ").replace("L", " ").split()]
    ys = numbers[1::2]
    assert shapes(upper) and max(ys) <= 0.5 and len(shapes(upper)) <= len(shapes(whole))


def test_the_prop_refuses_rows_that_are_not_a_top_above_a_bottom():
    cv = canvas()
    with pytest.raises(WireCarError, match="rows"):
        wire_car_prop.wire_car(cv, cv.comp, width=SMALL, rows=(10.0, -10.0))
    assert shapes(cv) == []


def test_a_frame_on_empty_space_is_refused_by_the_shared_view_error():
    with pytest.raises(WireError, match="frame shows no line"):
        wire_car.project(wire_car.make_car("monday"), "side", width=SMALL, around="driver-head", span=0.01, height=300)


def test_every_exterior_surface_of_a_car_has_a_material_and_the_wheels_and_the_seats_are_not_paint():
    car = wire_car.make_car("monday")
    assert len(car.mask_kinds) == len(car.masks)
    assert {PAINT, TIRE, DARK} <= set(car.mask_kinds) and set(car.mask_kinds) <= {PAINT, TIRE, DARK}
    lit = wire_car.project(car, "side", width=SMALL, light=(-0.55, 0.46, 0.70))
    codes = {c // BANDS for c in set(lit.cel) if c != NO_CEL}
    assert {PAINT, TIRE, LEATHER, TRIM} <= codes  # the seats show through the cabin's open glass


def test_a_car_seen_with_no_light_has_no_cel_and_a_light_changes_no_stroke():
    car = wire_car.make_car("monday")
    plain = wire_car.project(car, "side", width=SMALL)
    lit = wire_car.project(car, "side", width=SMALL, light=(0, 1, 1))
    assert plain.cel == b"" and len(lit.cel) == lit.width * lit.height
    assert plain.strokes == lit.strokes


def test_a_light_that_is_no_direction_is_refused_for_the_car():
    with pytest.raises(WireError, match="light is a direction"):
        wire_car.project(wire_car.make_car("monday"), "side", width=SMALL, light=(0, 0, 0))


LIGHT = (-0.55, 0.46, 0.70)


def test_the_plate_of_a_car_lies_where_its_strokes_do_and_is_a_picture_of_its_size():
    shot = {"at": (500.0, 900.0), "width": SMALL, "seed": "monday", "view": "side"}
    plate = wire_car_prop.plate(LIGHT, **shot)
    drawing = wire_car.project(wire_car.make_car("monday"), "side", width=SMALL, light=LIGHT)
    assert (plate.width, plate.height) == (drawing.width, drawing.height)
    assert (plate.x, plate.y) == (500.0 - plate.width / 2, 900.0 - plate.height / 2)
    assert plate.png.startswith(b"\x89PNG")


def test_a_plate_and_the_strokes_drawn_with_its_light_share_one_projection():
    shot = {"at": (500.0, 900.0), "width": SMALL, "seed": "shared", "view": "side"}
    wire_car_prop._drawing.cache_clear()
    wire_car_prop.plate(LIGHT, **shot)
    cv = canvas()
    wire_car_prop.wire_car(cv, cv.comp, light=LIGHT, **shot)
    wire_car_prop.anchor("driver-head", light=LIGHT, **shot)
    info = wire_car_prop._drawing.cache_info()
    assert (info.misses, info.hits) == (1, 2)


def test_a_plate_keeps_only_the_rows_asked_for_and_refuses_what_it_cannot_paint():
    shot = {"at": (500.0, 900.0), "width": SMALL, "seed": "monday", "view": "side"}
    whole, upper = wire_car_prop.plate(LIGHT, **shot), wire_car_prop.plate(LIGHT, rows=(-1e5, 0.0), **shot)
    assert upper.png != whole.png and (upper.x, upper.y) == (whole.x, whole.y)
    with pytest.raises(WireCarError, match="unknown palette 'day'"):
        wire_car_prop.plate(LIGHT, palette="day", **shot)
    with pytest.raises(WireCarError, match="rows"):
        wire_car_prop.plate(LIGHT, rows=(5.0, 1.0), **shot)


# -- perspective and the wheels as layers of their own -------------------------------------------------------------
def ink_points(drawing, inks=None):
    return [p for ink, lines in drawing.strokes.items() if inks is None or ink in inks for line in lines for p in line]


def test_a_car_seen_in_perspective_differs_from_the_flat_view_and_shows_the_nearer_side_larger():
    car = wire_car.make_car("monday")
    flat = wire_car.project(car, "front-quarter", width=SMALL)
    seen = wire_car.project(car, "front-quarter", width=SMALL, distance=7.0)
    assert flat.strokes != seen.strokes and ink_points(seen)
    near = wire_car.project(car, "front-quarter", width=SMALL, distance=4.5)
    assert near.strokes != seen.strokes  # the nearer the camera, the more the car is foreshortened


@pytest.mark.parametrize("distance", [0, -3.0, math.nan, True, "7"])
def test_a_distance_that_is_not_a_positive_number_is_refused_for_the_car(distance):
    with pytest.raises(WireError, match="distance"):
        wire_car.project(wire_car.make_car("monday"), "side", width=SMALL, distance=distance)


def test_a_camera_inside_the_car_is_refused_and_one_outside_it_draws():
    car = wire_car.make_car("monday")
    with pytest.raises(WireError, match="inside"):
        wire_car.project(car, "side", width=SMALL, distance=0.5)
    assert wire_car.project(car, "side", width=SMALL, distance=8.0).strokes


def test_the_hubs_are_where_the_wheels_of_the_side_the_camera_sees_are_and_a_close_up_can_go_round_one():
    car = wire_car.make_car("monday")
    side = wire_car.project(car, "side", width=SMALL)
    (fx, fy), (rx, ry) = side.anchors["hub-front"], side.anchors["hub-rear"]
    assert abs(fy - ry) < 1.0 and fx != rx  # the same height, an axle apart
    other = wire_car.project(car, "side", width=SMALL, yaw=180.0)
    assert other.anchors["hub-front"] != side.anchors["hub-front"]  # the far side's wheel is another one
    closer = wire_car.project(car, "side", width=SMALL, around="hub-front", span=1.0, height=SMALL)
    assert closer.strokes and closer.scale > side.scale


def test_every_wheel_has_its_own_run_of_surfaces_and_its_hub_in_the_cars_axes():
    car = wire_car.make_car("monday")
    assert set(car.wheel_masks) == set(car.hubs) == {f"Wheel {w} {s}" for w in ("front", "rear") for s in "LR"}
    spans = sorted(car.wheel_masks.values())
    assert all(a < b for a, b in spans) and all(x[1] <= y[0] for x, y in zip(spans, spans[1:], strict=False))
    assert all(car.mask_kinds[i] in (TIRE, DARK) for a, b in spans for i in range(a, b))


@pytest.mark.parametrize("wheels", ["front", "rear", "body", "all"])
def test_each_set_of_wheels_draws_something_and_a_wheel_less_body_has_fewer_lines(wheels):
    car = wire_car.make_car("monday")
    drawing = wire_car.project(car, "side", width=SMALL, light=LIGHT, wheels=wheels)
    assert ink_points(drawing)
    whole = ink_points(wire_car.project(car, "side", width=SMALL, light=LIGHT))
    assert len(ink_points(drawing)) <= len(whole)


def test_the_body_leaves_a_hole_where_a_wheel_is_and_the_wheels_fill_it():
    car = wire_car.make_car("monday")
    whole = wire_car.project(car, "side", width=SMALL, light=LIGHT)
    body = wire_car.project(car, "side", width=SMALL, light=LIGHT, wheels="body")
    front = wire_car.project(car, "side", width=SMALL, light=LIGHT, wheels="front")
    rear = wire_car.project(car, "side", width=SMALL, light=LIGHT, wheels="rear")
    assert (body.width, body.height) == (whole.width, whole.height) == (front.width, front.height)
    holes = [i for i, (a, b) in enumerate(zip(whole.cel, body.cel, strict=True)) if a != NO_CEL and b == NO_CEL]
    assert holes and all(whole.cel[i] // BANDS in (TIRE, DARK, PAINT) for i in holes)
    drawn = {i for i, c in enumerate(front.cel) if c != NO_CEL} | {i for i, c in enumerate(rear.cel) if c != NO_CEL}
    assert set(holes) <= drawn  # every pixel the body gave up is one a wheel layer paints


def test_the_body_without_its_wheels_keeps_no_wheel_line_nor_wheel_silhouette():
    car = wire_car.make_car("monday")
    body = wire_car.project(car, "side", width=SMALL, wheels="body")
    whole = wire_car.project(car, "side", width=SMALL)
    assert sum(map(len, body.strokes.get("tire", ()))) < sum(
        map(len, whole.strokes.get("tire", ()))
    ) or not body.strokes.get("tire")
    assert "alloy" not in body.strokes or len(body.strokes["alloy"]) < len(whole.strokes["alloy"])


def test_a_wheel_set_the_car_does_not_have_is_refused_naming_the_choices():
    with pytest.raises(WireCarError, match="wheels is one of all, body, front, rear"):
        wire_car.project(wire_car.make_car("monday"), "side", width=SMALL, wheels="middle")


def test_the_prop_draws_a_wheel_layer_in_perspective_and_gives_the_hub_where_it_is():
    shot = {"at": (500.0, 900.0), "width": SMALL, "seed": "monday", "view": "side", "distance": 7.0}
    cv = canvas()
    group = wire_car_prop.wire_car(cv, cv.comp, wheels="front", **shot)
    assert group is not None
    hub = wire_car_prop.anchor("hub-front", **shot)
    assert hub.scale > 0 and hub.x != 500.0 or hub.y != 900.0
    plate = wire_car_prop.plate(LIGHT, wheels="front", **shot)
    assert plate.png.startswith(b"\x89PNG")


def test_the_hub_scale_in_perspective_is_the_pixels_in_a_metre_where_the_wheel_is():
    flat = wire_car_prop.anchor("hub-front", at=(500.0, 900.0), width=SMALL, seed="monday", view="side")
    near = wire_car_prop.anchor("hub-front", at=(500.0, 900.0), width=SMALL, seed="monday", view="side", distance=4.5)
    assert flat.scale != near.scale  # a wheel nearer than the car's middle is bigger than the focus's scale


def test_a_positive_spin_rolls_the_car_forward_so_the_top_of_a_wheel_goes_towards_the_nose():
    (top,) = wire_car._turned([(2.0, 0.34 + 0.3, 0.8)], 2.0, 0.34, 0.1)
    assert top[0] < 2.0 and top[2] == 0.8 and top[1] < 0.64  # towards the nose (image left), the width unchanged


def test_no_spin_is_the_car_as_it_was_and_a_whole_turn_is_the_same_wheel():
    car = wire_car.make_car("monday")
    plain = wire_car.project(car, "front-quarter", width=SMALL, wheels="front")
    assert wire_car.project(car, "front-quarter", width=SMALL, wheels="front", spin=0.0).strokes == plain.strokes
    turned = wire_car.project(car, "front-quarter", width=SMALL, wheels="front", spin=2 * math.pi)
    assert set(turned.strokes) == set(plain.strokes)
    assert all(
        a == pytest.approx(b, abs=1e-3)
        for ink in plain.strokes
        for la, lb in zip(plain.strokes[ink], turned.strokes[ink], strict=True)
        for a, b in zip(la, lb, strict=True)
    )


def test_a_turned_wheel_changes_the_wheels_and_leaves_the_body_alone():
    car = wire_car.make_car("monday")
    front = wire_car.project(car, "front-quarter", width=SMALL, light=LIGHT, wheels="front")
    spun = wire_car.project(car, "front-quarter", width=SMALL, light=LIGHT, wheels="front", spin=0.4)
    assert spun.strokes != front.strokes
    body = wire_car.project(car, "front-quarter", width=SMALL, light=LIGHT, wheels="body")
    body_spun = wire_car.project(car, "front-quarter", width=SMALL, light=LIGHT, wheels="body", spin=0.4)
    assert body_spun.strokes == body.strokes  # no wheel line is in the body layer, so nothing in it moves
    differing = sum(a != b for a, b in zip(body.cel, body_spun.cel, strict=True))
    assert differing < 0.01 * len(body.cel)  # the discs that close the wheels are round: the hole stays where it is


@pytest.mark.parametrize("spin", [math.nan, math.inf, True, "1"])
def test_a_spin_that_is_not_a_number_of_radians_is_refused(spin):
    with pytest.raises(WireCarError, match="spin"):
        wire_car.project(wire_car.make_car("monday"), "side", width=SMALL, spin=spin)


def test_the_prop_draws_the_wheel_at_each_spin_apart_and_caches_each_projection_once():
    shot = {"at": (500.0, 900.0), "width": SMALL, "seed": "monday", "view": "front-quarter", "wheels": "front"}
    wire_car_prop._drawing.cache_clear()
    for spin in (0.0, 0.2, 0.2):
        wire_car_prop.plate(LIGHT, spin=spin, **shot)
    assert wire_car_prop._drawing.cache_info().misses == 2


def test_a_car_knows_how_many_spokes_its_wheels_have_and_the_same_seed_gives_the_same_count():
    counts = {wire_car.make_car(seed).spokes for seed in range(12)}
    assert counts <= {5, 6, 7, 8, 9} and len(counts) > 1
    assert wire_car.make_car("monday").spokes == wire_car.make_car("monday").spokes


CLOSE = {"at": (540.0, 990.0), "width": 1080, "seed": "monday", "view": "side", "around": "driver-head", "span": 1.25}


def test_the_edge_of_the_cars_door_is_found_under_the_drivers_head_and_cuts_the_plate_there():
    shot = {**CLOSE, "height": 1920, "distance": 4.0, "light": LIGHT}
    head = wire_car_prop.anchor("driver-head", **shot)
    row, slope = wire_car_prop.edge("driver-head", 0.3, 0.6, **shot)
    assert 0 < row + 990.0 - head.y < 0.5 * head.scale  # the door's top is a little under his head
    assert abs(slope) < 0.2  # from the side it is nearly level
    plate = {k: v for k, v in shot.items() if k != "light"}
    above = wire_car_prop.plate(LIGHT, rows=(-1e5, row), tilt=slope, **plate)
    below = wire_car_prop.plate(LIGHT, rows=(row, 1e5), tilt=slope, **plate)
    assert above.png != below.png


def test_an_edge_needs_the_light_that_gives_the_car_its_surfaces():
    with pytest.raises(WireCarError, match="no cel raster"):
        wire_car_prop.edge("driver-head", 0.3, 0.6, height=1920, **CLOSE)
