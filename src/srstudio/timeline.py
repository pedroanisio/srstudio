"""The timeline of an episode, read from ``dialogue.json``, ``timeline.json`` or a caption script.

``make_audio.py`` writes ``dialogue.json``: phrases with their voices and measured start/end,
sound effects, camera cuts and a few named beats (``reaction_start``, ``end_card_start``,
``park_start``...). A shot sequence brings ``timeline.json`` (``items`` of takes), and a silent
episode a list of timed captions (``script.json``). Everything time-related in a build comes from here.
"""

from __future__ import annotations

import json
import re
from collections.abc import Callable, Iterable
from dataclasses import dataclass, field
from pathlib import Path

from . import checks
from .errors import SrstudioError

ROUNDING = 1e-6  # recordings store start times rounded to six decimal places


class TimelineError(SrstudioError, ValueError):
    """Timing is invalid or a shot sequence would place its picture and audio on different clocks."""


class UnknownTakeError(TimelineError, KeyError):
    """The timeline has no take with that id."""


def _invalid(message: str, code: str, path: str, actual: object, expected: object) -> TimelineError:
    return TimelineError(
        message,
        code=f'timeline.{code}',
        path=path,
        actual=actual,
        expected=expected,
        remedy=f'Correct {path} to match the expected value and reload the timeline.',
    )


def _record(value: object, where: str, required: tuple[str, ...], *, path: str | None = None) -> dict:
    path = where if path is None else path
    if not isinstance(value, dict):
        raise _invalid(f"{where}: expected an object", 'object', path, value, 'object')
    for name in required:
        if name not in value:
            field_path = f'{path}.{name}' if path and path != 'timeline' else name
            raise _invalid(f"{where}.{name}: required field is missing", 'required', field_path, None, 'required field')
    return value


def _rows(value: object, where: str, required: tuple[str, ...], *, path: str | None = None) -> list[dict]:
    path = where if path is None else path
    if not isinstance(value, (list, tuple)):
        raise _invalid(f"{where}: expected a list or tuple", 'sequence', path, value, 'list or tuple')
    return [_record(item, f"{where} {i}", required, path=f'{path}[{i}]') for i, item in enumerate(value)]


def _text(value: object, where: str, *, path: str | None = None) -> str:
    if not isinstance(value, str) or not value.strip():
        raise _invalid(f"{where}: expected a nonempty string", 'text', path or where, value, 'nonempty string')
    return value


def _number(value: object, where: str, *, path: str | None = None) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float, str)):
        raise _invalid(
            f"{where}: expected a finite number, got {value!r}", 'number', path or where, value, 'finite number'
        )
    try:
        result = float(value)
    except (ValueError, OverflowError) as exc:
        raise _invalid(
            f"{where}: expected a finite number, got {value!r}", 'number', path or where, value, 'finite number'
        ) from exc
    _finite(result, where, path=path)
    return result


def _finite(value: float, where: str, *, path: str | None = None) -> None:
    if not checks.number(value):
        raise _invalid(
            f"{where}: expected a finite number, got {value!r}", 'number', path or where, value, 'finite number'
        )


def _span(
    start: float, end: float, duration: float, where: str, *, empty: bool = False, path: str | None = None
) -> None:
    _finite(start, where, path=f'{path}.start' if path else None)
    _finite(end, where, path=f'{path}.end' if path else None)
    if start < 0 or (end < start if empty else end <= start) or end > duration + ROUNDING:
        raise _invalid(
            f"{where}: range {start}..{end} must be inside 0..{duration} with end after start",
            'range',
            path or where,
            {'start': start, 'end': end},
            {'minimum': 0, 'maximum': duration, 'empty_allowed': empty},
        )


