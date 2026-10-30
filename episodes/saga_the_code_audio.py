#!/usr/bin/env python3
"""Saga 13 — The Code: Lord Gloom orders the planet destroyed, the weapon asks for the code it sent to his phone, and
his phone is on the planet.

    SRSTUDIO_ALLOW_CLOUD=1 python3 saga_the_code_audio.py PROJECT --font DIR

ARCHITECTURAL REQUIREMENT: LLMs will always produce some form of error.
Absence of output verification is a design defect, not a runtime bug.
All LLM output must be treated as untrusted and validated explicitly.

Recorded by :mod:`srstudio.takes` through :mod:`_saga`; ``tests/test_saga_episodes.py`` checks the staging. It opens
still (the ``a`` arm of the first-second test): a charging hum under a frozen bridge until the narrator asks.
"""

from __future__ import annotations

import sys
from functools import partial

from _saga import Reel, effect, line, record, word_at
from srstudio import saga_sets
from srstudio.saga_reel import Entry, Move, Place, Stage
from srstudio.saga_sets import FLOOR

Panel = partial(saga_sets.Panel, fade=True)  # fades in, so each panel is judged as read (strict contrast)

STAND = (Place("gloom", 330), Place("seven", 700, flip=True))  # Seven clear of the console's SR-1028
PLANET = (900, 820)  # the target in the bridge window; zooms pivot on the floor line, keeping the cast off the captions
VERIFY = Panel(0, "VERIFY IT'S YOU", "We sent a code to your phone.", tone="alert")
CALLING = Panel(0, "CALLING", "Lord Gloom's phone. Ringing...")
ANSWERED = Panel(0, "CALL CONNECTED", "Lord Gloom's phone", face="rook")
TAKES = (
    effect(
        "01", "[CHARGING HUM]", "A giant energy cannon charging up, a deep steady electrical hum", 1.3, 0.1, peak=0.45
    ),  # fmt: skip
    line("02", "narrator", "What can stop the deadliest weapon in the galaxy?", 0.3),
    line("03", "gloom", "Destroy the planet.", 0.5),
    line("04", "gloom", "Seven. My phone.", 0.3),
    line("05", "seven", "Your phone is on that planet, sir.", 0.7),
    line("06", "gloom", "Then call it.", 0.2),
    effect(
        "07", "[RINGING]", "A phone ringing twice through a small speaker, a classic ring tone", 1.6, 0.1, peak=0.4
    ),  # fmt: skip
    line("08", "rook", "Hello? Who is this?", 0.3),
    line("09", "gloom", "It's me. I need the code.", 0.4),
    line("10", "rook", "Sorry. It says never share this code with anyone.", 0.2),
    effect("11", "[CALL ENDED]", "Three short flat beeps of a phone call hanging up", 0.8, 1.3, peak=0.4),
    line("12", "narrator", "Lord Gloom has since reset his password. The new code went to his phone.", 1.2),
)


def stages(takes) -> dict[str, Stage]:
    t = {x.id: x for x in takes}

    def bridge(*panels: saga_sets.Panel, **kw) -> Stage:
        return Stage("bridge", cast=STAND, panels=panels, **kw)

    said = round(min(t["03"].words[-1]["end"] + 0.15, t["03"].duration - 0.9), 3)  # up long enough to read
    verify = Panel(said, VERIFY.title, VERIFY.body, tone="alert")
    never = Panel(word_at(t["10"], "never"), "YOUR CODE", "Never share this code with anyone.", tone="alert",
                  face="rook")  # fmt: skip
    return {
        "01": bridge(still=True),
        "02": bridge(move=Move("push", 0, 1.06, 540, FLOOR, until=t["02"].duration)),
        "03": bridge(verify),
        "04": bridge(VERIFY),
        "05": bridge(VERIFY, move=Move("crash", word_at(t["05"], "planet"), 1.3, PLANET[0], FLOOR)),
        "06": bridge(VERIFY),
        "07": bridge(CALLING, move=Move("push", 0, 1.08, 330, FLOOR, until=t["07"].duration)),
        "08": bridge(ANSWERED),
        "09": bridge(ANSWERED),
        "10": bridge(ANSWERED, never),
        "11": bridge(
            Panel(0, "CALL ENDED", "Code not shared. Your account is safe.", tone="ok"),
            move=Move("push", 0.2, 1.1, 330, FLOOR, until=t["11"].duration),
        ),
        "12": Stage(
            entry=Entry(
                "Two-Factor Sign-In", "A lock with two keys. One of them is always on another planet.", fade=True
            )
        ),
    }


REEL = Reel(
    slug="saga-the-code",
    number="S13",
    title="The Code — Saga 13",
    description="Portrait space-opera parody: the dark lord's superweapon wants the sign-in code it sent to his phone, "
    "and his phone is on the target planet. Native vector animation; ElevenLabs voices, effects and music bed.",
    accessible="Cartoon space opera: a dark lord in a horned helmet and a white-armoured enforcer on a command bridge "
    "with a planet in the window; a hologram asks for a sign-in code, then shows a call answered by a smuggler; "
    "word-by-word captions.",
    takes=TAKES,
    hook="What can stop the deadliest weapon in the galaxy?",
    stages=stages,
)

if __name__ == "__main__":
    sys.exit(record(REEL))
