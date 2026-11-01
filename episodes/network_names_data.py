"""Network Names — the sketch as data: Bruno and the neighbor he has never met talk through their Wi-Fi names. Nobody
reads the list out. It ends with the neighbor knowing how the finale ends.

Two voices (ElevenLabs premade Sarah as Mae, Bill as Bruno). It opens on Mae's question over the list, its wheel already
turning (the ``sp-hook_motion`` test's arm B). ``SKETCH`` is checked by :func:`srstudio.sketch.check`;
:func:`validate` checks what the events ask of the props; :func:`dress` draws each shot and :func:`sounds` the room.
"""

from __future__ import annotations

from dataclasses import replace

from srstudio import foley, scripting, sketch, toon, toon_everyday, toon_inserts, toon_rooms, toon_world
from srstudio.sketch import Line, Sketch, Speaker
from srstudio.toon_sketch import Sound
from srstudio.voice import Voice, VoiceSettings

SEED = 3114
SLUG = "network-names"
TITLE = "Network Names — The Neighbor (Toon)"
DESCRIPTION = (
    "A Toon sketch on a sofa at night: a couple and a neighbor they have never met carry on a friendship through "
    "their Wi-Fi network names, until he tells them how the finale ends."
)
ACCESSIBILITY = (
    "A list of Wi-Fi networks on a phone changes to read Bruno Home, Modem 204, Turn It Down. A cartoon rabbit asks"
    " who that is. On the sofa with the TV on, a cartoon bear says it is the neighbor he has never met. The list "
    "changes to I Know Its You Bruno. The bear types and his network becomes Sorry. The neighbor's becomes Its OK, "
    "Rough Week. They like him. The bear types On The Finale and they settle in, she leans on his shoulder, music "
    "swells. The list changes to Great Show, The Sister Did It. The music stops. Neither moves. Slowly, both look at "
    "the wall."
)
NARRATION = "Voiced with ElevenLabs premade voices Sarah (Mae) and Bill (Bruno); synthesized effects."
NOTE = "ElevenLabs premade voices Sarah and Bill at their natural pace; no reference-voice cloning."
RABBIT = Speaker(
    "rabbit",
    Voice(role="rabbit", id="EXAVITQu4vr4xnSDxMaL", name="Sarah"),
    VoiceSettings(stability=0.5, similarity_boost=0.75, style=0.25),
    "rabbit",
)
BEAR = Speaker(
    "bear",
    Voice(role="bear", id="pqHfZKP75CvOlQylNhV4", name="Bill"),
    VoiceSettings(stability=0.55, similarity_boost=0.75, style=0.2),
    "bear",
)
WIDE = "hamster"  # never seen: the name of the shots the dress draws whole
TINTS = {"rabbit": "#f4dde6", "bear": "#ead2b8", WIDE: "#ffffff"}
MOUTH = replace(sketch.MOUTH_STYLE, spelling=True, close_bilabials=True, lead=0.04, min_rest=0.12)

FIGURES = {"bear": (0.8, -55.0), "rabbit": (0.8, 130.0)}
SEAT = (165.0, 840.0)
CLOSER = 1.08  # how much bigger the last shot holds them
LEAN = (-14.0, -7.0)  # sideways and degrees: her head on his shoulder
SETTLE = 1.2  # seconds it takes her
PHONE = {"at": (296, 776), "scale": 1.5}
INSERT = "#3a2c4e"  # the sofa's plum, dark, behind the phone when the shot cuts to it
INSERT_CODE = "#e8dff0"
SCREEN = "#10202c"
DRIFT = 1.04
TOP = 308.0  # the list clears the caption above and the marks below
THE_LIST = {"mine": "BRUNO-HOME", "other": "MODEM-204", "his": "TURN IT DOWN"}
MURMUR = 8.0  # seconds of the TV in one stretch, the longest one burst lasts
END = 34.62

LINES = (
    Line("rabbit", "Who's Turn It Down?"),
    Line("bear", "Next door. He means the TV."),
    Line("rabbit", "You've talked to him?"),
    Line("bear", "Never met him. He doesn't know it's us."),
    Line("rabbit", "Bruno."),
    Line("bear", "Buddy."),
    Line("rabbit", "That's sweet."),
    Line("bear", "He's a nice guy."),
    Line("rabbit", "Tell him we're on the finale."),
)

script = scripting.Script(LINES)
hold, say, first, part = script.hold, script.say, script.first, script.part

