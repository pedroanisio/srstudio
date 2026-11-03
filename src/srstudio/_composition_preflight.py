"""Resolve scene manifests against authored bindings, approved parts and explicit backend envelopes."""

from __future__ import annotations

import hashlib
import itertools
import json
import math
import re
from bisect import bisect_right
from dataclasses import asdict, fields
from fractions import Fraction
from typing import Literal

from . import composition as c
from . import parts, styles
from .errors import SrstudioError
from .limbs.math3d import Frame, Quaternion, Vec3

_ID = re.compile(r'[A-Za-z_][A-Za-z0-9_.-]{0,127}\Z')
_SHA = re.compile(r'[a-f0-9]{64}\Z')
_COLOR = re.compile(r'#[a-fA-F0-9]{6}\Z')
_PASSES = {
    'vector': frozenset({'rgba'}),
    'plates': frozenset({'rgba'}),
    'proxy': frozenset({'rgba', 'back', 'front', 'under'}),
}


def _digest(value: object) -> str:
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, separators=(',', ':'), allow_nan=False).encode()
    ).hexdigest()


def style_revision(name: str) -> str:
    if not isinstance(name, str) or name not in styles.STYLES:
        raise c._fail('style.name', name, tuple(sorted(styles.STYLES)), 'composition.version')
    return _digest(styles.STYLES[name].facts())


def _id(value: str, path: str) -> None:
    if not _ID.fullmatch(value):
        raise c._fail(path, value, 'an identifier of 1..128 letters, digits, underscores, dots or hyphens')


def _unique(values: tuple, name: str, path: str) -> dict:
    result = {}
    for index, value in enumerate(values):
        key = getattr(value, name)
        _id(key, f'{path}[{index}].{name}')
        if key in result:
            raise c._fail(f'{path}[{index}].{name}', key, 'a unique identifier', 'composition.reference')
        result[key] = value
    return result


def _graph(value: object, count: list[int], depth: int = 0) -> None:
    count[0] += 1
    if count[0] > c.MAX_GRAPH_ITEMS or depth > 16:
        raise c._fail('scene', count[0], 'a bounded manifest graph')
    if isinstance(value, c._Record):
        value.__post_init__()
        for f in fields(value):
            if f.name == 'background' and getattr(value, f.name) is None:
                continue  # An unused optional clear color adds no legacy record visits.
            _graph(getattr(value, f.name), count, depth + 1)
    elif isinstance(value, tuple):
        for item in value:
            _graph(item, count, depth + 1)


def _camera(spec: c.CameraSpec) -> tuple[Vec3, Vec3, Vec3]:
    direction = Vec3(*spec.target) - Vec3(*spec.position)
    if direction.length <= spec.near:
        raise c._fail('camera.target', spec.target, 'a target beyond the near plane', 'composition.camera')
    forward = direction.unit()
    right = forward.cross(Vec3(0, 1, 0))
    if right.length <= 1e-9:
        raise c._fail('camera.position', spec.position, 'a camera with an unambiguous right axis', 'composition.camera')
    right = right.unit()
    return forward, right, right.cross(forward)


def _pose(layer: c.LayerSpec, layers: dict, cache: dict, visiting: set[str]) -> tuple[Frame, float]:
    if layer.id in cache:
        return cache[layer.id]
    if layer.id in visiting:
        raise c._fail(f'layers.{layer.id}.parent', layer.parent, 'an acyclic parent graph', 'composition.reference')
    visiting.add(layer.id)
    rotation = Quaternion()
    for axis, degrees in zip((Vec3(1, 0, 0), Vec3(0, 1, 0), Vec3(0, 0, 1)), layer.transform.rotation, strict=True):
        rotation = Quaternion.axis_angle(axis, math.radians(degrees)) * rotation
    frame, scale = Frame(Vec3(*layer.transform.translation), rotation), layer.transform.scale
    if layer.parent is not None:
        if layer.parent not in layers:
            raise c._fail(f'layers.{layer.id}.parent', layer.parent, 'an existing layer', 'composition.reference')
        parent, parent_scale = _pose(layers[layer.parent], layers, cache, visiting)
        frame = parent.compose(Frame(frame.origin * parent_scale, frame.rotation))
        scale *= parent_scale
    if not math.isfinite(scale) or not 1e-12 <= scale <= 1e12:
        raise c._fail(f'layers.{layer.id}.transform.scale', scale, 'a nonsingular bounded world scale')
    visiting.remove(layer.id)
    cache[layer.id] = frame, scale
    return frame, scale


