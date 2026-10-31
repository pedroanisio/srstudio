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
from collections.abc import Callable, Iterable, Mapping, Sequence
from dataclasses import dataclass, replace
from functools import partial
from pathlib import Path

from sr_core.scene import Project

from . import (
    COLLAGE,
    Episode,
    EpisodeSpec,
    camera,
    checks,
    collage,
    collage_sets,
    errors,
    foley,
    fonts,
    recording,
    sketch,
    soundtrack,
    subtitles,
    toon,
)
from .canvas import Canvas
from .narration import effect_cues, manifest_duration, require_consent
from .provider import KEY_ENV
from .scripting import hold, part, say
from .sketch import Appearance, Beat
from .staging import StagingError
from .voice import MODEL, ElevenLabsClient, Voice, VoiceSettings

BUILD_FLAGS = ("--init", "--voice")  # write the project files; build from the recording
GRAIN = {"intensity": 0.22, "size": 1.4}
# reveal and timer: no sound, a prop shows from them (see until); flash: the camera's shutter; swat, ding, crunch and
# thud (a door shutting, something heavy landing) play on their beat; hiss:<seconds> lets the air out of something for
# that long
EVENTS = ("zoom", "sting", "beep", "reveal", "timer", "flash", "swat", "ding", "crunch", "hiss", "thud")
ZOOM_SCALE = 1.55
ZOOM_SNAP = 0.15  # seconds the crash zoom takes to land
WHOOSH_GAIN_DB = -6.0
STING_GAIN_DB = -5.0
BEEP_GAIN_DB = -9.0
SHUTTER = (0.0, 0.085)  # a shutter: the mirror up, then down, as two clicks
SHUTTER_GAIN_DB = -4.0
BEEP = ((1568.0, 1568.0, 0.09), (2093.0, 2093.0, 0.11))  # Kai's headset: two short high notes
SWAT_GAIN_DB = -7.0
SWAT = 0.12  # seconds of a swat's whoosh: it lands on its beat
DING_GAIN_DB = -8.0
HISS_GAIN_DB = -9.0
CRUNCH_GAIN_DB = -6.0
THUD_GAIN_DB = -4.0
CRUNCH = (0.0, 0.016, 0.034, 0.21, 0.226, 0.25, 0.42, 0.436, 0.45)  # three bites, each a few quick clicks


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
    an ``int`` starts that line, a ``(line, word, caption)`` is a beat on that word of it, a ``str`` is a silent beat
    with that caption (``""`` for none). Returns the beats and the end, ``tail`` after the last one starts."""
    beats, at = [], 0.0
    for held, who, what, eyes, mouth, arms, *event in rows:
        ev = event[0] if event else ""
        if isinstance(what, tuple):
            line, word, caption = what
            beats.append(part(lines, at, who, line, word, caption, eyes, mouth, arms, ev))
        elif isinstance(what, int):
            beats.append(say(lines, at, who, what, eyes, mouth, arms, ev))
        else:
            beats.append(hold(at, who, what, eyes, mouth, arms, ev))
        at = round(at + held, 6)
    return beats, round(beats[-1].start + tail, 6)


def until(beats: Sequence[sketch.Beat], event: str, app: sketch.Appearance, before: bool) -> list[tuple[float, float]]:
    """The span of a shot before (or from) the first ``event`` beat: when a prop shows."""
    at = next((t for t, _ in sketch.events(beats, event)), None)
    if at is None:
        return [(app.start, app.end)] if before else []
    a, b = (app.start, min(at, app.end)) if before else (max(at, app.start), app.end)
    return [(a, b)] if b > a else []


@dataclass(frozen=True)
class Shot:
    """One appearance on screen: draw the props behind the character into ``back``, those in front into ``front``."""

    cv: Canvas
    app: sketch.Appearance
    back: object
    front: object
    beats: Sequence[sketch.Beat]
    end: float
    measure: Callable[..., float]  # the advance width of a text at a size, in the style's font


def solo(cv: Canvas, parent, app: sketch.Appearance, mouths: sketch.Mouths) -> collage.Point:
    """The default cast of a shot: the appearance's character alone, on its poses; returns its face, the pivot of a
    zoom onto it."""
    poses = collage.parse_poses(app.poses, f"poses of {app.who} from {app.start} s")
    collage.DRAWERS[app.who](cv, parent, poses, app.end, (), enter=app.start, mouths=mouths.get(app.who, ()))
    return collage.face(collage.LOOKS[app.who])


CastDrawer = Callable[[Canvas, object, sketch.Appearance, sketch.Mouths], collage.Point]
Casting = Callable[[Sequence[sketch.Beat], float], CastDrawer]


def stilled(cv: Canvas, parent, app: sketch.Appearance, mouths: sketch.Mouths) -> collage.Point:
    """The cast of a still opening: the appearance's character alone in its first pose, keying nothing (no breath,
    blink or lip sync, :func:`srstudio.collage.figure`'s ``still``); returns its face."""
    poses = collage.parse_poses(app.poses, f"poses of {app.who} from {app.start} s")
    collage.DRAWERS[app.who](cv, parent, poses[:1], app.end, (), enter=app.start, still=True)
    return collage.face(collage.LOOKS[app.who])


