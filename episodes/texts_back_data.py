"""Texts Back — the sketch as data: a friend who has read every silent man in Mia's life reads the silent recruiter the
same way, and breaks it to her on the sofa.

Mia shoves her phone across the cushion at Dana. Dana sets her mug down, takes it with two fingers and goes through the
evidence: strong candidate, viewed twice, midnight, keep you on file. She puts the phone face down, takes Mia's hand and
tells her he is seeing other candidates. Mia has one thing left to say for him, and Dana has the last line.

Two voices (ElevenLabs premade River as Mia, Jessica as Dana). One sofa in the lounge, two people in the shot
(:func:`srstudio.toon_pair.figure`), the room thrown out of focus behind them. ``ROWS`` act them per beat; :func:`dress`
draws the three framings, :func:`lens` the punch-in, :func:`key` the overlay and :func:`sounds` the room.
"""

from __future__ import annotations

import math

from srstudio import (
    anatomy_ledger,
    foley,
    look,
    scripting,
    sketch,
    toon,
    toon_bed,
    toon_everyday,
    toon_house,
    toon_pair,
    toon_props,
    toon_rooms,
    toon_voices,
    toon_world,
)
from srstudio.anatomy import Side
from srstudio.scripting import at
from srstudio.sketch import Line, Sketch
from srstudio.toon import fh, fx, fy
from srstudio.toon_everyday import Screen
from srstudio.toon_pair import Act
from srstudio.toon_sketch import Sound

MOUTH = toon_voices.MOUTH
SEED = 3408
SLUG = "texts-back"
TITLE = "Texts Back — Mia and Dana (Toon)"
DESCRIPTION = (
    "A Toon sketch on a sofa at night: Mia shows her best friend a recruiter who has gone quiet, and Dana reads him "
    "the way she reads any man who stopped texting."
)
ACCESSIBILITY = (
    "On a sofa in a dim living room a cartoon rabbit shoves her phone along the cushion at a cartoon dog holding a "
    "mug. The dog puts the mug on the arm of the sofa, slowly, and takes the phone with two fingers. She reads, "
    "unmoved, while the rabbit explains what the recruiter said. Her head comes up to ask whether it was at night. She "
    "holds the phone high out of reach as the rabbit grabs for it, then stops, lays it face down on the cushion and "
    "takes the rabbit's hand. She tells her the news gently. The rabbit, in tears, looks at the phone on the cushion. "
    "The dog shakes her head and tells her what she deserves. Lines appear in tinted pills and a bar reads INBOX: "
    "STILL NOTHING."
)
NARRATION = "Voiced with ElevenLabs premade voices River (Mia) and Jessica (Dana)."
NOTE = "ElevenLabs premade voices River and Jessica at their natural pace; no reference-voice cloning."
MIA = toon_voices.speaker("mia", "River", "rabbit")
DANA = toon_voices.speaker("dana", "Jessica", "dog")
TINTS = toon_voices.tinted(MIA, DANA)
TWO, MIA_C, DANA_C = "hamster", "goat", "sloth"  # never seen: the names of the shots the dress draws whole
BARE = (TWO, MIA_C, DANA_C)
RABBIT_COAT, DOG_COAT = "#efe8ee", "#f0a35c"
WHOSE = {RABBIT_COAT: "rabbit", DOG_COAT: "dog"}  # whose arm a swung arm in that coat is
MIA_AT, DANA_AT, PAIR_SCALE = (84.0, 850.0), (258.0, 850.0), 0.66
MIA_CLOSE, DANA_CLOSE = (165.0, 880.0), (235.0, 880.0)
SEAT_Y = 794.0  # the cushion's top, where a phone lies
MUG_SPOT = (394.0, 692.0)  # the mug's base on the arm of the sofa
MUG_REACH = 100.0  # the arm that sets the mug down
HOLD_DEG = 170.0  # the arm that holds the phone up to read
LOW_DEG = 158.0  # the same arm at the cushion, the paw still above it
LYING = 131.0  # where the phone lies on the cushion in Dana's close, under that paw
FLAT_W, FLAT_D = 92.0, 20.0  # a phone lying down, foreshortened
FLAT_BODY, FLAT_BACK, FLAT_LIT = toon_everyday.PHONE_BODY, "#5a5e6b", "#dcebff"
FAR_BLUR = 5.0
PUNCH = 1.14  # the punch-in, about a point that keeps the cactus and the code in frame
PIVOT = (1062.0, 1500.0)
LIGHTS = {"lamp": ((0, "on"),), "tv": ((0, "on", "blue"),)}

