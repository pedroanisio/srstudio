"""I Was Watching — the sketch as data: Bruno is asleep in front of the movie. Mae turns it off and he is awake at once:
he was watching that. What happened, then? He did it. He is out again, so she keeps clicking: the TV goes, then the
room, and the sofa ends up on the lawn with him on it. Does he come with it? He's free. A truck, a highway, a dump, a
seagull, and beside him the same TV, dead. He opens his eyes. He was watching that.

Three voices (ElevenLabs premade Bill as Bruno, Sarah as Mae, Roger as the buyer). Bruno's shots hold one frame, the
sofa with him on it, and the world behind it changes (``stage:`` events): that is the reveal. Mae and the buyer each
talk over a far view of the sofa. It opens on a still first second (the ``sp-hook_motion`` test's arm A): Bruno asleep
under a line that says he is watching. ``SKETCH`` is checked by :func:`srstudio.sketch.check`; :func:`validate` checks
what the events ask of the props; :func:`dress` draws each shot, :func:`push` its camera and :func:`sounds` its foley.
"""

from __future__ import annotations

from dataclasses import replace
from functools import partial

from srstudio import camera, foley, scripting, sketch, toon, toon_props, toon_redrawn, toon_rooms, toon_world
from srstudio.sketch import Line, Sketch, Speaker
from srstudio.toon_sketch import BADGE_SIZE, Sound
from srstudio.voice import Voice, VoiceSettings

SEED = 2411
SLUG = "i-was-watching"
TITLE = "I Was Watching — Bruno and Mae (Toon)"
DESCRIPTION = (
    "A Toon sketch at home: Bruno is asleep in front of the movie. Mae turns it off and he says he was watching that. "
    "The TV, the room and the sofa go, and he sleeps all the way to the dump."
)
ACCESSIBILITY = (
    "A cartoon bear sleeps on a sofa with his mouth open in front of a lit TV. An arm with a remote turns it off and "
    "his eyes open: he was watching that. A cartoon rabbit asks what happened. He says he did it and sleeps again. "
    "Click by click the TV, the shelf and the rug vanish, the sofa stands on a lawn at a yard sale, on a truck on a "
    "highway, then at a dump at dusk beside the same TV, dead. A seagull lands on him and he opens his eyes."
)
NARRATION = "Voiced with ElevenLabs premade voices Bill (Bruno), Sarah (Mae) and Roger (the buyer); synthesised foley."
NOTE = "ElevenLabs premade voices Bill, Sarah and Roger at their natural pace; no reference-voice cloning."
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
BUYER = Speaker(
    "buyer",
    Voice(role="buyer", id="CwhRBWXzGAHq8TQ4Fs17", name="Roger"),
    VoiceSettings(stability=0.50, similarity_boost=0.75, style=0.35),
    "goat",
)
TINTS = {"bruno": "#f1dcc4", "mae": "#fbd3e0", "buyer": "#dfe7c8"}
MOUTH = replace(sketch.MOUTH_STYLE, spelling=True, close_bilabials=True, lead=0.04, min_rest=0.12)
HOOK = "Bruno is watching the movie"
STAGES = ("lounge", "no-tv", "bare", "yard", "road", "dump")
CLICKED = ("no-tv", "bare", "yard")  # the stages a click of the remote brings on
ZOOM = (1.1, (1000.0, 1420.0))  # the last push's scale and pivot (frame px): both signature marks stay in frame
FAR = dict(at=(430.0, 704.0), scale=0.5)  # the far sofa behind Mae and the buyer
REACH = 0.45  # seconds the paw is in shot before its click
LAND_LEAD = 0.25  # seconds of squawk before the gull lands
END = 20.9

LINES = (
    Line("bruno", "I was watching that."),
    Line("mae", "What happened, then?"),
    Line("bruno", "He did it."),
    Line("buyer", "Does he come with it?"),
    Line("mae", "He's free."),
    Line("bruno", "I was watching that."),
)

