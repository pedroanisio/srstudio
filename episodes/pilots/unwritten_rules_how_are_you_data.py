"""The Unwritten Rules, how are you: the talking-head pilot with Rafa, main trigger recognition: the sketch as data.

Rafa, a clay man at his own worktop, explains the rules of "how are you" with a smile he is holding up by hand. Every
rule tells you it is fine, and every time the thing under his hand says otherwise: the mug says "(I think)", the phone
says 99+, the folder says PENDING. Rule three is that nobody asked. He says so, and then answers anyway, which breaks
rule one: he went out for bread, it was a hundred and eighty-seven dollars, and he does not know where the bread is. The
smile comes back on a cut. "Good."

:data:`BEATS` is the script. :data:`SKETCH` is the same script for the recording: :data:`VOICE`, the operator's choice,
says every line, one take a line, and :data:`KEPT` holds the seconds each take measured, so a beat starts where the one
before it ends plus its written hold. :func:`validate` checks every word, mood, prop and framing, and the length the
script comes to at :data:`PACE`; :func:`validate_sketch` checks the sketch on top of that.
"""

from __future__ import annotations

from dataclasses import dataclass, replace
from pathlib import Path

from srstudio import foley as synth
from srstudio import host_kit, music, rafa, rafa_host, rafa_reel, scripting, sketch
from srstudio.errors import SrstudioError
from srstudio.host_kit import BONE
from srstudio.rafa_reel import Act, Renders
from srstudio.sketch import Line, Sketch, Speaker
from srstudio.social import InstagramPost
from srstudio.thumbnail import Thumbnail
from srstudio.voice import Voice, VoiceSettings

SLUG = "unwritten-rules-how-are-you"
HOST = "rafa"
VOICE = "Will"  # the operator's choice: "will is the voice", 2026-10-31
SEED = 52026
SETTINGS = VoiceSettings(stability=0.42, similarity_boost=0.75, style=0.35)  # the settings of the audition
OUTPUT = f"renders/pilots/{SLUG}.mp4"
TITLE = "How are you has rules — The Unwritten Rules"
DESCRIPTION = (
    "A pilot of a talking-head show: Rafa, 34, mostly functional, explains the unwritten rules of how are you at his "
    "kitchen worktop, and breaks the first one."
)
ACCESSIBILITY = (
    "A clay man in a teal cardigan over mustard stands at a kitchen worktop and talks to camera with a tired smile, a "
    "mug that says I'm great, I think, under his hand. He gives three rules of how are you. The mug becomes a phone "
    "with 99+ unread, then a folder marked adult life, pending. He says nobody asked, footsteps walk away, and he "
    "answers anyway: his eyes go wide over a tote bag, which fills the frame, just came for bread, $187.40. He does "
    "not know where the bread is. On a cut the smile and the mug are back. He says good, then you know what you did."
)
NARRATION = "Voiced with the ElevenLabs premade voice Will; synthesised foley and a synthesised music bed."
NOTE = "ElevenLabs premade voice Will at its natural pace; no reference-voice cloning."
TINTS = {"rafa": BONE}
MOUTH = replace(
    sketch.MOUTH_STYLE, spelling=True, close_bilabials=True, lead=0.04, min_rest=0.12, fine=True, first_sound=True
)
VERSIONS: dict[str, int] = {}
GAP = 0.2  # seconds of air between two lines that have no hold
TAIL = 0.5  # seconds the reel runs on after the sign-off
BPM = 96
PACE = 2.7  # spoken words a second, the estimate a length is checked at until a take measures it
SHORTEST, LONGEST = 20.0, 30.0
SIGN_OFF = "You know what you did."
HOOK_LABEL = "HOW ARE YOU HAS RULES"
FRAMINGS = ("medium", "close", "tight")
LABEL_STOP = "break"  # the third rule's label goes when he turns it on you
BED_GAIN = -14.0
BED_FADE = 0.08
STEP, STEPS = 0.26, 5  # seconds between the steps walking away, and how many


