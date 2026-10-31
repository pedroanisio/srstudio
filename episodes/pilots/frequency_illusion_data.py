"""The Frequency Illusion — a pilot of "There's a Name for That", main trigger curiosity gap: the sketch as data.

The week you buy something you think makes you different, you see it everywhere and take it personally. A dog keeps a
tally on his dashboard of the yellow cars he has seen since Tuesday, which is the day he bought his. A frog asks. A
school bus goes by and he counts it. There's a name for that. Then why, and what the evidence can honestly hold, which
is one story from the post that named it and no direct test. And then it has happened to him again: it's the illusion
he now hears about everywhere, the pad reads ten, and the loop's first line is "That's eleven."

Text on screen carries every key point, for a muted viewer. The narrator is the channel's voice, ElevenLabs premade
Bella; the two characters are ElevenLabs premade Charlie and Matilda. ``SKETCH`` is checked by
:func:`srstudio.sketch.check`; :func:`validate` checks the events and every word on screen against
:func:`srstudio.mind_kit.check_copy`; :func:`dress` draws each shot and :func:`foley` its sound.

Every claim traces to ``pilots/mind/frequency-illusion/sources.md``. There is no study of the illusion itself, so
:data:`STORY` holds a story and says whose it is, and a line says plainly that no direct test was found. The counts on
the pad are the dog's: eleven, twelve, Tuesday and Friday are character detail, and no line says they were measured.
Yellow cars are an illustration, no study used them, and no line says yellow cars are no more common than before.
"""

from __future__ import annotations

from dataclasses import replace

from srstudio import camera, look, mind_kit, scripting, sketch, toon, toon_cars, toon_house, toon_world
from srstudio import foley as synth
from srstudio.mind_kit import CARD, CORAL, DIM, SPOT, STAGE
from srstudio.sketch import Line, Sketch, Speaker
from srstudio.social import InstagramPost
from srstudio.thumbnail import Thumbnail
from srstudio.toon_cars import BODY, GREY, Passing
from srstudio.voice import Voice, VoiceSettings

SEED = 3301
SLUG = "frequency-illusion"
OUTPUT = f"renders/pilots/{SLUG}.mp4"
TITLE = "The Frequency Illusion — There's a Name for That"
NAME = "The Frequency Illusion"
DESCRIPTION = (
    "A pilot about how people think: a dog counts yellow cars the week he buys one, and the effect behind that "
    "feeling is named, shown and held to what the evidence can say."
)
ACCESSIBILITY = (
    "A cartoon dog at the wheel of a yellow car adds a stroke to a tally pad on the dashboard as a yellow car goes "
    "past the window. A frog beside him asks what he is counting. He says yellow cars, since Tuesday, the day he "
    "bought his. A school bus goes past and he counts that too. A card reads There's a name for that, The Frequency "
    "Illusion. Cars cross a dark stage under a yellow lens and only the yellow ones get a stroke, then the bus, then "
    "a banana. A paper card tells one story from the post that named the illusion in 2005. Back in the car, the dog "
    "says everyone has been talking about it since Friday, the frog says that is when he heard of it, and he adds a "
    "stroke, the tenth."
)
NARRATION = "Voiced with ElevenLabs premade voices Bella (narrator), Charlie and Matilda; synthesised effects."
NOTE = "ElevenLabs premade voices Bella, Charlie and Matilda at their natural pace; no reference-voice cloning."

# Zwicky 2005, "Just between Dr. Language and I", Language Log, 7 Aug 2005, post body (a web post has no pages):
# "the frequency of quotative all is very low", and no number published. sources.md, claims 1 and 6.
STORY_NOTE = ("One story from the post that named it.", "Not a study of the illusion.")
STORY = mind_kit.Evidence(
    "Arnold Zwicky, who named it, on Language Log",
    "2005",
    "A Stanford group thought one speech habit was very common.",
    "Transcripts showed it was rare.",
)
ATTENTION = "selective attention"  # Zwicky 2006, abstract p. 1; sources.md, claim 4
BIAS = "confirmation bias"  # the same page