SCRIPT = scripting.Script(LINES)
say, hold = SCRIPT.say, SCRIPT.hold
ASLEEP = ("closed", "drop", "sigh")
BEATS = (
    hold(0.0, "bear", "", *ASLEEP),  # the still: asleep under the line that says he is watching
    hold(1.6, "bear", "", *ASLEEP, "click"),  # the paw clicks: the TV goes off
    hold(1.75, "bear", "", "wide", "flat", "crossed"),  # awake at once, before a word
    say(1.95, "bear", 0, "wide", "flat", "crossed"),
    say(3.3, "rabbit", 1, "narrow", "smirk", "crossed"),
    hold(4.6, "bear", "", "half", "flat", "crossed"),
    say(5.0, "bear", 2, "closed", "flat", "sigh"),
    hold(5.9, "bear", "", *ASLEEP, "snore"),
    hold(6.9, "rabbit", "", "half", "flat", "crossed"),  # she looks at him
    hold(7.7, "bear", "", *ASLEEP),  # her arm comes back in
    hold(8.1, "bear", "", *ASLEEP, "stage:no-tv"),
    hold(9.0, "bear", "", *ASLEEP, "stage:bare"),
    hold(9.9, "bear", "", *ASLEEP, "stage:yard"),
    say(11.2, "goat", 3, "side", "flat", "crossed"),
    say(12.5, "rabbit", 4, "half", "grin", "desk"),
    hold(13.8, "bear", "", *ASLEEP, "stage:road"),
    hold(16.0, "bear", "", *ASLEEP, "stage:dump"),
    hold(17.3, "bear", "", *ASLEEP, "gull"),
    hold(18.0, "bear", "", "half", "flat", "sigh"),  # the hold, then the line
    say(19.3, "bear", 5, "half", "flat", "sigh"),
)
SKETCH = Sketch(SLUG, TITLE, (BRUNO, MAE, BUYER), LINES, BEATS, END)


def stages(beats) -> list[tuple[float, str]]:
    """The world behind the sofa through the sketch: the lounge from 0, then every ``stage:`` event."""
    return scripting.changes(beats, "stage", STAGES[0])


def clicks(beats) -> list[float]:
    """Every click of the remote: the TV going off and each stage a click brings on."""
    return sorted(
        [at for at, _ in sketch.events(beats, "click")] + [at for at, name in stages(beats) if name in CLICKED]
    )


def land_of(beats) -> float:
    return sketch.events(beats, "gull")[0][0]


def validate(sk: Sketch = SKETCH) -> None:
    """The sketch is consistent, opens on a still of Bruno held at least 1 s, runs its stages in order on Bruno's
    shots, clicks once before the first line, lands one gull in the dump before the last line; no other events."""
    sketch.check(sk)
    opening = sk.beats[0]
    if opening.spoken or opening.caption or opening.event or opening.who != "bear" or sk.beats[1].start < 1.0:
        raise sketch.SketchError("the sketch opens on a still of Bruno: a silent, uncaptioned beat held at least 1 s")
    names = [name for _, name in stages(sk.beats)]
    if names != list(STAGES):
        raise sketch.SketchError(f"the stages run in order, got {names}")
    who_at = {b.start: b.who for b in sk.beats}
    if any(who_at[at] != "bear" for at, _ in sketch.events(sk.beats, "stage")):
        raise sketch.SketchError("a stage changes on Bruno's shot, the world behind him")
    scripting.exactly_once(sk.beats, "click", "the TV goes off once")
    scripting.exactly_once(sk.beats, "gull", "one gull lands")
    scripting.exactly_once(sk.beats, "snore", "he snores once on cue")
    dump = dict((name, at) for at, name in stages(sk.beats))["dump"]
    last = max(b.start for b in sk.beats if b.spoken)
    if not dump + toon_world.GULL_FLIGHT <= land_of(sk.beats) < last:
        raise sketch.SketchError("the gull flies in over the dump and lands before the last line")
    scripting.only_events(sk.beats, {"click", "stage", "snore", "gull"})


def far_sofa(shot, parent, stage_end: float) -> None:
    """Bruno asleep on the sofa across the room or the lawn, behind the speaker."""
    cv = shot.cv

    def draw(g) -> None:
        toon_world.sofa_back(cv, g)
        poses = toon.parse_poses(
            [{"start": 0.0, "eyes": ASLEEP[0], "mouth": ASLEEP[1], "arms": ASLEEP[2]}], "far Bruno"
        )
        sketch.drawer("bear", shot.versions)(cv, g, poses, stage_end, (), enter=shot.app.start)
        toon_world.sofa(cv, g, "bare", signed=False)

    toon_world.placed(cv, parent, draw=draw, **FAR)


def dress(shot) -> None:
    """One stage at a time: Bruno's shots hold the sofa in place and change what stands behind it and under it; Mae's
    and the buyer's put the far sofa over their shoulders."""
    cv, app = shot.cv, shot.app
    land = land_of(shot.beats)
    for a, b, name in scripting.spans(stages(shot.beats), app.start, app.end):
        back = cv.group(shot.back, cv.uid("g"), start=a, end=b)
        front = cv.group(shot.front, cv.uid("g"), start=a, end=b)
        if app.who == "bear":
            _bruno(shot, name, a, b, back, front, land)
        else:
            _far(shot, name, b, back, front)
    if app.who == "bear":
        _remote(shot)
    if app.who == "bear" and app.start == 0.0:
        measure = partial(shot.measure, size=BADGE_SIZE)
        spoken = next(b.start for b in shot.beats if b.spoken)
        toon_props.badge(cv, shot.front, HOOK, 0.0, spoken, measure, BADGE_SIZE)


