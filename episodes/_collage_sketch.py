"""The Collage sketches' shared build (ADR 0026): a :class:`srstudio.sketch.Sketch` on the Collage cast, one shot
per appearance on its character's set, crash zooms on ``zoom`` beats, and the recording run.

ARCHITECTURAL REQUIREMENT: LLMs will always produce some form of error.
Absence of output verification is a design defect, not a runtime bug.
All LLM output must be treated as untrusted and validated explicitly.

Every appearance (:func:`srstudio.sketch.appearances`) is one shot: the set its character stands in
(``Staging.sets``, a :data:`srstudio.collage_sets.SETS` name), the props the episode's ``dress`` puts behind it, the
paper character on its poses (:data:`srstudio.collage.DRAWERS`), and the props in front. A ``zoom`` beat snaps the
shot in on the character's face (:func:`srstudio.camera.crash_zoom`) and holds until the cut; a ``sting`` beat
plays the sagging two-note sting, a ``beep`` beat Kai's headset. The narrated build reads the placed beats from
``voiced/beats.json`` and the viseme tracks from ``voiced/mouths.json`` (both typed by :mod:`srstudio.sketch`
against :data:`srstudio.collage.CAST`), and refuses a recording that does not agree with ``narration.json``.
:func:`record_episode` is the ElevenLabs run: :func:`srstudio.sketch.record` (one request per line, speech-to-text
check, voices confirmed by name, nothing retried), then the effects synthesised by :mod:`srstudio.foley`.
"""

from __future__ import annotations

import json
import os
import sys
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass, replace
from functools import partial
from pathlib import Path

from srstudio import (
    COLLAGE,
    Episode,
    EpisodeSpec,
    camera,
    collage,
    collage_sets,
    foley,
    fonts,
    sketch,
    soundtrack,
    subtitles,
    toon,
)
from srstudio.canvas import Canvas
from srstudio.narration import effect_cues, manifest_duration, require_consent
from srstudio.provider import KEY_ENV
from srstudio.voice import MODEL, ElevenLabsClient, Voice, VoiceSettings

GRAIN = {"intensity": 0.22, "size": 1.4}
EVENTS = ("zoom", "sting", "beep", "reveal")  # reveal: no sound; a prop shows from it (see until)
ZOOM_SCALE = 1.55
ZOOM_SNAP = 0.15  # seconds the crash zoom takes to land
WHOOSH_GAIN_DB = -6.0
STING_GAIN_DB = -5.0
BEEP_GAIN_DB = -9.0
BEEP = ((1568.0, 1568.0, 0.09), (2093.0, 2093.0, 0.11))  # Kai's headset: two short high notes


def say(
    lines: Sequence[sketch.Line], start: float, who: str, line: int, eyes: str, mouth: str, arms: str, event: str = ""
) -> sketch.Beat:
    """The beat that starts line ``line``, captioned with all of it, ``who`` on screen."""
    return sketch.Beat(start, who, lines[line].text, eyes, mouth, arms, line, 0, event)


def hold(start: float, who: str, caption: str, eyes: str, mouth: str, arms: str, event: str = "") -> sketch.Beat:
    """A silent beat: ``who`` reacts, the caption stays (or goes, with ``""``)."""
    return sketch.Beat(start, who, caption, eyes, mouth, arms, None, None, event)


def _speaker(name: str, voice_id: str, voice: str, stability: float, style: float) -> sketch.Speaker:
    return sketch.Speaker(name, Voice(role=name, id=voice_id, name=voice), VoiceSettings(stability, 0.75, style), name)


# one ElevenLabs premade voice per character, the same in every episode (confirmed by name before recording)
SPEAKERS = {
    s.name: s
    for s in (
        _speaker("brent", "nPczCjzI2devNBz1zQrb", "Brian", 0.45, 0.45),
        _speaker("rosa", "XrExE9yKIg1WjnnlVkGX", "Matilda", 0.55, 0.30),
        _speaker("gary", "iP95p4xoKVk53GoZ742B", "Chris", 0.35, 0.55),
        _speaker("kai", "SAz9YHcvj6GT2YYXdXww", "River", 0.45, 0.40),
        _speaker("priya", "EXAVITQu4vr4xnSDxMaL", "Sarah", 0.50, 0.35),
        _speaker("deb", "cgSgspJ2msm6clMCkdW9", "Jessica", 0.45, 0.45),
        _speaker("jun", "bIHbv24MWmeRgasZH58o", "Will", 0.40, 0.45),
        _speaker("feld", "Xb7hH8MSUJpSbSDYk0k2", "Alice", 0.60, 0.25),
        _speaker("omar", "onwK4e9ZLuTAKqWW03F9", "Daniel", 0.50, 0.40),
        _speaker("flush", "IKne3meq5aSn9XLyUdCD", "Charlie", 0.30, 0.65),
    )
}
TINTS = {
    "brent": "#cfe1ff",
    "rosa": "#f7c6d9",
    "gary": "#d8f3c4",
    "kai": "#ffd6c9",
    "priya": "#c9f0f0",
    "deb": "#ffe5b4",
    "jun": "#e0d4ff",
    "feld": "#efe3f7",
    "omar": "#d0e4f5",
    "flush": "#fff7a8",
}


