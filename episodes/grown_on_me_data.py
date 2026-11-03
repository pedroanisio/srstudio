"""It's Grown On Me — the sketch as data: in every couple one of them turns down the first film the other suggests,
then forty-five minutes later suggests it himself.

Mae and Bruno on the sofa at night, in plain clay in the 3D lounge (episodes/grown_on_me.py). Mae picks The Quiet
Ferry; Bruno's "Fine." is a no, and she knows it. They browse for forty-five minutes. He finds a film he likes. The
trailer is the first one she said. He says it has grown on him; she says "Fine." and switches the TV off.

Three voices (ElevenLabs premade Sarah as Mae, Bill as Bruno, Brian as the trailer the TV plays). They face us, so the
TV is on our side of the frame: its light falls on the shot (:func:`srstudio.toon_rooms.front_screen`), one cue per
click. The TV's list of films is :func:`srstudio.toon_everyday.tv_browse`, full frame, twice: once still on the
first film she picks, once browsing at eleven. ``ROWS`` act each beat; :func:`dress` draws the flat control's shots,
:func:`overlay` the text line, :func:`sounds` the room; :func:`clay_keys` and :func:`clay_holds` move the clay
figures (examples/clay_sofa/performance.py reads them).

The ending is rendered both ways (``SKETCH`` with Mae's last "Fine.", ``VARIANT`` without it); one is picked on the
first render.
"""

from __future__ import annotations

import json
from dataclasses import replace
from math import ceil
from pathlib import Path

from srstudio import (
    anatomy_ledger,
    foley,
    look,
    scripting,
    sketch,
    toon_bed,
    toon_everyday,
    toon_house,
    toon_pair,
    toon_rooms,
    toon_voices,
    toon_world,
)
from srstudio.anatomy import Side
from srstudio.scripting import at
from srstudio.sketch import Line, Sketch
from srstudio.toon import fy
from srstudio.toon_pair import Act
from srstudio.toon_sketch import Sound

MOUTH = toon_voices.MOUTH
SEED = 3431
SLUG = "grown-on-me"
TITLE = "It's Grown On Me — Mae and Bruno (Clay)"
DESCRIPTION = (
    "A clay sketch on a sofa at night: Bruno turns down the first film Mae picks, they browse for forty-five minutes, "
    "and the film he finds is hers."
)
ACCESSIBILITY = (
    "On a sofa in a dark living room a clay rabbit and a clay bear face us, lit blue by a TV we cannot see; she holds "
    "a remote. A trailer voice says This winter, The Quiet Ferry. The frame is a TV list of films at 10:15 with one "
    "tile in focus: a small ferry on a grey sea, THE QUIET FERRY, 2h 38m. He says it's fine; she clicks it away. In "
    "close-ups they argue about subtitles. A loud trailer makes both jump. They stare. The list slides past at 11:00. "
    "He sits up delighted at a film, and the trailer is the same one. She turns to him slowly. He says it has grown on "
    "him. She clicks, the TV goes off and the room drops dark. Lines appear in tinted pills and a bar says US PICKING "
    "A MOVIE FOR 45 MINUTES."
)
NARRATION = "Voiced with ElevenLabs premade voices Sarah (Mae), Bill (Bruno) and Brian (the trailer)."
NOTE = "ElevenLabs premade voices Sarah, Bill and Brian at their natural pace; no reference-voice cloning."
MAE = toon_voices.speaker("mae", "Sarah", "rabbit")
BRUNO = toon_voices.speaker("bruno", "Bill", "bear")
TRAILER = toon_voices.speaker("narrator", "Brian", None, "big")  # the TV's trailer voice, never seen: a bible role
TINTS = toon_voices.tinted(MAE, BRUNO, TRAILER)
TWO, MAE_C, BRUNO_C, MENU = (
    "hamster",
    "goat",
    "sloth",
    "dog",
)  # never seen: the names of the shots the dress draws whole
BARE = (TWO, MAE_C, BRUNO_C, MENU)
RABBIT_COAT, BEAR_COAT = "#efe8ee", "#a8764f"
TEXT_LINE = "us picking a movie for 45 minutes"
FILM, RUNTIME = "THE QUIET FERRY", "2h 38m"
FIRST_CLOCK, LATER_CLOCK = "10:15", "11:00"
MAE_AT, BRUNO_AT, PAIR_SCALE = (84.0, 850.0), (258.0, 850.0), 0.66  # it-autoplayed's places: the room's plates
MAE_CLOSE, BRUNO_CLOSE = (165.0, 880.0), (235.0, 880.0)
FAR_BLUR = 5.0
LIGHTS = {"lamp": ((0, "off"),)}
REMOTE_ROOT, REMOTE_HAND = (-14.0, 800.0), (36.0, 752.0)  # her arm in from the frame's edge, and the remote in it
CLICK_LEAD = 0.25  # seconds a click comes before what it changes
UP_BEFORE, UP_AFTER = 0.25, 0.3  # seconds the remote is raised round a click
BROWSE_STEPS = (0.35, 0.65, 0.95, 1.25)  # seconds into the browsing insert the row steps a tile, on a tick each
BLAST_LIFT, BLAST_TILT = 40.0, -4.0  # canvas pixels up and degrees back: both jerk at the loud trailer
OOH_LIFT = 24.0  # canvas pixels Bruno sits up on "Ooh"
TURN_TO = -14.0  # reference pixels the face slides across the head toward the other one (the clay's head turn)
STING_GLOW = 0.4  # seconds the white flash of the loud trailer lasts
BLACKOUT, BLACKOUT_INK = 0.62, "#07080d"  # the room once the TV is off: this much of near-black over the screen's night