NARRATOR = mind_kit.NARRATOR
DOG = Speaker(
    "dog",
    Voice(role="dog", id="IKne3meq5aSn9XLyUdCD", name="Charlie"),
    VoiceSettings(stability=0.40, similarity_boost=0.75, style=0.40),
    "dog",
)
FROG = Speaker(
    "frog",
    Voice(role="frog", id="XrExE9yKIg1WjnnlVkGX", name="Matilda"),
    VoiceSettings(stability=0.50, similarity_boost=0.75, style=0.30),
    "frog",
)
TINTS = {"dog": mind_kit.SPOT, "frog": mind_kit.SPOT, "narrator": mind_kit.INK}
MOUTH = replace(sketch.MOUTH_STYLE, spelling=True, close_bilabials=True, lead=0.04, min_rest=0.12)
VERSIONS = {"toon-dog": 2, "toon-frog": 2}
FIGURES = {"dog": (1.3, -20.0), "frog": (1.2, 225.0)}

DOG_COAT = "#e9a05c"
SEAT_X = {"dog": 145.0, "frog": 400.0}
PAD_AT, PAD_SCALE = (330.0, 672.0), 0.85
WHEEL_AT = (145.0, 860.0)
FIRST_COUNT, LAST_COUNT = 10, 9  # the strokes on the page in the first frame and in the last, before the last is added
LENS_AT, LENS_RADIUS = (540.0, 880.0), 250.0
LANE, LANE_SCALE, LANE_SPEED = 680.0, 0.7, 420.0  # the stage's traffic: reference ground, size, reference px a second
STAGE_PAD_AT, STAGE_PAD_SCALE = (160.0, 728.0), 0.9
DIM_CAR = "#6a7183"  # the cars nobody counts, kept back on the dark stage
PARADE_GAP = 1.2  # seconds between two things crossing the lens, so it holds one at a time
LABEL_Y, LABEL_SIZE = 500.0, 64.0
NOTE_Y, NOTE_SIZE = 960.0, 50.0
PUNCH, PIVOT = 1.1, (1000.0, 1420.0)  # the pivot this far right keeps the marks in frame

LINES = (
    Line("dog", "That's eleven."),
    Line("frog", "Eleven what?"),
    Line("dog", "Yellow cars. Since Tuesday."),
    Line("frog", "You bought yours on Tuesday."),
    Line("dog", "I paid extra for this color."),
    Line("dog", "Twelve."),
    Line("frog", "That was a school bus."),
    Line("dog", "Long one."),
    Line("narrator", "Why are they suddenly everywhere?"),
    Line("narrator", "There's a name for that."),
    Line("narrator", "The frequency illusion."),
    Line("narrator", "Once you've noticed something, you think it happens a whole lot."),
    Line("narrator", "You catch nearly every one that passes."),
    Line("narrator", "And each one feels like proof."),
    Line("narrator", "A Stanford group thought one speech habit was very common."),
    Line("narrator", "Transcripts showed it was rare."),
    Line("narrator", "The name is recent. The attention research behind it isn't."),
    Line("narrator", "We found no direct test of this one."),
    Line("narrator", "Now you know the name."),
    Line("dog", "Everyone's been talking about it since Friday."),
    Line("frog", "You heard about it on Friday."),
    Line("dog", "That's ten."),
)

script = scripting.Script(LINES)
hold, say = script.hold, script.say


def on_card(beat: sketch.Beat) -> sketch.Beat:
    """A line whose words the card already shows, so no caption repeats them."""
    return replace(beat, caption="")