def _alignment(items: tuple[dict, ...], duration: float, where: str, *, path: str) -> None:
    previous = -1.0
    for i, item in enumerate(items):
        label = f"{where} {i}"
        if not isinstance(item, dict) or not {"start", "end"} <= item.keys():
            raise TimelineError(f"{label}: expected start and end times")
        start, end = item["start"], item["end"]
        _span(start, end, duration, label, empty=True, path=f'{path}[{i}]')
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
            raise _invalid(
                f"duration must be positive, got {self.duration}",
                'positive',
                'duration',
                self.duration,
                'positive number',
            )
        self._check_takes()
        previous = -1.0
        for p in self.phrases:
            _span(p.start, p.end, self.duration, f"phrase {p.index}", path=f'phrases[{p.index}]')
            if p.start < previous:
                raise TimelineError(f"phrase {p.index}: phrases must be ordered by start time")
            previous = p.start
        previous = -1.0
        for i, cut in enumerate(self.cuts):
            _finite(cut.time, f"cut {i}", path=f'camera_cuts[{i}].time')
            if not 0 <= cut.time < self.duration or cut.time <= previous:
                raise _invalid(
                    f"cut {i}: times must be strictly increasing inside 0..{self.duration}",
                    'order',
                    f'camera_cuts[{i}].time',
                    cut.time,
                    {'minimum': 0, 'exclusive_maximum': self.duration, 'after': previous},
                )
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
        for i, take in enumerate(self.takes):
            where = f"take {take.id}"
            if not take.id or take.id in ids:
                raise TimelineError(f"{where}: take IDs must be nonempty and unique")
            ids.add(take.id)
            _finite(take.duration, where, path=f'items[{i}].duration')
            _span(take.start, take.end, self.duration, where, path=f'items[{i}]')
            if abs(take.start - cursor) > ROUNDING:
                raise TimelineError(
                    f"{where}: sequence must be contiguous from zero; expected start {cursor}, got {take.start}. "
                    "Represent a pause inside a take's duration."
                )
            _finite(take.speech_duration, where)
            if not 0 <= take.speech_duration <= take.duration + ROUNDING:
                raise TimelineError(f"{where}: speech_duration must be inside 0..{take.duration}")
            _alignment(take.words, take.duration, f"{where} word", path=f'items[{i}].words')
            _alignment(take.phones, take.duration, f"{where} phone", path=f'items[{i}].phones')
            cursor += take.duration

    # -- loading --------------------------------------------------------------------------
    @classmethod
    def load(cls, path: str | Path) -> Timeline:
        path = Path(path)
        try:
            data = json.loads(path.read_text())
        except OSError as exc:
            raise TimelineError(f"{path}: cannot read timeline: {exc}") from exc
        except (json.JSONDecodeError, UnicodeError) as exc:
            raise TimelineError(f"{path}: invalid timeline JSON: {exc}") from exc
        return cls.from_dict(data, root=path.parent)

    @classmethod
    def from_dict(cls, data: dict | list, root: Path | None = None) -> Timeline:
        if isinstance(data, list):
            return cls.from_captions(data, root)
        data = _record(data, "timeline", ("duration",))
        if "items" in data and "phrases" in data:
            raise TimelineError("timeline: choose either 'phrases' or 'items', not both")
        if "items" in data:
            return cls.from_takes(data, root)
        data = _record(data, "timeline", ("phrases",))
        phrase_rows = _rows(data["phrases"], "phrases", ("role", "text", "start", "end"))
        cut_rows = _rows(data.get("camera_cuts", []), "camera_cuts", ("time", "angle"))
        effect_rows = _rows(data.get("sound_effects", []), "sound_effects", ("name", "start"))
        phrases = [
            Phrase(
                index=i,
                role=_text(p["role"], f"phrase {i}.role", path=f'phrases[{i}].role'),
                text=_text(p["text"], f"phrase {i}.text", path=f'phrases[{i}].text'),
                caption=_text(p.get("caption", p["text"]), f"phrase {i}.caption", path=f'phrases[{i}].caption'),
                start=_number(p["start"], f"phrase {i}.start", path=f'phrases[{i}].start'),
                end=_number(p["end"], f"phrase {i}.end", path=f'phrases[{i}].end'),
                voice=p.get("voice", ""),
                voice_name=p.get("voice_name", ""),
                speed=_number(p.get("speed", 1.0), f"phrase {i}.speed", path=f'phrases[{i}].speed'),
                timing_file=p.get("timing_file"),
                trim_seconds=_number(
                    p.get("trim_seconds", 0.0), f"phrase {i}.trim_seconds", path=f'phrases[{i}].trim_seconds'
                ),
            )
            for i, p in enumerate(phrase_rows)
        ]
        cuts = [
            Cut(
                _number(c["time"], f"camera_cuts {i}.time", path=f'camera_cuts[{i}].time'),
                _text(c["angle"], f"camera_cuts {i}.angle", path=f'camera_cuts[{i}].angle'),
            )
            for i, c in enumerate(cut_rows)
        ]
        sfx = [
            SoundEffect(
                s["name"],
                _number(s["start"], f"sound_effects {i}.start", path=f'sound_effects[{i}].start'),
                _number(s.get("duration", 0), f"sound_effects {i}.duration", path=f'sound_effects[{i}].duration'),
            )
            for i, s in enumerate(effect_rows)
        ]
        beats = {k: _number(v, f"beat {k}") for k, v in data.items() if k.endswith(("_start", "_end"))}
        meta = {
            k: v for k, v in data.items() if k not in ("phrases", "camera_cuts", "sound_effects") and k not in beats
        }
        return cls(
            duration=_number(data["duration"], "duration"),
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
        data = _record(data, "timeline", ("duration", "items"))
        take_rows = _rows(data["items"], "items", ("id", "actor", "shot", "text", "start", "duration"))
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
        for i, q in enumerate(take_rows):
            if not isinstance(q["id"], (str, int)) or isinstance(q["id"], bool) or not str(q["id"]).strip():
                raise TimelineError(f"take {i}.id: expected a nonempty string or integer")
            if not isinstance(q["shot"], str):
                raise TimelineError(f"take {i}.shot: expected a string")
        takes = [
            Take(
                id=str(q["id"]),
                actor=_text(q["actor"], f"take {i}.actor", path=f'items[{i}].actor'),
                shot=q["shot"],
                text=_text(q["text"], f"take {i}.text", path=f'items[{i}].text'),
                start=_number(q["start"], f"take {i}.start", path=f'items[{i}].start'),
                duration=_number(q["duration"], f"take {i}.duration", path=f'items[{i}].duration'),
                mood=q.get("mood", ""),
                speech_duration=_number(
                    q.get("speech_duration", 0.0), f"take {i}.speech_duration", path=f'items[{i}].speech_duration'
                ),
                audio=q.get("audio"),
                words=tuple(_rows(q.get("words", []), f"take {i}.words", ("start", "end"), path=f'items[{i}].words')),
                phones=tuple(
                    _rows(q.get("phones", []), f"take {i}.phones", ("start", "end"), path=f'items[{i}].phones')
                ),
                extra={k: v for k, v in q.items() if k not in known},
            )
            for i, q in enumerate(take_rows)
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
            duration=_number(data["duration"], "duration"),
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
        for i, q in enumerate(_rows(items, "caption", ("start", "end", "text"), path="")):
            start = _number(q["start"], f"caption {i}.start", path=f'[{i}].start')
            end = _number(q["end"], f"caption {i}.end", path=f'[{i}].end')
            if end <= start:
                raise _invalid(
                    f"caption {i}: end {end} must come after start {start}",
                    'range',
                    f'[{i}]',
                    {'start': start, 'end': end},
                    'end after start',
                )
            if phrases and start < phrases[-1].end - 1e-9:
                raise TimelineError(f"caption {i}: overlaps the caption before it ({phrases[-1].end} > {start})")
            text = _text(q["text"], f"caption {i}.text", path=f'[{i}].text')
            supplied_caption = q.get("caption")
            if supplied_caption is not None and not isinstance(supplied_caption, str):
                raise TimelineError(f"caption {i}.caption: expected a string or None")
            caption = supplied_caption or text.replace("...", "")
            phrases.append(Phrase(index=i, role="caption", text=text, caption=caption, start=start, end=end))
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
    def shots(self, angles: str | Iterable[str] | Callable[[str], bool]) -> list[tuple[float, float]]:
        """The intervals a camera setup is on screen, from consecutive cuts whose angle matches.

        ``angles`` is one angle name, an iterable of names or a predicate; adjacent matching cuts merge.
        """
        if callable(angles):
            match = angles
        else:
            names = {angles} if isinstance(angles, str) else set(angles)
            match = names.__contains__
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
        """When ``word`` (one word or a run of them, matched whole and case-blind) first starts inside a phrase, from
        the provider's character timestamps."""
        p = phrase if isinstance(phrase, Phrase) else self.phrases[phrase]
        if not p.timing_file or self.root is None:
            raise TimelineError(f"phrase {p.index} has no timing file")
        path = self.root / p.timing_file
        where = f"phrase {p.index} timing file {path}"
        try:
            provider = json.loads(path.read_text())
        except (OSError, UnicodeError, json.JSONDecodeError) as exc:
            raise TimelineError(f"{where}: cannot read alignment: {exc}") from exc
        if not isinstance(provider, dict):
            raise TimelineError(f"{where}: expected an object")
        alignment = provider.get("normalized_alignment") or provider.get("alignment")
        if not isinstance(alignment, dict):
            raise TimelineError(f"{where}: expected an alignment object")
        chars = alignment.get("characters")
        times = alignment.get("character_start_times_seconds")
        if (
            not isinstance(chars, list)
            or not all(isinstance(c, str) and len(c) == 1 for c in chars)
            or not isinstance(times, list)
            or len(times) != len(chars)
        ):
            raise TimelineError(f"{where}: characters and character_start_times_seconds must be equally sized arrays")
        parsed = [_number(value, f"{where}: character time {i}") for i, value in enumerate(times)]
        if any(value < 0 for value in parsed) or any(b < a for a, b in zip(parsed, parsed[1:], strict=False)):
            raise TimelineError(f"{where}: character times must be non-negative and ordered")
        text = "".join(chars)
        found = re.search(rf"(?<![\w'’]){re.escape(word)}(?![\w'’])", text, re.IGNORECASE)
        if found is None:
            raise TimelineError(f"phrase {p.index}: no word {word!r} in {text!r}")
        index = found.start()
        return p.start + parsed[index] - p.trim_seconds
