#!/usr/bin/env python3
"""Saga 16 — Travel Notice: Lord Gloom's card is frozen for buying a coffee away from home, and the bar takes cash
or dishes.

    SRSTUDIO_ALLOW_CLOUD=1 python3 saga_travel_notice_audio.py PROJECT --font DIR

ARCHITECTURAL REQUIREMENT: LLMs will always produce some form of error.
Absence of output verification is a design defect, not a runtime bug.
All LLM output must be treated as untrusted and validated explicitly.

Recorded by :mod:`srstudio.takes` through :mod:`_saga`; ``tests/test_saga_episodes.py`` checks the staging. It opens
moving (the ``b`` arm of the first-second test): the camera pushes in on the bar as the narrator asks.
"""

from __future__ import annotations

import sys
from functools import partial

from _saga import Reel, effect, line, record, word_at
from srstudio import saga_sets
from srstudio.saga_reel import Entry, Move, Place, Stage

Panel = partial(saga_sets.Panel, fade=True)  # fades in, so each panel is judged as read (strict contrast)

BAR = (Place("gloom", 330), Place("droid", 720, behind=True))
LENS = 900  # moves aim above the floor line so the shelf's signature cactus stays in frame
SINK = (Place("gloom", 400, behind=True), Place("droid", 760, behind=True))  # both behind the counter now
SHELF = (90, 340, 820, 210)  # the hologram hangs below the shelf, so it never covers the cactus and SR-1028 on it
ORDER = Panel(0, "ORDER", "One small coffee. Tap your card.", tone="gold")
DECLINED = Panel(0, "CARD DECLINED", "Please try again.", tone="alert")
FRAUD = Panel(0, "FRAUD ALERT", "A purchase on a desert planet. Was this you? Reply yes or no.", tone="alert")
ACCEPT = Panel(0, "WE ACCEPT", "Cash. Coins. Dishes.", tone="gold")
FROZEN = Panel(0, "THANK YOU", "Card frozen, for your safety.", tone="info")
TAKES = (
    line("01", "narrator", "Can the most feared man in the galaxy buy a coffee?", 0.3),
    line("02", "droid", "One small coffee. Tap your card when ready.", 0.3),
    effect("03", "[DECLINED]", "A card reader's harsh double error beep", 0.8, 0.3, peak=0.4),
    line("04", "gloom", "Again.", 0.4),
    effect("05", "[BUZZ]", "A phone vibrating twice on a hard wooden counter", 1.0, 0.2, peak=0.4),
    line("06", "gloom", "Yes. I am on a trip.", 0.3),
    effect("07", "[BUZZ]", "A phone vibrating once on a hard wooden counter", 0.9, 0.3, peak=0.4),
    line("08", "gloom", "Frozen?", 0.4),
    line("09", "droid", "We also take cash.", 0.3),
    line("10", "gloom", "I have an empire.", 0.3),
    line("11", "droid", "Then the sink is round the back.", 0.3),
    effect("12", "[DISHES]", "Plates and cups clattering in a sink, water splashing", 1.6, 1.4, peak=0.45),
    line("13", "narrator", "Lord Gloom now tells his bank before every trip. They freeze the card anyway.", 1.2),
)


def stages(takes) -> dict[str, Stage]:
    t = {x.id: x for x in takes}

    def bar(*panels: saga_sets.Panel, **kw) -> Stage:
        return Stage("cantina", cast=BAR, panels=panels, box=SHELF, **kw)

    tap = round(max(min(word_at(t["02"], "tap"), t["02"].duration - 0.9), 0.0), 3)
    return {
        "01": bar(move=Move("push", 0, 1.12, 400, LENS, until=t["01"].duration)),
        "02": bar(Panel(tap, ORDER.title, ORDER.body, tone="gold")),
        "03": bar(DECLINED, move=Move("crash", 0.05, 1.2, 330, LENS)),
        "04": bar(DECLINED),
        "05": bar(FRAUD),
        "06": bar(FRAUD, move=Move("push", 0, 1.08, 330, LENS, until=t["06"].duration)),
        "07": bar(FROZEN),
        "08": bar(FROZEN, move=Move("crash", 0.05, 1.3, 330, LENS)),
        "09": bar(ACCEPT),
        "10": bar(ACCEPT, move=Move("crash", 0.05, 1.2, 330, LENS)),
        "11": bar(ACCEPT, options={"stare": ((0.0, t["11"].duration),)}),
        "12": Stage(
            "cantina",
            cast=SINK,
            panels=(Panel(0, "SHIFT ROTA", "Lord Gloom: dishes. Until the card thaws.", tone="ok"),),
            box=SHELF,
            move=Move("push", 0.1, 1.1, 400, LENS, until=t["12"].duration),
        ),
        "13": Stage(
            entry=Entry(
                "Travel Notice", "A form you file so your bank can freeze your card more confidently.", fade=True
            )
        ),
    }


REEL = Reel(
    slug="saga-travel-notice",
    number="S16",
    title="Travel Notice — Saga 16",
    description="Portrait space-opera parody: the dark lord's card is frozen for a coffee bought away from home, "
    "and the bar takes cash or dishes. Native vector animation; ElevenLabs voices, effects and music bed.",
    accessible="Cartoon space opera: a dark lord in a horned helmet at a bar counter with a service droid behind it; "
    "a hologram shows his card declined, a fraud alert and a frozen card, then the dark lord behind the bar on "
    "dishes; word-by-word captions.",
    takes=TAKES,
    hook="Can the most feared man in the galaxy buy a coffee?",
    stages=stages,
    design=1,  # drawn with the first cast design; published or delivered so, kept as drawn (ADR 0025)
)

if __name__ == "__main__":
    sys.exit(record(REEL))
