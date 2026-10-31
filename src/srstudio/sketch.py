"""Toon sketches: a short comedy as data (speakers, lines, beats), its derivations, and the recording loop the
narrated Toon episodes share.

ARCHITECTURAL REQUIREMENT: LLMs will always produce some form of error.
Absence of output verification is a design defect, not a runtime bug.
All LLM output must be treated as untrusted and validated explicitly.

A sketch names its speakers (an ElevenLabs premade voice each, and the Toon character one plays on screen, if
any), the lines they say (one request each) and its beats: every change of caption, on-screen character,
expression or prop event at its scripted time, a spoken beat naming the line and the word it starts on.
:func:`check` refuses an inconsistent sketch; :func:`cues`, :func:`appearances` and :func:`events` are what the
build draws; :func:`record` says every line through :mod:`srstudio.voice` (typed parse, alignment and audio
checks), hears it back with speech-to-text (:func:`srstudio.voice.check_transcript`), confirms every voice id by
name, places the lines at the speakers' own pace (:func:`srstudio.narration.plan_relaxed`) and moves the beats onto
the heard words (:func:`place`). One request per line, none retried; every bound is a constant in this module.

**Lip sync.** Each take's character timestamps (the provider's alignment, parsed and checked against the requested
text by :mod:`srstudio.voice`) become a viseme track per on-screen character (:func:`visemes`, through
:func:`srstudio.soundtrack.phoneme_states`): ``(project second, viseme)`` states sampled at :data:`VISEME_RATE` Hz
over the kept part of the take, closed outside it. The track is written to ``voiced/mouths.json`` and read back
typed by :func:`load_mouths`; the brush-drawn characters (:mod:`srstudio.toon_cast`) key their mouths on it.

**Head motion.** The same timestamps, cut to what was kept (:func:`kept_take`), are written to ``voiced/speech.json``
and read back typed by :func:`load_speech`: what :mod:`srstudio.toon_sketch` plans a moving head from (ADR 0050).
"""

from __future__ import annotations

import json
import re
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass, replace
from pathlib import Path
from typing import Any, Protocol

from . import checks, fonts, lipsync, parts, soundtrack, toon, toon_cast, toon_critters, toon_inked, toon_redrawn  # noqa: F401 - they register
from .canvas import Canvas
from .errors import SrstudioError
from .fonts import GoogleFont
from .generated import gain_to_peak, trim_speech
from .hearing import blind_lines
from .narration import Slot, confirm_voice, conform, plan_relaxed, sha256_of
from .phrasing import words_of
from .voice import Alignment, Transcript, TranscriptMismatch, Voice, VoiceSettings, check_transcript, normalize_words

__all__ = [
    "PHONE_SPEAKER",
    "SketchError",
    "Speaker",
    "Line",
    "Beat",
    "Sketch",
    "Appearance",
    "Recorded",
    "Take",
    "Cast",
    "TOON_CAST",
    "CHARACTERS",
    "check",
    "cues",
    "appearances",
    "events",
    "line_spans",
    "typing_bursts",
    "place",
    "draw_cast",
    "write_project",
    "write_voiced",
    "load_beats",
    "extend_track",
    "load_mouths",
    "kept_take",
    "write_speech",
    "load_speech",
    "visemes",
    "record",
    "effect",
    "manifest",
]

CHARACTERS = ("cat", "dog", "frog", "bear", "rabbit", "fox", "raccoon", "hedgehog", "sloth", "goat", "hamster", "bento")
LIP_SYNCED = (
    "dog",
    "frog",
    "bear",
    "rabbit",
    "fox",
    "raccoon",
    "hedgehog",
    "sloth",
    "goat",
    "hamster",
    "bento",
)  # the brush-drawn characters, whose mouths follow a viseme track
MIN_STEP = 0.15  # the least a beat may be held, seconds
LINE_LEVELS = (-12.0, 0.0)  # (dB) how far a line may sit under the others in the mix
BLANK_GAP = 0.25  # a silent beat starts this long after the line before it ends
BLANK_MARGIN = 0.30  # and this long before the next spoken beat at the latest
CAPTION_MIN = 0.85  # a caption is held at least this long when the next change can wait for it
CAPTION_LAG = 0.45  # the most a change is held back from its word to give the caption before it that time
TYPING_ARMS = ("type", "lean")  # poses whose paws are on the keys
SPEECH_MARGIN = 0.15  # keys stay quiet this long around every spoken span
TAIL_AFTER_LAST = 1.5  # the project runs at least this long after the last beat
VOICE_PEAK = 0.80
SPEECH_LEAD, SPEECH_TAIL = 0.03, 0.06
BEAT_FIELDS = ("start", "who", "caption", "eyes", "mouth", "arms", "line", "word", "event")
VISEME_RATE = 12  # viseme samples per second of speech
MOUTH_STYLE = soundtrack.PhonemeStyle(rate=VISEME_RATE, round_letters="ouw")
_TAKE_FIELDS = frozenset(("id", "who", "at", "kept", "characters", "starts", "ends"))
VISEME_OF = {
    "closed": "closed",
    "open": "open",
    "round": "round",
    "teeth": "teeth",
    "shout": "open",
    "wide": "wide",
    "lip": "lip",
}
Mouths = dict[str, list[tuple[float, str]]]  # the viseme track per character, project seconds


