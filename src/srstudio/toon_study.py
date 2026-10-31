"""Toon props of someone studying: an open book, a shut one, a highlighter, the page in close-up, an old school quiz.

:func:`open_book` stands on a surface, propped towards the viewer, its text as ruled scrawl and each row highlighted
as asked; one row can be swept on cue, and a written note can stand on its right page instead of the text.
:func:`shut_book` is the same book closed. :func:`highlighter` is a paw moving a marker. :func:`study_page` fills the
frame with one page, its key in the margin, and :func:`quiz_sheet` is a folded sheet from a school quiz with its
result circled and a star stuck on it.

Book and marker measure in reference screen pixels (:func:`srstudio.toon.fx`/``fy``); the two sheets, which play as
full-frame inserts, in frame pixels. Every key is on the composition clock. Bad input is a
:class:`srstudio.toon.ToonDataError`.
"""

from __future__ import annotations

import math
import re
from collections.abc import Callable, Mapping, Sequence

from . import checks
from .canvas import Canvas
from .registry import register
from .toon import FINE_W, INK_W, ToonDataError, fh, fx, fy

__all__ = [
    "BOOK_ROWS",
    "HIGHLIGHT",
    "PINK",
    "QUIZ_SIZE",
    "SWEEP",
    "highlighter",
    "note_span",
    "open_book",
    "quiz_sheet",
    "row_span",
    "shut_book",
    "study_page",
]

Measure = Callable[[str, float], float]  # the advance width of a text at a size

HIGHLIGHT, PINK = "#ffe14d", "#ff9ec4"
PAGE, OLD_PAGE = "#fbf6e9", "#efe2c2"
LETTER, SCRAWL = "#23222e", "#6d6a72"
COVER, COVER_EDGE = "#2f6f73", "#23565a"
FOLD = "#b9a67f"
STAR, CIRCLE = "#f2b632", "#96210f"  # the circle keeps 4.5:1 on the old paper and under its letters
MARKER_BODY, MARKER_CAP = "#ffd21f", "#2f6f73"

BOOK_ROWS = 16  # the rows of text on the two pages of an open book, left page first
PAGE_ROWS = BOOK_ROWS // 2
BOOK_W, BOOK_H = 228.0, 190.0  # half the book's width and its height, in reference pixels
ROW_TOP, ROW_STEP = 20.0, 20.5
ROW_LENGTHS = (0.96, 0.88, 0.93, 0.8, 0.97, 0.9, 0.84, 0.62)
BOOK_AT = (300.0, 801.0)
SWEEP = 0.55  # seconds a row takes to fill
NOTE_ROWS = 2
NOTE_SIZE = 44.0
NOTE_HIGH = NOTE_SIZE * 1.25
NOTE_LEFT, NOTE_WIDTH = 16.0, 196.0
SHEET_ROWS = 9
SHEET_X, SHEET_Y, SHEET_W, SHEET_H = 80.0, 440.0, 860.0, 1010.0  # clear of the signature marks on a card shot
SHEET_MARGIN = 64.0
QUIZ_SIZE = 56.0
_HEX = re.compile(r"#[0-9a-fA-F]{6}")


def _colour(value: object, what: str) -> None:
    if not (isinstance(value, str) and _HEX.fullmatch(value)):
        raise ToonDataError(f"{what} is a #rrggbb colour, got {value!r}")


def _point(at: object, what: str) -> tuple[float, float]:
    if not (isinstance(at, tuple | list) and len(at) == 2 and all(checks.number(v) for v in at)):
        raise ToonDataError(f"{what} is a point (x, y), got {at!r}")
    return float(at[0]), float(at[1])


def _second(second: object) -> None:
    if not (checks.number(second) and second >= 0):
        raise ToonDataError(f"a sweep starts at a second >= 0, got {second!r}")


def _marks(marks: Mapping[int, str], rows: int, what: str) -> None:
    for row, colour in marks.items():
        if not (isinstance(row, int) and 0 <= row < rows):
            raise ToonDataError(f"{what} has rows 0 to {rows - 1}, got {row!r}")
        _colour(colour, f"{what}'s row {row}")


def _row_at(row: int) -> tuple[float, float, float]:
    """A book's text row ``row``: its left edge, its top and its width, in the book's own units."""
    side, line = divmod(row, PAGE_ROWS)
    left = -fh(BOOK_W) * 0.9 if side == 0 else fh(NOTE_LEFT)
    return left, -fh(BOOK_H) + fh(ROW_TOP + line * ROW_STEP), fh(192) * ROW_LENGTHS[line]