LINES = (
    Line("mia", "The recruiter said they'd be in touch."),
    Line("dana", "When?"),
    Line("mia", "Eleven days ago."),
    Line("dana", "Show me."),
    Line("mia", "He called me a strong candidate."),
    Line("dana", "He says that to everyone."),
    Line("mia", "He viewed my profile. Twice."),
    Line("dana", "At night?"),
    Line("mia", "Midnight."),
    Line("dana", "Do not follow up."),
    Line("mia", "He said they'd keep me on file."),
    Line("dana", "Oh, honey. He's seeing other candidates."),
    Line("mia", "But the dental."),
    Line("dana", "You deserve a company that texts back."),
)
script = scripting.Script(LINES)
say, first, part, hold = script.say, script.first, script.part, script.hold
TOP = ("up", "flat", "desk")
SHOVES = Act("left", "flat", "desk")  # Mia is mirrored, so her "left" is at Dana
HOPES = Act("left", "grin", "desk")
PLEADS = Act("wide", "flat", "desk")
SMALL = Act("teary", "flat", "desk")
BLANK = Act("left", "flat", "desk")
READS = Act("half", "flat", "desk")
HEAD_UP = Act("wide", "flat", "desk")
FIRM = Act("narrow", "flat", "desk")
STOPS = Act("half", "flat", "desk")
TENDER = Act("left", "flat", "desk")
ACHES = Act("half", "flat", "desk")

ROWS = (
    (first(0.0, TWO, 0, "The recruiter said", *TOP, "slide"), SHOVES, BLANK),
    (part(0.9, TWO, 0, 3, "they'd be in touch.", *TOP), SHOVES, BLANK),
    (say(2.2, TWO, 1, *TOP), SHOVES, BLANK),  # Dana does not pick it up
    (say(3.1, MIA_C, 2, *TOP), SHOVES, BLANK),
    (say(4.4, DANA_C, 3, *TOP, "mug"), SHOVES, BLANK),  # she has done this before
    (hold(5.1, DANA_C, "Show me.", *TOP, "take"), SHOVES, READS),
    (first(5.8, MIA_C, 4, "He called me", *TOP), HOPES, READS),
    (part(6.65, MIA_C, 4, 3, "a strong candidate.", *TOP), HOPES, READS),
    (say(7.5, DANA_C, 5, *TOP), HOPES, READS),  # without looking up
    (first(9.0, TWO, 6, "He viewed my profile.", *TOP), HOPES, READS),
    (part(10.15, TWO, 6, 4, "Twice.", *TOP), HOPES, READS),
    (say(11.05, DANA_C, 7, *TOP, "punch"), HOPES, HEAD_UP),  # her head comes up
    (say(11.9, MIA_C, 8, *TOP), PLEADS, HEAD_UP),
    (say(12.75, TWO, 9, *TOP, "away"), PLEADS, FIRM),  # out of reach
    (first(14.2, MIA_C, 10, "He said they'd", *TOP), PLEADS, FIRM),
    (part(15.05, MIA_C, 10, 3, "keep me on file.", *TOP), PLEADS, FIRM),
    (hold(15.75, DANA_C, "", *TOP, "down"), PLEADS, STOPS),  # the held silence: the phone goes down, she takes the hand
    (first(17.3, DANA_C, 11, "Oh, honey.", *TOP), PLEADS, TENDER),
    (part(18.2, DANA_C, 11, 2, "He's seeing other candidates.", *TOP), PLEADS, TENDER),
    (hold(19.5, DANA_C, "He's seeing other candidates.", *TOP, "sting"), PLEADS, TENDER),
    (say(20.2, MIA_C, 12, *TOP), SMALL, TENDER),  # a small voice, at the phone on the cushion
    (hold(21.1, TWO, "", *TOP, "shake"), SMALL, ACHES),  # the held silence
    (first(22.4, DANA_C, 13, "You deserve a company", *TOP), SMALL, TENDER),
    (part(23.35, DANA_C, 13, 4, "that texts back.", *TOP), SMALL, TENDER),
)
BEATS = tuple(row[0] for row in ROWS)
ACTS = {"rabbit": tuple(row[1] for row in ROWS), "dog": tuple(row[2] for row in ROWS)}
ONCE = ("slide", "mug", "take", "punch", "away", "down", "sting", "shake")
END = 24.5
SKETCH = Sketch(SLUG, TITLE, (MIA, DANA), LINES, BEATS, END, tail=0.3, bare=BARE)
STING = foley.Burst(0.5, 260.0, attack=0.004, decay=0.55, tone_hz=196.0, tone_end_hz=165.0, tone=0.9)


