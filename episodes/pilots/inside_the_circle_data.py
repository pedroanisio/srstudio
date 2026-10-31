"""Inside the Circle — a pilot of the Maps channel, main trigger jaw-drop: the sketch as data.

"Nearly half of all people live inside this circle." The dots arrive, a million people each, and a hamster squeezes
through them apologising. The count is stamped with its grid and its year, and the 2013 circle tightens into the 2015
one. Then the same circle slides over Australia, where 44 dots fall into it one at a time and the same hamster has
nobody to apologise to, and slides home to fill again. The last frame is the first.

The 3,300 km circle around Mong Khet held a majority on an older reading and does not on the 2025 grid, so the reel says
what the grid says and does not widen the circle. Every figure traces to ``pilots/maps/inside-the-circle/sources.md``
and every dot to ``tools/maps/build_layers.py``. The projection is Lambert equal-area, re-centred on each circle, at one
scale, so the two rings on screen are the same true size.

The narrator is ElevenLabs premade Bella in the channel's own constant, heard only. ``SKETCH`` is checked by
:func:`srstudio.sketch.check`; :func:`validate` checks the events and every word on screen; :func:`dress` draws each
shot from the events, so the map follows the recording; :func:`foley` its sound.
"""

from __future__ import annotations

import math
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
    "A red ring sits on a map of Asia, tagged 3,300 km, and dots fill it, one for each million people, thick inside "
    "the ring and thin outside it. A cartoon hamster squeezes through big red dots, apologising. A stamp gives the "
    "count inside and outside, and ripples run over the dots. A wider circle over the South China Sea tightens onto "
    "the ring. The map slides under the ring until it is over Australia, where 44 dots fall in one at a time. The "
    "hamster stands alone on an empty map with one dot far off. The map slides home and the ring fills again. The "
    "first picture comes back."
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
SLIDE = 2.0  # seconds the map takes to slide under the ring, either way
RECOLOUR = 0.8  # seconds the first circle's dots take to stop being what the reel is about
FALL = 1.1  # seconds the 44 dots take to fall in
LEAVE = 0.4  # seconds the 44 take to go as the map leaves, while they are still in frame
REFILL = 0.9  # seconds the first circle's dots take to come back
COUNTED = 0.95  # seconds between the ripples that count the dots: two inside, two outside
RIPPLE = 1.1  # seconds one ripple runs
RIPPLE_OUT = 2.7  # how many ring radii a ripple outside the ring reaches
# The 2013 circle: "centred in the South China Sea and about 4,000 km in radius" (Quah). He gives no point, so this one
# is a stand-in for drawing it, and the circle is drawn as "about": sources.md says so.
FIRST_DRAWN = (13.0, 114.0)
FIRST_DRAWN_KM = 4000.0
TIGHTEN = 1.2  # seconds the 2013 circle takes to become the 2015 one

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

END = 23.6

