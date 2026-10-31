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
checked against the beats). A character the staging names in ``heads`` moves its head (ADR 0050): :func:`head_plans`
plans it from the takes of ``voiced/speech.json`` (typed by :func:`srstudio.sketch.load_speech`), its own lines and
what the others say, and it is drawn through :func:`srstudio.toon_head.figure`. :func:`record_episode` is the
ElevenLabs run: :func:`srstudio.sketch.record` (one request per line, speech-to-text check, voices confirmed by
name), then the keyboard between the lines, a phone buzz on every ``toast`` event and the sting on ``hangup``,
all synthesised deterministically by :mod:`srstudio.foley`.
"""

from __future__ import annotations

import json
import os
from collections.abc import Callable, Iterable, Mapping, Sequence
from dataclasses import dataclass, field, replace
from functools import cache, partial
from pathlib import Path
from typing import Any

from sr_core.scene import Project

from . import (
    TOON,
    Episode,
    EpisodeSpec,
    camera,
    checks,
    errors,
    foley,
    fonts,
    head_motion,
    recording,
    sketch,
    soundtrack,
    subtitles,
    toon,
    toon_head,
    toon_props,
    toon_rigs,
)
from .canvas import Canvas
from .layout import SafeArea
from .narration import effect_cues, manifest_duration, require_consent
from .provider import KEY_ENV
from .staging import StagingError
from .styles import Style
from .voice import MODEL, ElevenLabsClient

TYPING_PEAK = 0.70
TYPING_GAIN_DB = -2.0  # the keys only play between the lines
BUZZ_GAIN_DB = -4.0
STING_GAIN_DB = -5.0
BADGE_SIZE = 28
CALL_ENDED = "Call ended"
BUILD_FLAGS = ("--init", "--voice")  # write the project files; build from the recording
PILL_MARGIN = 40  # frame pixels kept free at each side of the widest caption pill
SEAT = (165, 840)  # where a character sits on the desk, reference pixels: a framed figure grows from here


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
    light: object | None = None  # a lit staging's light layer, between the character and the desk (ADR 0043)
    versions: Mapping[str, int] = field(default_factory=dict)  # the pins, for a further character drawn in the shot
    mouths: Mapping[str, Sequence[tuple[float, str]]] = field(default_factory=dict)  # for a figure the dress draws
    said: Callable[[], Sequence[tuple[str | None, head_motion.Speech]]] = tuple  # the takes, for a head the dress draws

    def badges(self, texts: Mapping[str, str], ended: str = CALL_ENDED, event: str = "hangup") -> None:
        for a, b, text in badge_spans(self.beats, self.app, texts, ended, event):
            toon_props.badge(self.cv, self.front, text, a, b, partial(self.measure, size=BADGE_SIZE), BADGE_SIZE)


@dataclass(frozen=True)
class Staging:
    """What an episode adds to its sketch: how each shot is dressed, the pill tints per speaker, the stickers on
    a character, its words for the metadata, what stands in front of the character (the office desk unless a
    dinner, say, lays a table instead) and, optionally, a ``camera`` that moves each shot: it is called with the
    dressed :class:`Shot` (its beats are the ones drawn, scripted or voiced) and the shot's group (set, character,
    desk and props; the captions stay still), which is then named ``shot-NNN`` (its order) so
    :mod:`srstudio.craft` counts its moves as camera. ``heads`` names the characters that move their heads
    (:mod:`srstudio.toon_rigs`); everyone else is drawn flat. ``figures`` frames a character closer than the desk's
    medium: ``{who: (scale, dx)}`` draws it that much larger about its seat (:data:`SEAT`) and moves it ``dx``
    reference pixels sideways, set and desk staying where they are, so a small character can fill a shot.
    A channel that shares Toon's cast and sets but not its letters, clock or master brings its own ``style``;
    ``bare`` names who is drawn with no figure, a card playing as a shot of its own; ``captions`` letters the cues
    instead of Toon's pills, each fitted by that drawer; ``output`` is the master's path under the project's render
    root and ``crf`` its quality."""

    sketch: sketch.Sketch
    seed: int
    description: str
    accessibility: str
    narration: str
    tints: Mapping[str, str]
    dress: Callable[[Shot], None]
    versions: Mapping[str, int]  # the character versions its release pins; required, so no script can forget them
    stickers: Mapping[str, Sequence[tuple]] = field(default_factory=dict)
    desk: Callable[[Canvas, object], None] = toon.desk
    lit: bool = False  # each shot gets a light layer between the character and the desk (ADR 0043)
    camera: Callable[[Shot, object], None] | None = None
    heads: tuple[str, ...] = ()
    figures: Mapping[str, tuple[float, float]] = field(default_factory=dict)
    style: Style = TOON
    bare: tuple[str, ...] = ()
    captions: Callable[[Canvas, object, Sequence[toon.Line], Callable[..., float], Mapping[str, str]], Any] | None = (
        None
    )
    finish: Callable[[Canvas, object], None] | None = None  # the style's grade over each shot; none on the Toon reels
    output: str | None = None
    crf: str = "17"
    on_face: Mapping[str, Callable[..., None]] = field(default_factory=dict)
    """Per character in ``heads``: ``(cv, appearance, beats, face)`` draws into that shot's face group, so it moves with
    the head."""
    overlay: Callable[[Canvas, object, Sequence[Any], float, Callable[..., float]], None] | None = None
    """``(cv, parent, beats, end, measure)`` draws what stays over every shot, under the captions and out of the
    camera's reach, from the beats the build placed: a show's graphics."""
    safe_area: SafeArea | None = None  # declared on the project, for a show that keeps its text inside one
    loudness: str | None = None  # the master's integrated LUFS, when a reel departs from its style's
    moves: Mapping[str, Callable[[Canvas, Any, Any, Sequence[Any]], None]] = field(default_factory=dict)
    """Per character: ``(cv, body, appearance, beats)`` keys that shot's body group on the project clock, about the
    character's seat, so a figure can bend, sink or sway while its set stays put."""


