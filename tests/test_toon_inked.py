"""The inked fox: the fox redrawn the way the traced cat is drawn (dense, pressed, asymmetric contours, open inner
lines, a shade tone, a tilted head and a face of its own), beside the fox, with the whole brush-character contract."""

import dataclasses
import math
import xml.etree.ElementTree as ET

import pytest
from sr_core.scene import Scene

from srstudio import PEACH, Canvas, brush, flat_counter, registry, sketch, toon, toon_cast, toon_inked, toon_wear
from srstudio.sketch import Beat, Line, Sketch, Speaker
from srstudio.voice import Voice, VoiceSettings

INKED = toon_inked.FOX_INKED
DRAWING = toon_inked.FOX_INK
# the kinds the sloth, goat and hamster add to the vocabulary, drawn for this face ahead of it
EYE_KINDS = tuple(dict.fromkeys((*toon.EYES, "sleepy")))
MOUTH_KINDS = tuple(dict.fromkeys((*toon.MOUTHS, "yawn", "scream", "puff")))


def canvas(duration: float) -> Canvas:
    scene = Scene(version="auto")
    scene.add_project(width=1080, height=1920, fps="24", duration=duration, background=PEACH.background)
    return Canvas(scene, PEACH, font_asset=None, namer=flat_counter("k"))


def runs_of(cv: Canvas):
    tree = ET.fromstring(cv.scene.to_bytes(layout="pretty"))
    return [g for g in tree.find("composition").iter("group") if g.get("start") is not None]


def test_the_inked_fox_joins_the_cast_beside_the_fox():
    assert INKED.name == "fox-inked" and INKED.drawing is DRAWING
    assert INKED.coat == toon_cast.FOX.coat and INKED.paw == toon_cast.FOX.paw  # the same fox, drawn again
    assert toon_cast.FOX.drawing is None and all(look.drawing is None for look in toon_cast.LOOKS.values())
    assert "fox-inked" not in toon_cast.LOOKS  # LOOKS share the brush face; the inked fox draws its own
    assert sketch.DRAWERS["fox-inked"] is toon_inked.fox_inked and sketch.DRAWERS["fox"] is toon_cast.fox
    assert "fox-inked" in sketch.CHARACTERS and "fox-inked" in sketch.LIP_SYNCED
    entry = {e["name"]: e for e in registry.catalog(style="toon")}["toon-fox-inked"]
    assert entry["kind"] == "character"


def covering_sample() -> list[tuple[str, str, str]]:
    """Every eyes kind with every mouth kind, the arms turning through ARMS so each meets every eyes and mouth."""
    return [
        (eyes, mouth, toon.ARMS[(e + m) % len(toon.ARMS)])
        for e, eyes in enumerate(toon.EYES)
        for m, mouth in enumerate(toon.MOUTHS)
    ]


SAMPLE = covering_sample()


def test_the_sample_covers_every_pair_of_kinds():
    assert {(e, m) for e, m, _ in SAMPLE} == {(e, m) for e in toon.EYES for m in toon.MOUTHS}
    assert {(e, a) for e, _, a in SAMPLE} == {(e, a) for e in toon.EYES for a in toon.ARMS}
    assert {(m, a) for _, m, a in SAMPLE} == {(m, a) for m in toon.MOUTHS for a in toon.ARMS}


@pytest.mark.parametrize(("eyes", "mouth", "arms"), SAMPLE, ids=["-".join(s) for s in SAMPLE])
def test_every_expression_is_drawn_inside_the_character_s_corner(eyes, mouth, arms):
    layers = toon_cast.figure_shapes(INKED, eyes, mouth, arms)
    assert layers and all(len(s) >= 8 and (len(s) - 2) % 6 == 0 for s, _ in layers)
    boxes = [brush.bounds(s) for s, _ in layers]
    assert min(b[0] for b in boxes) > -40 and max(b[2] for b in boxes) < 440  # the bounds of test_toon_cast
    assert min(b[1] for b in boxes) > 360 and max(b[3] for b in boxes) < 860
    colours = [c for _, c in layers]
    assert colours[0] == "ink" and INKED.coat in colours and toon_inked.SHADE in colours
    rest = toon_cast.figure_shapes(INKED, eyes, mouth, "desk")
    if arms in ("face", "face2"):  # the paws over the mouth come last
        assert colours[-1] in ("ink", INKED.paw)
    if arms == "sigh":
        assert brush.bounds(layers[0][0])[1] == pytest.approx(
            brush.bounds(rest[0][0])[1] + toon_cast.SIGH_DROP, abs=0.01
        )
    if arms == "lean":  # the turn is clockwise about the hips: the shoulders and the head swing right
        assert span(body(layers)[0])[0] > span(body(rest)[0])[0]
    assert toon_cast.figure_shapes(INKED, eyes, mouth, arms) == layers  # the same drawing every build


