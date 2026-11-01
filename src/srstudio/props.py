"""Set dressing and hand props, each a registered builder ``fn(cv, parent, ...) -> node``."""

from __future__ import annotations

import math
import random
from collections.abc import Sequence

from . import checks
from .canvas import Canvas
from .errors import SrstudioError
from .registry import register


class PropError(SrstudioError, ValueError):
    """A prop asked for with arguments it cannot be drawn from."""


# ---------------------------------------------------------------- office set dressing


def office_paints(cv: Canvas) -> dict[str, str]:
    """The eight gradients of the office, created once in the original order."""
    return {
        "wall": cv.grad(
            "cool-wall", [(0, "#A4B0B3"), (0.4, "#D9E2E2"), (0.7, "#E3E9E7"), (1, "#8D999F")], (0, 0, 1, 0.1)
        ),
        "warm_wall": cv.grad("warm-wall", [(0, "#B6AC9B"), (0.16, "#DFD0B6"), (1, "#D7C7AF")], (0, 0, 0.5, 1)),
        "desk": cv.grad(
            "wood-top", [(0, "#CEB08A"), (0.3, "#E7CDA2"), (0.65, "#E8CCA1"), (1, "#C4A07A")], (0, 0, 0.4, 1)
        ),
        "desk_front": cv.grad("wood-front", [(0, "#B49A7B"), (1, "#9F886E")], (0, 0, 1, 1)),
        "chair_black": cv.grad("leather-black", [(0, "#363737"), (0.42, "#262727"), (0.75, "#353634"), (1, "#191A1A")]),
        "chair_gray": cv.grad("leather-gray", [(0, "#93918B"), (0.6, "#85847F"), (1, "#6F706D")]),
        "leaf": cv.grad("leaf-green", [(0, "#69874B"), (0.55, "#8DA263"), (1, "#BAC18B")]),
        "paper": cv.grad("paper", [(0, "#FFFFFF"), (0.7, "#F9F8EF"), (1, "#D8D9CF")]),
    }


@register("prop", "papers", summary="A stack of documents with seeded random lines")
def papers(cv: Canvas, parent, x, y, scale=1, angle=0, seed=3):
    p = office_paints(cv)
    g = cv.group(parent, cv.uid("documents"), x=x, y=y, scaleX=scale, scaleY=scale, rotation=angle)
    cv.path(g, "M-12 11 L202 0 L287 126 L29 151Z", "#9C8D73", cv.clear, 0, opacity=0.22)
    cv.path(g, "M-9 6 L198 0 L277 121 L25 143Z", "#E1E1D7", cv.ink, 2)
    cv.path(g, "M-5 0 Q80 9 190 -5 Q217 55 280 114 L25 136Z", p["paper"], cv.ink, 2.7)
    cv.path(g, "M-5 0 Q78 29 151 18 L204 58 Q126 88 20 84Z", "#F3F3EA", "#72766D", 1.5)
    rng = random.Random(seed)
    for i in range(14):
        yy = 30 + i * 6.1
        xx = 12 + i * 0.84
        length = rng.uniform(110, 190)
        cv.line(g, xx, yy, xx + length, yy - 4, "#92968D", 1.5)
    cv.line(g, 20, 25, 86, 23, "#5C625D", 3)
    cv.line(g, 170, 109, 235, 105, "#72776D", 1.3)
    cv.line(g, 190, 116, 251, 112, "#72776D", 1.3)
    return g


@register("prop", "woodgrain", summary="Seeded grain strokes over a desk top")
def woodgrain(cv: Canvas, parent, y, height, seed=4):
    rng = random.Random(seed)
    for _ in range(34):
        yy = y + rng.random() * height
        xx = rng.uniform(-200, 800)
        ll = rng.uniform(220, 850)
        cv.path(
            parent,
            f"M{xx:.2f} {yy:.2f} Q{xx + ll * 0.4:.2f} {yy - 4:.2f} {xx + ll:.2f} {yy + 2:.2f}",
            stroke="#BA936D",
            sw=rng.uniform(0.8, 4),
            opacity=rng.uniform(0.035, 0.10),
        )


@register("prop", "office-art", summary="The framed abstract print on the office wall")
def office_art(cv: Canvas, parent):
    ink, clear = cv.ink, cv.clear
    cv.rect(parent, 301, 45, 424, 507, "#465052", radius=4, opacity=0.17)
    cv.path(parent, "M318 39 L729 50 L730 539 L321 541Z", "#222628", ink, 5)
    cv.path(parent, "M331 52 L715 62 L716 525 L334 527Z", "#EDEFE8", "#777E7D", 2)
    cv.path(
        parent,
        "M384 113 L502 100 Q592 105 623 178 L648 228 Q655 270 623 310 Q693 360 665 470 L392 469Z",
        "#D5D8CD",
        clear,
        0,
    )
    cv.path(
        parent,
        "M383 115 Q434 112 473 100 Q598 98 621 180 Q570 225 528 241 Q489 257 482 296 L386 301Z",
        "#CABBAB",
        clear,
        0,
    )
    cv.path(parent, "M383 116 L432 111 Q426 220 483 245 L480 299 L386 301Z", "#CDB391", clear, 0, opacity=0.7)
    cv.path(parent, "M621 179 Q670 251 640 296 Q613 331 573 343 L480 299 Q495 253 541 237Z", "#E9E4D2", clear, 0)
    cv.path(
        parent,
        "M386 298 Q444 289 479 302 Q501 311 513 339 Q536 369 575 382 Q557 404 539 422 Q495 446 463 "
        "422 Q442 410 443 377 Q390 359 386 298Z",
        "#697780",
        clear,
        0,
    )
    cv.path(
        parent,
        "M560 357 Q610 308 652 351 Q691 393 655 430 L611 465 L506 466 Q496 427 519 392Z",
        "#B9AA9D",
        clear,
        0,
        opacity=0.83,
    )
    cv.path(parent, "M560 357 Q574 343 585 341 L585 468 L506 467 Q496 424 519 391Z", "#AC9689", clear, 0, opacity=0.45)
    cv.line(parent, 335, 523, 716, 521, "#FFFFFF", 2, opacity=0.4)


