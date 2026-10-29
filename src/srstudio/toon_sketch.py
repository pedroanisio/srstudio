"""The Toon sketches' shared build: a :class:`srstudio.sketch.Sketch` plus a dressing of each shot becomes the
silent or the narrated episode, and the recording run writes its ``narration.json``.

ARCHITECTURAL REQUIREMENT: LLMs will always produce some form of error.
Absence of output verification is a design defect, not a runtime bug.
All LLM output must be treated as untrusted and validated explicitly.

A sketch cuts between its characters: every appearance (:func:`srstudio.sketch.appearances`) is one shot, a group
on screen from its entrance to its exit, holding its set and the props behind the character (``back``), the
character on its poses, the desk, and the props in front (``front``), which the episode's ``dress`` draws. The
narrated build reads the placed beats from ``voiced/beats.json`` (typed by :func:`srstudio.sketch.load_beats`
and checked again as a sketch), takes its duration and effects from ``narration.json`` (hashes and fields checked
by :mod:`srstudio.narration`) and refuses any mismatch between the two; the brush-drawn characters key their
mouths on the viseme tracks of ``voiced/mouths.json`` (typed by :func:`srstudio.sketch.load_mouths`, its end
checked against the beats). :func:`record_episode` is the
ElevenLabs run: :func:`srstudio.sketch.record` (one request per line, speech-to-text check, voices confirmed by
name), then the keyboard between the lines, a phone buzz on every ``toast`` event and the sting on ``hangup``,
all synthesised deterministically by :mod:`srstudio.foley`.
"""

from __future__ import annotations

import json
import os
import sys
from collections.abc import Callable, Iterable, Mapping, Sequence
from dataclasses import dataclass, field, replace
from functools import partial
from pathlib import Path

from sr_core.scene import Project

from . import (
    TOON,
    Episode,
    EpisodeSpec,
    errors,
    foley,
    fonts,
    recording,
    sketch,
    soundtrack,
    subtitles,
    toon,
    toon_props,
)
from .canvas import Canvas
from .narration import effect_cues, manifest_duration, require_consent
from .provider import KEY_ENV
from .staging import StagingError
from .voice import MODEL, ElevenLabsClient

TYPING_PEAK = 0.70
TYPING_GAIN_DB = -2.0  # the keys only play between the lines
BUZZ_GAIN_DB = -4.0
STING_GAIN_DB = -5.0
BADGE_SIZE = 28
CALL_ENDED = "Call ended"
BUILD_FLAGS = ("--init", "--voice")  # write the project files; build from the recording
PILL_MARGIN = 40  # frame pixels kept free at each side of the widest caption pill


@dataclass(frozen=True)
class Shot:
    """One appearance on screen: draw its set and the props behind the character into ``back``, the props in
    front of the desk into ``front``."""

    cv: Canvas
    app: sketch.Appearance
    back: object
    front: object
    beats: Sequence[sketch.Beat]
    end: float
    measure: Callable[..., float]  # the advance width of a text at a size, in the style's font

    def badges(self, texts: Mapping[str, str], ended: str = CALL_ENDED, event: str = "hangup") -> None:
        for a, b, text in badge_spans(self.beats, self.app, texts, ended, event):
            toon_props.badge(self.cv, self.front, text, a, b, partial(self.measure, size=BADGE_SIZE), BADGE_SIZE)


@dataclass(frozen=True)
class Staging:
    """What an episode adds to its sketch: how each shot is dressed, the pill tints per speaker, the stickers on
    a character, its words for the metadata and what stands in front of the character (the office desk unless a
    dinner, say, lays a table instead)."""

    sketch: sketch.Sketch
    seed: int
    description: str
    accessibility: str
    narration: str
    tints: Mapping[str, str]
    dress: Callable[[Shot], None]
    stickers: Mapping[str, Sequence[tuple]] = field(default_factory=dict)
    desk: Callable[[Canvas, object], None] = toon.desk


def badge_spans(
    beats: Sequence[sketch.Beat], app: sketch.Appearance, texts: Mapping[str, str], ended: str, event: str
) -> list[tuple[float, float, str]]:
    """What the call badge says through one appearance: ``texts[who]`` (nothing when absent) until the ``event``
    beat, ``ended`` from then on."""
    hang = next((t for t, _ in sketch.events(beats, event)), None)
    base = texts.get(app.who)
    if hang is None or hang >= app.end:
        return [(app.start, app.end, base)] if base else []
    if hang <= app.start:
        return [(app.start, app.end, ended)]
    return ([(app.start, hang, base)] if base else []) + [(hang, app.end, ended)]


