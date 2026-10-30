"""Do You Floss — the sketch as data: everyone lies to the dentist, and the dentist can see. Fern in the chair, the
lamp already swinging at her. Do you floss? Every day. The room goes dark: every day, every day, when, this morning,
in the car park. Rex slides over a photo of one tooth, and pokes once. A single drop on the bib. Fern breaks: it was
Christmas. The lights come back, Rex calmly writes it down, Fern whispers every day, and his eyes rise and hold.

Two voices (ElevenLabs premade Charlie as Rex, Matilda as Fern), Rex's first line said off screen over his hand on the
lamp. The sketch opens with the lamp already swinging (the ``sp-hook_motion`` test's arm B). ``SKETCH`` is checked by
:func:`srstudio.sketch.check`; :func:`validate` checks what the events ask of the props; :func:`dress` draws each
shot's set and props, and :func:`foley` its sound.
"""

from __future__ import annotations

from dataclasses import replace

from srstudio import camera, scripting, sketch, toon_everyday, toon_house, toon_surgery
from srstudio import foley as synth
from srstudio.sketch import Line, Sketch, Speaker
from srstudio.voice import Voice, VoiceSettings

SEED = 2408
SLUG = "do-you-floss"
TITLE = "Do You Floss — Rex and Fern at the Dentist (Toon)"
DESCRIPTION = (
    "A Toon sketch at the dentist: Rex asks Fern if she flosses, and the check-up turns into an interrogation under "
    "a swinging lamp until a single drop lands on her bib."
)
ACCESSIBILITY = (
    "A cartoon frog sits in a dentist's chair while a hand swings the lamp at her. A cartoon dog asks if she flosses. "
    "The room goes dark around her face as they trade the words every day. He slides over a photo of one stained "
    "tooth and pokes once. A close-up shows one drop of blood landing on a paper bib. She shouts it was Christmas. "
    "The lights return, he writes on her chart, she whispers every day, and his eyes rise and hold on her."
)
NARRATION = "Voiced with ElevenLabs premade voices Charlie (Rex) and Matilda (Fern); synthesised effects."
NOTE = "ElevenLabs premade voices Charlie and Matilda at their natural pace; no reference-voice cloning."
VOICE_REX = Voice(role="rex", id="IKne3meq5aSn9XLyUdCD", name="Charlie")
SETTINGS_REX = VoiceSettings(stability=0.55, similarity_boost=0.75, style=0.30)
FERN = Speaker(
    "fern",
    Voice(role="fern", id="XrExE9yKIg1WjnnlVkGX", name="Matilda"),
    VoiceSettings(stability=0.45, similarity_boost=0.75, style=0.40),
    "frog",
)
REX = Speaker("rex", VOICE_REX, SETTINGS_REX, "dog")
REX_OFF = Speaker("rex-off", VOICE_REX, SETTINGS_REX)  # heard over Fern's shot, his hand on the lamp
# Her last line, flat and held in, said through a fixed mouth: the character plays no lip sync for it.
FERN_LOW = Speaker("fern-low", FERN.voice, VoiceSettings(stability=0.85, similarity_boost=0.75, style=0.0))
TINTS = {"rex": "#ffe3b3", "rex-off": "#ffe3b3", "fern": "#d6f5dc", "fern-low": "#d6f5dc"}
MOUTH = replace(sketch.MOUTH_STYLE, spelling=True, close_bilabials=True, lead=0.04, min_rest=0.12)

FIGURES = {"frog": (1.16, 0.0), "dog": (1.16, 0.0)}
FACE = {"frog": (176, 500), "dog": (176, 500)}
DIM = 0.5  # how far the ledge dims in the dark
HAND = "#f0a35c"  # Rex's coat
CHART = {"at": (414, 790), "scale": 1.2}
BIB_HOLD = 1.15
TIP = (194, 560)
STING = ((988.0, 466.0, 0.22), (196.0, 92.0, 0.4))
TICK = ((1800.0, 1500.0, 0.05),)
PUSH, PIVOT = 1.1, (860.0, 1000.0)  # the last shot's push; a pivot this far right keeps the code in frame
END = 17.2

LINES = (
    Line("rex-off", "Do you floss?"),
    Line("fern", "Every day."),
    Line("rex", "Every day."),
    Line("fern", "Every day."),
    Line("rex", "When?"),
    Line("fern", "This morning."),
    Line("rex", "In the car park."),
    Line("fern", "Yes."),
    Line("rex", "This one says otherwise."),
    Line("fern", "It was Christmas!"),
    Line("rex", "Same time in six months."),
    Line("fern-low", "...Every day."),
)

script = scripting.Script(LINES)
hold, say = script.hold, script.say

BEATS = (
    say(0.0, "frog", 0, "wide", "grin", "desk"),  # the lamp is already swinging
    say(1.0, "frog", 1, "wide", "grin", "desk"),
    say(1.95, "dog", 2, "narrow", "flat", "desk", "dark"),
    say(2.95, "frog", 3, "side", "grin", "desk", wear=("sweat",)),
    say(3.85, "dog", 4, "narrow", "flat", "desk"),
    say(4.4, "frog", 5, "side", "grin", "desk", wear=("sweat",)),
    say(5.2, "dog", 6, "narrow", "smirk", "desk"),
    hold(6.3, "frog", "", "shock", "flat", "desk", wear=("sweat",)),  # her eyes widen
    say(6.9, "frog", 7, "shock", "grimace", "desk", wear=("sweat",)),
    say(7.7, "dog", 8, "narrow", "flat", "desk", "photo"),
    hold(9.0, "frog", "", "shock", "o", "desk", "poke", wear=("sweat",)),
    hold(9.6, "frog", "", "shock", "o", "desk", "drop", wear=("sweat",)),  # the bib, close up
    say(10.8, "frog", 9, "shock", "scream", "desk", wear=("sweat",)),
    say(12.2, "dog", 10, "down", "flat", "desk", "lights"),
    say(14.0, "frog", 11, "side", "grimace", "desk", wear=("sweat",)),
    hold(15.0, "dog", "", "down", "flat", "desk"),
    hold(15.6, "dog", "", "narrow", "flat", "desk"),  # his eyes rise and hold: stop
)
SKETCH = Sketch(SLUG, TITLE, (FERN, REX, REX_OFF, FERN_LOW), LINES, BEATS, END)