def validate(sk: Sketch = SKETCH) -> None:
    """The sketch is consistent, speaks by 0.5 s and every event comes once, in the script's order."""
    sketch.check(sk)
    scripting.speaks_by(sk.beats, 0.5)
    scripting.only_events(sk.beats, set(ONCE))
    for kind in ONCE:
        scripting.exactly_once(sk.beats, kind, f"{kind} comes once")
    order = [at(sk.beats, kind) for kind in ONCE]
    if order != sorted(order):
        raise sketch.SketchError("the events run in the script's order")


def key(cv, parent, beats, end, measure) -> None:
    """The overlay: what the inbox says, over the opening, gone before the mug goes down. Never a line's words."""
    toon_house.key_line(cv, parent, "INBOX: STILL NOTHING", 0.2, at(beats, "mug"), measure=measure)


def sounds(beats, end) -> tuple[Sound, ...]:
    """The phone along the cushion, the mug on the arm, the phone put down, the sting after "candidates", the cushion
    in the last silence."""
    return (
        Sound("slide", foley.SCRAPE, (at(beats, "slide") + 0.05,), -10.0),
        Sound("mug", foley.KNOCK, (round(at(beats, "mug") + MUG_DOWN, 3),), -10.0),
        Sound("phone-down", foley.THUD, (round(at(beats, "down") + DOWN_LANDS, 3),), -12.0),
        Sound("sting", STING, (at(beats, "sting"),), -13.0),
        Sound("cushion", foley.SWISH, (round(at(beats, "shake") + 0.1, 3),), -24.0),
    )


MUG_DOWN = 0.7  # seconds the mug takes to reach the arm of the sofa
TAKE_REACH = 0.3  # seconds Dana's hand takes to reach the phone
DOWN_LANDS = 0.55  # seconds the phone takes to reach the cushion after the silence starts
HAND_TAKEN = 1.0  # seconds into the silence when she has Mia's hand


def _tip(shoulder, deg: float, length: float) -> tuple[float, float]:
    """Where an arm of ``length`` from ``shoulder`` at ``deg`` ends (:func:`srstudio.toon_bed.swung_arm`'s angle)."""
    return shoulder[0] + length * math.cos(math.radians(deg)), shoulder[1] + length * math.sin(math.radians(deg))


def _carried(cv, g, shoulder, length: float, swing, offset=(0.0, 0.0), rest=None) -> None:
    """Key the group ``g`` to stay in the hand of the arm that ``swing`` moves, on the arm's own curve; ``rest`` is the
    group's anchor when it has none of its own, for a group drawn in place."""
    x0, y0 = (0.0, 0.0) if rest is None else (fx(rest[0]), fy(rest[1]))
    xs = [(t, round(fx(_tip(shoulder, d, length)[0] + offset[0]) - x0, 2)) for t, d in swing]
    ys = [(t, round(fy(_tip(shoulder, d, length)[1] + offset[1]) - y0, 2)) for t, d in swing]
    cv.keys(g, "x", xs, hold=False, kind="cubic-out", local=False)
    cv.keys(g, "y", ys, hold=False, kind="cubic-out", local=False)


