"""Bounded deterministic baking of spatial limb performance into ordinary scene-render vector groups."""

from __future__ import annotations

import fnmatch
import math
import re
from copy import deepcopy
from dataclasses import dataclass, field, replace
from fractions import Fraction
from typing import Any

from ..canvas import Canvas
from .adapters import Appearance, adapter_for
from .correctives import ContourCorrection
from .errors import Diagnostic, LimbError
from .geometry import Part, ProjectedPose, project_pose, ribbon
from .math3d import number
from .motion import Motion, Sample, sample_motion
from .projection import Affine, Camera
from .validation import MotionReport, QualityProfile, audit, motion_diagnostics

_CAMERA = Camera()
_APPEARANCE = Appearance()
_PARENT = Affine()


def _scene_time(time: float) -> float:
    """Quantize an absolute scene time before emission so exact frame samples see the new pose."""
    return math.floor(time * 1e6 + 1e-9) / 1e6


def _check_id(cv: Canvas, id: str) -> None:
    if not isinstance(id, str) or not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_.-]*", id):
        raise LimbError("a compiled limb ID must be an XML name")
    existing = {str(n.attributes().get("id", "")) for n in cv.scene.iter()}
    if any(name == id or name.startswith(id + "-") for name in existing):
        raise LimbError(f"compiled limb ID namespace {id!r} is already in use")


@dataclass(frozen=True)
class BakeOptions:
    fps: int | None = None
    duration: float | None = None
    offset: float = 0.0
    max_frames: int = 2400
    max_nodes: int = 500000
    quality: QualityProfile | None = None

    def __post_init__(self) -> None:
        if self.quality is not None and not isinstance(self.quality, QualityProfile):
            raise LimbError('quality must be a QualityProfile')
        for name, high in (("fps", 120), ("max_frames", 100000), ("max_nodes", 10000000)):
            value = getattr(self, name)
            if name == "fps" and value is None:
                continue
            if isinstance(value, bool) or not isinstance(value, int) or not 1 <= value <= high:
                raise LimbError(f"{name} must be an integer in 1..{high}")
        if self.duration is not None and number(self.duration, "bake duration") <= 0:
            raise LimbError("bake duration must be positive")
        if number(self.offset, "bake offset") < 0:
            raise LimbError("bake offset must be non-negative")
        if math.ulp(self.offset) > 1e-6 or self.offset + 1 / (self.fps or 120) <= self.offset:
            raise LimbError("bake offset cannot represent a frame interval")


def _resolve_options(cv: Canvas, options: BakeOptions | None) -> BakeOptions:
    options = options or BakeOptions()
    if options.fps is not None:
        return options
    project = next(cv.scene.iter("project"), None)
    fps_value = project.attributes().get("fps") if project is not None else None
    if not fps_value:
        return replace(options, fps=24)
    try:
        fps = Fraction(str(fps_value))
    except (ValueError, ZeroDivisionError) as exc:
        raise LimbError("scene fps is invalid; supply an integer BakeOptions(fps=...)") from exc
    if fps.denominator != 1 or not 1 <= fps.numerator <= 120:
        raise LimbError("scene fps is not a supported integer; supply BakeOptions(fps=...) explicitly")
    return replace(options, fps=fps.numerator)


def _frame_count(duration: float, options: BakeOptions) -> int:
    """Bound work before multiplication, and reject intervals the six-decimal scene clock cannot represent.

    This is the only frame-budget check: refusing ``duration > max_frames / fps`` leaves at most ``max_frames``.
    """
    duration = number(duration, "resolved bake duration")
    if duration <= 0:
        raise LimbError("resolved bake duration must be positive")
    if options.fps is None:
        raise LimbError("bake fps must be resolved against a scene")
    if duration > options.max_frames / options.fps:
        raise LimbError("limb frame budget exceeded", code="budget")
    count = max(1, math.ceil(duration * options.fps - 1e-9))
    start = options.offset + (count - 1) / options.fps
    end = options.offset + duration
    if not math.isfinite(end) or math.ulp(end) > 1e-6 or math.floor(start * 1e6 + 1e-9) >= math.floor(end * 1e6 + 1e-9):
        raise LimbError("bake interval cannot be represented at the scene clock resolution")
    return count


