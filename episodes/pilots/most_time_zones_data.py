"""Most Time Zones — Maps #4, main trigger jaw-drop: the sketch as data.

"Most time zones on Earth? France." The globe turns and stops on a country the viewer did not guess. The hamster
objects, the narrator says it has islands, and the pins go up on the far side of the world, down to a land border with
Brazil. Twelve clocks then read twelve different times at one moment. One real day runs past over seven French towns
and they are never all dark, so the old line about the sun and the empire holds. The hamster asks when lunch is. "Yes."

The count is true in July and a tie in January, and the stamp says July. Every figure traces to
``pilots/maps/most-time-zones/sources.md`` and ``tools/maps/time_zones.py``. Clipperton has no tz zone and is not
counted.

The narrator is ElevenLabs premade Bella in the channel's own constant, heard only. ``SKETCH`` is checked by
:func:`srstudio.sketch.check`; :func:`validate` checks the events and every word on screen; :func:`dress` draws each
shot from the events, so the map follows the recording; :func:`foley` its sound.
"""

from __future__ import annotations

import math
from dataclasses import replace
from datetime import datetime, timedelta, timezone

from srstudio import foley as synth
from srstudio import map_kit, scripting, sketch
from srstudio.map_kit import CARD, Move, Place
from srstudio.sketch import Line, Sketch, Speaker, Voice, VoiceSettings
from srstudio.social import InstagramPost
from srstudio.thumbnail import Thumbnail

SEED = 3302
SLUG = "most-time-zones"
OUTPUT = f"renders/pilots/{SLUG}.mp4"
SERIES = "Maps #4"
TITLE = f"Most Time Zones — {SERIES}"
DESCRIPTION = (
    "A pilot about the shape of countries: in July France runs twelve clocks, more than any other country, because of "
    "its islands, and the sun does not set on all of it."
)
ACCESSIBILITY = (
    "A globe turns and stops on France, with a stamp that reads July, France 12, Russia 11, tz database 2026c. A "
    "cartoon hamster in front of a map of Europe says it's tiny. On a world map pins pop up on Tahiti and Reunion, "
    "then the map flies to South America, where France and Brazil share a border, and the hamster says sorry, what. "
    "Twelve clocks appear, each showing a different time, and one dims when Russia's eleven is said. Seven dots on the "
    "world map light and go dark as a clock runs through one day, and at least one is always lit. A stamp reads seven "
    "towns, every 5 minutes, 2026, never all dark. The hamster, ringed by clocks, asks what time lunch is. "
    "The narrator "
    "says yes."
)
NARRATION = "Voiced with ElevenLabs premade voices Bella (narrator) and River (hamster); synthesised effects."
NOTE = "ElevenLabs premade voices Bella and River at their natural pace; no reference-voice cloning."
COUNT = "July: France 12, Russia 11. tz database 2026c."
SUN_STAMP = "Seven towns, every 5 minutes, 2026: never all dark."

# tz database 2026c, 15 July 2026: France's distinct UTC offsets, in hours (sources.md).
OFFSETS = (-10.0, -9.5, -9.0, -4.0, -3.0, -2.0, 2.0, 3.0, 4.0, 5.0, 11.0, 12.0)
MOMENT_UTC = 10.0  # noon in Paris in July
# GeoNames, as in tools/maps/time_zones.py: the towns the sun figure is about.
TOWNS = (
    Place("Papeete", -17.5334, -149.5667),
    Place("Mata-Utu", -13.2825, -176.1736),
    Place("Fort-de-France", 14.6089, -61.0733),
    Place("Cayenne", 4.9333, -52.3333),
    Place("Paris", 48.8534, 2.3488),
    Place("Saint-Denis", -20.8823, 55.4504),
    Place("Noumea", -22.2763, 166.4572),
)
WORST_DAY = datetime(2026, 6, 18, tzinfo=timezone.utc)  # the day of 2026 the seven come closest to all dark
FRANCE = Place("France", 48.8534, 2.3488)
TAHITI = Place("Tahiti", -17.5334, -149.5667)
REUNION = Place("Reunion", -20.8823, 55.4504)
GUIANA = Place("France", 3.93, -53.12)
BRAZIL = Place("Brazil", 0.9, -52.5)