# what a phone's small speaker leaves of a voice: the speech band, a little pushed
PHONE_SPEAKER = "highpass=f=380,highpass=f=380,lowpass=f=3000,lowpass=f=3000,volume=4dB"


class SketchError(SrstudioError, ValueError):
    """The sketch (or a placement or recording of it) is inconsistent."""


@dataclass(frozen=True)
class Speaker:
    """A voice of the sketch; ``character`` is the Toon character it plays on screen (None: heard only)."""

    name: str
    voice: Voice
    settings: VoiceSettings
    character: str | None = None


@dataclass(frozen=True)
class Line:
    """A line of dialogue; ``heard`` lists transcripts the operator accepted for it besides its own words (a name
    or homophone speech-to-text cannot tell apart), so the speech check takes those and still refuses the rest.
    Every take is levelled to one peak, so a line meant to come out small is only small in the mix with a ``gain``:
    dB under the others, within :data:`LINE_LEVELS`; the take stays the same.
    ``phone``: the line is heard through a phone's speaker (:data:`PHONE_SPEAKER`); the speech check hears the take
    as it was said, and only the audio in the reel is band-limited."""

    speaker: str
    text: str
    heard: tuple[str, ...] = ()
    gain: float = 0.0  # dB against the others in the mix
    phone: bool = False


@dataclass(frozen=True)
class Beat:
    """One held picture from ``start`` until the next beat: who is on screen with which expression, the caption
    (empty for none), the line and word a spoken beat starts on, and a prop event (``"kind"`` or ``"kind:arg"``)."""

    start: float
    who: str
    caption: str
    eyes: str
    mouth: str
    arms: str
    line: int | None = None
    word: int | None = None
    event: str = ""
    wear: tuple[str, ...] = ()  # what ``who`` wears in this beat (the cast's ``wear``)

    @property
    def spoken(self) -> bool:
        return self.line is not None


@dataclass(frozen=True)
class Cast:
    """The characters a sketch may show and the expressions they take, by name, and what they may wear; the
    ``lip_synced`` ones key their mouths on a viseme track. Another style's sketches pass their own; the default is
    :data:`TOON_CAST`."""

    name: str
    characters: tuple[str, ...]
    lip_synced: tuple[str, ...]
    eyes: tuple[str, ...]
    mouths: tuple[str, ...]
    arms: tuple[str, ...]
    wear: tuple[str, ...] = ()
    visemes: tuple[str, ...] = toon_cast.VISEMES  # the mouths its viseme tracks may hold

    def __post_init__(self) -> None:
        if not (self.characters and self.eyes and self.mouths and self.arms):
            raise SketchError(f"the {self.name} cast needs characters and a vocabulary of eyes, mouths and arms")
        if not set(self.lip_synced) <= set(self.characters):
            raise SketchError(f"the {self.name} cast's lip-synced characters must be among {self.characters}")


TOON_CAST = Cast("Toon", CHARACTERS, LIP_SYNCED, toon.EYES, toon.MOUTHS, toon.ARMS, toon.WEAR)


@dataclass(frozen=True)
class Sketch:
    slug: str
    title: str
    speakers: tuple[Speaker, ...]
    lines: tuple[Line, ...]
    beats: tuple[Beat, ...]
    end: float
    cast: Cast = TOON_CAST
    tail: float = (
        TAIL_AFTER_LAST  # seconds the recording holds its last beat: less to cut on it (a loop, a hard button)
    )
    bare: tuple[str, ...] = ()  # the characters whose name only labels a shot the dress draws whole: never shown


@dataclass(frozen=True)
class Appearance:
    """One stretch of one character on screen, with its poses timed from its entrance."""

    who: str
    start: float
    end: float
    poses: list[dict]


