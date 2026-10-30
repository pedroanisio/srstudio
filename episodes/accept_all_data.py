"""Accept All — the sketch as data: a website wants Gary's cookies. Kai: just click accept. No: Gary is managing his
preferences, all eight hundred partners, one at a time. Twenty minutes later, partner eight hundred: no. And the
article says: subscribe to read. "What were you even reading?" "How to save time online."

Collage style (ADR 0026), cast cards of ADR 0036: Kai wants to be left alone and answers in as few words as he can;
Gary, when ignored, makes a performance of it, here of saying no to each partner. Father and son in the living room,
each screen the website shows pinned up beside them as it comes; the reel opens moving (the sp-hook_motion test's arm
b): Gary comes in with his phone, already talking. ElevenLabs premade voices, lip-synced.
"""

from __future__ import annotations

from srstudio import collage_sets
from srstudio.collage_sketch import TINTS, ZOOM_SCALE, CastDrawer, Staging, make_sketch, solo, timed, voices_note
from srstudio.sketch import Line

SEED = 3917
SLUG = "accept-all"
TITLE = "Accept All — Gary and Kai (Collage)"
NAMES = ("gary", "kai")
SET = "living-room"
DESCRIPTION = (
    "A Collage sketch: instead of accepting the cookies, a dad turns down eight hundred advertising partners one by "
    "one. Then the article wants a subscription."
)
ACCESSIBILITY = (
    "Paper cut-out characters in a living room: a balding man in a green sweater hurries in and reads out each "
    "screen of a website, which appears as a paper card beside him: we value your privacy, manage 800 partners, "
    "partner 1 off, partner 800 off; then a red stamp across them reads SUBSCRIBE TO READ. His son, a kid in a hoodie "
    "and headset, answers in as few words as he can. Lines appear in tinted pills."
)
NARRATION = f"Voiced with ElevenLabs premade voices {voices_note(NAMES)}; synthesised whoosh and sting."
NOTE = "ElevenLabs premade voices Chris and River at their natural pace; no reference-voice cloning."
BITRATE = 5_800_000  # two passes: a master under 20 MB; the grain, new every frame, is what costs the bits

ENTER = (760.0, 0.7)  # the opening: Gary comes in from this far right, landing after this many seconds
SHIFT = {"gary": -60.0, "kai": 60.0}  # Gary near enough the shelf (left) for his zoom to keep it and his face
RED = "#c1121f"
CARD = dict(x=470, w=570, h=84)  # the website's screens, stacked on the right, under a two-line pill
ROWS = (545, 640, 735)
STAMP = dict(x=420, y=560, w=620, h=160)  # on the screen, not in the room: a zoom leaves it whole

LINES = (
    Line("gary", "Kai, this website wants my cookies."),
    Line("kai", "Just click accept."),
    Line("gary", "No. I'm managing my preferences."),
    Line("kai", "Dad, there are eight hundred partners."),
    Line("gary", "Partner one: no. Partner two: no."),
    Line("kai", "It's been twenty minutes."),
    Line("gary", "Partner eight hundred: no!"),
    Line("kai", "And now?"),
    Line("gary", "It says I need a subscription."),
    Line("kai", "What were you even reading?"),
    Line("gary", "How to save time online."),
)
BEATS, END = timed(
    LINES,
    (
        (2.0, "gary", 0, "wide", "o", "hold"),  # coming in, the phone up
        (1.2, "kai", 1, "half", "flat", "down"),
        (2.0, "gary", 2, "closed", "smug", "hold"),
        (2.0, "kai", 3, "half", "flat", "point"),
        (2.4, "gary", 4, "angry", "grin", "point"),  # one at a time
        (1.6, "kai", 5, "closed", "flat", "face"),
        (2.0, "gary", 6, "wide", "grin", "fist"),  # the last one: triumph
        (1.0, "kai", 7, "half", "flat", "down"),
        (1.2, "gary", "", "up", "flat", "hold", "zoom"),  # the pause: he reads the page
        (2.0, "gary", 8, "sad", "frown", "hold", "reveal"),  # SUBSCRIBE TO READ
        (1.8, "kai", 9, "half", "smug", "point"),
        (1.8, "gary", 10, "half", "smile", "shrug", "sting"),  # the button
        (0.0, "kai", "", "closed", "flat", "face"),  # Kai, after
    ),
    tail=1.4,
)
# the screens as Gary reads them out: (beat, text); a card stays once it has come up, the oldest dropping off the top
SCREENS = (
    (0, "WE VALUE YOUR PRIVACY"),
    (2, "MANAGE 800 PARTNERS"),
    (4, "PARTNER 1: OFF"),
    (5, "PARTNER 347: OFF"),
    (6, "PARTNER 800: OFF"),
)
SKETCH = make_sketch(SLUG, TITLE, NAMES, LINES, BEATS, END)


def casting(beats, end) -> CastDrawer:
    """Each character a little right of the shelf; Gary's first shot comes in from the right. Returns the pivot of a
    zoom on the face that keeps the living room's signature in frame."""

    def cast(cv, parent, app, mouths):
        dx = SHIFT[app.who]
        moved = cv.group(parent, cv.uid("g"), x=dx)
        if app.start == 0.0:
            cv.keys(moved, "x", [(0.0, dx + ENTER[0]), (ENTER[1], dx)], kind="cubic-out")
        fx, fy = solo(cv, moved, app, mouths)
        return collage_sets.zoom_pivot(SET, (fx + dx, fy), ZOOM_SCALE)

    return cast


def dress(shot) -> None:
    """The phone's screens beside them, the last three shown, each from the beat Gary reads it; SUBSCRIBE TO READ
    stamped across them from the reveal, on the screen, so the crash zoom leaves it whole."""
    cv, app = shot.cv, shot.app
    zoom = next(b.start for b in shot.beats if b.event == "zoom")
    starts = [shot.beats[i].start for i, _ in SCREENS] + [shot.end]
    for m in range(len(SCREENS)):  # from screen m coming up until the next: the last three, oldest on top
        # the crash zoom is on his face: the screens leave it, and come back behind the stamp in the next shot
        a, b = max(starts[m], app.start), min(starts[m + 1], app.end, zoom if app.start <= zoom else app.end)
        if a >= b:
            continue
        first = max(0, m - len(ROWS) + 1)
        for n in range(first, m + 1):
            card = cv.group(shot.back, cv.uid("g"))
            tilt = (-2, 1.5, -1)[n % 3]
            collage_sets.sign(cv, card, SCREENS[n][1], y=ROWS[n - first], **CARD, size=46, tilt=tilt)
            cv.gate(card, [(a, b)])
    reveal = next(b.start for b in shot.beats if b.event == "reveal")
    if reveal < app.end:
        stamp = cv.group(cv.comp, cv.uid("g"), start=max(reveal, app.start), end=app.end)
        collage_sets.sign(cv, stamp, "SUBSCRIBE TO READ", **STAMP, size=66, color=RED, tilt=-7)


STAGING = Staging(
    sketch=SKETCH,
    seed=SEED,
    description=DESCRIPTION,
    accessibility=ACCESSIBILITY,
    narration=NARRATION,
    tints=TINTS,
    sets={"gary": SET, "kai": SET},
    dress=dress,
    cast=casting,
    bitrate=BITRATE,
)