@pytest.mark.parametrize("kind", EYE_KINDS)
def test_every_eye_is_drawn_for_this_face_not_the_shared_template(kind):
    plain = dataclasses.replace(INKED, drawing=None)
    left, right = INKED.eyes
    own = DRAWING.eye(INKED, left, kind, 1.0)
    assert own
    if kind in toon.EYES:  # the shared template draws a kind once the vocabulary has it
        assert own != toon_cast.figure_layers(plain, kind, "flat", "desk")[0][-len(own) :]
    assert all(DRAWING.eye(INKED, left, other, 1.0) != own for other in EYE_KINDS if other != kind)
    # the face is off-centre and tilted: the far eye is not the near one mirrored
    mirrored = [(brush.flip(s, (left[0] + right[0]) / 2), c) for s, c in DRAWING.eye(INKED, right, kind, -1.0)]
    assert mirrored != own


@pytest.mark.parametrize("kind", MOUTH_KINDS)
def test_every_mouth_is_drawn_for_this_face(kind):
    own = DRAWING.mouth(INKED, kind)
    if kind == "none":
        assert own == []
        return
    assert own and all(len(s) != 26 for s, _ in own)  # no perfect ellipse
    if kind in toon.MOUTHS:  # the shared template draws a kind once the vocabulary has it
        assert own != toon_cast.figure_layers(dataclasses.replace(INKED, drawing=None), "wide", kind, "desk")[1]
    assert all(DRAWING.mouth(INKED, other) != own for other in MOUTH_KINDS if other != kind)
    mx, my = INKED.mouth
    for shape, _ in own:  # on the muzzle, under the nose
        x0, y0, x1, y1 = brush.bounds(shape)
        assert mx - 40 < x0 and x1 < mx + 40 and my - 26 < y0 and y1 < my + 40


@pytest.mark.parametrize("kind", toon_cast.VISEMES[1:])
def test_every_viseme_is_drawn_for_this_face(kind):
    own = DRAWING.viseme(INKED, kind)
    assert own and all(DRAWING.viseme(INKED, other) != own for other in toon_cast.VISEMES[1:] if other != kind)
    mx, my = INKED.mouth
    assert all(mx - 40 < brush.bounds(s)[0] and brush.bounds(s)[3] < my + 40 for s, _ in own)
    with pytest.raises(toon.ToonDataError, match="no viseme"):
        DRAWING.viseme(INKED, "shout")


def test_sleepy_eyes_hang_a_heavy_lid_past_the_middle_over_a_low_iris():
    left = INKED.eyes[0]
    sleepy = DRAWING.eye(INKED, left, "sleepy", 1.0)
    lid = [brush.bounds(s) for s, c in sleepy if c == INKED.coat]
    iris = [brush.bounds(s) for s, c in sleepy if c == toon_inked.IRIS]
    assert len(lid) == 1 and len(iris) == 1 and all(len(s) != 26 for s, _ in sleepy)
    assert lid[0][3] > left[1] + 0.1 * INKED.eye_r  # down past the middle of the eye
    wide_iris = [brush.bounds(s) for s, c in DRAWING.eye(INKED, left, "wide", 1.0) if c == toon_inked.IRIS][0]
    assert (iris[0][1] + iris[0][3]) / 2 > (wide_iris[1] + wide_iris[3]) / 2 + 3  # the gaze dropped
    assert len([c for _, c in sleepy if c == "ink"]) > len(
        [c for _, c in DRAWING.eye(INKED, left, "half", 1.0) if c == "ink"]
    )


