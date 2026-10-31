#!/usr/bin/env python3
"""Scan the Code, built with srstudio: Milo wants a menu, and Ava is standing right there.

    srstudio record scan-the-code PROJECT   # generated clips, resolved and pinned by the engine
    srstudio build scan-the-code PROJECT    # → PROJECT/scan-the-code.scene.xml

Milo asks for a menu and gets a code. The code wants his email, then his location, then Ava turns and the code is on
her apron. The phone asks how she is doing, while she watches. The pigeon at the next table has a paper menu. Milo
holds his phone over his water and opens his hand. The heavy plop is synthesised here, from
:func:`srstudio.foley.plop`. The last hold is on Ava's face. The opening moves from the first frame (arm B of the
``sp-hook_motion`` test).
"""

import os

from _common import project_root
from instagram_posts import POSTS
from scan_the_code_audio import BUBBLES, INTERVIEW, SEED, SOUP, TURN
from srstudio import CAFE, Episode, EpisodeSpec, camera, cast, cutout_counter, foley, locations, props
from srstudio import interview as iv_audio

os.umask(0o077)  # generated outputs are private: folders 700, files 600

ROOT = project_root(__file__)
ep = Episode(
    EpisodeSpec(
        slug="scan-the-code",
        title="Scan the Code",
        description="Café comedy: a man who wants a paper menu, a code that wants his email, and a glass of water. "
        "Native vector animation in the café; ElevenLabs dialogue and sound effects, synthesised foley.",
        root=ROOT,
        **iv_audio.spec_font(INTERVIEW.font, ROOT),
        seed=SEED,
        background="#F0DDC0",
        palette=CAFE,
        audio=None,  # every clip is a pinned <generated> asset on its own track
        # no engine safe area: the camera crops the set on purpose; captions stay inside the vertical layout by hand
    )
)
t, cv = ep.t, ep.cv
L = [ep.P(i) for i in range(len(t.phrases))]
DURATION = t.duration
TURNS, LIFT, PIGEON = (float(t.meta[k]) for k in ("turn", "lift", "pigeon"))
OVER, LET_GO, PLOP = (float(t.meta[k]) for k in ("over", "let_go", "plop"))
SCANNED, CHIME, BOWL, MENU = (float(t.meta["cues"][k]) for k in ("scan", "chime", "bowl", "menu"))
foley.write_plop(ROOT / "assets" / "plop.wav", [PLOP], DURATION, seed=SEED)
ep.audio(
    extra=[
        ("room-tone", "assets/room-tone.wav", {"role": "ambience"}),
        ("plop", "assets/plop.wav", {"role": "effects", "gain": 0}),
    ]
)

AVA_AT, MILO_AT = (770, 760, 1.55), (300, 950, 1.30)
ARRIVES_FROM = 230  # she is half in the frame on the first frame, and still walking
ARRIVES = 0.95
TABLE_Y = 1180
TABLE_X, TABLE_WIDE = 540, 860
TENT_AT = (540, 1270)
NEXT_TABLE = (1375, 520)  # the pigeon's, past the edge of the two-shot
GLASS_BASE = (140, 1268)
GLASS_SCALE = 1.35
SURFACE = GLASS_BASE[1] - (1575 - 1431) * GLASS_SCALE
HAND_SCALE = 0.38  # the hand and the phone over the glass, small enough to go in
MILO_SKIN, MILO_SLEEVE = cast.Customer.skin, "#527B90"
AVA_SKIN, AVA_SLEEVE = cast.Barista.skin, "#F5EAD4"


def spans(angle: str) -> list[tuple[float, float]]:
    """The time ``angle`` is on screen."""
    ends = [c.time for c in t.cuts[1:]] + [DURATION]
    return [(c.time, end) for c, end in zip(t.cuts, ends, strict=True) if c.angle == angle]