def _motion_duration(motion: Motion, options: BakeOptions, hold_until: float | None) -> float:
    if options.duration is not None:
        return options.duration
    root_end = motion.root.keys[-1].time
    if hold_until is not None:
        root_end = min(root_end, hold_until - options.offset)
    return max([root_end, *(a.end for a in motion.actions), *(a.release for a in motion.attachments)]) or 1.0


@dataclass(frozen=True)
class LayerTargets:
    behind: Any
    body: Any
    front: Any


@dataclass(frozen=True)
class Occlusion:
    part: str
    start: float
    end: float
    layer: str = "body"
    visible: bool = True

    def __post_init__(self) -> None:
        if not self.part or self.layer not in ("behind", "body", "front"):
            raise LimbError("occlusion needs a part pattern and behind, body or front layer")
        if not 0 <= number(self.start, "occlusion start") < number(self.end, "occlusion end"):
            raise LimbError("occlusion times must be ordered and non-negative")
        if not isinstance(self.visible, bool):
            raise LimbError("occlusion visibility must be boolean")


@dataclass(frozen=True)
class Compiled:
    roots: tuple[Any, ...]
    frames: int
    backend: str
    report: MotionReport
    diagnostics: tuple[Diagnostic, ...] = ()


@dataclass(frozen=True)
class _BakePlan:
    samples: tuple[Sample, ...]
    poses: tuple[ProjectedPose, ...]
    assignments: tuple[dict[str, set[str]], ...]
    report: MotionReport
    diagnostics: tuple[Diagnostic, ...]


@dataclass
class _Preparation:
    """Build-local numeric preparation, reusable across preflight and emission; never owns scene nodes."""

    snapshot: tuple | None = None
    samples: dict[float, Sample] = field(default_factory=dict)
    poses: dict[float, ProjectedPose] = field(default_factory=dict)
    plans: dict[tuple, _BakePlan] = field(default_factory=dict)

    def configure(
        self,
        motion: Motion,
        camera: Camera,
        parent: Affine,
        correctives: tuple,
        options: BakeOptions,
        hold_until: float | None,
    ) -> None:
        inputs = (motion, camera, parent, correctives, options, hold_until)
        if self.snapshot != inputs:
            self.snapshot = deepcopy(inputs)
            self.samples.clear()
            self.poses.clear()
            self.plans.clear()

    def sample(self, motion: Motion, time: float, *, track: str) -> Sample:
        if time not in self.samples:
            self.samples[time] = sample_motion(motion, time, track=track)
        return self.samples[time]

    def project(
        self, motion: Motion, sample: Sample, camera: Camera, parent: Affine, correctives: tuple
    ) -> ProjectedPose:
        if sample.time not in self.poses:
            self.poses[sample.time] = project_pose(
                sample,
                camera,
                width=motion.arm.width,
                parent=parent,
                thickness=motion.hand.thickness,
                correctives=correctives,
            )
        return self.poses[sample.time]


