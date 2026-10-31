"""Inside the Circle — a pilot of the Maps channel, main trigger jaw-drop: the sketch as data.

"Nearly half of all people live inside this circle." The ring is full on the first frame and the rest of the world's
dots arrive round it, a million people each. A hamster squeezes through them apologising, and the count is stamped with
its grid and its year. Then the finding gets bigger: the same circle slides over Australia, 44 dots fall into it one at
a time, the same hamster has nobody to apologise to, and the first circle holds about ninety times as many. The reel
ends on that map and cuts to its first frame, so the full ring lands straight after the empty one.

The 3,300 km circle around Mong Khet held a majority on an older reading and does not on the 2025 grid, so the reel says
what the grid says and does not widen the circle. Every figure traces to ``pilots/maps/inside-the-circle/sources.md``
and every dot to ``tools/maps/build_layers.py``. The projection is Lambert equal-area, re-centred on each circle, at one
scale, so the two rings on screen are the same true size.

The narrator is ElevenLabs premade Bella in the channel's own constant, heard only. ``SKETCH`` is checked by
:func:`srstudio.sketch.check`; :func:`validate` checks the events and every word on screen; :func:`dress` draws each
shot from the events, so the map follows the recording; :func:`foley` its sound.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import replace

from srstudio import foley as synth
from srstudio import map_kit, scripting, sketch
from srstudio.map_kit import CARD, Place
from srstudio.sketch import Line, Sketch, Speaker, Voice, VoiceSettings
from srstudio.social import InstagramPost
from srstudio.thumbnail import Thumbnail

SEED = 3202
SLUG = "inside-the-circle"
OUTPUT = f"renders/pilots/{SLUG}.mp4"
TITLE = "Inside the Circle — Maps"
DESCRIPTION = (
    "A pilot about where people live: a circle 3,300 kilometers in radius around Mong Khet holds nearly half of "
    "everyone alive, and the same circle over Australia holds 44 million."
)
ACCESSIBILITY = (
    "A red ring on a map of Asia, tagged 3,300 km, is thick with red dots, one for each million people, and thinner "
    "grey dots arrive outside it. A cartoon hamster squeezes through big red dots, apologising. A stamp gives the "
    "count inside and outside, and ripples run over the dots. The map slides under the ring until it is over "
    "Australia, where 44 dots fall in one at a time. The hamster stands alone on an empty map with one dot far off. "
    "The ring over Australia stays, with its stamp, and the reel cuts back to the full ring."
)
NARRATION = "Voiced with ElevenLabs premade voices Bella (narrator) and River (hamster); synthesised effects."
NOTE = "ElevenLabs premade voices Bella and River at their natural pace; no reference-voice cloning."
LEGEND = "1 dot = 1 million people, rounded. GHS-POP 2025."
COUNT = "Inside 3.95 bn. Outside 4.24 bn. GHS-POP 2025."
OVER = "Same circle over Australia: 44 million. GHS-POP 2025."
PROJECTION = "Lambert equal-area."

# GeoNames, downloaded 2026-10-31: sources.md gives each record's id.
MONG_KHET = Place("Mong Khet", 21.70282, 99.34224)
ADELAIDE = Place("Adelaide", -34.92866, 138.59863)
RADIUS_KM = 3300.0
RING_PX = 430.0  # frame pixels of both rings, so the two circles are drawn at one scale
ZOOM = map_kit.zoom_for_ring(RADIUS_KM, RING_PX)
TAG = "3,300 km"
RING_Y = 960.0

FILL = 2.4  # seconds the dots take to arrive
OUTSIDE = 0.5  # the outside's dots start this long after the inside's
SLIDE = 2.0  # seconds the map takes to slide under the ring
RECOLOUR = 0.8  # seconds the first circle's dots take to stop being what the reel is about
FALL = 2.0  # seconds the 44 dots take to fall in: slow enough to count how few they are
LEAST_APART = 0.6  # seconds between the ripples that count the dots: two inside, two outside, along the line
RIPPLE = 1.1  # seconds one ripple runs
RIPPLE_OUT = 2.7  # how many ring radii a ripple outside the ring reaches
LAST_RIPPLES = (0.2, 1.5)  # seconds into the last line: the empty ring is counted too, and the picture does not stop

HAMSTER = Speaker(
    "ham",
    Voice(role="ham", id="SAz9YHcvj6GT2YYXdXww", name="River"),
    VoiceSettings(stability=0.45, similarity_boost=0.75, style=0.40),
    "hamster",
)
FIGURES = {"hamster": (1.35, 101.0)}  # centred in the frame
VERSIONS = {"toon-hamster": 1}
CROWD = (  # the big dots round the hamster: their rest in the frame, and where they push in from
    (120, 560, -160, 500),
    (330, 500, 300, -120),
    (540, 470, 540, -160),
    (750, 500, 790, -120),
    (960, 560, 1240, 500),
    (70, 800, -180, 800),
    (1010, 800, 1260, 800),
    (60, 1050, -180, 1050),
    (1030, 1000, 1260, 1050),
    (90, 1290, -180, 1400),
    (1010, 1190, 1260, 1400),
    (230, 1500, 200, 2060),
    (420, 1560, 400, 2080),
    (660, 1560, 680, 2080),
    (850, 1500, 880, 2060),
)
CROWD_R = 92.0
CROWD_AT = (540.0, 1000.0)  # what the crowd presses towards
PUSH_IN = 0.24  # seconds a big dot takes to shove in
STAGGER = 0.05  # seconds between them
PRESS = 0.14  # share of the way to the hamster a big dot leans over the rest of the shot
FAR_DOT = (930.0, 640.0, 1130.0, 16.0)  # the nearest million, a long way off: rest x, y, from x, and its radius

END = 20.2

LINES = (
    Line("narrator", "Nearly half of all people live inside this circle."),
    Line("narrator", "Each dot is a million people."),
    Line("ham", "Excuse me. Sorry. Sorry."),
    Line("narrator", "That's almost four billion inside, and over four billion outside."),
    Line("narrator", "Now the same circle, over Australia."),
    Line("narrator", "Forty-four million."),
    Line("ham", "Excuse me?"),
    Line("narrator", "The first circle holds about ninety times as many."),
)

script = scripting.Script(LINES)
hold, say = script.hold, script.say
FACE = ("wide", "flat", "desk")  # nobody is drawn on a map shot, and a beat still says who it is for

BEATS = (
    say(0.0, CARD, 0, *FACE),
    say(2.8, CARD, 1, *FACE, "dots"),
    say(4.2, "hamster", 2, "shock", "flat", "desk", "crowd"),
    say(6.2, CARD, 3, *FACE, "count"),
    say(10.2, CARD, 4, *FACE, "slide"),
    say(13.2, CARD, 5, *FACE, "fall"),
    say(15.6, "hamster", 6, "side", "flat", "desk", "alone"),
    say(17.0, CARD, 7, *FACE, "many"),
)
SKETCH = Sketch(SLUG, TITLE, (map_kit.NARRATOR, HAMSTER), LINES, BEATS, END, cast=map_kit.MAPS_CAST)
EVENTS = ("dots", "crowd", "count", "slide", "fall", "alone", "many")
TINTS = {"narrator": map_kit.PAPER, "ham": map_kit.PIN}
MOUTH = replace(sketch.MOUTH_STYLE, spelling=True, close_bilabials=True, lead=0.04, min_rest=0.12)
POST = InstagramPost(
    title="Why does one circle hold 3.95 billion here and 44 million there?",
    description=(
        "Around Mong Khet the same circle holds nearly half of everyone alive. A 2013 map started the idea, and an "
        "economist tightened the circle in 2015. The centre in Australia, Adelaide, was "
        "chosen so the circle holds the country and largely misses Java; about 19 million of the 44 live outside "
        "Australia.\n"
        f"Source: GHS-POP 2025, circle of 3,300 km around Mong Khet, 48.3% of the grid. {PROJECTION}"
    ),
    credit=(
        "GHS-POP R2023A, European Commission JRC, CC BY 4.0: summed inside circles, drawn as dots, recoloured. "
        "Coordinates: GeoNames (geonames.org), CC BY 4.0. Made with Natural Earth. Voices: ElevenLabs premade."
    ),
    hashtags=("#maps", "#population", "#geography", "#didyouknow"),
    thumbnail=Thumbnail("Nearly\nhalf", 3.4, "of everyone alive", zoom=1.0, place="top"),
)


def validate(sk: Sketch = SKETCH) -> None:
    """The sketch is consistent, each event happens once and in order, the first picture speaks, and no word on screen
    is one the channel keeps off it."""
    sketch.check(sk)
    for event in EVENTS:
        scripting.exactly_once(sk.beats, event, f"{event} happens once")
    scripting.only_events(sk.beats, set(EVENTS))
    times = [sketch.events(sk.beats, event)[0][0] for event in EVENTS]
    if times != sorted(times):
        raise sketch.SketchError(f"the events run {EVENTS}")
    _rest(_at(sk.beats))
    if sk.beats[0].line is None:
        raise sketch.SketchError("the reel opens on the claim, with its line")
    for text in (
        *(q.text for q in sk.lines),
        LEGEND,
        COUNT,
        OVER,
        POST.title,
        POST.description,
        TAG,
        MONG_KHET.name,
        ADELAIDE.name,
    ):
        map_kit.check_copy(text)
    map_kit.check_labels(labels(sk.beats, sk.end))


def no_desk(cv, parent) -> None:
    """A map stands on nothing."""


def _at(beats) -> dict[str, float]:
    return {name: sketch.events(beats, name)[0][0] for name in EVENTS}


def _rest(at: Mapping[str, float]) -> float:
    """When the map comes to rest, before the 44 fall in the scripted timing and in the recorded one alike."""
    rests = at["slide"] + SLIDE
    if rests > at["fall"]:
        raise sketch.SketchError(f"the map rests at {rests} s, after the dots start to fall at {at['fall']} s")
    return rests


def labels(beats, end: float) -> list[tuple[float, float, str]]:
    """What is lettered on screen, when: the caption, the stamp, the ring's tag and the pin of the place in the ring."""
    at = _at(beats)
    return [
        (0.0, end, "caption"),
        (0.0, end, "stamp"),
        (0.0, end, "tag"),
        (0.0, at["slide"], MONG_KHET.name),
        (at["fall"], end, ADELAIDE.name),
    ]


