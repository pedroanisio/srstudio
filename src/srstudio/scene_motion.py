"""Typed random-access camera, world-light and parent motion for composition.

Each sample is a normal validated ScenePlan, suitable for existing preparation
adapters. Sampling does not emit a timeline or estimate aggregate render work.
Euler channels follow authored turns; no shortest-arc rotation is inferred.
"""

from __future__ import annotations

import json
from bisect import bisect_right
from dataclasses import dataclass, field, fields, replace
from typing import Literal, TypeVar, cast

from . import composition as c
from ._composition_parse import _bounded_tree, _record, _string_bytes, _unique
from ._composition_preflight import _COLOR, _camera, _graph
from ._composition_preflight import _unique as _identifiers

Easing = Literal['linear', 'smoothstep', 'smootherstep', 'hold']
SCHEMA = 'srstudio.scene-motion/1.0.0'
MAX_KEYS = 1024


@dataclass(frozen=True)
class CameraKey(c._Record):
    time: float = field(metadata={'minimum': 0, 'maximum': 600})
    value: c.CameraSpec
    easing: Easing = 'linear'


@dataclass(frozen=True)
class LightKey(c._Record):
    time: float = field(metadata={'minimum': 0, 'maximum': 600})
    value: c.LightSpec
    easing: Easing = 'linear'


@dataclass(frozen=True)
class TransformKey(c._Record):
    time: float = field(metadata={'minimum': 0, 'maximum': 600})
    value: c.Transform
    easing: Easing = 'linear'


@dataclass(frozen=True)
class LightTrack(c._Record):
    light: str
    keys: tuple[LightKey, ...]


@dataclass(frozen=True)
class TransformTrack(c._Record):
    layer: str
    keys: tuple[TransformKey, ...]


@dataclass(frozen=True)
class SceneMotion(c._Record):
    """Scene-second tracks; easing belongs to the outgoing segment.

    Tracks begin at zero, match the base scene and hold their final value.
    Smoothstep has zero endpoint velocity; smootherstep also has zero endpoint
    acceleration. Held keys jump exactly at the next key. Numeric channels,
    including Euler angles, interpolate independently. Light color and camera
    projection changes require held segments. Light IDs/kinds cannot change.
    """

    camera: tuple[CameraKey, ...] = ()
    lights: tuple[LightTrack, ...] = ()
    transforms: tuple[TransformTrack, ...] = ()
    schema: Literal['srstudio.scene-motion/1.0.0'] = 'srstudio.scene-motion/1.0.0'


Key = CameraKey | LightKey | TransformKey
RecordT = TypeVar('RecordT', bound=c._Record)


def _fail(path: str, expected: str) -> c.CompositionError:
    return c._fail('motion.' + path, None, expected, 'composition.motion')


def parse_motion(value: str | dict) -> SceneMotion:
    """Parse bounded, closed JSON or a plain mapping; never execute callbacks."""
    if type(value) is str:
        if len(value) > c.MAX_INPUT_BYTES or _string_bytes(value) > c.MAX_INPUT_BYTES:
            raise _fail('input', f'at most {c.MAX_INPUT_BYTES} UTF-8 bytes')
        try:
            value = json.loads(value, object_pairs_hook=_unique)
        except (ValueError, RecursionError) as error:
            if isinstance(error, c.CompositionError):
                raise
            raise _fail('input', 'valid bounded JSON') from error
    _bounded_tree(value, set(), [0, 0])
    return _record(SceneMotion, value, 'motion')


def _keys(keys: tuple[Key, ...], initial: c._Record, duration: float, path: str) -> None:
    if not keys or keys[0].time != 0 or keys[0].value != initial:
        raise _fail(path, 'nonempty keys beginning at zero with the base scene value')
    if keys[-1].time > duration or any(a.time >= b.time for a, b in zip(keys, keys[1:], strict=False)):
        raise _fail(path, 'strictly increasing scene times within the scene duration')
    for a, b in zip(keys, keys[1:], strict=False):
        if a.easing == 'hold':
            continue
        for f in fields(a.value):
            left, right = getattr(a.value, f.name), getattr(b.value, f.name)
            if type(left) is str and left != right:
                raise _fail(path + '.' + f.name, 'a held segment for discrete changes')


def _lerp(a: float, b: float, u: float) -> float:
    # Keep constant channels exact and avoid cancellation at either arrival.
    if a == b:
        return a
    return a + (b - a) * u if u <= 0.5 else b + (a - b) * (1 - u)


def _blend(left: RecordT, right: RecordT, u: float) -> RecordT:
    values: dict[str, float | tuple[float, ...]] = {}
    for f in fields(left):
        a, b = getattr(left, f.name), getattr(right, f.name)
        if type(a) is tuple:
            values[f.name] = tuple(_lerp(x, y, u) for x, y in zip(a, b, strict=True))
        elif type(a) in (int, float):
            values[f.name] = _lerp(a, b, u)
    return replace(left, **values)