def make_sketch(slug: str, title: str, names: Sequence[str], lines, beats, end: float) -> sketch.Sketch:
    """A sketch on the Collage cast with the shared voices of ``names``."""
    return sketch.Sketch(
        slug, title, tuple(SPEAKERS[n] for n in names), tuple(lines), tuple(beats), end, cast=collage.CAST
    )


def voices_note(names: Sequence[str]) -> str:
    """``Brian (Brent) and Matilda (Rosa)``: the premade voices of an episode, for its words."""
    parts = [f"{SPEAKERS[n].voice.name} ({'Dr. Feld' if n == 'feld' else n.title()})" for n in names]
    return ", ".join(parts[:-1]) + " and " + parts[-1] if len(parts) > 1 else parts[0]


# the Toon's viseme reading with English spelling, every b/m/p closed, a one-frame lead (srstudio.lipsync, ADR 0019)
MOUTH = replace(sketch.MOUTH_STYLE, spelling=True, close_bilabials=True, lead=0.04, min_rest=0.12)


def timed(lines: Sequence[sketch.Line], rows: Sequence[tuple], tail: float = 1.2) -> tuple[list[sketch.Beat], float]:
    """Beats on the scripted clock from rows ``(seconds held, who, line or caption, eyes, mouth, arms[, event])``:
    an ``int`` starts that line, a ``str`` is a silent beat with that caption (``""`` for none). Returns the beats
    and the end, ``tail`` after the last one starts."""
    beats, at = [], 0.0
    for held, who, what, eyes, mouth, arms, *event in rows:
        ev = event[0] if event else ""
        beats.append(
            say(lines, at, who, what, eyes, mouth, arms, ev)
            if isinstance(what, int)
            else hold(at, who, what, eyes, mouth, arms, ev)
        )
        at = round(at + held, 6)
    return beats, round(beats[-1].start + tail, 6)


def until(beats: Sequence[sketch.Beat], event: str, app: sketch.Appearance, before: bool) -> list[tuple[float, float]]:
    """The span of a shot before (or from) the first ``event`` beat: when a prop shows."""
    at = next((t for t, _ in sketch.events(beats, event)), None)
    if at is None:
        return [(app.start, app.end)] if before else []
    a, b = (app.start, min(at, app.end)) if before else (max(at, app.start), app.end)
    return [(a, b)] if b > a else []


class StagingError(ValueError):
    """The episode's files do not agree with its sketch."""


@dataclass(frozen=True)
class Shot:
    """One appearance on screen: draw the props behind the character into ``back``, those in front into ``front``."""

    cv: Canvas
    app: sketch.Appearance
    back: object
    front: object
    beats: Sequence[sketch.Beat]
    end: float
    measure: Callable[[str, float], float]  # the advance width of a text at a size, in the style's font


@dataclass(frozen=True)
class Staging:
    """What an episode adds to its sketch: the set of each character, the props per shot, the pill tints."""

    sketch: sketch.Sketch
    seed: int
    description: str
    accessibility: str
    narration: str
    tints: Mapping[str, str]
    sets: Mapping[str, str]
    dress: Callable[[Shot], None] = lambda shot: None


def check_staging(staging: Staging) -> None:
    """The sketch is on the Collage cast, every character on screen has a known set, and its events are known."""
    sk = staging.sketch
    if sk.cast is not collage.CAST:
        raise StagingError(f"{sk.slug} is not cast from the Collage cast")
    sketch.check(sk)
    missing = sorted({b.who for b in sk.beats} - set(staging.sets))
    unknown = sorted(set(staging.sets.values()) - set(collage_sets.SETS))
    if missing or unknown:
        raise StagingError(f"{sk.slug}: no set for {missing}; unknown sets {unknown}")
    odd = sorted({b.event.split(":")[0] for b in sk.beats if b.event} - set(EVENTS))
    if odd:
        raise StagingError(f"{sk.slug}: unknown events {odd}; one of {EVENTS}")


def zooms(beats: Sequence[sketch.Beat], app: sketch.Appearance) -> list[float]:
    """The ``zoom`` cues inside one appearance; a shot snaps in once, on its first."""
    return [t for t, _ in sketch.events(beats, "zoom") if app.start <= t < app.end][:1]