def alone(beats: Sequence[sketch.Beat], end: float) -> CastDrawer:
    """The default casting: every shot is the speaker alone (:func:`solo`), whatever the beats."""
    return solo


@dataclass(frozen=True)
class Sound:
    """A sound a sketch adds to its events: ``sound`` at every ``at`` project second, on the track ``id``, at
    ``gain_db``."""

    id: str
    sound: foley.Burst
    at: tuple[float, ...]
    gain_db: float = -4.0


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
    # who is drawn in each shot, made from the beats the build draws (scripted or voiced), whose times differ;
    # a srstudio.collage_group.Lineup made from them puts several on one set
    cast: Casting = alone
    # the seconds the first shot holds still (the sp-hook_motion test's arm a, ADR 0036): that shot draws no grain,
    # and ``opening`` draws its cast keying nothing; 0 opens like any other shot
    still: float = 0.0
    opening: CastDrawer = stilled
    # the scale the first shot pushes in to across its length, for a reel that opens on a silent beat and on movement
    # (arm b, on a recording that kept its silent head); 0 leaves the shot where it stands
    push: float = 0.0
    # the set of a shot, from the beats the build draws and its appearance, for a reel that changes rooms; a name of
    # collage_sets.SETS. None keeps every character on its ``sets`` entry
    setting: Callable[[Sequence[Beat], Appearance], str] | None = None
    # the master's average video bits per second, encoded in two passes: 0, the rate factor alone, for every published
    # reel; a bitrate bounds a master's size by its length (the grain, new every frame, is what costs the bits), and
    # the first pass lets the encoder spend little on a still opening without blurring it
    bitrate: int = 0
    # a zoom pivots where collage_sets.zoom_pivot keeps the shelf, cactus and code, in frame and above the caption
    # pill, not on the face itself; off for every published reel, whose zooms are frozen where they landed
    keep_signature: bool = False
    # the sketch's own sounds, from the placed beats; each is a foley.Burst at its project seconds on its own track
    sounds: Callable[[Sequence[Beat], float], Sequence[Sound]] = lambda beats, end: ()

    def set_of(self, beats: Sequence[Beat], app: Appearance) -> str:
        """The set this appearance plays on."""
        return self.sets[app.who] if self.setting is None else self.setting(beats, app)


def check_push(beats: Sequence[sketch.Beat], staging: Staging, name: str) -> None:
    """A pushed opening moves, so it is not a still one, grows the shot so no edge shows, and leaves the first shot
    to no crash zoom, which would take the same keys."""
    push, still = staging.push, staging.still
    if push == 0:
        return
    if not (checks.number(push) and push > 1):
        raise StagingError(f"{name}: push {push!r} must grow the shot, above 1")
    if still:
        raise StagingError(f"{name}: an opening holds still or pushes in, not both")
    first = sketch.appearances(beats, beats[-1].start + 1.0)[0]
    if any(at < first.end for at, _ in sketch.events(beats, "zoom")):
        raise StagingError(f"{name}: a crash zoom in the first shot would take the keys of its push")


