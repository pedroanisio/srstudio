"""Cutting a wire drawing to a band of rows, and finding where a placed model's anchors fall."""

from __future__ import annotations

import struct
import zlib

import pytest

from srstudio.wire_draw import Anchor, Placement, anchor_of, band, cel_plate, edge_below
from srstudio.wire_view import BANDS, NO_CEL, Drawing, WireError


def drawing(strokes):
    return Drawing("v", 100, 100, strokes, 10.0, {"head": (60.0, 30.0)})


def test_a_stroke_that_crosses_the_band_is_cut_where_it_crosses():
    cut = band(drawing({"a": (((10.0, 0.0), (10.0, 100.0)),)}), (-20.0, 20.0), WireError)
    ((line,),) = cut.strokes.values()
    assert line == ((10.0, 30.0), (10.0, 70.0))  # heights are from the middle of the picture, row 50


def test_the_two_halves_of_a_stroke_meet_where_it_was_cut():
    whole = drawing({"a": (((10.0, 0.0), (40.0, 100.0)),)})
    upper, lower = band(whole, (-1e5, 0.0), WireError), band(whole, (0.0, 1e5), WireError)
    assert upper.strokes["a"][0][-1] == lower.strokes["a"][0][0] == pytest.approx((25.0, 50.0))
    assert upper.strokes["a"][0][0] == (10.0, 0.0) and lower.strokes["a"][0][-1] == (40.0, 100.0)


def test_a_level_stroke_is_kept_whole_or_dropped():
    level = drawing({"a": (((0.0, 40.0), (50.0, 40.0)),), "b": (((0.0, 90.0), (50.0, 90.0)),)})
    cut = band(level, (-20.0, 0.0), WireError)
    assert set(cut.strokes) == {"a"} and cut.strokes["a"] == (((0.0, 40.0), (50.0, 40.0)),)


def test_a_stroke_that_leaves_the_band_and_returns_is_two_strokes():
    zigzag = drawing({"a": (((0.0, 40.0), (10.0, 60.0), (20.0, 40.0)),)})
    cut = band(zigzag, (-10.0, -5.0), WireError)  # rows 40 to 45: the two ends of the dip
    assert len(cut.strokes["a"]) == 2


def test_an_ink_with_nothing_in_the_band_is_left_out_and_the_scale_and_anchors_are_kept():
    cut = band(drawing({"a": (((0.0, 90.0), (50.0, 90.0)),)}), (-50.0, -40.0), WireError)
    assert cut.strokes == {} and cut.scale == 10.0 and cut.anchors == {"head": (60.0, 30.0)}


@pytest.mark.parametrize(
    "rows", [None, 3, (1.0,), (0.0, 1.0, 2.0), (5.0, 5.0), (5.0, -5.0), ("a", 1.0), (0.0, float("nan"))]
)
def test_rows_that_are_not_a_top_above_a_bottom_are_refused(rows):
    with pytest.raises(WireError, match="row"):
        band(drawing({"a": (((0.0, 0.0), (1.0, 1.0)),)}), rows, WireError)


def test_an_anchor_falls_on_the_canvas_where_the_placed_picture_puts_it():
    found = anchor_of(drawing({}), Placement(500.0, 800.0, 100.0, 1.0), "head", WireError)
    assert (found.x, found.y, found.scale) == (510.0, 780.0)[:2] + (10.0,)


def test_an_anchor_the_model_does_not_have_is_refused_and_the_choices_named():
    with pytest.raises(WireError, match="unknown anchor 'hand'.*head"):
        anchor_of(drawing({}), Placement(0.0, 0.0, 100.0, 1.0), "hand", WireError)


RAMPS = (("#000010", "#101020", "#202030", "#303040"), ("#ff0000", "#00ff00", "#0000ff", "#ffffff"))


def with_cel(cel, width, height):
    return Drawing("v", width, height, {}, 10.0, {}, bytes(cel))


def decode(plate):
    """The pixels of ``plate``'s PNG: ``(width, height, rows of RGBA)``."""
    png = plate.png
    assert png[:8] == b"\x89PNG\r\n\x1a\n"
    pos, data, size = 8, b"", None
    while pos < len(png):
        (length,) = struct.unpack(">I", png[pos : pos + 4])
        kind, body = png[pos + 4 : pos + 8], png[pos + 8 : pos + 8 + length]
        (crc,) = struct.unpack(">I", png[pos + 8 + length : pos + 12 + length])
        assert crc == zlib.crc32(kind + body)
        if kind == b"IHDR":
            size = struct.unpack(">II", body[:8])
            assert body[8:] == bytes([8, 6, 0, 0, 0])
        if kind == b"IDAT":
            data += body
        pos += 12 + length
    raw = zlib.decompress(data)
    width, height = size
    stride = 1 + 4 * width
    assert len(raw) == stride * height and all(raw[y * stride] == 0 for y in range(height))
    return (
        width,
        height,
        [[raw[y * stride + 1 + 4 * x : y * stride + 5 + 4 * x] for x in range(width)] for y in range(height)],
    )