BEATS = (
    say(0.0, "dog", 0, "side", "flat", "desk"),  # already counting, with the car still in the window
    say(1.15, "frog", 1, "side", "flat", "desk"),
    say(2.1, "dog", 2, "side", "grin", "desk", "yellow"),
    say(4.2, "frog", 3, "half", "flat", "desk"),
    say(6.1, "dog", 4, "up", "flat", "desk", "paid"),
    hold(7.7, "dog", "", "side", "flat", "desk", "bus"),  # the silence is the bus going by
    say(9.2, "dog", 5, "side", "grin", "desk", "twelve"),
    say(10.0, "frog", 6, "half", "flat", "desk"),
    say(11.4, "dog", 7, "side", "flat", "desk", "long"),
    hold(12.2, "frog", "", "half", "flat", "desk"),  # the silence is the laugh
    say(13.0, "dog", 8, "side", "frown", "desk", "why"),
    on_card(say(15.0, CARD, 9, "wide", "flat", "desk", "name")),
    on_card(say(16.45, CARD, 10, "wide", "flat", "desk", "reveal")),
    say(18.2, STAGE, 11, "half", "flat", "desk", "lens"),
    say(21.65, STAGE, 12, "half", "flat", "desk", "attention"),
    say(24.1, STAGE, 13, "half", "flat", "desk", "bias"),
    on_card(say(26.5, CARD, 14, "wide", "flat", "desk", "story")),
    on_card(say(29.8, CARD, 15, "wide", "flat", "desk", "rare")),
    say(32.0, "frog", 16, "half", "flat", "desk", "recent"),
    say(35.6, "dog", 17, "side", "smirk", "desk", "untested"),
    say(37.85, "frog", 18, "half", "flat", "desk"),
    say(39.2, "dog", 19, "side", "flat", "desk", "friday"),
    say(41.25, "frog", 20, "half", "flat", "desk"),
    hold(42.7, "frog", "", "half", "flat", "desk"),
    say(42.95, "dog", 21, "side", "flat", "desk", "ten"),
)
END = 44.45
SKETCH = Sketch(SLUG, TITLE, (NARRATOR, DOG, FROG), LINES, BEATS, END, cast=mind_kit.MIND_CAST)
EVENTS = (
    "yellow", "paid", "bus", "twelve", "long", "why", "name", "reveal", "lens", "attention", "bias", "story", "rare",
    "recent", "untested", "friday", "ten",
)  # fmt: skip


def validate(sk: Sketch = SKETCH) -> None:
    """The sketch is consistent, each event happens once and in order, the first picture speaks, and no word on
    screen is one the channel keeps off it."""
    sketch.check(sk)
    for event in EVENTS:
        scripting.exactly_once(sk.beats, event, f"{event} happens once")
    scripting.only_events(sk.beats, set(EVENTS))
    times = [sketch.events(sk.beats, event)[0][0] for event in EVENTS]
    if times != sorted(times):
        raise sketch.SketchError(f"the events run {EVENTS}")
    if sk.beats[0].line is None:
        raise sketch.SketchError("the reel opens on the behaviour, with its line")
    for text in (
        *(q.text for q in sk.lines),
        NAME,
        STORY.who,
        STORY.what,
        STORY.result,
        *STORY_NOTE,
        ATTENTION,
        BIAS,
        POST.title,
        POST.description,
    ):
        mind_kit.check_copy(text)


def no_desk(cv, parent) -> None:
    """Each shot lays its own surface: see :func:`dress`."""


def _traffic(app, at: dict[str, float]) -> tuple[Passing, ...]:
    """What goes past the glass in a shot: a yellow car already going by as the reel opens, the bus at its beat, and
    yellow ones thick and fast as the narrator asks why."""
    plan = [
        Passing(0.5, "car", BODY),
        Passing(at["yellow"] + 0.6, "car", BODY),
        Passing(at["paid"] + 0.5, "car", GREY),
        Passing(at["bus"] + 0.7, "bus"),
        Passing(at["why"] + 0.5, "car", BODY),
        Passing(at["why"] + 1.5, "car", BODY),
        Passing(at["recent"] + 1.0, "car", GREY),
    ]
    return tuple(p for p in plan if app.start <= p.at < app.end)


def _page(app, at: dict[str, float]) -> tuple[int, tuple[float, ...]]:
    """The strokes on the page in a shot, and when any more land: the page the reel opens on, then Friday's, whose
    last stroke leaves it as the first frame's page starts."""
    if app.start >= at["friday"]:
        return LAST_COUNT, (at["ten"] + PEN_DOWN,) if app.start <= at["ten"] < app.end else ()
    if app.start == 0.0:
        return FIRST_COUNT, (PEN_DOWN,)
    if app.start <= at["twelve"]:
        return FIRST_COUNT + 1, (at["twelve"] + PEN_DOWN,) if at["twelve"] < app.end else ()
    return FIRST_COUNT + 2, ()


