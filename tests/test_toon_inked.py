"""The inked fox: the fox redrawn the way the traced cat is drawn (dense, pressed, asymmetric contours, open inner
lines, a shade tone, a tilted head and a face of its own), beside the fox, with the whole brush-character contract."""

import dataclasses
import math
import xml.etree.ElementTree as ET

import pytest
from sr_core.scene import Scene

from srstudio import PEACH, Canvas, brush, flat_counter, registry, sketch, toon, toon_cast, toon_inked
from srstudio.sketch import Beat, Line, Sketch, Speaker
from srstudio.voice import Voice, VoiceSettings

INKED = toon_inked.FOX_INKED
DRAWING = toon_inked.FOX_INK


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
        assert brush.bounds(body(layers)[0])[0] > brush.bounds(body(rest)[0])[0]
    assert toon_cast.figure_shapes(INKED, eyes, mouth, arms) == layers  # the same drawing every build


@pytest.mark.parametrize("kind", toon.EYES)
def test_every_eye_is_drawn_for_this_face_not_the_shared_template(kind):
    plain = dataclasses.replace(INKED, drawing=None)
    left, right = INKED.eyes
    own = DRAWING.eye(INKED, left, kind, 1.0)
    assert own and own != toon_cast.figure_layers(plain, kind, "flat", "desk")[0][-len(own) :]
    assert all(DRAWING.eye(INKED, left, other, 1.0) != own for other in toon.EYES if other != kind)
    # the face is off-centre and tilted: the far eye is not the near one mirrored
    mirrored = [(brush.flip(s, (left[0] + right[0]) / 2), c) for s, c in DRAWING.eye(INKED, right, kind, -1.0)]
    assert mirrored != own


@pytest.mark.parametrize("kind", toon.MOUTHS)
def test_every_mouth_is_drawn_for_this_face(kind):
    own = DRAWING.mouth(INKED, kind)
    if kind == "none":
        assert own == []
        return
    shared = toon_cast.figure_layers(dataclasses.replace(INKED, drawing=None), "wide", kind, "desk")[1]
    assert own and own != shared
    assert all(DRAWING.mouth(INKED, other) != own for other in toon.MOUTHS if other != kind)
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


def body(layers: list) -> tuple[brush.Shape, brush.Shape]:
    """The body's ink band and fill: the largest coloured shape and the ink drawn just before it."""

    def area(shape: brush.Shape) -> float:
        x0, y0, x1, y1 = brush.bounds(shape)
        return (x1 - x0) * (y1 - y0)

    i = max((i for i, (_, c) in enumerate(layers) if c not in ("ink", "white")), key=lambda i: area(layers[i][0]))
    assert layers[i - 1][1] == "ink"
    return layers[i - 1][0], layers[i][0]


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
    # heavier at the back (right, away from the light) than over the crown, measured against the fill it rims
    ix0, iy0, ix1, _ = brush.bounds(body_ink)
    fx0, fy0, fx1, _ = brush.bounds(fill)
    assert ix1 - fx1 > 1.5 * (fy0 - iy0) > 0
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


def test_inner_lines_stay_open_and_a_shade_tone_turns_the_forms():
    base = DRAWING.foundation(INKED)
    strokes = DRAWING.details(INKED)
    assert len(strokes) >= 8 and all(layer in base for layer in strokes)
    assert all(c == "ink" for _, c in strokes)
    shades = [s for s, c in base if c == toon_inked.SHADE]
    assert len(shades) >= 2

    def lightness(hex_colour: str) -> float:
        r, g, b = (int(hex_colour[i : i + 2], 16) for i in (1, 3, 5))
        return 0.2126 * r + 0.7152 * g + 0.0722 * b

    assert lightness(INKED.dark) < lightness(toon_inked.SHADE) < lightness(INKED.coat)


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