# -- checks and derivations -----------------------------------------------------------------------------------------
def check(sketch: Sketch) -> None:
    """Speakers are unique and play known characters; every line has a speaker; beats start at 0, rise by
    ``MIN_STEP``, end before ``end``, show known characters and expressions, and name real words of real lines in
    order, every line started by one of them."""
    names = [s.name for s in sketch.speakers]
    if not names or len(set(names)) != len(names):
        raise SketchError("speakers need distinct names")
    if not (checks.number(sketch.tail) and sketch.tail >= 0):
        raise SketchError(f"tail {sketch.tail!r} must be a non-negative number of seconds")
    cast = sketch.cast
    played = [s.character for s in sketch.speakers if s.character is not None]
    if any(c not in cast.characters for c in played) or len(set(played)) != len(played):
        raise SketchError(f"speakers play distinct characters among {cast.characters}, not {played}")
    if not sketch.lines or any(line.speaker not in names or not line.text.strip() for line in sketch.lines):
        raise SketchError("every line needs a known speaker and some text")
    for i, line in enumerate(sketch.lines):
        if not (checks.number(line.gain) and LINE_LEVELS[0] <= line.gain <= LINE_LEVELS[1]):
            raise SketchError(f"line {i}: gain {line.gain!r} is outside {LINE_LEVELS}")
        for text in line.heard:
            if not normalize_words(text) or normalize_words(text) == normalize_words(line.text):
                raise SketchError(f"line {i}: an accepted hearing must be other words than the line, got {text!r}")
    beats = sketch.beats
    if not beats or beats[0].start != 0:
        raise SketchError("the first beat starts at 0")
    last_spoken, started = (-1, -1), []
    for i, b in enumerate(beats):
        if not checks.number(b.start) or (i and b.start < beats[i - 1].start + MIN_STEP - 1e-9):
            raise SketchError(f"beat {i} at {b.start} s is held less than {MIN_STEP} s after the one before")
        known = b.who in cast.characters and b.eyes in cast.eyes and b.mouth in cast.mouths and b.arms in cast.arms
        if not known:
            raise SketchError(f"beat {i}: {b.who}/{b.eyes}/{b.mouth}/{b.arms} is not in the {cast.name} vocabulary")
        if any(w not in cast.wear or b.wear.count(w) > 1 for w in b.wear):
            raise SketchError(f"beat {i}: wear {b.wear} is not distinct items of the {cast.name} wear {cast.wear}")
        if (b.line is None) != (b.word is None):
            raise SketchError(f"beat {i}: line and word go together")
        if b.line is not None and b.word is not None:
            if not 0 <= b.line < len(sketch.lines):
                raise SketchError(f"beat {i}: no line {b.line}")
            if not 0 <= b.word < len(sketch.lines[b.line].text.split()):
                raise SketchError(f"beat {i}: line {b.line} has no word {b.word}")
            if (b.line, b.word) <= last_spoken:
                raise SketchError(f"beat {i}: line {b.line} word {b.word} is out of order")
            last_spoken = (b.line, b.word)
            if b.line not in started:
                started.append(b.line)
    if started != list(range(len(sketch.lines))):
        raise SketchError("every line needs a beat that starts it, in order")
    if not (checks.number(sketch.end) and beats[-1].start < sketch.end - MIN_STEP + 1e-9):
        raise SketchError(f"the last beat at {beats[-1].start} s needs {MIN_STEP} s before the end {sketch.end}")


def cues(beats: Sequence[Beat], end: float, lines: Sequence[Line] = ()) -> list[dict]:
    """The caption script (``{start, end, text, caption, speaker}``): one cue per run of one caption text, the
    speaker being the one whose line the cue's first beat speaks (the character on screen for a silent beat)."""
    out: list[dict] = []
    for b, nxt in zip(beats, list(beats[1:]) + [None], strict=True):
        stop = end if nxt is None else nxt.start
        who = lines[b.line].speaker if b.line is not None and b.line < len(lines) else b.who
        if b.caption and out and out[-1]["text"] == b.caption and out[-1]["end"] == b.start:
            out[-1]["end"] = stop
        elif b.caption:
            out.append({"start": b.start, "end": stop, "text": b.caption, "caption": b.caption, "speaker": who})
    return out


def appearances(beats: Sequence[Beat], end: float) -> list[Appearance]:
    """Consecutive beats of one character are one appearance; its poses (``toon.parse_poses``) count from it."""
    out: list[Appearance] = []
    for b, nxt in zip(beats, list(beats[1:]) + [None], strict=True):
        stop = end if nxt is None else nxt.start
        pose: dict[str, Any] = {"eyes": b.eyes, "mouth": b.mouth, "arms": b.arms}
        if b.wear:  # nothing worn writes nothing, so older poses files stay as they were
            pose["wear"] = list(b.wear)
        if out and out[-1].who == b.who and out[-1].end == b.start:
            app = out[-1]
            if {k: v for k, v in app.poses[-1].items() if k != "start"} != pose:
                app.poses.append({"start": round(b.start - app.start, 6), **pose})
            out[-1] = replace(app, end=stop)
        else:
            out.append(Appearance(b.who, b.start, stop, [{"start": 0.0, **pose}]))
    return out


def events(beats: Sequence[Beat], kind: str) -> list[tuple[float, str]]:
    """``(start, argument)`` of every beat whose event is ``kind`` or ``kind:argument``."""
    out = []
    for b in beats:
        if b.event == kind:
            out.append((b.start, ""))
        elif b.event.startswith(kind + ":"):
            out.append((b.start, b.event[len(kind) + 1 :]))
    return out


def line_spans(sketch: Sketch) -> list[tuple[float, float]]:
    """Where each line is spoken in the script: from its first beat to the next line's first (or the end)."""
    check(sketch)
    starts: dict[int, float] = {}
    for b in sketch.beats:
        if b.line is not None and b.line not in starts:
            starts[b.line] = b.start
    ordered = [starts[i] for i in range(len(sketch.lines))]
    return [(a, b) for a, b in zip(ordered, ordered[1:] + [sketch.end], strict=True)]


