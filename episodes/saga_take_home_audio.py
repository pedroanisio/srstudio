#!/usr/bin/env python3
"""Saga 14 — Take-Home: round six of a Directorate interview is an unpaid take-home task, design a battle station;
the rejection arrives, then the station, then the job advert for it.

    SRSTUDIO_ALLOW_CLOUD=1 python3 saga_take_home_audio.py PROJECT --font DIR

ARCHITECTURAL REQUIREMENT: LLMs will always produce some form of error.
Absence of output verification is a design defect, not a runtime bug.
All LLM output must be treated as untrusted and validated explicitly.

Recorded by :mod:`srstudio.takes` through :mod:`_saga`; ``tests/test_saga_episodes.py`` checks the staging. It opens
moving (the ``b`` arm of the first-second test): the camera pushes into the cockpit from the first frame.
"""

from __future__ import annotations

import sys
from functools import partial

from _saga import Reel, effect, line, record, word_at
from srstudio import saga_sets
from srstudio.saga_reel import Entry, Move, Place, Prop, Stage

Panel = partial(saga_sets.Panel, fade=True)  # fades in, so each panel is judged as read (strict contrast)

SEAT = (Place("juno", 540, behind=True),)
ROUND = Panel(0, "INTERVIEW · ROUND 6", "Directorate Careers", face="gloom")
TASK = Panel(0, "TAKE-HOME TASK", "Design a battle station. Unpaid. Due Monday.", tone="gold", face="gloom")
READ = 0.85  # s a panel stays up before the next replaces it: the engine's shortest readable text
STATION = Prop("cube", 540, 440, {"size": 240})  # out of the windshield, above the headrests
TAKES = (
    line("01", "narrator", "How hard is it to get hired by the Directorate?", 0.3),
    line("02", "gloom", "Welcome to round six.", 0.3),
    line("03", "juno", "There's a round six?", 0.3),
    line("04", "gloom", "Just a little homework.", 0.4),
    line("05", "juno", "A whole battle station?", 0.2),
    line("06", "gloom", "We just want to see how you think.", 0.3),
    effect("07", "[SENT]", "A message whooshing away as it is sent, a short soft swoosh", 0.9, 0.4, peak=0.4),
    line("08", "gloom", "Thank you! We went with another candidate.", 0.3),
    effect(
        "09", "[RUMBLE]", "A colossal space station passing overhead, a deep low engine rumble", 2.0, 0.1, peak=0.55
    ),  # fmt: skip
    line("10", "juno", "That's my battle station.", 0.4),
    line("11", "gloom", "And we're hiring! Ten years of experience required.", 1.4),
    line("12", "narrator", "The station opened on Tuesday. Juno is now in round seven.", 1.2),
)


def stages(takes) -> dict[str, Stage]:
    t = {x.id: x for x in takes}

    def seat(*panels: saga_sets.Panel, **kw) -> Stage:
        return Stage("cockpit", cast=SEAT, panels=panels, **kw)

    task = Panel(max(word_at(t["04"], "homework"), READ), TASK.title, TASK.body, tone="gold", face="gloom")
    sent = Panel(0.1, "SENT", "battle_station_FINAL_final2 · 400 pages", tone="ok")
    advert = "Station engineer. Ten years' experience with this station."
    hiring = Panel(max(word_at(t["11"], "ten"), READ), "NOW HIRING", advert, tone="gold", face="gloom")
    rumble = t["09"].duration
    return {
        "01": seat(move=Move("push", 0, 1.14, 540, 900, until=t["01"].duration)),
        "02": seat(ROUND),
        "03": seat(ROUND, move=Move("crash", 0.05, 1.2, 540, 820)),
        "04": seat(ROUND, task),
        "05": seat(TASK),
        "06": seat(TASK),
        "07": seat(sent),
        "08": seat(
            Panel(0, "APPLICATION STATUS", "Not selected. Keep an eye on our careers page!", tone="alert", face="gloom")
        ),  # fmt: skip
        "09": Stage(
            "space",
            props=(Prop("cube", 560, 760, {"size": 560}), Prop("freighter", 300, 1180, {"scale": 0.5})),
            shake=((0.0, rumble),),
        ),  # fmt: skip
        "10": seat(props=(STATION,), move=Move("crash", 0.05, 1.25, 540, 820)),
        "11": seat(
            Panel(0, "DIRECTORATE CAREERS", "One more thing!", face="gloom"),
            hiring,
            move=Move("push", 0, 1.1, 540, 820, until=t["11"].duration),
        ),
        "12": Stage(entry=Entry("Take-Home Task", "Unpaid work, returned with a rejection, then launched.", fade=True)),
    }


REEL = Reel(
    slug="saga-take-home",
    number="S14",
    title="Take-Home — Saga 14",
    description="Portrait space-opera parody: a job applicant's sixth interview round is an unpaid take-home task to "
    "design a battle station. Native vector animation; ElevenLabs voices, effects and music bed.",
    accessible="Cartoon space opera: a young hero in a freighter cockpit on a hologram video interview with a dark "
    "lord; a battle station later fills the windshield; word-by-word captions.",
    takes=TAKES,
    hook="How hard is it to get hired by the Directorate?",
    stages=stages,
    design=1,  # drawn with the first cast design; published or delivered so, kept as drawn (ADR 0025)
)

if __name__ == "__main__":
    sys.exit(record(REEL))
