"""Cutout, what the hands are busy with: a CV folder, a phone six years deep, a coat, a door.

Each prop is drawn at ``x``, ``y`` in its parent's pixels and keyed on the episode's clock. Light comes from the top
left, as in every Cutout set, so each contact shadow falls down and to the right. Every refusal is a
:class:`CutoutHandedError`.
"""

from __future__ import annotations

from collections.abc import Sequence

from . import checks, look
from .canvas import Canvas
from .errors import SrstudioError
from .registry import register

__all__ = ["CutoutHandedError", "big_thumb", "cafe_door", "coat_over", "cv_folder", "phone_post"]

MANILA = "#E2C07A"
MANILA_DARK = "#C49F58"
PAGE = "#FBFAF2"
SHADOW = "#2A2018CC"


class CutoutHandedError(SrstudioError, ValueError):
    """A prop asked for with arguments it cannot be drawn from."""


def _check_scale(scale) -> None:
    checks.positive(scale, CutoutHandedError, f"scale must be a positive number, got {scale!r}")


def _check_spans(spans, name: str) -> None:
    checks.spans(
        spans, CutoutHandedError, lambda s: f"{name} are rising spans, got {s!r}", ordered=f"{name} run in order"
    )


@register("prop", "cv-folder", style="cutout", summary="A manila CV folder on a desk: shut, or open on a page, on cue")
def cv_folder(
    cv: Canvas,
    parent,
    x=540,
    y=1200,
    *,
    open_spans: Sequence[tuple[float, float]] = (),
    label: str = "CV",
    scale: float = 1.0,
    id: str = "cv-folder",
):
    """The folder's centre is (``x``, ``y``), 460 wide shut and 760 open. ``open_spans`` are when it lies open, in
    rising order; it is shut the rest of the time. ``label`` (1 to 8 characters) is on its cover."""
    cv.require_font("a folder's label is set in it", CutoutHandedError)
    _check_scale(scale)
    _check_spans(open_spans, "open spans")
    if not isinstance(label, str) or not 0 < len(label.strip()) <= 8:
        raise CutoutHandedError(f"a folder's label has 1 to 8 characters, got {label!r}")
    ink = cv.ink
    g = cv.group(parent, id, x=x, y=y, scaleX=scale, scaleY=scale, rotation=-1.5)
    shut = cv.group(g, f"{id}-shut")
    look.pool(cv, shut, f"{id}-shut-contact", SHADOW, -226, 112, 480, 66, opacity=0.5)
    cv.path(shut, "M-230 -130 L-230 -168 Q-228 -176 -216 -176 L-70 -176 Q-58 -176 -54 -160 L-46 -130Z",
            MANILA_DARK, ink, 4)  # fmt: skip
    cv.rect(shut, -230, -134, 460, 280, MANILA, ink, 4, radius=8)
    cv.rect(shut, -210, -116, 170, 8, "#F4E3B4", radius=4, opacity=0.8)
    cv.rect(shut, -110, -56, 220, 110, PAGE, ink, 3, radius=6)
    cv.text(shut, f"{id}-label", label, -110, -56, 220, 110, 64, ink)
    wide = cv.group(g, f"{id}-open")
    cv.gate(wide, list(open_spans))
    look.pool(cv, wide, f"{id}-open-contact", SHADOW, -376, 112, 780, 66, opacity=0.5)
    cv.rect(wide, -380, -146, 380, 292, MANILA, ink, 4, radius=8)
    cv.rect(wide, 0, -146, 380, 292, MANILA, ink, 4, radius=8)
    cv.rect(wide, 24, -130, 330, 262, PAGE, ink, 3)
    cv.rect(wide, 48, -110, 76, 90, "#B9C9D2", ink, 3)
    cv.rect(wide, 142, -106, 180, 16, ink)
    for k in range(3):
        cv.line(wide, 142, -72 + k * 24, 330, -72 + k * 24, "#8C8C8C", 7)
    for k in range(4):
        cv.line(wide, 48, 8 + k * 30, 330 if k % 3 != 2 else 230, 8 + k * 30, "#8C8C8C", 7)
    cv.gate(shut, _gaps(open_spans))
    return g


