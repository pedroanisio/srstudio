#!/usr/bin/env python3
"""The Reference, built with srstudio: a bathrobe, a blazer, and a man on his knees with cue cards.

    srstudio record the-reference PROJECT   # generated clips, resolved and pinned by the engine
    srstudio build the-reference PROJECT    # → PROJECT/the-reference.scene.xml

From the first frame the cards are shaking and the camera is easing back: Rosa at the desk in a blazer over a bathrobe,
Milo on his knees beside her, a speakerphone between them. "You managed Milo for six years?" "Seven. Felt longer." "Is
he reliable?" "Very. Apart from the forty dollars." "What forty dollars?" "Would you hire him again?" She looks at him
and lets it sit. He takes two bills from his wallet and slides them over. "In a heartbeat." "You sound like a wonderful
leader. We have an opening above him." She looks at the speakerphone, at him; the cards come down. "I'd need a
reference." His hand comes out. "Forty dollars." Stop on the hand.

Arm B of the ``sp-hook_motion`` test: the frame moves from its first frame. No music: the foley is synthesized here. It
declares no engine safe area, so captions are placed inside x 80–920 by hand.
"""

import os

from _common import project_root
from instagram_posts import POSTS
from srstudio import OFFICE, Episode, EpisodeSpec, cast, cutout_home, cutout_reference, foley, locations, props
from srstudio import interview as iv_audio
from srstudio.cutout_reach import hand_at, reach
from the_reference_audio import INTERVIEW

os.umask(0o077)  # generated outputs are private: folders 700, files 600

ROOT = project_root(__file__)
ep = Episode(
    EpisodeSpec(
        slug="the-reference",
        title=INTERVIEW.title,
        description="Job-hunting comedy: a reference on speakerphone, in a blazer over a bathrobe, renegotiated line "
        "by line. Native vector animation; ElevenLabs dialogue, synthesized foley.",
        root=ROOT,
        **iv_audio.spec_font(INTERVIEW.font, ROOT),
        seed=31282,
        background="#A5B9AF",
        palette=OFFICE,
        audio=None,  # every clip is a pinned <generated> asset on its own track
    )
)
t, cv = ep.t, ep.cv
SITS, WALLET = float(t.meta["sits"]), float(t.meta["wallet"])
SLIDES, PAID = float(t.meta["slides"]), float(t.meta["paid"])
LOWERS, OFFERS = float(t.meta["lowers"]), float(t.meta["offers"])
DURATION = t.duration
L = [ep.P(i) for i in range(len(t.phrases))]
ROSA_AT = (315, 530, 1.62)
MILO_AT = (790, 770, 1.35)
CARDS_UP = (800, 480)
CARDS_DOWN = (790, 1060)
SHOULDERS = ((692, 952), (888, 952))
BILLS_FROM = (690, 1040)
BILLS_TO = (610, 1140)
PHONE = (455, 1040)
SKIN = cast.Customer.skin
OPEN_HAND = (585, 905)
ON_DESK = WALLET + 0.25  # his right hand comes over the desk: the shoulder it hangs from is below the desk's edge

shake = [(k * 0.15, CARDS_UP[0] + (3 if k % 2 else -3), CARDS_UP[1] + (2 if k % 3 else -3))
         for k in range(1, int((LOWERS - 0.2) / 0.15))]  # fmt: skip
CARDS = [(0.0, *CARDS_UP), *shake, (LOWERS, *CARDS_UP), (LOWERS + 0.55, *CARDS_DOWN)]
CARD_HAND = (-152, 42)
RIGHT_HOLD = (CARDS_UP[0] + 152, CARDS_UP[1] + 42)
RIGHT = [
    (0.0, *RIGHT_HOLD),
    (WALLET - 0.45, *RIGHT_HOLD),
    (WALLET - 0.1, 905, 985),
    (WALLET + 0.25, 905, 985),
    (SLIDES, *BILLS_FROM),
    (PAID, BILLS_TO[0] + 34, BILLS_TO[1]),
    (PAID + 0.5, 905, 985),
    (OFFERS - 0.1, 905, 985),
    (OFFERS + 0.3, *OPEN_HAND),
]
left = [(s, x + CARD_HAND[0], y + CARD_HAND[1]) for s, x, y in CARDS]
samples = [k / 30 for k in range(int(DURATION * 30) + 1)]

