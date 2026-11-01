"""Above Average — "There's a Name for That" #3, main trigger surprise: the sketch as data.

The observation: nobody thinks the bad driver is them, and a crash does not change that. So the claim comes first, in a
moving car, a bear rates himself top ten percent and nearly leaves the road. The narrator gives the number. Then a
bang, a hospital bed, and the finding that is the payoff: people who had caused the crash still rated themselves above
average. The rabbit asks again, and the bear blames the tree.

Every word about the studies lives in :data:`HOOK`, the two stamps and :data:`CRASH` and traces to
``pilots/mind/above-average/sources.md``. The bear, the rabbit and the tree are fiction with no study attached.
"""

from __future__ import annotations

from dataclasses import replace

from srstudio import (
    camera,
    look,
    mind_kit,
    scripting,
    sketch,
    toon,
    toon_cars,
    toon_everyday,
    toon_house,
    toon_rigs,
    toon_ward,
)
from srstudio import foley as synth
from srstudio.mind_kit import INK, SPOT
from srstudio.sketch import Line, Sketch, Speaker
from srstudio.social import InstagramPost
from srstudio.thumbnail import Thumbnail
from srstudio.toon_cars import Passing
from srstudio.voice import Voice, VoiceSettings

BLEED = True
SEED = 3703
SLUG = "above-average"
OUTPUT = f"renders/pilots/{SLUG}.mp4"
SERIES = "There's a Name for That #3"
TITLE = f"Above Average — {SERIES}"
NAME = "Better-than-average effect"
DESCRIPTION = (
    "A pilot about how people think: a bear rates his driving, crashes, and rates it again from a hospital bed."
)
ACCESSIBILITY = (
    "A cartoon bear drives a car with a rabbit beside him holding a clipboard. Asked to rate his driving he says top "
    "ten percent, and the car swerves with a blast of horn. A stamp reads 93% of US students above the median, "
    "Svenson, 1981. The rabbit says that is not how half works. A bang, and the bear is in a hospital bed in a "
    "bandage. A stamp reads 34 of 50 caused it, Preston & Harris, 1965, in Svenson, 1981. Asked again he says "
    "above average, "
    "and that the tree didn't signal."
)
NARRATION = "Voiced with ElevenLabs premade voices Bella (narrator), Bill and Sarah; synthesised effects."
NOTE = "ElevenLabs premade voices Bella, Bill and Sarah at their natural pace; no reference-voice cloning."

HOOK = "Most drivers say they're better than most drivers."
SAID = "Ninety-three percent of American students put themselves in the top half."
STAMP = ("93% of US students", "above the median.")
CITE = "Svenson, 1981"
CRASH = "So researchers asked drivers hospitalized by a crash."
CAUSED = "Most of them had caused it."
STAMP_CRASH = ("34 of 50 caused it.",)
CITE_CRASH = "Preston & Harris, 1965, in Svenson, 1981"
LAST = "The tree didn't signal."

