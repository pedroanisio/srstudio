"""The dentist's surgery for Toon sketches: the room, a lamp that swings on its arm, a tray of instruments for a signed
ledge to carry, the photograph of one tooth, the probe, the close-up of a bib, and the darkness that closes round a
face when a check-up turns into an interrogation. The lamp, the probe and the bib are timed on the sketch's clock and
drawn from ordinary shapes, so a still shows them at rest.
"""

from __future__ import annotations

from . import _toon_care_contracts as tc
from . import checks
from .canvas import Canvas
from .registry import register
from .toon import FINE_W, INK_W, ToonDataError, fh, fx, fy
from .toon_sets import _line, cycle_keys

__all__ = ["bib_insert", "darkness", "dental_lamp", "dental_tray", "probe", "surgery", "tooth_photo"]

Point = tuple[float, float]

WALL = (("0", "#e8f3ee"), ("1", "#cfe3dc"))
TILE, DADO = "#bcd6cd", "#8fc1b4"
HEADREST, HEADREST_LIGHT = "#3d6c7a", "#55899a"
LIGHTBOX, LIGHTBOX_FILM = "#f4fbff", "#2c3540"
CUPBOARD, CUPBOARD_GLASS = "#f2efe6", "#c9e2e6"
JARS = ("#f6efd9", "#e6c9a8", "#b9d8c9")
VIEWS = ("chair", "cupboards")
LAMP_ARM, LAMP_BODY, LAMP_GLASS = "#d7dde2", "#b7c1c9", "#fff6c9"
SWING_PERIOD = 1.6  # seconds per swing of the lamp
TRAY, TRAY_RIM, STEEL = "#dfe5ea", "#aeb8c0", "#8e9aa4"
COTTON = "#fbfaf4"
PHOTO, PHOTO_DARK, TOOTH, STAIN = "#fffdf7", "#1e2230", "#f5efdc", "#7c5a2e"
BIB, BIB_LINE, CHAIN, BLOOD, BLOOD_DARK = "#d4ecf4", "#b4d6e2", "#9aa6ae", "#c8141e", "#8c0c14"
DARK = "#0b1024"
DROP_FALL = 0.32  # seconds the drop takes to reach the bib
SLIDE = 0.28  # seconds the photograph and the probe take to arrive


def _point(at: object, what: str) -> Point:
    if not (isinstance(at, tuple | list) and len(at) == 2 and all(checks.number(v) for v in at)):
        raise ToonDataError(f"{what} is a reference point (x, y), got {at!r}")
    return float(at[0]), float(at[1])


def _span(start: float, end: float, what: str) -> None:
    if not (checks.number(start) and checks.number(end) and 0 <= start < end):
        raise ToonDataError(f"{what} needs 0 <= start < end, got {start}..{end}")


@register(
    "location",
    "toon-surgery",
    contract=tc.contract('toon-surgery'),
    summary="A dentist's surgery from either side: the chair, or the cupboards",
)
def surgery(cv: Canvas, parent, view: str = "chair") -> None:
    """The wall in pale tile to a teal dado. ``view`` ``"chair"`` looks at the patient: the headrest behind the
    character and a lit box of X-rays at the right. ``"cupboards"`` looks back at the dentist: glass-fronted cupboards
    of jars and a framed certificate."""
    if view not in VIEWS:
        raise ToonDataError(f"a surgery's view is one of {VIEWS}, got {view!r}")
    g = cv.group(parent, cv.uid("g"))
    cv.rect(g, 0, 0, cv.width, cv.height, cv.grad("toon-surgery-wall", [(float(o), c) for o, c in WALL], (0, 0, 0, 1)))
    for y in range(120, 700, 74):
        cv.rect(g, 0, fy(y), cv.width, fh(3), TILE, cv.clear, 0, radius=0)
    for x in range(0, 620, 74):
        cv.rect(g, fx(x), fy(40), fh(3), fh(660), TILE, cv.clear, 0, radius=0)
    cv.rect(g, fx(-10), fy(700), fh(620), fh(200), DADO, cv.ink, FINE_W, radius=0)
    if view == "chair":
        cv.rect(g, fx(386), fy(420), fh(190), fh(236), LIGHTBOX, cv.ink, INK_W * 0.8, radius=fh(6))
        cv.rect(g, fx(404), fy(440), fh(154), fh(196), LIGHTBOX_FILM, cv.clear, 0, radius=fh(4))
        for i in range(4):
            cv.ellipse(g, fx(420 + i * 32), fy(500), fh(26), fh(70), "#dfe7ee", opacity=0.82)
        cv.rect(g, fx(16), fy(300), fh(300), fh(640), HEADREST, cv.ink, INK_W * 0.8, radius=fh(110))
        cv.rect(g, fx(36), fy(320), fh(260), fh(240), HEADREST_LIGHT, cv.clear, 0, radius=fh(90), opacity=0.6)
        return
    for x in (-30, 400):
        cv.rect(g, fx(x), fy(330), fh(210), fh(300), CUPBOARD, cv.ink, INK_W * 0.8, radius=fh(6))
        cv.rect(g, fx(x + 14), fy(344), fh(182), fh(272), CUPBOARD_GLASS, cv.ink, FINE_W, radius=fh(3))
        cv.rect(g, fx(x + 14), fy(476), fh(182), fh(6), CUPBOARD, cv.clear, 0, radius=0)
        for k, tint in enumerate(JARS):
            cv.rect(g, fx(x + 26 + k * 58), fy(410), fh(44), fh(66), tint, cv.ink, FINE_W, radius=fh(8))
            cv.rect(g, fx(x + 22 + k * 58), fy(400), fh(52), fh(14), CUPBOARD, cv.ink, FINE_W * 0.7, radius=fh(3))