class ScriptError(SrstudioError, ValueError):
    """A beat this show cannot stage."""


@dataclass(frozen=True)
class Beat:
    """One line of the script: its ``id``, the words (a silent beat has none), his ``mood``, what his hand is on, the
    ``framing``, the seconds he holds after it, an ``insert`` that takes the frame for a moment, and the ``label``."""

    id: str
    line: str
    mood: str
    prop: str
    framing: str = "medium"
    hold: float = 0.0
    insert: str = ""
    label: str = ""


BEATS: tuple[Beat, ...] = (
    Beat("hook", "Nobody tells you how are you has rules.", "public-smile", "rafa-mug", label=HOOK_LABEL),
    Beat("one", "Rule one. You say good. Whatever happened.", "public-smile", "rafa-mug", label="RULE 1", hold=0.3),
    Beat("two", "Rule two. You can add busy.", "public-smile", "rafa-phone", label="RULE 2"),
    Beat("choice", "Busy sounds like a choice.", "public-smile", "rafa-phone", "close", hold=0.3),
    Beat("three", "Rule three. The one nobody admits.", "social-battery", "rafa-bills", label="RULE 3"),
    Beat(
        "walking", "They didn't ask. They're already walking away.", "social-battery", "rafa-bills", "close", hold=1.4
    ),
    Beat("break", "You didn't ask.", "social-battery", "rafa-bills", "tight", hold=0.5),
    Beat("bread", "I went out for bread.", "internal-meltdown", "rafa-tote"),
    Beat("price", "It was a hundred and eighty-seven dollars.", "internal-meltdown", "rafa-tote", insert="rafa-tote"),
    Beat("where", "I don't know where the bread is.", "internal-meltdown", "rafa-tote", "tight", hold=1.3),
    Beat("good", "Good.", "public-smile", "rafa-mug", hold=0.7),
    Beat("off", SIGN_OFF, "public-smile", "rafa-mug"),  # medium: the label sits under his chin only here
)
VOICE_CANDIDATES = (  # the three auditioned, one take each; the operator chose Will
    ("Chris", "iP95p4xoKVk53GoZ742B", "casual and down to earth, the man at the worktop; carries the deadpan rules"),
    (
        "Eric",
        "cjVigY5qzO86Huf0OWal",
        "smooth and friendly, a customer-service smile that has further to fall at the bread",
    ),
    (
        "Will",
        "bIHbv24MWmeRgasZH58o",
        "young and relaxed, cheerful denial; the closest to a man of 34 keeping it together",
    ),
)


KEPT = (
    2.172,
    2.332,
    1.55,
    1.365,
    2.668,
    2.37,
    0.804,
    1.065,
    2.034,
    1.474,
    0.444,
    1.32,
)  # seconds, measured from the takes
ACTS = tuple(Act(beat.framing, beat.prop, beat.mood) for beat in BEATS)
NAMES = tuple(beat.id for beat in BEATS)
SPEAKER = Speaker(HOST, Voice(role=HOST, id=VOICE_CANDIDATES[2][1], name=VOICE), SETTINGS, HOST)
LINES = tuple(Line(HOST, beat.line) for beat in BEATS)
PLACEHOLDER = ("side", "flat", "desk")  # a pose for the sketch's check: this man is drawn from ACTS


def starts() -> tuple[float, ...]:
    """Where each line starts: where the one before ends, plus its hold, or :data:`GAP` when it has none."""
    rows, at = [], 0.0
    for beat, kept in zip(BEATS, KEPT, strict=True):
        rows.append(round(at, 3))
        at += kept + (beat.hold or GAP)
    return tuple(rows)


