#!/usr/bin/env python3
"""Saga 19 — Dental Plan: however far you go, your family will ask why you can't be more like the relative with
benefits. The chosen one's grandmother has filled in the form.

    SRSTUDIO_ALLOW_CLOUD=1 python3 dental_plan_audio.py PROJECT --font DIR

ARCHITECTURAL REQUIREMENT: LLMs will always produce some form of error.
Absence of output verification is a design defect, not a runtime bug.
All LLM output must be treated as untrusted and validated explicitly.

Recorded by :mod:`srstudio.takes` through :mod:`_saga`, with no music bed; the staging is checked by
:func:`srstudio.saga_reel.check` before anything is drawn. The ration bar is planted in the first shot, breaks a
tooth on the turn, and the foley is synthesized at build from the recorded takes.
"""

from __future__ import annotations

import dataclasses
import sys
from functools import partial

import _saga
from _saga import line, record, word_at
from srstudio import foley, saga_everyday
from srstudio.saga import Arm
from srstudio.saga_reel import Entry, Move, Place, Prop, Stage

CHEW = 2.6  # how long the opening bite lasts, seconds
HOLD = 1.5  # Juno's open mouth, nothing coming out
BITE, DROP, WAIT, SLIDE, TAKE = 0.62, 0.4, 2.0, 1.0, 0.9  # the turn, after "But he calls."
TURN = BITE + DROP + WAIT + SLIDE + TAKE + 0.3
PLATE = (802, 1098)
CUP = (668, 1112)
MABEL, JUNO = 300, 780
MOUTH = (JUNO + 8, 850)
LENS = 880
SEED = 3314
TITLE = "The Chosen One"

TAKES = (
    line("01", "narrator", "What does a family want from the chosen one?", 0.2),
    line("02", "mabel", "Why can't you be more like your father?", 0.25),
    line("03", "juno", "He destroyed our planet.", 0.2),
    line("04", "mabel", "He has a dental plan.", 0.25),
    line("05", "juno", "He's evil, Grandma.", 0.2),
    line("06", "mabel", "With a pension.", 0.25),
    line("07", "juno", "I'm saving the galaxy!", 0.2),
    line("08", "mabel", "Does the galaxy match your contributions?", HOLD),
    line("09", "juno", "It's great exposure.", 0.2),
    line("10", "mabel", "He calls on Sundays.", 0.2),
    line("11", "juno", "To threaten you!", 0.2),
    line("12", "mabel", "But he calls.", TURN),
    line("13", "narrator", "Since: one tooth.", 0.2),
    line("14", "narrator", "Now: one form.", 0.2),
    line("15", "narrator", "Still: no dental.", 1.2),
)

BAR_UP = (115.0, 0.7)  # the bar held up beside her, between bites
BAR_BITE = (234.0, 0.35)  # the end of the bar at her mouth


def spoken(take) -> float:
    """The second of ``take`` its words end: what is left of it is its hold."""
    return round(take.speech_duration, 3)


def held(hand=None) -> Arm:
    """Juno, arguing with the bar in her hand."""
    return Arm(((0.0, *BAR_UP),), holds=hand or saga_everyday.ration_bar)


def table(*extra: Prop, on: float | None = 0.0, pour: tuple[float, float] | None = None) -> tuple[Prop, ...]:
    """What is on the table and the shelf: the hologram on from second ``on``, None for not yet."""
    return (
        Prop("benefits", 340, 522, {"since": on}),
        Prop("plate", *PLATE),
        Prop("cup", *CUP, {"pour": pour} if pour else {"steam": 0.0}),
        *extra,
    )


def two(arm: Arm | None = None, *, mabel_arm: Arm | None = None, mouth=(), lean=()) -> tuple[Place, Place]:
    return (
        Place("mabel", MABEL, behind=True, arm=mabel_arm),
        Place("juno", JUNO, flip=True, behind=True, arm=arm or held(), mouth=mouth, lean=lean),
    )


