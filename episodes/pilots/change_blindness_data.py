"""Change Blindness — a pilot of "There's a Name for That", main trigger challenge: the sketch as data.

"I notice everything." A fox in her hall tells a sloth what the neighbours are up to, and while she talks the front
door behind them turns from teal to red over twelve seconds. Nothing gets past her. The door rewinds and runs again,
sped up, and she says it has been red for years. Then two neighbours carry the old door through, the sloth comes out
from behind it a bear, and she carries on: he changed his shampoo back, and it's much better. The reel cuts back to its
first frame, with the door teal, so a second watch can catch what the first did not.

The viewer takes part, and sends this to whoever they want to try it on, or to the neighbour who sees everything. The
talking scene is the reel: the fox's gossip is what holds the eye, and the reveal is the last third. Text on screen
carries every key point, for a muted viewer. The narrator is the channel's voice, ElevenLabs premade Bella; the fox is
ElevenLabs premade Alice. ``SKETCH`` is checked by :func:`srstudio.sketch.check`; :func:`validate` checks the events
and every word on screen against :func:`srstudio.mind_kit.check_copy`; :func:`dress` draws each shot and :func:`foley`
its sound.

:func:`door_keys` is the change: one opacity ramp of a repainted door over the door the hall is drawn with, the same
shapes in the same place, so every frame is a plain mix of two opaque colours and nothing shows through. It takes
:data:`CHANGE` seconds, and it is one ramp, so it cannot flicker. Every claim traces to
``pilots/mind/change-blindness/sources.md``: the stamps are its two, both abstract-level, and the link to the study
is its safe wording, so no line says a study tested a door, a drawing, a hall or a talking fox, and none says how many
viewers miss this one.
"""

from __future__ import annotations

from dataclasses import replace

from srstudio import camera, mind_kit, scripting, sketch, toon, toon_house
from srstudio import foley as synth
from srstudio.sketch import Line, Sketch, Speaker
from srstudio.social import InstagramPost
from srstudio.thumbnail import Thumbnail
from srstudio.toon_house import DOOR_BOX, DOOR_LEAF, DOOR_PANEL
from srstudio.toon_sketch import figure_group
from srstudio.voice import Voice, VoiceSettings

SEED = 3106
SLUG = "change-blindness"
OUTPUT = f"renders/pilots/{SLUG}.mp4"
TITLE = "Change Blindness — There's a Name for That"
NAME = "Change Blindness"
PAD = "Noticed"
DESCRIPTION = (
    "A pilot about how people think: the viewer is challenged to catch what changes in a room while a fox talks, and "
    "the effect behind missing it is shown, tied to two studies and tried on the fox."
)
ACCESSIBILITY = (
    "A cartoon fox in a hall tells a sloth what her neighbours are up to, and says nothing gets past her. Behind them "
    "the teal front door slowly turns red. The door runs back to teal and on to red, sped up, and she says it has "
    "been red for years. Two neighbours carry a teal door through, and from behind it the sloth comes out a bear. She "
    "tells the bear he changed his shampoo back and it's much better. The first frame comes back, the door teal."
)
NARRATION = "Voiced with ElevenLabs premade voices Bella (narrator) and Alice; synthesised effects."
NOTE = "ElevenLabs premade voices Bella and Alice at their natural pace; no reference-voice cloning."

CHANGE = 12.0  # seconds: the only duration the sources document (Simons & Rensink 2005, p. 19), over 8 s in the brief
FPS = 30.0
SLOW = (("Large, slow changes can go unnoticed.",), "Simons et al., 2000")  # sources.md, stamp for the gradual change
SWAP = (("A stranger swapped mid-chat.", "Only half noticed."), "Simons & Levin, 1998")  # sources.md, the door study

