"""Cleaning Fee — the sketch as data: Fern paid the holiday rental's cleaning fee. Rex, her host, sends the checkout
list: strip the beds, run the dishwasher, take out the trash, repaint the fence (just the front). She does it all and
asks what the cleaner does. He checks her work. Then the late checkout fee lands: the kitchen clock says 11:40.

Two voices (ElevenLabs premade Matilda as Fern, Charlie as Rex), one shot per speaker: Fern in the rental's kitchen
on the phone, the wall clock jumping on through the morning every time we cut back to her; Rex at his desk, his host
rating on a chip. The sketch opens moving (the ``sp-hook_motion`` test's arm B): she is talking from the first frame,
the cleaning fee slides in on her phone and the camera pushes in. The fees arrive as toasts (``toast:`` events), the
list's worst items cut in full frame from the fridge note (``note:`` events), and the sting plays on ``hangup`` with
a crash zoom onto her. ``SKETCH`` is checked by :func:`srstudio.sketch.check`; :func:`validate` checks what the
events ask of the props; :func:`dress` draws each shot's set and props and :func:`push` its camera
(``toon_sketch.build`` draws the rest).
"""

from __future__ import annotations

from dataclasses import replace
from functools import partial

from srstudio import camera, scripting, sketch, toon, toon_props, toon_sets
from srstudio.sketch import Line, Sketch, Speaker
from srstudio.toon_sketch import BADGE_SIZE
from srstudio.voice import Voice, VoiceSettings

SEED = 1302
SLUG = "cleaning-fee"
TITLE = "Cleaning Fee — Fern and Rex (Toon)"
DESCRIPTION = (
    "A Toon sketch over the phone: Fern paid the rental's cleaning fee, then stripped the beds, ran the dishwasher, "
    "took out the trash and repainted the fence. The cleaner checks her work. Then the late checkout fee arrives."
)
ACCESSIBILITY = (
    "A cartoon frog on the phone in a kitchen with a fridge, a tiled wall and a wall clock; a notification on her "
    "phone reads cleaning fee, 150 dollars. A cartoon dog answers from his desk under a chip that reads host rating "
    "4.98. The note on the fridge is cut in full frame: strip the beds, then repaint fence. Every time we see her "
    "the clock is later. When she has finished, a notification reads late checkout fee, 75 dollars, the clock says "
    "11:40, her jaw drops and the camera snaps onto her. Their lines appear in tinted pills and their mouths move "
    "with their words."
)
NARRATION = "Voiced with ElevenLabs premade voices Matilda (Fern) and Charlie (Rex); synthesised buzz and sting."
NOTE = "ElevenLabs premade voices Matilda and Charlie at their natural pace; no reference-voice cloning."
FERN = Speaker(
    "fern",
    Voice(role="fern", id="XrExE9yKIg1WjnnlVkGX", name="Matilda"),
    VoiceSettings(stability=0.50, similarity_boost=0.75, style=0.40),
    "frog",
)
REX = Speaker(
    "rex",
    Voice(role="rex", id="IKne3meq5aSn9XLyUdCD", name="Charlie"),
    VoiceSettings(stability=0.40, similarity_boost=0.75, style=0.45),
    "dog",
)
TINTS = {"rex": "#ffe3b3", "fern": "#d6f5dc"}
MOUTH = replace(sketch.MOUTH_STYLE, spelling=True, close_bilabials=True, lead=0.04, min_rest=0.12)
BADGES = {"dog": "Host rating: 4.98"}
FIRST_NOTE = "CHECKOUT LIST"
TOASTS = (("Rex (host)", "Cleaning fee: $150"), ("Rex (host)", "Late checkout fee: $75"))
CLOCK = ("09:00", "09:35", "10:20", "10:55", "11:30", "11:40", "11:41")  # the wall clock, one per shot of Fern
CLOCK_AT = (100.0, 365.0)  # the clock on the tiles above Fern's head, in frame through the opening push (ref px)
HIDDEN = 0.125  # seconds of a toast's slide left unseen: its lettering is still off the frame's right edge
PUSH = (1.0, 1.08, 2.0, (900.0, 1000.0))  # the opening push: from, to, over seconds, pivot (frame px)
ZOOM = (1.2, (1000.0, 1420.0))  # the crash zoom's scale and pivot (frame px): both signature marks stay in frame
END = 23.5

