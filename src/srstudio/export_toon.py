"""The toon staging of sreditor's export: its cast drawn on its beats, each take in its set, each prop on its event.

ARCHITECTURAL REQUIREMENT: LLMs will always produce some form of error.
Absence of output verification is a design defect, not a runtime bug.
All LLM output must be treated as untrusted and validated explicitly.

An export whose ``episode.json`` names the ``toon`` style and that carries beats (``assets/poses.json``) is built as a
Toon sketch (:mod:`srstudio.toon_sketch`), the way an episode script builds one, from what the export already holds
instead of a recording run:

* the speakers are the timeline's actors; one whose bible entry draws a Toon character (its first ``look.drawing``
  part, such as ``toon-lyra``) plays it, at the version the bible pins;
* each take is a line; its words, as the export timed them, are cut into captions that each fit one pill and are on
  screen long enough to read (:func:`captions`), and the poses and prop events of ``assets/poses.json`` and
  ``assets/events.json`` become the beats between them;
* the takes' audio, the placed beats, the lips read from the word timings (:func:`srstudio.sketch.lips`) and
  ``narration.json`` are written where the voiced build reads them, so :func:`srstudio.toon_sketch.build` checks them
  as it checks a recording;
* ``assets/staging.json`` names the set of each take (a registered ``location``) and the drawing of each prop
  (a registered ``prop``): a set stands behind the character through its take, a prop in front of her from its event
  to the end of that take. A take with no set plays on the style's own room.

The export carries no letters for the style, so the pills are set in the bundled DejaVu Sans Bold, and the signature
(cactus and code) stands in the lower corner in place of the office desk, which a set of the export would not have.
Every input is checked: a cast, set or prop the catalogue does not draw is an :class:`ExportError` naming it.
"""

from __future__ import annotations

import inspect
import json
import shutil
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass, replace
from functools import partial
from pathlib import Path
from typing import Any

from . import fonts, registry, sketch, toon, toon_sketch
from .episode import Episode
from .export_build import ExportError
from .layout import Box
from .narration import sha256_of
from .signature import cactus, code
from .styles import CUTOUT, TOON
from .voice import Alignment, Voice, VoiceSettings

__all__ = ["Take", "build_toon", "is_toon", "toon_staging"]

POSES = "assets/poses.json"
EVENTS = "assets/events.json"
STAGING = "assets/staging.json"
CAST = "bible/cast.json"
TOON_PREFIX = "toon-"
POSE_KEYS = ("eyes", "mouth", "arms")
NO_VOICE = VoiceSettings(stability=0.5, similarity_boost=0.75, style=0.0)  # never asked: the takes are recorded
CACTUS_AT = (1000.0, 1830.0)  # frame pixels: the lower right corner, clear of the pills at the top
CACTUS_SCALE = 0.55
# A prop stands on the floor at her side, in front of whatever the set has there (Toon reference pixels), for a drawing
# that takes a place; one that does not stands where it draws itself.
PROP_PLACE = {"at": (420.0, 1040.0), "scale": 0.8}
CODE_AT = (1050.0, 1880.0)  # frame pixels: the code's right end, under the cactus
CODE_SIZE = 14
CODE_OPACITY = 0.9
assert CUTOUT.font is not None  # the cutout style ships it: srstudio/assets/fonts/DejaVuSans-Bold.ttf
STYLE = replace(TOON, font=CUTOUT.font)  # Toon's cast and pills, in the bundled DejaVu Sans Bold
FONT = CUTOUT.font.src
Fits = Callable[[str], bool]  # whether a caption's text fits one pill
NARRATION = "Narration recorded in sreditor."


@dataclass(frozen=True)
class Take:
    """One take of ``timeline.json``: who says it, from when, for how long, its audio and its timed words."""

    id: str
    actor: str
    start: float
    duration: float
    audio: str
    words: tuple[tuple[str, float, float], ...]  # (text, start, end) from the take's start

    @property
    def end(self) -> float:
        return round(self.start + self.duration, 6)


def _fail(message: str, path: str, actual: object = None) -> ExportError:
    return ExportError(
        message,
        code="export.toon",
        path=path,
        actual=actual,
        remedy="Fix the episode in sreditor (its library sheets, short script beats and staging) and export again.",
    )


