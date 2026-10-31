#!/usr/bin/env python3
"""Low Balance, built with srstudio: a teller, a fee, and the one free thing in the bank.

    srstudio record low-balance PROJECT   # generated clips, resolved and pinned by the engine
    srstudio build low-balance PROJECT    # → PROJECT/low-balance.scene.xml

The customer asks about a twelve dollar fee, and the screen on the counter loses twelve more for asking. He tries to
close the account and cannot afford to. The pen is free. He walks off with it across the whole of the reception; the
chain runs out; it takes him back. He walks up to the counter in the first second.
"""

import os

from _common import project_root
from instagram_posts import POSTS
from low_balance_audio import INTERVIEW, TAKES
from srstudio import OFFICE, Episode, EpisodeSpec, camera, cast, cutout_counter, locations, props
from srstudio import interview as iv_audio

os.umask(0o077)  # generated outputs are private: folders 700, files 600

ep = Episode(
    EpisodeSpec(
        slug="low-balance",
        title="Low Balance",
        description="Bank comedy: a twelve dollar fee for a low balance, and the only free thing in the building. "
        "Native vector animation at the reception; ElevenLabs dialogue and sound effects.",
        root=project_root(__file__),
        **iv_audio.spec_font(INTERVIEW.font, project_root(__file__)),
        seed=3103,
        background="#2A2018",
        palette=OFFICE,
        audio=None,  # every clip is a pinned <generated> asset on its own track
        # no engine safe area: the camera crops the set on purpose; captions stay inside the vertical layout by hand
    )
)
ep.audio(extra=[("room-tone", "assets/room-tone.wav", {"role": "ambience"})])
t, cv = ep.t, ep.cv
L = [ep.P(i) for i in range(len(t.phrases))]
DURATION = t.duration
FIRST_FEE, LAST_FEE = (float(v) for v in t.meta["balance"])
GO, YANK, FLOOR = float(t.meta["go"]), float(t.meta["yank"]), float(t.meta["floor"])
TAKE = L[11].end + TAKES  # his hand reaches the pen
TELLER_AT = (540, 850, 1.05)
CUSTOMER_AT = (230, 1040, 1.15)  # his head, standing at the counter
READER_AT = (770, locations.COUNTER_Y + 4, 0.72)
PEN_AT = (392, locations.COUNTER_Y - 4)
HAND_UP = (146, 120)  # the hand, from the customer's head at scale 1, forearm raised to the counter
HAND_OUT = (175, 274)  # the same, carrying the pen in front of him
CHAIN = 580
WALK_TO = 700  # where his head gets to before the chain has a word
ARRIVES = 1.05  # the seconds of the walk up to the counter, under the first frame
COMES_FROM = 60  # where his middle starts it, half in at the frame's left edge
FLUNG_TO = 565  # his middle, on the floor
ON_THE_FLOOR = 1690  # his middle, lying down
S = CUSTOMER_AT[2]
WAIST = 330 * S  # from his head to his middle


def hand(x: float, y: float, reach: tuple[float, float]) -> tuple[float, float]:
    return x + reach[0] * S, y + reach[1] * S


GRIP = (
    (TAKE - 0.10, *PEN_AT),
    (TAKE + 0.08, *hand(*CUSTOMER_AT[:2], HAND_UP)),
    (GO - 0.15, *hand(*CUSTOMER_AT[:2], HAND_OUT)),
    (GO, *hand(*CUSTOMER_AT[:2], HAND_OUT)),
    (YANK + 0.40, *hand(WALK_TO + 120, CUSTOMER_AT[1], HAND_OUT)),  # past the end of the chain: it stops him first
)
RUN = cutout_counter.chain_run(*PEN_AT, CHAIN, GRIP, snap=YANK)
if RUN.taut is None or not YANK - 0.20 <= RUN.taut <= YANK:
    raise SystemExit(f"the chain runs out at {RUN.taut}, not on the yank at {YANK}: move the walk or the length")
teller = cast.Manager(cv)
customer = cast.Candidate(cv)


def walk_keys() -> tuple[list, list, list]:
    """Where the customer's middle is: walking up to the counter, at it, walking off with a bounce, flung back, and
    on the floor."""
    x0, y0 = CUSTOMER_AT[0], CUSTOMER_AT[1] + WAIST
    steps = 6
    top = RUN.taut
    xs, ys, turns = [(0, COMES_FROM)], [(0, y0)], [(0, -3)]
    for k in range(1, 5):  # up to the counter, with the same bounce
        at = ARRIVES * k / 4
        xs.append((at, COMES_FROM + (x0 - COMES_FROM) * k / 4))
        ys.append((at, y0 - (14 if k % 2 else 0)))
        turns.append((at, 3 if k % 2 else -3 if k < 4 else 0))
    xs.append((GO, x0))
    ys.append((GO, y0))
    turns.append((GO, 0))
    for k in range(1, steps + 1):
        at = GO + (top - GO) * k / steps
        xs.append((at, x0 + (WALK_TO - x0) * k / steps))
        ys.append((at, y0 - (14 if k % 2 else 0)))
        turns.append((at, 3 if k % 2 else -3))
    xs += [(top + 0.26, 460), (FLOOR, FLUNG_TO)]
    ys += [
        (top + 0.26, y0 - 170),
        (FLOOR, ON_THE_FLOOR),
        (FLOOR + 0.07, ON_THE_FLOOR - 26),
        (FLOOR + 0.16, ON_THE_FLOOR),
    ]
    turns += [(top + 0.26, -72), (FLOOR, -87)]
    return xs, ys, turns


