"""It's Listening — the sketch as data: Bruno and Mae said they need a new mattress once, in bed. Now his phone is
all mattresses. It's listening, so Bruno will confuse it: "I love paying full price!" Thanks, prices updated. Then
Mae has him say he's broke. Loans near you.

Two voices (ElevenLabs premade Bill as Bruno, Sarah as Mae), one shot per speaker, both in their kitchen in the
morning: Bruno under a dark chip with the ad his phone keeps showing him, Mae at the coffee machine, brewing. The
sketch opens on a still first second (the ``sp-hook_motion`` test's arm A): Bruno looking at his phone under the ad,
nothing captioned, nothing moving, until his first word. The phone's answers arrive as toasts (``toast:`` events) on
his screen, and the sting plays on ``hangup`` with a crash zoom onto him. ``SKETCH`` is checked by
:func:`srstudio.sketch.check`; :func:`validate` checks what the events ask of the props; :func:`dress` draws each
shot's set and props and :func:`push` its camera (``toon_sketch.build`` draws the rest).
"""

from __future__ import annotations

from dataclasses import replace
from functools import partial

from srstudio import camera, scripting, sketch, toon_props, toon_sets
from srstudio.sketch import Line, Sketch, Speaker
from srstudio.toon_sketch import BADGE_SIZE
from srstudio.voice import Voice, VoiceSettings

SEED = 1305
SLUG = "its-listening"
TITLE = "It's Listening — Bruno and Mae (Toon)"
DESCRIPTION = (
    "A Toon sketch at home: Bruno and Mae said mattress once, in bed, and now his phone is all mattresses. He tries "
    "to confuse it. It thanks him."
)
ACCESSIBILITY = (
    "A cartoon bear in a kitchen in the morning looks at his phone under a dark chip that reads ad, mattresses near "
    "you. A cartoon rabbit stands by a brewing coffee machine. When he says he loves paying full price, a "
    "notification slides in: thanks, prices updated. When he says he is broke, another: loans near you, and the camera "
    "snaps onto his face. Their lines appear in tinted pills and their mouths move with their words."
)
NARRATION = "Voiced with ElevenLabs premade voices Bill (Bruno) and Sarah (Mae); synthesised buzz and sting."
NOTE = "ElevenLabs premade voices Bill and Sarah at their natural pace; no reference-voice cloning."
BRUNO = Speaker(
    "bruno",
    Voice(role="bruno", id="pqHfZKP75CvOlQylNhV4", name="Bill"),
    VoiceSettings(stability=0.55, similarity_boost=0.75, style=0.30),
    "bear",
)
MAE = Speaker(
    "mae",
    Voice(role="mae", id="EXAVITQu4vr4xnSDxMaL", name="Sarah"),
    VoiceSettings(stability=0.40, similarity_boost=0.75, style=0.45),
    "rabbit",
)
TINTS = {"bruno": "#f1dcc4", "mae": "#fbd3e0"}
MOUTH = replace(sketch.MOUTH_STYLE, spelling=True, close_bilabials=True, lead=0.04, min_rest=0.12)
AD = "Ad: Mattresses near you"
SENDER = "Ads for you"
TOASTS = ("Thanks! Prices updated", "Loans near you")
HIDDEN = 0.125  # seconds of a toast's slide left unseen: its lettering is still off the frame's right edge
ZOOM = (1.2, (1000.0, 1420.0))  # the crash zoom's scale and pivot (frame px): both signature marks stay in frame
END = 20.5

LINES = (
    Line("bruno", "Did you tell anyone we need a new mattress?"),
    Line("mae", "No. We said it once. In bed."),
    Line("bruno", "My phone is all mattresses now."),
    Line("mae", "Quiet. It's listening."),
    Line("bruno", "Fine. Let's confuse it."),
    Line("bruno", "I love paying full price!"),
    Line("mae", "Okay. Say you're broke."),
    Line("bruno", "I'm broke!"),
)


SCRIPT = scripting.Script(LINES)
say, first, part, hold = SCRIPT.say, SCRIPT.first, SCRIPT.part, SCRIPT.hold


