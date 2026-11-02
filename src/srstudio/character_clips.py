"""Typed character clips with one placement contract and one performance clock.

``Interval`` uses the parent's timeline seconds (project seconds under the composition;
shot seconds inside a sequence shot). Every performance uses seconds relative to the
interval's start. A container clock performs the conversion once, including procedural
idle and native limb animation. Legacy builders retain their original behavior.

Placement maps an explicit source anchor to a point in parent units. Source coordinates
remain the rig's: Actor head origin, Gloss feet/host center, Toon/plate frame pixels.
Adapters do not guess anatomical equivalence between these coordinate systems.
"""

from __future__ import annotations

import math
import re
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING, Literal

from sr_core.scene import Animate, Composition, Group, Key

from . import checks, gloss
from ._transaction import scene_transaction
from .canvas import Canvas
from .errors import SrstudioError
from .face_blends import FaceTrack
from .gaze import GazePlan
from .head_motion import CHANNELS, Channel, HeadPlan
from .limbs.integration import LimbTrack, prepare_tracks
from .rig import Actor, Performance
from .toon import ARMS, EYES, MOUTHS, WEAR, Pose
from .toon_cast import VISEMES
from .toon_head import Glancing, HeadRig, figure

if TYPE_CHECKING:
    from .rafa import Face
    from .rafa_host import Sheet

__all__ = [
    'ActorClip',
    'CharacterClip',
    'CharacterClipError',
    'GlossClip',
    'Interval',
    'Placement',
    'PlateClip',
    'PlateFrame',
    'PlateLayer',
    'ToonClip',
    'place_character',
]

MAX_DURATION = 600.0
MAX_KEYS = 20_000
MAX_LAYERS = 64
Track = tuple[tuple[float, str], ...]


class CharacterClipError(SrstudioError, ValueError):
    """A clip cannot be placed without dropping or misinterpreting authored data."""


def _fail(path: str, actual: object, expected: object, *, code: str = 'character.input') -> CharacterClipError:
    return CharacterClipError(
        f'{path}: expected {expected}',
        code=code,
        path=path,
        actual=actual,
        expected=expected,
        remedy='Use the typed clip for this rig; author performance seconds from zero and place its interval once.',
    )


@dataclass(frozen=True)
class Interval:
    """Inclusive start, exclusive end on the parent's clock; at most 600 seconds per clip."""

    start: float
    end: float

    def __post_init__(self) -> None:
        if not (
            checks.number(self.start)
            and checks.number(self.end)
            and 0 <= self.start < self.end
            and self.end - self.start <= MAX_DURATION
            and math.ulp(self.end) <= 1e-6
            and self.end - self.start >= 1e-6
        ):
            raise _fail(
                'interval', (self.start, self.end), 'finite 0 <= start < end, length <= 600s', code='character.interval'
            )

    @property
    def duration(self) -> float:
        return self.end - self.start


@dataclass(frozen=True)
class Placement:
    """Source ``anchor`` maps to parent ``(x,y)``; scale is a ratio, rotation clockwise degrees."""

    x: float = 0
    y: float = 0
    scale: float = 1
    anchor: tuple[float, float] = (0, 0)
    rotation: float = 0

    def __post_init__(self) -> None:
        for name in ('x', 'y', 'rotation', 'scale'):
            value = getattr(self, name)
            if not checks.number(value) or (name == 'scale' and value <= 0):
                raise _fail(f'placement.{name}', value, 'a finite number; scale must be positive')
        _point(self.anchor, 'placement.anchor')


@dataclass(frozen=True)
class ActorClip:
    """An Actor class and local mouth/blink/nod/limb tracks. Legacy untyped extras are refused."""

    actor: type[Actor]
    performance: Performance = field(default_factory=Performance)


@dataclass(frozen=True)
class ToonClip:
    """A split-head Toon rig: local poses, speech, taps and bounded HeadPlan (including gaze).

    Arm gestures belong to the poses. This adapter does not accept replacement LimbTracks;
    the underlying split-head figure has no such drawing hook.
    ``face_blends`` uses a declared rig driver and holds geometry on its source-clock
    grid; speech and named/target gaze require separate facial ownership and are refused.
    """

    rig: HeadRig
    poses: tuple[Pose, ...]
    head: HeadPlan = field(default_factory=HeadPlan.still)
    mouths: Track = ()
    taps: tuple[float, ...] = ()
    target_gaze: GazePlan | None = None
    face_blends: FaceTrack | None = None