NARRATOR = mind_kit.NARRATOR
NELL = Speaker(
    "nell",
    Voice(role="nell", id="Xb7hH8MSUJpSbSDYk0k2", name="Alice"),
    VoiceSettings(stability=0.40, similarity_boost=0.75, style=0.45),
    "fox",
)
TINTS = {"nell": mind_kit.SPOT, "narrator": mind_kit.INK}
MOUTH = replace(sketch.MOUTH_STYLE, spelling=True, close_bilabials=True, lead=0.04, min_rest=0.12)
VERSIONS = {"toon-fox": 2, "toon-sloth": 1, "toon-bear": 2, "toon-rabbit": 2, "toon-raccoon": 2}
FIGURES = {"fox": (1.0, -40.0)}
LISTENER = (0.86, 262.0)  # his framing, as FIGURES: he stands in front of the foot of the door, its top half clear
CARRIER = 0.8

RED_LEAF, RED_PANEL = "#b4423f", "#cf5a52"  # as dark as the teal they replace: the hue moves, the brightness does not
REPLAY = 1.3  # seconds of the rewind and the sped-up run at the reveal
DOOR_W, DOOR_H = 560.0, 1180.0  # the carried door, frame pixels: wider than the listener, so it hides him whole
CARRY = 2.0  # seconds it takes to cross
PUSH, PUNCH, PIVOT = (
    1.06,
    1.12,
    (1000.0, 1000.0),
)  # this far right keeps both signature marks whole, and the door in frame
LISTENER_HALF = 210.0  # his half-width on screen, for the check that the door hides him whole
LOG = {"x": 150, "y": 1436, "wide": 790, "tall": 134, "inset": 24, "size": 30, "row": 40}
CARRIED = 8  # spring keys in a row that carry momentum, see rest_springs
STAMP = {"x": 60, "y": 1436, "wide": 880, "inset": 24, "size": 42}
END = 26.8

LINES = (
    Line("narrator", "One thing in this room is changing."),
    Line("narrator", "You have until she shuts up."),
    Line("nell", "I notice everything."),
    Line("nell", "Number six cries on Tuesdays."),
    Line("nell", "Number nine has a new brother. Fourth this year."),
    Line("nell", "And you changed your shampoo. I'd change it back."),
    Line("nell", "Nothing gets past me."),
    Line("narrator", "The door."),
    Line("nell", "That door's been red for years."),
    Line("narrator", "Researchers found the same with photographs."),
    Line("narrator", "In one study, a stranger was swapped mid-chat."),
    Line("narrator", "Only half noticed."),
    Line("nell", "There. You changed it back. Much better."),
)

script = scripting.Script(LINES)
hold, say = script.hold, script.say

FIRST = ("side", "smirk", "desk")  # the fox of the first frame, which is also the last
BEATS = (
    say(0.0, "fox", 0, *FIRST),
    say(1.8, "fox", 1, *FIRST),
    say(3.2, "fox", 2, "narrow", "smirk", "desk"),
    say(4.5, "fox", 3, "side", "open", "lean"),
    say(6.6, "fox", 4, "up", "frown", "lean"),
    say(9.5, "fox", 5, "narrow", "flat", "crossed"),
    say(12.4, "fox", 6, "closed", "grin", "crossed"),
    say(13.9, "fox", 7, "wide", "flat", "crossed", "reveal"),
    hold(14.6, "fox", "", "left", "flat", "crossed"),
    say(15.35, "fox", 8, "narrow", "smirk", "crossed", "denial"),
    say(17.1, "fox", 9, *FIRST, "study"),
    say(19.4, "fox", 10, *FIRST, "carry"),
    say(22.4, "fox", 11, *FIRST),
    say(23.7, "fox", 12, "narrow", "grin", "lean", "credit"),
    hold(26.3, "fox", LINES[0].text, *FIRST, "first"),
)
# What the fox has noticed, on the pad on the ledge, each row with the line that says it: (column, row, words, beat).
NOTICED = (
    (0, 0, "No. 6: cries, Tuesdays", 3),
    (0, 1, "No. 9: brother (4th)", 4),
    (1, 0, "Him: new shampoo", 5),
    (1, 1, "Front door: red, years", 9),
)
SKETCH = Sketch(SLUG, TITLE, (NARRATOR, NELL), LINES, BEATS, END, cast=mind_kit.MIND_CAST)
EVENTS = ("reveal", "denial", "study", "carry", "credit", "first")
POST = InstagramPost(
    title="One thing in this room is changing. Did you catch it?",
    description=(
        "Watch it once, then watch it again knowing. Large, slow changes can go unnoticed, and in one study a stranger "
        "was swapped mid-chat and only half noticed.\n"
        "Sources: Simons, Franconeri & Reimer (2000), Perception 29(10); Simons & Levin (1998), Psychonomic Bulletin & "
        "Review 5(4)."
    ),
    credit="Voices: ElevenLabs premade voices Bella and Alice. Original characters, drawn in code.",
    hashtags=("#psychology", "#changeblindness", "#howpeoplethink", "#tryit"),
    thumbnail=Thumbnail(
        "Nothing gets\npast her.", 1.0, "There's a name for that", focus=(420.0, 860.0), zoom=1.0, place="bottom"
    ),
)