def check_still(beats: Sequence[sketch.Beat], still: float, name: str) -> None:
    """A still opening is one silent shot that lasts at least ``still`` seconds and ends on a cut: its first beat
    has no line, caption or event, and the next beat, on another character, starts no earlier than ``still``."""
    if not (checks.number(still) and still >= 0):
        raise StagingError(f"{name}: still {still!r} must be a non-negative number of seconds")
    if still == 0:
        return
    first = beats[0]
    if first.line is not None or first.caption or first.event:
        raise StagingError(f"{name}: a still opening is a silent beat, without a caption or an event")
    if len(beats) < 2 or beats[1].who == first.who:
        raise StagingError(f"{name}: a still opening ends on a cut to another character")
    if beats[1].start < still:
        raise StagingError(f"{name}: the opening holds still {still} s, but its next beat starts at {beats[1].start} s")


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
    for at, seconds in sketch.events(sk.beats, "hiss"):
        if not (seconds.replace(".", "", 1).isdigit() and float(seconds) > 0):
            raise StagingError(f"{sk.slug}: the hiss at {at} s runs for hiss:<seconds>, got {seconds!r}")
    for app in sketch.appearances(sk.beats, sk.end):
        if staging.set_of(sk.beats, app) not in collage_sets.SETS:
            raise StagingError(f"{sk.slug}: unknown set for {app.who} at {app.start} s")
    check_still(sk.beats, staging.still, sk.slug)
    check_push(sk.beats, staging, sk.slug)
    if not (type(staging.bitrate) is int and staging.bitrate >= 0):
        raise StagingError(f"{sk.slug}: bitrate {staging.bitrate!r} is not a whole number of bits a second")


def zooms(beats: Sequence[sketch.Beat], app: sketch.Appearance) -> list[float]:
    """The ``zoom`` cues inside one appearance; a shot snaps in once, on its first."""
    return [t for t, _ in sketch.events(beats, "zoom") if app.start <= t < app.end][:1]