@dataclass(frozen=True)
class GlossClip:
    """Local facial/speech tracks and guest pose/limb tracks; Sunny has no arms."""

    who: Literal['nadia', 'gus', 'tamsin', 'sunny']
    talk: Track = ()
    face: Track = ()
    pose: Track = ()
    limbs: tuple[LimbTrack, ...] = ()


@dataclass(frozen=True)
class PlateLayer:
    """An already-declared image asset at a source-frame pixel position."""

    asset: str
    at: tuple[float, float] = (0, 0)


@dataclass(frozen=True)
class PlateFrame:
    """Layers in painter order, held from local ``start`` until the next frame or clip end."""

    start: float
    layers: tuple[PlateLayer, ...]


@dataclass(frozen=True)
class PlateClip:
    """Prepared plate frames; no rendering or file copying occurs during placement.

    Assets must already be declared on the scene. ``duration`` optionally fixes the source
    length, preventing a frame sequence from being silently stretched by placement.
    """

    frames: tuple[PlateFrame, ...]
    duration: float | None = None

    @classmethod
    def from_rafa(cls, rows: Sequence[Face], sheet: Sheet, assets: Mapping[Path, str]) -> PlateClip:
        """Bind Rafa's prepared sheet to declared image IDs. Identical adjacent frames coalesce.

        ``rafa_host.sheet`` prepares the images separately; register their full-size and
        patch dimensions with Canvas.assets.add_image before placing the returned clip.
        """
        from .rafa import Face
        from .rafa_host import FPS, Sheet, eye_key, mouth_key

        _sequence(rows, 'rows', nonempty=True)
        if not isinstance(sheet, Sheet) or not isinstance(assets, Mapping):
            raise _fail('sheet/assets', None, 'a Rafa Sheet and a path-to-image-ID mapping')
        frames: list[PlateFrame] = []
        for index, face in enumerate(rows):
            if not isinstance(face, Face):
                raise _fail(f'rows[{index}]', face, 'a Rafa Face')
            try:
                eye, mouth = sheet.eyes[eye_key(face)], sheet.mouths[mouth_key(face)]
                layers = (
                    PlateLayer(assets[sheet.bodies[face.turn, face.nod]]),
                    PlateLayer(assets[eye.path], (eye.x, eye.y)),
                    PlateLayer(assets[mouth.path], (mouth.x, mouth.y)),
                )
            except KeyError as exc:
                raise _fail('sheet/assets', str(exc), 'a plate and declared asset ID for every face component') from exc
            if not frames or frames[-1].layers != layers:
                frames.append(PlateFrame(index / FPS, layers))
        return cls(tuple(frames), len(rows) / FPS)


CharacterClip = ActorClip | ToonClip | GlossClip | PlateClip


def _point(value: object, path: str) -> None:
    if not isinstance(value, tuple) or len(value) != 2 or not all(checks.number(v) for v in value):
        raise _fail(path, value, 'a pair of finite coordinates')


_PLACEMENT = Placement()


def _sequence(values: object, path: str, *, nonempty: bool = False, limit: int = MAX_KEYS) -> None:
    if not isinstance(values, (tuple, list)) or not (int(nonempty) <= len(values) <= limit):
        raise _fail(path, values, f'a sequence of {int(nonempty)}..{limit} entries')


def _times(values: Sequence[float], path: str, end: float, *, endpoint: bool = False) -> None:
    previous = -1.0
    for index, time in enumerate(values):
        if not (checks.number(time) and 0 <= time and time > previous and (time <= end if endpoint else time < end)):
            raise _fail(f'{path}[{index}]', time, f'strictly increasing local seconds in 0..{end}')
        rounded = round(time, 6)
        if rounded <= previous or (rounded > round(end, 6) if endpoint else rounded >= round(end, 6)):
            raise _fail(f'{path}[{index}]', time, 'distinct local seconds at six-decimal scene precision')
        previous = rounded