@register("prop", "plant", summary="Potted plant with 18 formula-generated leaves")
def plant(cv: Canvas, parent, id="office-plant"):
    p = office_paints(cv)
    g = cv.group(parent, id)
    cv.path(g, "M29 1134 L31 936 Q80 922 134 945 L127 1139Z", "#DFE3DB", cv.ink, 3)
    cv.ellipse(g, 28, 923, 107, 31, "#575C47", cv.ink, 3)
    for x1, y1, x2, y2 in [(81, 1002, 97, 337), (74, 1005, 26, 411), (91, 1007, 194, 561), (63, 1010, 4, 654)]:
        cv.path(g, f"M{x1} {y1} Q{x1 - 5} {(y1 + y2) / 2} {x2} {y2}", stroke="#465336", sw=7)
    leaves = [
        (95, 365, 20, 269, 40),
        (99, 402, 197, 277, 42),
        (96, 480, 276, 372, 49),
        (83, 493, -27, 365, 48),
        (91, 557, 8, 477, 48),
        (108, 603, 291, 485, 51),
        (104, 655, 237, 630, 42),
        (82, 686, -44, 575, 51),
        (113, 720, 322, 649, 49),
        (113, 743, 112, 541, 51),
        (118, 799, 291, 774, 46),
        (75, 817, -71, 719, 45),
        (89, 878, 8, 876, 56),
        (119, 886, 215, 898, 42),
        (87, 926, 179, 836, 39),
        (44, 714, -42, 694, 37),
        (24, 588, -50, 500, 41),
        (151, 717, 215, 550, 40),
    ]
    for index, (bx, by, tx, ty, width) in enumerate(leaves):
        dx, dy = tx - bx, ty - by
        le = math.hypot(dx, dy)
        nx, ny = -dy / le * width, dx / le * width
        mx, my = (bx + tx) / 2, (by + ty) / 2
        d = f"M{bx} {by} Q{mx + nx:.2f} {my + ny:.2f} {tx} {ty} Q{mx - nx:.2f} {my - ny:.2f} {bx} {by}Z"
        cv.path(g, d, p["leaf"], "#33422C", 2.5, opacity=0.88 if index % 3 else 1)
        cv.line(g, bx, by, tx, ty, "#405236", 2)
        for f in [0.30, 0.48, 0.65, 0.8]:
            px, py = bx + dx * f, by + dy * f
            for side in [-1, 1]:
                cv.line(
                    g,
                    px,
                    py,
                    px + dx * 0.04 + nx * 0.28 * math.sin(math.pi * f) * side,
                    py + dy * 0.04 + ny * 0.28 * math.sin(math.pi * f) * side,
                    "#53673D",
                    1.2,
                    opacity=0.65,
                )
    return g


@register("prop", "chair", summary="Office chair: the manager's black one or the candidate's gray one")
def chair(cv: Canvas, parent, style="black"):
    p = office_paints(cv)
    ink = cv.ink
    if style == "black":
        cv.path(
            parent,
            "M354 1170 Q350 1020 387 839 L412 754 L691 745 Q743 907 815 1145 L802 1186Z",
            p["chair_black"],
            ink,
            5,
        )
        cv.path(
            parent,
            "M377 809 Q353 699 382 684 Q467 659 658 676 Q714 681 731 774 Q745 839 708 861 L391 870Z",
            p["chair_black"],
            ink,
            5,
        )
        cv.path(parent, "M390 704 Q386 800 399 842 L708 832", stroke="#555653", sw=4, opacity=0.5)
        cv.path(parent, "M361 1164 Q321 1149 306 1154 Q296 1163 317 1174 L351 1187Z", "#282B2B", ink, 4)
        cv.path(
            parent, "M798 1160 L915 1165 Q926 1151 886 1135 Q840 1112 815 1127 Q793 1138 798 1160Z", "#383A3B", ink, 4
        )
    else:
        cv.path(parent, "M42 1396 Q75 1252 192 1263 L216 1301 Q136 1284 119 1397Z", p["chair_gray"], ink, 4)
        cv.path(parent, "M875 1264 Q1009 1255 1045 1395 L984 1397 Q959 1298 883 1307Z", p["chair_gray"], ink, 4)
        cv.path(
            parent,
            "M197 1404 Q194 1155 225 780 Q228 704 286 692 Q538 665 791 695 Q846 699 854 781 Q883 1137 883 1405Z",
            p["chair_gray"],
            ink,
            5,
        )
        cv.path(
            parent,
            "M213 1159 Q235 1290 365 1313 L747 1316 Q845 1297 874 1202 L882 1403 L197 1403Z",
            "#676A66",
            cv.clear,
            0,
            opacity=0.2,
        )


@register("prop", "chair-back", summary="The executive chair seen from behind, the occupant's crown above the headrest")
def chair_back(cv: Canvas, parent, head: tuple[float, float, float] | None = (560, 724, 145)):
    """``head`` = (x, y, radius) of the occupant drawn behind the backrest, or None for an empty chair."""
    p = office_paints(cv)
    ink = cv.ink
    if head:
        x, y, r = head
        cv.ellipse(parent, x - r, y - r, 2 * r, 2 * r, cv.white, ink, 8)
        cv.path(
            parent,
            f"M{x - r * 0.55:g} {y - r * 0.78:g} Q{x - r * 0.05:g} {y - r * 1.12:g} {x + r * 0.5:g} {y - r * 0.8:g} "
            f"M{x - r * 0.3:g} {y - r * 0.9:g} Q{x + r * 0.2:g} {y - r * 1.05:g} {x + r * 0.62:g} {y - r * 0.62:g}",
            stroke=ink,
            sw=7,
        )
    cv.path(
        parent,
        "M370 1170 Q348 905 388 700 Q400 652 470 641 Q560 629 650 641 Q720 652 732 700 Q772 905 750 1170Z",
        p["chair_black"],
        ink,
        6,
    )
    cv.path(
        parent,
        "M412 1110 Q396 905 428 726 Q438 690 492 683 L628 683 Q682 690 692 726 Q724 905 708 1110",
        stroke="#4A4C4A",
        sw=4,
        opacity=0.6,
    )
    cv.path(parent, "M560 690 L560 1120", stroke="#4A4C4A", sw=3, opacity=0.45)
    cv.path(parent, "M330 1060 Q318 1000 350 985 L380 990 L384 1120 Q350 1125 330 1060Z", "#282B2B", ink, 4)
    cv.path(parent, "M790 1060 Q802 1000 770 985 L740 990 L736 1120 Q770 1125 790 1060Z", "#282B2B", ink, 4)


@register("prop", "laptop", summary="Open laptop on the interviewer's right")
def laptop(cv: Canvas, parent):
    ink = cv.ink
    cv.ellipse(parent, 820, 1263, 310, 50, "#9E8A70", opacity=0.20)
    cv.path(parent, "M831 1221 L1045 1201 L1140 1261 L1000 1315 L830 1240Z", "#A8ABAC", ink, 3)
    cv.path(parent, "M866 1228 L1008 1218 L1090 1258 L995 1288Z", "#6C7275", ink, 2)
    for i in range(6):
        cv.line(parent, 889 + i * 15, 1230, 949 + i * 15, 1263, "#42494B", 2)
    cv.path(
        parent, "M1000 1307 L1056 985 Q1058 971 1076 969 L1166 975 L1119 1300 Q1116 1313 1101 1317Z", "#838B8F", ink, 4
    )
    cv.path(parent, "M1011 1299 L1065 990", stroke="#B5BEC1", sw=2)


@register("prop", "water-glass", summary="Glass of water at the edge of the reverse-angle desk")
def water_glass(cv: Canvas, parent):
    ink = cv.ink
    cv.path(parent, "M1062 1380 Q1093 1369 1125 1380 L1115 1565 Q1089 1581 1071 1564Z", "#E3E8E1", ink, 3)
    cv.path(
        parent,
        "M1067 1431 Q1090 1444 1121 1430 L1114 1560 Q1090 1573 1073 1560Z",
        "#9FC0CA",
        "#557480",
        1.5,
        opacity=0.75,
    )
    cv.ellipse(parent, 1061, 1369, 65, 20, "#E4E9E4", ink, 2)


