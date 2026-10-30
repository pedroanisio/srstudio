"""Heard Back — the sketch as data: Dana is interviewing Otto over video and it is going really well. He asks when
he will hear back; he hears back, mid-sentence: "We regret to inform you". That's automatic, ignore it. The next one
asks him to rate the interview; five stars helps. Then the same notice lands on Dana's screen. She heard back too.
Would she like to rate them? One star.

Two voices (ElevenLabs premade Jessica as Dana, Daniel as Otto), one shot per speaker: Dana in the meeting room,
WE'RE HIRING on the whiteboard behind her; Otto at his desk at home. The sketch opens moving (the ``sp-hook_motion``
test's arm B): Dana is talking from the first frame while the camera pulls back from her to the board. The hiring
system's notices arrive as toasts (``toast:`` events) on Otto's phone, the last on hers, and the sting plays on
``hangup`` with a crash zoom onto her. ``SKETCH`` is checked by :func:`srstudio.sketch.check`; :func:`validate`
checks what the events ask of the props; :func:`dress` draws each shot's set and props and :func:`push` its camera
(``toon_sketch.build`` draws the rest).
"""

from __future__ import annotations

from dataclasses import replace

from srstudio import camera, scripting, sketch, toon, toon_props
from srstudio.sketch import Line, Sketch, Speaker
from srstudio.voice import Voice, VoiceSettings

SEED = 1304
SLUG = "heard-back"
TITLE = "Heard Back — Dana and Otto (Toon)"
DESCRIPTION = (
    "A Toon sketch over a video interview: it is going really well, until the hiring system rejects Otto "
    "mid-interview, asks him to rate it, and then rejects his interviewer."
)
ACCESSIBILITY = (
    "A cartoon dog interviews over video from a meeting room with WE'RE HIRING written on the whiteboard behind her; "
    "a cartoon bear answers from his desk at home. Notifications from the hiring team slide in over his window: we "
    "regret to inform you, then how did we do, rate us. Then the same we regret to inform you slides in over her "
    "whiteboard, and the camera snaps onto her. Their lines appear in tinted pills and their mouths move with their "
    "words."
)
NARRATION = "Voiced with ElevenLabs premade voices Jessica (Dana) and Daniel (Otto); synthesised buzz and sting."
NOTE = "ElevenLabs premade voices Jessica and Daniel at their natural pace; no reference-voice cloning."
DANA = Speaker(
    "dana",
    Voice(role="dana", id="cgSgspJ2msm6clMCkdW9", name="Jessica"),
    VoiceSettings(stability=0.40, similarity_boost=0.75, style=0.55),
    "dog",
)
OTTO = Speaker(
    "otto",
    Voice(role="otto", id="onwK4e9ZLuTAKqWW03F9", name="Daniel"),
    VoiceSettings(stability=0.60, similarity_boost=0.75, style=0.25),
    "bear",
)
TINTS = {"dana": "#f6dcb8", "otto": "#d8e4f4"}
MOUTH = replace(sketch.MOUTH_STYLE, spelling=True, close_bilabials=True, lead=0.04, min_rest=0.12)
BOARD = "WE'RE HIRING!"
SENDER = "Hiring team"
TOASTS = ("We regret to inform you", "How did we do? Rate us", "We regret to inform you")
PHONE = ("bear", "bear", "dog")  # whose screen each toast lands on
HIDDEN = 0.125  # seconds of a toast's slide left unseen: its lettering is still off the frame's right edge
PULL = (1.08, 1.0, 1.6, (900.0, 1000.0))  # the opening pull back: from, to, over seconds, pivot (frame px)
ZOOM = (1.2, (1000.0, 1420.0))  # the crash zoom's scale and pivot (frame px): both signature marks stay in frame
END = 24.0

LINES = (
    Line("dana", "Honestly, Otto? This is going really well."),
    Line("otto", "Thank you! I'm very excited."),
    Line("dana", "Any questions for us?"),
    Line("otto", "Just one. When will I hear back?"),
    Line("otto", "I think I just heard back."),
    Line("dana", "Oh, that's automatic. Ignore it."),
    Line("otto", "Now it wants me to rate you."),
    Line("dana", "Five stars really helps."),
    Line("dana", "Huh. I just heard back too."),
    Line("otto", "Want to rate them?"),
    Line("dana", "One star."),
)


SCRIPT = scripting.Script(LINES)
say, first, part, hold = SCRIPT.say, SCRIPT.first, SCRIPT.part, SCRIPT.hold