def _track(values: object, path: str, end: float, *, names: Sequence[str] | None = None, numeric: bool = False) -> None:
    _sequence(values, path)
    assert isinstance(values, (tuple, list))
    for index, row in enumerate(values):
        if not isinstance(row, (tuple, list)) or len(row) != 2:
            raise _fail(f'{path}[{index}]', row, 'a (local second, value) pair')
        value = row[1]
        if numeric:
            valid = checks.number(value)
        else:
            valid = isinstance(value, str) and (names is None or value in names)
        if not valid:
            raise _fail(f'{path}[{index}][1]', value, 'a finite number' if numeric else names or 'a state name')
    _times([row[0] for row in values], path, end, endpoint=numeric)


def _limbs(cv: Canvas, tracks: tuple[LimbTrack, ...], end: float) -> None:
    _sequence(tracks, 'limbs', limit=2)
    if any(not isinstance(track, LimbTrack) for track in tracks):
        raise _fail('limbs', tracks, 'typed LimbTracks')
    if tracks:
        prepare_tracks(cv, tracks, end)


def _poses(clip: ToonClip, end: float) -> None:
    from .toon_bento import EYE_STATES, GESTURES, MOODS, MOUTH_KINDS, SHARED_EYES, SHARED_MOUTHS, Bento

    _sequence(clip.poses, 'poses', nonempty=True)
    eyes, mouths, arms = set(EYES), set(MOUTHS), set(ARMS)
    if isinstance(clip.rig.look.drawing, Bento):
        eyes = {'hearts', *MOODS, *EYE_STATES, *SHARED_EYES}
        eyes.update(f'{mood}/{state}' for mood in MOODS for state in EYE_STATES)
        mouths = {'none', *MOUTH_KINDS, *SHARED_MOUTHS}
        arms.update(GESTURES)
    for index, pose in enumerate(clip.poses):
        if not isinstance(pose, Pose):
            raise _fail(f'poses[{index}]', pose, 'a typed Toon Pose')
        for name, names in (('eyes', eyes), ('mouth', mouths), ('arms', arms)):
            value = getattr(pose, name)
            if not isinstance(value, str) or value not in names:
                raise _fail(f'poses[{index}].{name}', value, sorted(names))
        _sequence(pose.wear, f'poses[{index}].wear', limit=len(WEAR))
        if any(not isinstance(item, str) or item not in WEAR for item in pose.wear) or len(set(pose.wear)) != len(
            pose.wear
        ):
            raise _fail(f'poses[{index}].wear', pose.wear, f'unique items from {WEAR}')
    _times([p.start for p in clip.poses], 'poses.start', end)
    if clip.poses[0].start != 0:
        raise _fail('poses[0].start', clip.poses[0].start, 'zero, the clip entry pose')