def carried(g, draw, name, land, frm, to, rotation, *, skin, sleeve, scale=1.0, grip=60.0, comes=0.35, leaves=0.3):
    """A hand brings ``draw`` from ``frm`` to ``to`` by ``land``, leaves it there and goes back out of frame."""
    arm = cv.group(g, f"{name}-carrying", x=frm[0], y=frm[1])
    cv.gate(arm, [(land - comes, land)])
    for i, prop in enumerate(("x", "y")):
        cv.keys(arm, prop, [(land - comes, frm[i]), (land, to[i])], kind="sine-in-out")
    cutout_counter.reaching_hand(
        cv, arm, 0, 0, scale=scale, rotation=rotation, grip=grip, skin=skin, sleeve=sleeve, id=f"{name}-hand",
        holds=lambda h: draw(h, f"{name}-held"),
    )  # fmt: skip
    laid = cv.group(g, f"{name}-laid", x=to[0], y=to[1])
    cv.gate(laid, [(land, DURATION)])
    draw(laid, f"{name}-down")
    empty = cv.group(g, f"{name}-going", x=to[0], y=to[1])
    cv.gate(empty, [(land, land + leaves + 0.1)])
    for i, prop in enumerate(("x", "y")):
        cv.keys(empty, prop, [(land + 0.1, to[i]), (land + 0.1 + leaves, frm[i])], kind="sine-in-out")
    cutout_counter.reaching_hand(
        cv, empty, 0, 0, scale=scale, rotation=rotation, grip=grip, skin=skin, sleeve=sleeve, id=f"{name}-empty",
    )  # fmt: skip


def lit(g, x, y, scale, title, lines, name, shown=None):
    """A phone with a lit halo round it."""
    p = cv.group(g, name)
    if shown:
        cv.gate(p, shown)
    cv.ellipse(p, x - 150 * scale, y - 215 * scale, 300 * scale, 430 * scale, "#FFF2C4", opacity=0.45)
    cutout_counter.phone_screen(cv, p, x, y, scale=scale, title=title, lines=lines, id=f"{name}-screen")


def over_tent(g):
    """Milo's phone at the table's code, twice: the sign-up, then the location."""
    hand = cv.group(g, "tent-hand")
    cv.gate(hand, spans("tent"))
    x, y = 405, 1035
    first, second = spans("tent")
    cv.keys(hand, "y", [(first[0], 620), (first[0] + 0.45, 0)], kind="sine-in-out")

    def phones(h):
        lit(h, 0, 0, 1.0, "Scanning", (), "scan-phone", [(0, SCANNED)])
        lit(h, 0, 0, 1.0, "Sign up", ("Email", "to see soup"), "email-phone", [(SCANNED, second[0])])
        lit(h, 0, 0, 1.0, "Allow", ("Your location", "to see soup"), "where-phone", [(second[0], DURATION)])

    cutout_counter.reaching_hand(
        cv, hand, x, y, scale=0.86, grip=80, skin=MILO_SKIN, sleeve=MILO_SLEEVE, holds=phones, id="tent-reach"
    )


def held_up(g):
    """The phone comes up to her, as slowly as he can stand: the code, the chime, and the question."""
    hand = cv.group(g, "held-hand")
    cv.gate(hand, [(LIFT, PIGEON)])
    cv.keys(hand, "y", [(LIFT, 640), (CHIME, 0)], kind="sine-in-out")

    def phone(h):
        lit(h, 0, 0, 1.0, "Scanning", (), "held-scan", [(LIFT, CHIME)])
        lit(h, 0, 0, 1.0, "Hi Milo!", ("How's Ava", "doing so far?", "Rate Ava"), "held-rate", [(CHIME, PIGEON)])

    cutout_counter.reaching_hand(
        cv, hand, 395, 945, scale=1.25, grip=80, skin=MILO_SKIN, sleeve=MILO_SLEEVE, holds=phone, id="held-reach"
    )


