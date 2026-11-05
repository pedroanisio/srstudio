"""Opt-in typed limb tracks for existing rigs and explicit adapters from legacy pose names."""

from __future__ import annotations

from dataclasses import dataclass, field, replace
from typing import Any

from ..canvas import Canvas
from .adapters import Appearance, adapter_for
from .compile import (
    BakeOptions,
    Compiled,
    LayerTargets,
    Occlusion,
    _motion_duration,
    _Preparation,
    _resolve_options,
    bake,
    compile_motion,
)
from .correctives import ContourCorrection
from .errors import LimbError
from .model import label
from .motion import ACTIONS, Action, Motion
from .projection import Camera


@dataclass(frozen=True)
class LimbTrack:
    """One arm's performance in actor-local coordinates; its camera origin is the actor's local shoulder anchor."""

    motion: Motion
    style: str = "cutout"
    camera: Camera = Camera()
    appearance: Appearance = Appearance()
    options: BakeOptions = BakeOptions()
    backend: str = "auto"
    occlusion: tuple[Occlusion, ...] = ()
    correctives: tuple[ContourCorrection, ...] = ()
    deformation: str = "contour"
    _character_end: float | None = field(default=None, repr=False, compare=False)
    _prepared: _Preparation | None = field(default=None, repr=False, compare=False)

    def __post_init__(self) -> None:
        adapter_for(self.style)
        if self.backend not in ("auto", "native", "baked"):
            raise LimbError(f"unknown limb backend {self.backend}")
        if self.backend == "native" and (self.occlusion or self.correctives):
            raise LimbError("native limb tracks do not support separated body/head layers or artist corrections")
        if self.deformation not in ("contour", "skin"):
            raise LimbError(f"unknown limb deformation {self.deformation!r}")
        if self.deformation == "skin" and (self.backend == "baked" or self.occlusion or self.correctives):
            raise LimbError("skin tracks require native planar IK without layered or artist-corrected contours")

    def _source_time(self, time: float, *, end: float) -> float:
        """Map character seconds to the source, holding the first and cropped last poses."""
        return min(_motion_duration(self.motion, self.options, end), max(0, time - self.options.offset))

    def _held_interval(self, start: float, stop: float, *, end: float) -> tuple[float, float] | None:
        """Preimage of a half-open source interval on the cropped, held character clock."""
        limit = _motion_duration(self.motion, self.options, end)
        if start > limit:
            return None
        first = 0.0 if start == 0 else start + self.options.offset
        last = end if stop > limit else min(end, stop + self.options.offset)
        return (first, last) if first < last else None

    def draw(self, cv: Canvas, layers: LayerTargets, *, id: str) -> Compiled:
        if self.occlusion:
            return bake(
                cv,
                layers.body,
                self.motion,
                id=id,
                style=self.style,
                camera=self.camera,
                appearance=self.appearance,
                options=self.options,
                layers=layers,
                occlusion=self.occlusion,
                correctives=self.correctives,
                hold_until=self._character_end,
                _prepared=self._prepared,
            )
        return compile_motion(
            cv,
            layers.body,
            self.motion,
            id=id,
            style=self.style,
            camera=self.camera,
            appearance=self.appearance,
            options=self.options,
            backend=self.backend,
            correctives=self.correctives,
            deformation=self.deformation,
            hold_until=self._character_end,
            _prepared=self._prepared,
        )


_LEGACY = {
    "down": "rest",
    "desk": "rest",
    "lean": "reach",
    "hold": "grasp",
    "face": "facepalm",
    "face2": "facepalm",
    "sigh": "shrug",
    "fist": "grasp",
    "typing": "type",
}


def legacy_action(style: str, pose: str, *, start: float, duration: float, **options: Any) -> Action:
    """Explicitly convert supported old pose names; unsupported poses never silently become an idle hand."""
    adapter_for(style)
    name = _LEGACY.get(label(pose, "legacy arm pose"), pose)
    if name not in ACTIONS:
        raise LimbError(f"legacy {style} arm pose {pose!r} has no action mapping")
    return Action(name, start, duration, **options)