def _check(cv: Canvas, clip: CharacterClip, end: float) -> None:
    if isinstance(clip, ActorClip):
        if not isinstance(clip.actor, type) or not issubclass(clip.actor, Actor):
            raise _fail('actor', clip.actor, 'an Actor class')
        if clip.actor.build is not Actor.build:
            raise _fail(
                'actor.build', clip.actor.__name__, 'the standard Actor.build lifecycle', code='character.unsupported'
            )
        perf = clip.performance
        if not isinstance(perf, Performance):
            raise _fail('performance', perf, 'a Performance record')
        if perf.extras:
            raise _fail(
                'performance.extras',
                perf.extras,
                'typed tracks; legacy extras have no normalized clock',
                code='character.unsupported',
            )
        if perf.limbs and not clip.actor.supports_limbs:
            raise _fail(
                'performance.limbs', clip.actor.__name__, 'an Actor supporting limbs', code='character.unsupported'
            )
        _track(perf.mouth, 'performance.mouth', end, names=clip.actor.mouth_poses)
        _track(perf.nods, 'performance.nods', end, numeric=True)
        _sequence(perf.blinks, 'performance.blinks')
        for index, span in enumerate(perf.blinks):
            _point(span, f'performance.blinks[{index}]')
            if not 0 <= span[0] < span[1] <= end:
                raise _fail('performance.blinks', span, f'local spans inside 0..{end}')
        _sequence(perf.limbs, 'performance.limbs', limit=2)
        _limbs(cv, tuple(perf.limbs), end)
    elif isinstance(clip, ToonClip):
        if not isinstance(clip.rig, HeadRig) or not isinstance(clip.head, HeadPlan):
            raise _fail('rig/head', None, 'a HeadRig and a HeadPlan')
        _poses(clip, end)
        _track(clip.mouths, 'mouths', end, names=VISEMES)
        _sequence(clip.taps, 'taps')
        _times(clip.taps, 'taps', end)
        for name in CHANNELS:
            channel = getattr(clip.head, name)
            if not isinstance(channel, Channel):
                raise _fail(f'head.{name}', channel, 'a Channel')
            _track(channel.keys, f'head.{name}', end, numeric=True)
        _track(clip.head.gaze, 'head.gaze', end)
        clip.head.check_bounds(clip.rig.style)
        if clip.face_blends is not None:
            if not isinstance(clip.face_blends, FaceTrack):
                raise _fail('face_blends', None, 'a FaceTrack')
            if (
                clip.target_gaze is not None
                or any(n != 'ahead' for _, n in clip.head.gaze)
                or any(n != 'closed' for _, n in clip.mouths)
            ):
                raise _fail('face_blends', None, 'one facial owner; no named/target gaze or speech')
            clip.face_blends.prepare(clip.rig, clip.poses, end)
        if clip.target_gaze is not None:
            from ._gaze_drawing import prepare

            prepare(clip.rig, clip.poses, end, clip.head, clip.target_gaze)
        if any(name != 'ahead' for _, name in clip.head.gaze) and not isinstance(clip.rig.look.drawing, Glancing):
            raise _fail('head.gaze', clip.rig.look.name, 'a drawing supporting gaze', code='character.unsupported')
    elif isinstance(clip, GlossClip):
        if not isinstance(clip.who, str) or clip.who not in gloss.CAST:
            raise _fail('who', clip.who, gloss.CAST)
        if clip.who == 'sunny' and (clip.pose or clip.limbs):
            raise _fail('pose/limbs', clip.who, 'a Gloss guest with arms', code='character.unsupported')
        _track(clip.talk, 'talk', end, names=gloss.VISEMES)
        _track(clip.face, 'face', end, names=gloss.HOST_FACES if clip.who == 'sunny' else gloss.FACES)
        _track(clip.pose, 'pose', end, names=gloss.POSES)
        _limbs(cv, clip.limbs, end)
    elif isinstance(clip, PlateClip):
        _sequence(clip.frames, 'frames', nonempty=True)
        if clip.duration is not None and (not checks.number(clip.duration) or abs(clip.duration - end) > 1e-6):
            raise _fail('duration', end, f'the prepared plate duration {clip.duration}')
        images = {image.attributes().get('id') for image in cv.scene.iter('image')}
        for index, frame in enumerate(clip.frames):
            if not isinstance(frame, PlateFrame):
                raise _fail(f'frames[{index}]', frame, 'a PlateFrame')
            _sequence(frame.layers, f'frames[{index}].layers', nonempty=True, limit=MAX_LAYERS)
            for layer in frame.layers:
                if not isinstance(layer, PlateLayer) or not isinstance(layer.asset, str) or layer.asset not in images:
                    raise _fail(f'frames[{index}].layers', layer, 'PlateLayers referencing declared image assets')
                _point(layer.at, f'frames[{index}].layers.at')
        _times([f.start for f in clip.frames], 'frames.start', end)
        if clip.frames[0].start != 0:
            raise _fail('frames[0].start', clip.frames[0].start, 'zero, the clip entry frame')
    else:
        raise _fail('clip', clip, 'an ActorClip, ToonClip, GlossClip or PlateClip')