script = scripting.Script(LINES)
SKETCH = Sketch(
    SLUG,
    TITLE,
    (SPEAKER,),
    LINES,
    tuple(script.say(at, HOST, i, *PLACEHOLDER) for i, at in enumerate(starts())),
    round(starts()[-1] + KEPT[-1] + TAIL, 3),
    cast=rafa_host.CAST,
)
POST = InstagramPost(
    title="What do you actually say to how are you?",
    description="Rafa, 34, mostly functional, has rules.",
    credit="An animated character; synthetic voice.\nVoice: ElevenLabs premade Will.",
    hashtags=("#howareyou", "#unwrittenrules", "#animation", "#adulting"),
    thumbnail=Thumbnail(
        "How are you\nhas rules", 4.84, "The Unwritten Rules", focus=(540.0, 700.0), zoom=1.0, place="bottom"
    ),
)


def beat(name: str, beats=SKETCH.beats):
    """The beat called ``name``, from the sketch's or a recording's ``beats``."""
    return beats[NAMES.index(name)]


def spoken_words() -> int:
    return sum(len(beat.line.split()) for beat in BEATS)


def estimated_seconds() -> float:
    """The script's length at :data:`PACE`, with its holds: an estimate until a take measures it."""
    return spoken_words() / PACE + sum(beat.hold for beat in BEATS)


def moods() -> tuple[tuple[float, str], ...]:
    """His mood from the second it starts, at :data:`PACE`, as :func:`srstudio.rafa_host.faces` takes it."""
    rows: list[tuple[float, str]] = []
    at = 0.0
    for beat in BEATS:
        if not rows or rows[-1][1] != beat.mood:
            rows.append((round(at, 3), beat.mood))
        at += len(beat.line.split()) / PACE + beat.hold
    return tuple(rows)


def validate(beats: tuple[Beat, ...] = BEATS) -> None:
    """Every beat is one the show can stage, and the script keeps the show's rules; a :class:`ScriptError` if not."""
    for beat in beats:
        host_kit.check_copy(beat.line)
        if beat.mood not in rafa.MOODS:
            raise ScriptError(f"{beat.id}: Rafa's moods are {tuple(rafa.MOODS)}, got {beat.mood!r}")
        for prop in (beat.prop, beat.insert):
            if prop and prop not in rafa.PROPS:
                raise ScriptError(f"{beat.id}: his props are {tuple(rafa.PROPS)}, got {prop!r}")
        if beat.framing not in FRAMINGS:
            raise ScriptError(f"{beat.id}: a framing is one of {FRAMINGS}, got {beat.framing!r}")
        if beat.hold < 0.0:
            raise ScriptError(f"{beat.id}: a hold is not negative, got {beat.hold!r}")
        if len(beat.label.split()) > 7:
            raise ScriptError(f"{beat.id}: a label holds seven words at most, got {beat.label!r}")
    if not beats[0].line.startswith("Nobody tells you"):
        raise ScriptError(f"the show opens on a Nobody Tells You claim, got {beats[0].line!r}")
    if [beat.label for beat in beats if beat.label.startswith("RULE")] != ["RULE 1", "RULE 2", "RULE 3"]:
        raise ScriptError("the show has three rules, in order")
    if beats[-1].line != SIGN_OFF:
        raise ScriptError(f"the show ends on its sign-off, got {beats[-1].line!r}")
    if not any(beat.hold >= 1.2 for beat in beats):
        raise ScriptError("a punchline needs a hold of at least 1.2 s before it")
    if not {beat.prop for beat in beats} <= set(rafa_host.PLACES):
        raise ScriptError("every prop needs a place on the worktop")
    length = sum(len(beat.line.split()) for beat in beats) / PACE + sum(beat.hold for beat in beats)
    if not SHORTEST <= length <= LONGEST:
        raise ScriptError(
            f"the show runs {SHORTEST} to {LONGEST} s, this comes to {length:.1f} s at {PACE} words a second"
        )


def validate_sketch(sk: Sketch = SKETCH) -> None:
    """The sketch is consistent, parallel to the script, and shows no word the show keeps off the screen."""
    validate()
    sketch.check(sk)
    if len(sk.beats) != len(BEATS) or [q.text for q in sk.lines] != [b.line for b in BEATS]:
        raise ScriptError(f"{len(sk.beats)} beats for the script's {len(BEATS)}")
    if sk.beats[0].line is None:
        raise ScriptError("the reel opens on his line")
    for text in (*(b.label for b in BEATS if b.label), POST.title, POST.description):
        host_kit.check_copy(text)


