"""The fox, the raccoon and the hedgehog: three more brush-drawn Toon characters, each with a silhouette and a coat of
its own, taking the whole Toon vocabulary, the visemes and blinks, and playing in a sketch by name."""

import math
import xml.etree.ElementTree as ET

import pytest
from sr_core.scene import Scene

from srstudio import PEACH, Canvas, brush, flat_counter, registry, sketch, toon, toon_cast
from srstudio.sketch import Beat, Line, Sketch, Speaker
from srstudio.voice import Voice, VoiceSettings

NEW = {"fox": "FOX", "raccoon": "RACCOON", "hedgehog": "HEDGEHOG"}
CELL = 12.0  # reference pixels per thumbnail cell: the 592 px reference at about 50 cells wide
GRID_X = (-40.0, 440.0)
GRID_Y = (360.0, 690.0)  # the heads and ears, down to the shoulders every body shares


def canvas(duration: float = 3.0) -> Canvas:
    scene = Scene(version="auto")
    scene.add_project(width=1080, height=1920, fps="24", duration=duration, background=PEACH.background)
    return Canvas(scene, PEACH, font_asset=None, namer=flat_counter("k"))


def runs_of(cv: Canvas):
    root = ET.fromstring(cv.scene.to_bytes(layout="pretty"))
    return [g for g in root.find("composition").iter("group") if g.get("start") is not None]


def _polygon(shape) -> list[tuple[float, float]]:
    """A closed cubic shape sampled into a polygon."""
    out = [(shape[0], shape[1])]
    x0, y0 = shape[0], shape[1]
    for i in range(2, len(shape), 6):
        c1x, c1y, c2x, c2y, x, y = shape[i : i + 6]
        for k in range(1, 7):
            t = k / 6
            u = 1 - t
            out.append(
                (
                    u**3 * x0 + 3 * u * u * t * c1x + 3 * u * t * t * c2x + t**3 * x,
                    u**3 * y0 + 3 * u * u * t * c1y + 3 * u * t * t * c2y + t**3 * y,
                )
            )
        x0, y0 = x, y
    return out


def _inside(poly, x: float, y: float) -> bool:
    hit = False
    for (ax, ay), (bx, by) in zip(poly, poly[1:] + poly[:1], strict=True):
        if (ay > y) != (by > y) and x < ax + (y - ay) * (bx - ax) / (by - ay):
            hit = not hit
    return hit


def thumbnail(shapes) -> frozenset[tuple[int, int]]:
    """The cells of a coarse grid (a phone thumbnail of the frame) that the union of ``shapes`` covers."""
    polys = [_polygon(s) for s in shapes]
    cells = set()
    nx, ny = int((GRID_X[1] - GRID_X[0]) / CELL), int((GRID_Y[1] - GRID_Y[0]) / CELL)
    for i in range(nx):
        for j in range(ny):
            x, y = GRID_X[0] + (i + 0.5) * CELL, GRID_Y[0] + (j + 0.5) * CELL
            if any(_inside(p, x, y) for p in polys):
                cells.add((i, j))
    return frozenset(cells)


def _lab(hex_colour: str) -> tuple[float, float, float]:
    """CIE L*a*b* of an sRGB colour, D65."""
    rgb = [int(hex_colour[i : i + 2], 16) / 255 for i in (1, 3, 5)]
    lin = [c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4 for c in rgb]
    x = (0.4124 * lin[0] + 0.3576 * lin[1] + 0.1805 * lin[2]) / 0.95047
    y = 0.2126 * lin[0] + 0.7152 * lin[1] + 0.0722 * lin[2]
    z = (0.0193 * lin[0] + 0.1192 * lin[1] + 0.9505 * lin[2]) / 1.08883

    def f(t: float) -> float:
        return t ** (1 / 3) if t > 0.008856 else 7.787 * t + 16 / 116

    return 116 * f(y) - 16, 500 * (f(x) - f(y)), 200 * (f(y) - f(z))


def test_the_three_join_the_cast_by_name():
    for name, const in NEW.items():
        look = getattr(toon_cast, const)
        assert toon_cast.LOOKS[name] is look and look.name == name
        assert sketch.DRAWERS[name] is getattr(toon_cast, name)
        assert name in sketch.CHARACTERS and name in sketch.LIP_SYNCED and name in sketch.TOON_CAST.characters
    names = {e["name"]: e for e in registry.catalog(style="toon")}
    for name in NEW:
        assert names[f"toon-{name}"]["kind"] == "character"


def apart(a: frozenset, b: frozenset) -> float:
    """The share of the cells either outline covers that only one of them does."""
    return len(a ^ b) / len(a | b)


@pytest.mark.parametrize("name", list(NEW))
def test_each_new_head_reads_apart_from_every_other_character_at_thumbnail_size(name):
    """Every new head and its ears differ from each other character's at least as much as the two closest of the
    cast before them (the cat and the frog) differ from each other."""
    older = ("cat", "dog", "frog", "bear", "rabbit")
    heads = {n: silhouette_rest(n) for n in (*older, *NEW)}
    floor = min(apart(heads[a], heads[b]) for i, a in enumerate(older) for b in older[i + 1 :])
    assert floor > 0.2
    for other, theirs in heads.items():
        if other != name:
            assert apart(heads[name], theirs) >= floor, f"{name} reads too close to {other}"


