"""Further North — a pilot of the Maps channel, main trigger recognition of being wrong: the sketch as data.

"Which is further north: Rome, or New York City?" A globe turns with two pins on it, and the viewer has until the ticks
stop to commit. Then the globe falls towards Rome, the picture cuts to a map on which higher means further north, and a
line drawn west from Rome passes over New York City. It does it three more times, each more insulting than the last:
Paris over Montreal, London over Calgary by about fifty kilometers, Oslo over the capital of Alaska. The last frame
is the first, so the viewer can try it on somebody else.

The narrator is ElevenLabs premade Bella in the channel's own constant, heard only. ``SKETCH`` is checked by
:func:`srstudio.sketch.check`; :func:`validate` checks the events and every word on screen; :func:`dress` draws the
reel, one shot from the events, so the camera follows the recording; :func:`foley` its sound. Every latitude is a
GeoNames record, rounded in one place (:class:`srstudio.map_kit.Place`), and traces to
``pilots/maps/further-north/sources.md``.
"""

from __future__ import annotations

from dataclasses import dataclass, replace

from srstudio import foley as synth
from srstudio import map_kit, scripting, sketch
from srstudio.map_kit import CARD, Dive, Move, Place
from srstudio.sketch import Line, Sketch
from srstudio.social import InstagramPost
from srstudio.thumbnail import Thumbnail

SEED = 3201
SLUG = "further-north"
OUTPUT = f"renders/pilots/{SLUG}.mp4"
TITLE = "Further North — Maps"
DESCRIPTION = (
    "A pilot about the map in your head: the viewer guesses whether Rome or New York City is further north, and four "
    "lines of latitude drawn across the Atlantic show which European capitals sit above which North American cities."
)
ACCESSIBILITY = (
    "A globe turns with pins on Rome and New York City and a question over it. It falls towards Rome and cuts to a "
    "flat map. A red line runs west from Rome and passes above New York City, the two latitudes on labels. The same "
    "happens for Paris and Montreal, London and Calgary, and Oslo and Juneau. The globe and the question come back."
)
NARRATION = "Voiced with ElevenLabs premade voice Bella (narrator); synthesised effects."
NOTE = "ElevenLabs premade voice Bella at her natural pace; no reference-voice cloning."
STAMP = "Latitudes rounded to 0.1°. GeoNames, 2026."
PROJECTIONS = "Orthographic globe, then equirectangular."

# GeoNames cities15000, downloaded 2026-10-31: sources.md gives each record's id.
ROME = Place("Rome", 41.89193, 12.51133)
NEW_YORK_CITY = Place("New York City", 40.71427, -74.00597)
PARIS = Place("Paris", 48.85341, 2.3488)
MONTREAL = Place("Montreal", 45.50884, -73.58781)
LONDON = Place("London", 51.50853, -0.12574)
CALGARY = Place("Calgary", 51.05011, -114.08529)
OSLO = Place("Oslo", 59.91273, 10.74609)
JUNEAU = Place("Juneau", 58.30194, -134.41972)


@dataclass(frozen=True)
class Pair:
    """A European city, a North American one south of it, and how close the camera looks at them."""

    over: Place
    under: Place
    px: float  # frame pixels to a degree
    side: str = "right"  # where the label of the city to the east sits

    @property
    def lat(self) -> float:
        """The camera's latitude, halfway between the two, so the gap sits mid-frame."""
        return (self.over.lat + self.under.lat) / 2


PAIRS = (
    Pair(ROME, NEW_YORK_CITY, 72.0),
    Pair(PARIS, MONTREAL, 40.0),
    Pair(LONDON, CALGARY, 120.0),
    Pair(OSLO, JUNEAU, 60.0),
)
WHERE = ("rome", "paris", "london", "oslo")  # the event a pair starts on, on the first word that names it
LAND = ("nyc", "montreal", "calgary", "juneau")  # the event its pin lands on
TURN_FROM, TURN_TO = -38.0, -26.0  # the first frame's longitude, and where it has turned to when the answer comes
TILT = 30.0
HOME_TURN = 8.0  # degrees it turns through coming home, ending on the first frame's longitude
DIVE, DIVE_ZOOM = 1.3, 2.5  # seconds and zoom of the fall towards Rome: any faster and the coasts flash
CUT, FLY_WEST, DRAWN = 0.04, 1.5, 0.45  # seconds of the jump to the next pair, of a flight, of a line drawing
LEAD = 0.3  # seconds a city stands alone before its line starts, after Rome, whose line is on the word
PIN_READ = 0.85  # seconds a label is up before it hands over: the strict encode's shortest reading time
RHO = 1.7  # how far a flight pulls out: far enough to see an ocean go by
TICKS = 3
END = 25.0