def test_a_yawn_drops_the_jaw_a_scream_bares_teeth_and_a_puff_closes_between_cheeks():
    mx, my = INKED.mouth
    yawn, scream, puff = (DRAWING.mouth(INKED, k) for k in ("yawn", "scream", "puff"))
    span_of = lambda layers: (  # noqa: E731
        min(brush.bounds(s)[0] for s, _ in layers), min(brush.bounds(s)[1] for s, _ in layers),
        max(brush.bounds(s)[2] for s, _ in layers), max(brush.bounds(s)[3] for s, _ in layers),
    )  # fmt: skip
    o = span_of(DRAWING.mouth(INKED, "o"))
    y0, y1 = span_of(yawn)[1], span_of(yawn)[3]
    assert y1 - y0 > 1.6 * (o[3] - o[1])  # the jaw dropped, much taller than an "o"
    assert {toon_inked.INSIDE, toon_cast.TONGUE} <= {c for _, c in yawn} and "white" not in {c for _, c in yawn}
    sx0, _, sx1, _ = span_of(scream)
    assert sx1 - sx0 > 1.2 * (span_of(yawn)[2] - span_of(yawn)[0])  # wider than the yawn
    assert {toon_inked.INSIDE, toon_cast.TONGUE, "white"} <= {c for _, c in scream}  # teeth and tongue showing
    assert toon_inked.INSIDE not in {c for _, c in puff}  # closed
    px0, _, px1, _ = span_of(puff)
    assert px0 < mx - 0.6 * INKED.mouth_w and px1 > mx + 0.6 * INKED.mouth_w  # the cheeks blown out past the mouth


def test_a_kind_the_face_was_not_drawn_with_is_refused_by_name():
    with pytest.raises(toon.ToonDataError, match="no eyes 'laser' drawn for this face"):
        DRAWING.eye(INKED, INKED.eyes[0], "laser", 1.0)
    with pytest.raises(toon.ToonDataError, match="no mouth 'beak' drawn for this face"):
        DRAWING.mouth(INKED, "beak")


def test_the_blink_lids_cover_each_open_eye_even_a_shocked_one():
    lids = DRAWING.lids(INKED)
    for centre, inner in zip(INKED.eyes, (1.0, -1.0), strict=True):
        covers = [brush.bounds(s) for s, c in lids if c == INKED.coat]
        for kind in ("wide", "shock"):
            eye = [brush.bounds(s) for s, c in DRAWING.eye(INKED, centre, kind, inner) if c == "white"]
            white = eye[0]
            assert any(
                b[0] <= white[0] and b[1] <= white[1] and b[2] >= white[2] and b[3] >= white[3] for b in covers
            ), f"the lid leaves the {kind} eye at {centre} showing"


def span(shapes: list[brush.Shape]) -> tuple[float, float, float, float]:
    boxes = [brush.bounds(s) for s in shapes]
    return min(b[0] for b in boxes), min(b[1] for b in boxes), max(b[2] for b in boxes), max(b[3] for b in boxes)


def inked_runs(layers: list) -> list[tuple[list[brush.Shape], int]]:
    """Every coloured fill drawn straight over ink, with the run of ink pieces (its band) just before it."""
    out = []
    for i, (_, c) in enumerate(layers):
        if c in ("ink", "white") or i == 0 or layers[i - 1][1] != "ink":
            continue
        k = i
        while k > 0 and layers[k - 1][1] == "ink":
            k -= 1
        out.append(([s for s, _ in layers[k:i]], i))
    return out


def body(layers: list) -> tuple[list[brush.Shape], brush.Shape]:
    """The body's ink band (its pieces) and fill: the largest coloured shape and the ink drawn just before it."""

    def area(shape: brush.Shape) -> float:
        x0, y0, x1, y1 = brush.bounds(shape)
        return (x1 - x0) * (y1 - y0)

    i = max((i for i, (_, c) in enumerate(layers) if c not in ("ink", "white")), key=lambda i: area(layers[i][0]))
    band = [band for band, at in inked_runs(layers) if at == i]
    assert band
    return band[0], layers[i][0]