SPIN_FROM, TILT = -100.0, 30.0
WORLD_ZOOM = 0.0
BORDER_ZOOM = 3.6
EUROPE_ZOOM = 3.0
FLY = 1.5  # seconds of the flight to the border
CLOCK_R, CLOCK_GAP = 118.0, 290.0
GRID_TOP = 640.0  # frame y of the first row of the twelve
RING_R, RING_TALL = 455.0, 545.0  # the clocks round the hamster, half a clock off the vertical to clear the caption
RING_AT = (540.0, 965.0)
SMALL_R = 76.0
RUN_R = 110.0  # the clock that runs through the day
RUN_AT = (540.0, 1330.0)
DIMMED = 0.25
FLOOR_Y = 1340.0

HAMSTER = Speaker(
    "ham",
    Voice(role="ham", id="SAz9YHcvj6GT2YYXdXww", name="River"),
    VoiceSettings(stability=0.45, similarity_boost=0.75, style=0.40),
    "hamster",
)
FIGURES = {"hamster": (1.35, 101.0)}  # centred in the frame
VERSIONS = {"toon-hamster": 1}

END = 23.2

LINES = (
    Line("narrator", "Most time zones on Earth? France."),
    Line("narrator", "Not Russia. Not the US. France."),
    Line("ham", "France? It's tiny."),
    Line("narrator", "It has islands."),
    Line("narrator", "Tahiti is France."),
    Line("narrator", "Reunion is France."),
    Line("narrator", "France has a land border with Brazil."),
    Line("ham", "Sorry, what?"),
    Line("narrator", "Twelve clocks in July."),
    Line("narrator", "Russia has eleven."),
    Line("narrator", "The sun never sets on France."),
    Line("ham", "So what time is lunch?"),
    Line("narrator", "Yes."),
)

script = scripting.Script(LINES)
hold, say = script.hold, script.say
FACE = ("wide", "flat", "desk")  # nobody is drawn on a map shot, and a beat still says who it is for

BEATS = (
    say(0.0, CARD, 0, *FACE),
    say(2.55, CARD, 1, *FACE, "nots"),
    say(5.0, "hamster", 2, "wide", "open", "desk", "tiny"),
    say(6.3, CARD, 3, *FACE, "islands"),
    say(7.4, CARD, 4, *FACE, "tahiti"),
    say(8.6, CARD, 5, *FACE, "reunion"),
    say(10.1, CARD, 6, *FACE, "border"),
    say(12.5, "hamster", 7, "side", "flat", "desk", "what"),
    say(13.4, CARD, 8, *FACE, "clocks"),
    say(15.2, CARD, 9, *FACE, "eleven"),
    say(16.5, CARD, 10, *FACE, "sun"),
    say(20.0, "hamster", 11, "half", "grin", "desk", "lunch"),
    say(21.9, "hamster", 12, "wide", "flat", "desk", "yes"),
)
SKETCH = Sketch(SLUG, TITLE, (map_kit.NARRATOR, HAMSTER), LINES, BEATS, END, cast=map_kit.MAPS_CAST)
EVENTS = ("nots", "tiny", "islands", "tahiti", "reunion", "border", "what", "clocks", "eleven", "sun", "lunch", "yes")
TINTS = {"narrator": map_kit.PAPER, "ham": map_kit.PIN}
MOUTH = replace(sketch.MOUTH_STYLE, spelling=True, close_bilabials=True, lead=0.04, min_rest=0.12)
THUMBNAIL = Thumbnail("Twelve\nclocks", 15.0, SERIES, place="bottom")
POST = InstagramPost(
    title="Which country has the most time zones?",
    description=(
        f"{SERIES}. In July, France: 12 clocks to Russia's 11 on tz database 2026c. "
        "In January France and Russia tie at "
        "11. Antarctic claims are left out, and so is uninhabited Clipperton, which has no tz zone. For the sun we "
        "checked seven towns from Papeete to Noumea every five minutes of 2026, and they are never all dark.\n"
        "Source: tz database 2026c; sun from the Astronomical Almanac's low-precision formulae."
    ),
    credit=(
        "Coordinates: GeoNames (geonames.org), CC BY 4.0. Made with Natural Earth. Time zones: IANA tz database, "
        "public domain. Voices: ElevenLabs premade."
    ),
    hashtags=("#maps", "#geography", "#timezones", "#france", "#didyouknow"),
    thumbnail=THUMBNAIL,
)