def validate(sk: Sketch = SKETCH) -> None:
    """The sketch is consistent, each event happens once and in order, the first picture speaks, the door has its
    twelve seconds before the reveal, and no word on screen is one the channel keeps off it."""
    sketch.check(sk)
    for event in EVENTS:
        scripting.exactly_once(sk.beats, event, f"{event} happens once")
    scripting.only_events(sk.beats, set(EVENTS))
    times = [sketch.events(sk.beats, event)[0][0] for event in EVENTS]
    if times != sorted(times):
        raise sketch.SketchError(f"the events run {EVENTS}")
    if sk.beats[0].line is None:
        raise sketch.SketchError("the reel opens on the challenge, with its line")
    if times[0] < CHANGE + 1.0:
        raise sketch.SketchError(f"the door needs {CHANGE} s after the first frame, the reveal is at {times[0]}")
    words = (*(q.text for q in sk.lines), NAME, PAD, *(row[2] for row in NOTICED))
    for text in (*words, *SLOW[0], SLOW[1], *SWAP[0], SWAP[1], POST.title, POST.description):
        mind_kit.check_copy(text)


def no_desk(cv, parent) -> None:
    """The hall lays its own ledge: see :func:`dress`."""


def door_keys(reveal: float, first: float) -> list[tuple[float, float]]:
    """The repainted door's opacity: none, then one straight ramp over :data:`CHANGE` seconds that ends on the reveal,
    held; the rewind and the sped-up run of :data:`REPLAY` seconds; held; none again on the first frame's return."""
    start = reveal - CHANGE
    return [
        (0.0, 0.0),
        (start, 0.0),
        (reveal, 1.0),
        (reveal + 0.15, 1.0),
        (reveal + 0.15 + REPLAY * 0.35, 0.0),
        (reveal + 0.15 + REPLAY, 1.0),
        (first - 0.001, 1.0),
        (first, 0.0),
    ]


def _door(cv, parent, leaf: str, panel: str) -> None:
    """A door of the hall's shapes, in its own colours; ``hallway`` draws the same three rectangles and the handle."""
    x0, y0, x1, y1 = DOOR_BOX
    fx, fy, fh = toon.fx, toon.fy, toon.fh
    cv.rect(parent, fx(x0), fy(y0), fh(x1 - x0), fh(y1 - y0), leaf, cv.ink, toon.INK_W * 0.7, radius=0)
    for top, high in ((y0 + 30, 220), (y0 + 280, 240)):
        cv.rect(
            parent, fx(x0 + 28), fy(top), fh(x1 - x0 - 56), fh(high), panel, cv.ink, toon.FINE_W * 0.5, radius=fh(4)
        )
    cv.ellipse(parent, fx(x0 + 22), fy(y0 + 268), fh(24), fh(24), toon_house.BRASS, cv.ink, toon.FINE_W * 0.6)


def _stands(shot, who: str, framing: tuple[float, float], start: float, end: float, blinks=()) -> None:
    """``who`` in the hall from ``start`` to ``end``, half awake: not the shot's own figure, so behind it, and listening
    with nothing but the odd slow blink."""
    cv = shot.cv
    timed = cv.group(shot.back, cv.uid("g"), start=start, end=end)
    pose = {"eyes": "half", "mouth": "flat", "arms": "desk"}
    rows = [{"start": 0.0, **pose}]
    for t in blinks:
        rows += [{"start": t, **pose, "eyes": "closed"}, {"start": t + 0.4, **pose}]
    poses = toon.parse_poses(rows, f"{who} in the hall")
    sketch.drawer(who, shot.versions)(cv, figure_group(cv, timed, framing), poses, end, (), enter=start)