def stages(takes) -> dict[str, Stage]:
    t = {x.id: x for x in takes}
    hut = partial(Stage, "hut")

    # the opening bite: she is at it before the narrator has finished his first word
    n = t["01"].duration
    up, grind, down = 0.12, 0.48, min(CHEW, n - 0.3)
    biting = Arm(
        ((0.0, *BAR_UP), (up, 150.0, 0.55), (grind, *BAR_BITE), (0.8, 238.0, 0.35), (1.1, 230.0, 0.35),
         (1.4, 238.0, 0.35), (down - 0.4, *BAR_BITE), (down, *BAR_UP)),
        holds=saga_everyday.ration_bar,
    )  # fmt: skip
    pour = Arm(((0.0, 62.0, 0.7), (n, 58.0, 0.7)), holds=partial(saga_everyday.teapot, turn=84.0))
    wince = Prop("wince", MOUTH[0] - 164, MOUTH[1] - 30, {"spans": ((grind + 0.1, down - 0.3),)})

    # the turn, on the clock of "But he calls."
    s = spoken(t["12"])
    bite = s + 0.1
    crack = s + BITE
    land = crack + DROP
    look = land + WAIT
    slid = look + SLIDE
    taken = slid + 0.45

    def bar_hand(cv, hand):
        saga_everyday.ration_bar(cv, hand, until=land + 0.4)

    def pen_hand(cv, hand):
        saga_everyday.pen(cv, hand, since=taken)
        bar_hand(cv, hand)

    juno_turn = Arm(
        ((0.0, *BAR_UP), (bite, *BAR_UP), (crack - 0.12, *BAR_BITE), (crack + 0.2, *BAR_BITE), (land + 0.4, 333.0, 1.1),
         (slid, 345.0, 1.0), (taken, 395.0, 1.1), (taken + 0.45, 430.0, 0.72)),
        holds=pen_hand,
    )  # fmt: skip
    mabel_turn = Arm(
        ((0.0, 7.0, 1.0), (look - 0.35, 7.0, 1.0), (look, 14.0, 1.0), (slid, 28.0, 1.1), (slid + 0.3, 14.0, 1.0))
    )
    turn = (
        Place("mabel", MABEL, behind=True, arm=mabel_turn),
        Place("juno", JUNO, flip=True, behind=True, arm=juno_turn, lean=((land, 0.0), (land + 0.3, 4.0))),
    )
    props = table(
        Prop("ration-bar", PLATE[0] + 2, PLATE[1] - 14, {"since": land + 0.4}),
        Prop("tooth", PLATE[0] - 24, PLATE[1] - 8, {"start": MOUTH, "falls": (crack + 0.04, land)}),
        Prop("wince", MOUTH[0] - 164, MOUTH[1] - 30, {"spans": ((crack, crack + 1.0),)}),
        Prop("form", 380, 1106, {"since": look - 0.1, "slide": ((look, 380), (slid, 490)), "pen_until": taken}),
    )

    dental = word_at(t["04"], "dental")
    nothing = spoken(t["08"])
    return {
        "01": hut(
            cast=(
                Place("juno", JUNO, flip=True, behind=True, arm=biting),
                Place("mabel", MABEL, behind=True, arm=pour),
            ),
            props=table(wince, on=None, pour=(0.1, n - 0.4)),
            move=Move("push", 0, 1.06, 540, LENS, until=n),
        ),
        "02": hut(cast=two(), props=table(on=None)),
        "03": hut(cast=two(), props=table(on=None)),
        "04": hut(cast=two(), props=table(on=dental), move=Move("crash", dental, 1.12, MABEL + 60, LENS)),
        "05": hut(cast=two(), props=table()),
        "06": hut(cast=two(), props=table(), move=Move("crash", 0.05, 1.15, MABEL + 60, LENS)),
        "07": hut(cast=two(), props=table()),
        "08": hut(
            cast=two(mouth=((nothing + 0.1, "open"), (t["08"].duration - 0.1, "closed"))),
            props=table(),
            move=Move("push", nothing, 1.14, 560, LENS, until=t["08"].duration),
        ),
        "09": hut(cast=two(), props=table()),
        "10": hut(cast=two(), props=table()),
        "11": hut(cast=two(), props=table()),
        "12": hut(cast=turn, props=props, move=Move("crash", land, 1.16, 440, LENS), shake=((crack, crack + 0.16),)),
        "13": Stage(entry=Entry(TITLE, "", fade=True)),
        "14": Stage(entry=Entry(TITLE, "", fade=True, rise=False)),
        "15": Stage(entry=Entry(TITLE, "", fade=True, rise=False)),
    }


CRACK = foley.Burst(0.09, 7000.0, attack=0.001, decay=0.2, tone_hz=1500.0, tone_end_hz=700.0, tone=0.5)
PING = foley.Burst(0.5, 200.0, attack=0.001, decay=0.3, tone_hz=3400.0, tone_end_hz=3400.0, tone=1.0)


def sounds(takes, root) -> list[tuple[str, str, dict]]:
    """The bite on the opening, the crack, the tooth on the plate, the form on the table."""
    t = {x.id: x for x in takes}
    s = t["12"].start + spoken(t["12"])
    crack, land = s + BITE, s + BITE + DROP
    look = land + WAIT
    beds = (
        ("crunch", (t["01"].start + 0.5, t["01"].start + 1.1), foley.KNOCK, "-10"),
        ("crack", (crack,), CRACK, "-3"),
        ("ping", (land, land + 0.15), PING, "-9"),
        ("slide", (look, look + 0.35, look + 0.7), foley.SCRAPE, "-12"),
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
    slug="dental-plan",
    number="S19",
    title="Dental Plan — Saga 19",
    description="Portrait space-opera parody: the chosen one's grandmother wants to know why she can't be more like "
    "her father, the man who destroyed the planet. He has a dental plan.",
    accessible="An old woman pours tea at a table in a desert hut while a young rebel chews a hard ration bar, "
    "wincing. They argue. The rebel bites down, a tooth falls on the plate, and the grandmother slides over a "
    "filled-in form.",
    takes=TAKES,
    hook="THE CHOSEN ONE, 26",
    stages=stages,
    bleed=True,
    bed=False,
    loudness="-14",
    foley=sounds,
)

if __name__ == "__main__":
    sys.exit(record(REEL))