LINES = (
    Line("narrator", "This winter. The Quiet Ferry."),
    Line("mae", "This one."),
    Line("bruno", "Sure. Fine."),
    Line("mae", "Fine."),
    Line("bruno", "It's fine."),
    Line("mae", "That's your no."),
    Line("bruno", "This one's supposed to be good."),
    Line("mae", "It's got subtitles."),
    Line("bruno", "So?"),
    Line("mae", "So I'd have to watch it."),
    Line("narrator", "One man. One last job."),
    Line("mae", "We've seen this."),
    Line("bruno", "I haven't."),
    Line("bruno", "Ooh. What about this one?"),
    Line("narrator", "This winter. The Quiet Ferry."),
    Line("mae", "That's the first one I said."),
    Line("bruno", "It's grown on me."),
    Line("mae", "Fine."),
)
script = scripting.Script(LINES)
say, hold = script.say, script.hold
TOP = ("up", "flat", "desk")
# Mae is mirrored, so her "left" is at Bruno
M_FRONT = Act("wide", "flat", "desk")
M_AT_HIM = Act("left", "flat", "desk")
M_NARROW = Act("narrow", "flat", "desk")
M_BORED = Act("half", "flat", "desk")
# Bruno
B_FRONT = Act("wide", "flat", "desk")
B_FIXED = Act("narrow", "flat", "desk")
B_SIDE = Act("left", "flat", "desk")
B_DELIGHT = Act("wide", "grin", "desk")
B_CALM = Act("half", "smirk", "desk")

