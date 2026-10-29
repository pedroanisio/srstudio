"""Intervention — the sketch as data: Deb and Kai stage an intervention for Gary, who has watched every episode of
BOWLHEADS twice. Kai is ten, and he stopped; he is into tax law now. Then his headset beeps: a new episode. Just the
intro.

Collage style (ADR 0026): the family in the living room; ElevenLabs premade voices, lip-synced.
"""

from __future__ import annotations

from srstudio import collage_sets
from srstudio.collage_sketch import TINTS, Staging, make_sketch, timed, until, voices_note
from srstudio.sketch import Line

SEED = 2612
SLUG = "intervention"
TITLE = "Intervention — Deb, Kai and Gary (Collage)"
NAMES = ("deb", "kai", "gary")
DESCRIPTION = (
    "A Collage sketch: the family stages an intervention for Dad, who watched every episode of a kids' toilet show "
    "twice. It goes well, until a new episode drops."
)
ACCESSIBILITY = (
    "Paper cut-out characters in a striped living room: a mom holding a card reading WE LOVE YOU GARY, a kid in a "
    "hoodie with a headset, and a balding dad. Lines appear in tinted pills."
)
NARRATION = f"Voiced with ElevenLabs premade voices {voices_note(NAMES)}; synthesised whoosh, beeps and sting."
NOTE = "ElevenLabs premade voices Jessica, River and Chris at their natural pace; no reference-voice cloning."

LINES = (
    Line("deb", "Gary, do you know why we're all here?"),
    Line("gary", "Is it my birthday?"),
    Line("deb", "It's an intervention."),
    Line("kai", "Dad. You watched every episode of Bowl Heads. Twice."),
    Line("gary", "There are only ninety-nine!"),
    Line("kai", "I'm ten, and I stopped."),
    Line("gary", "You stopped?"),
    Line("kai", "I'm into tax law now."),
    Line("deb", "Was that a new episode?"),
    Line("kai", "Just the intro."),
)
BEATS, END = timed(
    LINES,
    (
        (2.4, "deb", 0, "sad", "flat", "hold", "reveal"),
        (1.6, "gary", 1, "up", "grin", "shrug"),
        (1.8, "deb", 2, "sad", "frown", "hold"),
        (3.2, "kai", 3, "half", "flat", "point"),
        (2.0, "gary", 4, "wide", "o", "fist"),
        (2.0, "kai", 5, "half", "smug", "hold"),
        (1.4, "gary", 6, "wide", "o", "face"),
        (2.0, "kai", 7, "closed", "smug", "hold", "zoom"),
        (1.0, "kai", "", "wide", "o", "hold", "beep"),  # the headset: a new episode
        (1.8, "deb", "", "side", "flat", "hold"),  # the pause: nobody moves
        (1.8, "deb", 8, "side", "o", "face"),
        (2.4, "kai", 9, "side", "grin", "shrug", "sting"),  # the button: the relapse
    ),
)
SKETCH = make_sketch(SLUG, TITLE, NAMES, LINES, BEATS, END)


def dress(shot) -> None:
    """Deb's card, from her first line."""
    cv = shot.cv
    if shot.app.who != "deb":
        return
    spans = until(shot.beats, "reveal", shot.app, before=False)
    if spans:
        card = cv.group(shot.back, cv.uid("g"))
        collage_sets.sign(cv, card, "WE LOVE YOU GARY", 560, 540, 400, 120, size=46, fill="#ffe5ec", tilt=4)
        cv.gate(card, spans)


STAGING = Staging(
    sketch=SKETCH,
    seed=SEED,
    description=DESCRIPTION,
    accessibility=ACCESSIBILITY,
    narration=NARRATION,
    tints=TINTS,
    sets={"deb": "living-room", "kai": "living-room", "gary": "living-room"},
    dress=dress,
)