def _flat_phone(cv, parent, x: float, y: float, start: float, end: float, *, lit: bool, slide: float = 0.0, shove=None):
    """A phone lying on a cushion at reference ``x, y``, its screen lit or its back up, from ``start`` to ``end``;
    ``shove`` is ``(from_t, to_t)`` over which it arrives from ``slide`` reference pixels to the left."""
    g = cv.group(parent, cv.uid("g"), start=start, end=end, x=fx(x), y=fy(y))
    near, far = FLAT_W / 2, FLAT_W / 2 - 8
    outline = f"M {fh(-near)} {fh(FLAT_D)} L {fh(near)} {fh(FLAT_D)} L {fh(far)} 0 L {fh(-far)} 0 Z"
    cv.path(g, outline, FLAT_BODY if lit else FLAT_BACK, cv.ink, toon.FINE_W)
    if lit:
        a, b = near - 6, far - 5
        inset = f"M {fh(-a)} {fh(FLAT_D - 4)} L {fh(a)} {fh(FLAT_D - 4)} L {fh(b)} {fh(3)} L {fh(-b)} {fh(3)} Z"
        cv.path(g, inset, FLAT_LIT, cv.clear, 0)
    else:
        cv.ellipse(g, fh(-far + 8), fh(4), fh(8), fh(6), FLAT_BODY)
    if shove is not None:
        a, b = shove
        cv.keys(g, "x", [(a, fx(x - slide)), (b, fx(x))], hold=False, kind="cubic-out", local=False)
    return g


def _mug(cv, parent, spot, scale: float, start: float, end: float):
    """The mug with its base at reference ``spot``: a group the caller may key to move it."""
    rest = 378.0, 838.0  # the middle of toon_props.mug's base, drawn at x=350
    g = cv.group(parent, cv.uid("g"), start=start, end=end, anchorX=fx(rest[0]), anchorY=fy(rest[1]), x=fx(spot[0]),
                 y=fy(spot[1]), scaleX=scale, scaleY=scale)  # fmt: skip
    toon_props.mug(cv, g, 350)
    return g


def _held_phone(cv, parent, spot, scale: float, start: float, end: float, measure, *, tag: str):
    """The phone in Dana's hand, its back to us, her thumb over its edge."""
    rest = 300.0, 820.0  # where it stands at full size: a held phone is smaller than toon_everyday.phone stands
    g = cv.group(parent, cv.uid("g"), start=start, end=end, anchorX=fx(rest[0]), anchorY=fy(rest[1]), x=fx(spot[0]),
                 y=fy(spot[1]), scaleX=scale, scaleY=scale)  # fmt: skip
    toon_everyday.phone(cv, g, (Screen(0.0, "off"),), measure=measure, at=rest, hand=DOG_COAT,
                        id=f"held-{tag}-{start:g}")  # fmt: skip
    return g


def _room(shot) -> None:
    """The lounge out of focus behind the sofa, whose back stays sharp with the people on it."""
    cv = shot.cv
    far = look.depth(cv, shot.back, "texts-back-far", FAR_BLUR, overscan=True)
    light = cv.group(far, cv.uid("g"))
    toon_rooms.stage(cv, far, light, "lounge", LIGHTS, shot.end, blink=False)
    toon_world.sofa_back(cv, shot.back)


def _arm(shot, parent, shoulder, coat, swing, start, end, length, width, side):
    """An arm in the coat of the character whose arm it is, on the frame's ``side`` of that character."""
    with anatomy_ledger.on_arm(WHOSE[coat], side):
        return toon_bed.swung_arm(shot.cv, parent, shoulder, coat, swing, start, end, length=length, width=width)


def _sampled(a: float, b: float, t0: float, t1: float, n: int = 5) -> list[tuple[float, float]]:
    """``n`` keys of a swing from ``a`` to ``b`` degrees over ``t0`` to ``t1``."""
    return [(round(t0 + (t1 - t0) * k / (n - 1), 4), a + (b - a) * k / (n - 1)) for k in range(n)]