def _sample(keys: tuple[Key, ...], time: float) -> c.CameraSpec | c.LightSpec | c.Transform:
    index = bisect_right(tuple(key.time for key in keys), time) - 1
    left = keys[index]
    if index == len(keys) - 1 or time == left.time or left.easing == 'hold':
        return left.value
    right = keys[index + 1]
    u = (time - left.time) / (right.time - left.time)
    if left.easing in ('smoothstep', 'smootherstep'):
        # Evaluate from the nearest endpoint. The expanded quintic near one
        # can exceed one through cancellation, making a valid fade negative.
        reflected = u > 0.5
        v = 1 - u if reflected else u
        weight = v * v * (3 - 2 * v) if left.easing == 'smoothstep' else v * v * v * (v * (v * 6 - 15) + 10)
        u = 1 - weight if reflected else weight
    return _blend(left.value, right.value, u)


def _contact_motion(spec: c.ScenePlan, tracks: tuple[TransformTrack, ...]) -> None:
    # A common rigid ancestor preserves the residual norm for the complete
    # interval, including moving source anchors. Independent transforms or
    # varying common scale need a new continuous-contact proof, not samples.
    layers = {layer.id: layer for layer in spec.layers}

    def ancestors(name: str) -> set[str]:
        result = {name}
        while layers[name].parent is not None:
            name = cast(str, layers[name].parent)
            result.add(name)
        return result

    for contact in spec.contacts:
        actor, target = ancestors(contact.actor), ancestors(contact.target)
        for track in tracks:
            if all(key.value == track.keys[0].value for key in track.keys):
                continue
            a, b = track.layer in actor, track.layer in target
            if a != b or (a and any(key.value.scale != track.keys[0].value.scale for key in track.keys)):
                raise _fail('contacts', 'static contact ancestry or a common rigid animated ancestor')


def sample_scene(
    spec: c.ScenePlan, bindings: tuple[c.AssetBinding, ...], motion: SceneMotion, time: float
) -> c.ValidatedScenePlan:
    """Validate and sample one scene time without changing source clocks.

    The result retains the original duration and layer windows. Its cost is for
    this static view, not a whole animated render. Camera/view envelopes are
    checked at the requested time; a valid sample is not a continuous camera
    safety proof. Contacts retain the static planner's continuous proof only
    for unchanged ancestry or common rigid parent motion.
    """
    if type(motion) is not SceneMotion:
        raise _fail('input', 'a SceneMotion record')
    _graph(motion, [0])
    base = c.preflight(spec, bindings)
    if type(time) not in (int, float) or not 0 <= time <= spec.duration:
        raise _fail('time', 'a finite non-boolean scene time within [0, duration]')
    count = len(motion.camera) + sum(len(t.keys) for t in motion.lights) + sum(len(t.keys) for t in motion.transforms)
    if count > MAX_KEYS:
        raise _fail('keys', f'at most {MAX_KEYS} keys across all tracks')
    light_tracks = _identifiers(motion.lights, 'light', 'motion.lights')
    transform_tracks = _identifiers(motion.transforms, 'layer', 'motion.transforms')
    lights = {light.id: light for light in spec.lights.lights}
    layers = {layer.id: layer for layer in spec.layers}
    if light_tracks.keys() - lights.keys() or transform_tracks.keys() - layers.keys():
        raise _fail('references', 'existing scene light and layer identifiers')
    if motion.camera:
        _keys(motion.camera, spec.camera, spec.duration, 'camera')
        for camera_key in motion.camera:
            _camera(camera_key.value)
    for track in motion.lights:
        light = lights[track.light]
        _keys(track.keys, light, spec.duration, 'lights.' + track.light)
        for key in track.keys:
            value = key.value
            if value.id != light.id or value.kind != light.kind:
                raise _fail('lights.' + track.light, 'unchanged light identity and kind')
            if not _COLOR.fullmatch(value.color) or (value.kind == 'sphere-area' and value.radius <= 0):
                raise _fail('lights.' + track.light, 'hex color and a positive sphere-area radius')
    for transform_track in motion.transforms:
        _keys(
            transform_track.keys,
            layers[transform_track.layer].transform,
            spec.duration,
            'transforms.' + transform_track.layer,
        )
    _contact_motion(spec, motion.transforms)
    if not count:
        return base
    sampled = replace(
        spec,
        camera=cast(c.CameraSpec, _sample(motion.camera, time)) if motion.camera else spec.camera,
        lights=replace(
            spec.lights,
            lights=tuple(
                cast(c.LightSpec, _sample(light_tracks[light.id].keys, time)) if light.id in light_tracks else light
                for light in spec.lights.lights
            ),
        ),
        layers=tuple(
            replace(layer, transform=cast(c.Transform, _sample(transform_tracks[layer.id].keys, time)))
            if layer.id in transform_tracks
            else layer
            for layer in spec.layers
        ),
    )
    return c.preflight(sampled, bindings)