def build(root: Path, staging: Staging, flags: set[str]) -> Episode:
    """The episode, drawn and ready for its post and :meth:`Episode.finish`; ``--init`` writes the project files
    and exits, ``--voice`` builds from the recording."""
    root = Path(root)
    check_staging(staging)
    sk = staging.sketch
    if "--init" in flags:
        sketch.write_project(root, sk, COLLAGE.font.google)
        sys.exit(0)
    voiced = "--voice" in flags
    mouths: sketch.Mouths = {}
    if voiced:
        beats, end = sketch.load_beats(root / "voiced" / "beats.json")
        sk = replace(sk, beats=tuple(beats), end=end)
        mouths, mouths_end = sketch.load_mouths(root / "voiced" / "mouths.json", collage.CAST)
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
            style=COLLAGE,
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
    ep.scene.find("project").duration = sk.end  # the last beats may be silent and uncaptioned
    effects = []
    manifest = root / "narration.json"
    if voiced:
        if manifest_duration(manifest) != sk.end:
            raise StagingError(f"narration.json runs {manifest_duration(manifest)} s, voiced/beats.json {sk.end} s")
        effects = effect_cues(manifest, root)
    font = (root / COLLAGE.font.src).read_bytes()
    measure = partial(fonts.text_width, font)
    for app in sketch.appearances(sk.beats, sk.end):
        g = cv.group(ep.comp, cv.uid("g"), start=app.start, end=app.end)
        cv.apply(g, cv.effect("collage-grain", "film-grain", **GRAIN))  # the paper's tooth, over set and cast
        collage_sets.SETS[staging.sets[app.who]](cv, g)
        back = cv.group(g, cv.uid("g"))
        poses = collage.parse_poses(app.poses, f"poses of {app.who} from {app.start} s")
        collage.DRAWERS[app.who](cv, g, poses, app.end, (), enter=app.start, mouths=mouths.get(app.who, ()))
        front = cv.group(g, cv.uid("g"))
        staging.dress(Shot(cv, app, back, front, sk.beats, sk.end, measure))
        for at in zooms(sk.beats, app):
            camera.anchor(g, *collage.face(collage.LOOKS[app.who]), place=True)
            camera.crash_zoom(cv, g, at, ZOOM_SCALE, duration=ZOOM_SNAP)
    lines = toon.load_script(root / ep.spec.dialogue)
    collage.captions(cv, ep.comp, lines, partial(measure, size=collage.CAPTION_SIZE), tints=staging.tints)
    if voiced:
        ep.audio(narration=manifest)
        for fx in effects:
            cv.assets.add_audio(id=f"fx-{fx.id}", src=fx.audio, sha256=fx.sha256)
            ep.add_track(f"fx-track-{fx.id}", f"fx-{fx.id}", start=fx.start, role="effects", gain=fx.gain_db)
    subtitles.write_srt(root / f"{sk.slug}.srt", [(p.start, p.end, p.caption) for p in t.phrases])
    return ep


# -- the recording run ------------------------------------------------------------------------------------------------
def sound_effects(beats: Sequence[sketch.Beat], end: float, root: Path, seed: int) -> list[dict]:
    """The manifest's effects: a whoosh into every ``zoom``, the sting on ``sting``, the headset on ``beep``."""
    audio = Path(root) / "audio"
    audio.mkdir(parents=True, exist_ok=True)
    out = []
    whooshes = [at for at, _ in sketch.events(beats, "zoom")]
    if whooshes:
        # the whoosh swells into the moment the zoom lands
        cues = [max(0.0, round(at + ZOOM_SNAP - foley.WHOOSH, 6)) for at in whooshes]
        whoosh = foley.write_whoosh(audio / "whoosh.wav", cues, end, seed=seed)
        out.append(sketch.effect("whoosh", 0.0, WHOOSH_GAIN_DB, root, whoosh))
    stings = [at for at, _ in sketch.events(beats, "sting")]
    if stings:
        sting = foley.write_tones(audio / "sting.wav", stings, end)
        out.append(sketch.effect("sting", 0.0, STING_GAIN_DB, root, sting))
    beeps = [at for at, _ in sketch.events(beats, "beep")]
    if beeps:
        beep = foley.write_tones(audio / "beep.wav", beeps, end, notes=BEEP)
        out.append(sketch.effect("beep", 0.0, BEEP_GAIN_DB, root, beep))
    return out


def record_episode(
    staging: Staging,
    root: Path,
    env: Mapping[str, str],
    ffmpeg: str,
    note: str,
    mouth: soundtrack.PhonemeStyle = sketch.MOUTH_STYLE,
) -> dict:
    """Record the sketch under ``root`` (only with ``SRSTUDIO_ALLOW_CLOUD=1``; the key from the environment, never
    written), synthesise its effects and write ``narration.json``; returns the manifest."""
    os.umask(0o077)  # generated outputs are private: folders 700, files 600
    check_staging(staging)
    require_consent(env)
    root = Path(root)
    sk = staging.sketch
    key = env.get(KEY_ENV, "")
    client = ElevenLabsClient(root / "assets" / "elevenlabs", key, model=MODEL, seed=staging.seed)
    rec = sketch.record(sk, root, client, key=key, ffmpeg=ffmpeg, mouth=mouth)
    effects = sound_effects(rec.beats, rec.end, root, staging.seed)
    manifest = sketch.manifest(sk, rec, effects, MODEL, note)
    (root / "narration.json").write_text(json.dumps(manifest, indent=2) + "\n")
    for q in rec.items:
        flags = " ".join(f for f, on in (("cut", q["cut"]), ("lag", q["lag"] > 0)) if on)
        print(f"{q['id']} {q['duration']:5.2f}s {flags:8} {q['text']}")
    print(f"{len(rec.items)} lines, {len(effects)} effects, the project runs {rec.end:.3f} s")
    return manifest
