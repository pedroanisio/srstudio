"""Toon characters told apart at a glance (ADR 0041): a head and its ears as the cells of a phone-thumbnail grid they
cover, the share of cells two outlines do not share, and coat colours in CIE L*a*b*."""

from __future__ import annotations

from srstudio import toon, toon_cast

CELL = 12.0  # reference pixels per thumbnail cell: the 592 px reference at about 50 cells wide
GRID_X = (-40.0, 440.0)
GRID_Y = (360.0, 690.0)  # the heads and ears, down to the shoulders every body shares


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


def lab(hex_colour: str) -> tuple[float, float, float]:
    """CIE L*a*b* of an sRGB colour, D65."""
    rgb = [int(hex_colour[i : i + 2], 16) / 255 for i in (1, 3, 5)]
    lin = [c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4 for c in rgb]
    x = (0.4124 * lin[0] + 0.3576 * lin[1] + 0.1805 * lin[2]) / 0.95047
    y = 0.2126 * lin[0] + 0.7152 * lin[1] + 0.0722 * lin[2]
    z = (0.0193 * lin[0] + 0.1192 * lin[1] + 0.9505 * lin[2]) / 1.08883

    def f(t: float) -> float:
        return t ** (1 / 3) if t > 0.008856 else 7.787 * t + 16 / 116

    return 116 * f(y) - 16, 500 * (f(x) - f(y)), 200 * (f(y) - f(z))


def apart(a: frozenset, b: frozenset) -> float:
    """The share of the cells either outline covers that only one of them does."""
    return len(a ^ b) / len(a | b)


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
