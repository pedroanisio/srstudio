"""Following Up — the sketch as data: one follow-up email after an interview takes four hours and a committee, and the
whole fight is about an exclamation mark.

Three voices (ElevenLabs premade River as Mia, Daniel as Otto, Will as Lewis). One kitchen. The laptop's screen sits
under the desk's edge, its draft changing on every line, starting at DRAFT 31; crossed-out notes pile up and the mugs
multiply; the clock jumps from 2:00 to 6:00 on ``six``. She sends on ``send``, the ping on ``ping``, the screen turns
to ``Thanks!`` on ``thanks``, Otto lifts the glass on ``lift``, the mark fills the frame, and the corkboard comes in on
``board``. :func:`validate` checks the events; :func:`dress` draws each shot, :func:`lens` its camera, :func:`sounds`
its foley and :func:`tired` Mia's eyes.
"""

from __future__ import annotations

from dataclasses import replace

from srstudio import (
    camera,
    foley,
    scripting,
    sketch,
    toon,
    toon_cast,
    toon_drafts,
    toon_house,
    toon_pair,
    toon_parlour,
    toon_props,
    toon_redrawn,
    toon_sets,
)
from srstudio.sketch import Line, Sketch, Speaker
from srstudio.toon_drafts import Draft, Note
from srstudio.toon_pair import Act
from srstudio.toon_sketch import Sound
from srstudio.voice import Voice, VoiceSettings

MOUTH = replace(sketch.MOUTH_STYLE, spelling=True, close_bilabials=True, lead=0.04, min_rest=0.12)
SEED = 3317
SLUG = "following-up"
TITLE = "Following Up — Mia, Otto and Lewis Write an Email (Toon)"
DESCRIPTION = "A Toon sketch: three friends spend four hours on one follow-up email, and the reply is one word."
ACCESSIBILITY = (
    "A cartoon rabbit types at a laptop in a kitchen with a bear and a raccoon over her shoulders, and the screen "
    "shows draft 31 of a short email. Every word gets a verdict: needy, threatening, now you're her friend, now you're "
    "her niece. Crossed-out sticky notes pile up. The clock jumps from two to six and there are nine mugs. She sends "
    "it. A ping: the reply says Thanks, with an exclamation mark. The bear lifts a magnifying glass, and the mark "
    "fills the frame. Is that friendly, or a warning? A corkboard slides in with the mark pinned at its center and "
    "every crossed-out greeting around it. Get the string, she says. Lines appear in tinted pills."
)
NARRATION = "Voiced with ElevenLabs premade voices River (Mia), Daniel (Otto) and Will (Lewis); synthesized foley."
NOTE = "ElevenLabs premade voices River, Daniel and Will at their natural pace; no reference-voice cloning."
MIA = Speaker(
    "mia",
    Voice(role="mia", id="SAz9YHcvj6GT2YYXdXww", name="River"),
    VoiceSettings(stability=0.5, similarity_boost=0.75, style=0.3),
    "rabbit",
)
OTTO = Speaker(
    "otto",
    Voice(role="otto", id="onwK4e9ZLuTAKqWW03F9", name="Daniel"),
    VoiceSettings(stability=0.65, similarity_boost=0.75, style=0.15),
    "bear",
)
LEWIS = Speaker(
    "lewis",
    Voice(role="lewis", id="bIHbv24MWmeRgasZH58o", name="Will"),
    VoiceSettings(stability=0.65, similarity_boost=0.75, style=0.15),
    "raccoon",
)
TINTS = {"mia": "#f7d6e0", "otto": "#f0dcc0", "lewis": "#d6e2f0"}
BARE = ("hamster", "sloth")  # the three of them, and the mark filling the frame
HEADS = ("rabbit", "bear", "raccoon")
FIGURES = {"rabbit": (0.92, 0.0), "bear": (0.92, 0.0), "raccoon": (0.92, 0.0)}
PIVOT = (980.0, 1420.0)
OTTO_SEAT, LEWIS_SEAT, MIA_SEAT = (88.0, 846.0), (444.0, 846.0), (262.0, 884.0)
OTTO_SCALE, LEWIS_SCALE, MIA_SCALE = 0.76, 0.76, 0.84
GLASS_AT, ARM_ROOT, FIST = (322.0, 950.0), (30.0, 1150.0), (214.0, 1062.0)
RISE = 330.0  # how far below its place the glass starts
CLOCK_AT, CLOCK_R = (72.0, 356.0), 56.0
MUG_SCALE = 0.72
MUGS = tuple(16.0 + 56.0 * k for k in range(9))  # the last, all nine; the first stands from the first frame
END = 32.2