LINES = (
    Line("narrator", "Nearly half of all people live inside this circle."),
    Line("narrator", "Each dot is a million people."),
    Line("ham", "Excuse me. Sorry. Sorry."),
    Line("narrator", "That's almost four billion inside, and over four billion outside."),
    Line("narrator", "A map started this in 2013. An economist tightened the circle in 2015."),
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
    say(4.4, "hamster", 2, "shock", "flat", "desk", "crowd"),
    say(6.2, CARD, 3, *FACE, "count"),
    say(10.2, CARD, 4, *FACE, "origin"),
    say(14.1, CARD, 5, *FACE, "slide"),
    say(16.3, CARD, 6, *FACE, "fall"),
    say(17.4, "hamster", 7, "side", "flat", "desk", "alone"),
    say(18.6, CARD, 8, *FACE, "many"),
    hold(22.2, CARD, LINES[0].text, *FACE, "first"),
)
SKETCH = Sketch(SLUG, TITLE, (map_kit.NARRATOR, HAMSTER), LINES, BEATS, END, cast=map_kit.MAPS_CAST)
EVENTS = ("dots", "crowd", "count", "origin", "slide", "fall", "alone", "many", "first")
TINTS = {"narrator": map_kit.PAPER, "ham": map_kit.PIN}
MOUTH = replace(sketch.MOUTH_STYLE, spelling=True, close_bilabials=True, lead=0.04, min_rest=0.12)
POST = InstagramPost(
    title="Slide this circle over Australia and it holds 44 million",
    description=(
        "Around Mong Khet the same circle holds nearly half of everyone alive. The centre in Australia, Adelaide, was "
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
    if at["many"] + SLIDE + REFILL > at["first"]:
        raise sketch.SketchError("the map comes home and the first circle fills before the first picture returns")
    return rests


def labels(beats, end: float) -> list[tuple[float, float, str]]:
    """What is lettered on screen, when: the caption, the stamp, the ring's tag and the pin of the place in the ring."""
    at = _at(beats)
    return [
        (0.0, end, "caption"),
        (0.0, end, "stamp"),
        (0.0, end, "tag"),
        (0.0, at["slide"], MONG_KHET.name),
        (at["fall"], at["many"], ADELAIDE.name),
        (at["many"] + SLIDE, end, MONG_KHET.name),
    ]


def _world(shot, start: float, end: float, id: str, *, dots: bool) -> None:
    """The map, the dots and the pins from ``start`` to ``end`` of the reel: the same map whichever shot draws it, keyed
    to the reel's clock, so a shot that comes back finds it where it would have been. It goes to Australia and back."""
    cv, back, front = shot.cv, shot.back, shot.front
    at = _at(shot.beats)
    slide, many = at["slide"], at["many"]
    arrived, home = _rest(at), many + SLIDE
    shift = None
    if dots:
        here, there = (MONG_KHET.lat, MONG_KHET.lon), (ADELAIDE.lat, ADELAIDE.lon)
        out, back_home = map_kit.glide(here, there, slide, arrived), map_kit.glide(there, here, many, home)
        shift = (out[0] + back_home[0], out[1] + back_home[1])
    view = map_kit.equal_area(cv, back, MONG_KHET.lon, MONG_KHET.lat, ZOOM, start, end, shift=shift, id=id)
    if dots:
        everyone = {"inside": (0.0, FILL), "rest": (OUTSIDE, FILL)}
        map_kit.population(cv, view, everyone, id=f"{id}-out")  # under the red, for when the red goes
        red = {"inside": (0.0, FILL)}
        fades = {"inside": (slide, slide + RECOLOUR)}
        if arrived <= start < many + LEAVE:  # the engine refuses a layer with nothing in frame at any frame of its map
            red["adelaide"] = (at["fall"], at["fall"] + FALL)
            fades["adelaide"] = (many, many + LEAVE)
        pins = {"inside": map_kit.PIN, "adelaide": map_kit.PIN}
        map_kit.population(cv, view, red, colours=pins, fades=fades, id=f"{id}-red")
        if end > home:
            map_kit.population(cv, view, {"inside": (home, home + REFILL)}, colours=pins, id=f"{id}-again")
    for n, (place, a, b) in enumerate(
        ((MONG_KHET, start, min(end, slide)), (MONG_KHET, max(start, home), end))
        if dots
        else ((MONG_KHET, start, end),)
    ):
        if a < b:
            map_kit.pin(cv, front, view, place, a, b, shot.measure, side="below", id=f"{id}-pin-{n}", figure=False,
                        pop=False)  # fmt: skip
    if dots and start < many and end > at["fall"]:
        map_kit.pin(cv, front, view, ADELAIDE, max(start, at["fall"]), min(end, many), shot.measure, side="below",
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
    count, origin = _at(shot.beats)["count"], _at(shot.beats)["origin"]
    if origin - count < 4 * COUNTED:
        raise sketch.SketchError(f"the count needs {4 * COUNTED} s of line, got {origin - count} s")
    _ripple(shot, count, (0.05, 1.0))
    _ripple(shot, count + COUNTED, (0.05, 1.0))
    _ripple(shot, count + 2 * COUNTED, (1.0, RIPPLE_OUT))
    _ripple(shot, count + 3 * COUNTED, (1.0, RIPPLE_OUT))


def first_drawn() -> tuple[float, float, float]:
    """Where the 2013 circle falls on the first map, in frame pixels: its centre, then its radius."""
    lat1, lat2 = math.radians(MONG_KHET.lat), math.radians(FIRST_DRAWN[0])
    west_east = math.radians(FIRST_DRAWN[1] - MONG_KHET.lon)
    bearing = math.atan2(
        math.sin(west_east) * math.cos(lat2),
        math.cos(lat1) * math.sin(lat2) - math.sin(lat1) * math.cos(lat2) * math.cos(west_east),
    )
    away = map_kit.ring_px(map_kit.km_between((MONG_KHET.lat, MONG_KHET.lon), FIRST_DRAWN), ZOOM)
    return 540.0 + away * math.sin(bearing), RING_Y - away * math.cos(bearing), map_kit.ring_px(FIRST_DRAWN_KM, ZOOM)


def _tightens(shot) -> None:
    """The 2013 circle comes up where it was drawn, wider and in the South China Sea, then tightens onto the ring."""
    cv = shot.cv
    at = _at(shot.beats)
    begins, ends = at["origin"], at["slide"]
    moves = begins + (ends - begins) / 2
    x, y, radius = first_drawn()
    g = cv.group(shot.back, cv.uid("g"), start=begins, end=ends, x=x, y=y)
    cv.keys(g, "x", [(moves, x), (moves + TIGHTEN, 540.0)], kind="sine-in-out", local=False)
    cv.keys(g, "y", [(moves, y), (moves + TIGHTEN, RING_Y)], kind="sine-in-out", local=False)
    for prop in ("scaleX", "scaleY"):
        cv.keys(g, prop, [(moves, 1.0), (moves + TIGHTEN, RING_PX / radius)], kind="sine-in-out", local=False)
    cv.keys(g, "opacity", [(begins, 0.0), (begins + 0.3, 1.0), (moves + TIGHTEN, 1.0), (ends, 0.0)], hold=False,
            local=False)  # fmt: skip
    cv.ellipse(g, -radius, -radius, 2 * radius, 2 * radius, cv.clear, map_kit.PAPER, 14.0)
    cv.ellipse(g, -radius, -radius, 2 * radius, 2 * radius, cv.clear, map_kit.INK, 7.0)


def _stamps(shot, start: float, end: float, id: str) -> None:
    """Whichever stamps fall from ``start`` to ``end``: how to read a dot, the count, then the second circle."""
    at = _at(shot.beats)
    for n, (text, begins, stops) in enumerate(
        (
            (LEGEND, 0.0, at["count"]),
            (COUNT, at["count"], at["slide"]),
            (OVER, at["fall"], at["many"]),
            (COUNT, at["many"] + SLIDE, at["first"]),
            (LEGEND, at["first"], shot.end),
        )
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
        if app.start < at["first"]:
            stop = min(app.end, at["first"])
            # Maps either side of a cut match, so it does not show: the 44 are drawn only on the map that holds them.
            cuts = [t for t in (_rest(at), at["many"] + LEAVE) if app.start < t < stop]
            for a, b in zip((app.start, *cuts), (*cuts, stop), strict=True):
                _world(shot, a, b, f"world-{round(a * 1000)}", dots=True)
                _stamps(shot, a, b, f"world-{round(a * 1000)}")
            if app.start <= at["count"] < stop:
                _ripples(shot)
                _tightens(shot)
            map_kit.ring(
                cv, shot.back, RING_PX, app.start, stop, y=RING_Y, id=f"ring-{n}", label=TAG, measure=shot.measure
            )
        if app.end > at["first"]:
            begins = max(app.start, at["first"])
            _world(shot, begins, app.end, f"home-{n}", dots=False)
            map_kit.ring(
                cv, shot.back, RING_PX, begins, app.end, y=RING_Y, id=f"home-ring-{n}", label=TAG, measure=shot.measure
            )
            _stamps(shot, begins, app.end, f"home-{n}")
    map_kit.sign(shot.cv, shot.front)


def foley(beats, end, speech, root, seed) -> list[dict]:
    """A bump for each big dot that shoves in, a pop for each of the 44, and a whoosh each way the map slides."""
    audio = root / "audio"
    audio.mkdir(parents=True, exist_ok=True)
    at = _at(beats)
    bumps = [at["crowd"] + i * STAGGER for i in range(len(CROWD))]
    falls = [at["fall"] + i * FALL / 44 for i in range(44)]
    pops = map_kit.write_pops(audio / "pops.wav", sorted([*bumps, *falls]), end, seed=seed)
    whoosh = synth.write_whoosh(audio / "whoosh.wav", [at["slide"], at["many"]], end, seed=seed)
    return [sketch.effect("pops", 0.0, -11.0, root, pops), sketch.effect("whoosh", 0.0, -13.0, root, whoosh)]