def build(root: Path, staging: Staging, flags: Iterable[str]) -> Episode | None:
    """The episode, drawn and ready for its post and :meth:`Episode.finish`; ``--init`` writes the project files
    and returns ``None`` (the script ends there), ``--voice`` builds from the recording."""
    root = Path(root)
    flags = errors.flags(flags, BUILD_FLAGS)
    check_staging(staging)
    sk = staging.sketch
    if "--init" in flags:
        sketch.write_project(root, sk, COLLAGE.google_font())
        return None
    voiced = "--voice" in flags
    mouths: sketch.Mouths = {}
    if voiced:
        beats, end = sketch.load_beats(root / "voiced" / "beats.json")
        sk = replace(sk, beats=tuple(beats), end=end)
        mouths, mouths_end = sketch.load_mouths(root / "voiced" / "mouths.json", collage.CAST)
        if mouths_end != end:
            raise StagingError(f"voiced/mouths.json runs {mouths_end} s, voiced/beats.json {end} s: record again")
    sketch.check(sk)
    check_still(sk.beats, staging.still, sk.slug)
    check_push(sk.beats, staging, sk.slug)
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
                **(dict(bitrate=str(staging.bitrate), twoPass=True) if staging.bitrate else {}),
            ),
            accessibility=dict(
                description=staging.accessibility
                + " "
                + (f"{staging.narration} Text transcript bundled." if voiced else "Silent master; transcript bundled.")
            ),
        )
    )
    cv, t = ep.cv, ep.t
    spoken = next(b.start for b in sk.beats if b.caption)  # 0 but after a still opening
    if t.duration > sk.end or t.phrases[0].start != spoken:
        raise StagingError(f"{ep.spec.dialogue} runs to {t.duration} s, the sketch to {sk.end} s: run --init again")
    project = ep.scene.find("project")
    if not isinstance(project, Project):  # pragma: no cover - an Episode always writes its project
        raise StagingError(f"{ep.spec.dialogue}: the scene has no <project>")
    project.duration = sk.end  # the last beats may be silent and uncaptioned
    effects = []
    manifest = root / "narration.json"
    if voiced:
        if manifest_duration(manifest) != sk.end:
            raise StagingError(f"narration.json runs {manifest_duration(manifest)} s, voiced/beats.json {sk.end} s")
        effects = effect_cues(manifest, root)
    if COLLAGE.font is None:  # pragma: no cover - a property of the style, tested there
        raise StagingError("the Collage style has no font to measure its captions in")
    font = (root / COLLAGE.font.src).read_bytes()
    measure = partial(fonts.text_width, font)
    cast = staging.cast(sk.beats, sk.end)
    for app in sketch.appearances(sk.beats, sk.end):
        g = cv.group(ep.comp, cv.uid("g"), start=app.start, end=app.end)
        opening = app.start < staging.still  # the grain is drawn afresh every frame: a still shot goes without it
        if not opening:
            cv.apply(g, cv.effect("collage-grain", "film-grain", **GRAIN))  # the paper's tooth, over set and cast
        collage_sets.SETS[staging.set_of(sk.beats, app)](cv, g)
        back = cv.group(g, cv.uid("g"))
        face = (staging.opening if opening else cast)(cv, g, app, mouths)
        front = cv.group(g, cv.uid("g"))
        staging.dress(Shot(cv, app, back, front, sk.beats, sk.end, measure))
        if staging.keep_signature:
            face = collage_sets.zoom_pivot(staging.set_of(sk.beats, app), face, ZOOM_SCALE, height=collage.CAPTION_TOP)
        if staging.push and app.start == 0:
            camera.anchor(g, *face, place=True)
            camera.push_in(cv, g, scale=[(0.0, 1.0), (app.end, staging.push)])
        for at in zooms(sk.beats, app):
            camera.anchor(g, *face, place=True)
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
def sound_effects(
    beats: Sequence[sketch.Beat], end: float, root: Path, seed: int, own: Sequence[Sound] = ()
) -> list[dict]:
    """The manifest's effects: a whoosh into every ``zoom``, the sting on ``sting``, the headset on ``beep``, the
    shutter on ``flash``, a short whoosh landing on every ``swat``, a notification on ``ding``, chewing on ``crunch``,
    a thud on ``thud`` and air on ``hiss:<seconds>``."""
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
    flashes = [at for at, _ in sketch.events(beats, "flash")]
    if flashes:
        clicks = sorted(at + d for at in flashes for d in SHUTTER)
        shutter = foley.write_typing(audio / "shutter.wav", clicks, end, seed=seed)
        out.append(sketch.effect("shutter", 0.0, SHUTTER_GAIN_DB, root, shutter))
    swats = [at for at, _ in sketch.events(beats, "swat")]
    if swats:
        cues = [max(0.0, round(at - SWAT, 6)) for at in swats]
        swat = foley.write_whoosh(audio / "swat.wav", cues, end, length=SWAT, seed=seed)
        out.append(sketch.effect("swat", 0.0, SWAT_GAIN_DB, root, swat))
    dings = [at for at, _ in sketch.events(beats, "ding")]
    if dings:
        ding = foley.write_tones(audio / "ding.wav", dings, end, notes=foley.DING)
        out.append(sketch.effect("ding", 0.0, DING_GAIN_DB, root, ding))
    bites = [at for at, _ in sketch.events(beats, "crunch")]
    if bites:
        clicks = sorted(at + d for at in bites for d in CRUNCH)
        crunch = foley.write_typing(audio / "crunch.wav", clicks, end, seed=seed)
        out.append(sketch.effect("crunch", 0.0, CRUNCH_GAIN_DB, root, crunch))
    thuds = [at for at, _ in sketch.events(beats, "thud")]
    if thuds:
        thud = foley.write_bursts(audio / "thud.wav", thuds, end, foley.THUD, seed=seed)
        out.append(sketch.effect("thud", 0.0, THUD_GAIN_DB, root, thud))
    for i, (at, seconds) in enumerate(sketch.events(beats, "hiss")):
        hiss = foley.write_air(audio / f"hiss-{i}.wav", [at], end, min(float(seconds), end - at), seed=seed + i)
        out.append(sketch.effect(f"hiss-{i}", 0.0, HISS_GAIN_DB, root, hiss))
    for fx in own:
        if fx.at:
            path = foley.write_bursts(audio / f"{fx.id}.wav", fx.at, end, fx.sound, seed=seed)
            out.append(sketch.effect(fx.id, 0.0, fx.gain_db, root, path))
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
    effects = sound_effects(rec.beats, rec.end, root, staging.seed, staging.sounds(rec.beats, rec.end))
    manifest = sketch.manifest(sk, rec, effects, MODEL, note)
    (root / "narration.json").write_text(json.dumps(manifest, indent=2) + "\n")
    for q in rec.items:
        flags = " ".join(f for f, on in (("cut", q["cut"]), ("lag", q["lag"] > 0)) if on)
        print(f"{q['id']} {q['duration']:5.2f}s {flags:8} {q['text']}")
    print(f"{len(rec.items)} lines, {len(effects)} effects, the project runs {rec.end:.3f} s")
    return manifest


def recorder(
    staging: Staging, note: str, doc: str | None, mouth: soundtrack.PhonemeStyle = sketch.MOUTH_STYLE
) -> Callable[..., int]:
    """The ``main`` of an episode's recording script: :func:`srstudio.recording.main` around :func:`record_episode`
    (``python3 <episode>_audio.py PROJECT [--ffmpeg PATH]``, the help from ``doc``)."""

    def main(argv: Sequence[str] | None = None, env: Mapping[str, str] | None = None) -> int:
        return recording.main(
            lambda project, env, ffmpeg: record_episode(staging, project, env, ffmpeg, note, mouth=mouth),
            doc,
            argv,
            env,
        )

    return main