ROWS = (
    (hold(0.0, TWO, "", *TOP, "open"), M_FRONT, B_FRONT),
    (say(0.25, TWO, 0, *TOP), M_FRONT, B_FRONT),
    (say(2.5, MENU, 1, *TOP, "menu"), M_FRONT, B_FRONT),
    (say(3.5, TWO, 2, *TOP), M_FRONT, B_FIXED),
    (say(4.6, TWO, 3, *TOP, "turn"), M_AT_HIM, B_FIXED),  # she turns to him; he does not turn
    (say(5.3, TWO, 4, *TOP), M_AT_HIM, B_FIXED),
    (say(6.3, MAE_C, 5, *TOP, "gone"), M_AT_HIM, B_FIXED),  # a click: the tile is gone
    (say(7.5, BRUNO_C, 6, *TOP), M_AT_HIM, B_SIDE),
    (say(9.4, MAE_C, 7, *TOP), M_NARROW, B_SIDE),
    (say(10.7, BRUNO_C, 8, *TOP), M_NARROW, B_SIDE),
    (say(11.3, MAE_C, 9, *TOP), M_NARROW, B_SIDE),
    (say(13.0, TWO, 10, *TOP, "blast"), M_FRONT, B_FRONT),  # a click, the trailer loud: both jerk
    (say(14.8, TWO, 11, *TOP), M_BORED, B_FRONT),
    (say(15.8, TWO, 12, *TOP), M_BORED, B_FIXED),
    (hold(16.6, TWO, "", *TOP, "stare"), M_AT_HIM, B_SIDE),  # the held silence: her eyes, his head; then a click
    (hold(18.0, MENU, "", *TOP, "browse"), M_BORED, B_FRONT),  # eleven o'clock, the row sliding past
    (say(19.8, TWO, 13, *TOP, "ooh"), M_BORED, B_DELIGHT),
    (say(21.6, TWO, 14, *TOP, "again"), M_BORED, B_DELIGHT),  # the first trailer, the first glow
    (hold(23.6, MAE_C, "", *TOP, "slow"), M_AT_HIM, B_DELIGHT),  # the held silence: her head turns to him
    (say(25.0, MAE_C, 15, *TOP), M_AT_HIM, B_CALM),
    (say(26.6, BRUNO_C, 16, *TOP), M_AT_HIM, B_CALM),
    (hold(28.0, TWO, "", *TOP, "reverse"), M_FRONT, B_SIDE),  # the held silence: lines 4 and 5 the other way round
    (say(29.2, TWO, 17, *TOP), M_FRONT, B_SIDE),
    # the click straight off the word, under its caption (a caption change would wait for the caption minimum): the TV
    # off, the room dark; the caption goes a step later
    (hold(29.5, TWO, "Fine.", *TOP, "off"), M_FRONT, B_SIDE),
    (hold(29.65, TWO, "", *TOP), M_FRONT, B_SIDE),
)
DARK = 1.7  # seconds of the dark room after the click
ONCE = ("open", "menu", "turn", "gone", "blast", "stare", "browse", "ooh", "again", "slow", "reverse", "off")


def _sketch(rows, lines, slug_title: str) -> Sketch:
    beats = tuple(row[0] for row in rows)
    end = round(at(beats, "off") + DARK, 3)
    return Sketch(SLUG, slug_title, (MAE, BRUNO, TRAILER), lines, beats, end, tail=0.15, bare=BARE)


ACTS = {"rabbit": tuple(row[1] for row in ROWS), "bear": tuple(row[2] for row in ROWS)}
SKETCH = _sketch(ROWS, LINES, TITLE)
# the other ending: no last "Fine.", the hold runs into the click; its acts are the same rows less that one
_LAST = next(k for k, row in enumerate(ROWS) if row[0].line == len(LINES) - 1)
_OFF = ROWS[_LAST + 1]  # the hold runs its scripted 1.2 s, then the click, with no caption to keep
VARIANT_ROWS = (*ROWS[:_LAST], (replace(_OFF[0], start=ROWS[_LAST][0].start, caption=""), *_OFF[1:]))
VARIANT = _sketch(VARIANT_ROWS, LINES[:-1], TITLE)
VARIANT_ACTS = {"rabbit": tuple(row[1] for row in VARIANT_ROWS), "bear": tuple(row[2] for row in VARIANT_ROWS)}
BREATH = foley.Burst(0.3, 2600.0, attack=0.14, decay=0.3)
TICK = foley.Burst(0.05, 3200.0, attack=0.001, decay=0.2, tone_hz=1400.0, tone_end_hz=1400.0, tone=0.5)
ROOM_AIR = foley.Burst(4.0, 240.0, attack=0.3, decay=8.0)  # the room once the TV stops: never digital silence
HIT = foley.Burst(0.6, 180.0, attack=0.003, decay=0.5, tone_hz=62.0, tone_end_hz=48.0, tone=0.9)  # a trailer's boom


