#!/usr/bin/env python3
"""Saga 15 — Call Juno: Elder Mabel asks her new smart speaker to call her granddaughter, and it calls Lord Gloom;
she mothers him anyway.

    SRSTUDIO_ALLOW_CLOUD=1 python3 saga_call_juno_audio.py PROJECT --font DIR

ARCHITECTURAL REQUIREMENT: LLMs will always produce some form of error.
Absence of output verification is a design defect, not a runtime bug.
All LLM output must be treated as untrusted and validated explicitly.

Recorded by :mod:`srstudio.takes` through :mod:`_saga`; ``tests/test_saga_episodes.py`` checks the staging. It opens
still (the ``a`` arm of the first-second test): the speaker's wake chime over a frozen desert until the narrator asks.
"""

from __future__ import annotations

import sys
from functools import partial

from _saga import Reel, effect, line, record, word_at
from srstudio import saga_sets
from srstudio.saga_reel import Entry, Move, Place, Stage
from srstudio.saga_sets import FLOOR

Panel = partial(saga_sets.Panel, fade=True)  # fades in, so each panel is judged as read (strict contrast)

HOME = (Place("mabel", 540),)
BRIDGE = (Place("gloom", 330), Place("seven", 700, flip=True))  # the other end of the call, with a witness
LISTENING = Panel(0, "SPEAKER", "Listening...", face="droid")
CALLING = Panel(0, "SPEAKER", "Calling Lord Gloom.", tone="gold", face="droid")
MOBILE = Panel(0, "SPEAKER", "Calling Lord Gloom. Mobile.", tone="alert", face="droid")
ANSWERED = Panel(0, "CALL CONNECTED", "Lord Gloom", face="gloom")
CALLER = Panel(0, "INCOMING CALL", "Unknown number. Desert.", tone="gold")
GRAN = Panel(0, "CALL CONNECTED", "Unknown number. Desert.", face="mabel")
TAKES = (
    effect("01", "[CHIME]", "A smart speaker's soft two-note wake chime in a quiet room", 1.3, 0.1, peak=0.4),
    line("02", "narrator", "What happens when Elder Mabel gets a smart speaker?", 0.3),
    line("03", "mabel", "Speaker. Call Juno.", 0.3),
    line("04", "droid", "Calling Lord Gloom.", 0.3),
    line("05", "mabel", "No, dear. Juno.", 0.3),
    line("06", "droid", "Calling Lord Gloom. Mobile.", 0.2),
    effect(
        "07", "[RINGING]", "A phone ringing twice through a small speaker, a classic ring tone", 1.6, 0.1, peak=0.4
    ),  # fmt: skip
    line("08", "gloom", "Who dares call this number?", 0.3),
    line("09", "mabel", "Oh, hello, dear. You sound tired.", 0.5),
    line("10", "gloom", "I am a little tired.", 0.4),
    line("11", "mabel", "Wear something warm, dear.", 0.4),
    line("12", "gloom", "I have a cape.", 1.4),
    line("13", "narrator", "They talk every Sunday now. Juno is still waiting for her call.", 1.2),
)


def stages(takes) -> dict[str, Stage]:
    t = {x.id: x for x in takes}

    def home(*panels: saga_sets.Panel, **kw) -> Stage:
        return Stage("desert", {"shade": True}, cast=HOME, panels=panels, **kw)  # dusk under the captions

    def bridge(*panels: saga_sets.Panel, **kw) -> Stage:
        return Stage("bridge", cast=BRIDGE, panels=panels, **kw)

    asked = round(max(min(word_at(t["03"], "call"), t["03"].duration - 0.9), 0.0), 3)
    return {
        "01": home(still=True),
        "02": home(move=Move("push", 0, 1.08, 540, FLOOR, until=t["02"].duration)),
        "03": home(Panel(asked, LISTENING.title, LISTENING.body, face="droid")),
        "04": home(CALLING),
        "05": home(CALLING, move=Move("crash", 0.05, 1.2, 540, FLOOR)),
        "06": home(MOBILE),
        "07": bridge(CALLER, move=Move("push", 0, 1.08, 330, FLOOR, until=t["07"].duration)),
        "08": bridge(GRAN, move=Move("crash", 0.05, 1.2, 600, FLOOR)),
        "09": home(ANSWERED),
        "10": bridge(GRAN, move=Move("push", 0, 1.08, 330, FLOOR, until=t["10"].duration)),
        "11": home(ANSWERED),
        "12": bridge(GRAN, move=Move("crash", 0.05, 1.2, 600, FLOOR)),
        "13": Stage(
            entry=Entry(
                "Smart Speaker",
                "Calls the wrong person with total confidence. Sometimes the right wrong person.",
                fade=True,
            )
        ),
    }


REEL = Reel(
    slug="saga-call-juno",
    number="S15",
    title="Call Juno — Saga 15",
    description="Portrait space-opera parody: an elder asks her new smart speaker to call her granddaughter and it "
    "calls the dark lord instead; she tells him to wear something warm. Native vector animation; ElevenLabs voices, "
    "effects and music bed.",
    accessible="Cartoon space opera: an elderly woman with glasses and a cane stands in a desert outside her hut; a "
    "hologram shows her smart speaker calling the wrong person, and a dark lord on his command bridge takes the call "
    "beside a white-armoured enforcer; word-by-word captions.",
    takes=TAKES,
    hook="What happens when Elder Mabel gets a smart speaker?",
    stages=stages,
    design=1,  # drawn with the first cast design; published or delivered so, kept as drawn (ADR 0025)
)

if __name__ == "__main__":
    sys.exit(record(REEL))