NARRATOR = mind_kit.NARRATOR
BEAR = Speaker(
    "bear",
    Voice(role="bear", id="pqHfZKP75CvOlQylNhV4", name="Bill"),
    VoiceSettings(stability=0.55, similarity_boost=0.75, style=0.2),
    "bear",
)
RABBIT = Speaker(
    "rabbit",
    Voice(role="rabbit", id="EXAVITQu4vr4xnSDxMaL", name="Sarah"),
    VoiceSettings(stability=0.55, similarity_boost=0.75, style=0.2),
    "rabbit",
)
TINTS = {"bear": SPOT, "rabbit": SPOT, "narrator": INK}
MOUTH = replace(sketch.MOUTH_STYLE, spelling=True, close_bilabials=True, lead=0.04, min_rest=0.12)
VERSIONS = {"toon-bear": 2, "toon-rabbit": 2}
HEADS = ("bear", "rabbit")
FIGURES = {"bear": (1.3, -20.0), "rabbit": (1.2, 225.0)}
SEAT_X = {"bear": 145.0, "rabbit": 400.0}
WHEEL_AT = (145.0, 860.0)
RABBIT_PAW = "#d9c9c0"
BOARD_AT, BOARD_SCALE = (420.0, 800.0), 0.76
MOUTH_FOOT = 985.0  # frame px of the foot of her open mouth, read off the full-size frames: the clip stops under it
ANSWER = "Top 10%"
SWERVE = (0.0, -46.0, 38.0, -24.0, 14.0, 0.0)  # frame px of the shot sliding across the road
SWERVE_STEP = 0.09
SWERVE_SCALE = 1.12  # the slide never shows the edge of the shot
PUNCH, PIVOT = 1.2, (560.0, 800.0)
THUD = synth.Burst(seconds=0.2, low_hz=320.0, decay=0.3, tone_hz=120.0, tone_end_hz=60.0, tone=0.8)
HORN = ((311.1, 311.1, 0.16), (329.6, 329.6, 0.5))
MONITOR = ((987.8, 987.8, 0.09),)
MONITOR_EVERY = 1.1
END = 23.6

LINES = (
    Line("narrator", HOOK),
    Line("rabbit", "Rate your driving."),
    Line("bear", "Top ten percent."),
    Line("narrator", SAID),
    Line("rabbit", "That's not how half works."),
    Line("narrator", CRASH),
    Line("narrator", CAUSED),
    Line("rabbit", "Rate your driving.", gain=-3.0),
    Line("bear", "Above average."),
    Line("bear", LAST),
)
EVENTS = ("swerve", "stamp", "half", "bang", "ward", "caused", "again", "tree", "named")

script = scripting.Script(LINES)
hold, say = script.hold, script.say


def on_stamp(beat: sketch.Beat) -> sketch.Beat:
    """A line whose words the stamp already shows, so no caption repeats them."""
    return replace(beat, caption="")


BEATS = (
    say(0.0, "bear", 0, "side", "grin", "desk"),
    say(3.0, "rabbit", 1, "half", "flat", "desk"),
    say(4.4, "bear", 2, "half", "grin", "desk"),
    hold(5.7, "bear", "", "wide", "open", "desk", "swerve"),
    on_stamp(say(6.5, "rabbit", 3, "down", "flat", "desk", "stamp")),
    say(10.6, "rabbit", 4, "half", "flat", "desk", "half"),
    hold(12.2, "rabbit", "", "wide", "open", "desk", "bang"),
    say(12.9, "bear", 5, "closed", "flat", "desk", "ward"),
    on_stamp(say(16.0, "bear", 6, "closed", "flat", "desk", "caused")),
    say(18.0, "rabbit", 7, "half", "flat", "desk", "again"),
    say(19.2, "bear", 8, "half", "grin", "desk"),
    say(20.5, "bear", 9, "side", "flat", "desk", "tree"),
    hold(22.0, "bear", "", "half", "grin", "desk", "named"),
)
SKETCH = Sketch(SLUG, TITLE, (NARRATOR, BEAR, RABBIT), LINES, BEATS, END, cast=mind_kit.MIND_CAST)


def validate(sk: Sketch = SKETCH) -> None:
    """The sketch is consistent, each event happens once and in order, the claim opens it, and no word on screen is
    one the channel keeps off it."""
    sketch.check(sk)
    for event in EVENTS:
        scripting.exactly_once(sk.beats, event, f"{event} happens once")
    scripting.only_events(sk.beats, set(EVENTS))
    times = [sketch.events(sk.beats, event)[0][0] for event in EVENTS]
    if times != sorted(times):
        raise sketch.SketchError(f"the events run {EVENTS}")
    if sk.beats[0].line != 0 or sk.beats[0].start != 0.0:
        raise sketch.SketchError("the claim opens the reel")
    cover = (THUMBNAIL.headline, THUMBNAIL.kicker)
    copy = (*STAMP, CITE, *STAMP_CRASH, CITE_CRASH, NAME, POST.title, POST.description, *cover)
    for text in (*(q.text for q in sk.lines), *copy):
        mind_kit.check_copy(text)