def _pad(shot, end: float, home: float, stop: float) -> None:
    """The fox's pad on the ledge, blank on the first frame, filling as she talks: each row on its line. Away for the
    stamps at ``end``, and blank again from ``home``, so the last frame is the first."""
    cv = shot.cv
    x, y, wide, tall, inset, size, row = (LOG[k] for k in ("x", "y", "wide", "tall", "inset", "size", "row"))

    def sheet(start: float, stop_at: float):
        g = cv.group(shot.front, cv.uid("g"), start=start, end=stop_at)
        cv.rect(g, x, y, wide, tall, mind_kit.PAPER, cv.ink, toon.FINE_W, radius=10.0)
        cv.text(g, cv.uid("pad"), PAD, x + inset, y + 8, wide, 36, 28, color=mind_kit.INK, align="start", wrap="none")
        return g

    g = sheet(0.0, end)
    sheet(home, stop)
    for column, line, words, beat in NOTICED:
        at = shot.beats[beat].start
        if at >= end:
            raise sketch.SketchError(f"{words!r} comes after the pad has gone")
        left, top = x + inset + column * (wide - 2 * inset) // 2, y + 46 + line * row
        shown = cv.group(g, cv.uid("g"), start=at, end=end)
        half = (wide - 2 * inset) // 2
        cv.text(shown, cv.uid("pad"), words, left, top, half, row, size, color=mind_kit.INK, align="start", wrap="none")


def _carried(shot, start: float) -> None:
    """The door the hall lost, carried through in front of everyone from right to left, a neighbour on each end. It
    slows while it hides the listener."""
    cv = shot.cv
    end = start + CARRY
    moving = cv.group(shot.front, cv.uid("g"), start=start, end=end, x=0.0)
    poses = toon.parse_poses([{"start": 0.0, "eyes": "side", "mouth": "flat", "arms": "desk"}], "a neighbour carrying")
    for who, dx in (("raccoon", -170.0), ("rabbit", 170.0)):
        sketch.drawer(who, shot.versions)(cv, figure_group(cv, moving, (CARRIER, dx)), poses, end, (), enter=start)
    leaf = cv.group(moving, cv.uid("g"), x=toon.fx(165) - DOOR_W / 2, y=toon.fy(801) - DOOR_H)
    cv.rect(leaf, 0, 0, DOOR_W, DOOR_H, DOOR_LEAF, cv.ink, toon.INK_W * 0.7, radius=0)
    for top, high in ((50.0, 460.0), (560.0, 500.0)):
        cv.rect(leaf, 56, top, DOOR_W - 112, high, DOOR_PANEL, cv.ink, toon.FINE_W * 0.5, radius=8)
    cv.keys(moving, "x", carry_keys(start), hold=False, local=False)


def carry_keys(start: float) -> list[tuple[float, float]]:
    """The carried door's way across: quick in from the right, slow in front of the listener, quick out on the left."""
    w = 1080.0
    over = toon.fx(165) + toon.fh(LISTENER[1])  # the listener's x, the point the door's middle is over
    middle = over - toon.fx(165)
    return [(start, w), (start + 0.65, middle + 30.0), (start + 1.15, middle - 30.0), (start + CARRY, -w)]


def swap_time(start: float) -> float:
    """The moment the door is square in front of the listener: the sloth goes out and the bear comes in."""
    return round(start + 0.9, 3)


def _stamp(shot, words: tuple[tuple[str, ...], str], start: float, end: float, heading: str = "") -> None:
    """One evidence line over the picture, on the ledge and short of the signature marks: the finding, the citation
    under it, and over them the effect's name when it has one."""
    cv = shot.cv
    x, y, wide, inset, size = STAMP["x"], STAMP["y"], STAMP["wide"], STAMP["inset"], STAMP["size"]
    rows = [(heading, 30, 38)] if heading else []
    rows += [*((row, size, 52) for row in words[0]), (words[1], 28, 38)]
    if any(shot.measure(text, big) > wide - 2 * inset for text, big, _ in rows):
        raise sketch.SketchError(f"a stamp's rows fit its box: {words!r}")
    g = cv.group(shot.front, cv.uid("g"), start=start, end=end)
    cv.rect(g, x, y, wide, 24 + sum(high for *_, high in rows), mind_kit.PAPER, cv.ink, toon.FINE_W, radius=14.0)
    top = y + 12
    for text, big, high in rows:
        cv.text(g, cv.uid("stamp"), text, x + inset, top, wide - 2 * inset, high, big, color=mind_kit.INK, wrap="none")
        top += high