def fit_captions(lines: Sequence[toon.Line], measure: Callable[[str], float], width: float) -> None:
    """Every caption pill fits the frame with :data:`PILL_MARGIN` to spare; a long line goes in two beats."""
    wide = [q.text for q in lines if toon.pill_width(measure, q.text) > width - 2 * PILL_MARGIN]
    if wide:
        raise StagingError("captions too wide for one pill: " + "; ".join(repr(t) for t in wide))


def build(root: Path, staging: Staging, flags: Iterable[str]) -> Episode:
    """The episode, drawn and ready for its post and :meth:`Episode.finish`; ``--init`` writes the project files
    and exits, ``--voice`` builds from the recording."""
    root = Path(root)
    flags = errors.flags(flags, BUILD_FLAGS)
    sk = staging.sketch
    if "--init" in flags:
        sketch.write_project(root, sk, TOON.google_font())
        sys.exit(0)
    voiced = "--voice" in flags
    mouths: sketch.Mouths = {}
    if voiced:
        beats, end = sketch.load_beats(root / "voiced" / "beats.json")
        sk = replace(sk, beats=tuple(beats), end=end)
        mouths, mouths_end = sketch.load_mouths(root / "voiced" / "mouths.json")
        if mouths_end != end:
            raise StagingError(f"voiced/mouths.json runs {mouths_end} s, voiced/beats.json {end} s: record again")
    sketch.check(sk)
    ep = Episode(
        EpisodeSpec(
            slug=sk.slug,
            title=sk.title,
            description=staging.description + " " + (staging.narration if voiced else "Silent master."),
            root=root,
            seed=staging.seed,
            style=TOON,
            dialogue="voiced/script.json" if voiced else "script.json",
            language="en-US",
            output_options=dict(
                codec="h264",
                container="mp4",
                fps="24",
                crf="17",
                preset="medium",
                pixelFormat="yuv420p",
                faststart=True,
                report="qa/render-report.json",
                **(dict(audioCodec="aac", audioBitrate="192000") if voiced else {}),
            ),
            accessibility=dict(
                description=staging.accessibility
                + " "
                + (f"{staging.narration} Text transcript bundled." if voiced else "Silent master; transcript bundled.")
            ),
        )
    )
    cv, t = ep.cv, ep.t
    if t.duration > sk.end or t.phrases[0].start != 0:
        raise StagingError(f"{ep.spec.dialogue} runs to {t.duration} s, the sketch to {sk.end} s: run --init again")
    project = ep.scene.find("project")
    if not isinstance(project, Project):  # pragma: no cover - an Episode always writes its project
        raise StagingError(f"{ep.spec.dialogue}: the scene has no <project>")
    project.duration = sk.end  # the last beats may be silent and uncaptioned
    taps: tuple[float, ...] = ()
    effects = []
    manifest = root / "narration.json"
    if voiced:
        if manifest_duration(manifest) != sk.end:
            raise StagingError(f"narration.json runs {manifest_duration(manifest)} s, voiced/beats.json {sk.end} s")
        effects = effect_cues(manifest, root)
        taps = tuple(at for fx in effects if fx.id == "typing" for at in fx.taps)
    if TOON.font is None:  # pragma: no cover - a property of the style, tested there
        raise StagingError("the Toon style has no font to measure its captions in")
    font = (root / TOON.font.src).read_bytes()
    measure = partial(fonts.text_width, font)
    for app in sketch.appearances(sk.beats, sk.end):
        g = cv.group(ep.comp, cv.uid("g"), start=app.start, end=app.end)
        back = cv.group(g, cv.uid("g"))
        poses = toon.parse_poses(app.poses, f"poses of {app.who} from {app.start} s")
        extra = sketch.drawer_extras(app.who, staging.stickers, mouths)
        sketch.DRAWERS[app.who](cv, g, poses, app.end, taps, enter=app.start, **extra)
        staging.desk(cv, g)
        front = cv.group(g, cv.uid("g"))
        staging.dress(Shot(cv, app, back, front, sk.beats, sk.end, measure))
    lines = toon.load_script(root / ep.spec.dialogue)
    fit_captions(lines, partial(measure, size=toon.CAPTION_SIZE), cv.width)
    toon.captions(cv, ep.comp, lines, partial(measure, size=toon.CAPTION_SIZE), tints=staging.tints)
    if voiced:
        ep.audio(narration=manifest)
        for fx in effects:
            cv.assets.add_audio(id=f"fx-{fx.id}", src=fx.audio, sha256=fx.sha256)
            ep.add_track(f"fx-track-{fx.id}", f"fx-{fx.id}", start=fx.start, role="effects", gain=fx.gain_db)
    subtitles.write_srt(root / f"{sk.slug}.srt", [(p.start, p.end, p.caption) for p in t.phrases])
    return ep


