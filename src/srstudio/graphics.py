"""On-screen graphics: slates, cards, captions. All vector, all gated by hold keys."""

from __future__ import annotations

from collections.abc import Sequence

from .canvas import Canvas
from .registry import register

GOLD = "#E2BB72"
SLATE_INK = "#203638"
RED = "#BE5C51"


def _part_id(instance: str, default: str, name: str, *, own: bool = False) -> str:
    """Namespace a custom instance's children; keep the shipped default instance's public IDs.

    ``own`` marks a name the caller chose (an explicit ``prefix`` or ``text_id``): it is kept as given, so the
    caller that picked it also keeps it unique.
    """
    return name if own or instance == default else f"{instance}-{name}"


@register("graphic", "episode-slate", summary="Episode number badge and title, fading in and out in the first second")
def episode_slate(
    cv: Canvas,
    parent,
    number: str,
    title: str,
    *,
    x=60,
    y=65,
    w=430,
    h=78,
    bg=SLATE_INK,
    badge=GOLD,
    badge_h=54,
    number_color=SLATE_INK,
    title_color="#FFFFFF",
    title_x=80,
    title_w=330,
    title_size=29,
    radius=15,
    badge_radius=9,
    fade=(0.12, 0.72, 1.05),
    id="episode-slate",
):
    g = cv.group(parent, id, x=x, y=y)
    cv.keys(g, "opacity", [(0, 0), (fade[0], 1), (fade[1], 1), (fade[2], 0)], hold=False)
    cv.rect(g, 0, 0, w, h, bg, radius=radius)
    cv.rect(g, 12, 12, 55, badge_h, badge, radius=badge_radius)
    cv.text(g, _part_id(id, "episode-slate", "episode-number"), number, 12, 12, 55, badge_h, 27, number_color)
    cv.text(
        g, _part_id(id, "episode-slate", "episode-title"), title, title_x, 12, title_w, badge_h, title_size, title_color
    )
    return g


@register("graphic", "quiz-card", summary="Question card with a gold spine; a NOPE. line appears on the wrong answer")
def quiz_card(
    cv: Canvas,
    parent,
    label: str,
    question: str,
    show: tuple[float, float],
    verdict: str | None = None,
    verdict_span: tuple[float, float] | None = None,
    *,
    x=540,
    y=285,
    id="quiz-card",
):
    g = cv.group(parent, id, x=x, y=y, anchorX=300, anchorY=100)
    cv.gate(g, [show])
    cv.pop_in(g, show[0], from_=0.92, over=1.03, rise=0.18, settle=0.30)
    cv.rect(g, 7, 11, 600, 200, "#465453", radius=25, opacity=0.16)
    cv.rect(g, 0, 0, 600, 200, "#FDFCF7", SLATE_INK, 4, radius=25)
    cv.rect(g, 0, 0, 12, 200, GOLD, radius=6)
    cv.text(g, _part_id(id, "quiz-card", "quiz-label"), label, 30, 12, 540, 37, 23, "#657975")
    cv.text(g, _part_id(id, "quiz-card", "quiz-question"), question, 28, 48, 544, 103, 64, SLATE_INK)
    if verdict:
        nope = cv.text(g, _part_id(id, "quiz-card", "wrong-label"), verdict, 80, 145, 440, 45, 31, RED)
        cv.gate(nope, [verdict_span or show])
    return g


@register("graphic", "answer-bubble", summary="Fast number reveal with motion streaks and a 9° tilt")
def answer_bubble(
    cv: Canvas, parent, value: str, show: tuple[float, float], *, x=876, y=660, rotation=9, id="instant-answer"
):
    g = cv.group(parent, id, x=x, y=y, anchorX=100, anchorY=80, rotation=rotation)
    cv.gate(g, [show])
    cv.pop_in(g, show[0], from_=0.45, over=1.15, rise=0.085, settle=0.195)
    for yy, ll in [(25, 40), (75, 58), (130, 37)]:
        cv.line(g, -ll, yy, -8, yy, GOLD, 6)
    cv.ellipse(g, 0, 0, 200, 160, "#DBEAE0", SLATE_INK, 4)
    cv.text(g, _part_id(id, "instant-answer", "wrong-answer-number"), value, 7, 8, 186, 140, 81, SLATE_INK)
    return g


