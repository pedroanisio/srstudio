"""Still Typing — the sketch as data: Brock asked Mia about pizza. MIA IS TYPING... has been on his screen for ten
minutes, so he starts apologising: her plant, her toothbrush (once), and her mom, who thinks they're engaged. Mia was
only choosing between pepperoni and mushroom. She answers: pepperoni. Brock relaxes. Then she starts typing again.

Two voices (ElevenLabs premade Roger as Brock, River as Mia, as in *Split It*), one shot per speaker: Brock in the
home office at night, the dark typing chip under the captions while she types; Mia in the meeting room working late,
the pizza question written up on the whiteboard behind her, a plant on her desk, typing. The sketch opens on a still
first second (the ``sp-hook_motion`` test's arm A): Brock and the chip, nothing captioned, nothing moving, until his
first word. His confessions arrive on Mia's phone as toasts (``toast:`` events), her answer on his; the chip goes off
when her answer lands and comes back on the ``typing`` event; the sting plays on ``hangup`` with a crash zoom onto
him. ``SKETCH`` is checked by :func:`srstudio.sketch.check`; :func:`validate` checks what the events ask of the
props; :func:`dress` draws each shot's set and props and :func:`push` its camera (``toon_sketch.build`` draws the
rest).
"""

from __future__ import annotations

from dataclasses import replace
from functools import partial

from srstudio import camera, scripting, sketch, toon_props, toon_sets
from srstudio.sketch import Line, Sketch, Speaker
from srstudio.toon_sketch import BADGE_SIZE
from srstudio.voice import Voice, VoiceSettings

SEED = 1301
SLUG = "still-typing"
TITLE = "Still Typing — Brock and Mia (Toon)"
DESCRIPTION = (
    "A Toon sketch over text: Mia has been typing for ten minutes, so Brock apologises for her plant, her "
    "toothbrush and her mom, who thinks they're engaged. She was choosing a pizza. Then she starts typing again."
)
ACCESSIBILITY = (
    "A cartoon bear sits at a desk in a room at night under a dark chip that reads MIA IS TYPING. A cartoon rabbit "
    "types at a desk in a meeting room late at work, a potted plant beside her and PEPPERONI VS MUSHROOM written on "
    "the whiteboard behind her. His messages slide in over her whiteboard as phone notifications: sorry about your "
    "plant, I used your toothbrush, also, we're engaged. Her answer slides in over his window: pepperoni. Then the "
    "typing chip comes back and the camera snaps onto his face. Their lines appear in tinted pills and their mouths "
    "move with their words."
)
NARRATION = "Voiced with ElevenLabs premade voices Roger (Brock) and River (Mia); synthesised keyboard, buzz and sting."
NOTE = "ElevenLabs premade voices Roger and River at their natural pace; no reference-voice cloning."
BROCK = Speaker(
    "brock",
    Voice(role="brock", id="CwhRBWXzGAHq8TQ4Fs17", name="Roger"),
    VoiceSettings(stability=0.40, similarity_boost=0.75, style=0.45),
    "bear",
)
MIA = Speaker(
    "mia",
    Voice(role="mia", id="SAz9YHcvj6GT2YYXdXww", name="River"),
    VoiceSettings(stability=0.50, similarity_boost=0.75, style=0.30),
    "rabbit",
)
TINTS = {"brock": "#f3dcc0", "mia": "#f6d6e4"}
MOUTH = replace(sketch.MOUTH_STYLE, spelling=True, close_bilabials=True, lead=0.04, min_rest=0.12)
CHIP = "Mia is typing..."
BOARD = "PEPPERONI vs MUSHROOM"
TOASTS = (
    ("Brock", "Sorry about your plant."),
    ("Brock", "I used your toothbrush."),
    ("Brock", "Also, we're engaged."),
    ("Mia", "Pepperoni."),
)
PHONE = {0: "rabbit", 1: "rabbit", 2: "rabbit", 3: "bear"}  # whose phone each toast lands on
HIDDEN = 0.125  # seconds of a toast's slide left unseen: its lettering is still off the frame's right edge
STILL = 1.1  # the opening holds still this long: no caption, no mouth, no blink, no move
ZOOM = (1.2, (1000.0, 1420.0))  # the crash zoom's scale and pivot (frame px): both signature marks stay in frame
END = 25.0

LINES = (
    Line("brock", "She's been typing for ten minutes."),
    Line("mia", "Pepperoni. Or mushroom?"),
    Line("brock", "Okay. I'm sorry about your plant."),
    Line("mia", "What about my plant?"),
    Line("brock", "And I used your toothbrush. Once."),
    Line("mia", "Once?"),
    Line("brock", "And your mom thinks we're engaged."),
    Line("brock", "Pepperoni. Great."),
)


SCRIPT = scripting.Script(LINES)
say, first, part, hold = SCRIPT.say, SCRIPT.first, SCRIPT.part, SCRIPT.hold