# -- the recording run ------------------------------------------------------------------------------------------------
def sound_effects(
    beats: Sequence[sketch.Beat], end: float, speech: Sequence[tuple[float, float]], root: Path, seed: int
) -> list[dict]:
    """The manifest's effects: the keyboard in the typing beats between the lines (its taps swap the frames), a
    buzz under every ``toast`` event and the sting on ``hangup``."""
    audio = Path(root) / "audio"
    audio.mkdir(parents=True, exist_ok=True)
    taps = foley.taps(sketch.typing_bursts(beats, end, speech), seed=seed, until=end - foley.KEY_TAIL)
    typing = foley.write_typing(audio / "typing.wav", taps, end, seed=seed, peak=TYPING_PEAK)
    out = [sketch.effect("typing", 0.0, TYPING_GAIN_DB, root, typing, taps)]
    buzzes = [at for at, _ in sketch.events(beats, "toast")]
    if buzzes:
        buzz = foley.write_buzz(audio / "buzz.wav", buzzes, end, seed=seed)
        out.append(sketch.effect("buzz", 0.0, BUZZ_GAIN_DB, root, buzz))
    stings = [at for at, _ in sketch.events(beats, "hangup")]
    if stings:
        sting = foley.write_tones(audio / "sting.wav", stings, end)
        out.append(sketch.effect("sting", 0.0, STING_GAIN_DB, root, sting))
    return out


def record_episode(
    sk: sketch.Sketch,
    root: Path,
    env: Mapping[str, str],
    ffmpeg: str,
    seed: int,
    note: str,
    mouth: soundtrack.PhonemeStyle = sketch.MOUTH_STYLE,
) -> dict:
    """Record the sketch under ``root`` (only with ``SRSTUDIO_ALLOW_CLOUD=1``; the key from the environment, never
    written), synthesise its effects and write ``narration.json``; returns the manifest. ``mouth`` reads the takes'
    letters into the characters' viseme tracks (``voiced/mouths.json``)."""
    os.umask(0o077)  # generated outputs are private: folders 700, files 600
    require_consent(env)
    root = Path(root)
    key = env.get(KEY_ENV, "")
    client = ElevenLabsClient(root / "assets" / "elevenlabs", key, model=MODEL, seed=seed)
    rec = sketch.record(sk, root, client, key=key, ffmpeg=ffmpeg, mouth=mouth)
    effects = sound_effects(rec.beats, rec.end, rec.speech, root, seed)
    manifest = sketch.manifest(sk, rec, effects, MODEL, note)
    (root / "narration.json").write_text(json.dumps(manifest, indent=2) + "\n")
    for q in rec.items:
        flags = " ".join(f for f, on in (("cut", q["cut"]), ("lag", q["lag"] > 0)) if on)
        print(f"{q['id']} {q['duration']:5.2f}s {flags:8} {q['text']}")
    print(f"{len(rec.items)} lines, {len(effects)} effects, the project runs {rec.end:.3f} s")
    return manifest


def recorder(
    sk: sketch.Sketch,
    seed: int,
    note: str,
    doc: str | None,
    mouth: soundtrack.PhonemeStyle = sketch.MOUTH_STYLE,
    validate: Callable[[sketch.Sketch], object] | None = None,
) -> Callable[..., int]:
    """The ``main`` of an episode's recording script: :func:`srstudio.recording.main` around :func:`record_episode`
    (``python3 <episode>_audio.py PROJECT [--ffmpeg PATH]``, the help from ``doc``); ``validate`` checks the sketch
    once the arguments are parsed, before anything is recorded."""

    def record(project: Path, env: Mapping[str, str], ffmpeg: str) -> dict:
        if validate is not None:
            validate(sk)
        return record_episode(sk, project, env, ffmpeg, seed, note, mouth=mouth)

    def main(argv: Sequence[str] | None = None, env: Mapping[str, str] | None = None) -> int:
        return recording.main(record, doc, argv, env)

    return main