def behind(g):
    cutout_counter.paper_poster(cv, g, 672, 575, width=190, height=240, size=34)
    ep.perform(
        teller,
        g,
        *TELLER_AT,
        arms="articulated",
        mouth=ep.mouth(
            "manager", smile=[(0, L[8].start), (L[9].start - 0.2, L[9].end + 0.5), (L[11].start, L[11].end + 0.2)]
        ),  # fmt: skip
        blinks=[
            (L[1].end + 0.10, L[1].end + 0.24),
            (L[5].end + 0.15, L[5].end + 0.29),
            (L[7].end + 0.50, L[7].end + 0.64),
            (L[9].end + 0.10, L[9].end + 0.24),
            (FLOOR + 0.60, FLOOR + 0.74),
        ],
        brows=(
            [(0, 0), (L[9].start - 0.2, 0), (L[9].start, -7), (L[9].end + 0.2, -7), (L[9].end + 0.4, 0)],
            [(0, 0), (L[9].start - 0.2, 0), (L[9].start, 7), (L[9].end + 0.2, 7), (L[9].end + 0.4, 0)],
        ),
        pupils=[(0, -31), (L[11].end + 0.3, -31), (L[11].end + 0.5, -22)],  # he goes back to his screen, and stays
        nods=[
            (0, 0),
            (L[1].start, 0),
            (L[1].start + 0.25, 3),
            (L[1].end, 0),
            (L[3].start, 0),
            (L[3].start + 0.25, -3),
            (L[3].end, 0),
            (L[5].start, 0),
            (L[5].start + 0.15, 4),
            (L[5].start + 0.35, 0),
            (L[7].start, 0),
            (L[7].start + 0.3, -3),
            (L[7].end, 0),
            (L[9].start, 0),
            (L[9].start + 0.3, 5),
            (L[9].end, 0),
            (L[11].end + 0.3, 0),
            (L[11].end + 0.5, 6),
        ],
    )


def on_desk(g):
    props.card_reader(
        cv,
        g,
        READER_AT[0],
        READER_AT[1],
        scale=READER_AT[2],
        readings=((0, "$31", "BALANCE"), (FIRST_FEE, "$19", "BALANCE"), (LAST_FEE, "$7", "BALANCE")),
    )


def front(g):
    walker = cv.group(g, "customer-walks", x=CUSTOMER_AT[0], y=CUSTOMER_AT[1] + WAIST)
    xs, ys, turns = walk_keys()
    cv.keys(walker, "x", xs, hold=False)
    cv.keys(walker, "y", ys, hold=False)
    cv.keys(walker, "rotation", turns, hold=False)
    ep.perform(
        customer,
        walker,
        0,
        -WAIST,
        S,
        arms="articulated",
        legs="standing",
        mouth=ep.mouth("candidate"),
        blinks=[
            (L[1].end + 0.30, L[1].end + 0.44),
            (L[3].end + 0.05, L[3].end + 0.19),
            (L[5].end + 0.40, L[5].end + 0.80),  # the slow one, at twelve more
            (L[7].end + 0.60, L[7].end + 1.00),
            (L[11].end + 0.05, L[11].end + 0.19),
        ],
        nods=[
            (0, 0),
            (L[0].start, 0),
            (L[0].start + 0.3, 4),
            (L[0].end, 0),
            (L[2].start, 0),
            (L[2].start + 0.3, -4),
            (L[2].end, 0),
            (L[4].start, 0),
            (L[4].start + 0.3, 3),
            (L[4].end, 0),
            (L[6].start, 0),
            (L[6].start + 0.2, -5),
            (L[6].end, 0),
            (L[8].start, 0),
            (L[8].start + 0.3, 4),
            (L[8].end, 0),
            (L[10].start, 0),
            (L[10].start + 0.3, 3),
            (L[10].end, 0),
            (FLOOR, 0),
            (FLOOR + 0.3, -8),  # the head comes round to the ceiling, and stays
        ],
        forearm=[(0, 0), (TAKE - 0.2, 0), (TAKE, -150), (GO - 0.15, -70), (YANK, -70), (YANK + 0.14, 20)],
    )
    cutout_counter.pen_on_chain(cv, g, *PEN_AT, length=CHAIN, grip=GRIP, snap=YANK)


reception = locations.reception(
    cv,
    locations.finish(cv, ep.comp),  # the Cutout grade over the set; the camera moves inside it
    behind_desk=behind,
    on_desk=on_desk,
    at_desk=front,
    shots=[(0, DURATION)],
)


FRAMES = {  # angle -> scale, x, y
    "two": (1.3, -99, -342),
    "teller": (1.7, -425, 800 - TELLER_AT[1] * 1.7),
    "wide": (1.0, 0, 0),
}
camera.reframe(cv, reception, [(c.time, *FRAMES[c.angle]) for c in t.cuts])

spoken = ep.captions(ep.spoken_captions(tail=0.25), x=80, y=1440, width=920, size=60)
ep.hide_on_cover(*spoken)
ep.markers(extra=[("marker-chain", YANK, "The chain runs out"), ("marker-floor", FLOOR, "The floor")])
ep.instagram(POSTS["low-balance"])
ep.finish()