def _pose_key(frame: Frame, scale: float) -> dict:
    """Resolved geometry coordinates, independent of integer/float spelling."""
    origin, rotation = frame.origin, frame.rotation
    return {
        'origin': tuple(float(v) for v in (origin.x, origin.y, origin.z)),
        'rotation': tuple(float(v) for v in (rotation.w, rotation.x, rotation.y, rotation.z)),
        'scale': float(scale),
    }


def _check_camera(
    layer: c.LayerSpec, binding: c.AssetBinding, pose: tuple[Frame, float], camera: c.CameraSpec, axes: tuple
) -> None:
    from ._composition_paths import spatial

    frame, scale = pose
    if layer.space == 'screen':
        if frame.origin.z != 0 or abs(frame.rotation.rotate(Vec3(0, 0, 1)).z - 1) > 1e-9:
            raise c._fail(
                f'layers.{layer.id}.transform', None, 'a nonsingular 2D screen transform', 'composition.camera'
            )
        return
    forward = axes[0]
    if binding.backend == 'vector' and not spatial(binding):
        normal = frame.rotation.rotate(Vec3(0, 0, 1))
        if abs(normal.dot(forward) + 1) > 1e-8:
            raise c._fail(
                f'layers.{layer.id}.transform', layer.transform, 'a frontal vector view', 'composition.capability'
            )
    for corner in itertools.product(*zip(binding.bounds.minimum, binding.bounds.maximum, strict=True)):
        point = frame.point(Vec3(*corner) * scale)
        depth = (point - Vec3(*camera.position)).dot(forward)
        if depth <= camera.near:
            raise c._fail(
                f'layers.{layer.id}.bounds', depth, 'all bounds beyond the camera near plane', 'composition.camera'
            )


def _anchor(anchor: c.Anchor, time: float, times: tuple[float, ...]) -> Vec3:
    if not anchor.keys:
        return Vec3(*anchor.position)
    index = bisect_right(times, time) - 1
    if index < 0:
        return Vec3(*anchor.keys[0].position)
    if index >= len(anchor.keys) - 1:
        return Vec3(*anchor.keys[-1].position)
    left, right = anchor.keys[index : index + 2]
    u = (time - left.time) / (right.time - left.time)
    return Vec3(*left.position) * (1 - u) + Vec3(*right.position) * u


def _contacts(spec: c.ScenePlan, layers: dict, assets: dict, poses: dict) -> int:
    samples = 0
    key_times = {id(a): tuple(key.time for key in a.keys) for asset in assets.values() for a in asset.anchors}
    for index, contact in enumerate(spec.contacts):
        path = f'contacts[{index}]'
        if contact.start >= contact.end or contact.end > spec.duration:
            raise c._fail(path, asdict(contact), 'an ordered scene-time interval', 'composition.contact')
        resolved = []
        times = {contact.start, contact.end}
        for layer_id, anchor_name in ((contact.actor, contact.actor_anchor), (contact.target, contact.target_anchor)):
            if layer_id not in layers:
                raise c._fail(path, layer_id, 'an existing contact layer', 'composition.reference')
            layer = layers[layer_id]
            if layer.space != 'world':
                raise c._fail(path, layer_id, 'world-space anchors for spatial contacts', 'composition.contact')
            anchors = {a.name: a for a in assets[layer.asset].anchors}
            if anchor_name not in anchors:
                raise c._fail(path, anchor_name, 'an authored anchor on the referenced asset', 'composition.reference')
            temporal, anchor = layer.temporal, anchors[anchor_name]
            if not temporal.start <= contact.start < contact.end <= temporal.end:
                raise c._fail(
                    path, (contact.start, contact.end), 'a contact within both layer intervals', 'composition.contact'
                )
            for key in anchor.keys:
                time = temporal.start + (key.time - temporal.source_start) / temporal.rate
                if contact.start < time < contact.end:
                    times.add(time)
            resolved.append((layer, anchor))
        if samples + len(times) > spec.budget.max_contact_samples:
            raise c._fail(
                'budget.max_contact_samples',
                samples + len(times),
                f'<= {spec.budget.max_contact_samples}',
                'composition.budget',
            )
        # Each difference is affine between the union of linear anchor keys. Its
        # norm is convex, so testing both endpoints bounds the complete segment.
        for time in sorted(times):
            points = []
            for layer, anchor in resolved:
                temporal = layer.temporal
                source_time = temporal.source_start + (time - temporal.start) * temporal.rate
                frame, scale = poses[layer.id]
                points.append(frame.point(_anchor(anchor, source_time, key_times[id(anchor)]) * scale))
            residual = (points[0] - points[1]).length
            samples += 1
            if residual > contact.tolerance:
                raise c._fail(
                    f'{path}@{time:g}', residual, f'world residual <= {contact.tolerance}', 'composition.contact'
                )
    return samples