LINES = (
    Line("mia", "Hi Joan, hope you're well."),
    Line("otto", "Needy."),
    Line("lewis", "Take out 'well'."),
    Line("mia", "Hi Joan, hope you."),
    Line("otto", "Threatening."),
    Line("lewis", "Exclamation mark."),
    Line("mia", "Hi Joan!"),
    Line("otto", "Now you're her friend."),
    Line("lewis", "Now you're her niece."),
    Line("mia", "'Just.' 'Just following up.' Send?"),
    Line("otto", "One exclamation mark."),
    Line("lewis", "Is that friendly?"),
    Line("otto", "Or a warning?"),
    Line("mia", "Get the string."),
)

SCRIPT = scripting.Script(LINES)
say, first, part, hold = SCRIPT.say, SCRIPT.first, SCRIPT.part, SCRIPT.hold

# what the screen says under each line: the draft moves on a line's first word, a beat behind what is said
DRAFTS = {
    0: ("DRAFT 31", "Hi Joan, hope you're"),
    1: ("DRAFT 31", "Hi Joan, hope you're well."),
    2: ("DRAFT 31", "Hi Joan, hope you're"),
    3: ("DRAFT 32", "Hi Joan, hope you"),
    4: ("DRAFT 32", "Hi Joan, hope you."),
    5: ("DRAFT 33", "Hi Joan, hope"),
    6: ("DRAFT 33", "Hi Joan"),
    7: ("DRAFT 33", "Hi Joan!"),
    8: ("DRAFT 34", "Hi Joan"),
}
SENT = ("DRAFT 212", "Hi Joan, just following up.")
OUT = ("SENT", "Hi Joan, just following up.")
BACK = ("FROM JOAN", "Thanks!")
NOTES = {1: "Dear Joan", 2: "Hi there", 4: "Hello Joan", 5: "Joan,", 7: "Hey!", 8: "Hi Joan,"}
LATE = ("Greetings", "Good day", "Joan?")

BEATS = (
    hold(0.0, "hamster", "", "half", "none", "type"),
    say(0.25, "hamster", 0, "half", "flat", "type"),
    say(2.2, "bear", 1, "half", "flat", "desk"),
    say(3.2, "raccoon", 2, "half", "flat", "desk"),
    say(4.6, "hamster", 3, "half", "flat", "type"),
    say(6.3, "bear", 4, "half", "flat", "desk"),
    say(7.5, "raccoon", 5, "half", "flat", "desk"),
    say(8.9, "hamster", 6, "wide", "grin", "type"),
    say(9.9, "bear", 7, "half", "flat", "desk"),
    say(11.3, "raccoon", 8, "half", "flat", "desk"),
    hold(12.8, "rabbit", "", "half", "none", "type", "six"),
    first(13.6, "rabbit", 9, "'Just.'", "half", "flat", "type"),
    part(14.5, "rabbit", 9, 1, "'Just following up.'", "half", "flat", "type"),
    part(16.0, "rabbit", 9, 4, "Send?", "half", "flat", "type"),
    hold(17.1, "hamster", "", "half", "none", "desk", "send"),  # all three nod, and she presses it
    hold(19.6, "hamster", "", "wide", "none", "desk", "ping"),  # 1.5 s of nobody breathing, after the key
    hold(20.4, "hamster", "", "wide", "none", "desk", "thanks"),
    hold(21.5, "hamster", "", "side", "none", "desk", "lift"),  # 2 s: the glass comes up to the screen
    say(23.6, "sloth", 10, "half", "none", "desk"),
    say(25.5, "raccoon", 11, "half", "flat", "desk"),
    say(26.9, "bear", 12, "half", "flat", "desk"),
    hold(28.3, "hamster", "", "half", "none", "desk", "board"),
    say(30.1, "hamster", 13, "half", "flat", "desk"),
)
SKETCH = Sketch(SLUG, TITLE, (MIA, OTTO, LEWIS), LINES, BEATS, END, tail=1.3)


