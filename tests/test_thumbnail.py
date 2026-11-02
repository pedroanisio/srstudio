"""Designed thumbnails: typed spec, the grid area, the layout's refusals, the composed scene and the engine render."""

import os
import shutil
import subprocess
from pathlib import Path

import pytest

from srstudio.checks import contrast
from srstudio.sample import SYSTEM_FONTS
from srstudio.thumbnail import (
    ACCENT_CONTRAST,
    BLOCK,
    INK,
    MARGIN,
    MAX_SIZE,
    Thumbnail,
    ThumbnailError,
    compose,
    covered,
    grid_box,
    layout,
    render,
)

FONT = next(f for f in SYSTEM_FONTS if f.exists())  # DejaVu Sans Bold, the fixture font
GOOD = Thumbnail("See my\nscreen?", 1.0, kicker="Stick 02", focus=(300, 800), zoom=1.5)


@pytest.mark.parametrize(
    "thumb, needle",
    [
        (Thumbnail("", 0), "empty line"),
        (Thumbnail("one\n\nthree", 0), "empty line"),
        (Thumbnail("a\nb\nc\nd", 0), "4 lines"),
        (Thumbnail("a", -1), "backdrop time"),
        (Thumbnail("a", float("nan")), "backdrop time"),
        (Thumbnail("a", True), "backdrop time"),  # type: ignore[arg-type]
        (Thumbnail("a", 0, kicker="two\nlines"), "kicker"),
        (Thumbnail("a", 0, zoom=0.5), "zoom"),
        (Thumbnail("a", 0, zoom=4), "zoom"),
        (Thumbnail("a", 0, accent="yellow"), "accent"),
        (Thumbnail("a", 0, place="middle"), "place"),  # type: ignore[arg-type]
    ],
)
def test_a_bad_spec_is_refused_with_its_reason(thumb, needle):
    assert any(needle in p for p in thumb.problems())
    with pytest.raises(ThumbnailError, match=needle):
        thumb.validate()


@pytest.mark.parametrize("accent", ["#A82E22", "#3355AA", "#0b0b0d"])
def test_an_accent_the_outline_ink_drowns_is_refused(accent):
    """The accent letters sit in the ink outline and the kicker's ink letters sit on the accent: a dark red read as
    a smudge on a delivered cover's dark band before this check."""
    assert contrast(accent, INK.ink) < ACCENT_CONTRAST
    with pytest.raises(ThumbnailError, match=f"accent {accent} is .* against the ink"):
        Thumbnail("a", 0, accent=accent).validate()


@pytest.mark.parametrize("accent", ["#ffd23f", "#FF9F7A", "#ff0000"])
def test_an_accent_that_reads_on_the_ink_passes(accent):
    assert contrast(accent, INK.ink) >= ACCENT_CONTRAST
    assert not Thumbnail("a", 0, accent=accent).problems()


def test_contrast_is_the_wcag_ratio():
    assert contrast("#ffffff", "#000000") == pytest.approx(21.0)
    assert contrast("#777777", "#777777") == pytest.approx(1.0)
    assert contrast("#ffd23f", "#0b0b0d") == contrast("#0b0b0d", "#ffd23f")


def test_the_headline_is_shown_in_capitals_line_by_line():
    assert GOOD.lines == ["SEE MY", "SCREEN?"]
    assert GOOD.validate() is GOOD


@pytest.mark.parametrize(
    "size, box",
    [((1080, 1920), (0, 240, 1080, 1440)), ((1080, 1080), (135, 0, 810, 1080)), ((1080, 1440), (0, 0, 1080, 1440))],
)
def test_the_grid_area_is_the_centred_three_by_four_window(size, box):
    assert grid_box(*size) == box