def _pad(shot, at: dict[str, float]) -> None:
    """The count on the dashboard, and the dog's arm reaching over for each stroke."""
    cv, app = shot.cv, shot.app
    count, strokes = _page(app, at)
    toon_cars.tally_pad(cv, shot.front, PAD_AT, count, strokes, PAD_SCALE, id=cv.uid("pad"))
    for t in strokes:
        foot, top = toon_cars.stroke_line(count)  # the pencil's point lands on the stroke it adds
        point = (PAD_AT[0] + PAD_SCALE * (foot[0] + top[0]) / 2, PAD_AT[1] + PAD_SCALE * (foot[1] + top[1]) / 2)
        toon_world.paw(
            cv,
            shot.front,
            ((max(app.start, t - 0.3), min(t + 0.42, app.end)),),
            coat=DOG_COAT,
            side=-1.0,
            y=point[1] - toon_world.PENCIL_DROP + 4.0,
            reach=point[0] - toon_world.PENCIL_REACH,
            holding="pencil",
        )


PEN_DOWN = 0.35  # seconds after the word starts that the stroke lands


def _car(shot, at: dict[str, float]) -> None:
    cv, app = shot.cv, shot.app
    who = app.who
    toon_cars.car_inside(cv, mind_kit.far(cv, shot.back), app.start, app.end, _traffic(app, at))
    toon_cars.seat(cv, shot.back, SEAT_X[who])
    if who == "dog":
        mind_kit.key(cv, shot.light)
    else:  # she sits by the window the key comes from, and at its full strength it would bleach her eyes
        look.pool(cv, shot.light, "mind-key-near", "#fff1c4AA", 700, 180, 900, 1000, opacity=0.18)
        look.fade(cv, shot.light, "mind-contact", "#2a1a4a66", toon.fy(801), toon.fy(801) - 60.0, cv.width)
    if who == "dog":
        toon_cars.steering_wheel(cv, shot.front, WHEEL_AT)
    toon_house.ledge(cv, shot.front, "dash")
    toon_cars.dash_vents(cv, shot.front)
    if who == "dog":
        _pad(shot, at)


def _text(cv, parent, text: str, y: float, size: float, colour: str) -> None:
    """One line of the channel's letters, centred in the safe width."""
    width = round(mind_kit.SAFE_WIDTH)
    cv.text(parent, cv.uid("mind-text"), text, mind_kit.SAFE_LEFT, y, width, round(1.4 * size), size, color=colour,
            align="center", wrap="none")  # fmt: skip


def _label(shot, text: str, start: float, end: float, colour: str) -> None:
    cv = shot.cv
    _text(cv, cv.group(shot.front, cv.uid("g"), start=start, end=end), text, LABEL_Y, LABEL_SIZE, colour)


def _parade(at: dict[str, float]) -> tuple[list[float], list[float], float, float]:
    """When each thing crosses the lens, one at a time and evenly over the shot: the cars take turns, grey and yellow,
    then the bus, then the banana."""
    first, last = at["lens"] + 0.3, at["story"] - 0.5
    step = (last - first) / 6
    times = [first + k * step for k in range(7)]
    return [times[0], times[2], times[4]], [times[1], times[3]], times[5], times[6]


def _mechanism(shot, at: dict[str, float]) -> None:
    """The lens over the traffic: grey cars go by uncounted, each yellow one earns a stroke, then a bus, a banana."""
    cv, app = shot.cv, shot.app
    lens, attention, bias, end = at["lens"], at["attention"], at["bias"], app.end
    grey, yellow, bus, fruit = _parade(at)
    mind_kit.stage(cv, shot.back)
    traffic = cv.group(shot.front, cv.uid("g"))
    for t in grey:
        toon_cars.drive_past(cv, traffic, Passing(t, "car", DIM_CAR), LANE, LANE_SCALE, LANE_SPEED)
    for t in yellow:
        toon_cars.drive_past(cv, traffic, Passing(t, "car", BODY), LANE, LANE_SCALE, LANE_SPEED)
    toon_cars.drive_past(cv, traffic, Passing(bus, "bus"), LANE, LANE_SCALE, LANE_SPEED)
    half = 300.0 / LANE_SPEED + 0.6
    item = cv.group(traffic, cv.uid("g"), start=fruit - half, end=fruit + half)
    cv.keys(
        item, "x", [(fruit - half, toon.fh(LANE_SPEED * half)), (fruit + half, -toon.fh(LANE_SPEED * half))], hold=False
    )
    toon_cars.banana(cv, item, (toon.REF_W / 2, LANE - 6.0), LANE_SCALE)
    mind_kit.lens(cv, shot.front, LENS_AT, lens, end, radius=LENS_RADIUS, id=cv.uid("lens"))
    _label(shot, ATTENTION, attention, bias, SPOT)
    _label(shot, BIAS, bias, end, CORAL)
    toon_cars.tally_pad(
        cv, shot.front, STAGE_PAD_AT, FIRST_COUNT + 2, sorted([*yellow, bus, fruit]), STAGE_PAD_SCALE, id=cv.uid("pad")
    )
    mind_kit.sign(cv, shot.front)