def validate(sk: Sketch = SKETCH) -> None:
    """The sketch is consistent and its events ask only what the props can do: each of dark, photo, poke, drop and
    lights happens once, in that order; the sketch opens speaking, not on a still; no other events."""
    sketch.check(sk)
    order = ("dark", "photo", "poke", "drop", "lights")
    for event in order:
        scripting.exactly_once(sk.beats, event, f"{event} happens once")
    times = [sketch.events(sk.beats, event)[0][0] for event in order]
    if times != sorted(times):
        raise sketch.SketchError(f"the events run {order}")
    if sk.beats[0].line is None:
        raise sketch.SketchError("the sketch opens in the middle of the exchange")
    scripting.only_events(sk.beats, set(order))


def no_desk(cv, parent) -> None:
    """Each shot lays its own surface: see :func:`dress`."""


def dress(shot) -> None:
    """The surgery in every shot, a steel ledge with the tray in front; the dark closing round each face from ``dark``
    to ``lights``; the lamp, the probe and the bib on Fern's shots; the photograph and the chart on Rex's."""
    cv, app, end = shot.cv, shot.app, shot.end
    at = {name: sketch.events(shot.beats, name)[0][0] for name in ("dark", "photo", "poke", "drop", "lights")}
    frog = app.who == "frog"
    toon_surgery.surgery(cv, shot.back, "chair" if frog else "cupboards")
    toon_house.ledge(cv, shot.front, "steel")
    toon_surgery.dental_tray(cv, shot.front)
    toon_surgery.darkness(cv, shot.light, FACE[app.who], at["dark"], at["lights"], end, drift=26.0 if frog else 0.0,
                          id=cv.uid("darkness"))  # fmt: skip
    keys = [(0.0, 0.0), (at["dark"], 0.0), (at["dark"] + 0.3, DIM), (at["lights"], DIM), (at["lights"] + 0.2, 0.0)]
    dim = cv.group(shot.front, cv.uid("g"), opacity=0.0)
    cv.rect(dim, 0, toon_house.fy(toon_house.LEDGE_TOP + 47), cv.width, cv.height, toon_surgery.DARK, opacity=1.0)
    cv.keys(dim, "opacity", keys, hold=False, local=False)
    if frog:
        toon_surgery.dental_lamp(cv, shot.front, end=end, hand=HAND, id=cv.uid("lamp"))
        if app.start <= at["poke"] < app.end:
            toon_surgery.probe(cv, shot.front, TIP, at["poke"], at["drop"], id=cv.uid("probe"))
            toon_surgery.bib_insert(cv, shot.front, at["drop"], at["drop"] + BIB_HOLD, id=cv.uid("bib"))
    elif app.start <= at["photo"] < app.end:
        toon_surgery.tooth_photo(cv, shot.front, start=at["photo"] + 0.3, end=app.end, id=cv.uid("photo"))
    elif app.end > at["lights"]:
        fields = [toon_everyday.Field("Flosses", "Christmas", at["lights"] + 0.6)]
        toon_everyday.clipboard(cv, shot.front, "CHART", fields, measure=shot.measure, id=cv.uid("chart"), **CHART)


def lens(shot, setup) -> None:
    """Rex's last shot pushes in, slowly, keeping the code in frame."""
    last = max(b.start for b in shot.beats if b.who == "dog")
    if shot.app.who == "dog" and shot.app.start <= last < shot.app.end:
        camera.anchor(setup, *PIVOT, place=True)
        keys = [(shot.app.start, 1.0), (shot.app.end, PUSH)]
        for channel in ("scaleX", "scaleY"):
            shot.cv.keys(setup, channel, keys, kind="sine-in-out", local=False)


def foley(beats, end, speech, root, seed) -> list[dict]:
    """A switch as the room goes dark and as it comes back, the photograph's slide, the tick of the probe, and the
    sting on the drop."""
    audio = root / "audio"
    audio.mkdir(parents=True, exist_ok=True)
    times = {name: sketch.events(beats, name)[0][0] for name in ("dark", "photo", "poke", "drop", "lights")}
    switch = synth.write_typing(audio / "switch.wav", [times["dark"], times["lights"]], end)
    slide = synth.write_whoosh(audio / "slide.wav", [times["photo"] + 0.3], end)
    sting = synth.write_tones(audio / "sting.wav", [times["drop"] + toon_surgery.DROP_FALL], end, STING)
    tick = synth.write_tones(audio / "tick.wav", [times["poke"] + toon_surgery.SLIDE], end, TICK)
    return [
        sketch.effect("tick", 0.0, -8.0, root, tick),
        sketch.effect("switch", 0.0, -4.0, root, switch),
        sketch.effect("slide", 0.0, -12.0, root, slide),
        sketch.effect("sting", 0.0, -6.0, root, sting),
    ]