def _binding(binding: c.AssetBinding, style: str, *, purpose: str = 'production') -> dict:
    from ._composition_forms import validate

    validate(binding.forms, binding)
    path = f'bindings.{binding.id}'
    if any(a > b for a, b in zip(binding.bounds.minimum, binding.bounds.maximum, strict=True)):
        raise c._fail(path + '.bounds', asdict(binding.bounds), 'ordered source bounds')
    if binding.duration is not None and not 0 < binding.duration <= 600:
        raise c._fail(path + '.duration', binding.duration, 'a finite duration in (0, 600] or static None')
    anchors = _unique(binding.anchors, 'name', path + '.anchors')
    for name, anchor in anchors.items():
        if anchor.keys:
            if binding.duration is None or anchor.keys[0].time != 0 or anchor.keys[0].position != anchor.position:
                raise c._fail(path + f'.anchors.{name}', None, 'a source clock and an initial key matching position')
            if (
                any(a.time >= b.time for a, b in zip(anchor.keys, anchor.keys[1:], strict=False))
                or anchor.keys[-1].time > binding.duration
            ):
                raise c._fail(path + f'.anchors.{name}', None, 'strictly increasing keys within the source duration')
    if binding.backend == 'vector' and binding.plates:
        raise c._fail(path + '.plates', None, 'no renderer jobs for vector source assets', 'composition.capability')
    if binding.backend != 'vector' and not binding.plates:
        raise c._fail(path + '.plates', None, 'explicit bounded render jobs', 'composition.capability')
    for job in binding.plates:
        if not _SHA.fullmatch(job.key):
            raise c._fail(path + '.plates.key', job.key, 'a content SHA-256')
    if binding.candidate is not None:
        from ._composition_review import candidate_identity

        return candidate_identity(binding, style, purpose)
    try:
        version = parts.pin(binding.part, binding.version)
        part = parts.get(binding.part)
    except SrstudioError as error:
        raise c._fail(
            path + '.version', binding.version, 'an approved, verified part version', 'composition.version'
        ) from error
    if part.style and part.style != style:
        raise c._fail(path + '.part', part.style, f'an asset authored for {style}', 'composition.version')
    return {'part': binding.part, 'version': asdict(version)}


def _layer(layer: c.LayerSpec, asset: c.AssetBinding, spec: c.ScenePlan, layers: dict) -> None:
    path, time = f'layers.{layer.id}', layer.temporal
    if layer.version != asset.version:
        raise c._fail(path + '.version', layer.version, asset.version, 'composition.version')
    if not time.start < time.end <= spec.duration:
        raise c._fail(path + '.temporal', asdict(time), 'an ordered interval within the scene', 'composition.clock')
    source_end = time.source_start + (time.end - time.start) * time.rate
    if asset.duration is not None and source_end > asset.duration + 1e-9:
        raise c._fail(path + '.temporal', source_end, f'source end <= {asset.duration}', 'composition.clock')
    if (
        not layer.passes
        or len(set(layer.passes)) != len(layer.passes)
        or not set(layer.passes) <= _PASSES[asset.backend]
    ):
        raise c._fail(path + '.passes', layer.passes, sorted(_PASSES[asset.backend]), 'composition.capability')
    if layer.effects:
        raise c._fail(path + '.effects', layer.effects, 'no undeclared per-layer finish', 'composition.capability')
    if layer.role == 'information' and (
        asset.backend != 'vector' or layer.surface_coordinates != 'local' or layer.space != 'screen'
    ):
        raise c._fail(path, layer.role, 'exact local vector information in screen space', 'composition.capability')
    if layer.parent is not None and layer.parent in layers and layers[layer.parent].space != layer.space:
        raise c._fail(path + '.parent', layer.parent, 'a coordinate frame in the same space', 'composition.reference')
    if asset.forms and (layer.role != 'picture' or layer.space != 'world' or spec.lights.mode != 'lit'):
        raise c._fail(path, None, 'lit world picture layers for authored form shading', 'composition.capability')
    if spec.lights.mode == 'lit' and asset.backend == 'vector' and layer.role != 'information' and not asset.forms:
        raise c._fail(path, asset.backend, 'a backend with a shared-light shading adapter', 'composition.capability')
    if layer.shadow_receiver is not None:
        if layer.shadow_receiver not in layers:
            raise c._fail(
                path + '.shadow_receiver', layer.shadow_receiver, 'an existing receiver', 'composition.reference'
            )
    for other in layer.intersects:
        if other not in layers or other == layer.id:
            raise c._fail(path + '.intersects', other, 'another existing layer', 'composition.reference')
    if layer.intersects or layer.depth == 'split':
        raise c._fail(path + '.depth', layer.depth, 'a proven split-pass composition adapter', 'composition.capability')