def _draw(cv: Canvas, parent: Group, clip: CharacterClip, end: float) -> None:
    if isinstance(clip, ActorClip):
        clip.actor(cv, tag=f'{parent.id}-actor').build(parent, 0, 0, perf=clip.performance, end=end)
    elif isinstance(clip, ToonClip):
        figure(
            cv,
            parent,
            clip.rig,
            clip.poses,
            end,
            clip.head,
            taps=clip.taps,
            mouths=clip.mouths,
            target_gaze=clip.target_gaze,
            face_blends=clip.face_blends,
        )
    elif isinstance(clip, GlossClip):
        if clip.who == 'sunny':
            gloss.sunny(cv, parent, at=(0, 0), end=end, talk=clip.talk, face=clip.face)
        else:
            gloss.draw(
                cv,
                parent,
                clip.who,
                at=(0, 0),
                end=end,
                talk=clip.talk,
                face=clip.face,
                pose=clip.pose,
                limbs=clip.limbs,
            )
    else:
        for index, frame in enumerate(clip.frames):
            stop = clip.frames[index + 1].start if index + 1 < len(clip.frames) else end
            group = cv.group(parent, cv.uid('plate-frame'), start=frame.start, end=stop)
            for layer in frame.layers:
                group.add_layer(id=cv.uid('plate-layer'), asset=layer.asset, x=layer.at[0], y=layer.at[1])


def _local_keys(group: Group) -> None:
    """Keep source keys aligned when the engine shifts a sequence shot's node starts.

    Group clocks retime both clocks, but sequence placement shifts node lifetimes without
    shifting composition key times. Express source keys relative to their owning node's
    original start; the engine then carries both together. Existing local/normalized
    channels retain their semantics, interpolation and spring context.
    """
    for animation in group.iter('animate'):
        assert isinstance(animation, Animate)
        if animation.timeBase not in (None, 'composition'):
            continue
        owner = animation.owner
        while owner is not None and not hasattr(type(owner), 'start'):
            owner = owner.owner
        start = float(owner.attributes().get('start', 0)) if owner is not None else 0
        for key in animation.find_all('key'):
            assert isinstance(key, Key)
            assert key.time is not None
            key.time = round(float(key.time) - start, 6)
        animation.timeBase = 'local'


def place_character(
    cv: Canvas,
    parent: Composition | Group,
    clip: CharacterClip,
    *,
    interval: Interval,
    placement: Placement = _PLACEMENT,
    id: str | None = None,
) -> Group:
    """Preflight and place a clip atomically, restoring scene/canvas state if drawing fails.

    The parent must belong to this canvas and cannot itself be a sequence (use its shot
    group). Frozen canvases are refused: this API places a running, timed clip. All four
    adapters use the same clock regardless of the caller's ``Canvas.local_time`` setting.
    File assets must be prepared separately; no filesystem transaction is implied.
    """
    if not isinstance(interval, Interval) or not isinstance(placement, Placement):
        raise _fail('interval/placement', None, 'typed Interval and Placement records')
    if not isinstance(parent, (Composition, Group)) or not any(node is parent for node in cv.scene.iter()):
        raise _fail('parent', parent, 'a composition or group belonging to this canvas')
    if cv._frozen:
        raise _fail('canvas', 'frozen', 'a running canvas', code='character.unsupported')
    if id is not None and (
        not isinstance(id, str)
        or not re.fullmatch(r'[A-Za-z_][A-Za-z0-9_.-]*', id)
        or any(node.attributes().get('id') == id for node in cv.scene.iter())
    ):
        raise _fail('id', id, 'a nonempty, unused scene ID')
    _check(cv, clip, interval.duration)
    local = cv.local_time
    try:
        with scene_transaction(cv.scene, cv):
            cv.local_time = False
            group = cv.group(
                parent,
                id or cv.uid('character'),
                start=interval.start,
                end=interval.end,
                timeOffset=interval.start,
                x=placement.x,
                y=placement.y,
                anchorX=placement.anchor[0],
                anchorY=placement.anchor[1],
                scaleX=placement.scale,
                scaleY=placement.scale,
                rotation=placement.rotation,
            )
            _draw(cv, group, clip, interval.duration)
            _local_keys(group)
            ids = [node.attributes()['id'] for node in cv.scene.iter() if 'id' in node.attributes()]
            if len(ids) != len(set(ids)):
                raise _fail('id', group.id, 'unique IDs throughout the completed drawing')
            return group
    finally:
        cv.local_time = local
