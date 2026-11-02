"""Measuring whether drawn lines hold between frames: ink masks, motion read from the plain picture, popped ink that
real motion does not explain, specks, and popped ink sorted by the width of the region it outlines."""

import numpy as np
import pytest
from scipy import ndimage

from srstudio import line_stability as ls
from srstudio import plates
from srstudio.errors import SrstudioError


def texture(height=120, width=160, seed=3):
    """A plain picture with detail everywhere, so a block match has one right answer."""
    rng = np.random.default_rng(seed)
    coarse = rng.integers(0, 255, (height // 8 + 2, width // 8 + 2, 3), dtype=np.uint8)
    return np.repeat(np.repeat(coarse, 8, axis=0), 8, axis=1)[:height, :width]


def shifted(frame, dy, dx):
    out = np.roll(frame, (dy, dx), axis=(0, 1))
    return out


def line(height=120, width=160, y=60, start=20, stop=140):
    mask = np.zeros((height, width), bool)
    mask[y, start:stop] = True
    return mask


def test_ink_is_where_the_inked_frame_leaves_the_plain_one():
    plain = np.full((4, 4, 3), 200, np.uint8)
    inked = plain.copy()
    inked[1, 1] = (10, 10, 10)
    inked[2, 2] = (195, 200, 200)  # a rounding wisp, not ink
    assert ls.ink(inked, plain).sum() == 1
    assert ls.ink(inked, plain)[1, 1]


def test_ink_reads_rgba_frames_and_ignores_alpha():
    plain = np.full((2, 2, 4), 200, np.uint8)
    inked = plain.copy()
    inked[..., 3] = 0
    assert not ls.ink(inked, plain).any()


def test_a_line_that_holds_still_never_pops():
    assert not ls.popped(line(), line()).any()


def test_a_line_inside_the_reach_has_not_popped():
    assert not ls.popped(line(y=60), line(y=62), reach=2).any()


def test_a_line_beyond_the_reach_has_popped():
    assert ls.popped(line(y=60), line(y=63), reach=2).sum() == line().sum()


def test_flow_finds_a_uniform_translation_even_and_odd():
    a = texture()
    for dy, dx in ((6, -4), (5, 7)):
        ys, xs = ls.flow(a, shifted(a, dy, dx), search=12, window=17)
        inner = (slice(24, -24), slice(24, -24))
        assert (ys[inner] == dy).mean() > 0.95
        assert (xs[inner] == dx).mean() > 0.95


def test_a_flat_picture_reads_as_no_motion():
    flat = np.full((64, 64, 3), 90, np.uint8)
    ys, xs = ls.flow(flat, flat, search=8, window=9)
    assert not ys.any()
    assert not xs.any()


def test_motion_explains_a_line_that_moved_with_the_picture():
    a = texture()
    b = shifted(a, 9, -7)
    near = line(y=60, start=40, stop=120)
    moved = shifted(near, 9, -7)
    assert ls.popped(near, moved, reach=2).sum() == near.sum()
    assert not ls.popped(near, moved, reach=2, motion=ls.flow(a, b, search=12, window=17)).any()


def test_motion_does_not_excuse_a_line_that_broke():
    a = texture()
    b = shifted(a, 9, -7)
    near = line(y=60, start=40, stop=120)
    broken = shifted(near, 9, -7)
    broken[:, :90] = False
    left = ls.popped(near, broken, reach=2, motion=ls.flow(a, b, search=12, window=17))
    assert left.sum() >= 30


def test_ink_carried_out_of_the_frame_is_not_counted():
    a = texture()
    near = line(y=60, start=2, stop=12)
    motion = (np.zeros(a.shape[:2], int), np.full(a.shape[:2], -40))
    assert not ls.popped(near, np.zeros_like(near), motion=motion).any()


def test_a_reading_holds_counts_and_rates():
    reading = ls.Reading(ink=200, area=1000, popped=50, unexplained=10)
    assert reading.cover == pytest.approx(0.2)
    assert reading.rate == pytest.approx(0.25)
    assert reading.unexplained_rate == pytest.approx(0.05)


def test_a_reading_of_nothing_has_zero_rates():
    reading = ls.Reading(ink=0, area=100, popped=0, unexplained=0)
    assert reading.rate == 0.0
    assert reading.unexplained_rate == 0.0


def test_compare_reads_one_pair_through_the_plain_frames():
    a = texture()
    b = shifted(a, 9, -7)
    near = line(y=60, start=40, stop=120)
    inked_a, inked_b = a.copy(), b.copy()
    inked_a[near] = 0
    inked_b[shifted(near, 9, -7)] = 0
    reading = ls.compare(inked_a, inked_b, a, b, search=12, window=17)
    assert reading.ink == near.sum()
    assert reading.popped == near.sum()
    assert reading.unexplained == 0


def test_a_scattered_reading_sums():
    one = ls.Reading(ink=10, area=100, popped=5, unexplained=1)
    two = ls.Reading(ink=30, area=100, popped=5, unexplained=3)
    total = ls.total([one, two])
    assert (total.ink, total.area, total.popped, total.unexplained) == (40, 200, 10, 4)


def test_total_of_nothing_is_refused():
    with pytest.raises(ls.StabilityError, match="no readings"):
        ls.total([])


def test_specks_counts_only_small_islands():
    mask = np.zeros((20, 20), bool)
    mask[1, 1] = True  # one pixel
    mask[5, 5:8] = True  # three pixels
    mask[10, 2:18] = True  # a real line
    assert ls.specks(mask, largest=4) == 2
    assert ls.specks(mask, largest=2) == 1


def test_specks_counts_a_diagonal_as_one_stroke():
    mask = np.eye(6, dtype=bool)
    assert ls.specks(mask, largest=5) == 0


def test_widths_measures_a_band_and_a_block():
    labels = np.zeros((40, 40), int)
    labels[10:13] = 1  # a band three pixels wide
    labels[20:] = 2  # a block twenty pixels wide
    width = ls.widths(labels)
    assert width[11, 20] == pytest.approx(3, abs=1)
    assert width[30, 20] == pytest.approx(20, abs=1)


def test_widths_treats_two_islands_of_one_label_apart():
    labels = np.zeros((40, 40), int)
    labels[5:8] = 1  # thin
    labels[20:36] = 1  # thick, same colour
    width = ls.widths(labels)
    assert width[6, 20] < width[28, 20]


def test_by_width_sorts_ink_and_popped_ink_into_bins():
    labels = np.zeros((40, 40), int)
    labels[10:13] = 1
    labels[20:] = 2
    ink = np.zeros((40, 40), bool)
    ink[11, 5:15] = True  # ten pixels on the thin band
    ink[30, 5:25] = True  # twenty on the block
    gone = ink.copy()
    gone[30] = False  # the thin band's ink popped, the block's held
    rows = ls.by_width(ink, gone, labels, edges=(4, 12))
    assert [(r.below, r.ink, r.popped) for r in rows] == [(4.0, 10, 10), (12.0, 0, 0), (float("inf"), 20, 0)]


def test_by_width_rate():
    assert ls.Bin(below=4.0, ink=10, popped=5).rate == pytest.approx(0.5)
    assert ls.Bin(below=4.0, ink=0, popped=0).rate == 0.0


def test_labels_gives_each_colour_one_integer():
    frame = np.zeros((2, 2, 3), np.uint8)
    frame[0, 0] = (1, 2, 3)
    frame[1, 1] = (1, 2, 3)
    frame[0, 1] = (9, 9, 9)
    out = ls.labels(frame, least=1)
    assert out[0, 0] == out[1, 1]
    assert len({out[0, 0], out[0, 1], out[1, 0]}) == 3


@pytest.mark.parametrize(
    "call",
    [
        lambda: ls.ink(np.zeros((2, 2, 3), np.uint8), np.zeros((2, 3, 3), np.uint8)),
        lambda: ls.ink(np.zeros((2, 2), np.uint8), np.zeros((2, 2), np.uint8)),
        lambda: ls.popped(np.zeros((2, 2), bool), np.zeros((3, 2), bool)),
        lambda: ls.popped(np.zeros((2, 2), int), np.zeros((2, 2), int)),
        lambda: ls.flow(np.zeros((2, 2, 3), np.uint8), np.zeros((3, 2, 3), np.uint8)),
        lambda: ls.by_width(np.zeros((2, 2), bool), np.zeros((2, 2), bool), np.zeros((3, 2), int)),
    ],
)
def test_frames_that_do_not_match_are_refused(call):
    with pytest.raises(ls.StabilityError, match="frames|mask|shape"):
        call()


@pytest.mark.parametrize(
    "call",
    [
        lambda: ls.ink(np.zeros((2, 2, 3), np.uint8), np.zeros((2, 2, 3), np.uint8), threshold=0),
        lambda: ls.ink(np.zeros((2, 2, 3), np.uint8), np.zeros((2, 2, 3), np.uint8), threshold=float("nan")),
        lambda: ls.popped(np.zeros((2, 2), bool), np.zeros((2, 2), bool), reach=-1),
        lambda: ls.flow(np.zeros((8, 8, 3), np.uint8), np.zeros((8, 8, 3), np.uint8), search=0),
        lambda: ls.flow(np.zeros((8, 8, 3), np.uint8), np.zeros((8, 8, 3), np.uint8), window=4),
        lambda: ls.specks(np.zeros((2, 2), bool), largest=0),
        lambda: ls.by_width(np.zeros((2, 2), bool), np.zeros((2, 2), bool), np.zeros((2, 2), int), edges=(4, 2)),
    ],
)
def test_bad_settings_are_refused(call):
    with pytest.raises(ls.StabilityError):
        call()


def test_the_error_is_a_library_error():
    assert issubclass(ls.StabilityError, SrstudioError)
    assert issubclass(ls.StabilityError, ValueError)


def test_labels_folds_a_blended_edge_into_a_neighbour():
    frame = np.zeros((64, 64, 3), np.uint8)
    frame[:, 32:] = (200, 10, 10)
    frame[:, 31] = (100, 5, 5)  # the engine's antialiased rim, a colour with no region of its own
    out = ls.labels(frame, least=128)
    assert len(np.unique(out)) == 2
    assert out[10, 31] in (out[10, 30], out[10, 32])


def test_labels_keeps_a_region_of_its_own():
    frame = np.zeros((64, 64, 3), np.uint8)
    frame[10:13] = (200, 10, 10)
    assert len(np.unique(ls.labels(frame, least=128))) == 2


def test_a_frame_of_only_rare_colours_is_not_an_id_frame():
    frame = np.arange(12, dtype=np.uint8).reshape(2, 2, 3)
    with pytest.raises(ls.StabilityError, match="not an id frame"):
        ls.labels(frame, least=2)


def test_labels_refuses_a_grey_frame():
    with pytest.raises(ls.StabilityError, match="dimensions"):
        ls.labels(np.zeros((2, 2), np.uint8))


def test_no_ink_has_no_specks():
    assert ls.specks(np.zeros((3, 3), bool)) == 0


def test_a_reading_of_nothing_covers_nothing():
    assert ls.Reading(ink=0, area=0, popped=0, unexplained=0).cover == 0.0


def test_nothing_in_the_next_frame_pops_everything():
    assert ls.popped(line(), np.zeros_like(line())).sum() == line().sum()


def test_a_palette_names_the_regions_and_folds_every_other_colour():
    frame = np.zeros((64, 64, 3), np.uint8)
    frame[:, 32:] = (200, 10, 10)
    frame[:, 31] = (100, 5, 5)  # a long straight edge repeats its blend past any pixel count
    out = ls.labels(frame, palette=("#000000", "#c80a0a"))
    assert len(np.unique(out)) == 2


def test_a_palette_with_nothing_on_the_frame_is_refused():
    with pytest.raises(ls.StabilityError, match="not an id frame"):
        ls.labels(np.zeros((4, 4, 3), np.uint8), palette=("#ffffff",))


def layered():
    """A textured wall and a textured card sliding across it, the case a block match gets wrong at the card's edge."""
    wall = texture(seed=3)
    card = texture(seed=8)
    box = np.zeros(wall.shape[:2], bool)
    box[40:80, 50:110] = True
    first, second = wall.copy(), wall.copy()
    first[box] = card[box]
    moved = np.roll(box, 9, axis=1)
    second[moved] = np.roll(card, 9, axis=1)[moved]
    outline = box & ~ndimage.binary_erosion(box)
    return first, second, outline, np.roll(outline, 9, axis=1)


def test_a_silhouette_moves_with_what_it_outlines_not_with_the_wall_behind():
    first, second, outline, moved = layered()
    motion = ls.flow(first, second, search=12, window=17)
    assert not ls.popped(outline, moved, reach=2, motion=motion, spread=8).any()


def test_spread_does_not_excuse_a_line_that_is_gone():
    first, second, outline, _ = layered()
    motion = ls.flow(first, second, search=12, window=17)
    assert ls.popped(outline, np.zeros_like(outline), motion=motion, spread=8).sum() == outline.sum()


def test_a_negative_spread_is_refused():
    with pytest.raises(ls.StabilityError, match="spread"):
        ls.popped(line(), line(), spread=-1)


def test_compare_spreads_by_half_a_window():
    first, second, outline, moved = layered()
    inked_a, inked_b = first.copy(), second.copy()
    inked_a[outline] = 0
    inked_b[moved] = 0
    assert ls.compare(inked_a, inked_b, first, second, search=12, window=17).unexplained == 0


def rgba(frame):
    return np.dstack([frame, np.full(frame.shape[:2], 255, np.uint8)])


def test_measure_reads_each_folder_against_the_plain_frames(tmp_path):
    plain, held, broken = tmp_path / "plain", tmp_path / "held", tmp_path / "broken"
    for folder in (plain, held, broken):
        folder.mkdir()
    a = texture()
    near = line(y=60, start=40, stop=120)
    for number in (7, 8):
        plates.write_png(plain / f"f{number:04d}.png", rgba(a))
        drawn = a.copy()
        drawn[near] = 0
        plates.write_png(held / f"f{number:04d}.png", rgba(drawn))
        plates.write_png(broken / f"f{number:04d}.png", rgba(drawn if number == 7 else a))
    got = ls.measure(plain, [held, broken], [7], search=8, window=9)
    assert got["held"].unexplained == 0
    assert got["broken"].unexplained == got["broken"].ink == near.sum()


def test_measure_refuses_a_missing_frame_and_an_empty_range(tmp_path):
    with pytest.raises(ls.StabilityError, match="no frame"):
        ls.measure(tmp_path, [tmp_path], [1])
    with pytest.raises(ls.StabilityError, match="no frames"):
        ls.measure(tmp_path, [tmp_path], [])


def strip(strokes, length=60):
    """A frame's one row: ``strokes`` of (left edge, width) in pixels, a fractional edge covering part of a pixel."""
    row = np.zeros(length)
    for left, width in strokes:
        for x in range(length):
            row[x] += max(0.0, min(x + 1, left + width) - max(x, left))
    return row.clip(0, 1)


def test_a_stroke_width_counts_part_covered_pixels():
    found = ls.strokes(strip([(10.5, 3.0), (30.0, 8.0)]))
    assert [round(s.width, 3) for s in found] == [3.0, 8.0]
    assert found[0].centre == pytest.approx(12.0, abs=0.01)


def test_a_steady_stroke_sliding_between_pixels_does_not_chatter():
    rows = [ls.strokes(strip([(10 + 0.3 * n, 3.5)])) for n in range(12)]
    got = ls.chatter(rows)
    assert got.worst == pytest.approx(0.0, abs=1e-6)
    assert got.flips == 0


def test_a_stroke_flipping_between_widths_chatters():
    rows = [ls.strokes(strip([(10, 3 if n % 2 else 4)])) for n in range(9)]
    got = ls.chatter(rows)
    assert got.worst == pytest.approx(1.0)
    assert got.flips == 7


def test_a_stroke_that_grows_steadily_does_not_flip():
    rows = [ls.strokes(strip([(10, 3 + 0.2 * n)])) for n in range(9)]
    got = ls.chatter(rows)
    assert got.worst == pytest.approx(0.2)
    assert got.flips == 0


def test_a_stroke_that_leaves_is_not_read_as_a_width_change():
    assert ls.chatter([ls.strokes(strip([(10, 4)])), ls.strokes(strip([(40, 8)]))]).pairs == 0


BLACK = (0.0, 0.0, 0.0)


def test_strokes_come_from_a_frame_row_and_a_column():
    plain = np.full((40, 40, 3), 200, np.uint8)
    inked = plain.copy()
    inked[:, 10:13] = 0
    assert [s.width for s in ls.drawn(inked, plain, BLACK, row=5)] == [pytest.approx(3.0)]
    assert ls.drawn(inked, plain, BLACK, column=11)[0].width == pytest.approx(40.0)


def test_a_line_over_a_dark_wall_reads_as_wide_as_over_a_pale_one():
    plain = np.full((4, 40, 3), 200, np.uint8)
    plain[:, 20:] = 60
    inked = plain.copy()
    inked[:, 5:8] = 0
    inked[:, 25:28] = 0
    inked[:, 8] = 100  # half a pixel of ink over the pale wall
    inked[:, 28] = 30  # half a pixel over the dark wall
    found = ls.drawn(inked, plain, BLACK, row=1)
    assert [round(s.width, 2) for s in found] == [3.5, 3.5]


def test_a_wall_the_colour_of_the_ink_counts_any_change_as_full():
    plain = np.full((2, 10, 3), 10, np.uint8)
    inked = plain.copy()
    inked[:, 4] = 0
    assert ls.drawn(inked, plain, BLACK, row=0)[0].width == pytest.approx(1.0)


def test_a_bad_ink_colour_is_refused():
    plain = np.zeros((4, 4, 3), np.uint8)
    with pytest.raises(ls.StabilityError, match="ink colour"):
        ls.drawn(plain, plain, (0.0, 2.0, 0.0), row=1)


def test_a_line_is_read_on_a_row_or_a_column_not_both():
    plain = np.zeros((4, 4, 3), np.uint8)
    with pytest.raises(ls.StabilityError, match="row or a column"):
        ls.drawn(plain, plain, BLACK)
    with pytest.raises(ls.StabilityError, match="row or a column"):
        ls.drawn(plain, plain, BLACK, row=1, column=1)


def test_a_row_off_the_frame_is_refused():
    plain = np.zeros((4, 4, 3), np.uint8)
    with pytest.raises(ls.StabilityError, match="off the frame"):
        ls.drawn(plain, plain, BLACK, row=9)


def test_swing_reads_the_ink_total_and_its_reversals():
    masks = [np.zeros((10, 10), bool) for _ in range(4)]
    for mask, size in zip(masks, (10, 12, 10, 12), strict=True):
        mask.flat[:size] = True
    got = ls.swing(masks)
    assert got.largest == pytest.approx(0.2)
    assert got.flips == 2


def test_swing_needs_two_frames_with_ink():
    with pytest.raises(ls.StabilityError, match="two frames"):
        ls.swing([np.zeros((2, 2), bool)])
    with pytest.raises(ls.StabilityError, match="two frames"):
        ls.swing([np.zeros((2, 2), bool), np.zeros((2, 2), bool)])


def test_width_chatter_reads_frame_folders_on_rows_and_columns(tmp_path):
    plain, inked = tmp_path / "plain", tmp_path / "inked"
    plain.mkdir()
    inked.mkdir()
    wall = np.full((30, 30, 3), 200, np.uint8)
    for number in range(6):
        plates.write_png(plain / f"f{number:04d}.png", rgba(wall))
        drawn = wall.copy()
        drawn[:, 10 : 13 + number % 2] = 0  # three pixels, then four, then three...
        drawn[20, :] = 0
        plates.write_png(inked / f"f{number:04d}.png", rgba(drawn))
    got = ls.width_chatter(plain, inked, range(6), BLACK, rows=[5], columns=[25])
    assert got.worst == pytest.approx(1.0)
    assert got.flips == 4


def test_width_chatter_needs_frames_and_a_line(tmp_path):
    with pytest.raises(ls.StabilityError, match="two frames"):
        ls.width_chatter(tmp_path, tmp_path, [1], BLACK, rows=[1])
    with pytest.raises(ls.StabilityError, match="row or a column"):
        ls.width_chatter(tmp_path, tmp_path, [1, 2], BLACK)