def figure_group(cv: Canvas, parent, framing: tuple[float, float] | None):
    """The group a character is drawn into: ``parent`` itself, or a group ``framing`` scales and moves."""
    if framing is None:
        return parent
    scale, dx = framing
    if not (checks.number(scale) and scale > 0 and checks.number(dx)):
        raise StagingError(f"a figure's framing is (scale > 0, dx), got {framing!r}")
    x, y = toon.fx(SEAT[0]), toon.fy(SEAT[1])
    return cv.group(parent, cv.uid("g"), anchorX=x, anchorY=y, x=x + toon.fh(dx), y=y, scaleX=scale, scaleY=scale)


def _rig(who: str, versions: Mapping[str, int]) -> toon_head.HeadRig:
    return toon_rigs.rig_of(sketch.part_of(who), versions)


def check_heads(sk: sketch.Sketch, heads: Sequence[str], versions: Mapping[str, int]) -> None:
    """Refuse a character in ``heads`` that has no rig, or that this sketch never shows, by name."""
    shown = {app.who for app in sketch.appearances(sk.beats, sk.end)}
    for who in heads:
        _rig(who, versions)
        if who not in shown:
            raise StagingError(f"heads names {who!r}, who is not in this sketch ({sorted(shown)})")


def spoken_takes(root: Path, sk: sketch.Sketch, voiced: bool) -> list[tuple[str | None, head_motion.Speech]]:
    """Who said each take of ``voiced/speech.json`` and the take as head motion reads it; in a silent build, nothing."""
    if not voiced:
        return []
    path = root / "voiced" / "speech.json"
    if not path.is_file():
        raise StagingError(f"heads need {path}, written by the recording run: record again")
    takes, end = sketch.load_speech(path, sk.cast)
    if end != sk.end:
        raise StagingError(f"voiced/speech.json runs {end} s, voiced/beats.json {sk.end} s: record again")
    return [(t.who, head_motion.speech_of(t.alignment, t.at, root / "audio" / f"vo-{t.id}.wav")) for t in takes]


def head_plans(
    root: Path, sk: sketch.Sketch, heads: Sequence[str], voiced: bool, versions: Mapping[str, int]
) -> dict[str, tuple[toon_head.HeadRig, head_motion.HeadPlan]]:
    """The rig and the plan of each character in ``heads`` over the whole sketch: in a voiced build from the takes
    of ``voiced/speech.json``, its own lines to speak and everyone else's to hear; in a silent one, idle."""
    if not heads:
        return {}
    spoken = spoken_takes(root, sk, voiced)
    out = {}
    for who in heads:
        rig = _rig(who, versions)
        own = [speech for said_by, speech in spoken if said_by == who]
        heard = [speech for said_by, speech in spoken if said_by != who]
        out[who] = (rig, head_motion.plan(rig.style, own, sk.end, heard=heard))
    return out


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


def opening_push(scale: float = 1.06, at: tuple[float, float] = (540.0, 1000.0)) -> Callable[[Shot, object], None]:
    """A :attr:`Staging.camera` that pushes in on ``at`` across the first shot and leaves the others where they stand:
    a reel that speaks from its first frame opens on movement (the ``sp-hook_motion`` test's arm b) without a redrawn
    pose or another second of recording."""
    if not (checks.number(scale) and scale > 1):
        raise StagingError(f"an opening push grows the shot, above 1, got {scale!r}")

    def push(shot: Shot, group: object) -> None:
        if shot.app.start == 0:
            camera.anchor(group, *at, place=True)
            camera.push_in(shot.cv, group, scale=[(0.0, 1.0), (shot.app.end, scale)])

    return push


