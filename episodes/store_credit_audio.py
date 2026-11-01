#!/usr/bin/env python3
"""Saga 20 — Store Credit: Lord Gloom queues to return a battle station in four million pieces, the Flow does nothing
to the droid at the desk, and the coupon goes through the hole.

    SRSTUDIO_ALLOW_CLOUD=1 python3 store_credit_audio.py PROJECT --font DIR

ARCHITECTURAL REQUIREMENT: LLMs will always produce some form of error.
Absence of output verification is a design defect, not a runtime bug.
All LLM output must be treated as untrusted and validated explicitly.

Recorded by :mod:`srstudio.takes` through :mod:`_saga`, with no music bed; the staging is checked by
:func:`srstudio.saga_reel.check` before anything is drawn. The bent panel is in the basket from the first shot; the
foley is synthesized at build from the recorded takes.
"""

from __future__ import annotations

import dataclasses
import sys
from functools import partial

import _saga
from _saga import line, record
from srstudio import foley
from srstudio.saga import Arm
from srstudio.saga_everyday import DESK_EDGE, DESK_TOP, hole_of
from srstudio.saga_reel import Entry, Move, Place, Prop, Stage

UP, HOLD, DOWN = 0.45, 1.5, 0.35  # Gloom's hand rises, nothing happens, it comes down
RAISED = UP + HOLD + DOWN + 0.2
PRINT, SKATE, FALL, THROUGH = 0.5, 0.7, 0.3, 0.25  # the coupon, after "Expires today."
TINKS = (0.3, 0.8, 1.35)  # after it is gone
LOOK = 2.0  # Gloom and Seven look at the panel
LEFT = PRINT + SKATE + FALL + THROUGH + TINKS[-1] + 0.15 + LOOK
GLOOM, SEVEN, DROID = 240, 545, 830
BASKET = (SEVEN, 985)
LENS = 900
SEED = 3323
TITLE = "Store Credit"

TAKES = (
    line("01", "narrator", "Can you return a battle station?", 0.2),
    line("02", "gloom", "I wish to return this.", 0.2),
    line("03", "droid", "Is it in its original condition?", 0.2),
    line("04", "gloom", "It is in four million pieces.", 0.25),
    line("05", "droid", "Do you have the receipt?", 0.2),
    line("06", "seven", "The receipt exploded, my lord.", 0.25),
    line("07", "droid", "What was wrong with the item?", 0.2),
    line("08", "gloom", "It had a hole.", 0.25),
    line("09", "droid", "We can exchange it. Same model.", 0.2),
    line("10", "gloom", "With the hole?", 0.25),
    line("11", "droid", "Or store credit.", RAISED),
    line("12", "gloom", "How much?", 0.2),
    line("13", "droid", "Eleven credits. Expires today.", LEFT),
    line("14", "narrator", "Since: one station.", 0.2),
    line("15", "narrator", "Now: no coupon.", 0.2),
    line("16", "narrator", "Still: the hole.", 1.2),
)


def spoken(take) -> float:
    """The second of ``take`` its words end: what is left of it is its hold."""
    return round(take.speech_duration, 3)


def desk(*extra: Prop, arm: Arm | None = None, gloom_lean=(), seven_lean=()) -> dict:
    """The three at the desk, the basket in Seven's hands, and what else is on."""
    return dict(
        cast=(
            Place("droid", DROID, behind=True),
            Place("seven", SEVEN, y=1215, scale=0.9, lean=seven_lean),
            Place("gloom", GLOOM, arm=arm, lean=gloom_lean),
        ),
        props=(Prop("basket", *BASKET), *extra),
    )