def validate(sk: Sketch = SKETCH) -> None:
    """The sketch is consistent, each event happens once and in order, the first picture speaks, there are twelve
    different clocks, a town is lit all through the day shown, and no word on screen is one the channel keeps off it."""
    sketch.check(sk)
    for event in EVENTS:
        scripting.exactly_once(sk.beats, event, f"{event} happens once")
    scripting.only_events(sk.beats, set(EVENTS))
    times = [sketch.events(sk.beats, event)[0][0] for event in EVENTS]
    if times != sorted(times):
        raise sketch.SketchError(f"the events run {EVENTS}")
    if sk.beats[0].line is None or sk.beats[0].start != 0.0:
        raise sketch.SketchError("the reel opens on the claim, with its line")
    if len(set(OFFSETS)) != 12:
        raise sketch.SketchError("the reel says twelve clocks, so it shows twelve different ones")
    if darkest(WORST_DAY) < 1:
        raise sketch.SketchError("the reel says the sun never sets, so a town is lit all through the day it shows")
    places = (FRANCE, TAHITI, REUNION, BRAZIL)
    words = (*(q.text for q in sk.lines), COUNT, SUN_STAMP, POST.title, POST.description, *(p.name for p in places))
    for text in words:
        map_kit.check_copy(text)
    map_kit.check_labels(labels(sk.beats, sk.end))


def darkest(day: datetime) -> int:
    """The fewest of the seven towns lit at any five-minute step of ``day``."""
    steps = (day + timedelta(minutes=5 * k) for k in range(288))
    return min(sum(map_kit.lit(town, moment) for town in TOWNS) for moment in steps)


def no_desk(cv, parent) -> None:
    """A map stands on nothing."""


def _at(beats) -> dict[str, float]:
    return {name: sketch.events(beats, name)[0][0] for name in EVENTS}


def labels(beats, end: float) -> list[tuple[float, float, str]]:
    """What is lettered on screen, when: the caption, the stamps and the pins. The clocks letter nothing."""
    at = _at(beats)
    return [
        (0.0, end, "caption"),
        (at["nots"], at["tiny"], "stamp"),
        (at["sun"], at["lunch"], "stamp"),
        (at["nots"], at["tiny"], FRANCE.name),
        (at["tahiti"], at["border"], TAHITI.name),
        (at["reunion"], at["border"], REUNION.name),
        (at["border"], at["what"], GUIANA.name),
        (at["border"], at["what"], BRAZIL.name),
    ]


def hours() -> list[float]:
    """What each of France's clocks reads at one moment, on the 24-hour count."""
    return [(MOMENT_UTC + offset) % 24.0 for offset in OFFSETS]


def _globe(shot, end: float, at) -> None:
    """The globe turning to stop on France on the first line's last word, then held there."""
    cv = shot.cv
    map_kit.ground(cv, shot.back)
    stop = at["nots"] - 0.1
    spin = [(0.0, SPIN_FROM), (stop, FRANCE.lon), (end, FRANCE.lon)]
    view = map_kit.globe(cv, shot.back, SPIN_FROM, TILT, 0.0, end, spin=spin, id="spin")
    cv.keys(view, "centerLat", [(0.0, TILT), (stop, FRANCE.lat)], hold=False, local=False)
    map_kit.pin(cv, shot.front, view, FRANCE, stop, end, shot.measure, side="below", id="pin-france", figure=False)
    map_kit.stamp(cv, shot.front, COUNT, at["nots"], end, shot.measure, id="count-stamp")


def _islands(shot, start: float, end: float, at) -> None:
    """The world, the pins on the far side of it, and the flight to the border."""
    cv = shot.cv
    fly = Move(at["border"], FLY, -53.0, 3.0, BORDER_ZOOM, rho=1.2)
    view = map_kit.flat(cv, shot.back, 0.0, 0.0, WORLD_ZOOM, start, end, moves=(fly,), id="world")
    for n, (place, side, begin, stop) in enumerate(
        (
            (TAHITI, "below", at["tahiti"], at["border"]),
            (REUNION, "below", at["reunion"], at["border"]),
            (GUIANA, "above", at["border"] + FLY, end),
            (BRAZIL, "below", at["border"] + FLY, end),
        )
    ):
        map_kit.pin(cv, shot.front, view, place, begin, stop, shot.measure, side=side, id=f"pin-{n}", figure=False)