LINES = (
    Line("fern", "So we paid the cleaning fee."),
    Line("rex", "Best money you'll ever spend!"),
    Line("fern", "Your list says strip the beds."),
    Line("rex", "Saves the cleaner time."),
    Line("fern", "Run the dishwasher. Take out the trash."),
    Line("rex", "Teamwork!"),
    Line("fern", "Repaint the fence?"),
    Line("rex", "Just the front."),
    Line("fern", "Done. So what does the cleaner do?"),
    Line("rex", "Checks your work."),
    Line("rex", "Hope you enjoyed your stay!"),
)


SCRIPT = scripting.Script(LINES)
say, first, part, hold = SCRIPT.say, SCRIPT.first, SCRIPT.part, SCRIPT.hold


BEATS = (
    say(0.0, "frog", 0, "half", "flat", "desk", "toast:0"),  # the hook: talking, the fee lands, the push
    say(1.65, "dog", 1, "closed", "grin", "lean"),
    first(3.5, "frog", 2, "Your list says", "down", "flat", "crossed"),
    part(4.3, "frog", 2, 3, "strip the beds.", "side", "flat", "crossed", "note:STRIP THE BEDS"),  # the list, cut in
    say(5.6, "dog", 3, "half", "smirk", "type"),
    first(7.1, "frog", 4, "Run the dishwasher.", "narrow", "flat", "sigh"),
    part(8.2, "frog", 4, 3, "Take out the trash.", "narrow", "flat", "sigh"),
    say(9.6, "dog", 5, "wide", "grin", "lean"),
    first(10.55, "frog", 6, "Repaint", "shock", "o", "face2"),
    part(11.0, "frog", 6, 1, "the fence?", "shock", "o", "face2", "note:REPAINT FENCE"),  # the worst of it, cut in
    say(12.3, "dog", 7, "closed", "smirk", "lean"),
    say(13.5, "frog", 8, "narrow", "flat", "crossed"),
    say(15.8, "dog", 9, "half", "smirk", "type"),
    hold(17.1, "frog", "", "wide", "flat", "crossed", "toast:1"),  # the fee lands; the clock says 11:40
    hold(18.1, "frog", "", "shock", "drop", "face"),  # the jaw drops
    say(19.3, "dog", 10, "closed", "grin", "lean"),  # the topper
    hold(21.0, "frog", "", "shock", "drop", "face2", "hangup"),  # the sting and the snap
)
SKETCH = Sketch(SLUG, TITLE, (FERN, REX), LINES, BEATS, END)


def fern_shots(beats, end: float) -> list[sketch.Appearance]:
    """Fern's appearances, in order: the wall clock is behind her, one time per shot."""
    return [app for app in sketch.appearances(beats, end) if app.who == "frog"]


def clock_times(beats, end: float) -> list[tuple[float, str]]:
    """``(project second, "HH:MM")`` for :func:`srstudio.toon_props.clock`: each shot of Fern shows a later time."""
    return [(app.start, CLOCK[i]) for i, app in enumerate(fern_shots(beats, end))]


def notes_by_time(beats) -> list[tuple[float, str]]:
    """The note on the fridge: the checkout list from 0, then every ``note:`` event."""
    return scripting.changes(beats, "note", FIRST_NOTE)


def inserts(beats, start: float, end: float) -> list[tuple[float, float, str]]:
    """The close-ups of the note in a shot: from each ``note:`` beat to the next beat (or the shot's end)."""
    starts = [b.start for b in beats] + [end]
    return [
        (at, min(end, next(t for t in starts if t > at)), text)
        for at, text in sketch.events(beats, "note")
        if start <= at < end
    ]


