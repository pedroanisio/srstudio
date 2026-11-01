"""Someone Else — the sketch as data: canceling your internet is a breakup. The agent takes it as one, and the fair
price only appears when you threaten to leave. The caller stays, the line goes dead, the heartbreak stops, and two eye
drops later the phone rings. Then the room: every agent on the floor tipping their head back.

Two voices (ElevenLabs premade Sarah as the caller, River as the agent). It opens on her with the phone, waiting, the
shot drifting in as her eyes go round the room. ``SKETCH`` is checked by :func:`srstudio.sketch.check`; :func:`validate`
checks what the events ask of the props; :func:`dress` draws each shot and :func:`sounds` the phone.
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
    toon_everyday,
    toon_house,
    toon_inserts,
    toon_sets,
    toon_world,
)
from srstudio.sketch import Line, Sketch, Speaker
from srstudio.toon_sketch import Sound
from srstudio.voice import Voice, VoiceSettings

SEED = 3107
SLUG = "someone-else"
TITLE = "Someone Else — Canceling the Internet (Toon)"
DESCRIPTION = (
    "A Toon sketch on a call: a woman cancels her internet and the agent takes it as a breakup, until forty percent "
    "off keeps her, the agent stops crying, and the whole floor picks up."
)
ACCESSIBILITY = (
    "A cartoon rabbit on the phone at home asks to cancel her internet. A cartoon hedgehog in a headset fills with "
    "tears and asks if there is someone else. They argue like a couple until the hedgehog whispers forty percent off "
    "and the rabbit stays. The call ends, the hedgehog's face goes flat, she ticks a form, squeezes eye drops into "
    "her eyes and the phone rings. The camera pulls back on rows of agents all doing the same, and all answer."
)
NARRATION = "Voiced with ElevenLabs premade voices Sarah (the caller) and River (the agent); synthesized effects."
NOTE = "ElevenLabs premade voices Sarah and River at their natural pace; no reference-voice cloning."
VOICE_AGENT = Voice(role="hedgehog", id="SAz9YHcvj6GT2YYXdXww", name="River")
RABBIT = Speaker(
    "rabbit",
    Voice(role="rabbit", id="EXAVITQu4vr4xnSDxMaL", name="Sarah"),
    VoiceSettings(stability=0.55, similarity_boost=0.75, style=0.2),
    "rabbit",
)
HEDGEHOG = Speaker("hedgehog", VOICE_AGENT, VoiceSettings(stability=0.3, similarity_boost=0.75, style=0.6), "hedgehog")
# The whisper, and the floor answering: played through a fixed mouth.
LOW = Speaker("hedgehog-low", VOICE_AGENT, VoiceSettings(stability=0.85, similarity_boost=0.75, style=0.0))
FLOOR = Speaker("floor", VOICE_AGENT, VoiceSettings(stability=0.3, similarity_boost=0.75, style=0.6))
TINTS = {
    "rabbit": "#ffd9e3",
    "hedgehog": "#e6e0d0",
    "hedgehog-low": "#e6e0d0",
    "floor": "#e6e0d0",
    "hamster": "#ffffff",
}
MOUTH = replace(sketch.MOUTH_STYLE, spelling=True, close_bilabials=True, lead=0.04, min_rest=0.12)

STILL = 1.2  # seconds she waits before she speaks
DRIFT = 1.05  # the opening drifts in this far
LOOKS = (0.0, "side"), (0.4, "half"), (0.8, "side")  # seconds, eyes: she waits, and goes on waiting
PIVOT = (900.0, 900.0)  # at the signature, which the drift keeps in frame
WIDE = "hamster"  # never seen: the name of the shots the dress draws whole
FIGURES: dict[str, tuple[float, float]] = {"rabbit": (1.1, 0.0), "hedgehog": (1.1, 0.0)}
STICKERS = {"hedgehog": toon_cast.headset(toon_cast.HEDGEHOG)}
PHONE = {"at": (450.0, 814.0), "scale": 0.9}  # stood on her desk, on speaker
BOARD = {"at": (424, 816), "scale": 1.1}  # stood on the agent's desk
EYE = (215.0, 558.0)  # where the drops land, her eye on the left
DROPS_HELD = 1.5  # the seconds the bottle is at her eye
CLOSE_ZOOM, CLOSE_SHIFT = 2.0, (120.0, 438.0)  # the frame on her face for those, its shift off the eye in pixels
END = 34.35
ROWS = (  # the floor, far row first: (reference height, scale, who, from left to right)
    (520.0, 0.3, ("dog", "hedgehog", "frog", "bear", "raccoon")),
    (680.0, 0.4, ("fox", "bear", "dog", "raccoon")),
    (860.0, 0.56, ("frog", "hedgehog", "raccoon")),
)
PULL = (1.5, 1.0)  # the wide's scale, at the start and the end of its pull back
DRIP = (0.5, 1.0)  # seconds into the drops, one for each eye
PLIP = foley.Burst(0.09, 1400.0, attack=0.002, decay=0.2, tone_hz=1900.0, tone_end_hz=700.0, tone=0.9)
RING = foley.Burst(0.9, 300.0, attack=0.01, decay=0.5, tone_hz=880.0, tone_end_hz=880.0, tone=0.8, flutter_hz=20.0)

LINES = (
    Line("rabbit", "Hi. I'd like to cancel my internet."),
    Line("hedgehog", "Is there someone else?"),
    Line("rabbit", "What?"),
    Line("hedgehog", "Is it fiber? It's fiber, isn't it."),
    Line("rabbit", "It's just cheaper."),
    Line("hedgehog", "Eleven years. I gave you everything."),
    Line("rabbit", "You drop out every night."),
    Line("hedgehog", "I can change!"),
    Line("rabbit", "You said that last year."),
    Line("hedgehog-low", "Forty percent off."),
    Line("rabbit", "Forty?"),
    Line("hedgehog", "And the sports channels."),
    Line("rabbit", "Okay. I'll stay."),
    Line("hedgehog", "Thank you."),
    Line("floor", "Is there someone else?"),
)

script = scripting.Script(LINES)
hold, say = script.hold, script.say

BEATS = (
    hold(0.0, WIDE, "", "side", "flat", "desk"),  # she waits on the line
    say(1.2, "rabbit", 0, "half", "flat", "desk"),
    hold(3.65, "hedgehog", "", "wide", "flat", "desk"),  # dead air
    hold(4.65, "hedgehog", "", "teary", "frown", "desk"),  # her eyes fill
    say(5.45, "hedgehog", 1, "teary", "frown", "desk"),
    say(6.96, "rabbit", 2, "wide", "o", "desk"),
    say(7.64, "hedgehog", 3, "teary", "frown", "desk"),
    say(9.68, "rabbit", 4, "half", "flat", "desk"),
    say(11.18, "hedgehog", 5, "teary", "frown", "desk"),
    say(13.38, "rabbit", 6, "narrow", "flat", "desk"),
    say(14.99, "hedgehog", 7, "shock", "open", "desk"),
    say(16.09, "rabbit", 8, "narrow", "flat", "desk"),
    hold(17.98, "hedgehog", "", "teary", "frown", "desk"),  # she breathes in, wet
    say(19.18, "hedgehog", 9, "teary", "flat", "desk"),
    say(20.41, "rabbit", 10, "wide", "o", "desk"),
    say(21.22, "hedgehog", 11, "teary", "frown", "desk"),
    say(22.65, "rabbit", 12, "half", "grin", "desk"),
    say(23.99, "hedgehog", 13, "teary", "frown", "desk"),
    hold(24.79, "hedgehog", "", "half", "flat", "desk", "click"),  # the line dies, and the face
    hold(25.59, "hedgehog", "", "down", "flat", "desk", "tick"),
    hold(26.49, "hedgehog", "", "up", "flat", "desk", "drops"),
    hold(28.39, "hedgehog", "", "half", "flat", "desk", "ring"),
    hold(29.09, WIDE, "", "wide", "flat", "desk", "pull"),
    say(32.09, WIDE, 14, "wide", "open", "desk"),
)
SKETCH = Sketch(SLUG, TITLE, (RABBIT, HEDGEHOG, LOW, FLOOR), LINES, BEATS, END, bare=(WIDE,))


def validate(sk: Sketch = SKETCH) -> None:
    """The sketch is consistent, opens on a silent uncaptioned shot of at least 1 s, and its last five things happen
    once and in order: the line dies, she ticks, the drops, the ring, and the pull back."""
    sketch.check(sk)
    opening = sk.beats[0]
    if opening.line is not None or opening.caption or sk.beats[1].start < 1.0:
        raise sketch.SketchError("the sketch opens on a silent, uncaptioned shot of at least 1 s")
    order = ("click", "tick", "drops", "ring", "pull")
    for event in order:
        scripting.exactly_once(sk.beats, event, f"{event} happens once")
    times = [sketch.events(sk.beats, event)[0][0] for event in order]
    if times != sorted(times):
        raise sketch.SketchError(f"the events run {order}")
    scripting.only_events(sk.beats, set(order))
    if next(b for b in sk.beats if b.event == "pull").who != WIDE:
        raise sketch.SketchError("the pull back is a wide")


def _phone(shot) -> None:
    screen = toon_everyday.Screen(0.0, "off")
    toon_everyday.phone(shot.cv, shot.front, [screen], measure=shot.measure, id=shot.cv.uid("phone"), **PHONE)


def home(shot) -> None:
    """The caller at home, the phone on her desk."""
    toon_sets.home(shot.cv, shot.back, end=shot.end)
    toon_house.ledge(shot.cv, shot.front)
    _phone(shot)


def opening(shot) -> None:
    """The first frames: the same room and the same rabbit, waiting; her eyes go round it (:func:`lens` drifts in)."""
    cv, app = shot.cv, shot.app
    toon_sets.home(cv, shot.back)
    toon_house.ledge(cv, shot.front)
    keys = [{"start": at, "eyes": eyes, "mouth": "flat", "arms": "desk"} for at, eyes in LOOKS]
    poses = toon.parse_poses(keys, "the opening")

    def draw(g) -> None:
        sketch.drawer("rabbit", shot.versions)(cv, g, poses, app.end, (), enter=app.start)

    toon_world.placed(cv, shot.back, (165.0, 840.0), FIGURES["rabbit"][0], draw, pivot=(165.0, 840.0))
    _phone(shot)


def agent(shot, who: str, group, at, scale: float, speaks: float) -> None:
    """One agent in a row, already crying, who picks up crying."""
    cv = shot.cv
    poses = toon.parse_poses(
        [
            {"start": 0.0, "eyes": "teary", "mouth": "frown", "arms": "desk"},
            {"start": max(0.0, speaks - shot.app.start), "eyes": "teary", "mouth": "open", "arms": "desk"},
        ],
        f"{who} on the floor",
    )
    stuck = sketch.drawer_extras(who, {who: toon_cast.headset(getattr(toon_cast, who.upper()))})

    def draw(g) -> None:
        sketch.drawer(who, shot.versions)(cv, g, poses, shot.app.end, (), enter=shot.app.start, **stuck)

    toon_world.placed(cv, group, at, scale, draw)


def floor(shot) -> None:
    """The floor: rows of low cubicles, every agent in tears with the bottle stood on the desk between them. The room
    starts close on the middle of the front row and draws back to all of it; the last line is the whole floor picking
    up."""
    cv, app = shot.cv, shot.app
    speaks = next(b.start for b in shot.beats if b.line == len(LINES) - 1)
    toon_sets.call_centre(cv, shot.back, ((0.0, 99),), end=shot.end, legible=True)
    room = cv.group(shot.front, cv.uid("g"))
    camera.anchor(room, toon.fx(296.0), toon.fy(800.0), place=True)
    cv.keys(room, "scaleX", [(app.start, PULL[0]), (speaks, PULL[1])], kind="sine-in-out", local=False)
    cv.keys(room, "scaleY", [(app.start, PULL[0]), (speaks, PULL[1])], kind="sine-in-out", local=False)
    for k, (y, scale, row) in enumerate(ROWS):
        step = 592.0 / len(row)
        for n, who in enumerate(row):
            agent(shot, who, room, (step * (n + 0.5) - 20.0, y), scale, speaks)
        last = k == len(ROWS) - 1
        if not last:
            cv.rect(
                room, toon.fx(-90), toon.fy(y - 6), toon.fh(770), toon.fh(40), "#6a84a8", cv.ink, toon.FINE_W, radius=0
            )
        for n in range(1, len(row)):  # between two agents, where it covers neither
            toon_inserts.standing_drops(cv, room, (step * n - 20.0, 806.0 if last else y - 2.0), scale)
    toon_house.ledge(cv, shot.front)  # the front row's own desk, with the marks


def dress(shot) -> None:
    """Who is on screen says where we are; the agent's shots carry the form she ticks and the drops."""
    cv, app = shot.cv, shot.app
    if app.who == WIDE:
        floor(shot) if app.start > 0 else opening(shot)
    elif app.who == "rabbit":
        home(shot)
    else:
        toon_sets.call_centre(cv, shot.back, ((0.0, 37),), end=shot.end, legible=True)
        toon_house.ledge(cv, shot.front)
        ticks = sketch.events(shot.beats, "tick")
        fields = [toon_everyday.Field("Kept", "YES", ticks[0][0])]
        toon_everyday.clipboard(cv, shot.front, "CALL 4,812", fields, measure=shot.measure, id=cv.uid("board"), **BOARD)
        drops = [at for at, _ in sketch.events(shot.beats, "drops") if app.start <= at < app.end]
        if drops:
            d = drops[0]
            squeezes = [d + at for at in DRIP]
            toon_inserts.eye_drops(
                cv,
                shot.front,
                EYE,
                start=d,
                squeezes=squeezes,
                leave=d + DROPS_HELD,
                scale=0.7,
                arm=toon_cast.HEDGEHOG.coat,
            )


