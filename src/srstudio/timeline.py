"""The timeline of an episode, read from ``dialogue.json``, ``timeline.json`` or a caption script.

``make_audio.py`` writes ``dialogue.json``: phrases with their voices and measured start/end,
sound effects, camera cuts and a few named beats (``reaction_start``, ``end_card_start``,
``park_start``...). A shot sequence brings ``timeline.json`` (``items`` of takes), and a silent
episode a list of timed captions (``script.json``). Everything time-related in a build comes from here.
"""

from __future__ import annotations

import json
import math
from collections.abc import Callable, Iterable
from dataclasses import dataclass, field
from pathlib import Path

from .errors import SrstudioError

ROUNDING = 1e-6  # recordings store start times rounded to six decimal places


class TimelineError(SrstudioError, ValueError):
    """Timing is invalid or a shot sequence would place its picture and audio on different clocks."""


class UnknownTakeError(TimelineError, KeyError):
    """The timeline has no take with that id."""


def _finite(value: float, where: str) -> None:
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
        raise TimelineError(f"{where}: expected a finite number, got {value!r}")


def _span(start: float, end: float, duration: float, where: str, *, empty: bool = False) -> None:
    _finite(start, where)
    _finite(end, where)
    if start < 0 or (end < start if empty else end <= start) or end > duration + ROUNDING:
        raise TimelineError(f"{where}: range {start}..{end} must be inside 0..{duration} with end after start")


def _alignment(items: tuple[dict, ...], duration: float, where: str) -> None:
    previous = -1.0
    for i, item in enumerate(items):
        label = f"{where} {i}"
        if not isinstance(item, dict) or not {"start", "end"} <= item.keys():
            raise TimelineError(f"{label}: expected start and end times")
        start, end = item["start"], item["end"]
        _span(start, end, duration, label, empty=True)
        if start < previous:
            raise TimelineError(f"{label}: alignment must be ordered by start time")
        previous = start


@dataclass(frozen=True)
class Phrase:
    index: int
    role: str
    text: str
    caption: str
    start: float
    end: float
    voice: str = ""
    voice_name: str = ""
    speed: float = 1.0
    timing_file: str | None = None
    trim_seconds: float = 0.0

    @property
    def span(self) -> tuple[float, float]:
        return (self.start, self.end)


@dataclass(frozen=True)
class Cut:
    time: float
    angle: str


@dataclass(frozen=True)
class SoundEffect:
    name: str
    start: float
    duration: float


@dataclass(frozen=True)
class Take:
    """One recorded take of a shot sequence (``timeline.json`` items): a line, an effect or a pause."""

    id: str
    actor: str
    shot: str
    text: str
    start: float
    duration: float
    mood: str = ""
    speech_duration: float = 0.0
    audio: str | None = None
    words: tuple[dict, ...] = ()  # {text, start, end} relative to the take
    phones: tuple[dict, ...] = ()  # {c, start, end} relative to the take
    extra: dict = field(default_factory=dict)

    @property
    def end(self) -> float:
        return self.start + self.duration

    @property
    def is_effect(self) -> bool:
        return self.actor == "sfx"


