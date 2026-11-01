"""The Unwritten Rules as a format: what every episode with Rafa shares, so an episode is its script and its sounds.

A :class:`Show` holds the script as :class:`Beat`, the seconds each take measured and the post. From those it derives
the sketch for the recording, the timing, the labels and the moods, and :meth:`Show.validate` keeps the format: a
"Nobody tells you" claim, three numbered rules, a hold of at least 1.2 s before a punchline, the sign-off last, and the
length at :data:`PACE`. :func:`run` builds an episode on it (ADR 0066, ADR 0068).

ARCHITECTURAL REQUIREMENT: LLMs will always produce some form of error.
Absence of output verification is a design defect, not a runtime bug.
All LLM output must be treated as untrusted and validated explicitly.
"""

from __future__ import annotations

import os
from collections.abc import Callable, Sequence
from dataclasses import dataclass, replace
from functools import cached_property, lru_cache, partial
from pathlib import Path

from . import foley as synth
from . import host_kit, rafa, rafa_host, rafa_reel, scripting, sketch, toon
from .errors import SrstudioError
from .fonts import text_width
from .host_kit import BONE
from .layout import VERTICAL
from .rafa_reel import Act, Renders
from .sketch import Beat as SketchBeat
from .sketch import Line, Sketch, Speaker
from .social import InstagramPost
from .toon_sketch import Staging, build, recorder
from .voice import Voice, VoiceSettings

__all__ = [
    "FRAMINGS",
    "GAP",
    "LONGEST",
    "MOUTH",
    "NOTE",
    "NARRATION",
    "PACE",
    "SEED",
    "SHORTEST",
    "SIGN_OFF",
    "SPEAKER",
    "TAIL",
    "Beat",
    "ScriptError",
    "Show",
    "audio_main",
    "run",
    "shared_sounds",
    "sounder",
]

HOST = "rafa"
VOICE = Voice(role=HOST, id="bIHbv24MWmeRgasZH58o", name="Will")  # the operator's choice, 2026-10-31
SETTINGS = VoiceSettings(stability=0.42, similarity_boost=0.75, style=0.35)
SPEAKER = Speaker(HOST, VOICE, SETTINGS, HOST)
SEED = 52026
NARRATION = "Voiced with the ElevenLabs premade voice Will; synthesised foley."
NOTE = "ElevenLabs premade voice Will at its natural pace; no reference-voice cloning."
TINTS = {HOST: BONE}
MOUTH = replace(
    sketch.MOUTH_STYLE, spelling=True, close_bilabials=True, lead=0.04, min_rest=0.12, fine=True, first_sound=True
)
GAP = 0.2  # seconds of air between two lines that have no hold
TAIL = 0.5  # seconds the reel runs on after the sign-off
PACE = 2.7  # spoken words a second, the estimate a length is checked at until a take measures it
SHORTEST, LONGEST = 20.0, 30.0
LEAST_HOLD = 1.2  # the hold a punchline needs before it
SIGN_OFF = "You know what you did."
HOOK = "Nobody tells you"
FRAMINGS = ("medium", "close", "tight")
ROOM_GAIN = -30.0  # the room under the holds: there when he stops, gone when he speaks
PLACEHOLDER = ("side", "flat", "desk")  # a pose for the sketch's check: this man is drawn from his acts
RULES = ["RULE 1", "RULE 2", "RULE 3"]


class ScriptError(SrstudioError, ValueError):
    """A beat this show cannot stage."""


@dataclass(frozen=True)
class Beat:
    """One line of the script: its ``id``, the words, his ``mood``, what his hand is on, the ``framing``, the seconds
    he holds after it, an ``insert`` that takes the frame for a moment, the ``label`` and the line's ``gain`` in dB."""

    id: str
    line: str
    mood: str
    prop: str
    framing: str = "medium"
    hold: float = 0.0
    insert: str = ""
    label: str = ""
    gain: float = 0.0