@pytest.mark.parametrize("place", ["top", "bottom"])
@pytest.mark.parametrize("size", [(1080, 1920), (1080, 1080)])
def test_the_layout_keeps_kicker_and_headline_inside_the_grid_area(place, size):
    from srstudio import fonts

    data = FONT.read_bytes()
    thumb = Thumbnail("Off and\non again?", 0, kicker="Ink 02", place=place)
    lay = layout(thumb, data, *size)
    gx, gy, gw, gh = grid_box(*size)
    first, last = lay.lines[0][0], lay.lines[-1][0] + lay.size
    assert lay.kicker is not None
    kx, ky, kw, kh = lay.kicker
    assert gy + MARGIN <= ky and ky + kh < first and last <= gy + gh - MARGIN + lay.size
    assert gx + MARGIN <= kx and kx + kw <= gx + gw - MARGIN
    assert all(w <= gw - 2 * MARGIN for _, w in lay.lines)
    assert all(fonts.text_width(data, x, lay.size) <= gw - 2 * MARGIN for x in thumb.lines)
    assert last - ky <= BLOCK * gh + lay.size  # the block's share of the grid area is capped
    px, py, pw, ph = lay.picture  # the picture area is the rest of the grid area, on the other side
    assert (py >= last - lay.size) if place == "top" else (py + ph <= ky)


def test_a_short_headline_gets_the_largest_size():
    assert layout(Thumbnail("Hi", 0), FONT.read_bytes(), 1080, 1920).size == MAX_SIZE


def test_a_headline_too_wide_at_the_smallest_size_is_refused():
    with pytest.raises(ThumbnailError, match="wider than"):
        layout(Thumbnail("an extremely long headline line", 0), FONT.read_bytes(), 1080, 1920)


def test_a_headline_too_tall_for_its_share_of_the_grid_area_is_refused():
    with pytest.raises(ThumbnailError, match="of the grid area"):
        layout(Thumbnail("a\nb\nc", 0, kicker="k"), FONT.read_bytes(), 600, 800)


def test_a_kicker_too_wide_is_refused():
    with pytest.raises(ThumbnailError, match="kicker"):
        layout(Thumbnail("a", 0, kicker="a kicker far too long for the frame"), FONT.read_bytes(), 1080, 1920)


def test_the_scene_draws_the_backdrop_covering_the_frame_and_one_outlined_layer_pair_per_line():
    scene = compose(GOOD, backdrop="b.png", font="f.ttf", font_bytes=FONT.read_bytes(), width=1080, height=1920)
    xml = scene.to_bytes().decode()
    assert 'src="b.png"' in xml and 'src="f.ttf"' in xml
    assert xml.count('id="outline-') == 2 * 2 and xml.count('id="line-') == 2 * 2  # asset + layer per line
    assert 'color="#ffd23f"' in xml  # the last line in the accent
    import re

    layer = re.search(r'<layer [^>]*id="backdrop-layer"[^>]*>', xml)
    assert layer is not None
    x = float(re.search(r' x="([-\d.]+)"', layer.group()).group(1))
    y = float(re.search(r' y="([-\d.]+)"', layer.group()).group(1))
    assert 1080 - 1.5 * 1080 <= x <= 0 and 1920 - 1.5 * 1920 <= y <= 0  # no edge of the frame is left uncovered


def engine() -> str:
    found = os.environ.get("SRSTUDIO_ENGINE") or shutil.which("scene-render")
    if not found or not shutil.which("ffmpeg"):
        pytest.skip("needs SRSTUDIO_ENGINE and ffmpeg")
    return found


def backdrop(path: Path, size: str = "270x480") -> Path:
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "lavfi", "-i", f"testsrc2=size={size}:rate=1",
                    "-frames:v", "1", str(path)], check=True)  # fmt: skip
    return path


def test_render_writes_a_private_jpeg_at_the_video_size(tmp_path):
    out = render(Thumbnail("Hi", 0, kicker="K"), backdrop(tmp_path / "b.png", "540x960"), tmp_path / "cover.jpg",
                 font=FONT, engine=engine(), width=540, height=960)  # fmt: skip
    probe = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "stream=width,height", "-of", "csv=p=0",
                            str(out)], check=True, capture_output=True, text=True)  # fmt: skip
    assert probe.stdout.strip() == "540,960"
    assert out.stat().st_mode & 0o777 == 0o600
    assert sorted(p.name for p in tmp_path.iterdir()) == ["b.png", "cover.jpg"]  # the work folder is gone