@dataclass
class Timeline:
    duration: float
    phrases: list[Phrase]
    cuts: list[Cut]
    sound_effects: list[SoundEffect]
    beats: dict[str, float] = field(default_factory=dict)
    meta: dict = field(default_factory=dict)
    root: Path | None = None
    takes: list[Take] = field(default_factory=list)

    def __post_init__(self) -> None:
        _finite(self.duration, "duration")
        if self.duration <= 0:
            raise TimelineError(f"duration must be positive, got {self.duration}")
        self._check_takes()
        previous = -1.0
        for p in self.phrases:
            _span(p.start, p.end, self.duration, f"phrase {p.index}")
            if p.start < previous:
                raise TimelineError(f"phrase {p.index}: phrases must be ordered by start time")
            previous = p.start
        previous = -1.0
        for i, cut in enumerate(self.cuts):
            _finite(cut.time, f"cut {i}")
            if not 0 <= cut.time < self.duration or cut.time <= previous:
                raise TimelineError(f"cut {i}: times must be strictly increasing inside 0..{self.duration}")
            previous = cut.time
        for effect in self.sound_effects:
            _finite(effect.duration, f"sound effect {effect.name}")
            _span(
                effect.start, effect.start + effect.duration, self.duration, f"sound effect {effect.name}", empty=True
            )
        for name, time in self.beats.items():
            _finite(time, f"beat {name}")
            if not 0 <= time <= self.duration:
                raise TimelineError(f"beat {name}: time must be inside 0..{self.duration}")

    def _check_takes(self) -> None:
        cursor = 0.0
        ids: set[str] = set()
        for take in self.takes:
            where = f"take {take.id}"
            if not take.id or take.id in ids:
                raise TimelineError(f"{where}: take IDs must be nonempty and unique")
            ids.add(take.id)
            _finite(take.duration, where)
            _span(take.start, take.end, self.duration, where)
            if abs(take.start - cursor) > ROUNDING:
                raise TimelineError(
                    f"{where}: sequence must be contiguous from zero; expected start {cursor}, got {take.start}. "
                    "Represent a pause inside a take's duration."
                )
            _finite(take.speech_duration, where)
            if not 0 <= take.speech_duration <= take.duration + ROUNDING:
                raise TimelineError(f"{where}: speech_duration must be inside 0..{take.duration}")
            _alignment(take.words, take.duration, f"{where} word")
            _alignment(take.phones, take.duration, f"{where} phone")
            cursor += take.duration

    # -- loading --------------------------------------------------------------------------
    @classmethod
    def load(cls, path: str | Path) -> Timeline:
        path = Path(path)
        data = json.loads(path.read_text())
        return cls.from_dict(data, root=path.parent)

    @classmethod
    def from_dict(cls, data: dict | list, root: Path | None = None) -> Timeline:
        if isinstance(data, list):
            return cls.from_captions(data, root)
        if "items" in data and "phrases" not in data:
            return cls.from_takes(data, root)
        phrases = [
            Phrase(
                index=i,
                role=p["role"],
                text=p["text"],
                caption=p.get("caption", p["text"]),
                start=float(p["start"]),
                end=float(p["end"]),
                voice=p.get("voice", ""),
                voice_name=p.get("voice_name", ""),
                speed=float(p.get("speed", 1.0)),
                timing_file=p.get("timing_file"),
                trim_seconds=float(p.get("trim_seconds", 0.0)),
            )
            for i, p in enumerate(data["phrases"])
        ]
        cuts = [Cut(float(c["time"]), c["angle"]) for c in data.get("camera_cuts", [])]
        sfx = [
            SoundEffect(s["name"], float(s["start"]), float(s.get("duration", 0)))
            for s in data.get("sound_effects", [])
        ]
        beats = {k: float(v) for k, v in data.items() if k.endswith(("_start", "_end")) and isinstance(v, (int, float))}
        meta = {
            k: v for k, v in data.items() if k not in ("phrases", "camera_cuts", "sound_effects") and k not in beats
        }
        return cls(
            duration=float(data["duration"]),
            phrases=phrases,
            cuts=cuts,
            sound_effects=sfx,
            beats=beats,
            meta=meta,
            root=root,
        )

    @classmethod
    def from_takes(cls, data: dict, root: Path | None = None) -> Timeline:
        """A shot-sequence timeline: contiguous takes from zero, each with its own shot, clock and audio file.

        Pauses belong in a take's duration; gaps or overlaps would desynchronise sequential picture from audio.
        """
        known = {
            "id",
            "actor",
            "shot",
            "text",
            "start",
            "duration",
            "mood",
            "speech_duration",
            "audio",
            "words",
            "phones",
        }
        takes = [
            Take(
                id=str(q["id"]),
                actor=q["actor"],
                shot=q["shot"],
                text=q["text"],
                start=float(q["start"]),
                duration=float(q["duration"]),
                mood=q.get("mood", ""),
                speech_duration=float(q.get("speech_duration", 0.0)),
                audio=q.get("audio"),
                words=tuple(q.get("words", ())),
                phones=tuple(q.get("phones", ())),
                extra={k: v for k, v in q.items() if k not in known},
            )
            for q in data["items"]
        ]
        phrases = [
            Phrase(index=i, role=t.actor, text=t.text, caption=t.text, start=t.start, end=t.end)
            for i, t in enumerate(takes)
            if not t.is_effect
        ]
        cuts = [Cut(t.start, t.shot) for t in takes]
        sfx = [SoundEffect(t.text, t.start, t.duration) for t in takes if t.is_effect]
        meta = {k: v for k, v in data.items() if k != "items"}
        return cls(
            duration=float(data["duration"]),
            phrases=phrases,
            cuts=cuts,
            sound_effects=sfx,
            meta=meta,
            root=root,
            takes=takes,
        )

    @classmethod
    def from_captions(cls, items: list, root: Path | None = None) -> Timeline:
        """A silent caption script: a list of ``{start, end, text, caption?}`` in order; it ends with the last one.

        A caption without its own ``caption`` text is the spoken text without its ellipsis (the lettering rule)."""
        if not items:
            raise TimelineError("a caption script needs at least one caption")
        phrases: list[Phrase] = []
        for i, q in enumerate(items):
            if not isinstance(q, dict) or not {"start", "end", "text"} <= set(q):
                raise TimelineError(f"caption {i}: expected an object with start, end and text")
            start, end = float(q["start"]), float(q["end"])
            if end <= start:
                raise TimelineError(f"caption {i}: end {end} must come after start {start}")
            if phrases and start < phrases[-1].end - 1e-9:
                raise TimelineError(f"caption {i}: overlaps the caption before it ({phrases[-1].end} > {start})")
            text = str(q["text"])
            caption = q.get("caption") or text.replace("...", "")
            phrases.append(Phrase(index=i, role="caption", text=text, caption=str(caption), start=start, end=end))
        return cls(duration=phrases[-1].end, phrases=phrases, cuts=[], sound_effects=[], root=root)

    def take(self, id: str) -> Take:
        for t in self.takes:
            if t.id == id:
                return t
        raise UnknownTakeError(f"no take {id!r}")

    # -- beats ------------------------------------------------------------------------------
    def __getattr__(self, name: str) -> float:
        # ``timeline.reaction_start``, ``timeline.park_start``... read the named beats.
        beats = self.__dict__.get("beats", {})
        if name in beats:
            return beats[name]
        raise AttributeError(name)

    @property
    def reaction(self) -> float:
        return self.beats["reaction_start"]

    @property
    def ending(self) -> float:
        """``end_card_start`` when the episode has one, else the duration."""
        return self.beats.get("end_card_start", self.duration)

    # -- phrases ----------------------------------------------------------------------------
    def phrase(self, i: int) -> Phrase:
        return self.phrases[i]

    def spans(self, role: str) -> list[tuple[float, float]]:
        return [p.span for p in self.phrases if p.role == role]

    def roles(self) -> list[str]:
        seen: list[str] = []
        for p in self.phrases:
            if p.role not in seen:
                seen.append(p.role)
        return seen

    def cut_time(self, i: int) -> float:
        return self.cuts[i].time

    # -- shots ------------------------------------------------------------------------------
    def shots(self, angles: Iterable[str] | Callable[[str], bool]) -> list[tuple[float, float]]:
        """The intervals a camera setup is on screen, from consecutive cuts whose angle matches.

        ``angles`` is a set of angle names or a predicate; adjacent matching cuts merge.
        """
        match = angles if callable(angles) else (lambda a, s=set(angles): a in s)
        out: list[tuple[float, float]] = []
        for i, cut in enumerate(self.cuts):
            if not match(cut.angle):
                continue
            end = self.cuts[i + 1].time if i + 1 < len(self.cuts) else self.duration
            if out and abs(out[-1][1] - cut.time) < 1e-9:
                out[-1] = (out[-1][0], end)
            else:
                out.append((cut.time, end))
        return out

    # -- word-level timing ----------------------------------------------------------------------
    def word_time(self, phrase: int | Phrase, word: str) -> float:
        """When ``word`` starts inside a phrase, from the provider's character timestamps."""
        p = phrase if isinstance(phrase, Phrase) else self.phrases[phrase]
        if not p.timing_file or self.root is None:
            raise TimelineError(f"phrase {p.index} has no timing file")
        provider = json.loads((self.root / p.timing_file).read_text())
        alignment = provider.get("normalized_alignment") or provider["alignment"]
        text = "".join(alignment["characters"]).lower()
        index = text.index(word.lower())
        return p.start + alignment["character_start_times_seconds"][index] - p.trim_seconds
