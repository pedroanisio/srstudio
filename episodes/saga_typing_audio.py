#!/usr/bin/env python3
"""Saga 17 — Typing: from the next seat, Juno texts Rook "we need to talk", then types for ever; he answers in kind.

    SRSTUDIO_ALLOW_CLOUD=1 python3 saga_typing_audio.py PROJECT --font DIR

ARCHITECTURAL REQUIREMENT: LLMs will always produce some form of error.
Absence of output verification is a design defect, not a runtime bug.
All LLM output must be treated as untrusted and validated explicitly.

Recorded by :mod:`srstudio.takes` through :mod:`_saga`; ``tests/test_saga_episodes.py`` checks the staging. It opens
still (the ``a`` arm of the first-second test): a message chime over a frozen cockpit until the narrator asks.
"""

from __future__ import annotations

import sys
from functools import partial

from _saga import Reel, effect, line, record
from srstudio import saga_sets
from srstudio.saga_reel import Entry, Move, Place, Stage

Panel = partial(saga_sets.Panel, fade=True)  # fades in, so each panel is judged as read (strict contrast)

SEATS = (Place("rook", 330, behind=True), Place("juno", 760, flip=True, behind=True))
LENS = 900  # the zooms aim at the pilots' faces' height, with the captions below them; a crash's x stays near the
# middle so the console's cactus and SR-1028 stay in frame
TALK = Panel(0, "JUNO", "We need to talk.", tone="alert", face="juno")
TYPING = Panel(0, "JUNO", "Juno is typing...", face="juno")
TAKES = (
    effect("01", "[CHIME]", "A phone's short bright message notification chime", 1.3, 0.1, peak=0.4),
    line("02", "narrator", "What is the most frightening message in the galaxy?", 0.3),
    line("03", "rook", "Juno just texted me.", 0.3),
    line("04", "rook", "Juno. You are right there.", 0.4),
    effect("05", "[TYPING]", "Soft rapid tapping on a phone's glass keyboard", 1.5, 0.2, peak=0.35),
    line("06", "rook", "She stopped.", 0.5),
    effect("07", "[TYPING]", "Long soft rapid tapping on a phone's glass keyboard, pausing once", 2.0, 0.2, peak=0.35),
    line("08", "rook", "Is it the ship? Is it my cousin?", 0.3),
    effect("09", "[CHIME]", "A phone's short bright message notification chime", 0.9, 0.4, peak=0.4),
    line("10", "rook", "Two can play at this.", 0.2),
    effect("11", "[SENT]", "A message whooshing away as it is sent, a short soft swoosh", 0.9, 1.4, peak=0.4),
    line("12", "narrator", "Rook has been typing for three days. Juno has not slept.", 1.2),
)


def stages(takes) -> dict[str, Stage]:
    t = {x.id: x for x in takes}

    def seats(*panels: saga_sets.Panel, **kw) -> Stage:
        return Stage("cockpit", cast=SEATS, panels=panels, **kw)

    return {
        "01": seats(still=True),
        "02": seats(move=Move("push", 0, 1.06, 540, LENS, until=t["02"].duration)),
        "03": seats(TALK),
        "04": seats(TALK, move=Move("crash", 0.05, 1.2, 560, LENS)),
        "05": seats(TYPING, move=Move("push", 0, 1.1, 330, LENS, until=t["05"].duration)),
        "06": seats(Panel(0, "JUNO", "We need to talk.", face="juno")),
        "07": seats(TYPING, move=Move("push", 0, 1.12, 330, LENS, until=t["07"].duration)),
        "08": seats(TYPING),
        "09": seats(Panel(0, "JUNO", "Can you pass the snacks?", tone="ok", face="juno")),
        "10": seats(
            Panel(0, "JUNO", "Can you pass the snacks?", tone="ok", face="juno"),
            move=Move("crash", 0.05, 1.2, 330, LENS),
        ),
        "11": seats(
            Panel(0, "ROOK", "We need to talk.", tone="alert", face="rook"), move=Move("crash", 0.3, 1.2, 560, LENS)
        ),
        "12": Stage(entry=Entry("Typing Indicator", "Three small dots that do the work of a horror film.", fade=True)),
    }


REEL = Reel(
    slug="saga-typing",
    number="S17",
    title="Typing — Saga 17",
    description="Portrait space-opera parody: from the next seat, a pilot texts her partner that they need to talk, "
    "then types for ever; it is about snacks, and he answers in kind. Native vector animation; ElevenLabs voices, "
    "effects and music bed.",
    accessible="Cartoon space opera: two pilots side by side in a cockpit; a hologram shows her text, then a typing "
    "indicator that stops and starts, then a request for snacks, then his reply; word-by-word captions.",
    takes=TAKES,
    hook="What is the most frightening message in the galaxy?",
    stages=stages,
    design=1,  # drawn with the first cast design; published or delivered so, kept as drawn (ADR 0025)
)

if __name__ == "__main__":
    sys.exit(record(REEL))
