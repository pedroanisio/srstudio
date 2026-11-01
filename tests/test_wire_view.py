"""The hidden-line view the wire models share, on a box small enough to know every answer."""

from __future__ import annotations

import math

import pytest

from srstudio.wire_view import BANDS, HOLE, MARGIN, NO_CEL, Drawing, Frame, WireError, frame_of, hidden_line_view

W = 400


def quad(z, x0=-1.0, x1=1.0, y0=0.0, y1=1.0):
    """A face of the box facing the camera at depth ``z`` (a larger z is nearer when looking from yaw 0)."""
    return ((x0, y0, z), (x1, y0, z), (x1, y1, z), (x0, y1, z))


def look(lines, masks, **kw):
    options = {"view": "t", "yaw": 0.0, "elevation": 0.0, "width": W, "inks": ("a", "b"), "slack": lambda _s: 0.01}
    return hidden_line_view(lines, masks, **{**options, **kw})


def spans(drawing, ink):
    return [(min(x for x, _ in line), max(x for x, _ in line)) for line in drawing.strokes.get(ink, ())]


def test_a_line_in_front_of_a_face_is_kept_and_one_behind_it_is_hidden():
    lines = {
        ("front", "a"): [[(-0.5, 0.5, 1.0), (0.5, 0.5, 1.0)]],
        ("back", "b"): [[(-0.5, 0.5, -1.0), (0.5, 0.5, -1.0)]],
    }
    drawing = look(lines, [quad(0.0)])
    assert "a" in drawing.strokes and "b" not in drawing.strokes


def test_a_line_that_leaves_the_face_is_cut_where_the_face_ends():
    # Behind the face from x=-1 to x=1, then free to x=3: the picture frames x from -1 to 3.
    drawing = look({("p", "a"): [[(-1.0, 0.5, -1.0), (3.0, 0.5, -1.0)]]}, [quad(0.0)])
    ((lo, hi),) = spans(drawing, "a")
    centre = (W - 2 * MARGIN) / 4  # one metre in pixels
    assert hi == pytest.approx(W - MARGIN, abs=1.5)
    assert lo == pytest.approx(MARGIN + 2 * centre, abs=3.0)  # the visible part starts at x = 1, not at x = -1


def test_a_line_within_the_slack_of_the_face_counts_as_on_it():
    on = {("p", "a"): [[(-0.5, 0.5, -0.005), (0.5, 0.5, -0.005)]]}
    assert "a" in look(on, [quad(0.0)], slack=lambda _s: 0.01).strokes
    assert "a" not in look(on, [quad(0.0)], slack=lambda _s: 0.001).strokes


def test_the_slack_is_given_the_pixels_per_metre_of_the_picture():
    seen = []
    look({("p", "a"): [[(-1.0, 0.0, 0.0), (1.0, 0.0, 0.0)]]}, [], slack=lambda scale: seen.append(scale) or 0.0)
    assert seen == [(W - 2 * MARGIN) / 2.0]


def test_the_picture_is_as_wide_as_asked_and_as_tall_as_the_model_needs():
    drawing = look({("p", "a"): [[(-1.0, 0.0, 0.0), (1.0, 0.0, 0.0), (1.0, 0.5, 0.0)]]}, [])
    assert isinstance(drawing, Drawing) and drawing.width == W
    assert drawing.height == round(0.5 * (W - 2 * MARGIN) / 2) + 2 * MARGIN


def test_the_strokes_follow_the_order_of_the_inks_asked_for():
    lines = {("p", "b"): [[(0.0, 0.0, 0.0), (1.0, 0.0, 0.0)]], ("q", "a"): [[(0.0, 1.0, 0.0), (1.0, 1.0, 0.0)]]}
    assert list(look(lines, []).strokes) == ["a", "b"]
    assert list(look(lines, [], inks=("b", "a")).strokes) == ["b", "a"]