@dataclass(frozen=True)
class Show:
    """One episode: ``number`` in the series, the script in ``beats``, ``kept`` the seconds each take measured."""

    slug: str
    number: int
    title: str
    description: str
    accessibility: str
    beats: tuple[Beat, ...]
    kept: tuple[float, ...]
    post: InstagramPost
    stop: str  # the beat the third rule's label goes on: he turns on you there
    push: tuple[float, float] = (2.4, 1.05)  # (seconds, scale) of the opening move; a scale of 1.0 is a still opening
    room: str = "rafa-kitchen"

    @property
    def output(self) -> str:
        return f"renders/pilots/{self.slug}.mp4"

    @property
    def names(self) -> tuple[str, ...]:
        return tuple(beat.id for beat in self.beats)

    @property
    def acts(self) -> tuple[Act, ...]:
        return tuple(Act(beat.framing, beat.prop, beat.mood) for beat in self.beats)

    @property
    def lines(self) -> tuple[Line, ...]:
        return tuple(Line(HOST, beat.line, gain=beat.gain) for beat in self.beats)

    def spoken_words(self) -> int:
        return sum(len(beat.line.split()) for beat in self.beats)

    def estimated_seconds(self) -> float:
        """The script's length at :data:`PACE`, with its holds: an estimate until a take measures it."""
        return self.spoken_words() / PACE + sum(beat.hold for beat in self.beats)

    def starts(self) -> tuple[float, ...]:
        """Where each line starts: where the one before ends, plus its hold, or :data:`GAP` when it has none."""
        rows, at = [], 0.0
        for beat, kept in zip(self.beats, self.kept, strict=True):
            rows.append(round(at, 3))
            at += kept + (beat.hold or GAP)
        return tuple(rows)

    @cached_property
    def sketch(self) -> Sketch:
        """The script for the recording, timed from the takes."""
        script = scripting.Script(self.lines)
        beats = tuple(script.say(at, HOST, i, *PLACEHOLDER) for i, at in enumerate(self.starts()))
        end = round(self.starts()[-1] + self.kept[-1] + TAIL, 3)
        return Sketch(self.slug, self.title, (SPEAKER,), self.lines, beats, end, cast=rafa_host.CAST)

    def said(self, speech: Sequence[tuple[float, float]]) -> dict[str, tuple[float, float]]:
        """When each line was said, by the name of its beat."""
        return dict(zip(self.names, speech, strict=True))

    def beat(self, name: str, beats: Sequence[SketchBeat] | None = None) -> SketchBeat:
        """The beat called ``name``, from the sketch's or a recording's ``beats``."""
        return (self.sketch.beats if beats is None else beats)[self.names.index(name)]

    def validate(self, beats: tuple[Beat, ...] | None = None) -> None:
        """Every beat is one the show can stage and the script keeps the format, or :class:`ScriptError`."""
        beats = self.beats if beats is None else beats
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
        if not beats[0].line.startswith(HOOK):
            raise ScriptError(f"the show opens on a Nobody Tells You claim, got {beats[0].line!r}")
        if [beat.label for beat in beats if beat.label.startswith("RULE")] != RULES:
            raise ScriptError("the show has three rules, in order")
        if beats[-1].line != SIGN_OFF:
            raise ScriptError(f"the show ends on its sign-off, got {beats[-1].line!r}")
        if beats[-1].id != "off" or self.stop not in {beat.id for beat in beats}:
            raise ScriptError(f"the last beat is 'off' and the label stops on a beat, got {self.stop!r}")
        if not any(beat.hold >= LEAST_HOLD for beat in beats):
            raise ScriptError(f"a punchline needs a hold of at least {LEAST_HOLD} s before it")
        if not {beat.prop for beat in beats} <= set(rafa_host.PLACES):
            raise ScriptError("every prop needs a place on the worktop")
        length = sum(len(beat.line.split()) for beat in beats) / PACE + sum(beat.hold for beat in beats)
        if not SHORTEST <= length <= LONGEST:
            raise ScriptError(
                f"the show runs {SHORTEST} to {LONGEST} s, this comes to {length:.1f} s at {PACE} words a second"
            )

    def validate_sketch(self, sk: Sketch | None = None) -> None:
        """The sketch is consistent, parallel to the script, and shows no word the show keeps off the screen."""
        sk = self.sketch if sk is None else sk
        self.validate()
        sketch.check(sk)
        if len(sk.beats) != len(self.beats) or [q.text for q in sk.lines] != [b.line for b in self.beats]:
            raise ScriptError(f"{len(sk.beats)} beats for the script's {len(self.beats)}")
        if sk.beats[0].line is None:
            raise ScriptError("the reel opens on his line")
        for text in (*(b.label for b in self.beats if b.label), self.post.title, self.post.description):
            host_kit.check_copy(text)

    def labels(self, beats: Sequence[SketchBeat], end: float) -> list[tuple[float, float, str]]:
        """Each label from its beat to the next label, the third to :attr:`stop`."""
        rows = [(beats[i].start, b.label) for i, b in enumerate(self.beats) if b.label]
        stops = [at for at, _ in rows[1:]] + [self.beat(self.stop, beats).start]
        return [(at, min(stop, end), text) for (at, text), stop in zip(rows, stops, strict=True)]

    def overlay(self, cv, parent, beats, end, measure, *, root: Path, renders: Renders) -> None:
        """Over the picture: each insert on its own, the labels, the sign-off, the signature marks."""
        for name, beat in zip(self.names, self.beats, strict=True):
            if beat.insert:
                stop = self.names[self.names.index(name) + 1]
                shown = rafa_reel.insert(
                    cv, parent, beat.insert, self.beat(name, beats).start, self.beat(stop, beats).start, renders, root
                )
                host_kit.finish(cv, shown)
        host_kit.sign(cv, parent)
        for first, last, text in self.labels(beats, end):
            host_kit.label(cv, parent, text, first, last, measure)
        host_kit.sign_off(cv, parent, SIGN_OFF, self.beat("off", beats).start, end, measure)


