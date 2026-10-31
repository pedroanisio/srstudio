"""Shower Argument — the sketch as data: everyone wins the argument in the shower three days too late, and sometimes
not even there. Rex beats Fern in the steam, until the Fern he made up brings up the shampoo.

Three voices (ElevenLabs premade Charlie as Rex, Matilda as Fern, River as Mia through the door). One shot: Rex in the
shower with the water falling from the first frame (the ``sp-hook_motion`` test's arm B), Fern a tinted figure in the
steam (:func:`srstudio.toon_extras.figure` at low opacity, ``steam`` on, ``fade`` off). :func:`validate` checks the
events; :func:`dress` draws the shot, :func:`lens` its camera and :func:`foley` its sound.
"""

from __future__ import annotations

from srstudio import camera, scripting, sketch, toon_extras, toon_homeware, toon_house
from srstudio import foley as synth
from srstudio.foley import Burst
from srstudio.sketch import Line, Sketch
from srstudio.toon_voices import speaker, tinted

SEED = 3114
SLUG = "shower-argument"
TITLE = "Shower Argument — Rex Wins (Toon)"
DESCRIPTION = "A Toon sketch: Rex wins the argument, in the shower, three days late, against a Fern he made up."
ACCESSIBILITY = (
    "A cartoon dog in a shower points and speaks into a shampoo bottle. A pale figure of a frog forms in the "
    "steam on the "
    "glass and apologizes. He bows to faint applause. Then the steam frog brings up the watered-down shampoo, and the "
    "bottle gives up one bubble. The water stops. A voice through the door asks who he is talking to, and if he won. "
    "The steam frog folds her arms and fades. Lines appear in tinted pills."
)
NARRATION = "Voiced with ElevenLabs premade voices Charlie (Rex), Matilda (Fern) and River (Mia)."
NOTE = "ElevenLabs premade voices Charlie, Matilda and River at their natural pace; no reference-voice cloning."
REX = speaker("rex", "Charlie", "dog", "big")
FERN = speaker("fern", "Matilda", "frog")
MIA = speaker("mia", "River")
TINTS = tinted(REX, FERN, MIA)
PIVOT = (980.0, 1420.0)
GHOST_AT = (430.0, 760.0)
GHOST_SCALE = 0.95
GHOST_OPACITY = 0.42
BOTTLE = dict(at=(322.0, 800.0), scale=0.72)
HANDS = Burst(1.4, 3400.0, attack=0.15, decay=0.8, tone_hz=0.0, tone_end_hz=0.0, tone=0.0, flutter_hz=19.0)
GURGLE = Burst(0.3, 500.0, attack=0.02, decay=0.4, tone_hz=240.0, tone_end_hz=520.0, tone=0.6, flutter_hz=14.0)
DRIP = Burst(0.09, 900.0, attack=0.002, decay=0.25, tone_hz=1500.0, tone_end_hz=2300.0, tone=0.8)
END = 26.4

LINES = (
    Line("rex", "No, Fern. You listen. You don't get to say calm down."),
    Line("fern", "You're right. I'm so sorry."),
    Line("rex", "Thank you."),
    Line("fern", "Although, you did start it."),
    Line("rex", "Excuse me. This is my shower."),
    Line("fern", "And you've been adding water to that shampoo since March."),
    Line("rex", "Fair."),
    Line("mia", "Who are you talking to?"),
    Line("rex", "Nobody."),
    Line("mia", "Did you win?"),
    Line("rex", "No."),
)

SCRIPT = scripting.Script(LINES)
say, first, part, hold = SCRIPT.say, SCRIPT.first, SCRIPT.part, SCRIPT.hold

BEATS = (
    hold(0.0, "dog", "", "narrow", "open", "lean"),
    first(0.2, "dog", 0, "No, Fern.", "narrow", "open", "lean"),
    part(1.2, "dog", 0, 2, "You listen.", "narrow", "open", "lean"),
    part(2.2, "dog", 0, 4, "You don't get to say calm down.", "narrow", "open", "lean"),
    hold(4.4, "dog", "", "half", "smirk", "lean", "steam"),  # she forms on the glass, head bowed
    say(5.0, "dog", 1, "half", "grin", "desk"),
    say(7.0, "dog", 2, "closed", "grin", "desk", "bow"),  # into the bottle: faint applause
    say(8.9, "dog", 3, "wide", "flat", "desk"),
    first(10.8, "dog", 4, "Excuse me.", "narrow", "open", "lean"),
    part(11.8, "dog", 4, 2, "This is my shower.", "narrow", "open", "lean"),
    first(13.2, "dog", 5, "And you've been adding water", "wide", "flat", "desk"),
    part(14.8, "dog", 5, 5, "to that shampoo since March.", "shock", "flat", "desk"),
    hold(16.7, "dog", "", "down", "none", "desk", "bubble"),  # two seconds with the bottle
    say(18.7, "dog", 6, "half", "flat", "sigh"),
    hold(19.5, "dog", "", "half", "none", "sigh", "off"),  # a knock; the water stops
    say(20.2, "dog", 7, "wide", "flat", "sigh"),
    say(21.6, "dog", 8, "wide", "open", "lean"),
    say(22.4, "dog", 9, "side", "flat", "sigh"),
    hold(23.3, "dog", "", "half", "none", "sigh", "fade"),  # two seconds: she folds her arms and goes
    say(24.9, "dog", 10, "down", "frown", "sigh"),
)
SKETCH = Sketch(SLUG, TITLE, (REX, FERN, MIA), LINES, BEATS, END)