def _gaps(spans: Sequence[tuple[float, float]]) -> list[tuple[float, float]]:
    """The time outside ``spans``, from 0, for a state shown when the other is not."""
    out, last = [], 0.0
    for a, b in spans:
        if a > last:
            out.append((last, a))
        last = b
    out.append((last, 3600.0))
    return out


HEART = ("M0 34 C-16 18 -44 2 -44 -18 C-44 -36 -30 -44 -18 -44 C-10 -44 -4 -40 0 -32 C4 -40 10 -44 18 -44 "
         "C30 -44 44 -36 44 -18 C44 2 16 18 0 34Z")  # fmt: skip
RED = "#E0314B"
GRAY_TEXT = "#6B6B6B"
POST_PHOTO = (-360, -580, 720, 760)  # x, y, width, height of the photo in the phone's pixels
POST_HEART = (262, 262)  # the heart's centre in the phone's pixels
MESSAGE_LINES = 4
MESSAGE_CHARS = 30


def _photo(cv: Canvas, g, id: str) -> None:
    """A dish held up to the lens, head out of frame: the way these are taken."""
    ink = cv.ink
    x, y, w, h = POST_PHOTO
    cv.rect(g, x, y, w, h, "#E9D8B4")
    for yy in range(y + 95, y + h, 95):
        cv.line(g, x, yy, x + w, yy, "#D9C69C", 3)
    for xx in range(x + 120, x + w, 120):
        cv.line(g, xx, y, xx, y + h, "#D9C69C", 3)
    cv.path(g, "M-64 -580 L64 -580 L72 -526 Q0 -470 -72 -526Z", "#E8C4A0", ink, 5)
    cv.path(g, "M-250 180 L-262 -400 Q-262 -480 -170 -500 L-72 -530 Q0 -470 72 -530 L170 -500 Q262 -480 262 -400 "
               "L250 180Z", "#8FA7C4", ink, 5)  # fmt: skip
    for fx, fy in [(-190, -420), (-60, -400), (80, -440), (190, -370), (-160, -300), (0, -310), (130, -280)]:
        cv.ellipse(g, fx - 21, fy - 21, 42, 42, "#E5EDF5", opacity=0.9)
    cv.rect(g, -300, -230, 600, 200, "#CFDDE8", ink, 5, radius=44)
    cv.rect(g, -335, -180, 70, 60, "#CFDDE8", ink, 5, radius=18)
    cv.rect(g, 265, -180, 70, 60, "#CFDDE8", ink, 5, radius=18)
    cv.ellipse(g, -275, -255, 550, 96, "#D39A45", ink, 5)
    for bx, by in [(-170, -220), (-60, -232), (70, -222), (170, -228), (-110, -196), (20, -198), (130, -198)]:
        cv.ellipse(g, bx - 32, by - 13, 64, 26, "#B5772C")
    for side in (-1, 1):
        cv.path(g, f"M{side * 345} -170 Q{side * 400} -160 {side * 390} -70 Q{side * 330} -46 {side * 290} -74 "
                   f"L{side * 280} -160Z", "#C8564B", ink, 5)  # fmt: skip