def bake(
    cv: Canvas,
    parent: Any,
    motion: Motion,
    *,
    id: str,
    style: str = "toon",
    camera: Camera = _CAMERA,
    appearance: Appearance = _APPEARANCE,
    options: BakeOptions | None = None,
    parent_transform: Affine = _PARENT,
    layers: LayerTargets | None = None,
    occlusion: tuple[Occlusion, ...] = (),
    correctives: tuple[ContourCorrection, ...] = (),
    hold_until: float | None = None,
    _prepared: _Preparation | None = None,
) -> Compiled:
    """Validate all samples before writing groups. Each sample is held only on its own frame interval.

    Geometry is projected once with ``camera`` and then taken through ``parent_transform.inverse()``. The caller
    supplies the actual drawing parent's world transform when it is not identity. Layer targets must share it.
    Occlusion rules override anatomy by part name/glob, in declaration order; hidden parts are counted in the report.
    ``hold_until`` extends the first and last poses across the character lifetime, in scene seconds.
    """
    options = _resolve_options(cv, options)
    prepared = _prepared if _prepared is not None else _Preparation()
    prepared.configure(motion, camera, parent_transform, correctives, options, hold_until)
    assert options.fps is not None
    _check_id(cv, id)
    adapter = adapter_for(style)
    if camera.projection == "perspective" and not adapter.capabilities.perspective:
        raise LimbError(f"adapter {style} does not support perspective")
    if len(motion.hand.digits) > 1 and not adapter.capabilities.articulated_digits:
        raise LimbError(f"adapter {style} does not support articulated digits")
    if "contour" not in adapter.capabilities.deformation:
        raise LimbError(f"adapter {style} does not support contour deformation")
    duration = _motion_duration(motion, options, hold_until)
    count = _frame_count(duration, options)
    if hold_until is not None and number(hold_until, "limb hold end") < options.offset + duration:
        raise LimbError("limb hold end must include the motion interval")
    trailing = hold_until is not None and hold_until > options.offset + duration
    if count + int(trailing) > options.max_frames:
        raise LimbError("limb frame budget exceeded", code="budget")
    # A conservative bound on built-in adapters: group, visibility keys, contours, details and paints in three slots.
    estimate = (count + int(trailing)) * (24 + 12 * len(motion.hand.digits)) * 3
    if estimate > options.max_nodes:
        raise LimbError(f"limb bake budget exceeded: {count} frames, at most {estimate} nodes", code="budget")
    plan_key = (options, hold_until, tuple(occlusion))
    plan = prepared.plans.get(plan_key)
    if plan is None:
        times = tuple(i / options.fps for i in range(count)) + ((duration,) if trailing else ())
        samples = tuple(prepared.sample(motion, t, track=id) for t in times)
        poses = tuple(prepared.project(motion, s, camera, parent_transform, correctives) for s in samples)
        names = {p.name for pose in poses for p in pose.parts}
        for rule in occlusion:
            if rule.end > duration + 1e-9 or not any(fnmatch.fnmatchcase(name, rule.part) for name in names):
                raise LimbError(f"occlusion part {rule.part!r} does not resolve or its time exceeds the bake")
        report = audit(samples, poses, motion.arm, quality=options.quality)
        assignments_list = []
        hidden = 0
        for pose in poses:
            slots: dict[str, set[str]] = {"behind": set(), "body": set(), "front": set()}
            for part in pose.parts:
                destination, visible = "body", True
                for rule in occlusion:
                    active = rule.start <= pose.time < rule.end or (trailing and pose.time == duration == rule.end)
                    if active and fnmatch.fnmatchcase(part.name, rule.part):
                        destination, visible = rule.layer, rule.visible
                if visible:
                    slots[destination].add(part.name)
                else:
                    hidden += 1
            assignments_list.append(slots)
        plan = _BakePlan(
            samples,
            poses,
            tuple(assignments_list),
            replace(report, hidden_parts=hidden),
            motion_diagnostics(samples) + tuple(f.diagnostic() for f in report.quality_findings),
        )
        prepared.plans[plan_key] = plan
    samples, poses, assignments = plan.samples, plan.poses, plan.assignments
    before = sum(1 for _ in cv.scene.iter())
    layers = layers or LayerTargets(parent, parent, parent)
    roots = {}
    for layer in ("behind", "body", "front"):
        if any(slots[layer] for slots in assignments):
            roots[layer] = cv.group(getattr(layers, layer), id if layer == "body" else f"{id}-{layer}")
    for i, (pose, slots) in enumerate(zip(poses, assignments, strict=True)):
        if i == count:
            assert hold_until is not None
            start, end = options.offset + duration, hold_until
        else:
            start, end = i / options.fps + options.offset, min(duration, (i + 1) / options.fps) + options.offset
            if i == 0 and hold_until is not None:
                start = 0
        # Canvas keys store six decimals. Flooring shared boundaries prevents a rounded-up start from showing
        # the previous drawing when the engine samples an exact rational frame time such as 2/12 seconds.
        start, end = _scene_time(start), _scene_time(end)
        for layer, names_in_layer in slots.items():
            if not names_in_layer:
                continue
            group = cv.group(roots[layer], f"{id}-frame-{i:06d}-{layer}")
            cv.gate(group, [(start, end)])
            adapter.draw(cv, group, pose.select(names_in_layer), appearance, id=f"{id}-drawing-{i:06d}-{layer}")
    nodes = sum(1 for _ in cv.scene.iter()) - before
    report = replace(plan.report, nodes=nodes)
    return Compiled(tuple(roots.values()), len(samples), "baked", report, plan.diagnostics)