def _world(shot, start: float, end: float, id: str) -> None:
    """The map, the dots and the pins from ``start`` to ``end`` of the reel: the same map whichever shot draws it, keyed
    to the reel's clock, so a shot that comes back finds it where it would have been."""
    cv, back, front = shot.cv, shot.back, shot.front
    at = _at(shot.beats)
    slide, arrived = at["slide"], _rest(at)
    shift = map_kit.glide((MONG_KHET.lat, MONG_KHET.lon), (ADELAIDE.lat, ADELAIDE.lon), slide, arrived)
    view = map_kit.equal_area(cv, back, MONG_KHET.lon, MONG_KHET.lat, ZOOM, start, end, shift=shift, id=id)
    map_kit.population(cv, view, {"inside": None, "rest": (OUTSIDE, FILL)}, id=f"{id}-out")  # under the red
    red: dict[str, tuple[float, float] | None] = {"inside": None}
    if start >= arrived:  # the engine refuses a layer with nothing in frame at any frame of its map
        red["adelaide"] = (at["fall"], at["fall"] + FALL)
    pins = {"inside": map_kit.PIN, "adelaide": map_kit.PIN}
    fades = {"inside": (slide, slide + RECOLOUR)}
    map_kit.population(cv, view, red, colours=pins, fades=fades, id=f"{id}-red")
    if start < slide:
        map_kit.pin(cv, front, view, MONG_KHET, start, min(end, slide), shot.measure, side="below", id=f"{id}-pin-0",
                    figure=False, pop=False)  # fmt: skip
    if end > at["fall"]:
        map_kit.pin(cv, front, view, ADELAIDE, max(start, at["fall"]), end, shot.measure, side="below",
                    id=f"{id}-adelaide", figure=False, pop=False)  # fmt: skip