def _json(export: Path, name: str, default: Any) -> Any:
    file = export / name
    if not file.is_file():
        return default
    try:
        return json.loads(file.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise _fail(f"{name}: cannot read: {exc}", name) from exc


def is_toon(export: Path, episode: Mapping[str, Any]) -> bool:
    """Whether the export is built as a Toon sketch: the toon style, with beats to draw."""
    return episode.get("style") == TOON.slug and bool(_json(export, POSES, []))


def takes(timeline: Mapping[str, Any]) -> list[Take]:
    """The timeline's spoken takes, typed."""
    out = []
    for i, item in enumerate(timeline.get("items", [])):
        where = f"timeline.json items[{i}]"
        try:
            words = tuple((str(w["text"]), float(w["start"]), float(w["end"])) for w in item.get("words", []))
            audio = item["audio"]
            if not isinstance(audio, str):
                raise TypeError(f"audio is {audio!r}, not the path of the take's WAV")
            out.append(
                Take(str(item["id"]), str(item["actor"]), float(item["start"]), float(item["duration"]), audio, words)
            )
        except (KeyError, TypeError, ValueError) as exc:
            raise _fail(f"{where}: {exc}", where, item) from exc
        if not words:
            raise _fail(f"{where}: a take needs its timed words", where)
    return out


def cast_of(export: Path) -> tuple[dict[str, str], dict[str, int]]:
    """Which Toon character each actor plays, by the bible's ``look.drawing``, and the versions the bible pins."""
    played: dict[str, str] = {}
    versions: dict[str, int] = {}
    for entry in _json(export, CAST, {}).get("characters", []):
        look = entry.get("look")
        drawing = (look.get("drawing") if isinstance(look, dict) else None) or []
        part = drawing[0].get("part", "") if drawing and isinstance(drawing[0], dict) else ""
        who = part.removeprefix(TOON_PREFIX)
        if not part.startswith(TOON_PREFIX) or who not in sketch.CHARACTERS:
            continue
        played[str(entry.get("slug"))] = who
        version = drawing[0].get("version")
        if isinstance(version, int) and not isinstance(version, bool):
            versions[part] = version
    return played, versions


def pose_points(export: Path) -> list[tuple[float, str, dict[str, Any]]]:
    """Every pose of ``assets/poses.json`` at its project second: ``(second, who, pose)``."""
    out = []
    for i, app in enumerate(_json(export, POSES, [])):
        try:
            for pose in app["poses"]:
                at = round(float(app["start"]) + float(pose["start"]), 6)
                missing = [key for key in POSE_KEYS if not isinstance(pose.get(key), str)]
                if missing:
                    raise KeyError(f"a pose names its {', '.join(missing)}")
                out.append((at, str(app["who"]), {k: v for k, v in pose.items() if k != "start"}))
        except (KeyError, TypeError, ValueError) as exc:
            raise _fail(f"{POSES}[{i}]: {exc}", f"{POSES}[{i}]", app) from exc
    return sorted(out, key=lambda point: point[0])


def event_points(export: Path) -> list[tuple[float, str]]:
    """Every prop event of ``assets/events.json`` at its project second."""
    try:
        return sorted((round(float(e["start"]), 6), str(e["event"])) for e in _json(export, EVENTS, []))
    except (KeyError, TypeError, ValueError) as exc:
        raise _fail(f"{EVENTS}: {exc}", EVENTS) from exc


def pill_room(region: Box, width: float) -> float:
    """The widest pill centred on the frame that stays inside the safe area, where the engine measures text (SA01)."""
    centre = width / 2
    return 2 * min(centre - region.x0, region.x1 - centre)


@dataclass(frozen=True)
class Caption:
    """One caption of a take: the word it starts on, its text and the project second it appears."""

    word: int
    text: str
    at: float


def _placed(word_at: float, after: float | None) -> tuple[float, bool]:
    """When a caption on a word at ``word_at`` appears after one that appeared at ``after``: on its word, or later so
    the one before is read :data:`srstudio.sketch.CAPTION_MIN`, but never more than :data:`srstudio.sketch.CAPTION_LAG`
    after the word (``True`` then: the one before is cut short)."""
    if after is None:
        return word_at, False
    wanted = max(word_at, after + sketch.CAPTION_MIN)
    latest = word_at + sketch.CAPTION_LAG
    return round(max(min(wanted, latest), after + sketch.MIN_STEP), 6), wanted > latest + 1e-9


def captions(take: Take, fits: Fits, after: float | None, until: float) -> list[Caption]:
    """The take's words cut into captions that each fit one pill (a word too wide alone stands alone), each appearing on
    its word or up to :data:`srstudio.sketch.CAPTION_LAG` later so the one before is read
    :data:`srstudio.sketch.CAPTION_MIN` (as :func:`srstudio.sketch.place` times a recording); of those cuts, the one
    with the fewest captions read for less, the last one until ``until``, then the fewest captions. ``after`` is when
    the caption before the take appeared, if any."""
    words = [(text, round(take.start + a, 6)) for text, a, _ in take.words]
    n = len(words)
    # a partial cut of the first i words: (short, count) and its captions; the last caption's time is the state
    frontier: dict[float | None, tuple[tuple[int, int], list[Caption]]] = {after: ((0, 0), [])}
    states: list[dict[float | None, tuple[tuple[int, int], list[Caption]]]] = [frontier] + [{} for _ in range(n)]
    for i in range(n):
        for last, ((short, count), cut) in states[i].items():
            for j in range(i + 1, n + 1):
                text = " ".join(w[0] for w in words[i:j])
                if j > i + 1 and not fits(text):
                    break
                at, cut_short = _placed(words[i][1], last)
                key = (short + cut_short, count + 1)
                held = states[j].get(at)
                if held is None or key < held[0]:
                    states[j][at] = (key, [*cut, Caption(i, text, at)])

    def total(entry: tuple[tuple[int, int], list[Caption]]) -> tuple[int, int]:
        (short, count), cut = entry
        return (short + (until - cut[-1].at < sketch.CAPTION_MIN - 1e-9), count)

    return min(states[n].values(), key=total)[1]


@dataclass
class _Draft:
    start: float
    caption: str
    seen: float  # the latest pose change this beat shows
    line: int | None = None
    word: int | None = None
    event: str = ""


def _pose_at(points: Sequence[tuple[float, str, dict[str, Any]]], at: float) -> tuple[str, dict[str, Any]]:
    current = (points[0][1], points[0][2])
    for t, who, pose in points:
        if t > at + 1e-9:
            break
        current = (who, pose)
    return current


def _spoken(spoken: Sequence[Take], fits: Fits, end: float) -> list[_Draft]:
    """A beat on every caption, at the second it appears; the first, when it comes before MIN_STEP, at 0."""
    drafts: list[_Draft] = []
    after: float | None = None
    for n, take in enumerate(spoken):
        until = spoken[n + 1].start + spoken[n + 1].words[0][1] if n + 1 < len(spoken) else end
        for caption in captions(take, fits, after, until):
            at = 0.0 if not drafts and caption.at < sketch.MIN_STEP else caption.at
            drafts.append(_Draft(at, caption.text, at, n, caption.word))
            after = at
    if drafts[0].start > 0:
        drafts.insert(0, _Draft(0.0, "", 0.0))
    return drafts


def beats_of(
    spoken: Sequence[Take],
    poses: Sequence[tuple[float, str, dict[str, Any]]],
    events: Sequence[tuple[float, str]],
    fits: Fits,
    end: float,
) -> list[sketch.Beat]:
    """The sketch's beats: one on every caption (:func:`captions`), then a silent one on every change of pose or prop
    event between them. A change closer than :data:`srstudio.sketch.MIN_STEP` to a beat joins that beat, so the
    captions keep their seconds; a beat shows the pose of the latest change it holds."""
    drafts = _spoken(spoken, fits, end)
    marks = sorted([(t, "") for t, _, _ in poses] + list(events))
    for t, event in marks:
        t = min(t, end - sketch.MIN_STEP)
        near = min(drafts, key=lambda d: abs(d.start - t))
        if abs(near.start - t) < sketch.MIN_STEP - 1e-9:
            near.seen = max(near.seen, t)
            if event and near.event:
                apart = f"the events {near.event!r} and {event!r} are less than {sketch.MIN_STEP} s apart"
                raise _fail(f"{EVENTS}: {apart}", EVENTS, t)
            near.event = near.event or event
            continue
        on = [d for d in drafts if d.start <= t]
        drafts.append(_Draft(round(t, 6), on[-1].caption if on else "", t, event=event))
        drafts.sort(key=lambda d: d.start)
    return [_beat(d, *_pose_at(poses, d.seen)) for d in drafts]


def _beat(d: _Draft, who: str, pose: Mapping[str, Any]) -> sketch.Beat:
    wear = tuple(pose.get("wear", ()))
    return sketch.Beat(
        d.start, who, d.caption, pose["eyes"], pose["mouth"], pose["arms"], d.line, d.word, d.event, wear
    )


def alignment_of(take: Take) -> Alignment:
    """The take's letters timed from its words, each word's letters spread evenly over it, a space between words."""
    letters: list[str] = []
    starts: list[float] = []
    ends: list[float] = []
    for i, (text, a, b) in enumerate(take.words):
        if i:
            letters.append(" ")
            starts.append(starts[-1])
            ends.append(max(ends[-1], starts[-1]))
        step = (b - a) / max(len(text), 1)
        for k, letter in enumerate(text):
            letters.append(letter)
            starts.append(round(a + k * step, 6))
            ends.append(round(min(a + (k + 1) * step, take.duration), 6))
    return Alignment(tuple(letters), tuple(starts), tuple(ends))


def write_recording(root: Path, sk: sketch.Sketch, spoken: Sequence[Take], export: Path, language: str) -> None:
    """What a recording run leaves for the voiced build, made from the export: the takes' audio, the placed beats, the
    lips, the kept takes and ``narration.json``."""
    played = {s.name: s.character for s in sk.speakers}
    mouths: dict[str, list[tuple[float, str]]] = {
        who: [] for who in played.values() if who is not None and who in sk.cast.lip_synced
    }
    kept, items = [], []
    for n, take in enumerate(spoken):
        audio = Path("audio") / f"vo-{take.id}.wav"
        (root / audio).parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(export / take.audio, root / audio)
        who = played[take.actor]
        kept.append(sketch.kept_take(take.id, who, alignment_of(take), take.start, 0.0, take.duration))
        if who in mouths:
            sketch.extend_track(mouths[who], sketch.lips(kept[-1]), take.id)
        items.append(
            dict(
                id=take.id,
                text=sk.lines[n].text,
                phase="line",
                caption_start=take.start,
                start=take.start,
                duration=take.duration,
                speech_duration=take.words[-1][2],
                speed=1.0,
                lead=0.0,
                tempo=1.0,
                cut=False,
                audio=str(audio),
                sha256=sha256_of(root / audio),
            )
        )
    sketch.write_voiced(root, sk.beats, sk.end, sk.lines, mouths)
    sketch.write_speech(root, kept, sk.end)
    manifest = dict(
        title=sk.title, language=language, duration=sk.end, caption_duration=sk.end, items=items, effects=[]
    )
    (root / "narration.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")


def _drawing(kind: str, name: str, where: str) -> registry.Entry:
    try:
        return registry.get(kind, name)
    except registry.NotRegisteredError as exc:
        raise _fail(f"{where}: srstudio draws no {kind} named {name!r}", where, name) from exc


def _ms(seconds: float) -> int:
    """A second as whole milliseconds, for an id that says when a group starts."""
    return round(seconds * 1000)


def dresser(
    spoken: Sequence[Take], sets: Mapping[str, str], props: Mapping[str, str]
) -> Callable[[toon_sketch.Shot], None]:
    """The ``Staging.dress`` of an export: each take's set behind the character through the take, each prop in front
    of her from its event to the end of its take."""
    drawn_sets = {
        take.id: _drawing("location", sets[take.id], f"{STAGING} sets.{take.id}") for take in spoken if take.id in sets
    }
    drawn_props = {slug: _drawing("prop", rig, f"{STAGING} props.{slug}") for slug, rig in props.items()}

    def take_end(at: float) -> float:
        return next((take.end for take in spoken if take.start <= at < take.end), spoken[-1].end)

    def dress(shot: toon_sketch.Shot) -> None:
        cv, app = shot.cv, shot.app
        for take in spoken:
            a, b = max(take.start, app.start), min(take.end, app.end)
            if take.id in drawn_sets and a < b:
                drawn_sets[take.id](cv, cv.group(shot.back, f"set-{take.id}-{_ms(a)}", start=a, end=b))
        for beat in shot.beats:
            slug = beat.event.partition(":")[0]
            if not slug or not app.start <= beat.start < app.end:
                continue
            if slug not in drawn_props:
                raise _fail(f"{EVENTS}: no drawing for the prop {slug!r} in {STAGING}", f"{STAGING} props", slug)
            stop = min(take_end(beat.start), app.end)
            prop = drawn_props[slug]
            g = cv.group(shot.front, f"prop-{slug}-{_ms(beat.start)}", start=beat.start, end=stop)
            prop(cv, g, **{k: v for k, v in PROP_PLACE.items() if k in inspect.signature(prop.builder).parameters})

    return dress


def signed(cv, parent) -> None:
    """The desk of an export's shots: only the signature (ADR 0001), the cactus and its code low in the right corner,
    since the set is the room."""
    g = cv.group(parent, cv.uid("g"))
    cactus(cv, g, *CACTUS_AT, CACTUS_SCALE)
    code(cv, g, CODE_AT[0], CODE_AT[1], CODE_SIZE, opacity=CODE_OPACITY, align="end")


def _fits(measure: Callable[[str], float], limit: float, text: str) -> bool:
    return toon.pill_width(measure, text) <= limit


def toon_staging(
    export: Path, root: Path, episode: Mapping[str, Any], timeline: Mapping[str, Any]
) -> toon_sketch.Staging:
    """The export as a Toon sketch staged from its beats and sets, its recording files written under ``root``."""
    spoken = takes(timeline)
    played, versions = cast_of(export)
    poses = pose_points(export)
    for at, who, _ in poses:
        if who not in sketch.CHARACTERS:
            raise _fail(f"{POSES}: {who!r} at {at} s is not in the Toon cast", POSES, who)
    actors = list(dict.fromkeys(take.actor for take in spoken))
    speakers = tuple(sketch.Speaker(actor, Voice(actor, actor, actor), NO_VOICE, played.get(actor)) for actor in actors)
    font = (root / FONT).read_bytes()
    limit = pill_room(STYLE.safe_area.region(STYLE.width, STYLE.height), STYLE.width)
    measure = partial(fonts.text_width, font, size=toon.CAPTION_SIZE)
    lines = tuple(sketch.Line(take.actor, " ".join(w[0] for w in take.words)) for take in spoken)
    duration = float(timeline["duration"])
    fits = partial(_fits, measure, limit)
    beats = beats_of(spoken, poses, event_points(export), fits, duration)
    # the last frame is held until the last caption has been read its least, as a recorded sketch holds a tail
    read = max(b.start for b in beats if b.caption) + sketch.CAPTION_MIN
    end = round(max(duration, read, beats[-1].start + sketch.MIN_STEP), 6)
    sk = sketch.Sketch(str(episode["slug"]), str(episode["title"]), speakers, lines, tuple(beats), end)
    sketch.check(sk)
    write_recording(root, sk, spoken, export, str(episode.get("language") or "en"))
    staged = _json(export, STAGING, {})
    title = str(episode["title"])
    return toon_sketch.Staging(
        sketch=sk,
        seed=int(episode.get("seed", 0)),
        description=f"{title}, built from sreditor's export.",
        accessibility=f"{title}: a Toon sketch with its cast on the beats sreditor wrote.",
        narration=NARRATION,
        tints={},
        dress=dresser(spoken, staged.get("sets", {}), staged.get("props", {})),
        versions=versions,
        desk=signed,
        style=STYLE,
        bleed=True,
        held_frames=True,
    )


def build_toon(export: Path, stage: Path, episode: Mapping[str, Any], timeline: Mapping[str, Any]) -> Episode:
    """The voiced Toon episode of the export, drawn under ``stage`` and ready for :meth:`Episode.finish`."""
    staging = toon_staging(export, stage, episode, timeline)
    ep = toon_sketch.build(stage, staging, {"--voice"})
    assert ep is not None  # a voiced build always returns its episode
    return ep