def _twelve(shot, start: float, end: float, at) -> None:
    """Twelve clocks at one moment, each arriving on its own beat; the twelfth dims on Russia's eleven."""
    cv = shot.cv
    cv.rect(cv.group(shot.back, cv.uid("g"), start=start, end=end), 0, 0, cv.width, cv.height, map_kit.SEA)
    arrive = (at["eleven"] - start - 0.3) / len(OFFSETS)
    for n, hour in enumerate(hours()):
        x = 540.0 + (n % 3 - 1) * CLOCK_GAP
        y = GRID_TOP + (n // 3) * CLOCK_GAP
        face = map_kit.clock(cv, shot.front, x, y, CLOCK_R, hour, start + n * arrive, end, id=f"clock-{n}")
        if n == len(OFFSETS) - 1:
            cv.keys(face, "opacity", [(at["eleven"], 1.0), (at["eleven"] + 0.3, DIMMED)], hold=False, local=False)


def _sun(shot, start: float, end: float) -> None:
    """One real day over the seven towns, with a clock running through it."""
    cv = shot.cv
    view = map_kit.flat(cv, shot.back, 0.0, 0.0, WORLD_ZOOM, start, end, id="sun-map", borders=False)
    map_kit.daylight(cv, shot.front, view, TOWNS, WORST_DAY, start, end)
    map_kit.clock(cv, shot.front, *RUN_AT, RUN_R, 0.0, start, end, runs=24.0, id="sun-clock", pop=False)
    map_kit.stamp(cv, shot.front, SUN_STAMP, start, end, shot.measure, id="sun-stamp")


def _behind(shot, lon: float, lat: float, zoom: float, id: str) -> None:
    """The map behind the hamster, where the last shot left him."""
    map_kit.flat(shot.cv, shot.back, lon, lat, zoom, shot.app.start, shot.app.end, id=id)
    _floor(shot)


def _floor(shot) -> None:
    """The ground he stands on, in front of his feet."""
    cv = shot.cv
    cv.rect(cv.group(shot.front, cv.uid("g")), -20.0, FLOOR_Y, cv.width + 40.0, 700.0, map_kit.LAND, map_kit.INK, 8.0)


def _ring(shot) -> None:
    """The hamster on the map's land, with every clock France owns round him, all wrong for lunch."""
    cv = shot.cv
    cv.rect(cv.group(shot.back, cv.uid("g")), 0, 0, cv.width, cv.height, map_kit.SEA)
    _floor(shot)
    for n, hour in enumerate(hours()):
        turn = math.tau * (n + 0.5) / len(OFFSETS)
        x = RING_AT[0] + RING_R * math.sin(turn)
        y = RING_AT[1] - RING_TALL * math.cos(turn)
        map_kit.clock(cv, shot.back, x, y, SMALL_R, hour, shot.app.start, shot.app.end, id=f"ring-{n}", pop=False)


def dress(shot) -> None:
    """Each shot from the events: a map cut where the narration turns, or the hamster where it has got to."""
    at = _at(shot.beats)
    app = shot.app
    if app.who == "hamster":
        if app.start < at["islands"]:
            _behind(shot, 8.0, 48.0, EUROPE_ZOOM, "europe")
        elif app.start < at["clocks"]:
            _behind(shot, -53.0, 3.0, BORDER_ZOOM, "border-again")
        else:
            _ring(shot)
    elif app.start < at["tiny"]:
        _globe(shot, app.end, at)
    elif app.start < at["what"]:
        _islands(shot, app.start, app.end, at)
    else:
        _twelve(shot, app.start, at["sun"], at)
        _sun(shot, at["sun"], app.end)
    map_kit.sign(shot.cv, shot.front)


def foley(beats, end, speech, root, seed) -> list[dict]:
    """A tick for each clock and for the day going by, a pop for each pin, a whoosh for the flight. No bed."""
    audio = root / "audio"
    audio.mkdir(parents=True, exist_ok=True)
    at = _at(beats)
    arrive = (at["eleven"] - at["clocks"] - 0.3) / len(OFFSETS)
    day = (at["lunch"] - at["sun"]) / 24
    ticks = [at["clocks"] + k * arrive for k in range(len(OFFSETS))] + [at["sun"] + k * day for k in range(24)]
    pins = [at["nots"] - 0.1, at["tahiti"], at["reunion"], at["border"] + FLY, at["border"] + FLY + 0.02]
    rows = {
        "ticks": (map_kit.write_ticks(audio / "ticks.wav", ticks, end, seed=seed), -13.0),
        "pops": (map_kit.write_pops(audio / "pops.wav", pins, end, seed=seed), -11.0),
        "whoosh": (synth.write_whoosh(audio / "whoosh.wav", [0.0, at["border"]], end, seed=seed), -13.0),
    }
    return [sketch.effect(name, 0.0, gain, root, path) for name, (path, gain) in rows.items()]