LINES = (
    Line("narrator", "Which is further north: Rome, or New York City?"),
    Line("narrator", "Lock it in."),
    Line("narrator", "Rome. Yes, the sunny one."),
    Line("narrator", "Draw a line west from Rome. It passes north of New York City."),
    Line("narrator", "Paris? Further north than Montreal."),
    Line("narrator", "London? Further north than Calgary, by about fifty kilometers."),
    Line("narrator", "Oslo? Further north than Juneau, the capital of Alaska."),
    Line("narrator", "Yes. That Alaska."),
    Line("narrator", "So. One more time. Which is further north?"),
)

script = scripting.Script(LINES)
hold, say = script.hold, script.say
FACE = ("wide", "flat", "desk")  # nobody is drawn on a map shot, and a beat still says who it is for


def on_word(start: float, line: int, word: int, event: str) -> sketch.Beat:
    """A beat of a line that lands on one of its words, however the recording falls."""
    return replace(say(start, CARD, line, *FACE, event), word=word)


BEATS = (
    say(0.0, CARD, 0, *FACE),
    say(3.1, CARD, 1, *FACE, "lock"),
    say(4.6, CARD, 2, *FACE, "rome"),
    on_word(6.1, 3, 1, "line"),
    on_word(8.1, 3, 8, "nyc"),
    say(9.9, CARD, 4, *FACE, "paris"),
    on_word(11.9, 4, 4, "montreal"),
    say(12.9, CARD, 5, *FACE, "london"),
    on_word(14.9, 5, 4, "calgary"),
    say(16.9, CARD, 6, *FACE, "oslo"),
    on_word(18.9, 6, 4, "juneau"),
    say(20.5, CARD, 7, *FACE),
    say(21.8, CARD, 8, *FACE, "home"),
    hold(24.4, CARD, LINES[0].text, *FACE, "first"),
)
SKETCH = Sketch(SLUG, TITLE, (map_kit.NARRATOR,), LINES, BEATS, END, cast=map_kit.MAPS_CAST)
EVENTS = ("lock", "rome", "line", "nyc", "paris", "montreal", "london", "calgary", "oslo", "juneau", "home", "first")
TINTS = {"narrator": map_kit.PAPER}
MOUTH = sketch.MOUTH_STYLE
VERSIONS: dict[str, int] = {}
POST = InstagramPost(
    title="Rome or New York City: which is further north?",
    description=(
        "Oslo is further north than the capital of Alaska. Paris, than Montreal. London, than Calgary. Why so mild? "
        f"Winter winds off the Atlantic.\nSource: GeoNames, 2026, latitudes rounded to 0.1°. {PROJECTIONS}"
    ),
    credit="Coordinates: GeoNames (geonames.org), CC BY 4.0. Made with Natural Earth. Voice: ElevenLabs premade Bella.",
    hashtags=("#maps", "#geography", "#didyouknow", "#tryit"),
    thumbnail=Thumbnail("Further\nnorth?", 1.0, "Rome or New York City", zoom=1.0, place="bottom"),
)


def validate(sk: Sketch = SKETCH) -> None:
    """The sketch is consistent, each event happens once and in order, the first picture speaks, each American city is
    south of its European one, and no word on screen is one the channel keeps off it."""
    sketch.check(sk)
    for event in EVENTS:
        scripting.exactly_once(sk.beats, event, f"{event} happens once")
    scripting.only_events(sk.beats, set(EVENTS))
    times = [sketch.events(sk.beats, event)[0][0] for event in EVENTS]
    if times != sorted(times):
        raise sketch.SketchError(f"the events run {EVENTS}")
    if sk.beats[0].line is None:
        raise sketch.SketchError("the reel opens on the question, with its line")
    for pair in PAIRS:
        if not pair.over.lat > pair.under.lat:
            raise sketch.SketchError(f"{pair.over.name} has to be north of {pair.under.name}")
    for text in (
        *(q.text for q in sk.lines),
        STAMP,
        PROJECTIONS,
        POST.title,
        POST.description,
        *(place.name for pair in PAIRS for place in (pair.over, pair.under)),
    ):
        map_kit.check_copy(text)
    map_kit.check_labels(labels(sk.beats, sk.end))


def no_desk(cv, parent) -> None:
    """A map stands on nothing."""


def _at(beats) -> dict[str, float]:
    return {name: sketch.events(beats, name)[0][0] for name in EVENTS}


def line_at(at: dict[str, float], i: int) -> float:
    """When the line of pair ``i`` starts running."""
    return at["line"] if i == 0 else at[WHERE[i]] + LEAD


def flies_at(at: dict[str, float], i: int) -> float:
    """When the camera leaves along it."""
    return line_at(at, i) + DRAWN * 0.6


def hands_at(at: dict[str, float], i: int) -> float:
    """When the tag on the line takes the name from the pin, which has been up long enough to read."""
    begins = at["rome"] + DIVE if i == 0 else at[WHERE[i]]
    return max(flies_at(at, i), begins + PIN_READ)


def lands_at(at: dict[str, float], i: int) -> float:
    """When the pin of the city under the line lands: on its word, or when the camera gets there if that is later."""
    return max(at[LAND[i]], flies_at(at, i) + FLY_WEST)