def row_span(row: int, at: tuple[float, float] = BOOK_AT, scale: float = 1.0) -> tuple[float, float, float]:
    """Where text row ``row`` of a book at ``at`` lies on the frame: its left end, its right end and its height."""
    x, y = _point(at, "a book's foot")
    _marks({row: HIGHLIGHT}, BOOK_ROWS, "a book")
    left, top, width = _row_at(row)
    return fx(x) + scale * left, fx(x) + scale * (left + width), fy(y) + scale * top


def _band(cv: Canvas, parent, left, top, width, colour, start: float | None, seconds: float, id: str) -> None:
    """A highlighter's stroke, whole, or growing from its left end at ``start``."""
    tall = fh(16)
    if start is None:
        cv.rect(parent, left, top - tall * 0.3, width, tall, colour, radius=fh(3))
        return
    g = cv.group(parent, id, x=left, y=top, anchorX=0, anchorY=0, start=start)
    cv.rect(g, 0, -tall * 0.3, width, tall, colour, radius=fh(3))
    cv.keys(g, "scaleX", [(start, 0.02), (start + seconds, 1.0)], local=False)


def _note_rows(note: Sequence[str], tall: float) -> list[tuple[float, str]]:
    """Each row of a note with its top, in the book's units, the rows centred on the page."""
    first = -tall / 2 - len(note) * NOTE_HIGH / 2
    return [(first + k * NOTE_HIGH, row) for k, row in enumerate(note)]


def note_span(
    note: Sequence[str], measure: Measure, at: tuple[float, float] = BOOK_AT, scale: float = 1.0
) -> tuple[float, float, float]:
    """Where a note's last row lies on the frame: its left end, its right end and the middle of its height."""
    x, y = _point(at, "a book's foot")
    top, row = _note_rows(note, fh(BOOK_H))[-1]
    left = fx(x) + scale * fh(NOTE_LEFT)
    return left, left + scale * measure(row, NOTE_SIZE), fy(y) + scale * (top + NOTE_HIGH / 2)


def _check_note(note: object, measure: Measure | None) -> None:
    """A note is a few short rows that fit the page."""
    if not (
        isinstance(note, tuple | list)
        and 1 <= len(note) <= NOTE_ROWS
        and all(isinstance(row, str) and row.strip() for row in note)
    ):
        raise ToonDataError(f"a note is 1 to {NOTE_ROWS} rows of words, got {note!r}")
    if measure is None:
        raise ToonDataError("a note on a page needs measure")
    if any(measure(row, NOTE_SIZE) > fh(NOTE_WIDTH) for row in note):
        raise ToonDataError(f"a note's rows fit {NOTE_WIDTH} reference pixels at {NOTE_SIZE}: {note!r}")