@register("prop", "phone-post", style="cutout", summary="A phone, full frame, on an old post: a dish, an empty heart")
def phone_post(
    cv: Canvas,
    parent,
    x=540,
    y=900,
    *,
    name: str = "Diane",
    date: str = "March 2016",
    liked_at: float | None = None,
    message: tuple[str, str] | None = None,
    message_at: float | None = None,
    scale: float = 1.0,
    id: str = "phone-post",
):
    """The phone's centre is (``x``, ``y``), 780 by 1560. The heart is empty until ``liked_at``, when it fills with a
    tiny pop and the line under it counts one like. ``message`` (sender, text with its own line breaks) slides in from
    the top at ``message_at``. Text is the post's own: a date or a sender is any name the reel needs."""
    cv.require_font("a post's name and date are set in it", CutoutHandedError)
    _check_scale(scale)
    if not isinstance(name, str) or not 0 < len(name.strip()) <= 16:
        raise CutoutHandedError(f"a post's name has 1 to 16 characters, got {name!r}")
    if not isinstance(date, str) or not 0 < len(date.strip()) <= 16:
        raise CutoutHandedError(f"a post's date has 1 to 16 characters, got {date!r}")
    if liked_at is not None:
        checks.positive(liked_at, CutoutHandedError, f"liked_at is a time in seconds, got {liked_at!r}")
    if (message is None) != (message_at is None):
        raise CutoutHandedError("a message needs both its text and its time")
    ink = cv.ink
    g = cv.group(parent, id, x=x, y=y, scaleX=scale, scaleY=scale)
    cv.rect(g, -390, -780, 780, 1560, "#1E2428", ink, 6, radius=72)
    cv.rect(g, -360, -744, 720, 1488, PAGE, radius=42)
    cv.ellipse(g, -340, -690, 84, 84, "#D8A7B1", ink, 4)
    cv.text(g, f"{id}-name", name, -232, -688, 460, 80, 50, ink, align="start")
    _photo(cv, g, id)
    hx, hy = POST_HEART
    cv.path(cv.group(g, f"{id}-heart-empty", x=hx, y=hy, scaleX=1.3, scaleY=1.3), HEART, stroke=ink, sw=6)
    never = cv.group(g, f"{id}-no-likes")
    cv.text(
        never, f"{id}-no-likes-text", "Be the first to like this.", -340, 232, 540, 60, 40, GRAY_TEXT, align="start"
    )
    cv.text(g, f"{id}-date", date, -340, 300, 560, 56, 36, GRAY_TEXT, align="start")
    if liked_at is not None:
        cv.gate(never, [(0, liked_at)])
        liked = cv.group(g, f"{id}-liked")
        cv.gate(liked, [(liked_at, liked_at + 100000)])
        heart = cv.group(liked, f"{id}-heart-red", x=hx, y=hy)
        pop = [(liked_at, 0.6), (liked_at + 0.09, 2.0), (liked_at + 0.22, 1.3)]
        cv.keys(heart, "scaleX", pop, hold=False)
        cv.keys(heart, "scaleY", pop, hold=False)
        cv.path(heart, HEART, RED, ink, 4)
        cv.text(liked, f"{id}-one-like", "1 like", -340, 232, 540, 60, 40, ink, align="start")
    if message is not None and message_at is not None:
        sender, text = message
        rows = text.split("\n")
        if not 0 < len(sender.strip()) <= 16 or len(rows) > MESSAGE_LINES or max(map(len, rows)) > MESSAGE_CHARS:
            raise CutoutHandedError(
                f"a message has a sender of 1 to 16 characters and up to {MESSAGE_LINES} lines of "
                f"{MESSAGE_CHARS} characters, got {message!r}"
            )
        toast = cv.group(g, f"{id}-message", y=-1300)
        cv.keys(toast, "y", [(0, -1300), (message_at, -1300), (message_at + 0.30, 0)], kind="cubic-out")
        cv.rect(toast, -342, -652, 684, 110 + 62 * len(rows), "#26323A", ink, 4, radius=30)
        cv.ellipse(toast, -314, -628, 60, 60, "#D8A7B1", ink, 3)
        cv.text(toast, f"{id}-sender", sender, -238, -632, 420, 62, 44, "#FFFFFF", align="start")
        for k, row in enumerate(rows):
            cv.text(toast, f"{id}-message-{k}", row, -314, -562 + 62 * k, 630, 60, 42, "#FFFFFF", align="start")
    return g


@register(
    "prop", "big-thumb", style="cutout", summary="A thumb, close to the lens, its tip on the point it is drawn at"
)
def big_thumb(
    cv: Canvas,
    parent,
    x=540,
    y=900,
    *,
    skin: str = "#F1D0AA",
    rotation: float = -30,
    scale: float = 1.0,
    id: str = "big-thumb",
):
    """The tip is at (``x``, ``y``) and the thumb runs 620 long from it, down and to the right at the default angle."""
    _check_scale(scale)
    ink = cv.ink
    g = cv.group(parent, id, x=x, y=y, scaleX=scale, scaleY=scale, rotation=rotation)
    cv.rect(g, -82, 0, 164, 760, skin, ink, 6, radius=82)
    cv.rect(g, -56, 16, 112, 136, "#FBE9D8", ink, 3.5, radius=40)
    cv.path(g, "M-46 300 Q0 314 46 300 M-40 330 Q0 342 40 330", stroke="#C49C78", sw=4)
    return g