BEATS = (
    say(0.0, WIDE, 0, "wide", "flat", "desk"),  # the list, already moving
    say(1.51, "bear", 1, "half", "flat", "desk"),
    say(3.74, "rabbit", 2, "wide", "o", "desk"),
    first(5.29, "bear", 3, "Never met him.", "half", "flat", "desk"),
    part(6.49, "bear", 3, 3, "He doesn't know it's us.", "half", "grin", "desk"),
    hold(9.04, WIDE, "", "wide", "flat", "desk", "accused"),  # the list refreshes, held to read
    say(11.44, "rabbit", 4, "wide", "flat", "desk"),
    hold(12.37, "bear", "", "down", "flat", "desk", "typed"),  # one thick finger
    hold(13.97, WIDE, "", "wide", "flat", "desk", "sorry"),
    hold(15.47, WIDE, "", "wide", "flat", "desk", "forgiven"),
    say(17.77, "bear", 5, "teary", "grin", "desk"),
    say(18.46, "rabbit", 6, "half", "grin", "desk"),
    say(19.81, "bear", 7, "half", "grin", "desk"),
    say(21.16, "rabbit", 8, "half", "grin", "desk"),
    hold(23.02, "bear", "", "down", "flat", "desk", "typed-again"),
    hold(24.22, WIDE, "", "wide", "flat", "desk", "finale"),
    hold(25.62, "bear", "", "half", "grin", "desk", "settle"),  # she leans on him, the music comes up
    hold(28.22, WIDE, "", "wide", "flat", "desk", "spoiled"),
    hold(30.22, WIDE, "", "wide", "flat", "desk", "close"),  # the music stops
    hold(31.42, WIDE, "", "wide", "flat", "desk", "wall"),
)
SKETCH = Sketch(SLUG, TITLE, (RABBIT, BEAR), LINES, BEATS, END, bare=(WIDE,))
ORDER = ("accused", "typed", "sorry", "forgiven", "typed-again", "finale", "settle", "spoiled", "close", "wall")


def validate(sk: Sketch = SKETCH) -> None:
    """The sketch is consistent, speaks within 0.3 s, and the list's steps come once each and in order."""
    sketch.check(sk)
    if sk.beats[0].line != 0 or sk.beats[0].start > 0.3:
        raise sketch.SketchError("the sketch's first line is spoken within 0.3 s")
    for event in ORDER:
        scripting.exactly_once(sk.beats, event, f"{event} happens once")
    times = [sketch.events(sk.beats, event)[0][0] for event in ORDER]
    if times != sorted(times):
        raise sketch.SketchError(f"the events run {ORDER}")
    scripting.only_events(sk.beats, set(ORDER))


def at(shot, event: str) -> float:
    return sketch.events(shot.beats, event)[0][0]


def states(shot) -> tuple[tuple[float, tuple[str, str, str]], ...]:
    """Three names, one of them changing at each step: his, and the neighbor's."""
    his, other = THE_LIST["mine"], THE_LIST["other"]
    return (
        (0.0, (his, other, THE_LIST["his"])),
        (at(shot, "accused"), (his, other, "I KNOW ITS YOU BRUNO")),
        (at(shot, "sorry"), ("SORRY", other, "I KNOW ITS YOU BRUNO")),
        (at(shot, "forgiven"), ("SORRY", other, "ITS OK. ROUGH WEEK?")),
        (at(shot, "finale"), ("ON THE FINALE", other, "ITS OK. ROUGH WEEK?")),
        (at(shot, "spoiled"), ("ON THE FINALE", other, "GREAT SHOW. THE SISTER DID IT.")),
    )


def lights(shot) -> dict:
    """The lamp stays on and the TV plays on, whatever happens."""
    return {"lamp": ((0, "on"),), "tv": ((0, "flicker", "blue"),)}


def still(who: str, eyes: str, mouth: str):
    return toon.parse_poses([{"start": 0.0, "eyes": eyes, "mouth": mouth, "arms": "desk"}], f"{who} on the sofa")


def beside(shot, who: str, poses, scale: float, dx: float, parent=None):
    """``who`` on the sofa, off the camera's mind: drawn at the same seat they speak from."""

    def draw(g) -> None:
        sketch.drawer(who, shot.versions)(shot.cv, g, poses, shot.app.end, (), enter=shot.app.start)

    return toon_world.placed(shot.cv, parent or shot.back, (SEAT[0] + dx, SEAT[1]), scale, draw, pivot=SEAT)


def listening(shot, who: str) -> tuple[str, str]:
    """The other one's face: frozen from the accusation until he has apologized, pleased after."""
    if at(shot, "accused") <= shot.app.start < at(shot, "forgiven"):
        return ("wide", "flat")
    return ("half", "grin") if shot.app.start > at(shot, "forgiven") else ("half", "flat")


def typing(shot, start: float, stop: float, screen: str) -> None:
    """The insert: his phone, whole frame, for as long as he types."""
    cv = shot.cv
    g = cv.group(shot.front, cv.uid("g"), start=start, end=stop)
    cv.rect(g, 0, 0, cv.width, cv.height, INSERT, cv.clear, 0, radius=0)
    toon_world.marks(cv, g, code=INSERT_CODE)
    toon_everyday.phone(
        shot.cv,
        g,
        [toon_everyday.Screen(0.0, "code", "Wi-Fi name", screen)],
        measure=shot.measure,
        id=shot.cv.uid("phone"),
        **PHONE,
    )


