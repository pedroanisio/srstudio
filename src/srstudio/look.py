"""The look primitives every style shares: measured text, a shot grade, a far plane out of focus, pools of light
and fades (ADR 0031).

A style keeps its own numbers (its grade, its blur, its colours, the prefix of every paint and effect id) and calls
these for the drawing, so a finish learned in one style is a call away in the next:

* :func:`wrap` breaks a text into lines the font draws within a width and refuses a text that does not fit, so a
  panel's lettering never spills; :func:`label` sets a line in its box, and :func:`text` sets one in an asset
  of its own with the weight, wrapping and overflow a style chooses;
* :func:`grade` applies a style's effects (bloom, vignette, grain...) to any node, a shot or a world group inside
  it; :func:`depth` is a group thrown out of focus for a set's far plane, and :func:`sheet` keeps a blur's frame
  edge covered on a reel that asks for :attr:`~srstudio.canvas.Canvas.bleed`;
* :func:`pool` is a soft radial light, :func:`fade` a band of colour thinning to nothing (haze, a shade at the
  frame's foot).
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from . import checks, fonts
from .canvas import Canvas
from .errors import SrstudioError

__all__ = ["FitError", "LookError", "REACH", "wrap", "label", "text", "grade", "sheet", "depth", "pool", "fade"]

REACH = 4.0  # blur radii past a drawing's edge that its blur still reads: the reach scene-render gives a blur


class LookError(SrstudioError, ValueError):
    """A grade or a far plane the look cannot make: no effect, a blur radius that is not positive."""


class FitError(SrstudioError, ValueError):
    """A text does not fit its box: a word wider than the box, or more lines than it holds."""


def wrap(font: bytes, text: str, size: float, width: float, max_lines: int) -> list[str]:
    """``text`` broken greedily into lines the font draws within ``width`` at ``size``; explicit newlines are
    kept. :class:`FitError` when a word alone is too wide or the text needs more than ``max_lines`` lines."""
    lines: list[str] = []
    for para in text.split("\n"):
        line = ""
        for word in para.split():
            trial = f"{line} {word}".strip()
            if fonts.text_width(font, trial, size) <= width:
                line = trial
                continue
            if not line:
                raise FitError(f"the word {word!r} is wider than {width:g} px at {size:g} px")
            lines.append(line)
            line = word
            if fonts.text_width(font, line, size) > width:
                raise FitError(f"the word {word!r} is wider than {width:g} px at {size:g} px")
        lines.append(line)
    if len(lines) > max_lines:
        raise FitError(f"{text!r} needs {len(lines)} lines at {size:g} px; the box holds {max_lines}")
    return lines


def label(cv: Canvas, parent, value: str, x, y, w, h, size, color, align: Any = "center"):
    """A text layer of ``value`` in the box ``x, y, w, h``."""
    return cv.text(parent, cv.uid("txt"), value, x, y, w, h, size, color=color, align=align)


def text(
    cv: Canvas,
    parent,
    value: str,
    x,
    y,
    w,
    h,
    size,
    color: str,
    *,
    weight: int | None = None,
    align: Any = "center",
    lines: int | None = None,
    wrap: str | None = None,
    line_height: str | None = None,
    overflow: str | None = None,
    asset: str = "text",
    layer: str = "layer",
):
    """``value`` set in the box ``x, y, w, h``: a text asset (id from ``asset``) and the layer that shows it (id
    from ``layer``). With ``lines`` it balances over at most that many lines (one line keeps it on one); ``wrap``
    chooses the wrapping outright. An option left ``None`` is not set, so the engine's default holds."""
    if wrap is None:
        wrap = "balance" if lines is not None and lines > 1 else "none"
    name = cv.uid(asset)
    cv.assets.add_text(
        id=name,
        text=value,
        width=w,
        height=h,
        size=size,
        fontAsset=cv.font_asset,
        weight=weight,
        color=color,
        align=align,
        verticalAlign="middle",
        wrap=wrap,
        lineHeight=line_height,
        maxLines=lines,
        overflow=overflow,
    )
    return parent.add_layer(id=cv.uid(layer), asset=name, x=x, y=y)


def grade(cv: Canvas, node, prefix: str, effects: Mapping[str, Mapping[str, Any]]):
    """``node`` (a shot, or the world group inside it) graded by ``effects``, ``{type: attrs}``, each declared as
    ``<prefix>-<type>``; returns ``node``."""
    if not effects:
        raise LookError("a grade needs at least one effect")
    return cv.apply(node, *(cv.effect(f"{prefix}-{kind}", kind, **attrs) for kind, attrs in effects.items()))


def sheet(cv: Canvas) -> dict[str, bool]:
    """The attribute that keeps a blurred group's edge on a reel with ``bleed``, none without it. The engine blurs a
    group in an offscreen the size of the frame, so what the group draws past the frame is gone before the blur reads
    it, and transparency comes in at the frame's edge. A ``threeD`` group is drawn on a sheet the size of what it
    draws; with no camera it lands where it was."""
    return {"threeD": True} if cv.bleed else {}


def _overscan(cv: Canvas, radius: float) -> dict[str, float]:
    """A far plane scaled about the frame's centre, so a drawing that stops at the frame reaches past it by its blur."""
    if not cv.bleed:
        return {}
    scale = 1 + 2 * REACH * radius / min(cv.width, cv.height)
    cx, cy = cv.width / 2, cv.height / 2
    return {"x": cx, "y": cy, "anchorX": cx, "anchorY": cy, "scaleX": scale, "scaleY": scale}


def depth(cv: Canvas, parent, name: str, radius: float, *, overscan: bool = False, moving: bool = False):
    """A group in ``parent`` thrown out of focus by a ``radius`` px blur (the effect ``name``): a set's far plane. On
    a reel with ``bleed`` it is drawn on a :func:`sheet`, and ``overscan`` also grows it past the frame: for a far plane
    painted exactly to the frame, whose bottom edge is hidden if it stops above the frame's centre. A far plane that
    is ``moving`` stays off the sheet: its bounds change every frame, and the sheets they ask for run the GPU out of
    memory over an encode. Lay a sharp plate of its own colour under it instead, so its edge shows no page."""
    if not (checks.number(radius) and radius > 0):
        raise LookError(f"a far plane's blur radius must be positive, got {radius}")
    if moving:
        far = cv.group(parent, cv.uid("g"))
    else:
        far = cv.group(parent, cv.uid("g"), **sheet(cv), **(_overscan(cv, radius) if overscan else {}))
    cv.apply(far, cv.effect(name, "blur", radius=radius))
    return far


def pool(cv: Canvas, parent, name: str, colour: str, x, y, w, h, opacity: float = 1.0):
    """A soft radial pool of ``colour`` in the box ``x, y, w, h`` (the gradient ``name``): a light, its spill on a
    floor or wall."""
    paint = cv.rgrad(name, [(0, colour), (1, colour[:7] + "00")])
    return cv.ellipse(parent, x, y, w, h, paint, opacity=opacity)


def fade(cv: Canvas, parent, name: str, colour: str, y0: float, y1: float, width: float, x: float = 0):
    """``colour`` at ``y0`` thinning to nothing at ``y1`` across ``width`` (the gradient ``name``): haze on a
    horizon, shade at the frame's foot."""
    top, bottom = (y0, y1) if y0 < y1 else (y1, y0)
    clear = colour[:7] + "00"
    stops = [(0, colour), (1, clear)] if y0 < y1 else [(0, clear), (1, colour)]
    return cv.rect(parent, x, top, width, bottom - top, cv.grad(name, stops, (0, 0, 0, 1)))