def validate(sk: Sketch = SKETCH) -> None:
    """The sketch is consistent and its events ask only what the props can do: the first beat is spoken, captioned
    and lands the first toast (the moving opening); toasts index ``TOASTS``, once each in order, on Fern's phone; the
    late fee lands after Rex's last answer, while the clock is past eleven; every note fits the fridge, is new and
    is cut in Fern's shot; the clock has a time for every shot of Fern, each later; exactly one hangup, after the
    last spoken line, on Fern; no other events."""
    sketch.check(sk)
    opening = sk.beats[0]
    if not (opening.spoken and opening.caption and opening.event == "toast:0" and opening.start == 0.0):
        raise sketch.SketchError("the sketch opens moving: Fern talking from 0 s as the cleaning fee lands")
    who_at = {b.start: b.who for b in sk.beats}
    shown = sketch.events(sk.beats, "toast")
    if [arg for _, arg in shown] != [str(i) for i in range(len(TOASTS))]:
        raise sketch.SketchError(f"the toasts land once each, in order: {len(TOASTS)} of them")
    if any(who_at[at] != "frog" for at, _ in shown):
        raise sketch.SketchError("the toasts land on Fern's phone, in her shot")
    for at, text in notes_by_time(sk.beats):
        if len(text) > toon_sets.NOTE_MAX:
            raise sketch.SketchError(f"the note {text!r} at {at} s does not fit the fridge ({toon_sets.NOTE_MAX})")
        if at > 0 and who_at[at] != "frog":
            raise sketch.SketchError(f"the note at {at} s is cut in off Fern's shot: the fridge is behind her")
    texts = [text for _, text in notes_by_time(sk.beats)]
    if len(set(texts)) != len(texts):
        raise sketch.SketchError(f"a note is written twice: {texts}")
    shots = fern_shots(sk.beats, sk.end)
    if len(shots) != len(CLOCK) or sorted(CLOCK) != list(CLOCK) or len(set(CLOCK)) != len(CLOCK):
        raise sketch.SketchError(f"the clock needs one later time for each of Fern's {len(shots)} shots")
    toon_props.clock_angles(CLOCK[0])  # every time is HH:MM (the prop refuses the rest)
    late = shown[-1][0]
    if late <= max(b.start for b in sk.beats if b.spoken and b.who == "dog" and b.start < late):
        raise sketch.SketchError("the late fee lands after Rex's answer")
    if dict(clock_times(sk.beats, sk.end)).get(next(a.start for a in shots if a.start <= late < a.end)) <= "11:00":
        raise sketch.SketchError("the late fee lands while the clock is past checkout (eleven)")
    scripting.exactly_once(sk.beats, "hangup", "the sting plays exactly once")
    sting = sketch.events(sk.beats, "hangup")[0][0]
    if sting < max(b.start for b in sk.beats if b.spoken) or who_at[sting] != "frog":
        raise sketch.SketchError("the sting comes after the last line, on Fern")
    scripting.only_events(sk.beats, {"toast", "note", "hangup"})


def toasts_in(beats, app) -> list[toon_props.Toast]:
    """The toasts that land during one appearance, each replaced by the next or gone with the shot."""
    arrivals = [(at, int(arg)) for at, arg in sketch.events(beats, "toast") if app.start <= at < app.end]
    out = []
    for (at, idx), nxt in zip(arrivals, arrivals[1:] + [None], strict=False):
        sender, text = TOASTS[idx]
        out.append(toon_props.Toast(at, app.end if nxt is None else nxt[0], sender, text))
    return out


def dress(shot) -> None:
    """Fern's shots: the rental's kitchen, the checkout list on the fridge, the wall clock at this shot's time, the
    list's worst items cut in full frame and the fees on her phone. Rex's: his desk, a mug, his host rating."""
    cv, app = shot.cv, shot.app
    if app.who == "frog":
        toon_sets.kitchen(cv, shot.back, note=FIRST_NOTE)
        toon_props.clock(cv, shot.back, clock_times(shot.beats, shot.end), at=CLOCK_AT)
        for toast in toasts_in(shot.beats, app):
            # each toast is shown from HIDDEN into its slide, once its lettering has entered the frame: the
            # engine's contrast check measures a text wholly off frame as 1:1 against itself
            shown = cv.group(shot.front, cv.uid("g"), start=round(toast.start + HIDDEN, 6), end=toast.end)
            toon_props.toasts(cv, shown, [toast])
        for a, b, text in inserts(shot.beats, app.start, app.end):
            toon_sets.note_insert(cv, shot.front, text, a, b)
    else:
        toon.room(cv, shot.back)
        toon_props.mug(cv, shot.front)
        measure = partial(shot.measure, size=BADGE_SIZE)
        toon_props.badge(cv, shot.front, BADGES["dog"], app.start, app.end, measure, BADGE_SIZE)


def push(shot, setup) -> None:
    """The camera: a push in on the opening shot from its first frame, a crash zoom onto Fern on the sting, still
    everywhere else."""
    app = shot.app
    if app.start == 0.0:
        a, b, over, (x, y) = PUSH
        camera.anchor(setup, x, y, place=True)
        camera.push_in(shot.cv, setup, scale=[(0.0, a), (min(over, app.end), b)])
    sting = sketch.events(shot.beats, "hangup")[0][0]
    if app.start <= sting < app.end:
        scale, (x, y) = ZOOM
        camera.anchor(setup, x, y, place=True)
        camera.crash_zoom(shot.cv, setup, sting, scale)