def silhouette_rest(name: str) -> frozenset[tuple[int, int]]:
    """The outline at rest without its arms: the cat's traced ink band, a brush character's mantle, ears and body
    rims (the first ink layers of :func:`toon_cast.figure_shapes`, before the marks)."""
    if name == "cat":
        return thumbnail([toon.art().bodies["desk"].ink])
    look = toon_cast.LOOKS[name]
    rims = len(look.ears) + 1 + bool(look.mantle)
    layers = toon_cast.figure_shapes(look, "wide", "flat", "desk")
    shapes = [s for s, c in layers if c == "ink"][:rims]
    return thumbnail(shapes)


def test_the_new_coats_tell_the_three_apart_and_from_the_older_cast():
    coats = {name: look.coat for name, look in toon_cast.LOOKS.items()}
    coats["cat"] = PEACH.shade
    for name in NEW:
        for other, colour in coats.items():
            if other != name:
                assert math.dist(_lab(coats[name]), _lab(colour)) > 20, f"{name}'s coat is too near {other}'s"


def test_the_builds_differ_small_slender_and_stout():
    def width(look, top, bottom):
        xs = [x for x, y in look.silhouette if top <= y <= bottom]
        return max(xs) - min(xs)

    def torso(look):  # the shoulders down to the desk
        return width(look, 700.0, 800.0)

    fox, raccoon, hedgehog = toon_cast.FOX, toon_cast.RACCOON, toon_cast.HEDGEHOG
    assert torso(raccoon) > max(torso(fox), torso(hedgehog)) + 30  # stout
    assert width(hedgehog, 0.0, hedgehog.mouth[1]) < min(width(n, 0.0, n.mouth[1]) for n in (fox, raccoon)) - 50

    def head(look):
        return min(y for _, y in look.silhouette)

    def ears(look):  # how far the ears rise over the head
        return head(look) - min(y for ear in look.ears for _, y in ear)

    assert ears(fox) > ears(raccoon) + 20  # the fox's ears stand tall
    assert head(hedgehog) > max(head(fox), head(raccoon)) + 25  # a small head, low on its shoulders
    assert hedgehog.limb < fox.limb < raccoon.limb


def test_a_mantle_is_drawn_behind_the_ears_and_the_body_and_paws_take_their_own_colour():
    layers = toon_cast.figure_shapes(toon_cast.HEDGEHOG, "wide", "flat", "desk")
    assert [c for _, c in layers[:2]] == ["ink", toon_cast.HEDGEHOG.dark]  # the spines first, under everything
    tips = toon_cast.HEDGEHOG.mantle
    assert min(y for _, y in tips) < min(y for _, y in toon_cast.HEDGEHOG.silhouette) - 25  # spines over the crown
    plain = toon_cast.figure_shapes(toon_cast.DOG, "wide", "flat", "desk")
    assert toon_cast.DOG.mantle == () and plain[0][1] == "ink"
    gloved = [c for _, c in toon_cast.figure_shapes(toon_cast.RACCOON, "wide", "flat", "desk")]
    assert gloved.count(toon_cast.RACCOON.paw) == 2 and toon_cast.RACCOON.paw != toon_cast.RACCOON.coat
    assert toon_cast.DOG.paw == ""  # the older cast keeps coat-coloured paws


@pytest.mark.parametrize("name", list(NEW))
def test_a_new_character_types_speaks_and_blinks(name):
    look = toon_cast.LOOKS[name]
    assert look.brows or name == "raccoon"  # the raccoon's eyes sit in its mask: no brows to see there
    assert look.shine and look.blink > 0
    cv = canvas(8.0)
    poses = toon.parse_poses(
        [
            {"start": 0.0, "eyes": "wide", "mouth": "flat", "arms": "desk"},
            {"start": 4.0, "eyes": "half", "mouth": "smirk", "arms": "type"},
        ]
    )
    track = [(0.3, "open"), (0.6, "round"), (0.9, "teeth"), (1.2, "closed")]
    getattr(toon_cast, name)(cv, cv.comp, poses, 8.0, taps=(4.5, 4.7), mouths=track)
    first, second = runs_of(cv)
    lips, shut = first.findall("group")
    assert len(lips.findall("group")) == 4  # closed, open, round, teeth
    assert shut.find("animate").get("property") == "opacity"
    assert len(second.findall("group")) == 3  # the two typing frames and the blink lids


def test_a_sketch_plays_the_new_three_by_name():
    lines = (Line("a", "New phone who dis."), Line("b", "Your bank."), Line("c", "Oh no."))

    def speaker(name, who):
        return Speaker(name, Voice(role=name, id=f"id-{name}", name=name), VoiceSettings(0.5, 0.75, 0.2), who)

    beats = (
        Beat(0.0, "fox", lines[0].text, "half", "smirk", "type", 0, 0),
        Beat(2.0, "raccoon", lines[1].text, "narrow", "flat", "crossed", 1, 0),
        Beat(4.0, "hedgehog", lines[2].text, "shock", "o", "face", 2, 0),
    )
    sk = Sketch(
        "new-three",
        "New three",
        (speaker("a", "fox"), speaker("b", "raccoon"), speaker("c", "hedgehog")),
        lines,
        beats,
        6.0,
    )
    sketch.check(sk)
    cv = canvas(6.0)
    groups = sketch.draw_cast(cv, cv.comp, sk.beats, sk.end, mouths={"fox": [(0.2, "open"), (0.5, "closed")]})
    assert len(groups) == 3
    assert [(g.get("start"), g.get("end")) for g in runs_of(cv)] == [("0", "2"), ("2", "4"), ("4", "6")]


@pytest.mark.parametrize("name", list(NEW))
def test_a_headset_fits_the_new_heads(name):
    look = toon_cast.LOOKS[name]
    layers = toon_cast.headset(look)
    band = brush.bounds(layers[0][0])
    top = min(y for _, y in look.silhouette)
    assert top - 16 < band[1] < top