def inflections(shape: brush.Shape) -> int:
    """How often the outline through the shape's on-curve points changes the way it bends: a hand's unevenness."""
    pts = [(shape[i], shape[i + 1]) for i in range(0, len(shape) - 1, 6)]
    n = len(pts)
    signs = []
    for i in range(n):
        (ax, ay), (bx, by), (cx, cy) = pts[i - 1], pts[i], pts[(i + 1) % n]
        cross = (bx - ax) * (cy - by) - (by - ay) * (cx - bx)
        if abs(cross) > 1e-3:
            signs.append(cross > 0)
    return sum(a != b for a, b in zip(signs, signs[1:] + signs[:1], strict=True))


def test_the_contour_is_dense_pressed_and_asymmetric_like_the_traced_cat():
    assert len(INKED.silhouette) >= 2 * len(toon_cast.FOX.silhouette)  # many more points placed by hand
    body_ink, fill = body(DRAWING.foundation(INKED))
    _, fox_fill = body(toon_cast.figure_shapes(toon_cast.FOX, "wide", "flat", "desk"))
    assert inflections(fill) > 2 * inflections(fox_fill)  # an uneven contour, not a smooth one
    # heavier underneath and at the back (away from the light) than over the crown, measured against the fill it
    # rims; the back's extreme is the ruff's sharp tip, where the brush lifts, so the bottom carries the full weight
    ix0, iy0, ix1, iy1 = span(body_ink)
    fx0, fy0, fx1, fy1 = brush.bounds(fill)
    assert iy1 - fy1 > 2 * (fy0 - iy0) > 0 and ix1 - fx1 > fy0 - iy0
    # not mirror-symmetric: the outline flipped about the axis lands away from itself
    points = INKED.silhouette
    flipped = [(2 * toon_cast.CENTRE - x, y) for x, y in points]
    assert sum(min(math.dist(p, q) for q in points) for p in flipped) / len(points) > 4.0
    # a head tilt, and the face off the head's own midline (taken at eye height, the tilt moves both)
    (lx, ly), (rx, ry) = INKED.eyes
    assert abs(ly - ry) >= 3.0
    sides = [x for x, y in points if abs(y - (ly + ry) / 2) < 30]
    midline = (min(sides) + max(sides)) / 2
    assert (lx + rx) / 2 - midline >= 4.0 and INKED.mouth[0] - midline >= 4.0


def test_the_ink_band_breaks_where_a_hand_lifts_the_brush():
    runs = inked_runs(DRAWING.foundation(INKED))
    assert len(runs) >= 4  # the tail, both ears and the body
    assert all(3 <= len(band) <= 5 for band, _ in runs)
    assert len(body(DRAWING.foundation(INKED))[0]) >= 4
    paw = DRAWING.limb([(100.0, 700.0), (120.0, 740.0), (150.0, 770.0)], INKED, (150.0, 770.0), True)
    mitten = [band for band, at in inked_runs(paw) if paw[at][1] == INKED.paw]
    assert len(mitten) == 1 and 3 <= len(mitten[0]) <= 5
    assert DRAWING.foundation(INKED) == DRAWING.foundation(INKED)  # seeded: the same breaks every build


def test_no_eye_nose_or_shine_is_a_perfect_ellipse_and_every_eye_is_a_one_off():
    for eyes, mouth, arms in SAMPLE:
        assert not [c for s, c in toon_cast.figure_shapes(INKED, eyes, mouth, arms) if len(s) == 26], (eyes, mouth)
    assert all(len(s) != 26 for s in INKED.nose)
    (lx, ly), (rx, ry) = INKED.eyes

    def white(kind: str, centre: tuple[float, float], inner: float) -> brush.Shape:
        (shape,) = [s for s, c in DRAWING.eye(INKED, centre, kind, inner) if c == "white"][:1]
        x0, y0, _, _ = brush.bounds(shape)
        return brush.shift(shape, -x0, -y0)

    level = ("wide", "half", "left", "up", "down", "side", "narrow", "roll", "teary")
    assert len({white(k, (lx, ly), 1.0) for k in level}) == len(level)  # each kind drawn once, by hand