def test_a_cel_plate_paints_each_tone_from_its_materials_ramp_and_leaves_the_rest_clear():
    cel = [NO_CEL, 0, 3, BANDS + 1, BANDS + 3, NO_CEL]
    plate = cel_plate(with_cel(cel, 3, 2), Placement(100.0, 200.0, 3.0, 1.0), RAMPS, WireError)
    width, height, rows = decode(plate)
    assert (width, height) == (3, 2) and (plate.width, plate.height) == (3, 2)
    assert rows[0] == [b"\x00\x00\x00\x00", bytes.fromhex("000010ff"), bytes.fromhex("303040ff")]
    assert rows[1] == [bytes.fromhex("00ff00ff"), bytes.fromhex("ffffffff"), b"\x00\x00\x00\x00"]
    assert (plate.x, plate.y) == (98.5, 199.0)  # its corner, so that it lies where the strokes of the same placement do


@pytest.mark.parametrize(
    ("ramps", "cel", "message"),
    [
        (RAMPS, b"", "no cel raster"),
        ((), bytes([0]), "ramps are"),
        ((("#000010", "#101020", "#202030"),), bytes([0]), "ramps are"),
        ((("#000010", "#101020", "#202030", "blue"),), bytes([0]), "ramps are"),
        (RAMPS[:1], bytes([BANDS]), "material 1, but only 1 ramps"),
    ],
)
def test_a_plate_that_cannot_be_painted_is_refused_and_says_why(ramps, cel, message):
    with pytest.raises(WireError, match=message):
        cel_plate(with_cel(cel, 1, 1), Placement(0.0, 0.0, 1.0, 1.0), ramps, WireError)


def test_the_rows_of_a_band_cut_the_cel_raster_as_they_cut_the_strokes():
    cel = bytes([0, 1, 2, 3] * 5)  # a picture 1 wide and 20 tall... as 4 wide and 5 tall
    whole = with_cel(cel, 4, 5)
    kept = band(whole, (-1.0, 0.5), WireError)  # rows 1.5 to 3: rows 2 and 3 are the ones inside
    assert kept.cel == bytes([NO_CEL] * 8) + cel[8:16] + bytes([NO_CEL] * 4)
    assert band(whole, (-100.0, 100.0), WireError).cel == cel
    assert band(whole, (50.0, 60.0), WireError).cel == bytes([NO_CEL] * 20)


def sloped(width=40, height=30, rise=0.25, noise=()):
    """A raster whose paint (material 0) lies under a line that falls ``rise`` rows for each column to the right,
    level with the middle row at the middle column; ``noise`` are columns whose paint reaches up to the top."""
    cel = bytearray([NO_CEL]) * (width * height)
    for x in range(width):
        top = 0 if x in noise else int(height / 2 + rise * (x - width / 2) + 0.999)
        for y in range(top, height):
            cel[y * width + x] = 0
    return with_cel(cel, width, height)


def test_a_tilt_slopes_the_cut_of_a_band_so_that_it_follows_an_edge_in_perspective():
    whole = sloped()  # paint under a line that falls to the right through the middle of the picture
    level = band(whole, (0.0, 1e5), WireError)
    slanted = band(whole, (0.0, 1e5), WireError, 0.25)
    assert slanted.cel == whole.cel  # a cut along the edge keeps all the paint under it
    assert level.cel != whole.cel and level.cel[10 * 40 + 5] == NO_CEL  # a level one cuts the paint high on the left
    above = band(whole, (-1e5, 0.0), WireError, 0.25)
    assert above.cel.count(0) < 40  # and none of it above: at most the one row the line rounds up


def test_a_tilt_that_is_not_a_number_is_refused():
    with pytest.raises(WireError, match="tilt"):
        band(sloped(), (-5.0, 5.0), WireError, float("nan"))


def test_the_edge_under_an_anchor_is_found_as_a_row_at_the_middle_and_a_slope():
    row, slope = edge_below(
        sloped(), Placement(0.0, 0.0, 10.0, 1.0), Anchor(0.0, 0.0, 10.0), reach=1.0, below=0.2, error=WireError
    )
    assert row == pytest.approx(0.0, abs=1.0) and slope == pytest.approx(0.25, abs=0.03)


def test_a_column_that_stands_apart_from_the_edge_is_dropped_from_the_fit():
    row, slope = edge_below(
        sloped(noise=(18, 22)),
        Placement(0.0, 0.0, 10.0, 1.0),
        Anchor(0.0, 0.0, 10.0),
        reach=1.0,
        below=0.2,
        error=WireError,
    )
    assert row == pytest.approx(0.0, abs=1.0) and slope == pytest.approx(0.25, abs=0.03)


@pytest.mark.parametrize(
    ("drawn", "below", "reach", "message"),
    [
        (with_cel(b"", 40, 30), 0.2, 1.0, "no cel raster"),
        (sloped(), 5.0, 1.0, "no paint"),  # the point under the anchor is off the picture
        (sloped(), 0.2, 0.2, "no paint"),  # fewer than eight columns to read
    ],
)
def test_an_edge_that_cannot_be_found_is_refused_and_says_why(drawn, below, reach, message):
    with pytest.raises(WireError, match=message):
        edge_below(
            drawn, Placement(0.0, 0.0, 10.0, 1.0), Anchor(0.0, 0.0, 10.0), reach=reach, below=below, error=WireError
        )