def prepare_tracks(cv: Canvas, tracks: tuple[LimbTrack, ...], end: float) -> tuple[LimbTrack, ...]:
    """Validate a character's replacement tracks, including compilation, before drawing any of its geometry."""
    from sr_core.scene import Scene

    from ..rig import Performance
    from .math3d import number

    Performance(limbs=tracks)
    if number(end, "character end") <= 0:
        raise LimbError("character end must be positive")
    tracks = tuple(
        replace(track, _character_end=end, options=_resolve_options(cv, track.options), _prepared=_Preparation())
        for track in tracks
    )
    for track in tracks:
        duration = _motion_duration(track.motion, track.options, end)
        if track.options.offset + duration > end + 1e-9:
            raise LimbError("limb track exceeds the character performance duration")
    scratch = Canvas(Scene(version="auto"), cv.palette, width=cv.width, height=cv.height, font_asset=cv.font_asset)
    for track in tracks:
        track.draw(
            scratch, LayerTargets(scratch.comp, scratch.comp, scratch.comp), id=f"preflight-{track.motion.arm.side}"
        )
    return tuple(tracks)


_OTHER = {"left": "right", "right": "left"}


@dataclass(frozen=True)
class Facing:
    """How a character shows its own sides on screen; a track's ``left`` or ``right`` is always anatomical.

    Motions reach outward toward +x with the right arm and mirror a left arm's goals to -x. A profile character
    (``front=False``) faces +x, so its near arm is its right. There x is forward, not sideways, so a left track is
    reflected about its shoulder origin and both arms reach forward; the far arm draws behind the torso. A
    ``front`` character faces the viewer, so its right arm is on screen-left: each of its tracks is reflected about
    its shoulder origin. ``flip`` mirrors the character's group. A profile character then faces -x and its far arm
    is its right. A front character's tracks are mirrored back about local x = 0, so they stay on its anatomical
    side; a builder that flips a front character keeps its centre line there.
    """

    front: bool
    flip: bool = False

    def slot(self, side: str) -> str:
        """The builder's own name for the arm on anatomical ``side``: front builders name arms by screen side
        before any flip; a profile builder names its far arm left and its near arm right."""
        return _OTHER[side] if self.front != self.flip else side

    def slots(self, tracks: tuple[LimbTrack, ...]) -> frozenset[str]:
        return frozenset(self.slot(track.motion.arm.side) for track in tracks)

    def layers(self, cv: Canvas, layers: LayerTargets, track: LimbTrack) -> LayerTargets:
        """``layers`` for one track, wrapped so its arm lands on the character's anatomical side. A profile
        character's far arm draws its body layer behind the torso, like the legacy far arm it replaces."""
        x = track.camera.origin[0]
        if not self.front:
            if self.slot(track.motion.arm.side) == "left":
                layers = LayerTargets(layers.behind, layers.behind, layers.front)
            if track.motion.arm.side == "right":
                return layers
            # Undo the left arm's sideways mirror, which in profile would point it backward.
            reflect = {"x": 2 * x, "scaleX": -1}
            return _wrapped(cv, layers, reflect)
        # Unflipped: reflect about the shoulder, x -> 2x0 - x. Flipped: that reflection followed by the mirror back
        # about the centre line, x -> x - 2x0, so the flipped group draws the arm on screen-left with no reflection.
        transform = {"x": -2 * x} if self.flip else {"x": 2 * x, "scaleX": -1}
        return _wrapped(cv, layers, transform)


def _wrapped(cv: Canvas, layers: LayerTargets, transform: dict[str, float]) -> LayerTargets:
    return LayerTargets(
        *(cv.group(layer, cv.uid("g"), **transform) for layer in (layers.behind, layers.body, layers.front))
    )


def draw_tracks(
    cv: Canvas, layers: LayerTargets, tracks: tuple[LimbTrack, ...], *, id: str, facing: Facing
) -> tuple[Compiled, ...]:
    """Draw validated tracks into a character's ordered layers in its own coordinate system, each on the
    anatomical side ``facing`` shows."""
    return tuple(
        track.draw(cv, facing.layers(cv, layers, track), id=f"{id}-{track.motion.arm.side}") for track in tracks
    )
