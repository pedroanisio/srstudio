"""Opt-in typed limb tracks for existing rigs and explicit adapters from legacy pose names."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from ..canvas import Canvas
from .adapters import Appearance, adapter_for
from .compile import BakeOptions, Compiled, LayerTargets, Occlusion, bake, compile_motion
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
    for track in tracks:
        duration = track.options.duration or max((a.end for a in track.motion.actions), default=1.0)
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

    Motions reach outward toward +x with the right arm. A profile character (``front=False``) faces +x, so its near
    arm is its right. A ``front`` character faces the viewer, so its right arm is on screen-left: each of its tracks
    is reflected about its shoulder origin. ``flip`` mirrors the character's group. A profile character then faces
    -x and its far arm is its right. A front character's tracks are mirrored back about local x = 0, so they stay on
    its anatomical side; a builder that flips a front character keeps its centre line there.
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
        """``layers`` for one track, wrapped so its arm lands on the character's anatomical side."""
        if not self.front:
            return layers
        x = track.camera.origin[0]
        # Unflipped: reflect about the shoulder, x -> 2x0 - x. Flipped: that reflection followed by the mirror back
        # about the centre line, x -> x - 2x0, so the flipped group draws the arm on screen-left with no reflection.
        transform = {"x": -2 * x} if self.flip else {"x": 2 * x, "scaleX": -1}
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