def labels(beats, end: float) -> list[tuple[float, float, str]]:
    """What is lettered on screen, when: the caption, the stamp, and the labels of the pair in view."""
    at = _at(beats)
    home = at["home"]
    spans = [(0.0, end, "caption"), (at["rome"], home, "stamp"), (0.0, at["rome"], "Rome"), (0.0, at["rome"], "NYC")]
    for i, pair in enumerate(PAIRS):
        leaves = at[WHERE[i + 1]] if i + 1 < len(PAIRS) else home
        spans += [
            (at[WHERE[i]], leaves, pair.over.name),
            (line_at(at, i), leaves, f"{pair.over.name} line"),
            (lands_at(at, i), leaves, pair.under.name),
        ]
    return spans


def moves(at: dict[str, float]) -> list[Move]:
    """The camera: along each line to the city under it, then a cut to the next pair. Flown back across the ocean, the
    land and the sea swapped over most of the frame too often in a second for the strict encode's flash check."""
    out = []
    for i, pair in enumerate(PAIRS):
        zoom = map_kit.zoom_for_degree(pair.px)
        if i:
            out.append(Move(at[WHERE[i]] - CUT, CUT, pair.over.lon, pair.over.lat, zoom, RHO))
        out.append(Move(flies_at(at, i), FLY_WEST, pair.under.lon, pair.lat, zoom, RHO))
    return out


def dress(shot) -> None:
    """The globe, the fall towards Rome, the flat map with its four lines, and the globe again."""
    cv, back, front = shot.cv, shot.back, shot.front
    at = _at(shot.beats)
    answer, home, measure = at["rome"], at["home"], shot.measure
    fallen = answer + DIVE
    map_kit.ground(cv, back)
    dive = Dive(answer, DIVE, ROME.lon, ROME.lat, DIVE_ZOOM)
    ball = map_kit.globe(
        cv, back, TURN_FROM, TILT, 0.0, fallen, spin=[(0.0, TURN_FROM), (answer, TURN_TO)], dive=dive, id="ball"
    )
    px = map_kit.globe_degree_px(DIVE_ZOOM)
    view = map_kit.flat(
        cv, back, ROME.lon, ROME.lat, map_kit.zoom_for_degree(px), fallen, home, moves=moves(at), id="flat"
    )
    returned = map_kit.globe(
        cv,
        back,
        TURN_FROM - HOME_TURN,
        TILT,
        home,
        shot.end,
        spin=[(home, TURN_FROM - HOME_TURN), (at["first"], TURN_FROM), (shot.end, TURN_FROM)],
        id="back",
    )
    for spanning, start, end, name in ((ball, 0.0, answer, "ask"), (returned, home, shot.end, "asked")):
        for place, city in ((ROME, "rome"), (NEW_YORK_CITY, "nyc")):  # above: to a side, a label would hide its pin
            map_kit.pin(
                cv,
                front,
                spanning,
                place,
                start,
                end,
                measure,
                side="above",
                id=f"{name}-{city}",
                figure=False,
                pop=False,
            )
    map_kit.pin(cv, front, ball, ROME, answer, fallen, measure, id="fall-rome")
    for i, pair in enumerate(PAIRS):
        leaves = at[WHERE[i + 1]] if i + 1 < len(PAIRS) else home
        first = i == 0
        begins = fallen if first else at[WHERE[i]]
        hands = hands_at(at, i)  # the pin stays behind, and the tag carries its name along the line
        map_kit.pin(cv, front, view, pair.over, begins, hands, measure, side=pair.side, id=f"over-{i}", pop=not first)
        map_kit.parallel(cv, front, view, pair.over, line_at(at, i), leaves, drawn=DRAWN, tag_from=hands,
                         measure=measure, id=f"line-{i}")  # fmt: skip
        map_kit.pin(cv, front, view, pair.under, lands_at(at, i), leaves, measure, side="below", id=f"under-{i}")
    map_kit.stamp(cv, front, STAMP, answer, home, measure)
    map_kit.sign(cv, front)


def foley(beats, end, speech, root, seed) -> list[dict]:
    """Ticks while the viewer commits, a pop on each pin, and a whoosh on each flight."""
    audio = root / "audio"
    audio.mkdir(parents=True, exist_ok=True)
    at = _at(beats)
    lock = at["lock"]
    ticks = map_kit.write_ticks(audio / "ticks.wav", [lock + 0.05 + i * 0.4 for i in range(TICKS)], end, seed=seed)
    pairs = range(len(PAIRS))
    pops = map_kit.write_pops(
        audio / "pops.wav", sorted([*(at[name] for name in WHERE), *(lands_at(at, i) for i in pairs)]), end, seed=seed
    )
    whoosh = synth.write_whoosh(audio / "whoosh.wav", [flies_at(at, i) for i in pairs], end, seed=seed)
    return [
        sketch.effect("ticks", 0.0, -9.0, root, ticks),
        sketch.effect("pops", 0.0, -10.0, root, pops),
        sketch.effect("whoosh", 0.0, -13.0, root, whoosh),
    ]