def _clocks(spec: c.ScenePlan) -> None:
    states: dict[str, list[c.LayerSpec]] = {}
    for layer in spec.layers:
        if layer.temporal.state:
            _id(layer.temporal.state, f'layers.{layer.id}.temporal.state')
            states.setdefault(layer.temporal.state, []).append(layer)
    for state, layers in states.items():
        layers.sort(key=lambda layer: layer.temporal.start)
        for left, right in zip(layers, layers[1:], strict=False):
            a, b = left.temporal, right.temporal
            if left.asset != right.asset or left.version != right.version:
                raise c._fail(
                    'temporal.state.' + state, right.asset, 'one pinned source performance', 'composition.clock'
                )
            if b.start < a.end:
                raise c._fail('temporal.state.' + state, b.start, 'non-overlapping state windows', 'composition.clock')
            if b.continuity == 'continuous':
                end = a.source_start + (a.end - a.start) * a.rate
                if abs(a.end - b.start) > 1e-9 or abs(end - b.source_start) > 1e-9 or a.rate != b.rate:
                    raise c._fail(
                        'temporal.state.' + state,
                        asdict(b),
                        'an adjacent source clock with equal rate',
                        'composition.clock',
                    )
                if left.transform != right.transform or left.parent != right.parent:
                    raise c._fail(
                        'temporal.state.' + state,
                        None,
                        'continuous world placement or an explicit cut',
                        'composition.clock',
                    )