def sofa(shot) -> None:
    """The two of them on the sofa, the one who is not speaking beside the one who is."""
    app = shot.app
    toon_rooms.dress(shot, "lounge", lights(shot))
    other = "rabbit" if app.who == "bear" else "bear"
    scale, dx = FIGURES[other]
    settle = at(shot, "settle")
    leaning = app.start <= settle < app.end
    parent = shot.front if leaning else shot.back
    g = beside(shot, other, still(other, *listening(shot, other)), scale, dx, parent)
    toon_world.sofa(shot.cv, shot.front)
    if leaning:
        x = g.x
        shot.cv.keys(g, "x", [(settle, x), (settle + SETTLE, x + toon.fh(LEAN[0]))], kind="sine-in-out", local=False)
        shot.cv.keys(g, "rotation", [(settle, 0.0), (settle + SETTLE, LEAN[1])], kind="sine-in-out", local=False)
    for event, screen in (("typed", "SORRY"), ("typed-again", "ON THE")):
        if app.who == "bear" and app.start <= at(shot, event) < app.end:
            typing(shot, at(shot, event), app.end, screen)


def wall(shot) -> None:
    """Both of them, closer. Nothing moves, then their eyes go to the wall, his first."""
    start = at(shot, "close")
    turn = at(shot, "wall")
    cv = shot.cv
    back, front = cv.group(shot.back, cv.uid("g"), start=start), cv.group(shot.front, cv.uid("g"), start=start)
    toon_rooms.dress(replace(shot, back=back, front=front), "lounge", lights(shot))
    for who, late in (("bear", 0.0), ("rabbit", 0.5)):
        poses = toon.parse_poses(
            [
                {"start": 0.0, "eyes": "wide", "mouth": "flat", "arms": "desk"},
                {"start": turn + late - shot.app.start, "eyes": "left", "mouth": "flat", "arms": "desk"},
            ],
            f"{who} and the wall",
        )
        scale, dx = FIGURES[who]
        g = beside(replace(shot, back=back), who, poses, scale * CLOSER, dx * CLOSER, front)
        if who == "rabbit":  # she has not moved
            g.x += toon.fh(LEAN[0] * CLOSER)
            cv.keys(g, "rotation", [(0.0, LEAN[1])], local=False)
    toon_world.sofa(cv, front)


def insert(shot, stop: float) -> None:
    """The list over everything: a phone's dark, the names and the marks."""
    cv = shot.cv
    cx, cy = toon.fx(296.0), toon.fy(560.0)
    g = cv.group(shot.front, cv.uid("g"), end=stop, x=cx, y=cy, anchorX=cx, anchorY=cy)
    if shot.app.start == 0:  # the opening moves: the list drifts in as the name changes under her question
        for prop in ("scaleX", "scaleY"):
            cv.keys(g, prop, [(0.0, 1.0), (stop, DRIFT)], hold=False, local=False)
    cv.rect(g, toon.fx(-10), toon.fy(-140), toon.fh(612), toon.fh(1300), SCREEN, cv.clear, 0, radius=0)
    toon_inserts.wifi_list(cv, g, [s for s in states(shot) if s[0] < stop], end=stop, top=TOP)
    toon_world.marks(cv, g)


def dress(shot) -> None:
    """The sofa, or the list; and the list runs straight into the last shot when it is the last."""
    app = shot.app
    if app.who != WIDE:
        sofa(shot)
        return
    final = app.start <= at(shot, "close") < app.end
    if final:
        wall(shot)
    insert(shot, at(shot, "close") if final else app.end)


def sounds(beats, end) -> tuple[Sound, ...]:
    """The TV through it all, his thumb, the sting of being known, and the music, which stops dead on the cut."""
    accused = sketch.events(beats, "accused")[0][0]
    typed = [sketch.events(beats, e)[0][0] + d for e in ("typed", "typed-again") for d in (0.3, 0.6, 0.85, 1.0)]
    settle = sketch.events(beats, "settle")[0][0]
    close = sketch.events(beats, "close")[0][0]
    length = close - settle
    sound = {"attack": length * 0.6, "decay": 12.0, "flutter_hz": 5.0}
    low = foley.Burst(length, 400.0, tone_hz=147.0, tone_end_hz=196.0, tone=0.9, **sound)
    high = foley.Burst(length, 800.0, tone_hz=294.0, tone_end_hz=392.0, tone=0.9, **sound)
    starts = tuple(k * MURMUR for k in range(int(close // MURMUR)))
    tail = close - len(starts) * MURMUR
    return (
        Sound("tv", foley.Burst(MURMUR, 900.0, attack=0.05, decay=40.0, flutter_hz=9.0), starts, -10.0),
        Sound("tv-end", foley.Burst(tail, 900.0, attack=0.05, decay=40.0, flutter_hz=9.0), (close - tail,), -10.0),
        Sound("sting", foley.THUD, (accused,), 0.0),
        Sound("thumb", foley.REMOTE_CLICK, tuple(typed), -8.0),
        Sound("tv-low", low, (settle,), -6.0),
        Sound("tv-high", high, (settle,), -10.0),
    )
