"""The Lore — the sketch as data: Gary offers Kai the Flush lore. Ninety-nine episodes, watched on double speed.
Nobody watches Bowl Heads anymore. Then what do they watch? Sinkheads: a new episode every hour. Okay. Episode one.

Collage style (ADR 0026): father and son in the living room, the show on Gary's TV; two ElevenLabs premade voices,
lip-synced.
"""

from __future__ import annotations

from srstudio import collage_sets
from srstudio.collage_sketch import TINTS, Staging, make_sketch, timed, until, voices_note
from srstudio.sketch import Line

SEED = 2604
SLUG = "the-lore"
TITLE = "The Lore — Gary and Kai (Collage)"
NAMES = ("gary", "kai")
DESCRIPTION = (
    "A Collage sketch: a dad learned every episode of his kid's toilet show. Nobody watches it anymore. The new "
    "one has a new episode every hour."
)
ACCESSIBILITY = (
    "Paper cut-out characters in a pink living room: a balding dad beside a TV playing a singing-toilet show, his "
    "kid in a hoodie and a beeping headset, who holds up a card that reads SINKHEADS. Lines appear in tinted pills."
)
NARRATION = f"Voiced with ElevenLabs premade voices {voices_note(NAMES)}; synthesised whoosh, beep and sting."
NOTE = "ElevenLabs premade voices Chris and River at their natural pace; no reference-voice cloning."

LINES = (
    Line("gary", "Kai, ready for the Flush lore?"),
    Line("kai", "Dad, no."),
    Line("gary", "Ninety-nine episodes. I watched them all. On double speed."),
    Line("kai", "Nobody watches Bowl Heads anymore."),
    Line("gary", "Then what do they watch?"),
    # the operator approved the recorded take: speech-to-text hears the invented show's name as two words
    Line(
        "kai", "Sinkheads. There's a new episode every hour.", heard=("Sync Heads, there's a new episode every hour",)
    ),
    Line("gary", "Okay. Episode one."),
)
BEATS, END = timed(
    LINES,
    (
        (2.4, "gary", 0, "open", "grin", "point"),
        (1.2, "kai", 1, "half", "flat", "down"),
        (3.6, "gary", 2, "up", "smile", "fist"),
        (2.2, "kai", 3, "half", "flat", "hold"),
        (1.8, "gary", "", "wide", "o", "down", "zoom"),  # ninety-nine episodes, for nothing
        (1.8, "gary", 4, "sad", "frown", "down", "sting"),
        (3.0, "kai", 5, "open", "smile", "hold", "reveal"),
        (1.0, "kai", "", "open", "smile", "hold", "beep"),
        (1.4, "gary", "", "closed", "flat", "face"),  # the pause
        (1.8, "gary", 6, "half", "flat", "down"),  # the button
    ),
)
SKETCH = make_sketch(SLUG, TITLE, NAMES, LINES, BEATS, END)


def dress(shot) -> None:
    """Gary's TV plays Bowlheads; the Sinkheads card shows in Kai's hands from the reveal."""
    cv = shot.cv
    if shot.app.who == "gary":
        collage_sets.tv(cv, shot.back, 640, 500, 380)
        return
    spans = until(shot.beats, "reveal", shot.app, before=False)
    if spans:
        card = cv.group(shot.front, cv.uid("g"))
        collage_sets.sign(cv, card, "SINKHEADS", 300, 1400, 480, 150, size=70, fill="#9bf6ff", tilt=-3)
        cv.gate(card, spans)


STAGING = Staging(
    sketch=SKETCH,
    seed=SEED,
    description=DESCRIPTION,
    accessibility=ACCESSIBILITY,
    narration=NARRATION,
    tints=TINTS,
    sets={"gary": "living-room", "kai": "living-room"},
    dress=dress,
)