def preflight(
    spec: c.ScenePlan,
    bindings: tuple[c.AssetBinding, ...],
    *,
    purpose: Literal['production', 'candidate-review'] = 'production',
) -> c.ValidatedScenePlan:
    if type(purpose) is not str or purpose not in ('production', 'candidate-review'):
        raise c._fail('purpose', purpose, 'production or candidate-review', 'composition.candidate')
    if type(spec) is not c.ScenePlan or type(bindings) is not tuple or not 1 <= len(bindings) <= c.MAX_LAYERS:
        raise c._fail('scene/bindings', None, 'a ScenePlan and 1..256 immutable asset bindings')
    if any(type(binding) is not c.AssetBinding for binding in bindings):
        raise c._fail('bindings', None, 'AssetBinding records')
    _graph((spec, bindings), [0])
    if spec.background is not None and not re.fullmatch(r'#[0-9a-fA-F]{6}', spec.background):
        raise c._fail('background', spec.background, 'an opaque #RRGGBB project color or null', 'composition.color')
    if spec.width % 2 or spec.height % 2 or Fraction(spec.fps.numerator, spec.fps.denominator) > 120:
        raise c._fail('scene.frame', (spec.width, spec.height, asdict(spec.fps)), 'even dimensions and fps <= 120')
    if spec.style.revision != style_revision(spec.style.name):
        raise c._fail('style.revision', spec.style.revision, style_revision(spec.style.name), 'composition.version')
    if not 1 <= len(spec.layers) <= c.MAX_LAYERS or len(spec.contacts) > c.MAX_LAYERS:
        raise c._fail('layers/contacts', None, '1..256 layers and at most 256 contacts')
    layers = _unique(spec.layers, 'id', 'layers')
    assets = _unique(bindings, 'id', 'bindings')
    lights = _unique(spec.lights.lights, 'id', 'lights')
    if len(lights) > 16 or bool(lights) != (spec.lights.mode == 'lit'):
        raise c._fail('lights', None, 'no lights for flat mode, or 1..16 lights for lit mode')
    for light in lights.values():
        if not _COLOR.fullmatch(light.color) or (light.kind == 'sphere-area' and light.radius <= 0):
            raise c._fail('lights.' + light.id, asdict(light), 'a hex color and positive area-light radius')
    axes = _camera(spec.camera)
    poses: dict[str, tuple[Frame, float]] = {}
    revisions = []
    used: dict[str, c.AssetBinding] = {}
    candidates: dict[tuple[str, int], c.CandidateSource] = {}
    information_seen = False
    for layer in spec.layers:
        if layer.asset not in assets:
            raise c._fail(f'layers.{layer.id}.asset', layer.asset, 'an existing asset binding', 'composition.reference')
        asset = assets[layer.asset]
        if asset.id not in used:
            revisions.append(_binding(asset, spec.style.name, purpose=purpose))
            if asset.candidate is not None:
                key = (asset.part, asset.version)
                if key in candidates and candidates[key] != asset.candidate:
                    raise c._fail(
                        f'bindings.{asset.id}.candidate',
                        asdict(asset.candidate),
                        'one content identity per candidate part/version; increment the version for changed content',
                        'composition.candidate',
                    )
                candidates[key] = asset.candidate
            used[asset.id] = asset
        _layer(layer, asset, spec, layers)
        if information_seen and layer.role == 'picture':
            raise c._fail('layers', layer.id, 'information above all picture layers', 'composition.capability')
        information_seen |= layer.role == 'information'
        pose = _pose(layer, layers, poses, set())
        _check_camera(layer, asset, pose, spec.camera, axes)
    _clocks(spec)
    contact_samples = _contacts(spec, layers, assets, poses)
    from ._composition_shadows import validate as shadows

    contact_samples += shadows(spec, layers, assets, poses, already=contact_samples)
    jobs: dict[str, c.PlateWork] = {}
    for asset in used.values():
        for job in asset.plates:
            if job.key in jobs and jobs[job.key] != job:
                raise c._fail(
                    'bindings.plates', job.key, 'one work declaration per content key', 'composition.reference'
                )
            jobs[job.key] = job
    # A source job reused at another world pose is another render. The temporal
    # window alone does not change static geometry; identical resolved poses can
    # still share a cold job even when their parent graphs differ.
    render_jobs = {}
    for layer in spec.layers:
        frame, scale = poses[layer.id]
        for job in assets[layer.asset].plates:
            key = _digest(
                {
                    'job': job.key,
                    'pose': _pose_key(frame, scale),
                    'space': layer.space,
                    'backend': assets[layer.asset].backend,
                    'passes': layer.passes,
                }
            )
            render_jobs[key] = job
    frames = math.ceil(Fraction(str(spec.duration)) * Fraction(spec.fps.numerator, spec.fps.denominator))
    pixels = spec.width * spec.height
    nodes = 16 + sum(assets[layer.asset].nodes + 1 for layer in spec.layers)
    cost = c.CostEstimate(
        frames,
        pixels,
        frames * pixels,
        nodes,
        len(render_jobs),
        sum(j.engine_invocations for j in render_jobs.values()),
        sum(j.width * j.height * j.samples for j in render_jobs.values()),
        max((j.bounces for j in jobs.values()), default=0),
        8 * pixels
        + 256 * nodes
        + sum(a.memory_bytes for a in used.values())
        + max((j.memory_bytes for j in jobs.values()), default=0),
        contact_samples,
    )
    metrics = {
        'max_frames': cost.frames,
        'max_frame_pixels': cost.frame_pixels,
        'max_output_pixels': cost.output_pixels,
        'max_nodes': cost.nodes,
        'max_new_plates': cost.unique_plates,
        'max_engine_invocations': cost.engine_invocations,
        'max_samples': cost.samples,
        'max_bounces': cost.bounces,
        'max_memory_bytes': cost.memory_bytes,
    }
    for name, value in metrics.items():
        limit = getattr(spec.budget, name)
        if value > limit:
            raise c._fail('budget.' + name, value, f'<= {limit}', 'composition.budget')
    ordered = tuple(used[name] for name in sorted(used))
    declarations = []
    for asset in ordered:
        declaration = asdict(asset)
        if not asset.forms:
            del declaration['forms']
        if asset.candidate is None:
            del declaration['candidate']  # Preserve pre-review production identities.
        declarations.append(declaration)
    from ._composition_shadows import definition

    identity = {'spec': definition(spec), 'bindings': declarations, 'versions': revisions, 'cost': asdict(cost)}
    if purpose != 'production':
        identity['purpose'] = purpose
    digest = _digest(identity)
    return c.ValidatedScenePlan(spec, ordered, cost, digest, len(spec.contacts), purpose)