def typing_bursts(
    beats: Sequence[Beat], end: float, speech: Sequence[tuple[float, float]] = (), step: float = 0.3
) -> list[float]:
    """Burst times (for ``srstudio.foley.taps``) ``step`` apart while a typing pose is held and nothing is said:
    keys clack between the lines, never under them; ``speech`` lists the spoken spans (project seconds)."""
    if any(b <= a for a, b in speech):
        raise SketchError("speech spans need start < end")
    quiet_from = [(a - SPEECH_MARGIN, b + SPEECH_MARGIN) for a, b in speech]
    out = []
    for b, nxt in zip(beats, list(beats[1:]) + [None], strict=True):
        if b.arms not in TYPING_ARMS:
            continue
        stop = end if nxt is None else nxt.start
        t = b.start + 0.1
        while t < stop - step:
            if not any(a <= t <= z for a, z in quiet_from):
                out.append(round(t, 6))
            t += step
    return out


def place(sketch: Sketch, word_starts: Sequence[Sequence[float]], speech_ends: Sequence[float]) -> list[Beat]:
    """The beats moved to a recording: a spoken beat starts where its word is heard (``word_starts[line][word]``,
    project seconds), a silent one a beat after the line before it ends, no earlier than its scripted distance from
    the beat before and no later than ``BLANK_MARGIN`` before the next spoken one (the midpoint when that window is
    empty). A change of caption that would cut the caption before it short of ``CAPTION_MIN`` (measured from when
    that caption appeared) waits for it, up to ``CAPTION_LAG`` after its own word. Strictly increasing by
    ``MIN_STEP``."""
    check(sketch)
    if len(word_starts) != len(sketch.lines) or len(speech_ends) != len(sketch.lines):
        raise SketchError("place needs the word starts and the speech end of every line")
    beats = sketch.beats
    out: list[Beat] = []
    shown = 0.0
    for i, b in enumerate(beats):
        if b.line is not None and b.word is not None:
            words = word_starts[b.line]
            if b.word >= len(words):
                raise SketchError(f"beat {i}: the take of line {b.line} has no word {b.word}")
            at = words[b.word]
        else:
            before = next((q for q in reversed(out) if q.line is not None), None)
            spoken_end = speech_ends[before.line] if before and before.line is not None else 0.0
            ref_gap = b.start - beats[i - 1].start if i else 0.0
            at = max(spoken_end + BLANK_GAP, (out[-1].start if out else 0.0) + ref_gap)
            nxt = next((q for q in beats[i + 1 :] if q.line is not None and q.word is not None), None)
            if nxt is not None and nxt.line is not None and nxt.word is not None:
                latest = word_starts[nxt.line][nxt.word] - BLANK_MARGIN
                floor = (out[-1].start if out else 0.0) + MIN_STEP
                at = min(at, latest) if latest >= floor else (floor + latest) / 2
        if out:
            at = max(at, out[-1].start + MIN_STEP)
            if out[-1].caption and out[-1].caption != b.caption:
                at = min(max(at, shown + CAPTION_MIN), at + CAPTION_LAG)
        if not out or out[-1].caption != b.caption:
            shown = at
        out.append(replace(b, start=round(at, 6)))
    out[0] = replace(out[0], start=0.0)
    return out


# -- drawing and files ----------------------------------------------------------------------------------------------
Drawer = Callable[..., list]


def part_of(who: str) -> str:
    """The registered character a sketch's ``who`` names."""
    return f"toon-{who}"


def drawer(who: str, versions: Mapping[str, int] | None = None) -> Drawer:
    """The drawing of a sketch's character: the version ``versions`` pins, else its latest approved (ADR 0047)."""
    name = part_of(who)
    return parts.drawing(name, parts.resolved(name, versions)).builder


def draw_cast(
    cv: Canvas,
    parent,
    beats: Sequence[Beat],
    end: float,
    taps: Sequence[float] = (),
    stickers: Mapping[str, Sequence[tuple]] | None = None,
    mouths: Mapping[str, Sequence[tuple[float, str]]] | None = None,
    versions: Mapping[str, int] | None = None,
) -> list:
    """Every appearance drawn by its character's part (:func:`drawer`, at the version ``versions`` pins), on from its
    entrance to its exit, the typing frames swapped on ``taps``; ``stickers[who]`` are layers stuck on that character
    (``toon_cast.sticky_note``) and ``mouths[who]`` its viseme track (:func:`load_mouths`); the traced cat takes
    neither."""
    groups = []
    for app in appearances(beats, end):
        poses = toon.parse_poses(app.poses, f"poses of {app.who} from {app.start} s")
        extra = drawer_extras(app.who, stickers, mouths)
        groups.extend(drawer(app.who, versions)(cv, parent, poses, app.end, taps, enter=app.start, **extra))
    return groups


def drawer_extras(
    who: str,
    stickers: Mapping[str, Sequence[tuple]] | None = None,
    mouths: Mapping[str, Sequence[tuple[float, str]]] | None = None,
) -> dict[str, Any]:
    """The keyword arguments one character's drawer takes beyond the poses: its stickers and its viseme track."""
    stuck = (stickers or {}).get(who, ())
    track = (mouths or {}).get(who, ())
    if (stuck or track) and who not in LIP_SYNCED:
        raise SketchError(f"the traced {who} takes no stickers and has no lip sync")
    out: dict[str, Any] = {}
    if stuck:
        out["stickers"] = stuck
    if track:
        out["mouths"] = track
    return out


