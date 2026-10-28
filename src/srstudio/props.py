"""Set dressing and hand props, each a registered builder ``fn(cv, parent, ...) -> node``."""

from __future__ import annotations

import math
import random

from .canvas import Canvas
from .registry import register

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


@register("prop", "papers", summary="A stack of documents with seeded random lines", episodes=("01", "02", "03", "04"))
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


@register("prop", "woodgrain", summary="Seeded grain strokes over a desk top", episodes=("01", "02", "03", "04"))
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


@register(
    "prop", "office-art", summary="The framed abstract print on the office wall", episodes=("01", "02", "03", "04")
)
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


@register("prop", "plant", summary="Potted plant with 18 formula-generated leaves", episodes=("01", "02", "03", "04"))
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


@register(
    "prop",
    "chair",
    summary="Office chair: the manager's black one or the candidate's gray one",
    episodes=("01", "02", "03", "04"),
)
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


@register(
    "prop",
    "chair-back",
    summary="The executive chair seen from behind, the occupant's crown above the headrest",
    episodes=("06",),
)
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


@register("prop", "laptop", summary="Open laptop on the interviewer's right", episodes=("01", "02", "03", "04"))
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


@register(
    "prop",
    "water-glass",
    summary="Glass of water at the edge of the reverse-angle desk",
    episodes=("01", "02", "03", "04"),
)
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


@register(
    "prop",
    "candidate-back",
    summary="The candidate seen from behind in the foreground of the wide shot",
    episodes=("01", "02", "03", "04"),
)
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


@register(
    "prop", "silent-phone", summary="A phone face up on the desk with a muted work notification", episodes=("02",)
)
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


@register("prop", "coffee-cup", summary="Takeaway cup with lid and a foam heart", episodes=("05",))
def coffee_cup(cv: Canvas, parent, x, y, scale=1, rotation=0):
    ink, clear, white = cv.ink, cv.clear, cv.white
    g = cv.group(parent, cv.uid("coffee-cup"), x=x, y=y, scaleX=scale, scaleY=scale, rotation=rotation)
    cv.ellipse(g, -29, 56, 64, 10, "#5C4D3E", opacity=0.16)
    cv.path(g, "M-28 -18 L28 -18 L22 57 Q0 66 -22 57Z", white, ink, 3)
    cv.path(g, "M-26 11 L26 11 L24 37 L-24 37Z", "#B27F51", clear, 0)
    cv.ellipse(g, -32, -25, 64, 15, "#3E4947", ink, 3)
    cv.rect(g, -31, -19, 62, 10, "#4B5550", ink, 2, radius=3)
    cv.ellipse(g, -5, 17, 12, 13, "#F3DDAD")
    cv.path(g, "M-1 20 Q7 26 0 29", stroke="#94683E", sw=1.2)
    return g


@register("prop", "menu-board", summary="Chalkboard menu with the Free Wi-Fi line", episodes=("05",))
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


@register("prop", "cafe-window", summary="Window onto the street, the view clipped by a rect mask", episodes=("05",))
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


@register("prop", "pendant-light", summary="Hanging pendant lamp", episodes=("05",))
def pendant_light(cv: Canvas, parent, x):
    cv.line(parent, x, -200, x, 174, "#3C4C49", 5)
    cv.path(parent, f"M{x - 74} 218 Q{x - 60} 154 {x} 153 Q{x + 60} 154 {x + 74} 218Z", "#8E5141", cv.ink, 5)
    cv.ellipse(parent, x - 76, 207, 152, 24, "#F2CF91", cv.ink, 4)


@register("prop", "bean-jar", summary="Jar of coffee beans on the shelf", episodes=("05",))
def bean_jar(cv: Canvas, parent, x):
    cv.rect(parent, x, 915, 67, 97, "#C2B595", cv.ink, 3, radius=8)
    cv.rect(parent, x - 3, 908, 73, 17, "#70513C", cv.ink, 3, radius=4)
    for k in range(8):
        cv.ellipse(parent, x + 9 + (k % 3) * 18, 948 + (k // 3) * 17, 12, 7, "#684E3A", rotation=30)


@register(
    "prop", "espresso-machine", summary="Espresso machine with steam that breathes by expression", episodes=("05",)
)
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


@register("prop", "pastry-stand", summary="Plate of croissants on the counter", episodes=("05",))
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


@register("prop", "building", summary="Background apartment block with lit windows", episodes=("05",))
def building(cv: Canvas, parent, x, y, w, h):
    cv.rect(parent, x, y, w, h, "#A9BCAD")
    for wx in range(int(x + 20), min(1060, int(x + w - 10)), 38):
        for wy in range(int(y + 30), 690, 55):
            cv.rect(parent, wx, wy, 16, 23, "#D9E1CD", radius=2)


@register("prop", "tree", summary="Park tree whose canopy sways by expression", episodes=("05",))
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


@register("prop", "shrub", summary="Small planted shrub along the path", episodes=("05",))
def shrub(cv: Canvas, parent, x):
    cv.path(parent, f"M{x} 1410 q-30 -60 -45 -40 q32 0 45 40 q16 -79 38 -68 q-10 45 -38 68Z", "#6F9563", cv.ink, 2)


@register("prop", "park-sign", summary="PUBLIC PARK sign on a post", episodes=("05",))
def park_sign(cv: Canvas, parent, text="PUBLIC\nPARK"):
    cv.line(parent, 916, 520, 916, 1040, "#637969", 8)
    cv.rect(parent, 785, 526, 260, 112, "#486C58", cv.ink, 4, radius=13)
    cv.text(parent, "park-sign", text, 804, 538, 222, 88, 32, "#F0E7CF")


@register("prop", "bench", summary="Slatted wooden park bench", episodes=("05",))
def bench(cv: Canvas, parent):
    p = cafe_paints(cv)
    for yy in [1030, 1100, 1170]:
        cv.rect(parent, 210, yy, 635, 48, p["wood"], cv.ink, 4, radius=7)
    for xx in [240, 779]:
        cv.path(parent, f"M{xx} 1045 L{xx - 18} 1555 L{xx + 13} 1555 L{xx + 38} 1045Z", "#4A5C54", cv.ink, 3)
    cv.rect(parent, 187, 1268, 681, 48, p["wood"], cv.ink, 4, radius=8)
    cv.rect(parent, 187, 1317, 681, 22, "#8B5F3D", cv.ink, 3, radius=5)