def _slide_up(cv, g, at, y):
    cv.keys(g, "y", [(0, y + 50), (at, y + 50), (at + 0.19, y - 8), (at + 0.32, y)], hold=False)


@register("graphic", "scorecard", summary="Dark end card with a heading and label/value rows that slides up")
def scorecard(
    cv: Canvas,
    parent,
    heading: str,
    rows: Sequence[tuple[str, str, str]],
    show: tuple[float, float],
    *,
    x=110,
    y=1540,
    w=860,
    row_h=80,
    heading_size=27,
    row_size=39,
    value_size=45,
    value_w=310,
    label_w=400,
    id="final-scorecard",
    prefix="score",
):
    """``rows`` = (label, value, value_colour); the height follows the row count."""
    h = 89 + row_h * len(rows) + 19
    own = prefix != "score"
    g = cv.group(parent, id, x=x, y=y)
    cv.gate(g, [show])
    _slide_up(cv, g, show[0], y)
    cv.rect(g, 7, 12, w, h, "#8C765C", radius=24, opacity=0.22)
    cv.rect(g, 0, 0, w, h, SLATE_INK, GOLD, 3, radius=24)
    cv.text(
        g,
        _part_id(id, "final-scorecard", f"{prefix}-heading", own=own),
        heading,
        35,
        15,
        w - 70,
        44,
        heading_size,
        "#BFCFCA",
    )
    cv.line(g, 42, 73, w - 42, 73, "#6B807B", 2)
    for i, (label, value, color) in enumerate(rows):
        yy = 89 + i * row_h
        cv.text(
            g,
            _part_id(
                id, "final-scorecard", f"{prefix}-{i}-label" if prefix != "score" else f"{label.lower()}-label", own=own
            ),
            label,
            45,
            yy,
            label_w,
            65,
            row_size,
            "#F7F4E9",
            "start",
        )
        cv.text(
            g,
            _part_id(
                id, "final-scorecard", f"{prefix}-{i}-value" if prefix != "score" else f"{label.lower()}-value", own=own
            ),
            value,
            w - value_w - 55,
            yy,
            value_w,
            65,
            value_size,
            color,
            "end",
        )
    return g


@register("graphic", "dashboard", summary="MULTITASKING: ACTIVE style status board with three label/value rows")
def dashboard(
    cv: Canvas,
    parent,
    heading: str,
    rows: Sequence[tuple[str, str]],
    show: tuple[float, float],
    *,
    x=95,
    y=1465,
    w=890,
    h=350,
    id="multitasking-dashboard",
    prefix="dashboard",
):
    own = prefix != "dashboard"
    g = cv.group(parent, id, x=x, y=y)
    cv.gate(g, [show])
    _slide_up(cv, g, show[0], y)
    cv.rect(g, 7, 12, w, h, "#8C765C", radius=24, opacity=0.22)
    cv.rect(g, 0, 0, w, h, SLATE_INK, GOLD, 3, radius=24)
    cv.text(
        g,
        _part_id(id, "multitasking-dashboard", f"{prefix}-heading", own=own),
        heading,
        35,
        15,
        w - 70,
        45,
        29,
        "#BFCFCA",
    )
    cv.line(g, 42, 77, w - 42, 77, "#6B807B", 2)
    for i, (label, value) in enumerate(rows):
        yy = 91 + i * 79
        cv.text(
            g,
            _part_id(id, "multitasking-dashboard", f"{prefix}-label-{i}", own=own),
            label,
            38,
            yy,
            370,
            61,
            34,
            "#F7F4E9",
            "start",
        )
        cv.text(
            g,
            _part_id(id, "multitasking-dashboard", f"{prefix}-value-{i}", own=own),
            value,
            423,
            yy,
            425,
            61,
            34,
            "#E6AA92",
            "end",
        )
    return g


