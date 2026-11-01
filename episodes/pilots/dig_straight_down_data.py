"""Dig Straight Down — Maps #3, main trigger jaw-drop: the sketch as data.

"Dig through the Earth and you come up in the sea." A hamster is already digging. The world's people are turned through
the middle of the planet onto their antipodes, and most of them land in water; so does New York City, and so does the
hamster. Beijing does better, in Argentina, not China. Then the far side of the land is flipped onto this one, Madrid
gets New Zealand, and the hamster comes up on a hill and asks if this is China.

The claim the old playground line makes is the one the reel tests, for one city and not for a country: Chengdu lands in
the sea and Xi'an in Chile, so nothing here says China has a fixed answer. Every figure traces to
``pilots/maps/dig-straight-down/sources.md`` and ``tools/maps/antipodes.py``.

The narrator is ElevenLabs premade Bella in the channel's own constant, heard only. ``SKETCH`` is checked by
:func:`srstudio.sketch.check`; :func:`validate` checks the events and every word on screen; :func:`dress` draws each
shot from the events, so the map follows the recording; :func:`foley` its sound.
"""

from __future__ import annotations

from dataclasses import replace

from srstudio import foley as synth
from srstudio import map_kit, scripting, sketch
from srstudio.map_kit import CARD, Place
from srstudio.sketch import Line, Sketch, Speaker, Voice, VoiceSettings
from srstudio.social import InstagramPost
from srstudio.thumbnail import Thumbnail

SEED = 3301
SLUG = "dig-straight-down"
OUTPUT = f"renders/pilots/{SLUG}.mp4"
SERIES = "Maps #3"
TITLE = f"Dig Straight Down — {SERIES}"
DESCRIPTION = (
    "A pilot about where people live: four in five people would come up in the ocean if they dug straight through the "
    "Earth, and a hamster tries it."
)
ACCESSIBILITY = (
    "A cartoon hamster digs a hole, throwing dirt, and shouts that he is almost there. On a world map red dots for "
    "people turn through the middle of the Earth and land mostly in the sea, and a stamp reads 80% of people, GHS-POP "
    "2025, Natural Earth. A globe turns from a pin on New York City to a pin in the Indian Ocean, where the hamster "
    "bobs in the water and says hello. Another globe turns from Beijing to a pin in Argentina. The land is flipped "
    "over the world map, Madrid is pinned opposite New Zealand, and the hamster comes up on a green hill and asks if "
    "this is China. The narrator says no."
)
NARRATION = "Voiced with ElevenLabs premade voices Bella (narrator) and River (hamster); synthesised effects."
NOTE = "ElevenLabs premade voices Bella and River at their natural pace; no reference-voice cloning."
HOOK = "Dig through the Earth and you come up in the sea."
OCEAN = "Four in five people would come up in the ocean."
STAMP = "80% of people. GHS-POP 2025, Natural Earth."
EIGHTH = "About an eighth of the land has land opposite."

# GeoNames, sources.md gives each record's id; the far points are their antipodes from tools/maps/antipodes.py.
NEW_YORK = Place("New York City", 40.71427, -74.00597)
INDIAN = Place("Indian Ocean", -40.71427, 105.99403)
BEIJING = Place("Beijing", 39.9075, 116.39723)
ARGENTINA = Place("Argentina", -39.9075, -63.60277)
MADRID = Place("Madrid", 40.4165, -3.70256)
NEW_ZEALAND = Place("New Zealand", -40.4165, 176.29744)

WORLD_ZOOM = 0.0
TURN = 1.8  # seconds a globe takes to turn to the far side: any faster and the coasts flash
TURN_LEAD = 0.2  # seconds of turning before the far place is said
FLIP = 1.5  # seconds the world takes to turn through its middle
FLIP_AFTER = 0.5  # seconds into the line the turn starts
THROW = 0.16  # seconds between two clods of dirt
FLIGHT = 0.62  # seconds a clod is in the air
SOIL, SOIL_DARK, HILL, SKY = "#a7713f", "#8a5a2f", "#7fb65a", "#cfeaf5"
GROUND_Y = 1230.0  # frame y of the ground's edge in front of the hamster
WAVE_Y = 1120.0
BOB, BOB_PX = 0.8, 16.0  # seconds and pixels of one rise and fall of the water
FOAM = ((120.0, 1190.0, 210.0), (640.0, 1250.0, 280.0), (250.0, 1370.0, 240.0), (760.0, 1480.0, 170.0))