def sounder(root: Path, end: float, seed: int) -> Callable[..., dict]:
    """A maker of foley tracks for one episode: ``sound(id, gain, burst, times)``, one clip the length of the reel."""
    audio = Path(root) / "audio"
    audio.mkdir(parents=True, exist_ok=True)

    def sound(id: str, gain: float, burst: synth.Burst, times: Sequence[float]) -> dict:
        path = synth.write_bursts(audio / f"{id}.wav", list(times), end, burst, seed=seed)
        return sketch.effect(id, 0.0, gain, root, path)

    return sound


def shared_sounds(show: Show, beats, end: float, speech, root: Path, seed: int) -> list[dict]:
    """What lands in every episode: the room under it all, the mug, the phone, the folder, and the mug set down last."""
    sound, said = sounder(root, end, seed), show.said(speech)
    audio = Path(root) / "audio"
    room = synth.write_room(audio / "room.wav", end, seed=seed)
    buzz = synth.write_buzz(audio / "buzz.wav", [show.beat("two", beats).start], end, seed=seed)
    return [
        sketch.effect("room", 0.0, ROOM_GAIN, root, room),
        sound("mug", -9.0, synth.KNOCK, [show.beat("one", beats).start, said["off"][1]]),
        sketch.effect("buzz", 0.0, -6.0, root, buzz),
        sound("folder", -6.0, synth.THUD, [show.beat("three", beats).start]),
    ]


def audio_main(show: Show, doc: str | None, foley_of: Callable[..., list[dict]]) -> Callable[..., int]:
    """The ``main`` of an episode's recording script: Will says every line, one take a line."""
    return recorder(show.sketch, SEED, NOTE, doc, mouth=MOUTH, validate=show.validate_sketch, foley_of=foley_of)


def run(show: Show, argv: Sequence[str], env=os.environ) -> None:
    """``python3 <episode>.py PROJECT [--init | --voice]``: the episode's project files, or its master."""
    show.validate_sketch()
    root = Path(argv[1]).resolve()
    voiced = "--voice" in argv
    renders = Renders(
        Path(env["SRSTUDIO_ENGINE"]),
        Path(env.get("SRSTUDIO_PLATES", Path(env["SRSTUDIO_RENDERS"]).parent / "plates")),
        Path(env["SRSTUDIO_FONTS"]),
    )

    @lru_cache(maxsize=1)
    def plan_of(end: float):
        return host_kit.head_plan(root, end, voiced, cast=rafa_host.CAST, style=rafa_host.MOTION)

    staging = Staging(
        sketch=show.sketch,
        seed=SEED,
        description=show.description,
        accessibility=show.accessibility,
        narration=NARRATION,
        tints=TINTS,
        dress=rafa_reel.stage(show.acts, plan_of, renders, root, room=show.room, push=show.push),
        versions={},
        desk=lambda cv, parent: None,  # the worktop is on his plates
        style=host_kit.HOST,
        bare=rafa_host.CAST.characters,
        captions=lambda *_: None,  # the engine's track, added to the built episode below
        camera=rafa_reel.framing(show.acts),
        finish=host_kit.finish,
        overlay=partial(show.overlay, root=root, renders=renders),
        safe_area=VERTICAL,
        output=show.output,
        crf="25",
    )
    ep = build(root, staging, set(argv[2:]))
    if ep is not None:  # None: --init wrote the project files
        if ep.spec.font is None:
            raise ScriptError("the show's style draws no text")
        font = (root / ep.spec.font).read_bytes()
        words = host_kit.spoken(root, rafa_host.CAST) if voiced else ()
        lines = toon.load_script(root / ep.spec.dialogue)
        ep.hide_on_cover(*host_kit.captions(ep, lines, partial(text_width, font), words, (SIGN_OFF,)))
        ep.finish()