def _two(shot) -> None:
    """Both of them on the sofa, each two-shot showing what is true by then."""
    cv, app, beats, measure = shot.cv, shot.app, shot.beats, shot.measure
    slide, take, away, down, shake = (at(beats, k) for k in ("slide", "take", "away", "down", "shake"))
    mia_arm, dana_right, dana_left = (108.0, 760.0), (298.0, 756.0), (219.0, 772.0)
    high = (312.0, 780.0)
    if take <= app.start < down and away < app.end:  # behind her head: the phone held up, out of reach
        swing = _sampled(-58.0, -84.0, away, away + 0.28)
        up = _held_phone(cv, shot.back, _tip(high, -58.0, 220.0), 0.34, app.start, app.end, measure, tag="up")
        _carried(cv, up, high, 220.0, swing, (0.0, 14.0))
        _arm(shot, shot.back, high, DOG_COAT, swing, app.start, app.end, 220.0, 34.0, Side.RIGHT)
    toon_pair.figure(shot, shot.back, "rabbit", MIA_AT, ACTS["rabbit"], scale=PAIR_SCALE, mirror=True)
    dog = toon_pair.figure(shot, shot.back, "dog", DANA_AT, ACTS["dog"], scale=PAIR_SCALE)
    if app.start <= shake < app.end:  # she shakes her head, tender
        rock = [(shake + 0.1 + k * 0.28, (-1) ** k * 2.6) for k in range(1, 4)]
        cv.keys(dog, "rotation", [(shake + 0.1, 0.0), *rock, (shake + 1.1, 0.0)], hold=False, kind="sine-in-out",
                local=False)  # fmt: skip
    if app.start < take:  # the shove, the phone on the cushion, the mug in her hand
        _arm(shot, shot.back, mia_arm, RABBIT_COAT, [(slide, 66.0), (slide + 0.32, 16.0), (slide + 0.9, 16.0),
             (slide + 1.25, 96.0)], app.start, slide + 1.25, 106.0, 40.0, Side.RIGHT)  # fmt: skip
        tip = _tip(dana_right, -30.0, 24.0)
        _mug(cv, shot.back, (tip[0] + 12.0, tip[1] + 10.0), 0.5, app.start, app.end)
        _arm(shot, shot.back, dana_right, DOG_COAT, [(app.start, -30.0)], app.start, app.end, 24.0, 30.0, Side.RIGHT)
    elif app.start < away:  # she has it, low, and reads
        tip = _tip(dana_left, 172.0, 46.0)
        _held_phone(cv, shot.back, (tip[0], tip[1] + 14.0), 0.28, app.start, app.end, measure, tag="low")
        _arm(shot, shot.back, dana_left, DOG_COAT, [(app.start, 172.0)], app.start, app.end, 46.0, 32.0, Side.LEFT)
    elif app.start < down:  # Mia reaches for it
        _arm(shot, shot.back, mia_arm, RABBIT_COAT, [(away + 0.25, 72.0), (away + 0.6, -30.0)], app.start, app.end,
             96.0, 40.0, Side.RIGHT)  # fmt: skip
    else:  # her hand on Mia's, over the phone
        _arm(shot, shot.back, mia_arm, RABBIT_COAT, [(app.start, 15.0)], app.start, app.end, 66.0, 34.0, Side.RIGHT)
        _arm(shot, shot.back, dana_left, DOG_COAT, [(app.start, 176.0)], app.start, app.end, 50.0, 34.0, Side.LEFT)
    toon_world.sofa(cv, shot.front, "rug")
    if app.start < take:
        _flat_phone(cv, shot.front, 252.0, SEAT_Y, app.start, app.end, lit=True, slide=122.0,
                    shove=(slide + 0.05, slide + 0.36))  # fmt: skip
    if app.start >= down:
        _flat_phone(cv, shot.front, 172.0, SEAT_Y + 2, app.start, app.end, lit=False)
    if app.start >= take:
        _mug(cv, shot.front, MUG_SPOT, 0.72, app.start, app.end)


def _mia(shot) -> None:
    """Mia alone, and from the moment it is put down, the phone on the cushion beside her."""
    cv, app, beats = shot.cv, shot.app, shot.beats
    toon_pair.figure(shot, shot.back, "rabbit", MIA_CLOSE, ACTS["rabbit"], scale=1.0, mirror=True)
    toon_world.sofa(cv, shot.front, "rug")
    if app.start >= at(beats, "down"):
        _flat_phone(cv, shot.front, 290.0, SEAT_Y + 2, app.start, app.end, lit=False)