foley.write_bursts(ROOT / "assets" / "slide.wav", [SLIDES + 0.03], DURATION, foley.SCRAPE, seed=31283)
foley.write_bursts(ROOT / "assets" / "wallet.wav", [WALLET + 0.05], DURATION, foley.REMOTE_CLICK, seed=31284)
foley.write_bursts(ROOT / "assets" / "cards.wav", [LOWERS + 0.02], DURATION, foley.SWISH, seed=31285)
ep.audio(
    extra=[
        ("room-tone", "assets/room-tone.wav", {"role": "ambience"}),
        ("slide", "assets/slide.wav", {"role": "effects", "gain": -5}),
        ("wallet", "assets/wallet.wav", {"role": "effects", "gain": -9}),
        ("cards", "assets/cards.wav", {"role": "effects", "gain": -10}),
    ],
    loudness="-14",
)


def rosa(g):
    """Eyes on the speakerphone, except when she wants something."""
    who = cast.Rosa(cv, tag="rosa-character")
    ep.perform(
        who,
        g,
        *ROSA_AT,
        mouth=ep.mouth("rosa", smile=[(L[6].start - 0.2, L[6].start), (L[6].end, L[7].start + 0.8)]),
        blinks=[(L[1].end + 0.1, L[1].end + 0.24), (SITS + 0.9, SITS + 1.04), (LOWERS - 0.5, LOWERS - 0.36)],
        nods=[(0, 3), (L[1].start, 3), (L[1].start + 0.3, 6), (L[3].start, 4), (SITS, 4), (SITS + 0.3, 0),
              (L[6].start, 0), (L[6].start + 0.3, 5), (L[7].end, 5), (LOWERS, 2), (L[8].start, 2),
              (L[8].start + 0.3, 6)],
        stitch=None,
    )  # fmt: skip
    look_x = [(0, 6), (L[3].end, 6), (L[3].end + 0.1, 12), (L[4].end, 12), (L[4].end + 0.1, 6), (SITS, 6),
              (SITS + 0.1, 15), (L[6].start, 15), (L[6].start + 0.1, 6), (L[7].end + 0.2, 6),
              (L[7].end + 0.3, 2), (L[7].end + 0.75, 2), (L[7].end + 0.85, 15)]  # fmt: skip
    cv.keys(who.eyes, "x", look_x, hold=False)
    cv.keys(who.eyes, "y", [(0, 12), (SITS, 12), (SITS + 0.1, 0), (L[6].start, 0), (L[6].start + 0.1, 12),
                            (L[7].end + 0.75, 12), (L[7].end + 0.85, 0)], hold=False)  # fmt: skip
    cutout_reference.robe_and_blazer(cv, who.group)


def milo(g):
    """On his knees, head just over the desk, his eyes on her."""
    who = cast.Customer(cv, tag="milo-character", seated=True)
    ep.perform(
        who,
        g,
        *MILO_AT,
        mouth=ep.mouth("milo"),
        blinks=[(L[2].end, L[2].end + 0.14), (SITS + 0.5, SITS + 0.64), (L[8].end - 0.1, L[8].end + 0.04)],
        nods=[(0, 0), (L[3].end - 0.5, 0), (L[3].end - 0.3, -4), (L[4].end, -4), (L[4].end + 0.3, 2), (WALLET, 2),
              (WALLET + 0.3, 8), (PAID + 0.4, 2), (OFFERS, 2), (OFFERS + 0.3, -4)],
        free_arms=("left", "right"),
    )  # fmt: skip
    cv.keys(who.eyes, "x", [(0, -10)], hold=False)


def cards(g):
    """The stack in his hands, its top card the line he wants from her."""
    move = cv.group(g, "cards-held", x=CARDS_UP[0], y=CARDS_UP[1])
    track = [(s, *hand_at(CARDS, s)) for s in samples if s <= LOWERS + 0.6]
    cv.keys(move, "x", [(s, x) for s, x, _ in track], hold=False)
    cv.keys(move, "y", [(s, y) for s, _, y in track], hold=False)
    cutout_reference.cue_cards(
        cv,
        move,
        0,
        0,
        words=("SIX YEARS", "VERY RELIABLE", "IN A HEARTBEAT"),
        spans=[(0.0, L[1].end + 0.2), (L[1].end + 0.2, L[4].end + 0.1), (L[4].end + 0.1, DURATION)],
        scale=1.04,
    )
    reach(cv, g, "milo-card-arm", SHOULDERS[0], left, skin=SKIN, hand=46, width=7, sleeve="#527B90")
    up = cv.group(g, "milo-arm-up")
    cv.gate(up, [(0.0, ON_DESK)])
    reach(cv, up, "milo-reach-up", SHOULDERS[1], RIGHT, skin=SKIN, hand=46, width=7, sleeve="#527B90")