def _at(beats, kind: str) -> float:
    return sketch.events(beats, kind)[0][0]


def validate(sk: Sketch = SKETCH) -> None:
    """The sketch is consistent, speaks by 0.5 s; each event comes once, the steam before Fern's first line, the fade
    after the water stops."""
    sketch.check(sk)
    if next(b for b in sk.beats if b.spoken).start > 0.5:
        raise sketch.SketchError("the first line starts by 0.5 s")
    kinds = ("steam", "bow", "bubble", "off", "fade")
    for kind in kinds:
        scripting.exactly_once(sk.beats, kind, f"{kind} comes once")
    if _at(sk.beats, "fade") <= _at(sk.beats, "off"):
        raise sketch.SketchError("she fades after the water stops")
    scripting.only_events(sk.beats, set(kinds))


def dress(shot) -> None:
    """The shower; the steam on the glass with the Fern he made up in it; the water to ``off``; the bottle in front."""
    cv = shot.cv
    steam, fade, off = (_at(shot.beats, k) for k in ("steam", "fade", "off"))
    toon_house.bathroom(cv, shot.back)
    fog = cv.group(shot.back, cv.uid("g"), opacity=0.0)
    cv.rect(fog, cv.width * 0.5, 0, cv.width * 0.5, cv.height, "#f4fbff")
    cv.keys(
        fog, "opacity", [(0.0, 0.25), (steam, 0.25), (steam + 0.8, 0.6), (fade, 0.6), (fade + 1.4, 0.2)], hold=False
    )
    poses = (
        (0.0, "closed", "flat", "desk"),
        (steam + 0.5, "half", "flat", "desk"),
        (fade - 0.1, "half", "flat", "crossed"),
    )
    ghost = toon_extras.figure(shot, shot.back, "frog", GHOST_AT, GHOST_SCALE, poses, start=steam)
    cv.keys(ghost, "opacity", [(steam, 0.0), (steam + 0.8, GHOST_OPACITY), (fade, GHOST_OPACITY), (fade + 1.4, 0.0)],
            hold=False)  # fmt: skip
    toon_house.shower_water(cv, shot.front, [(0.0, off)], clear=(40.0, 330.0), stop=372.0)
    toon_homeware.shampoo(cv, shot.front, bubble=_at(shot.beats, "bubble") + 0.8, **BOTTLE)
    toon_house.ledge(cv, shot.front, "white")


def lens(shot, setup) -> None:
    """A slow push from the first frame, another for his last word."""
    camera.anchor(setup, *PIVOT, place=True)
    last = [b for b in shot.beats if b.line == 10][0].start
    camera.push_in(shot.cv, setup, scale=[(0.0, 1.0), (4.0, 1.05), (last - 1.5, 1.05), (last + 0.6, 1.13)])


def _bed(start: float, stop: float, step: float) -> list[float]:
    out, t = [], start
    while t < stop:
        out.append(round(t, 3))
        t += step
    return out


def foley(beats, end, speech, root, seed) -> list[dict]:
    """The water to ``off``, the applause on ``bow``, the bottle's gurgle, the knock, the drips after it."""
    audio = root / "audio"
    audio.mkdir(parents=True, exist_ok=True)
    off = _at(beats, "off")
    bubble = _at(beats, "bubble") + 0.8
    water = synth.write_water(audio / "water.wav", [(0.0, off)], end)
    hands = synth.write_bursts(audio / "hands.wav", [_at(beats, "bow") + 0.2], end, HANDS, seed=seed)
    gurgle = synth.write_bursts(audio / "gurgle.wav", [bubble], end, GURGLE, seed=seed)
    knock = synth.write_bursts(audio / "knock.wav", [off, off + 0.22], end, synth.KNOCK, seed=seed)
    drip = synth.write_bursts(audio / "drip.wav", _bed(off + 0.7, end - 0.5, 1.15), end, DRIP, seed=seed)
    return [sketch.effect("water", 0.0, -20.0, root, water), sketch.effect("hands", 0.0, -22.0, root, hands),
            sketch.effect("gurgle", 0.0, -8.0, root, gurgle), sketch.effect("knock", 0.0, -9.0, root, knock),
            sketch.effect("drip", 0.0, -14.0, root, drip)]  # fmt: skip