def write_project(root: Path, sketch: Sketch, font: GoogleFont) -> None:
    """``script.json`` and ``assets/poses.json`` (the appearances) on the scripted timing, the font pinned under
    ``assets/fonts``."""
    check(sketch)
    root = Path(root)
    (root / "assets").mkdir(parents=True, exist_ok=True)
    (root / "script.json").write_text(json.dumps(cues(sketch.beats, sketch.end, sketch.lines), indent=2) + "\n")
    (root / "assets" / "poses.json").write_text(json.dumps(_appearance_data(sketch.beats, sketch.end), indent=2) + "\n")
    fonts.install(font, root / "assets" / "fonts")


def write_voiced(
    root: Path,
    beats: Sequence[Beat],
    end: float,
    lines: Sequence[Line] = (),
    mouths: Mapping[str, Sequence[tuple[float, str]]] | None = None,
) -> None:
    """``voiced/script.json``, ``voiced/poses.json`` and ``voiced/beats.json`` (every placed beat with its event,
    what the voiced build draws from; see :func:`load_beats`) for placed beats, and ``voiced/mouths.json`` (the
    viseme track per character; see :func:`load_mouths`) when ``mouths`` is given."""
    folder = Path(root) / "voiced"
    folder.mkdir(parents=True, exist_ok=True)
    (folder / "script.json").write_text(json.dumps(cues(beats, end, lines), indent=2) + "\n")
    (folder / "poses.json").write_text(json.dumps(_appearance_data(beats, end), indent=2) + "\n")
    data = {"end": end, "beats": [_beat_data(b) for b in beats]}
    (folder / "beats.json").write_text(json.dumps(data, indent=2) + "\n")
    if mouths is not None:
        track = {"end": end, "mouths": {who: [[t, v] for t, v in states] for who, states in mouths.items()}}
        (folder / "mouths.json").write_text(json.dumps(track, indent=2) + "\n")


def _beat_data(b: Beat) -> dict[str, Any]:
    """A placed beat for ``beats.json``: every field, and ``wear`` only when something is worn."""
    data: dict[str, Any] = {f: getattr(b, f) for f in BEAT_FIELDS}
    if b.wear:
        data["wear"] = list(b.wear)
    return data


def load_beats(path: Path) -> tuple[list[Beat], float]:
    """The placed beats and project end from ``voiced/beats.json``: typed, every field present, ``wear`` when
    something is worn, and nothing else; the caller runs :func:`check` on the sketch rebuilt with them."""
    try:
        data = json.loads(Path(path).read_text())
    except (OSError, ValueError) as exc:
        raise SketchError(f"{path}: {exc}") from None
    if not isinstance(data, dict) or set(data) != {"end", "beats"} or not isinstance(data["beats"], list):
        raise SketchError(f"{path}: expected an object with end and beats")
    end = data["end"]
    if not checks.number(end):
        raise SketchError(f"{path}: end must be a number of seconds")
    beats = []
    for i, q in enumerate(data["beats"]):
        if not isinstance(q, dict) or set(q) - {"wear"} != set(BEAT_FIELDS):
            raise SketchError(f"{path} beat {i}: fields must be exactly {BEAT_FIELDS} and an optional wear")
        if "wear" in q and not (
            isinstance(q["wear"], list) and q["wear"] and all(isinstance(w, str) for w in q["wear"])
        ):
            raise SketchError(f"{path} beat {i}: wear is a non-empty list of names")
        if not checks.number(q["start"]):
            raise SketchError(f"{path} beat {i}: start must be a number of seconds")
        if any(not isinstance(q[f], str) for f in ("who", "caption", "eyes", "mouth", "arms", "event")):
            raise SketchError(f"{path} beat {i}: who, caption, eyes, mouth, arms and event are strings")
        if any(q[f] is not None and (isinstance(q[f], bool) or not isinstance(q[f], int)) for f in ("line", "word")):
            raise SketchError(f"{path} beat {i}: line and word are whole numbers or null")
        beats.append(
            Beat(
                float(q["start"]),
                q["who"],
                q["caption"],
                q["eyes"],
                q["mouth"],
                q["arms"],
                q["line"],
                q["word"],
                q["event"],
                tuple(q.get("wear", ())),
            )
        )
    return beats, float(end)