def build(root: Path, staging: Staging, flags: Iterable[str]) -> Episode | None:
    """The episode, drawn and ready for its post and :meth:`Episode.finish`; ``--init`` writes the project files
    and returns ``None`` (the script ends there), ``--voice`` builds from the recording."""
    root = Path(root)
    flags = errors.flags(flags, BUILD_FLAGS)
    sk = staging.sketch
    check_heads(sk, staging.heads, staging.versions)
    if "--init" in flags:
        sketch.write_project(root, sk, staging.style.google_font())
        return None
    voiced = "--voice" in flags
    mouths: sketch.Mouths = {}
    if voiced:
        beats, end = sketch.load_beats(root / "voiced" / "beats.json")
        sk = replace(sk, beats=tuple(beats), end=end)
        mouths, mouths_end = sketch.load_mouths(root / "voiced" / "mouths.json", sk.cast)
        if mouths_end != end:
            raise StagingError(f"voiced/mouths.json runs {mouths_end} s, voiced/beats.json {end} s: record again")
    sketch.check(sk)
    heads = head_plans(root, sk, staging.heads, voiced, staging.versions)
    said = cache(partial(spoken_takes, root, sk, voiced))  # read once, and only by a dress that asks
    ep = Episode(
        EpisodeSpec(
            slug=sk.slug,
            title=sk.title,
            description=staging.description + " " + (staging.narration if voiced else "Silent master."),
            root=root,
            seed=staging.seed,
            style=staging.style,
            dialogue="voiced/script.json" if voiced else "script.json",
            language="en-US",
            output=staging.output,
            safe_area=staging.safe_area,
            output_options=dict(
                codec="h264",
                container="mp4",
                fps=str(staging.style.fps),
                crf=staging.crf,
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
    cues = sketch.cues(sk.beats, sk.end, sk.lines)
    first = cues[0]["start"] if cues else 0.0  # 0, or later after a still, uncaptioned opening
    if t.duration > sk.end or t.phrases[0].start != first:
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
    if staging.style.font is None:  # pragma: no cover - a property of the style, tested there
        raise StagingError(f"the {staging.style.name} style has no font to measure its captions in")
    font = (root / staging.style.font.src).read_bytes()
    measure = partial(fonts.text_width, font)
    bare = {*staging.bare, *sk.bare}
    for n, app in enumerate(sketch.appearances(sk.beats, sk.end), 1):
        g = cv.group(ep.comp, f"shot-{n:03d}" if staging.camera else cv.uid("g"), start=app.start, end=app.end)
        back = cv.group(g, cv.uid("g"))
        poses = toon.parse_poses(app.poses, f"poses of {app.who} from {app.start} s")
        extra = {} if app.who in bare else sketch.drawer_extras(app.who, staging.stickers, mouths)
        body = figure_group(cv, g, staging.figures.get(app.who))
        if app.who in staging.moves:
            x, y = toon.fx(SEAT[0]), toon.fy(SEAT[1])
            body = cv.group(body, cv.uid("g"), anchorX=x, anchorY=y, x=x, y=y)
            staging.moves[app.who](cv, body, app, sk.beats)
        if app.who in bare:
            pass  # a card: the dress draws the whole frame
        elif app.who in heads:
            rig, plan = heads[app.who]
            shot_plan = plan.during(app.start, app.end)
            if app.who in staging.on_face:
                extra = {**extra, "on_face": partial(staging.on_face[app.who], cv, app, sk.beats)}
            toon_head.figure(cv, body, rig, poses, app.end, shot_plan, taps, enter=app.start, **extra)
        else:
            sketch.drawer(app.who, staging.versions)(cv, body, poses, app.end, taps, enter=app.start, **extra)
        light = cv.group(g, cv.uid("g")) if staging.lit else None
        staging.desk(cv, g)
        front = cv.group(g, cv.uid("g"))
        shot = Shot(cv, app, back, front, sk.beats, sk.end, measure, light, staging.versions, mouths, said)
        staging.dress(shot)
        if staging.camera is not None:
            staging.camera(shot, g)
        if staging.finish is not None:
            staging.finish(cv, g)
    lines = toon.load_script(root / ep.spec.dialogue)
    if staging.overlay is not None:
        staging.overlay(cv, ep.comp, sk.beats, sk.end, measure)
    if staging.captions is not None:
        drawn = staging.captions(cv, ep.comp, lines, measure, staging.tints)
        if drawn is not None:
            ep.hide_on_cover(drawn)
    else:
        fit_captions(lines, partial(measure, size=toon.CAPTION_SIZE), cv.width)
        toon.captions(cv, ep.comp, lines, partial(measure, size=toon.CAPTION_SIZE), tints=staging.tints)
    if voiced:
        ep.audio(narration=manifest, loudness=staging.loudness)
        for fx in effects:
            cv.assets.add_audio(id=f"fx-{fx.id}", src=fx.audio, sha256=fx.sha256)
            ep.add_track(f"fx-track-{fx.id}", f"fx-{fx.id}", start=fx.start, role="effects", gain=fx.gain_db)
    subtitles.write_srt(root / f"{sk.slug}.srt", [(p.start, p.end, p.caption) for p in t.phrases])
    return ep


# -- the recording run ------------------------------------------------------------------------------------------------
@dataclass(frozen=True)
class Sound:
    """A sound a sketch adds to the keys, the buzz and the sting: ``sound`` at every ``at`` project second, on the
    track ``id``, at ``gain_db``."""

    id: str
    sound: foley.Burst
    at: tuple[float, ...]
    gain_db: float = -4.0


Sounds = Callable[[Sequence[sketch.Beat], float], Sequence[Sound]]  # the sketch's own sounds, from the placed beats


def sound_effects(
    beats: Sequence[sketch.Beat],
    end: float,
    speech: Sequence[tuple[float, float]],
    root: Path,
    seed: int,
    sounds: Sounds | None = None,
) -> list[dict]:
    """The manifest's effects: the keyboard in the typing beats between the lines (its taps swap the frames), a
    buzz under every ``toast`` event, the sting on ``hangup``, and what ``sounds`` asks of the placed beats."""
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
    for fx in sounds(beats, end) if sounds is not None else ():
        if fx.at:
            path = foley.write_bursts(audio / f"{fx.id}.wav", fx.at, end, fx.sound, seed=seed)
            out.append(sketch.effect(fx.id, 0.0, fx.gain_db, root, path))
    return out


Foley = Callable[[Sequence[sketch.Beat], float, Sequence[tuple[float, float]], Path, int], list[dict]]


def record_episode(
    sk: sketch.Sketch,
    root: Path,
    env: Mapping[str, str],
    ffmpeg: str,
    seed: int,
    note: str,
    mouth: soundtrack.PhonemeStyle = sketch.MOUTH_STYLE,
    foley_of: Foley = sound_effects,
    sounds: Sounds | None = None,
) -> dict:
    """Record the sketch under ``root`` (only with ``SRSTUDIO_ALLOW_CLOUD=1``; the key from the environment, never
    written), synthesise its effects and write ``narration.json``; returns the manifest. ``mouth`` reads the takes'
    letters into the characters' viseme tracks (``voiced/mouths.json``); ``foley_of`` makes the effects, the office
    sounds of :func:`sound_effects` unless a sketch set somewhere else brings its own; ``sounds`` instead adds a
    sketch's own foley to those office sounds."""
    os.umask(0o077)  # generated outputs are private: folders 700, files 600
    require_consent(env)
    root = Path(root)
    key = env.get(KEY_ENV, "")
    client = ElevenLabsClient(root / "assets" / "elevenlabs", key, model=MODEL, seed=seed)
    rec = sketch.record(sk, root, client, key=key, ffmpeg=ffmpeg, mouth=mouth)
    effects = (
        foley_of(rec.beats, rec.end, rec.speech, root, seed)
        if sounds is None
        else sound_effects(rec.beats, rec.end, rec.speech, root, seed, sounds)
    )
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
    foley_of: Foley = sound_effects,
    sounds: Sounds | None = None,
) -> Callable[..., int]:
    """The ``main`` of an episode's recording script: :func:`srstudio.recording.main` around :func:`record_episode`
    (``python3 <episode>_audio.py PROJECT [--ffmpeg PATH]``, the help from ``doc``); ``validate`` checks the sketch
    once the arguments are parsed, before anything is recorded; ``foley_of`` and ``sounds`` as in
    :func:`record_episode`."""

    def record(project: Path, env: Mapping[str, str], ffmpeg: str) -> dict:
        if validate is not None:
            validate(sk)
        return record_episode(sk, project, env, ffmpeg, seed, note, mouth=mouth, foley_of=foley_of, sounds=sounds)

    def main(argv: Sequence[str] | None = None, env: Mapping[str, str] | None = None) -> int:
        return recording.main(record, doc, argv, env)

    return main