def _ripple(shot, at: float, reach: tuple[float, float]) -> None:
    """One ring of light running across what is being counted, ``reach`` in ring radii, from ``at``."""
    cv = shot.cv
    g = cv.group(shot.back, cv.uid("g"), start=at, end=at + RIPPLE, x=540.0, y=RING_Y)
    for prop in ("scaleX", "scaleY"):
        cv.keys(g, prop, [(at, reach[0]), (at + RIPPLE, reach[1])], kind="sine-out", local=False)
    cv.keys(g, "opacity", [(at, 0.9), (at + RIPPLE, 0.0)], hold=False, local=False)
    cv.ellipse(g, -RING_PX, -RING_PX, 2 * RING_PX, 2 * RING_PX, cv.clear, map_kit.PAPER, 9.0)


def _ripples(shot) -> None:
    """While the line counts them: two ripples over the dots inside the ring, then two over the dots outside it."""
    count, slide = _at(shot.beats)["count"], _at(shot.beats)["slide"]
    apart = (slide - count) / 4
    if apart < LEAST_APART:
        raise sketch.SketchError(f"the count needs {4 * LEAST_APART} s of line, got {slide - count} s")
    for n, reach in enumerate(((0.05, 1.0), (0.05, 1.0), (1.0, RIPPLE_OUT), (1.0, RIPPLE_OUT))):
        _ripple(shot, count + n * apart, reach)


