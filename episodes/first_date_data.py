"""First Date — the sketch as data: Deb asks her date what he does. Jun makes a kids' show; she won't let her son
watch that stuff. It's Bowl Heads, the toilet thing: thirty billion views. Her son calls. She wants one autograph,
then she's leaving. Flush flush? Yeah.

Collage style (ADR 0026): Deb and Jun in a café, Kai at home in front of the show; three ElevenLabs premade
voices, lip-synced.
"""

from __future__ import annotations

from _collage_sketch import TINTS, Staging, make_sketch, timed, voices_note
from srstudio import collage_sets
from srstudio.sketch import Line

SEED = 2603
SLUG = "first-date"
TITLE = "First Date — Deb, Jun and Kai (Collage)"
NAMES = ("deb", "jun", "kai")
DESCRIPTION = (
    "A Collage sketch: a first date. She won't let her son watch the toilet show. Her date makes the toilet show."
)
ACCESSIBILITY = (
    "Paper cut-out characters: a woman and a man in a beanie on a date in a brick café; a kid in a hoodie and a "
    "headset at home in front of a TV playing a show about a singing toilet. Lines appear in tinted pills."
)
NARRATION = f"Voiced with ElevenLabs premade voices {voices_note(NAMES)}; synthesised whoosh, beep and sting."
NOTE = "ElevenLabs premade voices Jessica, Will and River at their natural pace; no reference-voice cloning."

LINES = (
    Line("deb", "So, Jun. What do you do?"),
    Line("jun", "I make a kids' show. You've probably seen it."),
    Line("deb", "I don't let my son watch that stuff."),
    Line("jun", "It's called Bowl Heads."),
    Line("deb", "The toilet thing?"),
    Line("jun", "Thirty billion views. It's the toilet thing."),
    Line("kai", "Mom! Get his autograph!"),
    Line("deb", "One autograph. Then I'm leaving."),
    Line("jun", "Flush flush?"),
    Line("deb", "Yeah."),
)
BEATS, END = timed(
    LINES,
    (
        (2.0, "deb", 0, "open", "smile", "hold"),
        (2.8, "jun", 1, "half", "smug", "shrug"),
        (2.4, "deb", 2, "half", "smug", "down"),
        (1.6, "jun", 3, "open", "smile", "point"),
        (1.4, "deb", "", "wide", "o", "down", "zoom"),  # it lands on her
        (1.2, "deb", 4, "wide", "frown", "down"),
        (2.8, "jun", 5, "half", "flat", "hold"),
        (1.8, "kai", 6, "wide", "grin", "fist", "beep"),
        (2.4, "deb", 7, "half", "flat", "face"),
        (1.4, "jun", 8, "side", "smug", "point"),
        (1.2, "deb", "", "half", "flat", "down"),  # the pause
        (1.4, "deb", 9, "closed", "smile", "fist", "sting"),  # the button
    ),
)
SKETCH = make_sketch(SLUG, TITLE, NAMES, LINES, BEATS, END)


def dress(shot) -> None:
    """Kai's TV plays the show his mother's date makes."""
    if shot.app.who == "kai":
        collage_sets.tv(shot.cv, shot.back, 640, 500, 380)


STAGING = Staging(
    sketch=SKETCH,
    seed=SEED,
    description=DESCRIPTION,
    accessibility=ACCESSIBILITY,
    narration=NARRATION,
    tints=TINTS,
    sets={"deb": "cafe", "jun": "cafe", "kai": "living-room"},
    dress=dress,
)