@register("prop", "candidate-back", summary="The candidate seen from behind in the foreground of the wide shot")
def candidate_back(cv: Canvas, parent):
    p = office_paints(cv)
    ink, white = cv.ink, cv.white
    cv.path(
        parent, "M33 1591 L33 1512 Q36 1438 102 1420 Q235 1387 357 1424 Q430 1443 435 1515 L435 1581Z", white, ink, 9
    )
    cv.ellipse(parent, -9, 923, 489, 490, white, ink, 10)
    cv.path(parent, "M90 965 Q179 880 308 928 M151 953 Q247 911 354 962", stroke=ink, sw=8)
    cv.path(parent, "M-50 1581 L441 1582 Q585 1581 607 1711 L625 1950 L-50 1950Z", p["chair_gray"], ink, 9)
    cv.path(parent, "M-3 1623 Q235 1610 513 1643", stroke="#A9ADAD", sw=14, opacity=0.55)


@register("prop", "silent-phone", summary="A phone face up on the desk with a muted work notification")
def silent_phone(cv: Canvas, parent, x=85, y=1640, rotation=-8, label="WORK\nSILENCED", id="silent-work-phone"):
    ink, clear = cv.ink, cv.clear
    g = cv.group(parent, id, x=x, y=y, rotation=rotation)
    cv.rect(g, 4, 10, 280, 160, "#8C765C", radius=22, opacity=0.20)
    cv.rect(g, 0, 0, 280, 160, "#22292D", ink, 4, radius=22)
    cv.rect(g, 12, 11, 255, 135, "#344448", radius=15)
    cv.line(g, 113, 5, 168, 5, "#768185", 3)
    cv.path(g, "M36 83 L45 68 L45 52 Q46 33 62 33 Q79 33 79 52 L79 68 L87 82Z", fill="#CCDCDA", stroke=clear, sw=0)
    cv.path(g, "M55 88 Q62 99 69 88", stroke="#CCDCDA", sw=4)
    cv.line(g, 35, 31, 91, 92, "#E7C380", 6)
    cv.ellipse(g, 239, 23, 9, 9, "#A6C9A1")
    cv.assets.add_text(
        id="phone-label",
        text=label,
        width=157,
        height=90,
        size="23",
        fontAsset=cv.font_asset,
        color="#E4ECE9",
        lineHeight="1.5",
        verticalAlign="middle",
    )
    g.add_layer(id="phone-label-layer", asset="phone-label", x=101, y=28)
    return g


# ---------------------------------------------------------------- café and park


def cafe_paints(cv: Canvas) -> dict[str, str]:
    return {
        "cream": cv.grad("cream", [(0, "#F5E8CE"), (1, "#DBC49F")], (0, 0, 0.4, 1)),
        "wood": cv.grad("wood", [(0, "#CE9D69"), (0.5, "#BD8653"), (1, "#A96C42")], (0, 0, 0.8, 1)),
        "sky": cv.grad("sky", [(0, "#B9D9E0"), (1, "#E9E9CD")], (0, 0, 0, 1)),
        "metal": cv.grad("metal", [(0, "#DCE6DF"), (0.35, "#9CADAB"), (0.65, "#CBD9D2"), (1, "#718888")], (0, 0, 1, 0)),
        "grass": cv.grad("grass", [(0, "#A8BD84"), (1, "#769965")], (0, 0, 0, 1)),
    }


@register(
    "prop",
    "coffee-cup",
    summary="Takeaway cup with lid and a foam heart",
    examples=('from srstudio import get\ncup = get("prop", "coffee-cup")(ep.cv, ep.comp, 540, 960)',),
)
def coffee_cup(cv: Canvas, parent, x, y, scale=1, rotation=0, *, shadow: bool = True):
    """``shadow`` is its contact shadow on what it stands on: off for a cup held in the air."""
    ink, clear, white = cv.ink, cv.clear, cv.white
    g = cv.group(parent, cv.uid("coffee-cup"), x=x, y=y, scaleX=scale, scaleY=scale, rotation=rotation)
    if shadow:
        cv.ellipse(g, -29, 56, 64, 10, "#5C4D3E", opacity=0.16)
    cv.path(g, "M-28 -18 L28 -18 L22 57 Q0 66 -22 57Z", white, ink, 3)
    cv.path(g, "M-26 11 L26 11 L24 37 L-24 37Z", "#B27F51", clear, 0)
    cv.ellipse(g, -32, -25, 64, 15, "#3E4947", ink, 3)
    cv.rect(g, -31, -19, 62, 10, "#4B5550", ink, 2, radius=3)
    cv.ellipse(g, -5, 17, 12, 13, "#F3DDAD")
    cv.path(g, "M-1 20 Q7 26 0 29", stroke="#94683E", sw=1.2)
    return g


@register("prop", "menu-board", summary="Chalkboard menu with the Free Wi-Fi line")
def menu_board(
    cv: Canvas,
    parent,
    items=(
        ("menu-title", "CAFÉ", 343, 90, 67, "#F3DCA4"),
        ("menu-coffee", "COFFEE   $5", 458, 67, 34, "#F5EBD5"),
        ("menu-pastry", "PASTRY   $3", 534, 67, 34, "#F5EBD5"),
        ("menu-wifi", "FREE WI-FI", 634, 61, 31, "#A9CBB8"),
    ),
):
    cv.rect(parent, 70, 305, 405, 440, "#2E4F4C", cv.ink, 7, radius=18)
    cv.rect(parent, 85, 320, 375, 410, cv.clear, "#C49B68", 3, radius=9)
    for name, value, y, h, size, color in items:
        cv.text(parent, name, value, 110, y, 320, h, size, color)


@register("prop", "cafe-window", summary="Window onto the street, the view clipped by a rect mask")
def cafe_window(cv: Canvas, parent):
    p = cafe_paints(cv)
    cv.rect(parent, 620, 232, 365, 430, "#638789", cv.ink, 6, radius=8)
    window = parent.add_group(id="cafe-window-view", width=1080, height=1920, isolate=True)
    window.add_mask(type="rect", x=637, y=249, width=331, height=396)
    cv.rect(window, 637, 249, 331, 396, p["sky"], radius=3)
    for xx, yy, rr in [(650, 475, 110), (890, 450, 125), (760, 530, 90)]:
        cv.ellipse(window, xx, yy, rr, rr, "#9CB98D", opacity=0.7)
    cv.line(parent, 803, 245, 803, 650, "#5B7776", 7)
    cv.line(parent, 638, 455, 969, 455, "#5B7776", 6)
    cv.rect(parent, 606, 652, 395, 21, "#98704E", cv.ink, 3)
    return window