BEATS = (
    first(0.0, "dog", 0, "Honestly, Otto?", "half", "grin", "desk"),  # the hook: talking, the pull back
    part(1.2, "dog", 0, 2, "This is going really well.", "wide", "grin", "lean"),
    say(3.4, "bear", 1, "wide", "grin", "desk"),
    say(5.4, "dog", 2, "half", "smirk", "crossed"),
    say(6.9, "bear", 3, "half", "flat", "desk"),
    hold(8.9, "bear", "", "down", "flat", "desk", "toast:0"),  # he hears back
    say(10.1, "bear", 4, "down", "o", "face"),
    say(11.9, "dog", 5, "closed", "grin", "crossed"),
    hold(13.9, "bear", "", "down", "flat", "desk", "toast:1"),  # the survey
    say(14.6, "bear", 6, "narrow", "flat", "crossed"),
    say(16.3, "dog", 7, "half", "grin", "lean"),
    hold(17.9, "dog", "", "side", "flat", "desk", "toast:2"),  # her turn
    hold(18.7, "dog", "", "shock", "drop", "face"),
    say(19.5, "dog", 8, "down", "flat", "face2"),
    say(21.3, "bear", 9, "half", "smirk", "crossed"),
    say(22.6, "dog", 10, "narrow", "flat", "crossed"),
    hold(23.4, "dog", "", "narrow", "smirk", "crossed", "hangup"),  # the sting and the snap
)
SKETCH = Sketch(SLUG, TITLE, (DANA, OTTO), LINES, BEATS, END)


def validate(sk: Sketch = SKETCH) -> None:
    """The sketch is consistent and its events ask only what the props can do: the first beat is spoken, captioned
    and on Dana from 0 s (the moving opening); toasts index ``TOASTS``, once each in order, each on its screen's
    owner; Otto's first one lands after he asks when he will hear back; hers after his five stars; exactly one
    hangup, after the last spoken line, on Dana; no other events."""
    sketch.check(sk)
    opening = sk.beats[0]
    if not (opening.spoken and opening.caption and opening.who == "dog" and opening.start == 0.0):
        raise sketch.SketchError("the sketch opens moving: Dana talking from 0 s")
    who_at = {b.start: b.who for b in sk.beats}
    shown = sketch.events(sk.beats, "toast")
    if [arg for _, arg in shown] != [str(i) for i in range(len(TOASTS))]:
        raise sketch.SketchError(f"the toasts land once each, in order: {len(TOASTS)} of them")
    for at, arg in shown:
        if who_at[at] != PHONE[int(arg)]:
            raise sketch.SketchError(f"toast {arg} at {at} s lands off screen: it is on the {PHONE[int(arg)]}'s")
    spoken = {b.line: b.start for b in sk.beats if b.spoken}
    if shown[0][0] <= spoken[3] or shown[2][0] <= spoken[7]:
        raise sketch.SketchError("he hears back after asking when; she hears back after the five stars")
    scripting.exactly_once(sk.beats, "hangup", "the sting plays exactly once")
    sting = sketch.events(sk.beats, "hangup")[0][0]
    if sting < max(b.start for b in sk.beats if b.spoken) or who_at[sting] != "dog":
        raise sketch.SketchError("the sting comes after the last line, on Dana")
    scripting.only_events(sk.beats, {"toast", "hangup"})


def toasts_in(beats, app) -> list[toon_props.Toast]:
    """The toasts that land during one appearance, each replaced by the next or gone with the shot."""
    arrivals = [(at, int(arg)) for at, arg in sketch.events(beats, "toast") if app.start <= at < app.end]
    out = []
    for (at, idx), nxt in zip(arrivals, arrivals[1:] + [None], strict=False):
        out.append(toon_props.Toast(at, app.end if nxt is None else nxt[0], SENDER, TOASTS[idx]))
    return out


def dress(shot) -> None:
    """Dana's shots: the meeting room, WE'RE HIRING on the board. Otto's: his room at home, a mug. Each screen's
    notices from the hiring team."""
    cv, app = shot.cv, shot.app
    if app.who == "dog":
        toon_props.meeting(cv, shot.back)
        toon_props.board_text(cv, shot.back, BOARD)
    else:
        toon.room(cv, shot.back)
        toon_props.mug(cv, shot.front)
    for toast in toasts_in(shot.beats, app):
        # each toast is shown from HIDDEN into its slide, once its lettering has entered the frame: the engine's
        # contrast check measures a text wholly off frame as 1:1 against itself
        shown = cv.group(shot.front, cv.uid("g"), start=round(toast.start + HIDDEN, 6), end=toast.end)
        toon_props.toasts(cv, shown, [toast])


def push(shot, setup) -> None:
    """The camera: a pull back from Dana to the board on the opening shot from its first frame, a crash zoom onto
    her on the sting, still everywhere else."""
    app = shot.app
    if app.start == 0.0:
        a, b, over, (x, y) = PULL
        camera.anchor(setup, x, y, place=True)
        camera.push_in(shot.cv, setup, scale=[(0.0, a), (min(over, app.end), b)])
    sting = sketch.events(shot.beats, "hangup")[0][0]
    if app.start <= sting < app.end:
        scale, (x, y) = ZOOM
        camera.anchor(setup, x, y, place=True)
        camera.crash_zoom(shot.cv, setup, sting, scale)