def labels(beats, end: float) -> list[tuple[float, float, str]]:
    """Each label from its beat to the next label, the third to :data:`LABEL_STOP`."""
    rows = [(beats[i].start, b.label) for i, b in enumerate(BEATS) if b.label]
    stops = [at for at, _ in rows[1:]] + [beat(LABEL_STOP, beats).start]
    return [(at, min(stop, end), text) for (at, text), stop in zip(rows, stops, strict=True)]


def overlay(cv, parent, beats, end, measure, *, root: Path, renders: Renders) -> None:
    """Over the picture: the tote on its own, the labels, the sign-off, the signature marks."""
    tote = rafa_reel.insert(
        cv, parent, "rafa-tote", beat("price", beats).start, beat("where", beats).start, renders, root
    )
    host_kit.finish(cv, tote)
    host_kit.sign(cv, parent)
    for start, stop, text in labels(beats, end):
        host_kit.label(cv, parent, text, start, stop, measure)
    host_kit.sign_off(cv, parent, SIGN_OFF, beat("off", beats).start, end, measure)


def bed(path: Path, beats, end: float, seed: int) -> Path:
    """The kitchen radio: bass and keys, a shop's idea of fine, gone from the bread to the "Good."."""
    groove = music.Groove(BPM)
    bars = int(end / groove.bar) + 2
    sections = [music.Section(0, bars, frozenset({"bass", "keys"}))]
    samples = music.render(groove, sections, seed=seed, peak=0.6)[: round(end * synth.RATE)]
    fall, rise = beat("bread", beats).start, beat("good", beats).start
    for k in range(round(fall * synth.RATE), round(rise * synth.RATE)):
        samples[k] = 0.0
    fade = round(BED_FADE * synth.RATE)
    for k in range(fade):
        samples[round(fall * synth.RATE) - k - 1] *= k / fade
    return music.write_wav(path, samples, synth.RATE)


def foley(beats, end: float, speech, root, seed: int) -> list[dict]:
    """A sound for each thing that lands: the mug down, the phone, the folder, the steps walking off through the hold,
    the tote, the till on the price, the clock through the longest silence, the bell of the smile coming back."""
    audio = root / "audio"
    audio.mkdir(parents=True, exist_ok=True)

    def sound(id: str, gain: float, burst: synth.Burst, times) -> dict:
        path = synth.write_bursts(audio / f"{id}.wav", list(times), end, burst, seed=seed)
        return sketch.effect(id, 0.0, gain, root, path)

    said = {name: span for name, span in zip(NAMES, speech, strict=True)}
    buzz = [beat("two", beats).start, beat("choice", beats).start]
    away = said["walking"][1]
    steps = [round(away + STEP * i, 3) for i in range(STEPS)]
    clock = said["where"][1] + 0.25
    return [
        sketch.effect("bed", 0.0, BED_GAIN, root, bed(audio / "bed.wav", beats, end, seed), role="music"),
        sound("mug", -9.0, synth.KNOCK, [beat("one", beats).start, said["off"][1]]),
        sketch.effect("buzz", 0.0, -6.0, root, synth.write_buzz(audio / "buzz.wav", buzz, end, seed=seed)),
        sound("folder", -6.0, synth.THUD, [beat("three", beats).start]),
        sound("steps-near", -8.0, synth.KNOCK, steps[:2]),
        sound("steps-off", -16.0, synth.KNOCK, steps[2:4]),
        sound("steps-gone", -24.0, synth.KNOCK, steps[4:]),
        sound("tote", -8.0, synth.SWISH, [beat("bread", beats).start]),
        sound("till", -8.0, synth.BELL, [said["price"][1]]),
        sound("clock", -14.0, synth.REMOTE_CLICK, [clock, clock + 0.7]),
        sound("ting", -9.0, synth.BELL, [beat("good", beats).start]),
    ]