COAT = "#A8875C"
COAT_DARK = "#8C6F49"


@register(
    "prop", "coat-over", style="cutout", summary="A long coat that goes on over an actor, one side, then the other"
)
def coat_over(
    cv: Canvas,
    parent,
    left_at: float = 0.2,
    right_at: float = 0.5,
    *,
    bottom: float = 470,
    color: str = COAT,
    id: str = "coat-over",
):
    """Drawn in the actor's own units, from the shoulders (y 116) to ``bottom``, so hang it on ``actor.group``. Each
    side wraps from the outside in over 0.25 s: the screen-left side at ``left_at``, the other at ``right_at``."""
    for at in (left_at, right_at):
        checks.positive(at, CutoutHandedError, f"a coat goes on at a time in seconds, got {at!r}")
    checks.positive(bottom - 200, CutoutHandedError, f"a coat's bottom is below the waist, got {bottom!r}")
    ink = cv.ink
    g = cv.group(parent, id)
    for side, at, name in ((-1, left_at, "left"), (1, right_at, "right")):
        half = cv.group(g, f"{id}-{name}", x=side * 88, scaleX=0.0)
        cv.gate(half, [(at, at + 100000)])
        cv.keys(half, "scaleX", [(at, 0.0), (at + 0.25, 1.0)], kind="sine-out")
        cv.path(half, f"M{side * 8} 124 Q{side * -40} 112 {side * -92} 116 L{side * -92} {bottom} "
                      f"L{side * 16} {bottom}Z", color, ink, 4.5)  # fmt: skip
        cv.path(half, f"M{side * -92} 116 L{side * -48} 118 L{side * -66} 206Z", COAT_DARK, ink, 3.5)
        cv.line(half, side * 2, 140, side * 34, 214, ink, 24)
        cv.line(half, side * 2, 140, side * 34, 214, color, 16)
        cv.rect(half, side * -50 - 22, 360, 44, 12, COAT_DARK, radius=4)
    return g


@register("prop", "cafe-door", style="cutout", summary="A glass café door with a bar handle, its sign read from inside")
def cafe_door(
    cv: Canvas,
    parent,
    x=-30,
    y=320,
    *,
    width: float = 240,
    height: float = 920,
    sign: str = "CLOSED",
    id: str = "cafe-door",
):
    """The door's top left is (``x``, ``y``). ``sign`` hangs on the glass: a door that reads OPEN to the street reads
    the other thing from the inside."""
    cv.require_font("a door's sign is set in it", CutoutHandedError)
    checks.positive(width, CutoutHandedError, f"width must be positive, got {width!r}")
    checks.positive(height, CutoutHandedError, f"height must be positive, got {height!r}")
    if not isinstance(sign, str) or not 0 < len(sign.strip()) <= 8:
        raise CutoutHandedError(f"a door's sign has 1 to 8 characters, got {sign!r}")
    ink = cv.ink
    g = cv.group(parent, id, x=x, y=y)
    cv.rect(g, -18, -18, width + 36, height + 36, "#6E4B32", ink, 5)
    cv.rect(g, 0, 0, width, height, "#8A5F42", ink, 4)
    cv.rect(g, 26, 26, width - 52, height - 240, "#C9DEE0", ink, 4)
    cv.path(g, f"M40 {height * 0.5:g} L{width * 0.55:g} 44 L{width - 40:g} 44 L40 {height * 0.62:g}Z", "#E4F0EE",
            opacity=0.55)  # fmt: skip
    cv.line(g, width - 30, height * 0.48, width - 30, height * 0.78, "#D9C49A", 12)
    cv.rect(g, 56, 56, width - 112, 62, PAGE, ink, 3, radius=6)
    cv.text(g, f"{id}-sign", sign, 56, 56, width - 112, 62, 30, ink)
    return g