def load_mouths(path: Path, cast: Cast = TOON_CAST) -> tuple[Mouths, float]:
    """The viseme track per character and the project end from ``voiced/mouths.json``: typed, every character one
    of ``cast``'s lip-synced ones (:data:`LIP_SYNCED` by default), every state ``[second, viseme]`` with the
    cast's visemes (:data:`srstudio.toon_cast.VISEMES` by default), in strictly rising time within the project."""
    try:
        data = json.loads(Path(path).read_text())
    except (OSError, ValueError) as exc:
        raise SketchError(f"{path}: {exc}") from None
    if not isinstance(data, dict) or set(data) != {"end", "mouths"} or not isinstance(data["mouths"], dict):
        raise SketchError(f"{path}: expected an object with end and mouths")
    end = data["end"]
    if not (checks.number(end) and end > 0):
        raise SketchError(f"{path}: end must be a positive number of seconds")
    out: Mouths = {}
    for who, states in data["mouths"].items():
        if who not in cast.lip_synced:
            raise SketchError(f"{path}: {who!r} is not a lip-synced character among {cast.lip_synced}")
        if not isinstance(states, list):
            raise SketchError(f"{path} {who}: states must be a list")
        track: list[tuple[float, str]] = []
        for i, state in enumerate(states):
            if not (isinstance(state, list) and len(state) == 2):
                raise SketchError(f"{path} {who} state {i}: expected [second, viseme]")
            t, v = state
            if not (checks.number(t) and 0 <= t <= end):
                raise SketchError(f"{path} {who} state {i}: the second must lie within 0..{end}")
            if v not in cast.visemes:
                raise SketchError(f"{path} {who} state {i}: viseme {v!r} is not one of {cast.visemes}")
            if track and t <= track[-1][0]:
                raise SketchError(f"{path} {who} state {i}: seconds must rise")
            track.append((float(t), v))
        out[who] = track
    return out, float(end)


def visemes(
    alignment: Alignment, at: float, clip_in: float, kept: float, *, style: soundtrack.PhonemeStyle = MOUTH_STYLE
) -> list[tuple[float, str]]:
    """The viseme states of one take placed in the project: the take's character timestamps sampled at
    :data:`VISEME_RATE` Hz over ``[clip_in, clip_in + kept)`` of the take (what was kept of it), moved to start at
    ``at`` (project seconds), consecutive repeats dropped, the mouth closed at the end. ``style`` reads the letters
    (:data:`srstudio.lipsync.SPEECH_MOUTH` for English spelling, closed bilabials, a lead and bridged word joins). A
    trimmed take opens shut until its first sample, or on the sound due then under ``style.first_sound``."""
    if not (
        checks.number(at) and at >= 0 and checks.number(clip_in) and clip_in >= 0 and checks.number(kept) and kept > 0
    ):
        raise SketchError("a take is placed at a second >= 0, cut from a second >= 0, for more than 0 s")
    phones = [
        {"c": c, "start": a, "end": b}
        for c, a, b in zip(alignment.characters, alignment.starts, alignment.ends, strict=True)
    ]
    samples = soundtrack.phoneme_states(phones, max(alignment.end, clip_in + kept), style=style)
    out: list[tuple[float, str]] = []
    for t, pose in samples:
        if t < clip_in - 1e-9 or t >= clip_in + kept - 1e-9:
            continue
        state = (round(at + t - clip_in, 6), VISEME_OF[pose])
        if not out or out[-1][1] != state[1]:
            out.append(state)
    start = round(at, 6)  # compared rounded, like the states: a take speaking from its first sample adds no key
    opening = VISEME_OF[lipsync.due_pose(phones, clip_in, style)] if style.first_sound else "closed"
    if out and out[0][1] == opening:
        out[0] = (start, opening)  # the take opens on this pose: from its first second, not the first sample
    elif not out or out[0][0] > start:
        out.insert(0, (start, opening))
    stop = round(at + kept, 6)
    if out[-1][1] != "closed":
        out.append((stop, "closed"))
    return out


def extend_track(track: list[tuple[float, str]], states: Sequence[tuple[float, str]], take: str = "") -> None:
    """Append one take's viseme states to a character's track: the takes of one character never overlap, so the
    new states start after the track's last second (a take starting exactly on the previous close replaces it)."""
    if track and states and states[0][0] == track[-1][0] and track[-1][1] == "closed":
        track.pop()
    if track and states and states[0][0] <= track[-1][0]:
        raise SketchError(f"take {take} starts at {states[0][0]} s, before the mouth closed at {track[-1][0]} s")
    track.extend(states)


def _appearance_data(beats: Sequence[Beat], end: float) -> list[dict]:
    return [{"who": a.who, "start": a.start, "end": a.end, "poses": a.poses} for a in appearances(beats, end)]


# -- recording --------------------------------------------------------------------------------------------------------
@dataclass(frozen=True)
class Take:
    """One line as the project plays it: ``audio/vo-<id>.wav`` starts at project second ``at`` and lasts ``kept``, said
    by the character ``who`` (``None`` for a voice off screen), its letters timed from the start of that file."""

    id: str
    who: str | None
    at: float
    kept: float
    alignment: Alignment


def kept_take(id: str, who: str | None, alignment: Alignment, at: float, clip_in: float, kept: float) -> Take:
    """The take cut from ``clip_in`` for ``kept`` seconds: the letters that start inside the cut, timed from it."""
    timed = [
        (c, max(0.0, a - clip_in), max(0.0, min(kept, b - clip_in)))
        for c, a, b in zip(alignment.characters, alignment.starts, alignment.ends, strict=True)
        if a - clip_in < kept
    ]
    letters = tuple(c for c, _, _ in timed)
    starts = tuple(round(a, 6) for _, a, _ in timed)
    return Take(id, who, at, kept, Alignment(letters, starts, tuple(round(b, 6) for _, _, b in timed)))