def no_desk(cv, parent) -> None:
    """Each shot lays its own dash or bed: see :func:`dress`."""


def _traffic(app, at: dict[str, float]) -> tuple[Passing, ...]:
    """What goes by the glass: a car by the first second, and the one he nearly hits as he swerves."""
    plan = [
        Passing(0.2, "car", toon_cars.GREY),
        Passing(1.8, "car", toon_cars.BODY),
        Passing(at["swerve"] - 0.2, "car", "#ff8fa3"),
        Passing(at["stamp"] + 1.2, "bus"),
    ]
    return tuple(p for p in plan if app.start <= p.at < app.end)


def answer(start: float, at: dict[str, float]) -> str:
    """What the form reads on a shot from ``start``: blank while she asks, his answer once he has given it, and blank
    again on the new form she brings to the ward."""
    return ANSWER if at["swerve"] <= start < at["ward"] else ""


def _board(shot, at: dict[str, float]) -> None:
    """The rabbit's clipboard, held under her mouth."""
    toon_everyday.clipboard(
        shot.cv,
        shot.front,
        "Driver survey",
        (toon_everyday.Field("Driving", answer(shot.app.start, at), shot.app.start),),
        measure=shot.measure,
        at=BOARD_AT,
        scale=BOARD_SCALE,
        hand=RABBIT_PAW,
        id=shot.cv.uid("clipboard"),
    )


def _car(shot, at: dict[str, float]) -> None:
    cv, app = shot.cv, shot.app
    who = app.who
    toon_cars.car_inside(cv, mind_kit.far(cv, shot.back), app.start, app.end, _traffic(app, at))
    toon_cars.seat(cv, shot.back, SEAT_X[who])
    if who == "bear":
        mind_kit.key(cv, shot.light)
        toon_cars.steering_wheel(cv, shot.front, WHEEL_AT)
    else:  # she sits by the window the key comes from, and at its full strength it would bleach her eyes
        look.pool(cv, shot.light, "mind-key-near", "#fff1c4AA", 700, 180, 900, 1000, opacity=0.18)
        look.fade(cv, shot.light, "mind-contact", "#2a1a4a66", toon.fy(801), toon.fy(801) - 60.0, cv.width)
    toon_house.ledge(cv, shot.front, "dash")
    toon_cars.dash_vents(cv, shot.front)
    if who == "rabbit":
        _board(shot, at)


def _ward(shot, at: dict[str, float]) -> None:
    cv, app = shot.cv, shot.app
    toon_ward.ward(cv, mind_kit.far(cv, shot.back))
    look.fade(
        cv,
        shot.light,
        "mind-contact",
        "#2a1a4a66",
        toon.fy(toon_ward.BED_TOP),
        toon.fy(toon_ward.BED_TOP) - 60.0,
        cv.width,
    )
    toon_ward.ward_bed(cv, shot.front, 46.0)
    if app.who == "rabbit":
        _board(shot, at)


def dress(shot) -> None:
    """Every shot's set and props: the car up to the bang, the ward from it, the stamps over either."""
    cv, app = shot.cv, shot.app
    at = {name: sketch.events(shot.beats, name)[0][0] for name in EVENTS}
    if app.start < at["ward"] - 1e-6:
        _car(shot, at)
    else:
        _ward(shot, at)
    if app.start <= at["stamp"] < app.end:
        mind_kit.stamp(cv, shot.front, STAMP, CITE, at["stamp"], at["half"], shot.measure)
    if app.start <= at["caused"] < app.end:
        mind_kit.stamp(cv, shot.front, STAMP_CRASH, CITE_CRASH, at["caused"], app.end, shot.measure)
    if app.start <= at["named"] < app.end:
        mind_kit.named(cv, shot.front, NAME, at["named"], app.end, shot.measure, PUNCH, PIVOT)
    if app.start <= at["bang"] < app.end:  # the bang: the frame goes white and the next shot is the ward
        flash = cv.group(shot.front, cv.uid("g"), start=at["bang"], end=app.end)
        cv.rect(flash, 0, 0, cv.width, cv.height, "#ffffff")


