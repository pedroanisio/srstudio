#!/usr/bin/env python3
"""Saga 03 — Group Chat: the dramatic reveal on the dunes was already in the family group chat, and in the
Directorate's, and Gary has replied.

    SRSTUDIO_ALLOW_CLOUD=1 python3 saga_group_chat_audio.py PROJECT --font DIR

ARCHITECTURAL REQUIREMENT: LLMs will always produce some form of error.
Absence of output verification is a design defect, not a runtime bug.
All LLM output must be treated as untrusted and validated explicitly.

Recorded by :mod:`srstudio.takes` through :mod:`_saga`; ``tests/test_saga_episodes.py`` checks the staging.
"""

from __future__ import annotations

import sys

from _saga import Reel, effect, line, record
from srstudio.saga_reel import Entry, Move, Place, Stage
from srstudio.saga_sets import Panel

DUEL = (Place("gloom", 290), Place("juno", 790, flip=True))
FAMILY = Panel(0, "FAMILY (3)", "Dad: I am your father. Surprise!", face="gloom")
EVERYONE = Panel(0, "THE WHOLE DIRECTORATE", "40,000 members. 40,000 likes.", tone="alert")
TAKES = (
    line("01", "narrator", "What is the worst way to find out who your father is?", 0.3),
    line("02", "gloom", "Juno. I am your father.", 0.9),
    line("03", "juno", "Yeah. I know.", 0.8),
    line("04", "gloom", "You know?", 0.3),
    line("05", "juno", "You posted it in the family group chat.", 0.3),
    line("06", "gloom", "That chat was private!", 0.3, mood="angry"),
    line("07", "juno", "Dad. You sent it to the whole Directorate.", 0.4),
    effect("08", "[PING]", "A single bright phone message notification ping", 0.8, 1.6, peak=0.45),
    line("09", "narrator", "Gary has since been moved to a smaller chat. It is a trash compactor.", 1.2),
)


def stages(takes) -> dict[str, Stage]:
    t = {x.id: x for x in takes}
    return {
        "01": Stage("desert", cast=DUEL),
        "02": Stage("desert", cast=DUEL, move=Move("push", 0, 1.15, 290, 900, until=t["02"].duration)),
        "03": Stage("desert", cast=DUEL),
        "04": Stage("desert", cast=DUEL, move=Move("crash", 0.05, 1.25, 290, 880)),
        "05": Stage("desert", cast=DUEL, panels=(FAMILY,)),
        "06": Stage("desert", cast=DUEL, panels=(FAMILY,)),
        "07": Stage("desert", cast=DUEL, panels=(EVERYONE,), move=Move("crash", 0.1, 1.25, 450, 480)),
        "08": Stage(
            "desert", cast=DUEL, panels=(Panel(0, "GARY", "Congrats on the baby!!", tone="gold", face="gary"),)
        ),
        "09": Stage(entry=Entry("Group chats", "Where empires keep their secrets. Briefly.")),
    }


REEL = Reel(
    slug="saga-group-chat",
    number="S3",
    title="Group Chat — Saga 03",
    description="Portrait space-opera parody: a dark lord's big reveal on the dunes was already in the family group "
    "chat, and the whole Directorate's. Native vector animation; ElevenLabs voices, effect and music bed.",
    accessible="Cartoon space opera: a dark lord and a young hero on a desert dune at sunset, a hologram group chat; "
    "word-by-word captions.",
    takes=TAKES,
    hook="What is the worst way to find out who your father is?",
    stages=stages,
)

if __name__ == "__main__":
    sys.exit(record(REEL))