@register("prop", "pendant-light", summary="Hanging pendant lamp")
def pendant_light(cv: Canvas, parent, x):
    cv.line(parent, x, -200, x, 174, "#3C4C49", 5)
    cv.path(parent, f"M{x - 74} 218 Q{x - 60} 154 {x} 153 Q{x + 60} 154 {x + 74} 218Z", "#8E5141", cv.ink, 5)
    cv.ellipse(parent, x - 76, 207, 152, 24, "#F2CF91", cv.ink, 4)


@register("prop", "bean-jar", summary="Jar of coffee beans on the shelf")
def bean_jar(cv: Canvas, parent, x):
    cv.rect(parent, x, 915, 67, 97, "#C2B595", cv.ink, 3, radius=8)
    cv.rect(parent, x - 3, 908, 73, 17, "#70513C", cv.ink, 3, radius=4)
    for k in range(8):
        cv.ellipse(parent, x + 9 + (k % 3) * 18, 948 + (k // 3) * 17, 12, 7, "#684E3A", rotation=30)


@register("prop", "espresso-machine", summary="Espresso machine with steam that breathes by expression")
def espresso_machine(cv: Canvas, parent):
    p = cafe_paints(cv)
    ink = cv.ink
    cv.rect(parent, 885, 1035, 300, 218, p["metal"], ink, 5, radius=16)
    cv.rect(parent, 907, 1060, 245, 54, "#3D5554", ink, 3, radius=7)
    for xx in [938, 996, 1054]:
        cv.ellipse(parent, xx, 1075, 20, 20, "#B7D1BF", ink, 2)
    cv.path(parent, "M934 1140 L1085 1140 L1085 1207 L934 1207Z", "#657E7C", ink, 3)
    cv.line(parent, 950, 1140, 950, 1171, ink, 8)
    cv.line(parent, 1022, 1140, 1022, 1171, ink, 8)
    cv.rect(parent, 905, 1230, 250, 15, "#435A59", ink, 3, radius=4)
    for i in range(3):
        steam = cv.path(
            parent,
            f"M{930 + i * 34} 1010 Q{910 + i * 34} 985 {935 + i * 34} 957 Q{948 + i * 34} 937 {933 + i * 34} 918",
            stroke="#F7F4DF",
            sw=5,
            opacity=0.6,
        )
        cv.expression(steam, "opacity", f".35+.18*Math.sin(time*2.4+{i})")
        cv.expression(steam, "y", f"-5*Math.sin(time*1.8+{i})")


@register("prop", "pastry-stand", summary="Plate of croissants on the counter")
def pastry_stand(cv: Canvas, parent):
    cv.ellipse(parent, 470, 1190, 250, 36, "#ECE6D2", cv.ink, 3)
    for i in range(3):
        xx = 501 + i * 65
        cv.path(
            parent,
            f"M{xx - 24} 1203 Q{xx - 20} 1154 {xx + 6} 1160 Q{xx + 24} 1165 {xx + 26} 1202Z",
            "#DCA35F",
            "#8D603A",
            3,
        )
        cv.path(
            parent,
            f"M{xx - 10} 1199 Q{xx - 15} 1177 {xx - 2} 1168 M{xx + 8} 1199 Q{xx + 4} 1180 {xx + 13} 1171",
            stroke="#A46D3C",
            sw=2,
        )


@register("prop", "building", summary="Background apartment block with lit windows")
def building(cv: Canvas, parent, x, y, w, h):
    cv.rect(parent, x, y, w, h, "#A9BCAD")
    for wx in range(int(x + 20), min(1060, int(x + w - 10)), 38):
        for wy in range(int(y + 30), 690, 55):
            cv.rect(parent, wx, wy, 16, 23, "#D9E1CD", radius=2)


@register("prop", "tree", summary="Park tree whose canopy sways by expression")
def tree(cv: Canvas, parent):
    cv.path(
        parent, "M49 1440 L91 670 L42 385 L88 373 L128 640 L161 450 L193 467 L154 751 L139 1440Z", "#8A7052", cv.ink, 4
    )
    canopy = cv.group(parent, "park-tree-canopy")
    cv.expression(canopy, "rotation", ".25*Math.sin(time*.9)")
    for xx, yy, ww, hh, col in [
        (-125, 185, 340, 330, "#6B956C"),
        (52, 80, 330, 310, "#85AA79"),
        (238, 140, 300, 260, "#91B37E"),
        (-110, 390, 365, 290, "#7BA475"),
        (112, 330, 365, 300, "#8BAF7D"),
    ]:
        cv.ellipse(canopy, xx, yy, ww, hh, col, cv.ink, 3)
    for xx, yy in [(40, 350), (155, 250), (290, 300), (100, 505), (280, 472)]:
        cv.path(canopy, f"M{xx} {yy} q25 -30 49 -10", stroke="#B8CC95", sw=8, opacity=0.5)
    return canopy


@register("prop", "shrub", summary="Small planted shrub along the path")
def shrub(cv: Canvas, parent, x):
    cv.path(parent, f"M{x} 1410 q-30 -60 -45 -40 q32 0 45 40 q16 -79 38 -68 q-10 45 -38 68Z", "#6F9563", cv.ink, 2)


@register("prop", "park-sign", summary="PUBLIC PARK sign on a post")
def park_sign(cv: Canvas, parent, text: str | None = "PUBLIC\nPARK"):
    """The post and the board; ``text=None`` leaves the lettering out (:func:`srstudio.locations.park`)."""
    cv.line(parent, 916, 520, 916, 1040, "#637969", 8)
    cv.rect(parent, 785, 526, 260, 112, "#486C58", cv.ink, 4, radius=13)
    if text is not None:
        cv.text(parent, "park-sign", text, 804, 538, 222, 88, 32, "#F0E7CF")


@register("prop", "bench", summary="Slatted wooden park bench")
def bench(cv: Canvas, parent):
    p = cafe_paints(cv)
    for yy in [1030, 1100, 1170]:
        cv.rect(parent, 210, yy, 635, 48, p["wood"], cv.ink, 4, radius=7)
    for xx in [240, 779]:
        cv.path(parent, f"M{xx} 1045 L{xx - 18} 1555 L{xx + 13} 1555 L{xx + 38} 1045Z", "#4A5C54", cv.ink, 3)
    cv.rect(parent, 187, 1268, 681, 48, p["wood"], cv.ink, 4, radius=8)
    cv.rect(parent, 187, 1317, 681, 22, "#8B5F3D", cv.ink, 3, radius=5)


CRUMB_FALL = 0.32  # seconds from the hand to the ground


@register("prop", "crumbs", summary="A tossed handful of pastry crumbs that fall from the hand and stay on the ground")
def crumbs(cv: Canvas, parent, x, y, ground, *, toss: float, count: int = 7, seed: int = 0, id="crumbs"):
    """``count`` crumbs leave ``(x, y)`` at ``toss`` and land scattered on ``ground``; nothing shows before."""
    if count < 1:
        raise PropError(f"crumbs needs at least one crumb, got {count}")
    if toss < 0:
        raise PropError(f"crumbs toss {toss} is before the start")
    if ground <= y:
        raise PropError(f"crumbs fall down: ground {ground} must be below the hand at {y}")
    rng = random.Random(seed)
    g = cv.group(parent, id, x=x, y=y)
    cv.keys(g, "opacity", sorted({0.0: 0, float(toss): 1}.items()))  # shown from the toss on
    for i in range(count):
        dx, size = rng.uniform(-70, 70), rng.uniform(9, 15)
        land = toss + CRUMB_FALL * rng.uniform(0.8, 1.1)
        bit = cv.group(g, f"{id}-bit-{i}")
        cv.keys(bit, "x", [(toss, 0), (land, dx)], hold=False)
        cv.keys(bit, "y", [(toss, 0), (land, ground - y)], hold=False)
        cv.ellipse(bit, -size / 2, -size / 2, size, size * 0.8, "#D9A657", cv.ink, 2)
    return g


# ---------------------------------------------------------------- polished office rooms (ADR 0011)

GLOW = "#FFF3D6"  # the warm light every glaze in the polished rooms shares


def glow(cv: Canvas, parent, x, y, r, rings=4, color=GLOW, peak=0.2):
    """A soft halo: ``rings`` translucent discs around ``x, y``, faintest at radius ``r``."""
    for k in range(rings):
        rr = r * (k + 1) / rings
        cv.ellipse(parent, x - rr, y - rr, 2 * rr, 2 * rr, color, opacity=round(peak / (k + 1.5), 3))


@register(
    "prop",
    "whiteboard",
    summary="A framed whiteboard with a marker chart, three sticky notes, a gloss and a marker tray",
)
def whiteboard(cv: Canvas, parent, x, y, w, h, rising=True, id="whiteboard"):
    """``rising`` draws the chart's trend line going up (blue) or down (red)."""
    if w < 160 or h < 160:
        raise PropError(f"a whiteboard needs at least 160×160 units for its chart and notes, got {w}×{h}")
    ink = cv.ink
    g = cv.group(parent, id)
    frame = cv.grad("aluminium", [(0, "#EEF2F1"), (0.5, "#AEB8BA"), (1, "#DCE2E1")], (0, 0, 1, 1))
    board = cv.grad("board", [(0, "#FFFFFF"), (1, "#E9EEED")], (0, 0, 0.3, 1))
    cv.rect(g, x + 9, y + 14, w, h, "#33403F", radius=8, opacity=0.18)
    cv.rect(g, x, y, w, h, frame, ink, 4, radius=8)
    bx, by, bw, bh = x + 14, y + 14, w - 28, h - 28
    cv.rect(g, bx, by, bw, bh, board, "#8F9A9B", 2, radius=3)
    marker = "#3E4A52"
    cv.path(g, f"M{bx + 26} {by + 40} q30 -14 60 0 t60 0 t50 -4", stroke=marker, sw=5)
    cv.path(g, f"M{bx + 26} {by + 70} q24 -10 48 0 t44 0", stroke=marker, sw=4, opacity=0.7)
    cw, ch = bw * 0.62, bh * 0.52  # the chart's axes
    ox, oy = bx + 34, by + 100 + ch
    cv.path(g, f"M{ox} {oy - ch} L{ox} {oy} L{ox + cw} {oy}", stroke=marker, sw=4)
    for k, frac in enumerate((0.35, 0.55, 0.45, 0.8)):
        bh_k = ch * frac * (1 if rising else 1 - 0.18 * k)
        cv.rect(g, ox + 18 + k * cw / 4.4, oy - bh_k, cw / 7, bh_k, "#A7D3A1", "#5E8F5A", 2.5, opacity=0.85)
    trend = "#2F7FC1" if rising else "#D2553F"
    y0, y1 = (oy - ch * 0.25, oy - ch * 0.95) if rising else (oy - ch * 0.9, oy - ch * 0.2)
    xs = [ox + cw * f for f in (0.05, 0.3, 0.55, 0.8, 0.98)]
    ys = [y0 + (y1 - y0) * f for f in (0, 0.35, 0.25, 0.7, 1)]
    cv.path(g, "M" + " L".join(f"{a:.1f} {b:.1f}" for a, b in zip(xs, ys, strict=True)), stroke=trend, sw=6)
    sgn = -1 if rising else 1
    tx, ty = xs[-1], ys[-1]
    cv.path(g, f"M{tx - 22:.1f} {ty + 4:.1f} L{tx:.1f} {ty:.1f} L{tx - 8:.1f} {ty - sgn * 20:.1f}", stroke=trend, sw=6)
    nx = bx + bw * 0.74
    for k, (col, rot) in enumerate((("#FFE27A", -6), ("#FFB3C1", 5), ("#A9D8F2", -3))):
        note = cv.group(g, cv.uid("sticky"), x=nx, y=by + 34 + k * bh * 0.27, rotation=rot)
        side = min(bw * 0.2, 70)
        cv.rect(note, 4, 6, side, side, "#4A4030", opacity=0.16)
        cv.path(note, f"M0 0 L{side} 0 L{side} {side * 0.8} L{side * 0.8} {side} L0 {side}Z", col, ink, 2.5)
        cv.path(note, f"M{side} {side * 0.8} L{side * 0.82} {side * 0.82} L{side * 0.8} {side}Z", "#FFFFFF", ink, 2)
        for j in (1, 2):
            cv.line(note, side * 0.16, side * 0.26 * j, side * (0.82 - 0.2 * j), side * 0.26 * j, marker, 2.5)
    cv.path(
        g,
        f"M{bx + bw * 0.52:.1f} {by} L{bx + bw * 0.64:.1f} {by} L{bx + bw * 0.42:.1f} {by + bh} "
        f"L{bx + bw * 0.3:.1f} {by + bh}Z",
        "#FFFFFF",
        cv.clear,
        0,
        opacity=0.38,
    )  # the gloss of the laminate
    tray_x, tray_w = x + w * 0.15, w * 0.7
    cv.rect(g, tray_x, y + h - 2, tray_w, 16, frame, ink, 3, radius=4)
    for k, col in enumerate(("#D2553F", "#2F7FC1", "#2A2F33")):
        cv.rect(g, tray_x + 24 + k * 64, y + h - 12, 52, 12, col, ink, 2, radius=5)
    return g


@register(
    "prop",
    "blinds-window",
    summary="A tall window with a sky, a city skyline and venetian blinds lowered two thirds, with a sill",
)
def blinds_window(cv: Canvas, parent, x, y, w, h, id="blinds-window"):
    ink = cv.ink
    g = cv.group(parent, id)
    sky = cv.grad("window-sky", [(0, "#8FC0DB"), (0.7, "#D4E6EA"), (1, "#EDEFE2")], (0, 0, 0, 1))
    slat = cv.grad("blind-slat", [(0, "#FDFCF8"), (0.55, "#E8E4DA"), (1, "#C9C2B4")], (0, 0, 0, 1))
    cv.rect(g, x - 6, y - 6, w + 12, h + 12, "#F5F3EE", ink, 4, radius=4)
    gx, gy, gw, gh = x + 16, y + 16, w - 32, h - 32
    cv.rect(g, gx, gy, gw, gh, sky, ink, 3)
    for k, (fx, fh) in enumerate(((0.0, 0.3), (0.16, 0.42), (0.38, 0.24), (0.56, 0.5), (0.8, 0.34))):
        bw = gw * 0.2
        cv.rect(g, gx + gw * fx, gy + gh * (1 - fh), bw, gh * fh, "#A9C3CC" if k % 2 else "#B9D0D6", opacity=0.9)
        for wy in range(int(gy + gh * (1 - fh) + 18), int(gy + gh) - 10, 34):
            cv.line(g, gx + gw * fx + 10, wy, gx + gw * fx + bw - 10, wy, "#E9F1F2", 3, opacity=0.6)
    cv.line(g, gx + gw / 2, gy, gx + gw / 2, gy + gh, "#F5F3EE", 10)
    cv.line(g, gx + gw / 2, gy, gx + gw / 2, gy + gh, ink, 2.5, opacity=0.5)
    lowered = gy + gh * 0.62
    yy = gy
    while yy < lowered:
        cv.rect(g, gx - 4, yy, gw + 8, 24, slat, "#8E877A", 1.5, radius=4)
        yy += 32
    cv.rect(g, gx - 8, yy, gw + 16, 18, "#E2DDD2", ink, 3, radius=5)  # the bottom rail
    cv.line(g, gx + gw - 30, gy, gx + gw - 30, yy + 120, "#9C9585", 2.5)
    cv.ellipse(g, gx + gw - 38, yy + 116, 16, 22, "#E2DDD2", ink, 2)
    cv.rect(g, x - 22, y + h, w + 44, 26, "#F8F6F1", ink, 4, radius=4)
    cv.rect(g, x - 14, y + h + 26, w + 28, 14, "#7A8285", opacity=0.18)
    return g


@register("prop", "speakerphone", summary="A three-lobed conference speakerphone with a live green ring")
def speakerphone(cv: Canvas, parent, x, y, id="speakerphone", talk: Sequence[tuple[float, float]] = ()):
    """``talk``: (start, end) spans, in order and apart, in which the far end speaks and the ring lights up."""
    last = 0.0
    for start, end in talk:
        if not (last <= start < end):
            raise PropError(f"speakerphone talk spans are (start, end) in order from 0, apart; got {list(talk)}")
        last = end
    ink = cv.ink
    g = cv.group(parent, id, x=x, y=y)
    body = cv.grad("speaker-body", [(0, "#4B5257"), (0.5, "#2E3336"), (1, "#1E2224")], (0, 0, 0, 1))
    cv.ellipse(g, -150, 18, 300, 46, "#1E1A16", opacity=0.22)
    cv.path(g, "M-140 22 Q-150 -4 -98 -22 Q0 -54 98 -22 Q150 -4 140 22 Q0 52 -140 22Z", body, ink, 4)
    cv.path(g, "M-128 10 Q0 34 128 10 L140 22 Q0 52 -140 22Z", "#16191B", ink, 2.5)
    for k in range(-5, 6):
        for j in (-1, 0, 1):
            cv.ellipse(g, k * 18 - 2.5, j * 9 - 6, 5, 4, "#6E777C")
    cv.ellipse(g, -26, -16, 52, 18, "#1B1F21", ink, 2.5)
    cv.ellipse(g, -22, -14, 44, 14, cv.clear, "#5FD1A0", 3.5)
    cv.ellipse(g, -38, -24, 76, 34, "#5FD1A0", opacity=0.16)
    cv.path(g, "M-96 -16 Q-40 -38 30 -34", stroke="#FFFFFF", sw=3, opacity=0.35)
    if talk:
        ring = cv.group(g, f"{id}-talk", opacity=0)
        cv.ellipse(ring, -60, -34, 120, 54, "#5FD1A0", opacity=0.35)
        cv.ellipse(ring, -26, -16, 52, 18, cv.clear, "#B9FFE0", 5)
        cv.keys(ring, "opacity", [(0, 0)] + [k for start, end in talk for k in ((start, 1), (end, 0))])
    return g


@register("prop", "globe-pendant", summary="An opal globe pendant on a cord, with a brass cap")
def globe_pendant(cv: Canvas, parent, x, y, r=46, light=None, id=None):
    """``light``: a group that receives the globe's halo (a location's glaze group)."""
    ink = cv.ink
    g = cv.group(parent, id or cv.uid("globe-pendant"))
    opal = cv.grad("opal", [(0, "#FFFDF5"), (0.6, "#FCEBC2"), (1, "#EFC77F")], (0.2, 0.1, 0.8, 1))
    brass = cv.grad("brass", [(0, "#F0D18E"), (0.5, "#B98A3F"), (1, "#E2BD75")], (0, 0, 1, 0))
    cv.line(g, x, -10, x, y - r - 14, "#2C2A27", 3)
    cv.path(
        g, f"M{x - 16} {y - r + 4} L{x - 12} {y - r - 18} L{x + 12} {y - r - 18} L{x + 16} {y - r + 4}Z", brass, ink, 3
    )
    if light is not None:
        glow(cv, light, x, y, r * 3.4)
    cv.ellipse(g, x - r, y - r, 2 * r, 2 * r, opal, ink, 3.5)
    cv.path(
        g,
        f"M{x - r * 0.62:.1f} {y - r * 0.2:.1f} Q{x - r * 0.55:.1f} {y - r * 0.66:.1f} {x - r * 0.12:.1f} "
        f"{y - r * 0.72:.1f}",
        stroke="#FFFFFF",
        sw=5,
        opacity=0.85,
    )
    return g


@register("prop", "slat-wall", summary="A walnut slat feature wall with a warm LED strip along its top")
def slat_wall(cv: Canvas, parent, x, y, w, h, light=None, id="slat-wall"):
    """``light``: a group that receives the LED's wash down the slats."""
    ink = cv.ink
    g = cv.group(parent, id)
    slat = cv.grad("walnut-slat", [(0, "#8A5D3D"), (0.45, "#B7845B"), (1, "#7E5436")], (0, 0, 1, 0))
    cv.rect(g, x, y, w, h, "#3B2A20", ink, 4)
    n = int(w // 36)
    pitch = w / n
    for k in range(n):
        cv.rect(g, x + k * pitch + 6, y + 4, pitch - 12, h - 8, slat)
        cv.line(g, x + k * pitch + 8, y + 10, x + k * pitch + 8, y + h - 10, "#D9A877", 2, opacity=0.5)
    cv.rect(g, x - 10, y - 18, w + 20, 18, "#EDE7DC", ink, 3)  # the soffit hiding the LED
    cv.rect(g, x, y, w, 6, "#FFE9B8")
    if light is not None:
        wash = cv.grad("led-wash", [(0, GLOW + "FF"), (1, GLOW + "00")], (0, 0, 0, 1))
        cv.rect(light, x, y, w, h * 0.45, wash, opacity=0.42)
    return g


@register(
    "prop",
    "reception-counter",
    summary="A reception counter: a veined stone top over a fluted lacquer front, lit along its kick",
)
def reception_counter(cv: Canvas, parent, x0, x1, top, bottom, id="reception-counter"):
    ink = cv.ink
    g = cv.group(parent, id)
    stone = cv.grad("stone-top", [(0, "#F6F3EC"), (0.5, "#E1DBCF"), (1, "#F2EEE6")], (0, 0, 1, 0))
    front = cv.grad("fluted-front", [(0, "#EDE8DE"), (1, "#CFC7B8")], (0, 0, 0, 1))
    cv.rect(g, x0 + 14, top + 14, x1 - x0, bottom - top, "#2E2620", opacity=0.16)
    cv.rect(g, x0, top + 34, x1 - x0, bottom - top - 64, front, ink, 4)
    for xx in range(int(x0) + 30, int(x1) - 10, 38):
        cv.line(g, xx, top + 48, xx, bottom - 44, "#B4AB9B", 3)
        cv.line(g, xx + 6, top + 48, xx + 6, bottom - 44, "#FBF8F2", 3, opacity=0.8)
    cv.rect(g, x0 + 16, bottom - 30, x1 - x0 - 32, 30, "#2D2925", ink, 3)  # the recessed kick
    cv.rect(g, x0 + 16, bottom - 30, x1 - x0 - 32, 5, "#FFE2A8")
    cv.rect(g, x0 - 24, top, x1 - x0 + 48, 36, stone, ink, 4, radius=6)
    for vx, vy, vw in ((x0 + 60, top + 12, 140), (x0 + (x1 - x0) * 0.55, top + 20, 180), (x1 - 160, top + 9, 90)):
        cv.path(g, f"M{vx:.0f} {vy:.0f} q{vw / 3:.0f} -6 {vw / 2:.0f} 2 t{vw / 2:.0f} 0", stroke="#B9B1A3", sw=2)
    cv.line(g, x0 - 18, top + 6, x1 + 18, top + 6, "#FFFFFF", 3, opacity=0.8)
    return g


TIP_SCREEN = (300, 220)  # the tablet's screen, at scale 1
TIP_PICKED, TIP_BUTTON = "#2E7D5B", "#EAF2EE"


@register(
    "prop",
    "tip-tablet",
    summary="A counter-top payment tablet asking for a tip: big percentage buttons, a tiny no tip, taps that light",
)
def tip_tablet(
    cv: Canvas,
    parent,
    x,
    y,
    *,
    heading: str = "Add a tip",
    options: tuple[str, ...] = ("20%", "25%", "30%"),
    picks: tuple[tuple[float, int], ...] = (),
    scale: float = 1.0,
):
    """A tablet on a swivel stand whose foot stands on (``x``, ``y``), its screen toward the viewer: ``heading``,
    one big button per option (1 to 4), and under them the smallest thing on the screen, ``no tip``. Each pick
    ``(time, index)`` lights that button from its time until the next pick."""
    cv.require_font("the tip tablet's screen is set in it")
    if not heading.strip():
        raise PropError("a tip tablet needs a heading")
    if not 1 <= len(options) <= 4 or any(not o.strip() for o in options):
        raise PropError(f"a tip tablet shows 1 to 4 non-empty options, got {options!r}")
    times = [t for t, _ in picks]
    if any(not (0 <= t) for t in times) or times != sorted(times) or any(not 0 <= i < len(options) for _, i in picks):
        raise PropError(f"each pick is (time >= 0, option index), in time order, got {picks!r}")
    if not (checks.number(scale) and scale > 0):
        raise PropError(f"scale must be a positive number, got {scale!r}")
    ink = cv.ink
    w, h = TIP_SCREEN
    g = cv.group(parent, cv.uid("tip-tablet"), x=x, y=y, scaleX=scale, scaleY=scale)
    cv.ellipse(g, -70, -12, 140, 22, "#5C4D3E", opacity=0.18)
    cv.rect(g, -56, -16, 112, 16, "#6B7178", ink, 3, radius=6)  # the foot and the swivel post
    cv.rect(g, -10, -70, 20, 56, "#8A9097", ink, 3)
    top = -70 - h - 24
    cv.rect(g, -w / 2 - 12, top - 12, w + 24, h + 24, "#2B2F36", ink, 4, radius=18)
    cv.rect(g, -w / 2, top, w, h, "#FFFFFF", radius=8)
    cv.text(g, cv.uid("tip-heading"), heading, -w / 2, top + 6, w, 44, 28, ink, weight="700")
    n = len(options)
    gap, bh = 10, 92
    bw = (w - 24 - (n - 1) * gap) // n
    bx0, by = -w / 2 + 12, top + 60
    for i, option in enumerate(options):
        bx = bx0 + i * (bw + gap)
        cv.rect(g, bx, by, bw, bh, TIP_BUTTON, "#2E7D5B", 3, radius=12)
        cv.text(g, cv.uid("tip-option"), option, bx, by, bw, bh, 34, "#1D4D38", weight="700")
    for k, (t, i) in enumerate(picks):
        bx = bx0 + i * (bw + gap)
        lit = cv.group(g, cv.uid("tip-pick"))
        if k + 1 < len(picks):
            cv.gate(lit, [(t, picks[k + 1][0])])
        else:
            cv.keys(lit, "opacity", [(0.0, 0), (t, 1)])
        cv.rect(lit, bx, by, bw, bh, TIP_PICKED, ink, 3, radius=12)
        cv.text(lit, cv.uid("tip-picked"), options[i], bx, by, bw, bh, 34, "#FFFFFF", weight="700")
    cv.text(g, cv.uid("tip-none"), "no tip", -w / 2, top + h - 40, w, 30, 13, ink)
    return g


READER_SCREEN = (230, 150)  # the card reader's screen, at scale 1
READER_AMOUNT = 8  # the most characters an amount holds ("$1000.00")
READER_LABEL = 16  # the most characters the line under it holds


@register(
    "prop",
    "card-reader",
    summary="A counter-top card reader whose screen shows a running total and the line it was added for",
)
def card_reader(cv: Canvas, parent, x, y, *, readings: tuple[tuple[float, str, str], ...], scale: float = 1.0):
    """A card terminal whose foot stands on (``x``, ``y``), its screen toward the viewer. Each reading ``(time,
    amount, label)`` shows a big ``amount`` (1 to :data:`READER_AMOUNT` characters) over a small ``label`` (at
    most :data:`READER_LABEL`) from its time until the next. The first reading is at 0 and is still; each later one
    pops in, so the total visibly climbs."""
    cv.require_font("the card reader's screen is set in it")
    times = [t for t, _, _ in readings]
    if (
        not readings
        or not all(checks.number(t) for t in times)
        or times[0] != 0
        or any(b <= a for a, b in zip(times, times[1:], strict=False))
    ):
        raise PropError(f"readings start at 0 and rise strictly, got {times!r}")
    for _, amount, label in readings:
        if not amount.strip() or len(amount) > READER_AMOUNT:
            raise PropError(f"an amount has 1 to {READER_AMOUNT} characters, got {amount!r}")
        if len(label) > READER_LABEL:
            raise PropError(f"a label has at most {READER_LABEL} characters, got {label!r}")
    if not (checks.number(scale) and scale > 0):
        raise PropError(f"scale must be a positive number, got {scale!r}")
    ink = cv.ink
    w, h = READER_SCREEN
    g = cv.group(parent, cv.uid("card-reader"), x=x, y=y, scaleX=scale, scaleY=scale)
    cv.ellipse(g, -w / 2 - 10, -14, w + 20, 24, "#5C4D3E", opacity=0.2)  # the contact shadow on the counter
    body_h = h + 150
    cv.rect(g, -w / 2 - 18, -body_h, w + 36, body_h, "#30353D", ink, 4, radius=22)
    cv.rect(g, -w / 2 - 8, -body_h + 8, 10, body_h - 30, "#4A515B", radius=5)  # the lit edge, from the café's left
    top = -body_h + 18
    cv.rect(g, -w / 2, top, w, h, "#E9F3EC", ink, 3, radius=10)
    for row in range(2):  # the keypad
        for col in range(3):
            cv.rect(g, -w / 2 + 22 + col * 68, top + h + 22 + row * 52, 50, 36, "#5B636E", ink, 2, radius=8)
    for k, (t, amount, label) in enumerate(readings):
        shown = cv.group(g, cv.uid("reader-reading"))
        if k + 1 < len(readings):
            cv.gate(shown, [(t, readings[k + 1][0])])
        elif k:
            cv.keys(shown, "opacity", [(0.0, 0), (t, 1)])
        if k:  # a later reading pops in about the screen's middle
            shown = cv.group(shown, cv.uid("reader-pop"), anchorX=0, anchorY=top + h / 2, x=0, y=top + h / 2)
            cv.pop_in(shown, t, from_=0.9, over=1.06)
        cv.text(shown, cv.uid("reader-amount"), amount, -w / 2, top + 14, w, 80, 62, "#1D4D38", weight="700")
        if label:
            cv.text(shown, cv.uid("reader-label"), label, -w / 2, top + 96, w, 40, 26, ink)
    return g


SLIP_CHARS = 10  # the most letters the envelope's name line holds
SLIP_FALL = 0.28  # seconds from the drop to the floor
SLIP_SIZE = (150, 96)  # the envelope's width and height


@register(
    "prop",
    "pink-slip",
    summary="A pink-slip envelope lettered with a name: held until a moment, or falling to the floor and tipping",
)
def pink_slip(
    cv: Canvas,
    parent,
    x,
    y,
    *,
    name: str | None,
    rotation: float = 0.0,
    scale: float = 1.0,
    show: tuple[float, float] | None = None,
    fall: tuple[float, float] | None = None,
):
    """A sealed pink envelope whose middle rests on (``x``, ``y``), its flap drawn in and ``name`` (1 to
    :data:`SLIP_CHARS` characters; ``None``: its back, blank) lettered across it. ``show=(start, end)`` shows it
    only in that span (the slip in a hand or a beak); ``fall=(at, height)`` hides it until ``at``, then drops it
    ``height`` above its mark onto the mark in :data:`SLIP_FALL` seconds, tipping as it lands. A slip either is
    held or falls, not both."""
    if name is not None:
        cv.require_font("the pink slip's name is lettered in it")
    if name is not None and (not name.strip() or len(name) > SLIP_CHARS):
        raise PropError(f"the slip's name has 1 to {SLIP_CHARS} characters, got {name!r}")
    if show is not None and (not 0 <= show[0] < show[1] or fall is not None):
        raise PropError(f"show is one (start, end) span with 0 <= start < end, and never with fall, got {show!r}")
    if fall is not None and not (fall[0] >= 0 and fall[1] > 0):
        raise PropError(f"fall is (time >= 0, height > 0), got {fall!r}")
    if not (checks.number(scale) and scale > 0):
        raise PropError(f"scale must be a positive number, got {scale!r}")
    ink = cv.ink
    w, h = SLIP_SIZE
    g = cv.group(parent, cv.uid("pink-slip"), x=x, y=y, scaleX=scale, scaleY=scale, rotation=rotation)
    if show is not None:
        cv.gate(g, [show])
    if fall is not None:
        at, height = fall
        cv.keys(g, "opacity", [(0.0, 0), (at, 1)])
        cv.keys(g, "y", [(at, y - height), (at + SLIP_FALL, y)], hold=False)
        turn = [(at, rotation - 28), (at + SLIP_FALL * 0.7, rotation + 5), (at + SLIP_FALL, rotation)]
        cv.keys(g, "rotation", turn, hold=False)
    cv.ellipse(g, -w / 2 + 6, h / 2 - 4, w - 12, 14, "#5C4D3E", opacity=0.16)  # its shadow on the floor
    cv.rect(g, -w / 2, -h / 2, w, h, "#F4B6C2", ink, 3, radius=6)
    cv.path(g, f"M{-w / 2 + 4} {-h / 2 + 4} L0 {-h / 2 + 40} L{w / 2 - 4} {-h / 2 + 4}", stroke="#C9788A", sw=3)
    cv.ellipse(g, -9, -h / 2 + 31, 18, 18, "#C23B4E", ink, 2)  # the seal on the flap's point
    if name is not None:
        cv.text(g, cv.uid("pink-slip-name"), name, -w / 2 + 8, -h / 2 + 50, w - 16, 40, 30, ink, weight="700")
    return g


PARCEL_LABEL = 12  # characters an address label holds


@register("prop", "parcel", summary="A taped cardboard parcel with an address label, held against a chest or set down")
def parcel(cv: Canvas, parent, x, y, *, label: str | None = None, scale: float = 1.0, id: str = "parcel"):
    """A parcel whose box centre is (``x``, ``y``); ``label`` letters its address label (1 to :data:`PARCEL_LABEL`
    characters), ``None`` leaves the label blank."""
    if label is not None:
        if not (isinstance(label, str) and label.strip() and len(label) <= PARCEL_LABEL):
            raise PropError(f"a label has 1 to {PARCEL_LABEL} characters, got {label!r}")
        cv.require_font("the parcel's address label is set in it")
    if not (checks.number(scale) and scale > 0):
        raise PropError(f"scale must be a positive number, got {scale!r}")
    ink = cv.ink
    g = cv.group(parent, id, x=x, y=y, scaleX=scale, scaleY=scale)
    cv.rect(g, -120, -80, 240, 160, "#C99A62", ink, 4, radius=6)
    cv.rect(g, -120, -80, 240, 26, "#B5864F", ink, 3, radius=6)  # the top flap, in the light
    cv.rect(g, -14, -80, 28, 160, "#E2C48E", opacity=0.85)  # the tape
    cv.rect(g, 4, -10, 104, 64, "#FBF8EF", ink, 2.5, radius=4)
    for k in range(3):
        cv.line(g, 14, 30 + 8 * k, 96, 30 + 8 * k, "#B9B2A4", 2)
    if label is not None:
        cv.text(g, f"{id}-label", label, 8, -6, 96, 30, 18, "#2C2A26")
    return g