def glass(g):
    """The water glass, and the phone that goes into it."""
    x, y = GLASS_BASE
    group = cv.group(
        g, "glass", x=x - 1093 * GLASS_SCALE, y=y - 1575 * GLASS_SCALE, scaleX=GLASS_SCALE, scaleY=GLASS_SCALE
    )
    props.water_glass(cv, group)
    falling = cv.group(g, "falling-phone", x=x, y=880)
    cv.gate(falling, [(LET_GO, DURATION)])
    cv.keys(falling, "y", [(LET_GO, 880), (PLOP, SURFACE - 40), (PLOP + 0.4, y - 80)], hold=False)
    cv.keys(falling, "rotation", [(LET_GO, 0), (PLOP, 2), (PLOP + 0.4, 5)], hold=False)
    cutout_counter.phone_screen(cv, falling, 0, 0, scale=HAND_SCALE, title="Hi Milo!", id="sunk-phone")
    over = cv.group(group, "glass-water-over", opacity=0.55)
    cv.path(over, "M1067 1431 Q1090 1444 1121 1430 L1114 1560 Q1090 1573 1073 1560Z", "#9FC0CA", cv.clear, 0)
    cutout_counter.rising_bubbles(
        cv, g, x, y - 20, start=PLOP + 0.12, width=44, height=y - 20 - SURFACE, count=14,
        seconds=BUBBLES - 0.2, seed=SEED, id="glass-bubbles",
    )  # fmt: skip
    cutout_counter.water_splash(cv, g, x, SURFACE, start=PLOP, reach=135, seed=SEED, id="glass-splash")


def over_glass(g):
    """His hand over the glass; it opens, and goes."""
    x, y = GLASS_BASE[0], 880
    hand = cv.group(g, "glass-hand")
    cv.gate(hand, [(OVER, PLOP + 0.75)])
    cv.keys(hand, "x", [(OVER, -260), (OVER + 0.3, 0), (PLOP + 0.4, 0), (PLOP + 0.75, -340)], kind="sine-in-out")

    def phone(h):
        turned = cv.group(h, "glass-hand-phone", rotation=-60)
        cv.gate(turned, [(OVER, LET_GO)])
        cutout_counter.phone_screen(cv, turned, 0, 0, title="Hi Milo!", id="glass-phone")

    cutout_counter.reaching_hand(
        cv, hand, x, y, scale=HAND_SCALE, rotation=60, grip=80, skin=MILO_SKIN, sleeve=MILO_SLEEVE, holds=phone,
        id="glass-reach",
    )  # fmt: skip


def table(g):
    """The two of them behind the cloth, and everything on it."""
    ep.perform(
        milo,
        g,
        *MILO_AT,
        mouth=ep.mouth("milo"),
        held_cup=[(0, 0)],
        blinks=[(0.9, 1.04), (L[3].end + 0.1, L[3].end + 0.26), (L[8].end + 0.2, L[8].end + 0.5), (PLOP, PLOP + 0.6)],
        nods=[
            (0, 0),
            (L[0].start, 0),
            (L[0].start + 0.3, 4),
            (L[0].end, 0),
            (L[6].start, 0),
            (L[6].start + 0.4, -4),
            (L[6].end, 0),
        ],
    )
    walk = cv.group(g, "ava-walks", x=ARRIVES_FROM, y=0)
    cv.keys(walk, "x", [(0, ARRIVES_FROM), (ARRIVES, 0)], kind="sine-in-out")
    cv.keys(walk, "y", [(i * ARRIVES / 6, 16 * (i % 2)) for i in range(7)], kind="sine-in-out")
    turn = cv.group(walk, "ava-turns", x=AVA_AT[0], y=0)
    half = TURNS + TURN / 2
    cv.keys(turn, "scaleX", [(TURNS, 1), (half, 0.04), (TURNS + TURN, 1)], kind="sine-in-out")
    ep.perform(
        ava,
        turn,
        0,
        *AVA_AT[1:],
        name=None,  # a code goes on this apron, and the tag would show under it
        mouth=ep.mouth("ava"),
        blinks=[(L[3].end + 0.2, L[3].end + 0.34), (L[7].end + 0.9, L[7].end + 1.04)],  # none in the last hold
        nods=[
            (0, -3),
            (0.35, 2),
            (0.7, -2),
            (ARRIVES, 0),
            (L[1].start, 0),
            (L[1].start + 0.25, 3),
            (L[1].end, 0),
            (L[5].start, 0),
            (L[5].start + 0.25, -3),
            (L[5].end, 0),
        ],
    )
    code = cv.group(turn, "apron-code", x=0, y=AVA_AT[1] + 212 * AVA_AT[2])
    cv.gate(code, [(half, DURATION)])
    cutout_counter.qr_code(cv, code, 0, 0, size=136, seed=SEED + 1, id="apron-qr")
    cutout_counter.cafe_table(cv, g, TABLE_X, TABLE_Y, width=TABLE_WIDE, id="milo-table")
    cutout_counter.table_tent(cv, g, *TENT_AT, seed=SEED, id="tent")
    glass(g)
    next_table(g)
    over_tent(g)
    held_up(g)
    over_glass(g)
    carried(
        g,
        lambda h, name: cutout_counter.paper_menu(cv, h, 0, 0, scale=0.86, lying=True, id=name),
        "menu",
        MENU,
        (760, 1040),
        (290, 1262),
        -80,
        skin=AVA_SKIN,
        sleeve=AVA_SLEEVE,
        scale=0.62,
        grip=90,
    )