def _stamps(shot, start: float, end: float, id: str) -> None:
    """Whichever stamps fall from ``start`` to ``end``: how to read a dot, the count, then the second circle."""
    at = _at(shot.beats)
    for n, (text, begins, stops) in enumerate(
        ((LEGEND, 0.0, at["count"]), (COUNT, at["count"], at["slide"]), (OVER, at["fall"], shot.end))
    ):
        a, b = max(start, begins), min(end, stops)
        if a < b:
            map_kit.stamp(shot.cv, shot.front, text, a, b, shot.measure, id=f"{id}-stamp-{n}")


def _ground(shot) -> None:
    """A hamster's-eye view of the map: land, with the paper grid of the channel gone."""
    cv = shot.cv
    cv.rect(cv.group(shot.back, cv.uid("g")), 0, 0, cv.width, cv.height, map_kit.LAND)


def _crowd(shot) -> None:
    """A million people each, close up: they shove in round her, in turn, and press."""
    cv = shot.cv
    start, end = shot.app.start, shot.app.end
    _ground(shot)
    for i, (x, y, from_x, from_y) in enumerate(CROWD):
        at = start + i * STAGGER
        landed = at + PUSH_IN
        g = cv.group(shot.back, cv.uid("g"), x=from_x, y=from_y)
        cv.keys(g, "x", [(at, float(from_x)), (landed, float(x))], kind="back-out", local=False)
        cv.keys(g, "y", [(at, float(from_y)), (landed, float(y))], kind="back-out", local=False)
        leans = cv.group(g, cv.uid("g"))
        cv.keys(leans, "x", [(landed, 0.0), (end, (CROWD_AT[0] - x) * PRESS)], kind="linear", local=False)
        cv.keys(leans, "y", [(landed, 0.0), (end, (CROWD_AT[1] - y) * PRESS)], kind="linear", local=False)
        cv.ellipse(leans, -CROWD_R, -CROWD_R, 2 * CROWD_R, 2 * CROWD_R, map_kit.PIN, map_kit.PAPER, 6.0)


def _alone(shot) -> None:
    """The same hamster, the same size of map, and one dot on the horizon, wandering in."""
    cv = shot.cv
    _ground(shot)
    x, y, from_x, r = FAR_DOT
    g = cv.group(shot.back, cv.uid("g"), x=from_x, y=y)
    cv.keys(g, "x", [(shot.app.start, from_x), (shot.app.end, x)], kind="linear", local=False)
    cv.ellipse(g, -r, -r, 2 * r, 2 * r, map_kit.PIN, map_kit.PAPER, 3.0)


def dress(shot) -> None:
    """The world, or the hamster among the dots, or the hamster with nobody."""
    at = _at(shot.beats)
    cv, app, n = shot.cv, shot.app, round(shot.app.start * 1000)
    if app.who == "hamster":
        if app.start == at["crowd"]:
            _crowd(shot)
        else:
            _alone(shot)
    else:
        # Maps either side of a cut match, so it does not show: the 44 are drawn only on the map that holds them.
        cuts = [t for t in (_rest(at),) if app.start < t < app.end]
        for a, b in zip((app.start, *cuts), (*cuts, app.end), strict=True):
            _world(shot, a, b, f"world-{round(a * 1000)}")
            _stamps(shot, a, b, f"world-{round(a * 1000)}")
        if app.start <= at["count"] < app.end:
            _ripples(shot)
        if app.start == at["many"]:
            for after in LAST_RIPPLES:
                _ripple(shot, at["many"] + after, (0.05, 1.0))
        map_kit.ring(
            cv, shot.back, RING_PX, app.start, app.end, y=RING_Y, id=f"ring-{n}", label=TAG, measure=shot.measure
        )
    map_kit.sign(shot.cv, shot.front)


def foley(beats, end, speech, root, seed) -> list[dict]:
    """A bump for each big dot that shoves in, a pop for each of the 44, and a whoosh as the map slides."""
    audio = root / "audio"
    audio.mkdir(parents=True, exist_ok=True)
    at = _at(beats)
    bumps = [at["crowd"] + i * STAGGER for i in range(len(CROWD))]
    falls = [at["fall"] + i * FALL / 44 for i in range(44)]
    pops = map_kit.write_pops(audio / "pops.wav", sorted([*bumps, *falls]), end, seed=seed)
    whoosh = synth.write_whoosh(audio / "whoosh.wav", [at["slide"]], end, seed=seed)
    return [sketch.effect("pops", 0.0, -11.0, root, pops), sketch.effect("whoosh", 0.0, -13.0, root, whoosh)]