def test_the_edge_where_a_facing_facet_meets_one_turned_away_is_a_silhouette_in_the_contour_ink():
    facing = ((-1.0, 0.0, 1.0), (0.0, 0.0, 1.0), (0.0, 1.0, 1.0), (-1.0, 1.0, 1.0))
    turned = ((0.0, 1.0, 1.0), (0.0, 0.0, 1.0), (-0.5, 0.0, 0.0), (-0.5, 1.0, 0.0))  # folds back over the first
    anchor = {("p", "b"): [[(-1.0, 0.5, 5.0), (1.0, 0.5, 5.0)]]}  # frames x from -1 to 1
    contours = look(anchor, [facing, turned], contour_ink="a")
    ((lo, hi),) = spans(contours, "a")
    assert hi - lo < 1.0 and lo == pytest.approx(W / 2, abs=1.0)  # the edge at x = 0 is straight up, mid-picture
    flat = look(anchor, [facing, ((0.0, 0.0, 1.0), (1.0, 0.0, 1.0), (1.0, 1.0, 1.0), (0.0, 1.0, 1.0))], contour_ink="a")
    assert "a" not in flat.strokes  # two facets that both face the camera share no silhouette


def test_extra_points_widen_the_framing_without_drawing_anything():
    plain = look({("p", "a"): [[(0.0, 0.0, 0.0), (1.0, 0.0, 0.0)]]}, [])
    framed = look({("p", "a"): [[(0.0, 0.0, 0.0), (1.0, 0.0, 0.0)]]}, [], extra_points=[(-3.0, 0.0, 0.0)])
    assert spans(framed, "a")[0][1] - spans(framed, "a")[0][0] < spans(plain, "a")[0][1] - spans(plain, "a")[0][0]


def test_a_model_with_no_line_or_no_width_from_here_is_refused():
    with pytest.raises(WireError, match="no line to draw"):
        look({}, [quad(0.0)])
    with pytest.raises(WireError, match="no width"):
        look({("p", "a"): [[(0.0, 0.0, -1.0), (0.0, 1.0, 1.0)]]}, [])  # a line straight at the camera


def test_a_silhouette_edge_outside_the_framing_of_the_lines_is_left_out_not_read_off_the_raster():
    facing = ((-1.0, 0.0, 1.0), (0.0, 0.0, 1.0), (0.0, 5.0, 1.0), (-1.0, 5.0, 1.0))
    turned = ((0.0, 5.0, 1.0), (0.0, 0.0, 1.0), (-0.5, 0.0, 0.0), (-0.5, 5.0, 0.0))
    anchor = {("p", "b"): [[(-1.0, 0.5, 5.0), (1.0, 0.5, 5.0)]]}  # frames only a hair of height
    drawing = look(anchor, [facing, turned], contour_ink="a")
    assert all(0 <= y < drawing.height for line in drawing.strokes.get("a", ()) for _, y in line)


def test_a_close_up_is_seen_at_the_frames_scale_round_its_centre_and_only_what_it_frames_is_drawn():
    # A line three metres either side of the middle, in a picture two metres across: it is cut at both edges.
    frame = Frame((0.0, 0.5, 0.0), 2.0, 100)
    drawing = look({("p", "a"): [[(-3.0, 0.5, 0.0), (3.0, 0.5, 0.0)]]}, [], frame=frame)
    assert (drawing.width, drawing.height, drawing.scale) == (W, 100, W / 2.0)
    ((lo, hi),) = spans(drawing, "a")
    assert lo == pytest.approx(0.0, abs=3.0) and hi == pytest.approx(W, abs=3.0)
    assert {round(y) for line in drawing.strokes["a"] for _, y in line} == {50}


def test_a_frame_that_shows_no_line_is_refused_rather_than_drawn_empty():
    far = Frame((50.0, 0.5, 0.0), 2.0, 100)
    with pytest.raises(WireError, match="frame shows no line"):
        look({("p", "a"): [[(-1.0, 0.5, 0.0), (1.0, 0.5, 0.0)]]}, [], frame=far)


def test_the_anchors_come_back_in_the_pictures_pixels_in_a_close_up_and_in_a_fitted_view():
    lines = {("p", "a"): [[(-1.0, 0.0, 0.0), (1.0, 0.0, 0.0), (1.0, 1.0, 0.0)]]}
    anchors = {"middle": (0.0, 0.5, 0.0), "off": (5.0, 0.5, 0.0)}
    level = {("p", "a"): [[(-0.5, 0.5, 0.0), (0.5, 0.5, 0.0)]]}
    close = look(level, [], anchors=anchors, frame=Frame((0.0, 0.5, 0.0), 2.0, 100))
    assert close.anchors["middle"] == pytest.approx((W / 2, 50.0))
    assert close.anchors["off"][0] > W  # a point the picture does not frame lies outside it
    fitted = look(lines, [], anchors=anchors)
    assert fitted.scale == (W - 2 * MARGIN) / 2.0
    assert fitted.anchors["middle"][0] == pytest.approx(W / 2)