def next_table(g):
    """The pigeon's table: a paper menu, read, and the soup arriving."""
    x, wide = NEXT_TABLE
    cast.pigeon(
        cv, g, x + 30, 1090, 1.15, flip=True, id="reader",
        nods=[(PIGEON, 0), (PIGEON + 0.3, 7), (PIGEON + 0.55, 0), (BOWL + 0.5, 0), (BOWL + 0.75, 9), (BOWL + 1.0, 0)],
    )  # fmt: skip
    cutout_counter.cafe_table(cv, g, x, TABLE_Y, width=wide, id="pigeon-table")
    cutout_counter.paper_menu(cv, g, x - 140, 1168, scale=0.62, rotation=-6, id="pigeon-menu")
    carried(
        g,
        lambda h, name: cutout_counter.soup_bowl(cv, h, 0, 0, scale=0.7, id=name),
        "soup",
        BOWL,
        (1820, 1200),
        (x + 110, 1262),
        -86,
        skin=AVA_SKIN,
        sleeve=AVA_SLEEVE,
        scale=0.62,
        grip=90,
        comes=SOUP - 0.1,
    )


ava = cast.Barista(cv)
milo = cast.Customer(cv)
cafe = ep.setup(locations.cafe, [(0, DURATION)], at_counter=table, menu=("SCAN", "SCAN", "NO MENUS"))


def close(at, scale, to=(540, 800)):
    x, y = at
    return scale, to[0] - x * scale, to[1] - y * scale


FRAMES = {  # angle -> scale, x, y
    "wide": close((530, 1010), 1.15, (540, 810)),
    "ava": close(AVA_AT[:2], 1.42, (540, 640)),
    "milo": close(MILO_AT[:2], 1.5, (540, 720)),
    "tent": close((TENT_AT[0] - 40, 1120), 2.0, (640, 730)),
    "held-up": close((AVA_AT[0] - 70, 900), 1.45, (610, 760)),
    "pigeon": close((NEXT_TABLE[0], 1120), 1.72, (540, 860)),
    "glass": close((GLASS_BASE[0] + 90, 1030), 3.0, (540, 700)),
    "face": close(AVA_AT[:2], 1.95, (540, 610)),
}
camera.reframe(cv, cafe, [(c.time, *FRAMES[c.angle]) for c in t.cuts])

spoken = ep.captions(ep.spoken_captions(tail=0.25), x=80, y=1290, width=920, size=60)
ep.hide_on_cover(*spoken)
ep.markers(extra=[("marker-apron", TURNS, "Scan me"), ("marker-plop", PLOP, "Plop")])
ep.instagram(POSTS["scan-the-code"])
ep.finish()