def validate(sk: Sketch = SKETCH) -> None:
    """The sketch is consistent, speaks by 0.5 s, and every event comes once and in the story's order."""
    sketch.check(sk)
    if next(b for b in sk.beats if b.spoken).start > 0.5:
        raise sketch.SketchError("the first line starts by 0.5 s")
    order = ("six", "send", "ping", "thanks", "lift", "board")
    for kind in order:
        scripting.exactly_once(sk.beats, kind, f"{kind} happens once")
    at = [sketch.events(sk.beats, kind)[0][0] for kind in order]
    if at != sorted(at):
        raise sketch.SketchError(f"the events run in the order {order}")
    scripting.only_events(sk.beats, set(order))


def at(shot, kind: str) -> float:
    return sketch.events(shot.beats, kind)[0][0]


def line_at(beats, line: int) -> float:
    return next(b.start for b in beats if b.line == line)


def drafts(shot) -> tuple[Draft, ...]:
    """The screen's whole run, across the reel, cut to this shot."""
    beats = shot.beats
    times = [(0.0, DRAFTS[0])]
    times += [(line_at(beats, k), DRAFTS[k]) for k in sorted(DRAFTS) if k]
    times += [(at(shot, "six"), SENT), (at(shot, "send"), OUT), (at(shot, "thanks"), BACK)]
    times.append((shot.app.end if shot.app.end > at(shot, "thanks") else times[-1][0] + 1.0, BACK))
    out = []
    for (a, what), (b, _) in zip(times, times[1:], strict=False):
        lo, hi = max(a, shot.app.start), min(b, shot.app.end)
        if lo < hi:
            out.append(Draft(lo, hi, *what))
    return tuple(out)


def _kitchen(shot) -> None:
    """The kitchen, its clock, and the notes piling up on it."""
    cv = shot.cv
    toon_sets.kitchen(cv, shot.back)
    six = at(shot, "six")
    toon_props.clock(cv, shot.back, ((0.0, "02:00"), (six, "06:00")), CLOCK_AT, CLOCK_R)
    notes = [Note(line_at(shot.beats, k), text) for k, text in NOTES.items()]
    notes += [Note(six, text) for text in LATE]
    toon_drafts.stuck_notes(cv, shot.back, notes)


def _mug(cv, parent, x: float) -> None:
    """A mug, smaller than the desk's, so nine stand apart along the ledge."""
    ax, ay = toon.fx(x), toon.fy(838.0)
    g = cv.group(parent, cv.uid("g"), anchorX=ax, anchorY=ay, x=ax, y=ay, scaleX=MUG_SCALE, scaleY=MUG_SCALE)
    toon_props.mug(cv, g, x)


def _desk(shot) -> None:
    """The ledge, the mugs on it, and the screen under its edge until the mark takes over."""
    cv = shot.cv
    toon_house.ledge(cv, shot.front, "oak")
    six = at(shot, "six")
    _mug(cv, shot.front, MUGS[0])
    late = cv.group(shot.front, cv.uid("g"), start=six)
    for x in MUGS[1:]:
        _mug(cv, late, x)
    pages = drafts(shot)
    if pages and shot.app.start < at(shot, "lift") + 0.1:
        toon_drafts.laptop_screen(cv, shot.front, pages)