def test_the_head_shade_turns_the_form_tapering_at_both_ends():
    head = [s for s, c in DRAWING.foundation(INKED) if c == toon_inked.SHADE and brush.bounds(s)[1] < 560]
    assert len(head) == 1
    points = [(head[0][i], head[0][i + 1]) for i in range(0, len(head[0]) - 1, 6)]
    outline = INKED.silhouette
    edges = list(zip(outline, outline[1:] + outline[:1], strict=True))
    starts = [0.0]
    for a, b in edges:
        starts.append(starts[-1] + math.dist(a, b))

    def place(p: tuple[float, float]) -> tuple[float, float]:
        """How far along the silhouette the point sits, and how far inside it."""
        best = (math.inf, 0.0)
        for (a, b), s0 in zip(edges, starts, strict=False):
            (ax, ay), (bx, by) = a, b
            t = max(0.0, min(1.0, ((p[0] - ax) * (bx - ax) + (p[1] - ay) * (by - ay)) / math.dist(a, b) ** 2))
            best = min(best, (math.dist(p, (ax + t * (bx - ax), ay + t * (by - ay))), s0 + t * math.dist(a, b)))
        return best[1], best[0]

    placed = [place(p) for p in points]
    first, last = min(s for s, _ in placed), max(s for s, _ in placed)
    deepest = max(d for _, d in placed)
    ends = [d for s, d in placed if s < first + 0.08 * (last - first) or s > last - 0.08 * (last - first)]
    assert deepest >= 18.0  # it swells into the cheek
    assert ends and max(ends) < 0.5 * deepest  # and thins to the outline at both ends, where a stripe stays full


def sampled(shape: brush.Shape, k: int = 6) -> list[tuple[float, float]]:
    """The shape's outline as a polygon: each cubic sampled ``k`` times."""
    out, (x0, y0) = [], (shape[0], shape[1])
    for i in range(2, len(shape), 6):
        c1x, c1y, c2x, c2y, x, y = shape[i : i + 6]
        for j in range(1, k + 1):
            t, u = j / k, 1 - j / k
            out.append(
                (
                    u**3 * x0 + 3 * u * u * t * c1x + 3 * u * t * t * c2x + t**3 * x,
                    u**3 * y0 + 3 * u * u * t * c1y + 3 * u * t * t * c2y + t**3 * y,
                )
            )
        x0, y0 = x, y
    return out


def inside(poly: list[tuple[float, float]], x: float, y: float) -> bool:
    hit = False
    for (ax, ay), (bx, by) in zip(poly, poly[1:] + poly[:1], strict=True):
        if (ay > y) != (by > y) and x < ax + (y - ay) * (bx - ax) / (by - ay):
            hit = not hit
    return hit


def to_outline(poly: list[tuple[float, float]], p: tuple[float, float]) -> float:
    """How far the point is from the polygon's edge."""
    best = math.inf
    for a, b in zip(poly, poly[1:] + poly[:1], strict=True):
        (ax, ay), (bx, by) = a, b
        t = max(0.0, min(1.0, ((p[0] - ax) * (bx - ax) + (p[1] - ay) * (by - ay)) / (math.dist(a, b) ** 2 or 1.0)))
        best = min(best, math.dist(p, (ax + t * (bx - ax), ay + t * (by - ay))))
    return best


OUTLINE = brush.spline(INKED.silhouette, True, 8)  # the body's drawn contour
SHOULDER = (676.0, 770.0)  # from under the ruff down the flank, reference px