BEATS = (
    hold(0.0, "bear", "", "down", "flat", "desk"),  # the still: Bruno, his phone, the ad
    first(1.1, "bear", 0, "Did you tell anyone", "narrow", "flat", "desk"),
    part(2.1, "bear", 0, 4, "we need a new mattress?", "narrow", "flat", "crossed"),
    say(3.9, "rabbit", 1, "side", "flat", "crossed"),
    say(6.2, "bear", 2, "down", "flat", "sigh"),
    say(8.0, "rabbit", 3, "wide", "flat", "face2"),
    say(9.6, "bear", 4, "narrow", "smirk", "crossed"),
    say(11.0, "bear", 5, "wide", "grin", "desk"),  # loud, to the phone
    hold(12.6, "bear", "", "down", "flat", "desk", "toast:0"),  # it thanks him
    hold(13.4, "bear", "", "shock", "drop", "face"),
    say(14.8, "rabbit", 6, "half", "smirk", "crossed"),
    say(16.4, "bear", 7, "wide", "grin", "desk"),
    hold(17.4, "bear", "", "down", "flat", "desk", "toast:1"),  # loans near you
    hold(18.2, "bear", "", "shock", "drop", "face2", "hangup"),  # the sting and the snap
)
SKETCH = Sketch(SLUG, TITLE, (BRUNO, MAE), LINES, BEATS, END)


def validate(sk: Sketch = SKETCH) -> None:
    """The sketch is consistent and its events ask only what the props can do: the first beat is the still (silent,
    uncaptioned, no event, held at least 1 s, on Bruno); toasts index ``TOASTS``, once each in order, on Bruno's
    phone, each after the line that asked for it (full price, then broke); exactly one hangup, after the last
    spoken line, on Bruno; no other events."""
    sketch.check(sk)
    opening = sk.beats[0]
    if opening.spoken or opening.caption or opening.event or opening.who != "bear" or sk.beats[1].start < 1.0:
        raise sketch.SketchError("the sketch opens on a still of Bruno: a silent, uncaptioned beat held at least 1 s")
    who_at = {b.start: b.who for b in sk.beats}
    shown = sketch.events(sk.beats, "toast")
    if [arg for _, arg in shown] != [str(i) for i in range(len(TOASTS))]:
        raise sketch.SketchError(f"the toasts land once each, in order: {len(TOASTS)} of them")
    if any(who_at[at] != "bear" for at, _ in shown):
        raise sketch.SketchError("the toasts land on Bruno's phone, in his shot")
    spoken = {b.line: b.start for b in sk.beats if b.spoken}
    if not spoken[5] < shown[0][0] < spoken[6] or not spoken[7] < shown[1][0]:
        raise sketch.SketchError("the phone answers what it heard: prices after full price, loans after broke")
    scripting.exactly_once(sk.beats, "hangup", "the sting plays exactly once")
    sting = sketch.events(sk.beats, "hangup")[0][0]
    if sting < max(b.start for b in sk.beats if b.spoken) or who_at[sting] != "bear":
        raise sketch.SketchError("the sting comes after the last line, on Bruno")
    scripting.only_events(sk.beats, {"toast", "hangup"})


def toasts_in(beats, app) -> list[toon_props.Toast]:
    """The toasts that land during one appearance, each replaced by the next or gone with the shot."""
    arrivals = [(at, int(arg)) for at, arg in sketch.events(beats, "toast") if app.start <= at < app.end]
    out = []
    for (at, idx), nxt in zip(arrivals, arrivals[1:] + [None], strict=False):
        out.append(toon_props.Toast(at, app.end if nxt is None else nxt[0], SENDER, TOASTS[idx]))
    return out


def dress(shot) -> None:
    """Both shots are their kitchen in the morning. Bruno's: the ad on his chip, held still, and the phone's
    answers. Mae's: the coffee machine, brewing."""
    cv, app = shot.cv, shot.app
    toon_sets.kitchen(cv, shot.back)
    if app.who == "bear":
        measure = partial(shot.measure, size=BADGE_SIZE)
        toon_props.badge(cv, shot.front, AD, app.start, app.end, measure, BADGE_SIZE)
        for toast in toasts_in(shot.beats, app):
            # each toast is shown from HIDDEN into its slide, once its lettering has entered the frame: the
            # engine's contrast check measures a text wholly off frame as 1:1 against itself
            shown = cv.group(shot.front, cv.uid("g"), start=round(toast.start + HIDDEN, 6), end=toast.end)
            toon_props.toasts(cv, shown, [toast])
    else:
        toon_sets.coffee_machine(cv, shot.back, brewing=[(app.start, app.end)])


def push(shot, setup) -> None:
    """The camera: still everywhere but the last shot of Bruno, which snaps in on the sting."""
    sting = sketch.events(shot.beats, "hangup")[0][0]
    if shot.app.start <= sting < shot.app.end:
        scale, (x, y) = ZOOM
        camera.anchor(setup, x, y, place=True)
        camera.crash_zoom(shot.cv, setup, sting, scale)