@register(
    "prop",
    "toon-dental-lamp",
    contract=tc.contract('toon-dental-lamp'),
    summary="A dentist's lamp on a long arm, swinging, with a hand on it if asked",
)
def dental_lamp(
    cv: Canvas,
    parent,
    pivot: Point = (712, 30),
    angle: float = 34.0,
    swing: float = 9.0,
    end: float = 0.0,
    hand: str | None = None,
    id: str = "dental-lamp",
) -> None:
    """The arm hangs from reference ``pivot`` turned ``angle`` degrees, the lamp at its end facing the character, and
    swings ``swing`` degrees each way from the first frame to ``end``; a still (``end`` 0) hangs at ``angle``. ``hand``
    is a ``#rrggbb`` colour: an arm reaching in from the side, its paw on the lamp's rim."""
    x, y = _point(pivot, "a lamp's pivot")
    if not (checks.number(angle) and checks.number(swing) and 0 <= swing <= 30):
        raise ToonDataError(f"a lamp's angle is a number and its swing 0 to 30 degrees, got {angle!r}, {swing!r}")
    if not (checks.number(end) and end >= 0):
        raise ToonDataError(f"a lamp's end is a number of seconds >= 0, got {end!r}")
    g = cv.group(parent, id, x=fx(x), y=fy(y), rotation=angle)
    cv.rect(g, -fh(9), 0, fh(18), fh(470), LAMP_ARM, cv.ink, FINE_W, radius=fh(8))
    cv.ellipse(g, -fh(16), -fh(16), fh(32), fh(32), LAMP_BODY, cv.ink, FINE_W)
    cv.ellipse(g, -fh(92), fh(440), fh(184), fh(92), LAMP_BODY, cv.ink, INK_W * 0.8)
    cv.ellipse(g, -fh(72), fh(466), fh(144), fh(54), LAMP_GLASS, cv.ink, FINE_W)
    if hand is not None:
        cv.rect(g, fh(84), fh(466), fh(600), fh(46), hand, cv.ink, INK_W * 0.7, radius=fh(20))
        cv.ellipse(g, fh(58), fh(458), fh(62), fh(62), hand, cv.ink, INK_W * 0.7)
        for k in range(3):
            cv.ellipse(g, fh(50 + k * 4), fh(452 + k * 22), fh(34), fh(24), hand, cv.ink, FINE_W)
    if end and swing:
        keys = cycle_keys([(0.0, angle - swing), (SWING_PERIOD / 2, angle + swing)], SWING_PERIOD, 0.0, end)
        cv.keys(g, "rotation", keys, kind="sine-in-out", local=False)