def test_a_view_with_no_anchors_has_none():
    assert look({("p", "a"): [[(-1.0, 0.0, 0.0), (1.0, 0.0, 0.0)]]}, []).anchors == {}


ANCHORS = {"head": (0.0, 1.0, 0.0)}


def test_a_close_up_asks_for_no_frame_when_it_names_no_anchor():
    assert frame_of(ANCHORS, None, None, None, WireError) is None
    assert frame_of(ANCHORS, "head", 1.5, 200, WireError) == Frame((0.0, 1.0, 0.0), 1.5, 200)


@pytest.mark.parametrize(
    ("around", "span", "height", "message"),
    [
        (None, 1.0, None, "name the anchor"),
        (None, None, 100, "name the anchor"),
        ("hand", 1.0, 100, "unknown anchor 'hand'.*head"),
        (3, 1.0, 100, "unknown anchor 3"),
        ("head", None, 100, "span is a number of metres above 0"),
        ("head", 0, 100, "span is a number of metres above 0"),
        ("head", -1.0, 100, "span is a number of metres above 0"),
        ("head", math.nan, 100, "span is a number of metres above 0"),
        ("head", True, 100, "span is a number of metres above 0"),
        ("head", "1", 100, "span is a number of metres above 0"),
        ("head", 1.0, None, "height is a whole number of pixels"),
        ("head", 1.0, 0, "height is a whole number of pixels"),
        ("head", 1.0, 99.5, "height is a whole number of pixels"),
        ("head", 1.0, True, "height is a whole number of pixels"),
    ],
)
def test_a_close_up_that_cannot_be_framed_is_refused_and_says_why(around, span, height, message):
    with pytest.raises(WireError, match=message):
        frame_of(ANCHORS, around, span, height, WireError)