@register("prop", "toon-open-book", summary="An open book propped on a surface, each row highlighted as asked")
def open_book(
    cv: Canvas,
    parent,
    marks: Mapping[int, str] | None = None,
    *,
    sweep: tuple[int, str, float] | None = None,
    note: Sequence[str] | None = None,
    note_sweep: tuple[str, float] | None = None,
    measure: Measure | None = None,
    at: tuple[float, float] = BOOK_AT,
    scale: float = 1.0,
    id: str = "open-book",
) -> None:
    """A book open towards the viewer, its spine's foot on reference ``at``. ``marks`` highlights text rows, ``{row:
    colour}``; ``sweep`` is ``(row, colour, second)``, a row filled on cue. ``note`` replaces the text of the right
    page with up to two written rows, and ``note_sweep``, ``(colour, second)``, highlights them on cue."""
    x, y = _point(at, "a book's foot")
    if not (checks.number(scale) and scale > 0):
        raise ToonDataError(f"a book's scale is over 0, got {scale!r}")
    marks = dict(marks or {})
    _marks(marks, BOOK_ROWS, "a book")
    if note is not None:
        _check_note(note, measure)
        if any(row >= PAGE_ROWS for row in marks):
            raise ToonDataError("a book's right page holds its note, so its marks stay on the left page")
    elif note_sweep is not None:
        raise ToonDataError("a note's sweep needs a note")
    if sweep is not None:
        row, colour, second = sweep
        rows = PAGE_ROWS if note is not None else BOOK_ROWS
        _marks({row: colour}, rows, "a sweep")
        _second(second)
    if note_sweep is not None:
        _colour(note_sweep[0], "a note's sweep")
        _second(note_sweep[1])
    wide, tall = fh(BOOK_W), fh(BOOK_H)
    g = cv.group(parent, id, x=fx(x), y=fy(y), scaleX=scale, scaleY=scale)
    cv.ellipse(g, -wide * 1.02, -fh(8), wide * 2.04, fh(18), "#000000", opacity=0.22)
    cv.rect(g, -wide, -tall - fh(8), 2 * wide, tall + fh(10), COVER, cv.ink, INK_W, radius=fh(5))
    bow = fh(9)
    for side in (-1, 1):
        far = side * (wide - fh(12))
        cv.path(
            g,
            f"M 0 {-tall + fh(4)} Q {far / 2} {-tall - bow} {far} {-tall + fh(4)} L {far} {-fh(8)} "
            f"Q {far / 2} {-fh(8) - bow} 0 {-fh(4)} Z",
            PAGE,
            cv.ink,
            FINE_W,
        )
    shade = cv.grad("toon-book-gutter", [(0.0, "#00000000"), (0.5, "#00000044"), (1.0, "#00000000")], (0, 0, 1, 0))
    cv.rect(g, -fh(26), -tall + fh(2), fh(52), tall - fh(8), shade)
    for row in range(BOOK_ROWS):
        if note is not None and row >= PAGE_ROWS:
            break
        left, top, width = _row_at(row)
        if row in marks:
            _band(cv, g, left, top, width, marks[row], None, 0.0, "")
        if sweep is not None and sweep[0] == row:
            _band(cv, g, left, top, width, sweep[1], float(sweep[2]), SWEEP, f"{id}-sweep")
        cv.rect(g, left, top, width, fh(4.5), SCRAWL, radius=fh(2))
    for k, (top, row_text) in enumerate(_note_rows(note or (), tall)):
        width = measure(row_text, NOTE_SIZE) if measure else 0.0
        if note_sweep is not None:
            strip = cv.group(g, f"{id}-sweep-{k}", x=fh(NOTE_LEFT), y=top, anchorX=0, anchorY=0, start=note_sweep[1])
            cv.rect(strip, 0, 0, width + fh(6), NOTE_HIGH, note_sweep[0], radius=fh(3))
            cv.keys(strip, "scaleX", [(note_sweep[1], 0.02), (note_sweep[1] + SWEEP, 1.0)], local=False)
        cv.text(
            g,
            cv.uid("note-text"),
            row_text,
            fh(NOTE_LEFT),
            top,
            round(fh(NOTE_WIDTH)),
            round(NOTE_HIGH),
            NOTE_SIZE,
            color=LETTER,
            align="start",
            wrap="none",
        )


@register("prop", "toon-shut-book", summary="The same book shut, lying on a surface")
def shut_book(cv: Canvas, parent, at: tuple[float, float] = BOOK_AT, scale: float = 1.0, id: str = "shut-book") -> None:
    """The book shut and lying flat, its foot on reference ``at``, its pages' edge towards the viewer."""
    x, y = _point(at, "a book's foot")
    if not (checks.number(scale) and scale > 0):
        raise ToonDataError(f"a book's scale is over 0, got {scale!r}")
    wide, tall = fh(250), fh(46)
    g = cv.group(parent, id, x=fx(x), y=fy(y), scaleX=scale, scaleY=scale)
    cv.ellipse(g, -wide * 1.04, -fh(7), wide * 2.08, fh(16), "#000000", opacity=0.22)
    cv.rect(g, -wide, -tall, 2 * wide, tall, COVER, cv.ink, INK_W, radius=fh(6))
    cv.rect(g, -wide + fh(14), -tall + fh(11), 2 * wide - fh(14), tall - fh(22), PAGE, cv.ink, FINE_W)
    for k in (1, 2):
        cv.rect(g, -wide + fh(14), -tall + fh(11) + k * fh(8), 2 * wide - fh(14), fh(1.2), "#c9c0ae")