def behind(g):
    rosa(g)
    milo(g)
    cards(g)


def on_desk(g):
    props.speakerphone(cv, g, *PHONE, talk=[(L[i].start, L[i].end) for i in (0, 2, 5, 7)])
    bills = cv.group(g, "bills", x=BILLS_FROM[0], y=BILLS_FROM[1])
    cv.gate(bills, [(ON_DESK, DURATION)])
    path = [(s, *hand_at(RIGHT, s)) for s in samples if ON_DESK <= s <= PAID]
    follow = [(s, x - 34, y) for s, x, y in path]
    cv.keys(bills, "x", [(s, x) for s, x, _ in follow], hold=False)
    cv.keys(bills, "y", [(s, y) for s, _, y in follow], hold=False)
    cutout_reference.banknotes(cv, bills, 0, 0, value="20", scale=0.9)
    over = cv.group(g, "milo-arm-over")
    cv.gate(over, [(ON_DESK, DURATION)])
    _, grip = reach(cv, over, "milo-reach", SHOULDERS[1], RIGHT, skin=SKIN, hand=46, width=7, sleeve="#527B90")
    palm = cv.group(grip, "open-palm")
    cv.gate(palm, [(OFFERS + 0.1, DURATION)])
    for k, (fx, turn) in enumerate(((-26, -14), (-9, -4), (9, 4), (26, 14))):
        cv.rect(cv.group(palm, f"finger-{k}", x=fx, y=-16, rotation=turn), -8, -48, 16, 52, SKIN, cv.ink, 3, radius=8)
    cv.ellipse(palm, -34, -30, 68, 72, SKIN, cv.ink, 3.5)
    cv.path(palm, "M30 8 Q56 -6 58 -30 Q62 -40 50 -38 Q34 -18 24 -8", SKIN, cv.ink, 3.5)
    cv.path(palm, "M-20 2 Q2 20 22 -2", stroke="#C49C78", sw=3)


finish = locations.finish(cv, ep.comp)
room = cutout_home.home_study(cv, finish, behind_desk=behind, on_desk=on_desk, shots=[(0, DURATION)])

MILO_CLOSE = (MILO_AT[0] - 30, MILO_AT[1] - 40)
ROSA_CLOSE = (ROSA_AT[0] + 150, ROSA_AT[1] + 100)
FIRST = 1.08
FIRST_AT = (520, 640)  # pushed in from the first frame, with both marks whole
LAST = 1.2
LAST_AT = (498, 760)  # as close as the frame goes with the cactus and the whole paper still in it
A, B = L[4].start - 0.08, L[4].end + 0.12  # the punch on "What forty dollars?"
OUT = L[0].end


def framing(size: float, at: tuple[float, float]) -> tuple[float, float, float]:
    return size, 540 - at[0] * size, 760 - at[1] * size


WIDE = (1.0, 0.0, 0.0)
keys = [
    (0.0, framing(FIRST, FIRST_AT)),
    (OUT, WIDE),
    (A - 0.02, WIDE),
    (A, framing(1.5, MILO_CLOSE)),
    (B - 0.02, framing(1.5, MILO_CLOSE)),
    (B, WIDE),
    (SITS + 0.2, WIDE),
    (WALLET, framing(1.3, ROSA_CLOSE)),
    (SLIDES - 0.3, framing(1.3, ROSA_CLOSE)),
    (L[6].start - 0.3, WIDE),
    (L[7].end, WIDE),
    (OFFERS, framing(1.12, ROSA_CLOSE)),
    (OFFERS + 0.1, framing(1.12, ROSA_CLOSE)),
    (DURATION, framing(LAST, LAST_AT)),
]
for i, prop in enumerate(("scaleX", "x", "y")):
    cv.keys(room, prop, [(at, frame[i]) for at, frame in keys], hold=False)
cv.keys(room, "scaleY", [(at, frame[0]) for at, frame in keys], hold=False)

spoken = ep.captions(ep.spoken_captions(), x=80, y=1420, width=920, size=60)
ep.hide_on_cover(*spoken)
ep.markers(extra=[("marker-sits", SITS, "She lets it sit"), ("marker-paid", PAID, "Paid")])
ep.instagram(POSTS["the-reference"])
ep.finish()