def _dana(shot) -> None:
    """Dana alone: the mug going down and the phone taken; reading; the phone face down and Mia's hand in hers."""
    cv, app, beats, measure = shot.cv, shot.app, shot.beats, shot.measure
    mug, take, down = at(beats, "mug"), at(beats, "take"), at(beats, "down")
    toon_pair.figure(shot, shot.back, "dog", DANA_CLOSE, ACTS["dog"], scale=1.0)
    right, left = (296.0, 738.0), (196.0, 762.0)
    held, reach = 70.0, 140.0
    tip = _tip(left, HOLD_DEG, held)
    hold_at = (tip[0], tip[1] + 16.0)
    lifted = [(take + TAKE_REACH, LOW_DEG), (take + TAKE_REACH + 0.3, HOLD_DEG)]
    set_down = mug + MUG_DOWN
    land = down + DOWN_LANDS
    if app.start < take:  # the hand is drawn over what it holds, so the hand shows in every frame
        lowers = _sampled(-66.0, -35.0, mug, set_down)
        m = _mug(cv, shot.back, MUG_SPOT, 0.72, app.start, set_down)
        _carried(cv, m, right, MUG_REACH, lowers, (16.0, 11.0))  # the mug stands clear of the paw that holds it
        _arm(shot, shot.back, right, DOG_COAT, [*lowers, (set_down + 0.35, 74.0)], app.start, app.end, MUG_REACH,
             46.0, Side.RIGHT)  # fmt: skip
        up = _held_phone(cv, shot.back, hold_at, 0.42, take + TAKE_REACH, app.end, measure, tag="take")
        _carried(cv, up, left, held, lifted, (0.0, 16.0))
        _arm(shot, shot.back, left, DOG_COAT, [(take, 96.0), *lifted], take, app.end, held, 44.0, Side.LEFT)
    elif app.start < down:
        _held_phone(cv, shot.back, hold_at, 0.42, app.start, app.end, measure, tag="read")
        _arm(shot, shot.back, left, DOG_COAT, [(app.start, HOLD_DEG)], app.start, app.end, held, 44.0, Side.LEFT)
    else:
        if app.start <= down:
            carried = _held_phone(cv, shot.back, hold_at, 0.42, app.start, land, measure, tag="down")
            _carried(cv, carried, left, held, [(down, HOLD_DEG), (land, LOW_DEG)], (0.0, 16.0))
            _arm(shot, shot.back, left, DOG_COAT, [(down, HOLD_DEG), (land, LOW_DEG)], app.start, land, held, 44.0,
                 Side.LEFT)  # fmt: skip
        _arm(shot, shot.back, (-60.0, 790.0), RABBIT_COAT, [(down + 0.45, -30.0), (down + HAND_TAKEN - 0.2, -6.0)],
             max(app.start, down + 0.45), app.end, 110.0, 44.0, Side.LEFT)  # fmt: skip
        _arm(shot, shot.back, left, DOG_COAT, [(land, 130.0), (down + HAND_TAKEN, 172.0)], max(app.start, land),
             app.end, reach, 44.0, Side.LEFT)  # fmt: skip
    toon_world.sofa(cv, shot.front, "rug")
    if app.start < take:
        _flat_phone(cv, shot.front, LYING, SEAT_Y + 8, app.start, take + TAKE_REACH, lit=True)
        _mug(cv, shot.front, MUG_SPOT, 0.72, set_down, app.end)
    else:
        _mug(cv, shot.front, MUG_SPOT, 0.72, app.start, app.end)
    if app.start >= down:
        _flat_phone(cv, shot.front, LYING, SEAT_Y + 8, max(app.start, land), app.end, lit=False)


def dress(shot) -> None:
    """The lounge behind, then the two-shot, Mia alone or Dana alone."""
    _room(shot)
    {TWO: _two, MIA_C: _mia, DANA_C: _dana}[shot.app.who](shot)


def lens(shot, setup) -> None:
    """The one punch-in, on Dana's head coming up, held to the cut: it grows the shot about the bottom right, so the
    cactus and the code stay whole in frame."""
    cv, app = shot.cv, shot.app
    t = at(shot.beats, "punch")
    if not app.start <= t < app.end:
        return
    cv.keys(setup, "scaleX", [(0.0, PUNCH)], hold=False, local=False)
    cv.keys(setup, "scaleY", [(0.0, PUNCH)], hold=False, local=False)
    cv.keys(setup, "x", [(0.0, round(PIVOT[0] * (1 - PUNCH), 2))], hold=False, local=False)
    cv.keys(setup, "y", [(0.0, round(PIVOT[1] * (1 - PUNCH), 2))], hold=False, local=False)