def write_speech(root: Path, takes: Sequence[Take], end: float) -> None:
    """``voiced/speech.json``: every kept take, what a moving head is planned from (see :func:`load_speech`)."""
    folder = Path(root) / "voiced"
    folder.mkdir(parents=True, exist_ok=True)
    data = [
        {"id": t.id, "who": t.who, "at": t.at, "kept": t.kept, "characters": list(t.alignment.characters),
         "starts": list(t.alignment.starts), "ends": list(t.alignment.ends)}
        for t in takes
    ]  # fmt: skip
    (folder / "speech.json").write_text(json.dumps({"end": end, "takes": data}, indent=2) + "\n")


def _take_data(path: Path, i: int, data: Any, end: float, cast: Cast) -> Take:
    where = f"{path} take {i}"
    if not (isinstance(data, dict) and set(data) == _TAKE_FIELDS):
        raise SketchError(f"{where}: expected exactly the fields {sorted(_TAKE_FIELDS)}")
    take, who, at, kept = data["id"], data["who"], data["at"], data["kept"]
    letters, starts, ends = data["characters"], data["starts"], data["ends"]
    if not (isinstance(take, str) and re.fullmatch(r"\d{2,}", take)):
        raise SketchError(f"{where}: id {take!r} is two or more digits")
    if who is not None and who not in cast.characters:
        raise SketchError(f"{where}: who {who!r} is not one of {cast.characters}")
    if not (checks.number(at) and at >= 0):
        raise SketchError(f"{where}: at must be a second >= 0")
    if not (checks.number(kept) and kept > 0):
        raise SketchError(f"{where}: kept must be a positive number of seconds")
    if at + kept > end:
        raise SketchError(f"{where}: runs past the end of the project ({end} s)")
    if not (isinstance(letters, list) and all(isinstance(c, str) for c in letters)):
        raise SketchError(f"{where}: characters must be a list of strings")
    if not (isinstance(starts, list) and isinstance(ends, list) and len(starts) == len(ends) == len(letters)):
        raise SketchError(f"{where}: one start and end per character")
    if not all(checks.number(t) for t in starts) or any(b < a for a, b in zip(starts, starts[1:], strict=False)):
        raise SketchError(f"{where}: starts must be seconds that rise")
    if not all(checks.number(b) and a <= b <= kept for a, b in zip(starts, ends, strict=True)) or (
        starts and starts[0] < 0
    ):
        raise SketchError(f"{where}: every letter ends after it starts, inside the take")
    alignment = Alignment(tuple(letters), tuple(float(t) for t in starts), tuple(float(t) for t in ends))
    return Take(take, who, float(at), float(kept), alignment)


def load_speech(path: Path, cast: Cast = TOON_CAST) -> tuple[list[Take], float]:
    """The takes and the project end from ``voiced/speech.json``: typed, no field more or fewer, every take inside the
    project and in time order, every id once, every letter's time inside its take."""
    try:
        data = json.loads(Path(path).read_text())
    except (OSError, ValueError) as exc:
        raise SketchError(f"{path}: {exc}") from None
    if not (isinstance(data, dict) and set(data) == {"end", "takes"} and isinstance(data["takes"], list)):
        raise SketchError(f"{path}: expected an object with end and takes")
    end = data["end"]
    if not (checks.number(end) and end > 0):
        raise SketchError(f"{path}: end must be a positive number of seconds")
    takes = [_take_data(path, i, take, float(end), cast) for i, take in enumerate(data["takes"])]
    for a, b in zip(takes, takes[1:], strict=False):
        if b.at < a.at:
            raise SketchError(f"{path}: takes {a.id} and {b.id} are out of time order")
    ids = [t.id for t in takes]
    twice = sorted({i for i in ids if ids.count(i) > 1})
    if twice:
        raise SketchError(f"{path}: take {twice[0]} is listed twice")
    return takes, float(end)


class _Client(Protocol):
    def synthesize(self, text: str, voice: Voice, settings: VoiceSettings) -> Any: ...

    def transcribe(self, audio: str | Path, language: str = "en") -> Transcript: ...


@dataclass(frozen=True)
class Recorded:
    """What :func:`record` produced: the manifest items, the placed beats and project end, the spoken spans, the
    confirmed voices and what speech-to-text heard."""

    items: list[dict]
    beats: list[Beat]
    end: float
    speech: list[tuple[float, float]]
    voices: dict[str, dict]
    heard: list[dict]