def dress(shot) -> None:
    """The hall, its door and what becomes of it, the listener, the carried door, the ledge and the two stamps. One
    shot: nothing cuts away from the door while it changes."""
    cv, app = shot.cv, shot.app
    at = {name: sketch.events(shot.beats, name)[0][0] for name in EVENTS}
    far = mind_kit.far(cv, cv.group(shot.back, cv.uid("g")))
    toon_house.hallway(cv, far, door="shut")
    repaint = cv.group(far, "door-change", opacity=0.0)
    _door(cv, repaint, RED_LEAF, RED_PANEL)
    cv.keys(repaint, "opacity", door_keys(at["reveal"], at["first"]), hold=False, local=False)
    mind_kit.key(cv, shot.light)
    swapped = swap_time(at["carry"])
    beats = shot.beats
    _stands(shot, "sloth", LISTENER, app.start, swapped, blinks=[beats[i].start + 0.6 for i in (3, 4, 6)])
    _stands(shot, "bear", LISTENER, swapped, at["first"])
    _stands(shot, "sloth", LISTENER, at["first"], app.end)
    _carried(shot, at["carry"])
    toon_house.ledge(cv, shot.front, "oak")
    _pad(shot, at["study"], at["first"], app.end)
    _stamp(shot, SLOW, at["study"], at["carry"], heading=NAME)
    _stamp(shot, SWAP, swapped, at["first"])


def lens_keys(reveal: float, study: float) -> list[tuple[float, float]]:
    """The whole shot's scale: a slow push while she talks, so the picture never stands still, the cut in at the
    reveal, and the cut back out at the stamp, where it holds, the first frame's framing."""
    return [(0.0, 1.0), (reveal - 0.001, PUSH), (reveal, PUNCH), (study - 0.001, PUNCH), (study, 1.0)]


def rest_springs(setup, run: int = CARRIED) -> None:
    """Start every ``run``-th spring key of the shot from rest. The head's spring keys carry their momentum from key to
    key, and the engine's time for a frame doubled or worse with each carried key before it: fine on the short shots
    the rig was drawn for, and a still at 9 s took over two minutes on this one long shot. Each move in a head plan
    starts from rest anyway, so a restart moves nothing a viewer can see."""
    for animate in setup.iter("animate"):
        chain = [key for key in animate.iter("key") if key.carry]
        for key in chain[run - 1 :: run]:
            key.carry = None


def lens(shot, setup) -> None:
    """The push, the punch in at the reveal and the cut back out: :func:`lens_keys`. The door stays whole."""
    rest_springs(setup)
    at = {name: sketch.events(shot.beats, name)[0][0] for name in ("reveal", "study")}
    camera.anchor(setup, *PIVOT, place=True)
    zoom = lens_keys(at["reveal"], at["study"])
    shot.cv.keys(setup, "scaleX", zoom, hold=False)
    shot.cv.keys(setup, "scaleY", zoom, hold=False)


def foley(beats, end, speech, root, seed) -> list[dict]:
    """The channel's sting on the reveal and a whoosh as the door goes through."""
    audio = root / "audio"
    audio.mkdir(parents=True, exist_ok=True)
    reveal, carry = sketch.events(beats, "reveal")[0][0], sketch.events(beats, "carry")[0][0]
    sting = mind_kit.write_sting(audio / "sting.wav", [reveal], end)
    whoosh = synth.write_whoosh(audio / "whoosh.wav", [carry + 0.2], end, seed=seed)
    return [sketch.effect("sting", 0.0, -5.0, root, sting), sketch.effect("whoosh", 0.0, -12.0, root, whoosh)]