def _three(shot) -> None:
    """The three of them behind the laptop; the glass comes up on ``lift``, the board in behind them on ``board``."""
    cv, app = shot.cv, shot.app
    _kitchen(shot)
    t = at(shot, "board")
    if app.start >= t or app.end > t:
        toon_drafts.corkboard(cv, shot.back, slide=(t, t + 0.8))

    def acts(speaker: str, listen: Act) -> list[Act]:
        return [
            Act(b.eyes, b.mouth, b.arms) if b.line is not None and LINES[b.line].speaker == speaker else listen
            for b in shot.beats
        ]

    send, flat = at(shot, "send"), Act("half", "flat", "desk")
    for who, seat, speaker, scale in (
        ("bear", OTTO_SEAT, "otto", OTTO_SCALE),
        ("raccoon", LEWIS_SEAT, "lewis", LEWIS_SCALE),
        ("rabbit", MIA_SEAT, "mia", MIA_SCALE),
    ):
        g = toon_pair.figure(shot, shot.back, who, seat, acts(speaker, flat), scale=scale)
        if app.start <= send < app.end:
            y = toon.fy(seat[1])
            nod = [(send + 0.1 + k * 0.17, y + (12.0 if k % 2 else 0.0)) for k in range(5)]
            cv.keys(g, "y", nod, hold=False, local=False)
    _desk(shot)
    lift = at(shot, "lift")
    if app.start <= lift < app.end:
        rise = cv.group(shot.front, cv.uid("g"), start=lift)
        cv.keys(rise, "y", [(lift, toon.fh(RISE)), (lift + 0.9, 0.0)], hold=False, local=False, kind="cubic-out")
        toon_drafts.magnifier(cv, rise, GLASS_AT, 0.9)
        toon_parlour.held(cv, rise, (), ARM_ROOT, FIST, toon_redrawn.BEAR.coat, toon_cast.BEAR.coat, lift, app.end)


def _mark(shot) -> None:
    """The mark, huge, on the white of the screen, seen through the glass."""
    cv = shot.cv
    cv.rect(shot.back, 0, 0, cv.width, cv.height, "#ffffff")
    x, y, r = 280.0, 430.0, 270.0
    toon_drafts.exclaim(cv, shot.front, (x, y), 2 * r - 60.0)
    cv.ellipse(shot.front, toon.fx(x - r), toon.fy(y - r), toon.fh(2 * r), toon.fh(2 * r), cv.clear, "#c9a24d", 34.0)
    toon_house.ledge(cv, shot.front, "oak")


def dress(shot) -> None:
    """The three of them, one of them close, or the mark."""
    if shot.app.who == "hamster":
        _three(shot)
    elif shot.app.who == "sloth":
        _mark(shot)
    else:
        _kitchen(shot)
        _desk(shot)


def tired(cv, app, beats, face) -> None:
    """Six o'clock on her eyes: red in the corners, from ``six`` on."""
    t = sketch.events(beats, "six")[0][0]
    if app.end <= t:
        return
    g = cv.group(face, cv.uid("g"), start=max(app.start, t))
    for x, y in TIRED:
        for k in (-14.0, 0.0, 14.0):
            toon._path(cv, g, toon._d("M", (x + k, y + 14), "L", (x + k * 0.4, y - 2)), None, 3.0, stroke="#d42a2a")


TIRED = ((153.0, 566.0), (222.0, 566.0))


def lens(shot, setup) -> None:
    """Held, but for a push on the mark."""
    camera.anchor(setup, *PIVOT, place=True)
    if shot.app.who == "sloth":
        a = shot.app.start
        camera.push_in(shot.cv, setup, scale=[(a, 1.0), (shot.app.end, 1.06)], hold_scale=True)


def sounds(beats, end) -> list[Sound]:
    """The key she presses, the ping, the glass, and the board on its way in."""
    send = sketch.events(beats, "send")[0][0]
    ping = sketch.events(beats, "ping")[0][0]
    board = sketch.events(beats, "board")[0][0]
    return [
        Sound("key", foley.REMOTE_CLICK, (round(send + 0.9, 3),), -14.0),
        Sound("ping", foley.BELL, (ping,), -12.0),
        Sound("board", foley.SCRAPE, tuple(round(board + k * 0.16, 3) for k in range(5)), -14.0),
    ]