@register(
    "prop",
    "toon-dental-tray",
    contract=tc.contract('toon-dental-tray'),
    summary="A steel tray of instruments and cotton rolls, for a ledge to carry",
)
def dental_tray(cv: Canvas, parent, x: float = 150.0, y: float = 842.0) -> None:
    """A tray standing on the surface at reference (``x``, ``y``): a mirror, a probe, and two rolls of cotton."""
    if not (checks.number(x) and checks.number(y)):
        raise ToonDataError(f"a tray stands at a reference point, got {x!r}, {y!r}")
    g = cv.group(parent, cv.uid("g"))
    cv.rect(g, fx(x), fy(y - 30), fh(330), fh(30), TRAY, cv.ink, INK_W * 0.7, radius=fh(6))
    cv.rect(g, fx(x + 8), fy(y - 28), fh(314), fh(6), TRAY_RIM, cv.clear, 0, radius=fh(3))
    _line(cv, g, [(x + 26, y - 40), (x + 150, y - 36)], 7.0, STEEL)
    cv.ellipse(g, fx(x + 8), fy(y - 56), fh(34), fh(34), STEEL, cv.ink, FINE_W)
    _line(cv, g, [(x + 170, y - 38), (x + 268, y - 42), (x + 278, y - 56)], 5.0, STEEL)
    for i in range(2):
        cv.rect(g, fx(x + 284 + i * 8), fy(y - 66 + i * 20), fh(36), fh(18), COTTON, cv.ink, FINE_W * 0.7, radius=fh(9))


@register(
    "prop",
    "toon-tooth-photo",
    contract=tc.contract('toon-tooth-photo'),
    summary="A photograph of one bad tooth, sliding in from the right",
)
def tooth_photo(
    cv: Canvas, parent, at: Point = (432, 620), start: float = 0.0, end: float = 0.0, id: str = "tooth-photo"
) -> None:
    """The print centred on reference ``at``, tilted a little, sliding in from the right at ``start`` and staying until
    ``end``; a still (``end`` 0) shows it in place."""
    x, y = _point(at, "a photograph's place")
    if end:
        _span(start, end, "a photograph")
    timed = {"start": start, "end": end} if end else {}
    g = cv.group(parent, id, x=fx(x), y=fy(y), rotation=6, **timed)
    w, h = fh(250), fh(280)
    cv.rect(g, -w / 2 + fh(7), -h / 2 + fh(8), w, h, "#1b1430", cv.clear, 0, radius=fh(4), opacity=0.2)
    cv.rect(g, -w / 2, -h / 2, w, h, PHOTO, cv.ink, INK_W * 0.8, radius=fh(4))
    cv.rect(g, -w / 2 + fh(16), -h / 2 + fh(16), w - fh(32), h - fh(56), PHOTO_DARK, cv.clear, 0, radius=fh(2))
    for dx in (-54, 6):
        cv.rect(g, fh(dx), -fh(26), fh(48), fh(96), TOOTH, cv.ink, FINE_W, radius=fh(20))
    cv.rect(g, -fh(70), -fh(104), fh(140), fh(104), TOOTH, cv.ink, FINE_W, radius=fh(34))
    cv.rect(g, -fh(52), -fh(12), fh(104), fh(24), TOOTH, cv.clear, 0, radius=fh(4))
    cv.ellipse(g, -fh(34), -fh(78), fh(58), fh(48), STAIN)
    cv.ellipse(g, fh(30), -fh(64), fh(20), fh(18), STAIN, opacity=0.8)
    if end:
        cv.keys(g, "x", [(start, fx(760)), (start + SLIDE, fx(x))], hold=False, local=False)


@register(
    "prop",
    "toon-probe",
    contract=tc.contract('toon-probe'),
    summary="A steel dental probe coming in from the right to a point, once",
)
def probe(cv: Canvas, parent, tip: Point = (232, 610), start: float = 0.0, end: float = 0.0, id: str = "probe") -> None:
    """A probe with its hooked tip on reference ``tip``, its handle running out of frame to the right, arriving at
    ``start`` and gone at ``end``; a still (``end`` 0) shows it in place."""
    x, y = _point(tip, "a probe's tip")
    if end:
        _span(start, end, "a probe")
    timed = {"start": start, "end": end} if end else {}
    g = cv.group(parent, id, x=fx(x), y=fy(y), rotation=-14, **timed)
    cv.rect(g, fh(2), -fh(5), fh(202), fh(10), STEEL, cv.ink, FINE_W * 0.6, radius=fh(4))
    cv.rect(g, fh(196), -fh(13), fh(420), fh(26), TRAY, cv.ink, FINE_W, radius=fh(10))
    cv.rect(g, 0, -fh(18), fh(8), fh(22), STEEL, cv.ink, FINE_W * 0.5, radius=fh(3))
    if end:
        cv.keys(g, "x", [(start, fx(x + 150)), (start + SLIDE, fx(x))], hold=False, local=False)