def _remote(shot) -> None:
    """Mae's arm in Bruno's shot: it comes in before the first click of the shot and goes with its last."""
    cv, app = shot.cv, shot.app
    here = [t for t in clicks(shot.beats) if app.start < t < app.end]
    if here:
        cut = dict((name, at) for at, name in stages(shot.beats))["yard"]
        last = cut if here[-1] == cut else here[-1] + 0.25
        spans = [(max(app.start, here[0] - REACH), last)]
        toon_world.paw(cv, shot.front, spans, toon_redrawn.RABBIT.coat, presses=here)


def _bruno(shot, name: str, a: float, b: float, back, front, land: float) -> None:
    cv = shot.cv
    off = sketch.events(shot.beats, "click")[0][0]
    if name in ("lounge", "no-tv", "bare"):
        light = cv.group(back, cv.uid("g"))  # the light stays on the room: it would wash Bruno out
        lights = {"lamp": ((0, "on"),), "tv": ((0, "on", "blue"), (off, "off"))}
        bare = {"lounge": (), "no-tv": ("tv",), "bare": toon_rooms.LOUNGE_BARE}[name]
        toon_rooms.stage(cv, back, light, "lounge", lights, shot.end, bare=bare, blink=False)
        toon_world.sofa(cv, front, "bare" if name == "bare" else "rug")
    elif name == "yard":
        toon_world.yard(cv, back)
        toon_world.sofa_back(cv, back)
        toon_world.sofa(cv, front, "lawn")
    elif name == "road":
        toon_world.road(cv, back, a, b)
        toon_world.sofa_back(cv, back)
        toon_world.sofa(cv, front, "flatbed")
    else:
        toon_world.dump(cv, back)
        toon_world.sofa_back(cv, back)
        toon_world.sofa(cv, front, "heap")
        toon_world.gull(cv, front, land=land, end=b)
    if name != "lounge":
        snoring = (a, min(b, land)) if land > a else None
        if snoring:
            toon_world.snores(cv, front, [snoring])
    elif sketch.events(shot.beats, "snore")[0][0] < b:
        toon_world.snores(cv, front, [(sketch.events(shot.beats, "snore")[0][0], b)])


def _far(shot, name: str, b: float, back, front) -> None:
    cv = shot.cv
    if name == "yard":
        toon_world.yard(cv, back, table=False)
        far_sofa(shot, back, b)
        toon_world.ledge(cv, front, "#e9e4d8", "#cfc8b6", "#857c68")
    else:
        toon_world.wall(cv, back)
        far_sofa(shot, back, b)
        toon_world.ledge(cv, front, "#86604c", "#6b4a3a", "#3f2a20")


def push(shot, setup) -> None:
    """The camera holds. The truck's frame shakes; the last shot pushes in over the dump, to the end."""
    held = dict((name, at) for at, name in stages(shot.beats))
    if not shot.app.start <= held["dump"] < shot.app.end:
        return
    cv = shot.cv
    scale, (x, y) = ZOOM
    camera.anchor(setup, x, y, place=True)
    camera.push_in(cv, setup, scale=((held["dump"], 1.0), (shot.app.end, scale)))
    t, keys = held["road"], []
    while t < held["dump"] - 0.1:
        keys += [(round(t, 3), y), (round(t + 0.05, 3), y - 5.0)]
        t += 0.17 + 0.03 * (len(keys) % 3)
    keys.append((held["dump"], y))
    cv.keys(setup, "y", keys)


def sounds(beats, end: float) -> list[Sound]:
    """A click for each click, the snore, the road under the truck, the gull's cry as it comes in."""
    named = dict((name, at) for at, name in stages(beats))
    snored = [sketch.events(beats, "snore")[0][0], named["no-tv"] + 0.3, named["road"] + 0.5, named["dump"] + 0.2]
    return [
        Sound("click", foley.REMOTE_CLICK, tuple(clicks(beats)), 0.0),
        Sound("snore", foley.SNORE, tuple(snored), -2.0),
        Sound("road", foley.ROAD, (named["road"],), -6.0),
        Sound("gull", foley.GULL, (land_of(beats) - LAND_LEAD,), -5.0),
    ]