@register("graphic", "notification", summary="Phone-style notification card with a red spine")
def notification(
    cv: Canvas, parent, index: int, who: str, status: str, show: tuple[float, float], *, x, y, id_prefix="notification"
):
    start = show[0]
    g = cv.group(parent, f"{id_prefix}-{index}", x=x, y=y)
    cv.gate(g, [show])
    cv.keys(g, "y", [(0, y + 22), (start, y + 22), (start + 0.13, y - 4), (start + 0.24, y)], hold=False)
    cv.pop_in(g, start, from_=0.94, over=1.02, rise=0.13, settle=0.24)
    cv.rect(g, 4, 7, 290, 120, "#5F675D", radius=19, opacity=0.16)
    cv.rect(g, 0, 0, 290, 120, "#FCFBF5", SLATE_INK, 3, radius=19)
    cv.rect(g, 0, 0, 8, 120, RED, radius=4)
    cv.text(g, f"{id_prefix}-person-{index}", who, 20, 10, 250, 35, 20, "#657975")
    cv.text(g, f"{id_prefix}-status-{index}", status, 15, 48, 260, 55, 24, RED)
    return g


@register(
    "graphic", "password-card", summary="Cream card: heading, big password, small footnote; pops on a spoken word"
)
def password_card(
    cv: Canvas,
    parent,
    heading: str,
    password: str,
    footnote: str,
    show: tuple[float, float],
    *,
    x=180,
    y=258,
    id="cafe-password-reveal",
    prefix="wifi",
):
    own = prefix != "wifi"
    g = cv.group(parent, id, x=x, y=y)
    cv.gate(g, [show])
    cv.pop_in(g, show[0], from_=0.93, over=1.025, rise=0.15, settle=0.28)
    cv.rect(g, 6, 9, 720, 200, "#624F3C", radius=22, opacity=0.16)
    cv.rect(g, 0, 0, 720, 200, "#FCF6E8", "#2D5753", 4, radius=22)
    cv.text(
        g, _part_id(id, "cafe-password-reveal", f"{prefix}-heading", own=own), heading, 30, 17, 660, 42, 29, "#628074"
    )
    cv.text(
        g,
        _part_id(id, "cafe-password-reveal", f"{prefix}-password", own=own),
        password,
        25,
        65,
        670,
        102,
        55,
        "#2D5753",
    )
    cv.text(
        g,
        _part_id(id, "cafe-password-reveal", f"{prefix}-no-spaces", own=own),
        footnote,
        30,
        163,
        660,
        26,
        18,
        "#A7794C",
    )
    return g


@register("graphic", "location-slate", summary="Small green banner such as LATER, AT THE PARK")
def location_slate(
    cv: Canvas,
    parent,
    text: str,
    show: tuple[float, float],
    *,
    x=62,
    y=72,
    id="new-location-slate",
    text_id="park-transition",
):
    own = text_id != "park-transition"
    g = cv.group(parent, id, x=x, y=y)
    cv.gate(g, [show])
    cv.rect(g, 0, 0, 460, 69, "#355C53", radius=13)
    cv.text(g, _part_id(id, "new-location-slate", text_id, own=own), text, 14, 9, 430, 51, 25, "#F2E7C6")
    return g


@register("graphic", "connected-card", summary="Status card with a green dot, heading and value")
def connected_card(
    cv: Canvas,
    parent,
    heading: str,
    value: str,
    show: tuple[float, float],
    *,
    x=200,
    y=285,
    id="park-connected-card",
    prefix="connected",
):
    own = prefix != "connected"
    g = cv.group(parent, id, x=x, y=y)
    cv.gate(g, [show])
    cv.rect(g, 5, 8, 680, 151, "#5A735E", radius=21, opacity=0.17)
    cv.rect(g, 0, 0, 680, 151, "#F7F4E4", "#426B5E", 3, radius=21)
    cv.ellipse(g, 31, 57, 21, 21, "#62976F")
    cv.text(
        g, _part_id(id, "park-connected-card", f"{prefix}-heading", own=own), heading, 61, 13, 578, 47, 29, "#426B5E"
    )
    cv.text(
        g, _part_id(id, "park-connected-card", f"{prefix}-password", own=own), value, 52, 64, 580, 67, 42, "#263F39"
    )
    return g