@register("prop", "toon-highlighter", summary="A paw moving a highlighter along a line")
def highlighter(
    cv: Canvas,
    parent,
    at: tuple[float, float],
    paw: str,
    path: Sequence[tuple[float, float]] = (),
    scale: float = 1.0,
    id: str = "highlighter",
) -> None:
    """A marker whose tip is on frame point ``at``, in a paw of the colour ``paw``. ``path`` moves it, ``(seconds,
    x)`` keys on the frame."""
    x, y = _point(at, "a marker's tip")
    _colour(paw, "a marker's paw")
    if not (checks.number(scale) and scale > 0):
        raise ToonDataError(f"a marker's scale is over 0, got {scale!r}")
    times = [t for t, _ in path]
    if any(not (checks.number(t) and checks.number(v)) for t, v in path) or times != sorted(set(times)):
        raise ToonDataError(f"a marker's path is (seconds, x) pairs at rising times, got {path!r}")
    g = cv.group(parent, id, x=x, y=y, scaleX=scale, scaleY=scale)
    tilt = cv.group(g, cv.uid("g"), rotation=28)
    cv.path(tilt, "M -11 -6 L 11 -6 L 18 -36 L -18 -36 Z", MARKER_BODY, cv.ink, FINE_W)
    cv.rect(tilt, -22, -176, 44, 142, MARKER_BODY, cv.ink, INK_W, radius=9)
    cv.rect(tilt, -22, -214, 44, 46, MARKER_CAP, cv.ink, INK_W, radius=9)
    cv.ellipse(tilt, -46, -136, 92, 78, paw, cv.ink, INK_W)
    if path:
        cv.keys(g, "x", list(path), local=False)


@register(
    "prop", "toon-study-page", summary="One page in close-up, every row highlighted, its colour key in the margin"
)
def study_page(
    cv: Canvas,
    parent,
    heading: str,
    marks: Mapping[int, str],
    key: Sequence[tuple[str, str]],
    *,
    measure: Measure,
    id: str = "study-page",
) -> None:
    """A page filling the frame on a dark desk: ``heading``, :data:`SHEET_ROWS` rows of scrawl highlighted as ``marks``
    says, ``{row: colour}``, and ``key``, ``(colour, words)``, the reader's own legend for those colours."""
    if not (isinstance(heading, str) and heading.strip()):
        raise ToonDataError("a page needs a heading")
    _marks(marks, SHEET_ROWS, "a page")
    inner = SHEET_W - 2 * SHEET_MARGIN
    if measure(heading, 66.0) > inner:
        raise ToonDataError(f"a page's heading fits {inner} px at 66: {heading!r}")
    if not 1 <= len(key) <= 3:
        raise ToonDataError(f"a page's key has 1 to 3 rows, got {len(key)}")
    for colour, words in key:
        _colour(colour, "a key's colour")
        if measure(words, 44.0) > inner - 96:
            raise ToonDataError(f"a key's words fit {inner - 96} px at 44: {words!r}")
    g = cv.group(parent, id, x=540, y=960, anchorX=540, anchorY=960, rotation=-1.2)
    cv.rect(g, SHEET_X + 12, SHEET_Y + 14, SHEET_W, SHEET_H, "#000000", radius=10.0, opacity=0.3)
    cv.rect(g, SHEET_X, SHEET_Y, SHEET_W, SHEET_H, PAGE, cv.ink, INK_W, radius=10.0)
    left = SHEET_X + SHEET_MARGIN
    cv.text(
        g,
        cv.uid("page-text"),
        heading,
        left,
        SHEET_Y + 44,
        round(inner),
        90,
        66.0,
        color=LETTER,
        align="start",
        wrap="none",
    )
    for row in range(SHEET_ROWS):
        top = SHEET_Y + 170 + row * 62.0
        width = inner * ROW_LENGTHS[row % len(ROW_LENGTHS)]
        if row in marks:
            cv.rect(g, left - 12, top - 17, width + 24, 48.0, marks[row], radius=6.0)
        cv.rect(g, left, top + 2, width, 10.0, SCRAWL, radius=5.0)
    for k, (colour, words) in enumerate(key):
        top = SHEET_Y + 760 + k * 74.0
        cv.rect(g, left, top + 6, 72.0, 44.0, colour, cv.ink, FINE_W, radius=6.0)
        cv.text(
            g,
            cv.uid("page-text"),
            words,
            left + 96,
            top,
            round(inner - 96),
            60,
            44.0,
            color=LETTER,
            align="start",
            wrap="none",
        )