BEATS = (
    hold(0.0, "bear", "", "wide", "flat", "desk"),  # the still: Brock and the chip, nothing else
    say(STILL, "bear", 0, "wide", "flat", "desk"),
    say(3.6, "rabbit", 1, "half", "flat", "type"),  # what she is really typing about
    say(5.8, "bear", 2, "narrow", "flat", "type"),
    hold(8.1, "rabbit", "", "side", "flat", "desk", "toast:0"),  # she looks at her plant
    say(8.6, "rabbit", 3, "narrow", "o", "desk"),
    say(10.3, "bear", 4, "down", "flat", "type"),
    hold(12.8, "rabbit", "", "narrow", "flat", "crossed", "toast:1"),
    say(13.2, "rabbit", 5, "shock", "o", "face"),
    first(14.2, "bear", 6, "And your mom thinks", "closed", "smirk", "type"),
    part(15.3, "bear", 6, 4, "we're engaged.", "half", "grin", "type"),
    hold(16.5, "rabbit", "", "shock", "drop", "face2", "toast:2"),  # the jaw drops
    hold(17.9, "rabbit", "", "narrow", "flat", "type"),  # she types her answer
    hold(19.2, "bear", "", "wide", "o", "desk", "toast:3"),  # it lands: pepperoni
    say(20.0, "bear", 7, "closed", "grin", "lean"),
    hold(21.6, "bear", "", "wide", "flat", "desk", "typing"),  # the chip is back
    hold(22.6, "bear", "", "shock", "drop", "face", "hangup"),  # the sting and the snap
)
SKETCH = Sketch(SLUG, TITLE, (BROCK, MIA), LINES, BEATS, END)


def chip_spans(beats, end: float) -> list[tuple[float, float]]:
    """When MIA IS TYPING shows: from 0 until her answer lands (``toast:3``), then from ``typing`` to the end."""
    answer = next(at for at, arg in sketch.events(beats, "toast") if arg == "3")
    again = sketch.events(beats, "typing")[0][0]
    return [(0.0, answer), (again, end)]


def validate(sk: Sketch = SKETCH) -> None:
    """The sketch is consistent and its events ask only what the props can do: the first beat is the still (silent,
    uncaptioned, no event, held until the first word); toasts index ``TOASTS``, once each in order, each on its
    owner's phone; the chip comes back once, in Brock's shot, after her answer; exactly one hangup, after the last
    spoken line, in his shot; no other events."""
    sketch.check(sk)
    first = sk.beats[0]
    if first.spoken or first.caption or first.event or sk.beats[1].start < 1.0:
        raise sketch.SketchError("the sketch opens on a still: a silent, uncaptioned beat held at least 1 s")
    who_at = {b.start: b.who for b in sk.beats}
    shown = sketch.events(sk.beats, "toast")
    if [arg for _, arg in shown] != [str(i) for i in range(len(TOASTS))]:
        raise sketch.SketchError(f"the toasts land once each, in order: {len(TOASTS)} of them")
    for at, arg in shown:
        if who_at[at] != PHONE[int(arg)]:
            raise sketch.SketchError(f"toast {arg} at {at} s lands off screen: it is on the {PHONE[int(arg)]}'s phone")
    scripting.exactly_once(sk.beats, "typing", "the chip comes back exactly once")
    again = sketch.events(sk.beats, "typing")[0][0]
    if who_at[again] != "bear" or again <= shown[-1][0]:
        raise sketch.SketchError("the chip comes back in Brock's shot, after her answer")
    scripting.exactly_once(sk.beats, "hangup", "the sting plays exactly once")
    sting = sketch.events(sk.beats, "hangup")[0][0]
    if sting < max(b.start for b in sk.beats if b.spoken) or who_at[sting] != "bear":
        raise sketch.SketchError("the sting comes after the last line, on Brock")
    scripting.only_events(sk.beats, {"toast", "typing", "hangup"})


def toasts_in(beats, app) -> list[toon_props.Toast]:
    """The toasts that land during one appearance, each replaced by the next or gone with the shot."""
    arrivals = [(at, int(arg)) for at, arg in sketch.events(beats, "toast") if app.start <= at < app.end]
    out = []
    for (at, idx), nxt in zip(arrivals, arrivals[1:] + [None], strict=False):
        sender, text = TOASTS[idx]
        out.append(toon_props.Toast(at, app.end if nxt is None else nxt[0], sender, text))
    return out


def dress(shot) -> None:
    """Brock's shots: the home office at night, held still (no twinkle: the opening is the test's still arm), the
    typing chip while she types. Mia's: the meeting room, the pizza question on the board, a plant on her desk."""
    cv, app = shot.cv, shot.app
    if app.who == "bear":
        toon_sets.home(cv, shot.back)
        measure = partial(shot.measure, size=BADGE_SIZE)
        for a, b in chip_spans(shot.beats, shot.end):
            a, b = max(a, app.start), min(b, app.end)
            if a < b:
                toon_props.badge(cv, shot.front, CHIP, a, b, measure, BADGE_SIZE)
    else:
        toon_props.meeting(cv, shot.back)
        toon_props.board_text(cv, shot.back, BOARD)
        toon_sets.plant(cv, shot.front, end=app.end)
    for toast in toasts_in(shot.beats, app):
        # each toast is shown from HIDDEN into its slide, once its lettering has entered the frame: the engine's
        # contrast check measures a text wholly off frame as 1:1 against itself
        shown = cv.group(shot.front, cv.uid("g"), start=round(toast.start + HIDDEN, 6), end=toast.end)
        toon_props.toasts(cv, shown, [toast])


def push(shot, setup) -> None:
    """The camera: still everywhere but the last shot of Brock, which snaps in on the sting."""
    sting = sketch.events(shot.beats, "hangup")[0][0]
    if shot.app.start <= sting < shot.app.end:
        scale, (x, y) = ZOOM
        camera.anchor(setup, x, y, place=True)
        camera.crash_zoom(shot.cv, setup, sting, scale)