@register("graphic", "squeak-mark", summary="Comic SQUEAK! lettering with vibration arcs; pops in and wobbles")
def squeak_mark(
    cv: Canvas,
    parent,
    text: str,
    show: tuple[float, float],
    *,
    x,
    y,
    w=360,
    h=110,
    size=64,
    color="#F4D492",
    rotation=-8,
    wobble=4,
    rate=0.045,
    id="squeak-mark",
):
    """Centred on (``x``, ``y``) and visible inside ``show``.

    The rotation alternates ``rotation ± wobble`` every ``rate`` seconds."""
    start, end = show
    g = cv.group(parent, id, x=x, y=y, anchorX=w / 2, anchorY=h / 2)
    cv.gate(g, [show])
    cv.pop_in(g, start, from_=0.55, over=1.18, rise=0.07, settle=0.16)
    shake = [(0, rotation), (start, rotation)]
    n = max(1, int((end - start) / rate))
    shake += [(start + i * rate, rotation + (wobble if i % 2 else -wobble)) for i in range(1, n)]
    shake.append((end, rotation))
    cv.keys(g, "rotation", shake, hold=False)
    for side in (-1, 1):
        cx = w / 2 + side * (w / 2 + 6)
        for i, reach in enumerate((14, 30, 46)):
            cv.path(
                g,
                f"M{cx + side * reach:g} {h * 0.5 - 18 - i * 8:g} Q{cx + side * (reach + 14):g} {h * 0.5:g} "
                f"{cx + side * reach:g} {h * 0.5 + 18 + i * 8:g}",
                stroke=cv.ink,
                sw=6,
            )
    cv.text(
        g,
        f"{id}-text",
        text,
        0,
        0,
        w,
        h,
        size,
        color,
        strokeColor=cv.ink,
        strokeWidth=9,
        strokePosition="outside",
        weight="700",
    )
    return g


@register("graphic", "captions", summary="Outlined, shadowed subtitles; a highlight colours part of a line")
def captions(
    cv: Canvas,
    specs: Sequence[tuple[float, float, str, str]],
    *,
    x=35,
    y=1435,
    width=1010,
    height=180,
    size=53,
    weight: str | None = "700",
    line_height="1.14",
    color="#FFFFFF",
    stroke="#121415",
    stroke_width=8,
    shadow: str | None = "#00000066",
    highlight_color="#F4D492",
    highlights: dict[str, Sequence[tuple[str, bool]]] | None = None,
    layer_suffix="-caption",
):
    """``specs`` = (start, end, text, name).

    ``highlights[name]`` = [(text, is_highlighted), ...] splits a line into spans. ``color`` is the text,
    ``stroke`` its outline; ``shadow=None`` draws no drop shadow (dark text on a light stage)."""
    highlights = highlights or {}
    layers = []
    for start, end, text, name in specs:
        kw = dict(
            width=width,
            height=height,
            size=str(size),
            fontAsset=cv.font_asset,
            color=color,
            align="center",
            verticalAlign="middle",
            lineHeight=line_height,
            strokeColor=stroke,
            strokeWidth=stroke_width,
            strokePosition="outside",
        )
        if shadow:
            kw.update(shadowColor=shadow, shadowOffsetY=2, shadowBlur=1)
        if weight:
            kw["weight"] = weight
        asset = cv.assets.add_text(id=name, **kw)
        if name in highlights:
            for part, lit in highlights[name]:
                span = asset.add_span(color=highlight_color) if lit else asset.add_span()
                span.content = part
        else:
            asset.text = text
        layers.append(cv.comp.add_layer(id=f"{name}{layer_suffix}", asset=name, x=x, y=y, start=start, end=end))
    return layers