def stages(takes) -> dict[str, Stage]:
    t = {x.id: x for x in takes}
    bay = partial(Stage, "returns")

    s = spoken(t["11"])
    raised = Arm(((s, 0.0, 1.0), (s + UP, 166.0, 1.1), (s + UP + HOLD, 166.0, 1.1), (s + UP + HOLD + DOWN, 0.0, 1.0)))
    dark = ((s + 0.1, s + UP + HOLD + DOWN),)

    c = spoken(t["13"])
    out, edge, drop, gone = c + PRINT, c + PRINT + SKATE, c + PRINT + SKATE + FALL, c + PRINT + SKATE + FALL + THROUGH
    hole = hole_of(BASKET)
    slot = (755.0, DESK_TOP - 8.0)
    coupon = Prop(
        "coupon",
        *slot,
        {
            "track": (
                (c, *slot, 0.3),
                (out, slot[0], slot[1] - 8, 1.0),
                (edge, DESK_EDGE, DESK_TOP - 12, 1.0),
                (drop, *hole, 0.9),
                (gone, *hole, 0.0),
            )
        },
    )
    down = gone + TINKS[-1] + 0.15
    looks = ((down - 0.5, 0.0), (down, 4.0))
    nods = ((down - 0.5, 0.0), (down, 2.5))  # the basket stays in his hands
    return {
        "01": bay(**desk(), move=Move("push", 0, 1.06, 600, LENS, until=t["01"].duration)),
        "02": bay(**desk()),
        "03": bay(**desk()),
        "04": bay(**desk(), move=Move("crash", 0.05, 1.1, 600, LENS)),
        "05": bay(**desk()),
        "06": bay(**desk()),
        "07": bay(**desk()),
        "08": bay(**desk(), move=Move("crash", 0.05, 1.12, 600, LENS)),
        "09": bay(**desk()),
        "10": bay(**desk(), move=Move("crash", 0.05, 1.12, 600, LENS)),
        "11": bay(**desk(Prop("dim", 540, 960, {"spans": dark}), arm=raised)),
        "12": bay(**desk()),
        "13": bay(**desk(coupon, gloom_lean=looks, seven_lean=nods), move=Move("crash", edge, 1.15, 600, LENS)),
        "14": Stage(entry=Entry(TITLE, "", fade=True)),
        "15": Stage(entry=Entry(TITLE, "", fade=True, rise=False)),
        "16": Stage(entry=Entry(TITLE, "", fade=True, rise=False)),
    }


TINK = foley.Burst(0.16, 200.0, attack=0.001, decay=0.3, tone_hz=5200.0, tone_end_hz=5200.0, tone=1.0)


def sounds(takes, root) -> list[tuple[str, str, dict]]:
    """The room's rumble under the raised hand, the printer, and three tinks a long way down."""
    t = {x.id: x for x in takes}
    s = t["11"].start + spoken(t["11"])
    c = t["13"].start + spoken(t["13"])
    gone = c + PRINT + SKATE + FALL + THROUGH
    beds = (
        ("rumble", (s + 0.1,), foley.RUMBLE, "-6"),
        ("printer", tuple(c + 0.05 + k * 0.11 for k in range(4)), foley.REMOTE_CLICK, "-10"),
        ("skate", (c + PRINT, c + PRINT + 0.3), foley.SCRAPE, "-16"),
        ("tink-1", (gone + TINKS[0],), TINK, "-8"),
        ("tink-2", (gone + TINKS[1],), TINK, "-16"),
        ("tink-3", (gone + TINKS[2],), TINK, "-24"),
    )
    (root / "audio").mkdir(exist_ok=True)
    made = []
    for name, times, burst, gain in beds:
        path = f"audio/foley-{name}.wav"
        foley.write_bursts(root / path, times, takes[-1].end, burst, seed=SEED)
        made.append((f"foley-{name}", path, dict(role="effects", gain=gain)))
    return made


class Reel(_saga.Reel):
    series = dataclasses.replace(_saga.SERIES, seed=SEED)


REEL = Reel(
    slug="store-credit",
    number="S20",
    title="Store Credit — Saga 20",
    description="Portrait space-opera parody: the dark lord queues at the returns desk with what is left of his "
    "battle station. The droid offers an exchange, same model, or store credit.",
    accessible="A dark lord stands at a returns desk, an enforcer behind him with a basket of wreckage. He raises a "
    "hand and the room darkens, and nothing happens to the droid. Its coupon slides off the desk through a hole.",
    takes=TAKES,
    hook="RETURNS DESK: NOW SERVING 1",
    stages=stages,
    bleed=True,
    bed=False,
    loudness="-14",
    foley=sounds,
)

if __name__ == "__main__":
    sys.exit(record(REEL))
