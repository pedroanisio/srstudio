"""First sip: the sketch as data. Brent noses, swirls and gargles his way through a wine and finds plum, regret and wet
dog. Omar, who has not moved: this morning, sir. That's the water, I was topping you up. Send it back.

Collage (ADR 0026), ElevenLabs premade Brian (Brent), Jessica (Deb) and Daniel (Omar). It opens on a held frame (arm a
of ``sp-hook_motion``). :func:`dress` draws the table, the glass and the jug.
"""

from __future__ import annotations

from srstudio import collage, collage_everyday, collage_group, collage_odds, foley, signature
from srstudio.collage_group import Place
from srstudio.collage_sketch import TINTS, CastDrawer, Sound, Staging, make_sketch, solo, timed, voices_note
from srstudio.sketch import Appearance, Line, Mouths, events

SEED = 4127
RECORDING_SEED = 4123  # the takes were made on it; regards-dad had it first
SLUG = "first-sip"
TITLE = "First sip - Brent (Collage)"
NAMES = ("brent", "deb", "omar")
ROOM = "cafe"
STILL = 1.0  # the recording's silent head, the first shot
PUSH = 1.06  # that shot moves: the first second opens on movement, arm b
BITRATE = 5_800_000  # two passes: a master under 20 MB; the grain, new every frame, is what costs the bits
DESCRIPTION = "A man tastes the wine for a long time. It is not the wine."
ACCESSIBILITY = (
    "A paper cut-out man noses a glass with his eyes shut, swirls it, gargles and announces plum, regret and wet dog, "
    "while his date sips and agrees. What year? A waiter, unmoved: this morning, sir. He tilts a water jug: that's the "
    "water, I was topping you up. The man straightens his tie. Send it back."
)
NARRATION = f"Voiced with ElevenLabs premade voices {voices_note(NAMES)}; synthesised foley."
NOTE = "ElevenLabs premade voices Brian, Jessica and Daniel at their natural pace; no reference-voice cloning."
PLACES = {"brent": Place(290.0, 1920.0, 0.76), "deb": Place(800.0, 1920.0, 0.76)}
WATER = "#cfe4ec"
TABLE = 1560.0
SNIFF = foley.Burst(0.8, 3000.0, attack=0.3, decay=0.2)
GARGLE = foley.Burst(1.1, 900.0, attack=0.1, decay=0.2, tone_hz=210.0, tone_end_hz=240.0, tone=0.5, flutter_hz=19.0)
ICE = foley.Burst(0.2, 3600.0, attack=0.002, decay=0.5, tone_hz=1900.0, tone_end_hz=2300.0, tone=0.4)

LINES = (
    Line("brent", "Interesting."),
    Line("brent", "Bold. Stony. A little leather."),
    Line("brent", "There it is. Plum. Regret."),
    Line("deb", "Regret?"),
    Line("brent", "You get that?"),
    Line("deb", "I think so, yes."),
    Line("brent", "Some wet dog at the end. What year?"),
    Line("omar", "This morning, sir."),
    Line("omar", "That's the water. I was topping you up."),
    Line("brent", "Send it back."),
)
BEATS, END = timed(
    LINES,
    (
        (STILL, "omar", "", "half", "flat", "hold"),
        (1.5, "brent", 0, "closed", "smug", "hold", "reveal:sniff"),
        (3.0, "brent", 1, "closed", "smug", "hold"),
        (1.2, "brent", "", "closed", "o", "point", "reveal:gargle"),
        (2.4, "brent", 2, "closed", "smug", "point"),
        (0.9, "deb", 3, "side", "flat", "down"),
        (1.2, "brent", 4, "open", "smug", "hold"),
        (1.6, "deb", 5, "open", "smile", "hold"),
        (3.2, "brent", 6, "closed", "smug", "down"),
        (2.2, "omar", 7, "half", "flat", "hold"),
        (3.4, "omar", 8, "half", "flat", "hold", "reveal:jug"),
        (1.5, "brent", "", "side", "flat", "down", "zoom"),
        (0.0, "brent", 9, "half", "smug", "down", "sting"),
    ),
    tail=1.9,
)
SKETCH = make_sketch(SLUG, TITLE, NAMES, LINES, BEATS, END)


def moments(beats, name: str) -> list[float]:
    return [t for t, what in events(beats, "reveal") if what == name]


def casting(beats, end: float) -> CastDrawer:
    """The table for two; Omar is the only one alone in a shot, as he has been all evening."""
    lineup = collage_group.pair(PLACES, (STILL, end))

    def draw(cv, parent, app: Appearance, mouths: Mouths) -> collage.Point:
        return solo(cv, parent, app, mouths) if app.who == "omar" else lineup(cv, parent, app, mouths)

    return draw


def dress(shot) -> None:
    """Their table and glass; from its cue, the jug in Omar's hands."""
    cv, front, app, beats = shot.cv, shot.front, shot.app, shot.beats
    if app.who == "omar":
        jug = moments(beats, "jug")[0]
        if app.end > jug:  # in front of his chest, his two hands on it
            collage_odds.water_jug(cv, cv.group(front, cv.uid("g"), start=jug), 530.0, 1630.0, scale=0.9)
        return
    collage_everyday.tablecloth(cv, front, TABLE)
    collage_odds.wine_glass(cv, front, 440.0, 1790.0, full=0.45, colour=WATER, scale=0.72)
    collage_odds.wine_glass(cv, front, 640.0, 1790.0, full=0.45, colour=WATER, scale=0.72)
    if any(app.start <= at < app.end for at, _ in events(beats, "zoom")):  # the zoom loses the shelf's code
        signature.code(cv, front, 130.0, 1670.0, 10.0, color="#5a4a3a")


def sounds(beats, end: float) -> list[Sound]:
    """The long sniff, the gargle, the ice in the jug."""
    return [
        Sound("sniff", SNIFF, tuple(moments(beats, "sniff")), -14.0),
        Sound("gargle", GARGLE, tuple(moments(beats, "gargle")), -11.0),
        Sound("ice", ICE, tuple(moments(beats, "jug")), -8.0),
    ]


STAGING = Staging(
    sketch=SKETCH,
    seed=SEED,
    description=DESCRIPTION,
    accessibility=ACCESSIBILITY,
    narration=NARRATION,
    tints=TINTS,
    sets={"brent": ROOM, "deb": ROOM, "omar": ROOM},
    dress=dress,
    cast=casting,
    push=PUSH,
    recording_seed=RECORDING_SEED,
    bitrate=BITRATE,
    sounds=sounds,
)