def plaster(cv, app, beats, face) -> None:
    """His bandage from the ward on, in the face's own group, so it stays on him when he talks."""
    start = max(app.start, sketch.events(beats, "ward")[0][0])
    if start < app.end:
        toon_ward.bandage(cv, face, start, app.end, toon_rigs.rig_of("toon-bear", VERSIONS).look)


def lens(shot, setup) -> None:
    """The shot slides across the road on the swerve, and a punch on the tree."""
    ev = {name: sketch.events(shot.beats, name)[0][0] for name in EVENTS}
    camera.anchor(setup, *PIVOT, place=True)
    if shot.app.start <= ev["swerve"] < shot.app.end:
        rows = [(ev["swerve"] + k * SWERVE_STEP, 560.0 + dx) for k, dx in enumerate(SWERVE)]
        t, stop = rows[0][0], rows[-1][0]
        scale = [(t - 0.02, 1.0), (t, SWERVE_SCALE), (stop, SWERVE_SCALE), (stop + 0.04, 1.0)]
        camera.push_in(shot.cv, setup, x=rows, scale=scale, hold_scale=True)
    if shot.app.start <= ev["tree"] < shot.app.end:
        camera.zoom_holds(shot.cv, setup, [(0.0, 1.0), (ev["tree"], PUNCH)])


def foley(beats, end, speech, root, seed) -> list[dict]:
    """The road under the car and nothing under the ward but its monitor: the horn, the bang, the stamps, the sting."""
    audio = root / "audio"
    audio.mkdir(parents=True, exist_ok=True)
    at = {name: sketch.events(beats, name)[0][0] for name in EVENTS}
    room = synth.write_room(audio / "room.wav", end, seed=seed)
    road = [round(k * 0.6, 3) for k in range(int(at["bang"] / 0.6) + 1)]
    beeps = [at["ward"] + 0.3 + k * MONITOR_EVERY for k in range(int((end - at["ward"] - 0.4) / MONITOR_EVERY))]
    rows = {
        "road": (synth.write_whoosh(audio / "road.wav", road, end, seed=seed), -22.0),
        "horn": (synth.write_tones(audio / "horn.wav", [at["swerve"]], end, HORN), -8.0),
        "bang": (synth.write_bursts(audio / "bang.wav", [at["bang"]], end, synth.SLAM, seed=seed), -2.0),
        "stamp": (synth.write_bursts(audio / "stamp.wav", [at["stamp"], at["caused"]], end, THUD, seed=seed), -6.0),
        "monitor": (synth.write_tones(audio / "monitor.wav", beeps, end, MONITOR), -26.0),
        "sting": (mind_kit.write_sting(audio / "sting.wav", [at["named"]], end), -9.0),
        "room": (room, -30.0),
    }
    return [sketch.effect(name, 0.0, gain, root, path) for name, (path, gain) in rows.items()]


THUMBNAIL = Thumbnail("Top ten\npercent", 5.2, SERIES, place="bottom")
POST = InstagramPost(
    title="Are you an above-average driver?",
    description=(
        f"{SERIES}. The better-than-average effect: in a 1981 study, 93% of US students and 69% of Swedish students "
        "rated themselves more skillful than the median driver. A 2023 replication with American adults found 91%, and "
        "78% on adjusted materials. The hospital drivers are Preston & Harris, 1965, as Svenson reports them. Small "
        "samples and self-reports; the tree is ours.\n"
        "Source: Svenson (1981), Acta Psychologica"
    ),
    credit="Voices: ElevenLabs premade voices Bella, Bill and Sarah. Original characters, drawn in code.",
    hashtags=("#psychology", "#betterthanaverage", "#howpeoplethink", "#driving"),
    thumbnail=THUMBNAIL,
)