def _star(cx: float, cy: float, r: float) -> str:
    points = []
    for k in range(10):
        reach = r if k % 2 == 0 else r * 0.45
        angle = math.pi * (k / 5 - 0.5)
        points.append(f"{round(cx + reach * math.cos(angle), 2)} {round(cy + reach * math.sin(angle), 2)}")
    return "M " + " L ".join(points) + " Z"


@register("prop", "toon-quiz-sheet", summary="A folded sheet from an old school quiz, its result circled, a star on it")
def quiz_sheet(
    cv: Canvas,
    parent,
    title: Sequence[str],
    rule: str,
    result: str,
    *,
    measure: Measure,
    at: tuple[float, float] = (510.0, 945.0),
    scale: float = 1.0,
    tilt: float = 2.0,
    start: float | None = None,
    end: float | None = None,
    answers_lettered: bool = True,
    id: str = "quiz-sheet",
) -> None:
    """A sheet of old paper centred on frame point ``at``, showing its folds: its ``title`` rows, four circled answers,
    the ``rule`` that scores them and the ``result``, circled in red with a gold star. It is on from ``start`` to
    ``end``. ``answers_lettered=False`` leaves the letters out of the answers, for a sheet too small to read them."""
    x, y = _point(at, "a sheet's place")
    if not (checks.number(scale) and scale > 0 and checks.number(tilt)):
        raise ToonDataError(f"a sheet's scale is over 0 and its tilt a number, got {scale!r}, {tilt!r}")
    if not (isinstance(title, tuple | list) and 1 <= len(title) <= 2):
        raise ToonDataError(f"a sheet's title is 1 or 2 rows, got {title!r}")
    wide, tall = 800.0, 960.0
    inner = wide - 2 * SHEET_MARGIN
    for text, size in ((rule, 58.0), (result, 92.0), *((row, QUIZ_SIZE) for row in title)):
        if not (isinstance(text, str) and text.strip()) or measure(text, size) > inner:
            raise ToonDataError(f"a sheet's words fit {inner} px at {size}: {text!r}")
    timing = {key: value for key, value in (("start", start), ("end", end)) if value is not None}
    g = cv.group(parent, id, x=x, y=y, rotation=tilt, scaleX=scale, scaleY=scale, **timing)
    left, top = -wide / 2, -tall / 2
    cv.rect(g, left + 12, top + 14, wide, tall, "#000000", radius=6.0, opacity=0.3)
    cv.rect(g, left, top, wide, tall, OLD_PAGE, cv.ink, INK_W, radius=6.0)
    cv.rect(g, left, -1.5, wide, 3.0, FOLD)
    cv.rect(g, -1.5, top, 3.0, tall, FOLD)
    for hole in (-300.0, 300.0):
        cv.ellipse(g, left + 22, hole - 16, 32, 32, "#3b2b1e")
    margin = left + SHEET_MARGIN
    for k, row in enumerate(title):
        cv.text(
            g,
            cv.uid("quiz-text"),
            row,
            margin,
            top + 56 + k * 70,
            round(inner),
            72,
            QUIZ_SIZE,
            color=LETTER,
            align="start",
            wrap="none",
        )
    for row in range(3):
        for column, letter in enumerate("ABCD"):
            cx, cy = margin + 76 + column * 170.0, top + 272 + row * 74.0
            ticked = column == 0 or (row == 1 and column == 2)
            cv.ellipse(g, cx - 28, cy - 28, 56, 56, CIRCLE if ticked else OLD_PAGE, LETTER, FINE_W)
            if answers_lettered:
                cv.text(
                    g,
                    cv.uid("quiz-text"),
                    letter,
                    cx - 28,
                    cy - 22,
                    56,
                    44,
                    34.0,
                    color="#ffffff" if ticked else LETTER,
                    wrap="none",
                )
    cv.text(
        g,
        cv.uid("quiz-text"),
        rule,
        margin,
        top + 520,
        round(inner),
        74,
        58.0,
        color=LETTER,
        align="start",
        wrap="none",
    )
    cv.text(g, cv.uid("quiz-text"), result, left, top + 640, round(wide), 112, 92.0, color=LETTER, wrap="none")
    cv.ellipse(g, -360, top + 610, 720, 170, cv.clear, CIRCLE, 12.0)
    cv.path(g, _star(wide / 2 - 104, top + 856, 74), STAR, cv.ink, FINE_W)