HAMSTER = Speaker(
    "ham",
    Voice(role="ham", id="SAz9YHcvj6GT2YYXdXww", name="River"),
    VoiceSettings(stability=0.45, similarity_boost=0.75, style=0.40),
    "hamster",
)
FIGURES = {"hamster": (1.35, 101.0)}  # centred in the frame
VERSIONS = {"toon-hamster": 1}

END = 23.9

LINES = (
    Line("narrator", HOOK),
    Line("ham", "Almost there!"),
    Line("narrator", OCEAN),
    Line("narrator", "New York City?"),
    Line("narrator", "The Indian Ocean."),
    Line("ham", "Hello?"),
    Line("narrator", "China?"),
    Line("narrator", "Beijing comes up in Argentina."),
    Line("narrator", "Flip the far side onto this one."),
    Line("narrator", EIGHTH),
    Line("narrator", "Madrid gets New Zealand."),
    Line("ham", "Is this China?"),
    Line("narrator", "No."),
)

script = scripting.Script(LINES)
hold, say = script.hold, script.say
FACE = ("wide", "flat", "desk")  # nobody is drawn on a map shot, and a beat still says who it is for

BEATS = (
    say(0.0, "hamster", 0, "half", "grin", "desk"),
    say(2.35, "hamster", 1, "wide", "open", "desk", "almost"),
    say(3.4, CARD, 2, *FACE, "ocean"),
    say(6.5, CARD, 3, *FACE, "nyc"),
    say(7.6, CARD, 4, *FACE, "indian"),
    say(10.1, "hamster", 5, "side", "flat", "desk", "hello"),
    say(11.0, CARD, 6, *FACE, "china"),
    say(11.9, CARD, 7, *FACE, "argentina"),
    say(14.55, CARD, 8, *FACE, "flip"),
    say(16.6, CARD, 9, *FACE, "eighth"),
    say(19.3, CARD, 10, *FACE, "madrid"),
    say(21.4, "hamster", 11, "half", "grin", "desk", "here"),
    say(22.8, "hamster", 12, "wide", "flat", "desk", "no"),
)
SKETCH = Sketch(SLUG, TITLE, (map_kit.NARRATOR, HAMSTER), LINES, BEATS, END, cast=map_kit.MAPS_CAST)
EVENTS = ("almost", "ocean", "nyc", "indian", "hello", "china", "argentina", "flip", "eighth", "madrid", "here", "no")
TINTS = {"narrator": map_kit.PAPER, "ham": map_kit.PIN}
MOUTH = replace(sketch.MOUTH_STYLE, spelling=True, close_bilabials=True, lead=0.04, min_rest=0.12)
THUMBNAIL = Thumbnail("Dig straight\ndown", 1.2, SERIES, place="bottom")
POST = InstagramPost(
    title="Where would you come up if you dug straight through the Earth?",
    description=(
        f"{SERIES}. For about 80% of people, in the sea: 79.8% on GHS-POP 2025 and 80.0% on WorldPop 2025, opposite "
        "Natural Earth's land. Only 13% of the land has land opposite. A city here is one coordinate, not its whole "
        "footprint, and Beijing is not all of China: Chengdu lands in the sea and Xi'an in Chile.\n"
        "Source: GHS-POP 2025, antipodes computed against Natural Earth 10m land."
    ),
    credit=(
        "GHS-POP R2023A, European Commission JRC, CC BY 4.0. Coordinates: GeoNames (geonames.org), CC BY 4.0. Made "
        "with Natural Earth. Voices: ElevenLabs premade."
    ),
    hashtags=("#maps", "#geography", "#antipodes", "#didyouknow"),
    thumbnail=THUMBNAIL,
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
    if sk.beats[0].line is None or sk.beats[0].start != 0.0:
        raise sketch.SketchError("the reel opens on the claim, with its line")
    places = (NEW_YORK, INDIAN, BEIJING, ARGENTINA, MADRID, NEW_ZEALAND)
    words = (*(q.text for q in sk.lines), STAMP, POST.title, POST.description, *(p.name for p in places))
    for text in words:
        map_kit.check_copy(text)
    map_kit.check_labels(labels(sk.beats, sk.end))


def no_desk(cv, parent) -> None:
    """A map stands on nothing, and the ground is drawn in :func:`dress`."""


def _at(beats) -> dict[str, float]:
    return {name: sketch.events(beats, name)[0][0] for name in EVENTS}


def labels(beats, end: float) -> list[tuple[float, float, str]]:
    """What is lettered on screen, when: the caption, the stamp and the pins."""
    at = _at(beats)
    return [
        (0.0, end, "caption"),
        (at["ocean"], at["nyc"], "stamp"),
        (at["nyc"], at["indian"], NEW_YORK.name),
        (at["indian"], at["hello"], INDIAN.name),
        (at["china"], at["argentina"], BEIJING.name),
        (at["argentina"], at["flip"], ARGENTINA.name),
        (at["madrid"], at["here"], MADRID.name),
        (at["madrid"], at["here"], NEW_ZEALAND.name),
    ]


def _people(shot, start: float, end: float) -> None:
    """The world's people where they live, turned through the middle of the Earth onto where they would come up."""
    cv = shot.cv
    map_kit.flat(cv, shot.back, 0.0, 0.0, WORLD_ZOOM, start, end, id="people-map", borders=False)
    flip = start + FLIP_AFTER
    map_kit.far_side(cv, shot.back, WORLD_ZOOM, start, (flip, flip + FLIP), end, what="people", id="people-far")
    map_kit.stamp(cv, shot.front, STAMP, start, end, shot.measure, id="people-stamp")


def _turn(shot, start: float, end: float, here: Place, there: Place, begin: float, id: str) -> None:
    """A globe on ``here`` with its pin, turned from ``begin`` to its far side and the pin of ``there``."""
    cv = shot.cv
    map_kit.ground(cv, shot.back)
    view = map_kit.globe(cv, shot.back, here.lon, here.lat, start, end, id=id)
    landed = begin + TURN
    cv.keys(view, "centerLon", [(begin, here.lon), (landed, there.lon)], kind="sine-in-out", local=False)
    cv.keys(view, "centerLat", [(begin, here.lat), (landed, there.lat)], kind="sine-in-out", local=False)
    map_kit.pin(cv, shot.front, view, here, start, begin, shot.measure, side="below", id=f"{id}-here", figure=False)
    map_kit.pin(cv, shot.front, view, there, landed, end, shot.measure, side="below", id=f"{id}-there", figure=False)


def _far(shot, start: float, end: float, at) -> None:
    """The land, its far side flipped onto it, and the one pair that lands on land."""
    cv = shot.cv
    view = map_kit.flat(cv, shot.back, 0.0, 0.0, WORLD_ZOOM, start, end, id="far-map", borders=False)
    flip = start + FLIP_AFTER
    map_kit.far_side(cv, shot.back, WORLD_ZOOM, start, (flip, flip + FLIP), end, id="far-land")
    for n, (place, side) in enumerate(((MADRID, "above"), (NEW_ZEALAND, "below"))):
        map_kit.pin(cv, shot.front, view, place, at["madrid"] + n * 0.5, end, shot.measure, side=side,
                    id=f"far-pin-{n}", figure=False)  # fmt: skip


def _clods(shot) -> None:
    """Dirt thrown out of the hole, left and right in turn, all through the shot."""
    cv = shot.cv
    for n in range(int((shot.app.end - shot.app.start - FLIGHT) / THROW)):
        at = shot.app.start + n * THROW
        side = -1.0 if n % 2 else 1.0
        reach = side * (260.0 + 90.0 * ((n * 7) % 5))
        rise = 420.0 + 60.0 * ((n * 3) % 4)
        x0, y0 = 540.0 + side * 150.0, GROUND_Y
        g = cv.group(shot.front, cv.uid("g"), start=at, end=at + FLIGHT, x=x0, y=y0)
        cv.keys(g, "x", [(at, x0), (at + FLIGHT, x0 + reach)], hold=False, local=False)
        arc = [(at + FLIGHT * k / 6, y0 - rise * 4 * (k / 6) * (1 - k / 6)) for k in range(7)]
        cv.keys(g, "y", arc, hold=False, local=False)
        r = 20.0 + 6.0 * (n % 3)
        cv.ellipse(g, -r, -r, 2 * r, 2 * r, SOIL_DARK if n % 3 else SOIL, map_kit.INK, 4.0)


def _ground(shot, earth: str, sky: str = SKY) -> None:
    """Sky behind him, and the ground's edge in front of him, with the heap he has dug up."""
    cv = shot.cv
    cv.rect(cv.group(shot.back, cv.uid("g")), 0, 0, cv.width, cv.height, sky)
    g = cv.group(shot.front, cv.uid("g"))
    cv.rect(g, -20.0, GROUND_Y, cv.width + 40.0, cv.height - GROUND_Y + 20.0, earth, map_kit.INK, 8.0)
    cv.ellipse(g, 110.0, GROUND_Y - 70.0, 860.0, 150.0, SOIL_DARK, map_kit.INK, 8.0)


def _sea(shot) -> None:
    """Open water up to his chest, rising and falling."""
    cv = shot.cv
    cv.rect(cv.group(shot.back, cv.uid("g")), 0, 0, cv.width, cv.height, SKY)
    g = cv.group(shot.front, cv.uid("g"), y=0.0)
    start, end = shot.app.start, shot.app.end
    count = int((end - start) / BOB) + 1
    keys = [(start + k * BOB, BOB_PX * (-1.0 if k % 2 else 1.0)) for k in range(count + 1)]
    cv.keys(g, "y", keys, kind="sine-in-out", local=False)
    cv.rect(g, -40.0, WAVE_Y, cv.width + 80.0, cv.height - WAVE_Y + 80.0, map_kit.SEA, map_kit.INK, 8.0)
    for x, y, wide in FOAM:
        cv.rect(g, x, y, wide, 12.0, map_kit.PAPER, radius=6.0)


def dress(shot) -> None:
    """Each shot from the events: the hole, the sea, the hill, or a map cut where the narration turns."""
    at = _at(shot.beats)
    app = shot.app
    if app.who == "hamster":
        if app.start < at["ocean"]:
            _ground(shot, SOIL)
            _clods(shot)
        elif app.start < at["china"]:
            _sea(shot)
        else:
            _ground(shot, HILL)
    elif app.start < at["hello"]:
        _turn(shot, at["nyc"], app.end, NEW_YORK, INDIAN, at["indian"] - TURN_LEAD, "ocean-globe")
        _people(shot, app.start, at["nyc"])
    else:
        _turn(shot, app.start, at["flip"], BEIJING, ARGENTINA, at["argentina"], "city-globe")
        _far(shot, at["flip"], app.end, at)
    map_kit.sign(shot.cv, shot.front)


def foley(beats, end, speech, root, seed) -> list[dict]:
    """A spade all through the first shot, a splash into the sea, a whoosh for each turn of the world, and a pop for
    each pin. It stops dead on the cut to the map, and there is no bed under the voices."""
    audio = root / "audio"
    audio.mkdir(parents=True, exist_ok=True)
    at = _at(beats)
    digs = [k * THROW * 2 for k in range(int(at["ocean"] / (THROW * 2)))]
    turns = [at["ocean"] + FLIP_AFTER, at["indian"] - TURN_LEAD, at["argentina"], at["flip"] + FLIP_AFTER]
    landed = at["indian"] - TURN_LEAD + TURN
    pins = [at["nyc"], landed, at["china"], at["argentina"] + TURN, at["madrid"], at["madrid"] + 0.5]
    rows = {
        "dig": (synth.write_bursts(audio / "dig.wav", digs, end, synth.SCRAPE, seed=seed), -12.0),
        "whoosh": (synth.write_whoosh(audio / "whoosh.wav", turns, end, seed=seed), -13.0),
        "splash": (synth.write_plop(audio / "splash.wav", [at["hello"] - 0.15], end, seed=seed), -9.0),
        "pops": (map_kit.write_pops(audio / "pops.wav", pins, end, seed=seed), -11.0),
    }
    return [sketch.effect(name, 0.0, gain, root, path) for name, (path, gain) in rows.items()]