def dress(shot) -> None:
    """Every shot's set and props: the car for the behaviour, the stage for the name, the mechanism and the evidence,
    and the car again for the turn and the last frame, which is the first."""
    cv, app = shot.cv, shot.app
    at = {name: sketch.events(shot.beats, name)[0][0] for name in EVENTS}
    if app.who == CARD and app.start <= at["name"]:
        mind_kit.stage(cv, shot.back)
        mind_kit.name_card(cv, shot.front, NAME, app.start, at["reveal"], app.end, shot.measure, id=cv.uid("name"))
        mind_kit.sign(cv, shot.front)
    elif app.who == CARD:
        mind_kit.stage(cv, shot.back)
        mind_kit.evidence_card(
            cv, shot.front, STORY, app.start, app.end, shot.measure, id=cv.uid("story"), reveal=at["rare"]
        )
        note = cv.group(shot.front, cv.uid("g"), start=at["rare"], end=app.end)
        for k, words in enumerate(STORY_NOTE):
            _text(cv, note, words, NOTE_Y + k * 70.0, NOTE_SIZE, DIM)
        mind_kit.sign(cv, shot.front)
    elif app.who == STAGE:
        _mechanism(shot, at)
    else:
        _car(shot, at)


def lens(shot, setup) -> None:
    """A punch-in on the dog for "Long one."; everything else holds, and the road and the traffic do the moving."""
    punch = sketch.events(shot.beats, "long")[0][0]
    if shot.app.start <= punch < shot.app.end:
        camera.anchor(setup, *PIVOT, place=True)
        camera.zoom_holds(shot.cv, setup, [(0.0, 1.0), (punch, PUNCH)])


def foley(beats, end, speech, root, seed) -> list[dict]:
    """The channel's sting on the name, a soft whoosh for what goes by the glass, and the pencil on each stroke."""
    audio = root / "audio"
    audio.mkdir(parents=True, exist_ok=True)
    at = {name: sketch.events(beats, name)[0][0] for name in EVENTS}
    shots = [app for app in sketch.appearances(beats, end) if app.who in ("dog", "frog")]
    passes = sorted(p.at for app in shots for p in _traffic(app, at))
    grey, yellow, bus, fruit = _parade(at)
    strokes = sorted([PEN_DOWN, at["twelve"] + PEN_DOWN, at["ten"] + PEN_DOWN, *yellow, bus, fruit])
    sting = mind_kit.write_sting(audio / "sting.wav", [at["reveal"]], end)
    road = synth.write_whoosh(audio / "road.wav", [max(0.0, t - 0.3) for t in passes], end, seed=seed)
    pencil = synth.write_typing(audio / "pencil.wav", strokes, end, seed=seed)
    return [
        sketch.effect("sting", 0.0, -5.0, root, sting),
        sketch.effect("road", 0.0, -8.0, root, road),
        sketch.effect("pencil", 0.0, -12.0, root, pencil),
    ]


POST = InstagramPost(
    title="He has counted eleven yellow cars since Tuesday.",
    description=(
        "The frequency illusion: once you've noticed something, you think it happens a whole lot. Arnold Zwicky named "
        "it in 2005. We found no direct test of it; the attention research behind it is older than the name.\n"
        "Source: Zwicky (2005), Language Log; Zwicky (2006), Why are we so illuded?"
    ),
    credit="Voices: ElevenLabs premade voices Bella, Charlie and Matilda. Original characters, drawn in code.",
    hashtags=("#psychology", "#frequencyillusion", "#howpeoplethink", "#everydaylife"),
    thumbnail=Thumbnail("Eleven\nwhat?", 0.95, "There's a name for that", place="bottom"),
)