def compile_motion(
    cv: Canvas,
    parent: Any,
    motion: Motion,
    *,
    id: str,
    backend: str = "auto",
    style: str = "toon",
    camera: Camera = _CAMERA,
    appearance: Appearance = _APPEARANCE,
    options: BakeOptions | None = None,
    parent_transform: Affine = _PARENT,
    layers: LayerTargets | None = None,
    occlusion: tuple[Occlusion, ...] = (),
    correctives: tuple[ContourCorrection, ...] = (),
    deformation: str = "contour",
    hold_until: float | None = None,
    _prepared: _Preparation | None = None,
) -> Compiled:
    """Use native two-bone IK for strictly planar arms; bake spatial requests with an explicit selection diagnostic.

    Native mode uses the engine for the two arm segments and baked spatial contours for articulated fingers.
    Arm and shoulder keys hold between bake frames to stay aligned with the held hand contours.
    No joint-limit solver is duplicated in the engine: its target/pole are the validated canonical wrist/elbow.
    Hand and arm positions therefore share the same contract, including explicit reach-clamping diagnostics.
    """
    if backend not in ("auto", "native", "baked"):
        raise LimbError(f"unknown limb backend {backend!r}")
    if deformation not in ("contour", "skin"):
        raise LimbError(f"unknown limb deformation {deformation!r}", code="capability")
    if deformation == "skin" and backend == "baked":
        raise LimbError("skin deformation requires native planar IK", code="capability")
    _check_id(cv, id)
    prepared = _prepared if _prepared is not None else _Preparation()
    options = _resolve_options(cv, options)
    prepared.configure(motion, camera, parent_transform, correctives, options, hold_until)
    assert options.fps is not None
    if backend == "baked":
        return bake(
            cv,
            parent,
            motion,
            id=id,
            style=style,
            camera=camera,
            appearance=appearance,
            options=options,
            parent_transform=parent_transform,
            layers=layers,
            occlusion=occlusion,
            correctives=correctives,
            hold_until=hold_until,
            _prepared=prepared,
        )
    duration = _motion_duration(motion, options, hold_until)
    count = _frame_count(duration, options)
    if count * (24 + 12 * len(motion.hand.digits)) * 3 + 128 > options.max_nodes:
        raise LimbError("native limb budget exceeded", code="budget")
    adapter = adapter_for(style)
    if deformation == "skin" and "skin" not in adapter.capabilities.deformation:
        raise LimbError(f"adapter {style} does not support skin deformation", code="capability")
    samples = tuple(prepared.sample(motion, min(duration, i / options.fps), track=id) for i in range(count + 1))
    planar = camera.projection == "orthographic" and parent_transform == _PARENT and layers is None
    for s in samples:
        a, b, c = (camera.project(p).xy for p in (s.arm.shoulder, s.arm.elbow, s.arm.wrist))
        planar = planar and abs(math.dist(a, b) - motion.arm.upper * camera.scale) < 1e-6
        planar = planar and abs(math.dist(b, c) - motion.arm.forearm * camera.scale) < 1e-6
    planar = planar and not any(fnmatch.fnmatchcase(p, rule.part) for p in ("upper", "forearm") for rule in occlusion)
    planar = planar and adapter.capabilities.native_planar and not correctives
    if not planar:
        if backend == "native" or deformation == "skin":
            raise LimbError(
                "native limb compilation requires a planar arm, orthographic camera "
                "and a common untransformed drawing parent without artist contour corrections",
                code="capability",
            )
        result = bake(
            cv,
            parent,
            motion,
            id=id,
            style=style,
            camera=camera,
            appearance=appearance,
            options=options,
            parent_transform=parent_transform,
            layers=layers,
            occlusion=occlusion,
            correctives=correctives,
            hold_until=hold_until,
            _prepared=prepared,
        )
        return replace(
            result,
            diagnostics=(Diagnostic("backend", "spatial, layered or corrected request uses baked contours"),)
            + result.diagnostics,
        )
    # Preflight the entire baked hand, including budget, IDs, styles and occlusion, in an isolated scene.
    from sr_core.scene import Scene

    scratch = Canvas(Scene(version="auto"), cv.palette, font_asset=None)
    hidden = (Occlusion("upper", 0, duration, visible=False), Occlusion("forearm", 0, duration, visible=False))
    bake(
        scratch,
        scratch.comp,
        motion,
        id=id,
        style=style,
        camera=camera,
        appearance=appearance,
        options=options,
        occlusion=hidden + occlusion,
        hold_until=hold_until,
        _prepared=prepared,
    )
    before = sum(1 for _ in cv.scene.iter())
    root = cv.group(parent, id)
    cv.gate(
        root,
        [
            (
                _scene_time(0 if hold_until is not None else options.offset),
                _scene_time(hold_until or options.offset + duration),
            )
        ],
    )
    target = cv.group(root, f"{id}-target")
    pole = cv.group(root, f"{id}-pole")
    times = tuple(_scene_time(options.offset + min(duration, i / options.fps)) for i in range(count + 1))
    for node, attribute in ((target, "wrist"), (pole, "elbow")):
        points = [camera.project(getattr(s.arm, attribute)).xy for s in samples]
        for axis, index in (("x", 0), ("y", 1)):
            cv.keys(node, axis, [(time, p[index]) for time, p in zip(times, points, strict=True)], hold=True)
    skeleton = root.add_skeleton(id=f"{id}-skeleton")
    upper = skeleton.add_bone(id=f"{id}-upper", length=motion.arm.upper * camera.scale)
    skeleton.add_bone(
        id=f"{id}-forearm", parent=upper.id, x=motion.arm.upper * camera.scale, length=motion.arm.forearm * camera.scale
    )
    skeleton.add_transformConstraint(type="ik", target=target.id, pole=pole.id, softness=0)
    shoulders = [camera.project(s.arm.shoulder).xy for s in samples]
    for axis, index in (("x", 0), ("y", 1)):
        cv.keys(upper, axis, [(time, p[index]) for time, p in zip(times, shoulders, strict=True)], hold=True)
    segments = (
        ()
        if deformation == "skin"
        else (("upper", motion.arm.upper, (1.2, 1.0)), ("forearm", motion.arm.forearm, (1.0, 0.72)))
    )
    if deformation == "skin":
        # Keep intermediate rest vertices: older renderers do not adaptively subdivide skin-deformed edges.
        bind_points = tuple((motion.arm.upper * camera.scale * i / 8, 0.0) for i in range(9)) + tuple(
            ((motion.arm.upper + motion.arm.forearm * i / 8) * camera.scale, 0.0) for i in range(1, 9)
        )
        sizes = tuple(motion.arm.width * camera.scale * (1.2 - 0.2 * i / 8) for i in range(9)) + tuple(
            motion.arm.width * camera.scale * (1 - 0.28 * i / 8) for i in range(1, 9)
        )
        part = Part(
            "sleeve", ribbon(bind_points, sizes), bind_points, 0, sum(sizes) / len(sizes), "sleeve", authored=True
        )
        pose = ProjectedPose((part,), bind_points[0], bind_points[8], bind_points[-1], (), "palm", 0)
        drawing = adapter.draw(cv, root, pose, appearance, id=f"{id}-sleeve-drawing")
        for shape in drawing.iter("shape"):
            shape.add_deform().add_modifier(type="skin", skeleton=f"{id}-skeleton")
    for name, length, widths in segments:
        group = cv.group(root, f"{id}-{name}-draw")
        group.add_transformConstraint(type="copy-transform", target=f"{id}-{name}")
        strip_points = ((0.0, 0.0), (length * camera.scale, 0.0))
        sizes = tuple(motion.arm.width * camera.scale * w for w in widths)
        part = Part(name, ribbon(strip_points, sizes), strip_points, 0, sum(sizes) / 2, "sleeve")
        pose = ProjectedPose((part,), strip_points[0], strip_points[0], strip_points[-1], (), "palm", 0)
        adapter.draw(cv, group, pose, appearance, id=f"{id}-{name}-drawing")
    result = bake(
        cv,
        root,
        motion,
        id=f"{id}-hand",
        style=style,
        camera=camera,
        appearance=appearance,
        options=options,
        occlusion=hidden + occlusion,
        hold_until=hold_until,
        _prepared=prepared,
    )
    nodes = sum(1 for _ in cv.scene.iter()) - before
    report = replace(result.report, hidden_parts=max(0, result.report.hidden_parts - 2 * result.frames), nodes=nodes)
    return Compiled(
        (root,), result.frames, "native-skin" if deformation == "skin" else "native", report, result.diagnostics
    )