def lens(shot, setup) -> None:
    """The opening drifts in on her; every other shot holds its frame."""
    cv, app = shot.cv, shot.app
    if app.start == 0:
        camera.anchor(setup, *PIVOT, place=True)
        camera.push_in(cv, setup, scale=[(0.0, 1.0), (app.end, DRIFT)])
    for at in (at for at, _ in sketch.events(shot.beats, "drops") if app.start <= at < app.end):
        # close enough on the face that her paws on the desk are out of frame, and the arm with the bottle is hers
        x, y = toon.fx(EYE[0]), toon.fy(EYE[1])
        camera.anchor(setup, x, y, place=True)
        out = at + DROPS_HELD
        cv.keys(setup, "x", [(app.start, x), (at, x + CLOSE_SHIFT[0]), (out, x)], local=False)
        cv.keys(setup, "y", [(app.start, y), (at, y + CLOSE_SHIFT[1]), (out, y)], local=False)
        cv.keys(setup, "scaleX", [(app.start, 1.0), (at, CLOSE_ZOOM), (out, 1.0)], local=False)
        cv.keys(setup, "scaleY", [(app.start, 1.0), (at, CLOSE_ZOOM), (out, 1.0)], local=False)


def sounds(beats, end) -> tuple[Sound, ...]:
    """The line dying, and the ring, close and then from all over the floor."""
    click = sketch.events(beats, "click")[0][0]
    ring = sketch.events(beats, "ring")[0][0]
    pull = sketch.events(beats, "pull")[0][0]
    rings = (ring, *(pull + 0.35 * k for k in range(1, 7)))
    tick = sketch.events(beats, "tick")[0][0]
    drops = sketch.events(beats, "drops")[0][0]
    return (
        Sound("click", foley.REMOTE_CLICK, (click,), -6.0),
        Sound("tick", foley.SCRAPE, (tick,), -8.0),
        Sound("plip", PLIP, tuple(drops + at for at in DRIP), -4.0),
        Sound("ring", RING, rings, -10.0),
    )