def record(
    sketch: Sketch,
    root: Path,
    client: _Client,
    *,
    key: str = "",
    ffmpeg: str = "ffmpeg",
    confirm: Callable[..., dict] = confirm_voice,
    conform_clip: Callable[..., float] = conform,
    mouth: soundtrack.PhonemeStyle = MOUTH_STYLE,
) -> Recorded:
    """Every line said by its speaker's voice (cached by the client), trimmed, placed at its own pace, heard back
    and conformed to ``audio/vo-NN.wav``; the beats moved onto the words and, under ``voiced/``, the viseme tracks, read
    with ``mouth``, and the kept takes (:func:`load_speech`).
    :class:`SketchError` lists every line speech-to-text did not hear as scripted (nothing is retried), and refuses a
    line no transcript could confirm (:func:`~srstudio.hearing.blind_lines`) before the first take is paid for."""
    check(sketch)
    blind = blind_lines(sketch.lines)
    if blind:
        raise SketchError("reword these lines or pass heard=(...) on them:\n" + "\n".join(blind))
    root = Path(root)
    audio = root / "audio"
    audio.mkdir(parents=True, exist_ok=True)
    cache = root / "assets" / "elevenlabs"
    speakers = {s.name: s for s in sketch.speakers}
    voices = {name: confirm(cache, key, s.voice) for name, s in speakers.items()}
    plan = [
        Slot(f"{i + 1:02d}", line.text, False, a, b)
        for i, (line, (a, b)) in enumerate(zip(sketch.lines, line_spans(sketch), strict=True))
    ]
    takes = []
    for line in sketch.lines:
        speaker = speakers[line.speaker]
        spoken = client.synthesize(line.text, speaker.voice, speaker.settings)
        takes.append((spoken, trim_speech(spoken.wav, lead=SPEECH_LEAD, tail=SPEECH_TAIL)))
    placed, needed = plan_relaxed(plan, [trim.clip_out - trim.clip_in for _, trim in takes])
    items, heard, failures, word_starts, kept_takes = [], [], [], [], []
    lip_synced = sketch.cast.lip_synced
    mouths: Mouths = {s.character: [] for s in sketch.speakers if s.character is not None and s.character in lip_synced}
    for line, slot, (spoken, trim), at in zip(sketch.lines, plan, takes, placed, strict=True):
        transcript = client.transcribe(spoken.wav)
        heard.append(
            {"id": slot.id, "speaker": line.speaker, "expected": line.text, "heard": transcript.text}
            | ({"accepted": list(line.heard)} if line.heard else {})
        )
        try:
            check_transcript(transcript, line.text, accepted=line.heard)
        except TranscriptMismatch as exc:
            failures.append(f"line {slot.id} ({line.speaker}): {exc}")
            continue
        dst = audio / f"vo-{slot.id}.wav"
        kept = round(at.kept, 6)
        colour = {"effect": PHONE_SPEAKER} if line.phone else {}
        conform_clip(
            spoken.wav,
            dst,
            trim.clip_in,
            trim.clip_in + kept,
            kept,
            gain_to_peak(trim.peak, VOICE_PEAK) + line.gain,
            ffmpeg,
            **colour,
        )
        word_starts.append([round(at.start + max(0.0, a - trim.clip_in), 6) for _, a, _ in words_of(spoken.alignment)])
        played = speakers[line.speaker].character
        kept_takes.append(kept_take(slot.id, played, spoken.alignment, round(at.start, 6), trim.clip_in, kept))
        if played is not None and played in mouths:
            extend_track(mouths[played], visemes(spoken.alignment, at.start, trim.clip_in, kept, style=mouth), slot.id)
        items.append(
            {
                "id": slot.id,
                "text": line.text,
                "phase": "line",
                "caption_start": slot.start,
                "start": round(at.start, 6),
                "duration": kept,
                "speech_duration": round(trim.clip_out - trim.clip_in, 6),
                "speed": speakers[line.speaker].settings.speed,
                "lead": 0.0,
                "tempo": 1.0,
                "lag": round(at.lag, 6),
                "cut": at.cut,
                "audio": f"audio/{dst.name}",
                "sha256": sha256_of(dst),
            }
        )
    (root / "voice-transcript.json").write_text(json.dumps({"lines": heard, "passed": not failures}, indent=2) + "\n")
    if failures:
        raise SketchError("speech check failed:\n" + "\n".join(failures))
    beats = place(sketch, word_starts, [p.end for p in placed])
    end = round(max(needed, beats[-1].start + sketch.tail), 6)
    write_voiced(root, beats, end, sketch.lines, mouths)
    write_speech(root, kept_takes, end)
    return Recorded(items, beats, end, [(p.start, p.end) for p in placed], voices, heard)


def effect(
    id: str,
    start: float,
    gain_db: float,
    root: Path,
    path: Path,
    taps: Sequence[float] | None = None,
    role: str = "effects",
) -> dict:
    """One ``effects`` entry of the manifest for a clip under ``root``; ``role="music"`` makes it a bed the lines
    duck (see :func:`srstudio.toon_sketch.build`)."""
    out: dict[str, Any] = {
        "id": id,
        "start": round(start, 6),
        "gain_db": gain_db,
        "audio": str(Path(path).relative_to(root)),
        "sha256": sha256_of(Path(path)),
    }
    if taps is not None:
        out["taps"] = [round(t, 6) for t in taps]
    if role != "effects":
        out["role"] = role
    return out


def manifest(sketch: Sketch, recorded: Recorded, effects: Sequence[Mapping[str, Any]], model: str, note: str) -> dict:
    """``narration.json`` for the episode: the lines, their voices, the effects and the extended duration."""
    return {
        "title": sketch.title,
        "language": "en-US",
        "tts_engine": "ElevenLabs",
        "model": model,
        "voice": recorded.voices,
        "voice_note": note,
        "caption_duration": sketch.end,
        "duration": recorded.end,
        "items": recorded.items,
        "effects": list(effects),
    }
