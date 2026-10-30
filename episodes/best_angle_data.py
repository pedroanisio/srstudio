"""Best Angle — the sketch as data: Rosa video-calls her son. Gary can only see her forehead. Then half her face.
Then a wall. "Perfect." She can see him fine: "Gary, why are you a toilet?" Cut to what she sees: his camera is
wearing the toilet show's face filter, and has been all along. "I'm a what?" "Leave it on. It's your best angle."

Collage style (ADR 0026), cast cards of ADR 0036: Rosa demands dignity and enjoys everyone's humiliation, and can't
resist a cutting line; Gary's toilet show finally gets him. Rosa's shots are her side of the video call (the call
buttons over a phone held wrong); Gary's shots are Gary at work, until the cut to her side shows him as she sees
him. The reel opens moving (the sp-hook_motion test's arm b): her forehead rises into the frame as the phone comes
up. ElevenLabs premade voices, lip-synced.
"""

from __future__ import annotations

from collections.abc import Sequence

from srstudio import collage, collage_sets
from srstudio.collage_sketch import TINTS, ZOOM_SCALE, CastDrawer, Staging, make_sketch, solo, timed, voices_note
from srstudio.sketch import Appearance, Beat, Line, appearances, events

SEED = 3912
SLUG = "best-angle"
TITLE = "Best Angle — Rosa and Gary (Collage)"
NAMES = ("rosa", "gary")
ROSA_SET, GARY_SET = "living-room", "boardroom"
DESCRIPTION = (
    "A Collage sketch: Rosa video-calls Gary and finds every angle but her face. Then she asks why he is a toilet."
)
ACCESSIBILITY = (
    "Paper cut-out characters on a video call: an older woman in pearls holds her phone so that her son sees only "
    "her forehead, then half her face, then her living-room wall, with the call's grey and red buttons over the "
    "picture; her balding son answers from a glass boardroom. When she finally frames herself, she sees him as a "
    "singing porcelain toilet with a paper head, in his boardroom, under the same call buttons. Lines appear in "
    "tinted pills."
)
NARRATION = f"Voiced with ElevenLabs premade voices {voices_note(NAMES)}; synthesised whoosh and sting."
NOTE = "ElevenLabs premade voices Matilda and Chris at their natural pace; no reference-voice cloning."

# Rosa's phone, shot by shot of hers: where her figure sits in the frame (dx, dy), or None for the wall
FRAMINGS: tuple[tuple[float, float] | None, ...] = ((0.0, 760.0), (430.0, 60.0), None, (0.0, 0.0), (0.0, 0.0))
LIFT = (1100.0, 0.6)  # the opening: her forehead starts this low and rises to its framing in this many seconds
BOB, BOB_PERIOD = 14.0, 1.2  # a held phone: pixels up and down, seconds a cycle
STEADY = 3  # from her fourth shot on she holds it still

LINES = (
    Line("rosa", "Gary? Is this thing on?"),
    Line("gary", "Mom, I can only see your forehead."),
    Line("rosa", "How about now?"),
    Line("gary", "Now it's half your face."),
    Line("rosa", "Better?"),
    Line("gary", "Mom, I'm talking to a wall."),
    Line("rosa", "Perfect."),
    Line("rosa", "Gary, why are you a toilet?"),
    Line("gary", "I'm a what?"),
    Line("rosa", "Leave it on. It's your best angle."),
)
BEATS, END = timed(
    LINES,
    (
        (2.0, "rosa", 0, "up", "o", "down"),  # her forehead, coming up into the frame
        (2.4, "gary", 1, "half", "flat", "hold"),  # Gary at work, phone in hand
        (1.4, "rosa", 2, "side", "smile", "down"),  # half her face
        (1.8, "gary", 3, "half", "frown", "hold"),
        (1.2, "rosa", 4, "open", "smile", "down"),  # the wall: she is out of the picture
        (2.0, "gary", 5, "angry", "frown", "face"),
        (1.0, "rosa", 6, "closed", "smile", "down"),  # framed at last
        (1.2, "rosa", "", "half", "flat", "down"),  # the pause: she looks at what she sees
        (2.2, "rosa", 7, "wide", "o", "point", "zoom"),
        (1.4, "gary", 8, "wide", "o", "hold", "reveal"),  # what she sees: the filter, his voice
        (2.4, "rosa", 9, "half", "smug", "down"),  # the button
        (0.0, "gary", "", "sad", "frown", "down", "sting"),  # the toilet, after
    ),
    tail=1.6,
)
SKETCH = make_sketch(SLUG, TITLE, NAMES, LINES, BEATS, END)


def _bob(at: float, end: float, base: float, lift: float = 0.0) -> list[tuple[float, float]]:
    """The keys of a phone held by hand from ``at`` to ``end``: from ``base + lift`` up to ``base``, then a slow
    bob about it."""
    keys = [(at, base + lift)]
    t = at + (LIFT[1] if lift else 0.0)
    keys.append((round(t, 6), base))
    i = 0
    while t + BOB_PERIOD / 2 < end:
        t += BOB_PERIOD / 2
        i += 1
        keys.append((round(t, 6), base + (-BOB if i % 2 else 0.0)))
    return keys


def casting(beats: Sequence[Beat], end: float) -> CastDrawer:
    """Rosa where her phone puts her, shot by shot; Gary as himself, until the reveal cuts to her side of the
    call, where his camera shows the toilet, playing his poses and his lip sync."""
    rosa = [a.start for a in appearances(beats, end) if a.who == "rosa"]
    reveal = events(beats, "reveal")[0][0]

    def draw(cv, parent, app: Appearance, mouths) -> collage.Point:
        if app.who == "gary":
            if app.start < reveal:
                return solo(cv, parent, app, mouths)
            poses = collage.parse_poses(app.poses, f"poses of the filter from {app.start} s")
            collage.DRAWERS["flush"](cv, parent, poses, app.end, (), enter=app.start, mouths=mouths.get("gary", ()))
            return collage.face(collage.LOOKS["flush"])
        i = rosa.index(app.start)
        framing = FRAMINGS[min(i, len(FRAMINGS) - 1)]
        face = collage.face(collage.LOOKS["rosa"])
        if framing is None:  # the phone points at the wall
            return face
        dx, dy = framing
        held = cv.group(parent, cv.uid("g"), x=dx, y=dy)
        if i < STEADY:
            cv.keys(held, "y", _bob(app.start, app.end, dy, LIFT[0] - dy if i == 0 else 0.0), kind="sine-in-out")
        solo(cv, held, app, mouths)
        return collage_sets.zoom_pivot(ROSA_SET, (face[0] + dx, face[1] + dy), ZOOM_SCALE)

    return draw


def dress(shot) -> None:
    """The call's buttons over every shot of her side of the call (her phone, and him as she sees him), on the
    screen rather than in the room: a zoom into the room leaves them where they are."""
    cv, app = shot.cv, shot.app
    if app.who == "rosa" or app.start >= events(shot.beats, "reveal")[0][0]:
        collage_sets.call_buttons(cv, cv.group(cv.comp, cv.uid("g"), start=app.start, end=app.end))


STAGING = Staging(
    sketch=SKETCH,
    seed=SEED,
    description=DESCRIPTION,
    accessibility=ACCESSIBILITY,
    narration=NARRATION,
    tints=TINTS,
    sets={"rosa": ROSA_SET, "gary": GARY_SET},
    dress=dress,
    cast=casting,
    bitrate=5_800_000,  # two passes: a master under 20 MB; the grain, new every frame, is what costs the bits
)