@register(
    "prop",
    "toon-bib-insert",
    contract=tc.contract('toon-bib-insert'),
    summary="The whole frame: a paper bib in close-up, and one drop landing on it",
)
def bib_insert(cv: Canvas, parent, start: float, end: float, skin: str = "#7fcf6b", id: str = "bib-insert") -> None:
    """A full-frame insert from ``start`` to ``end``: the wearer's ``skin`` at the top, the bib's waffled paper and its
    chain across it, a drop of blood falling from the top and landing at the centre."""
    _span(start, end, "a bib")
    if end - start <= DROP_FALL:
        raise ToonDataError(f"a bib holds longer than the drop's {DROP_FALL} s fall, got {start}..{end}")
    g = cv.group(parent, id, start=start, end=end)
    cv.rect(g, 0, 0, cv.width, cv.height, BIB)
    for k in range(1, 12):
        cv.rect(g, 0, k * cv.height / 12, cv.width, fh(2), BIB_LINE, cv.clear, 0, radius=0)
        cv.rect(g, k * cv.width / 12, 0, fh(2), cv.height, BIB_LINE, cv.clear, 0, radius=0)
    cv.rect(g, 0, 0, cv.width, fh(250), skin, cv.ink, INK_W, radius=0)
    for k in range(13):
        cv.ellipse(
            g, cv.width * (k + 1) / 14 - fh(13), fh(212 + abs(k - 6) * 8), fh(26), fh(26), cv.clear, CHAIN, FINE_W * 1.6
        )
    cx, cy = cv.width / 2, cv.height / 2
    land = start + DROP_FALL
    falling = cv.group(g, f"{id}-drop", x=cx, y=cy, start=start, end=land)
    cv.ellipse(falling, -fh(26), -fh(44), fh(52), fh(70), BLOOD, cv.ink, FINE_W)
    cv.keys(falling, "y", [(start, fh(80)), (land, cy)], hold=False, local=False)
    mark = cv.group(g, f"{id}-mark", x=cx, y=cy, start=land, end=end)
    cv.ellipse(mark, -fh(66), -fh(58), fh(132), fh(116), BLOOD, BLOOD_DARK, FINE_W)
    for dx, dy, r in ((-96, 30, 14), (88, -44, 10), (60, 74, 8)):
        cv.ellipse(mark, fh(dx - r), fh(dy - r), fh(2 * r), fh(2 * r), BLOOD, BLOOD_DARK, FINE_W * 0.6)


def darkness(
    cv: Canvas, parent, centre: Point, start: float, stop: float, end: float, drift: float = 0.0, id: str = "darkness"
) -> None:
    """The room going dark round a pool of light on reference ``centre``, fading in at ``start`` and out at ``stop``
    (``stop`` at or after ``end`` stays dark). ``drift`` carries the pool that many reference pixels each way, in time
    with the lamp."""
    x, y = _point(centre, "the light's centre")
    _span(start, end, "darkness")
    if not (checks.number(stop) and stop > start and checks.number(drift) and drift >= 0):
        raise ToonDataError(f"darkness needs a stop after its start and a drift >= 0, got {stop!r}, {drift!r}")
    g = cv.group(parent, id, opacity=0.0)
    keys = [(0.0, 0.0)] if start else []
    keys += [(start, 0.0), (start + 0.3, 1.0)]
    if stop < end:
        keys += [(stop, 1.0), (stop + 0.2, 0.0)]
    cv.keys(g, "opacity", keys, hold=False, local=False)
    pool = cv.group(g, cv.uid("g"), x=fx(x), y=fy(y))
    size = fh(1500)
    paint = cv.rgrad(
        "toon-surgery-dark", ((0, DARK + "00"), (0.13, DARK + "00"), (0.24, DARK + "f2"), (1, DARK + "fa"))
    )
    cv.ellipse(pool, -size, -size, 2 * size, 2 * size, paint)
    if drift:
        a, b = fx(x - drift), fx(x + drift)
        cv.keys(pool, "x", cycle_keys([(0.0, a), (SWING_PERIOD / 2, b)], SWING_PERIOD, 0.0, end), kind="sine-in-out",
                local=False)  # fmt: skip