def middle(drawing):
    return drawing.cel[(drawing.height // 2) * drawing.width + drawing.width // 2]


@pytest.mark.parametrize(
    ("light", "tone"), [((0, 0, 1), 3), ((1, 0, 1), 2), ((1, 0, 0.3), 1), ((0, 1, 0), 0), ((0, 0, -1), 0)]
)
def test_a_face_takes_the_tone_the_light_gives_it_and_a_face_turned_from_the_light_is_darkest(light, tone):
    drawing = look({("p", "a"): [[(-1.0, 0.5, 0.0), (1.0, 0.5, 0.0)]]}, [quad(0.0)], light=light)
    assert len(drawing.cel) == drawing.width * drawing.height and middle(drawing) == tone


def test_the_side_of_a_face_that_looks_at_the_lens_is_the_one_that_is_lit_whichever_way_its_quad_is_wound():
    flipped = tuple(reversed(quad(0.0)))
    drawing = look({("p", "a"): [[(-1.0, 0.5, 0.0), (1.0, 0.5, 0.0)]]}, [flipped], light=(0, 0, 1))
    assert middle(drawing) == 3


def test_the_cel_raster_says_the_material_of_the_nearest_surface_and_is_empty_where_there_is_none():
    near, far = quad(1.0, -0.5, 0.5, 0.25, 0.75), quad(0.0)
    drawing = look({("p", "a"): [[(-1.0, 0.5, 0.0), (1.0, 0.5, 0.0)]]}, [far, near], kinds=[0, 2], light=(0, 0, 1))
    assert middle(drawing) == 2 * BANDS + 3  # the near face, of material 2, hides the far one
    assert drawing.cel[MARGIN * drawing.width + MARGIN - 1] == NO_CEL  # outside the box
    corner = (drawing.height // 2) * drawing.width + MARGIN + 5
    assert drawing.cel[corner] == 0 * BANDS + 3  # the far face, where the near one is not


def test_a_view_with_no_light_has_no_cel_raster():
    assert look({("p", "a"): [[(-1.0, 0.5, 0.0), (1.0, 0.5, 0.0)]]}, [quad(0.0)]).cel == b""


@pytest.mark.parametrize(
    ("kw", "message"),
    [
        ({"kinds": [0]}, "name the light"),
        ({"light": (1, 2)}, "light is a direction of three finite numbers"),
        ({"light": (0, 0, 0)}, "light is a direction of three finite numbers"),
        ({"light": (0, math.nan, 1)}, "light is a direction of three finite numbers"),
        ({"light": ("a", 0, 1)}, "light is a direction of three finite numbers"),
        ({"light": (0, 0, 1), "kinds": [0, 0]}, "one material for each of the 1 surfaces"),
        ({"light": (0, 0, 1), "kinds": [-2]}, "a material is a whole number"),
        ({"light": (0, 0, 1), "kinds": [63]}, "a material is a whole number"),
        ({"light": (0, 0, 1), "kinds": [True]}, "a material is a whole number"),
        ({"light": (0, 0, 1), "kinds": [1.5]}, "a material is a whole number"),
    ],
)
def test_a_shading_that_cannot_be_made_is_refused_and_says_why(kw, message):
    with pytest.raises(WireError, match=message):
        look({("p", "a"): [[(-1.0, 0.5, 0.0), (1.0, 0.5, 0.0)]]}, [quad(0.0)], **kw)


def test_a_face_seen_edge_on_takes_the_darkest_tone_rather_than_failing():
    edge = ((0.0, 0.0, 0.0), (0.5, 0.0, 0.0), (1.0, 0.0, 0.0), (0.5, 0.0, 0.0))  # a quad with no area
    drawing = look({("p", "a"): [[(0.0, 0.0, 0.0), (1.0, 0.0, 0.0)]]}, [edge], light=(0, 0, 1))
    assert set(drawing.cel) <= {0, NO_CEL}


# -- perspective: the camera stands ``distance`` metres from the model's origin, looking at it ------------------------
D = 5.0


def width_of(drawing, ink):
    ((lo, hi),) = spans(drawing, ink)
    return hi - lo


def test_in_perspective_the_nearer_of_two_equal_lines_is_the_wider_by_the_ratio_of_their_distances():
    lines = {
        ("near", "a"): [[(-1.0, 0.3, 1.0), (1.0, 0.3, 1.0)]],
        ("far", "b"): [[(-1.0, 0.6, -1.0), (1.0, 0.6, -1.0)]],
    }
    flat = look(lines, [])
    assert width_of(flat, "a") == pytest.approx(width_of(flat, "b"), rel=1e-3)  # orthographic: depth changes nothing
    seen = look(lines, [], distance=D)
    assert width_of(seen, "a") / width_of(seen, "b") == pytest.approx((D + 1) / (D - 1), rel=1e-2)


def test_a_line_on_a_tilted_face_is_seen_all_along_it_because_depth_is_interpolated_for_the_lens():
    tilted = ((-1.0, 0.0, -1.0), (1.0, 0.0, 1.0), (1.0, 1.0, 1.0), (-1.0, 1.0, -1.0))
    on = {("p", "a"): [[(-1.0, 0.5, -1.0), (1.0, 0.5, 1.0)]]}
    ((lo, hi),) = spans(look(on, [tilted], distance=2.5, slack=lambda _s: 0.01), "a")
    flat = spans(look(on, [], distance=2.5), "a")[0]
    assert hi - lo == pytest.approx(flat[1] - flat[0], abs=3.0)  # no gap where the face and the line disagree


def test_in_perspective_a_line_behind_a_face_is_hidden_and_one_in_front_is_kept():
    lines = {
        ("front", "a"): [[(-0.5, 0.5, 1.0), (0.5, 0.5, 1.0)]],
        ("back", "b"): [[(-0.5, 0.5, -1.0), (0.5, 0.5, -1.0)]],
    }
    drawing = look(lines, [quad(0.0)], distance=D)
    assert "a" in drawing.strokes and "b" not in drawing.strokes


def test_the_slack_is_in_metres_whatever_the_distance():
    near = {("p", "a"): [[(-0.5, 0.5, -0.005), (0.5, 0.5, -0.005)]]}
    assert "a" in look(near, [quad(0.0)], distance=D, slack=lambda _s: 0.01).strokes
    assert "a" not in look(near, [quad(0.0)], distance=D, slack=lambda _s: 0.001).strokes


def test_the_nearer_surface_takes_the_pixel_in_the_cel_raster_in_perspective():
    far, near = quad(-1.0), quad(1.0, x0=-0.5, x1=0.5)
    drawing = look(
        {("p", "a"): [[(-1.0, 0.0, 0.0), (1.0, 1.0, 0.0)]]}, [far, near], distance=D, light=(0, 0, 1), kinds=[0, 1]
    )
    row = drawing.height // 2
    centre = drawing.cel[row * W + W // 2]
    edge = drawing.cel[row * W + W // 2 + 140]  # 0.7 m out: inside the far face (0.83 m), outside the near (0.63 m)
    assert centre // BANDS == 1 and edge // BANDS == 0


def test_anchors_report_the_pixels_in_a_metre_where_they_are_not_where_the_focus_is():
    drawing = look(
        {("p", "a"): [[(-1.0, 0.0, 0.0), (1.0, 1.0, 0.0)]]},
        [],
        distance=D,
        anchors={"near": (0.0, 0.5, 1.0), "far": (0.0, 0.5, -1.0)},
    )
    assert drawing.anchor_scale["near"] / drawing.anchor_scale["far"] == pytest.approx((D + 1) / (D - 1), rel=1e-6)
    ortho = look({("p", "a"): [[(-1.0, 0.0, 0.0), (1.0, 1.0, 0.0)]]}, [], anchors={"p": (0.0, 0.5, 1.0)})
    assert ortho.anchor_scale == {"p": ortho.scale}


def test_a_close_up_in_perspective_has_the_asked_span_at_the_centre_depth():
    frame = Frame((0.0, 0.5, 1.0), 2.0, 300)
    drawing = look({("p", "a"): [[(-1.0, 0.5, 1.0), (1.0, 0.5, 1.0)]]}, [], distance=D, frame=frame)
    assert width_of(drawing, "a") == pytest.approx(W, abs=2.0)  # 2 m at the centre's depth fill the 2 m span


@pytest.mark.parametrize("bad", [0, -1.0, math.nan, math.inf, True, "5"])
def test_a_distance_that_is_not_a_positive_number_is_refused(bad):
    with pytest.raises(WireError, match="distance"):
        look({("p", "a"): [[(-1.0, 0.0, 0.0), (1.0, 0.0, 0.0)]]}, [], distance=bad)


def test_a_camera_inside_the_model_is_refused_and_one_at_the_surface_too():
    lines = {("p", "a"): [[(-1.0, 0.0, 0.0), (1.0, 0.0, 2.0)]]}
    for inside in (1.0, 2.0, 2.05):
        with pytest.raises(WireError, match="inside"):
            look(lines, [], distance=inside)
    assert "a" in look(lines, [], distance=4.0).strokes


def test_a_hole_hides_what_is_behind_it_but_is_not_in_the_cel_raster():
    drawing = look(
        {("p", "a"): [[(-0.5, 0.5, -1.0), (0.5, 0.5, -1.0)]]},
        [quad(-1.0, x0=-2.0, x1=2.0), quad(0.0)],
        light=(0, 0, 1),
        kinds=[0, HOLE],
    )
    assert "a" not in drawing.strokes  # the hole is in front of the line
    row = drawing.height // 2
    assert drawing.cel[row * W + W // 2] == NO_CEL  # and not painted: the layer under it shows


def test_a_quiet_surface_throws_no_silhouette_line_and_the_others_still_do():
    facing = ((-1.0, 0.0, 1.0), (0.0, 0.0, 1.0), (0.0, 1.0, 1.0), (-1.0, 1.0, 1.0))
    turned = ((0.0, 1.0, 1.0), (0.0, 0.0, 1.0), (-0.5, 0.0, 0.0), (-0.5, 1.0, 0.0))
    lines = {("p", "b"): [[(-1.0, 0.5, 5.0), (1.0, 0.5, 5.0)]]}
    assert "a" in look(lines, [facing, turned], contour_ink="a").strokes
    assert "a" not in look(lines, [facing, turned], contour_ink="a", quiet=[1]).strokes
    assert "a" not in look(lines, [facing, turned], contour_ink="a", quiet=[0]).strokes  # the edge is shared: both ends


def test_a_light_in_perspective_lights_the_face_that_faces_the_camera_not_the_depth_axis():
    # a face at the side of the view, seen from a camera at (0, 0, D) and not along the depth axis
    wall = ((3.0, 0.0, 0.0), (3.0, 0.0, 1.0), (3.0, 1.0, 1.0), (3.0, 1.0, 0.0))
    drawing = look({("p", "a"): [[(-3.0, 0.0, 0.0), (3.0, 1.0, 0.0)]]}, [wall], distance=D, light=(1, 0, 0), kinds=[0])
    assert any(c != NO_CEL for c in drawing.cel)