@pytest.mark.parametrize("side", ["left", "right"])
def test_the_neck_runs_into_the_shoulder_and_flank_as_one_gentle_contour(side):
    at = [
        i
        for i, (x, y) in enumerate(OUTLINE)
        if SHOULDER[0] <= y <= SHOULDER[1] and (x < toon_cast.CENTRE) == (side == "left")
    ]
    assert at == list(range(at[0], at[0] + len(at))) and len(at) >= 30  # one stretch of the contour
    run = [OUTLINE[i] for i in at]
    heads = [math.atan2(b[1] - a[1], b[0] - a[0]) for a, b in zip(run, run[1:], strict=False)]
    turns = [
        abs(math.degrees((h - g + math.pi) % (2 * math.pi) - math.pi)) for g, h in zip(heads, heads[1:], strict=False)
    ]
    # no notch where an arm met the torso and no ruff tip under the cheek: one gentle curve, never a corner
    assert max(turns) < 30.0 and sum(turns) < 150.0


@pytest.mark.parametrize("arms", toon.ARMS)
def test_every_arm_leaves_the_shoulder_inside_the_body_and_ends_under_its_paw(arms):
    for frame in (0, 1) if arms == "type" else (0,):
        under, over = toon_cast._arms(INKED, arms, frame)
        layers = under + over
        fills = [s for s, c in layers if c == INKED.coat]
        paws = [s for s, c in layers if c == INKED.paw]
        assert len(fills) == len(paws) == 2
        for fill, (sx, sy) in zip(fills, toon_cast.SHOULDERS, strict=True):
            # no lobe over the shoulder: round it, down to 12 px under it, the arm is inside the body; a forearm
            # reaching out (typing, leaning) leaves the flank lower down, at the elbow
            near = [(x, y) for x, y in sampled(fill) if math.dist((x, y), (sx, sy)) < 45.0 and y < sy + 12.0]
            assert near and all(inside(OUTLINE, *p) for p in near), (arms, sx)
            if arms not in ("face", "face2"):  # paws up at the mouth climb the chest, inside the body
                assert brush.bounds(fill)[1] > sy, (arms, sx)
        for fill, paw in zip(fills, paws, strict=True):
            assert any(inside(sampled(paw), *p) for p in sampled(fill)), arms  # the arm runs under its paw


@pytest.mark.parametrize("arms", ["desk", "crossed", "face", "face2"])
def test_an_arm_resting_on_the_body_is_an_inner_line_never_a_second_contour(arms):
    under, over = toon_cast._arms(INKED, arms, 0)
    layers = under + over
    paws = [brush.bounds(s) for s, c in layers if c == INKED.paw]

    def on_a_paw(p: tuple[float, float]) -> bool:
        return any(x0 - 8 <= p[0] <= x1 + 8 and y0 - 8 <= p[1] <= y1 + 8 for x0, y0, x1, y1 in paws)

    lines = [s for s, c in layers if c == "ink" and not all(on_a_paw(p) for p in sampled(s))]
    assert lines  # the overlap still reads
    points = [p for s in lines for p in sampled(s) if not on_a_paw(p)]
    assert all(inside(OUTLINE, *p) for p in points)
    assert min(to_outline(OUTLINE, p) for p in points) > 0.25 * INKED.limb  # never doubling the flank


def test_an_arm_is_slim_at_the_shoulder_and_widest_at_forearm_and_paw():
    widths = [toon_inked.ARM_TAPER.at(k / 20) for k in range(21)]
    assert max(widths) == max(widths[12:]) and widths[0] < 0.6 * max(widths)


def test_inner_lines_stay_open_and_a_shade_tone_turns_the_forms():
    base = DRAWING.foundation(INKED)
    strokes = DRAWING.details(INKED)
    # few, chosen lines: the operator's second pass cut the crown parting, the chest tufts and two ear fluffs
    assert 5 <= len(strokes) <= 7 and all(layer in base for layer in strokes)
    assert all(c == "ink" for _, c in strokes)
    shades = [s for s, c in base if c == toon_inked.SHADE]
    assert len(shades) >= 2

    def lightness(hex_colour: str) -> float:
        r, g, b = (int(hex_colour[i : i + 2], 16) for i in (1, 3, 5))
        return 0.2126 * r + 0.7152 * g + 0.0722 * b

    assert lightness(INKED.dark) < lightness(toon_inked.SHADE) < lightness(INKED.coat)