def test_a_failing_engine_raises_and_writes_nothing(tmp_path):
    fake = tmp_path / "engine"
    fake.write_text("#!/bin/sh\necho 'no GPU' >&2\nexit 3\n")
    fake.chmod(0o700)
    with pytest.raises(ThumbnailError, match="no GPU"):
        render(Thumbnail("Hi", 0), backdrop(tmp_path / "b.png"), tmp_path / "cover.jpg", font=FONT, engine=fake,
               width=270, height=480)  # fmt: skip
    assert not (tmp_path / "cover.jpg").exists()


# -- a headline over a face -----------------------------------------------------------------------------------------
TOP = Thumbnail("Five minutes\naway", 1.0, kicker="News", place="top")
SIZE = (1080, 1920)


def test_a_face_under_the_headline_is_named():
    lay = layout(TOP, FONT.read_bytes(), *SIZE)
    top, _ = lay.lines[0]
    face = (440.0, top + 10.0, 200.0, 200.0)
    assert covered(TOP, FONT.read_bytes(), *SIZE, [face]) == [face]


def test_a_face_under_the_kicker_is_named():
    lay = layout(TOP, FONT.read_bytes(), *SIZE)
    assert lay.kicker is not None
    x, y, w, h = lay.kicker
    face = (float(x), float(y), float(w), float(h))
    assert covered(TOP, FONT.read_bytes(), *SIZE, [face]) == [face]


def test_a_face_in_the_picture_area_is_clear():
    px, py, pw, ph = layout(TOP, FONT.read_bytes(), *SIZE).picture
    face = (px + pw / 2 - 100.0, py + ph / 2 - 100.0, 200.0, 200.0)
    assert covered(TOP, FONT.read_bytes(), *SIZE, [face]) == []


def test_a_face_beside_a_short_line_is_clear():
    """Only the width the words take counts, not the whole band."""
    short = Thumbnail("Hi", 1.0)
    lay = layout(short, FONT.read_bytes(), *SIZE)
    top, _ = lay.lines[0]
    assert covered(short, FONT.read_bytes(), *SIZE, [(0.0, float(top), 100.0, 100.0)]) == []


def test_the_face_is_read_where_the_zoom_puts_it():
    """A face in the frame's lower half is clear unzoomed; the zoom and the focus carry it up under the headline."""
    px, py, pw, ph = layout(TOP, FONT.read_bytes(), *SIZE).picture
    top = layout(TOP, FONT.read_bytes(), *SIZE).lines[0][0]
    zoomed = Thumbnail(TOP.headline, 1.0, kicker="News", place="top", zoom=2.0, focus=(540.0, 1400.0))
    below = (440.0, (top - (py + ph / 2 - 2.0 * 1400.0)) / 2.0, 200.0, 40.0)
    assert covered(TOP, FONT.read_bytes(), *SIZE, [below]) == []
    assert covered(zoomed, FONT.read_bytes(), *SIZE, [below]) == [below]


@pytest.mark.parametrize(
    "face",
    [
        (0.0, 0.0, 0.0, 10.0),
        (0.0, 0.0, 10.0, -1.0),
        (float("nan"), 0.0, 10.0, 10.0),
        (True, 0.0, 10.0, 10.0),
        ("0", 0.0, 10.0, 10.0),
        (0.0, 0.0, 10.0),
    ],
)
def test_a_box_that_is_no_box_is_refused(face):
    with pytest.raises(ThumbnailError, match="keep-clear box"):
        covered(TOP, FONT.read_bytes(), *SIZE, [face])


def test_a_headline_refuses_a_backslash_that_was_meant_as_a_line_break():
    """An over-escaped ``\\\\n`` is two printable characters: it would be drawn as "LEFT IT\\NVERY LATE"."""
    assert any("backslash" in problem for problem in Thumbnail("Left it\\nvery late", 1.0).problems())
    with pytest.raises(ThumbnailError, match="backslash"):
        Thumbnail("Left it\\nvery late", 1.0).validate()


def test_a_real_line_break_is_two_lines():
    assert Thumbnail("Left it\nvery late", 1.0).validate().lines == ["LEFT IT", "VERY LATE"]