def sketch_for(root: Path, variant: bool = False) -> Sketch:
    """The ending a project holds: the one its recording says, whose takes are its lines (``voiced/speech.json``);
    before anything is recorded, the variant when ``variant``. A recording of neither is refused."""
    speech = Path(root) / "voiced" / "speech.json"
    if not speech.exists():
        return VARIANT if variant else SKETCH
    try:
        takes = len(json.loads(speech.read_text())["takes"])
    except (OSError, ValueError, KeyError, TypeError) as error:
        raise sketch.SketchError(f"{speech}: not a recording this reel can read: {error}") from error
    found = {len(SKETCH.lines): SKETCH, len(VARIANT.lines): VARIANT}.get(takes)
    if found is None or (variant and found is SKETCH):
        raise sketch.SketchError(f"{speech} holds {takes} takes: neither ending, or not the one asked for")
    return found


def validate(sk: Sketch = SKETCH) -> None:
    """The sketch is consistent, speaks by 0.5 s, every event comes once and in the script's order, the text line
    fits its bar and the trailer's first line is said again word for word."""
    sketch.check(sk)
    scripting.speaks_by(sk.beats, 0.5)
    scripting.only_events(sk.beats, set(ONCE))
    for kind in ONCE:
        scripting.exactly_once(sk.beats, kind, f"{kind} comes once")
    order = [at(sk.beats, kind) for kind in ONCE]
    if order != sorted(order):
        raise sketch.SketchError("the events run in the script's order")
    if sk.lines[0] != sk.lines[14]:
        raise sketch.SketchError("the trailer at the end is the trailer at the start, word for word")
    if len(TEXT_LINE) > toon_house.KEY_LINE_MAX:
        raise sketch.SketchError(
            f"the text line runs {len(TEXT_LINE)} letters, its bar holds {toon_house.KEY_LINE_MAX}"
        )


def clicks(beats) -> dict[str, float]:
    """When Mae presses the remote: the tile away, the loud trailer, into the browsing, and off. The last comes
    straight off her word, so it is the off beat itself."""
    return {
        "gone": round(at(beats, "gone") - CLICK_LEAD, 3),
        "blast": round(at(beats, "blast") - CLICK_LEAD, 3),
        "browse": round(at(beats, "browse") - 0.1, 3),
        "off": at(beats, "off"),
    }


def ticks(beats) -> tuple[float, ...]:
    """The browsing row's steps, project seconds: one tick, one tile."""
    start = at(beats, "browse")
    return tuple(round(start + s, 3) for s in BROWSE_STEPS)


def glow(beats) -> tuple:
    """What the TV does to the room: blue on the first trailer, a change at each click, the loud trailer's white flash,
    the first glow again on the same trailer, and off."""
    c = clicks(beats)
    return (
        (0, "on", "blue"),
        (c["gone"], "on", "purple"),
        (c["blast"], "on", "white"),
        (round(c["blast"] + STING_GLOW, 3), "on", "amber"),
        (c["browse"], "dim", "purple"),
        (at(beats, "ooh"), "on", "amber"),
        (at(beats, "again"), "on", "blue"),
        (c["off"], "off"),
    )


def blackout(beats) -> list[tuple[float, float]]:
    """The dark sheet's opacity over the shot, held: none until her last click, :data:`BLACKOUT` from it. The
    screen's own night (toon_rooms.front_screen) alone leaves the room about two thirds as bright as lit."""
    return [(0.0, 0.0), (clicks(beats)["off"], BLACKOUT)]


def overlay(cv, parent, beats, end, measure) -> None:
    """The text line, from the first frame until the first line is said."""
    toon_house.key_line(cv, parent, TEXT_LINE, 0.0, at(beats, "menu"), measure=measure)