def test_glasses_turn_with_the_tilted_head():
    assert toon_wear.face_of(INKED).tilt == toon_inked.TILT


def test_the_two_typing_frames_differ_only_in_the_arms():
    a = toon_cast.figure_shapes(INKED, "half", "flat", "type", 0)
    b = toon_cast.figure_shapes(INKED, "half", "flat", "type", 1)
    assert len(a) == len(b) and a != b
    base = len(DRAWING.foundation(INKED))
    assert a[:base] == b[:base] and a[-1] == b[-1]


@pytest.mark.parametrize("wear", [("glasses",), ("sweat", "flush"), toon.WEAR])
def test_the_inked_fox_wears_what_any_character_wears(wear):
    plain = toon_cast.figure_shapes(INKED, "wide", "flat", "desk")
    worn = toon_cast.figure_shapes(INKED, "wide", "flat", "desk", wear=wear)
    assert len(worn) > len(plain)
    assert all(-40 < brush.bounds(s)[0] and brush.bounds(s)[2] < 440 for s, _ in worn)


def test_the_inked_fox_types_speaks_and_blinks_like_the_rest():
    assert INKED.blink > 0
    cv = canvas(8.0)
    poses = toon.parse_poses(
        [
            {"start": 0.0, "eyes": "wide", "mouth": "flat", "arms": "desk"},
            {"start": 4.0, "eyes": "half", "mouth": "smirk", "arms": "type"},
        ]
    )
    track = [(0.3, "open"), (0.6, "round"), (0.9, "teeth"), (1.2, "closed")]
    groups = toon_inked.fox_inked(cv, cv.comp, poses, 8.0, taps=(4.5, 4.7), mouths=track)
    first, second = runs_of(cv)
    assert len(groups) == 2
    lips, shut = first.findall("group")
    assert len(lips.findall("group")) == 4  # closed, open, round, teeth
    assert shut.find("animate").get("property") == "opacity"
    assert len(second.findall("group")) == 3  # the two typing frames and the blink lids


@pytest.mark.parametrize(
    ("eyes", "mouth"), (("sleepy", "flat"), ("half", "yawn"), ("wide", "scream"), ("half", "puff"))
)
def test_a_sketch_draws_the_four_kinds_every_brush_character_shares_on_the_inked_fox(eyes, mouth):
    line = Line("a", "New phone who dis.")
    who = Speaker("a", Voice(role="a", id="id-a", name="a"), VoiceSettings(0.5, 0.75, 0.2), "fox-inked")
    sk = Sketch("kinds", "Kinds", (who,), (line,), (Beat(0.0, "fox-inked", line.text, eyes, mouth, "desk", 0, 0),), 2.0)
    sketch.check(sk)
    cv = canvas(2.0)
    assert len(sketch.draw_cast(cv, cv.comp, sk.beats, sk.end)) == 1
    look = toon_inked.FOX_INKED
    assert toon_cast._eye(look, look.eyes[0], eyes, 1.0) and toon_cast._mouth(look, mouth)


def test_a_sketch_swaps_the_inked_fox_in_by_name():
    lines = (Line("a", "New phone who dis."), Line("b", "Your bank."))

    def speaker(name, who):
        return Speaker(name, Voice(role=name, id=f"id-{name}", name=name), VoiceSettings(0.5, 0.75, 0.2), who)

    beats = (
        Beat(0.0, "fox-inked", lines[0].text, "roll", "smirk", "type", 0, 0, wear=("glasses",)),
        Beat(2.0, "fox", lines[1].text, "hearts", "grimace", "crossed", 1, 0),
    )
    sk = Sketch("inked", "Inked", (speaker("a", "fox-inked"), speaker("b", "fox")), lines, beats, 4.0)
    sketch.check(sk)
    cv = canvas(4.0)
    groups = sketch.draw_cast(cv, cv.comp, sk.beats, sk.end, mouths={"fox-inked": [(0.2, "open"), (0.5, "closed")]})
    assert len(groups) == 2
    assert [(g.get("start"), g.get("end")) for g in runs_of(cv)] == [("0", "2"), ("2", "4")]