def sounds(beats, end) -> tuple[Sound, ...]:
    """The TV's hum until it goes off, the room's air after, her clicks, the browsing row's ticks, the loud trailer's
    boom and his breath in at the jerk."""
    c = clicks(beats)
    off = c["off"]
    whole = int(off // foley.HUM.seconds)
    last = round(off - whole * foley.HUM.seconds, 3)  # the hum's last piece stops on her click
    pieces = [Sound("hum", foley.HUM, tuple(k * foley.HUM.seconds for k in range(whole)), -32.0)]
    if last > 0.05:
        pieces.append(Sound("hum-end", replace(foley.HUM, seconds=last, decay=0.1), (off - last,), -32.0))
    return (
        *pieces,
        Sound("room", ROOM_AIR, tuple(round(off + k * 3.6, 3) for k in range(ceil((end - off) / 3.6))), -34.0),
        Sound("click", foley.REMOTE_CLICK, (c["gone"], c["blast"], c["browse"], off), -12.0),
        Sound("tick", TICK, (0.1, *ticks(beats)), -20.0),
        Sound("hit", HIT, (at(beats, "blast"),), -10.0),
        Sound("breath", BREATH, (round(at(beats, "blast") + 0.02, 3),), -16.0),
    )


# --- the clay's moves (examples/clay_sofa/performance.py samples them on every frame) ------------------------------


def clay_keys(beats, who: str) -> dict[str, list[tuple[float, float]]]:
    """The whole figure's ``lift`` (canvas pixels, up is negative) and ``tilt`` (degrees), and the head's ``face``
    turn (reference pixels across the head, toward the other one when negative), keyed on the sketch's clock: both
    jerk at the loud trailer; Bruno sits up on "Ooh" and turns to her on the stare and at the end; Mae turns to him on
    her first "Fine.", and slowly in the held close-up, and back to the front at the end."""
    blast = at(beats, "blast")
    jerk = [(blast, 0.0), (blast + 0.08, -BLAST_LIFT), (blast + 0.3, -BLAST_LIFT), (blast + 0.9, 0.0)]
    if who == "bruno":
        ooh, slow, stare, browse, reverse = (at(beats, k) for k in ("ooh", "slow", "stare", "browse", "reverse"))
        lift = [*jerk, (ooh - 0.15, 0.0), (ooh + 0.1, -OOH_LIFT), (slow, -OOH_LIFT), (slow + 0.5, 0.0)]
        tilt = [(blast, 0.0), (blast + 0.08, BLAST_TILT), (blast + 0.3, BLAST_TILT), (blast + 0.9, 0.0)]
        face = [(stare, 0.0), (stare + 0.5, TURN_TO), (browse, TURN_TO), (browse + 0.3, 0.0), (reverse, 0.0),
                (reverse + 0.35, TURN_TO)]  # fmt: skip
        return dict(lift=lift, tilt=tilt, face=face)
    turn, gone, slow, reverse = (at(beats, k) for k in ("turn", "gone", "slow", "reverse"))
    face = [(turn, 0.0), (turn + 0.25, TURN_TO), (gone, TURN_TO), (gone + 0.3, 0.0), (slow, 0.0),
            (slow + 1.2, TURN_TO), (reverse, TURN_TO), (reverse + 0.3, 0.0)]  # fmt: skip
    return dict(lift=jerk, tilt=[(0.0, 0.0)], face=face)


def clay_holds(beats, who: str, t: float) -> str:
    """What ``who`` holds at ``t``: Mae the remote, raised round each click and through the browsing; Bruno nothing."""
    if who != "mae":
        return ""
    browse = at(beats, "browse")
    if browse - UP_BEFORE <= t < browse + BROWSE_STEPS[-1] + UP_AFTER:
        return "remote-up"
    if any(c - UP_BEFORE <= t < c + UP_AFTER for c in clicks(beats).values()):
        return "remote-up"
    return "remote"


# --- the flat control: the same shots drawn as cards, which the clay build takes the cards out of -----------------


def _room(shot) -> None:
    """The lounge out of focus behind the sofa, whose back stays sharp with the people on it, and no TV in it."""
    cv = shot.cv
    far = look.depth(cv, shot.back, "grown-on-me-far", FAR_BLUR, overscan=True)
    light = cv.group(far, cv.uid("g"))
    toon_rooms.stage(cv, far, light, "lounge", LIGHTS, shot.end, blink=False, bare=("tv",))
    toon_world.sofa_back(cv, shot.back)


def _keyed(cv, g, rest: tuple[float, float], keys: dict[str, list[tuple[float, float]]]) -> None:
    """Key the card ``g`` with the clay's lift and tilt, on the sketch's clock."""
    y = fy(rest[1])
    cv.keys(g, "y", [(t, y + v) for t, v in keys["lift"]], hold=False, kind="sine-out", local=False)
    if len(keys["tilt"]) > 1:
        cv.keys(g, "rotation", keys["tilt"], hold=False, kind="sine-out", local=False)


def _two(shot) -> None:
    """Both of them on the sofa, her remote in her hand."""
    cv, beats = shot.cv, shot.beats
    acts = acts_of_beats(beats)
    mae = toon_pair.figure(shot, shot.back, "rabbit", MAE_AT, acts["rabbit"], scale=PAIR_SCALE, mirror=True)
    bruno = toon_pair.figure(shot, shot.back, "bear", BRUNO_AT, acts["bear"], scale=PAIR_SCALE)
    _keyed(cv, mae, MAE_AT, clay_keys(beats, "mae"))
    _keyed(cv, bruno, BRUNO_AT, clay_keys(beats, "bruno"))
    with anatomy_ledger.on_arm("rabbit", Side.LEFT):
        toon_bed.swung_arm(cv, shot.back, REMOTE_ROOT, RABBIT_COAT, [(shot.app.start, -38.0)], shot.app.start,
                           shot.app.end, length=60.0, width=30.0)  # fmt: skip
    toon_everyday.remote(cv, shot.back, REMOTE_HAND, scale=0.42, tilt=14.0, id=cv.uid("remote"))
    toon_world.sofa(cv, shot.front, "rug")


def _mae(shot) -> None:
    """Mae alone."""
    acts = acts_of_beats(shot.beats)
    toon_pair.figure(shot, shot.back, "rabbit", MAE_CLOSE, acts["rabbit"], scale=1.0, mirror=True)
    toon_world.sofa(shot.cv, shot.front, "rug")


def _bruno(shot) -> None:
    """Bruno alone."""
    acts = acts_of_beats(shot.beats)
    toon_pair.figure(shot, shot.back, "bear", BRUNO_CLOSE, acts["bear"], scale=1.0)
    toon_world.sofa(shot.cv, shot.front, "rug")


def acts_of_beats(beats) -> dict[str, tuple]:
    """The acts for the beats a build placed: as many as the sketch they came from has rows."""
    return ACTS if len(beats) == len(ROWS) else VARIANT_ACTS


def _menu(shot) -> None:
    """The TV, full frame: still on the film she picks at a quarter past ten, or browsing at eleven."""
    cv, beats = shot.cv, shot.beats
    if shot.app.start <= at(beats, "menu") < shot.app.end:
        toon_everyday.tv_browse(cv, shot.front, FIRST_CLOCK, title=FILM, runtime=RUNTIME, measure=shot.measure,
                                id=cv.uid("menu"))  # fmt: skip
    else:
        toon_everyday.tv_browse(cv, shot.front, LATER_CLOCK, steps=ticks(beats), measure=shot.measure,
                                id=cv.uid("menu"))  # fmt: skip


def dress(shot) -> None:
    """The lounge behind, then the shot, and the TV's light over all of it but its own menu."""
    who = shot.app.who
    if who == MENU:
        _menu(shot)
        return
    _room(shot)
    {TWO: _two, MAE_C: _mae, BRUNO_C: _bruno}[who](shot)
    cv = shot.cv
    toon_rooms.front_screen(cv, shot.front, glow(shot.beats), shot.end)
    dark = cv.group(shot.front, cv.uid("g"), blend="multiply", opacity=0.0)
    cv.keys(dark, "opacity", blackout(shot.beats), hold=True, local=False)
    cv.rect(dark, 0, 0, cv.width, cv.height, BLACKOUT_INK, cv.clear, 0, radius=0)
