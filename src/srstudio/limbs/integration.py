"""Opt-in typed limb tracks for existing rigs and explicit adapters from legacy pose names."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from ..canvas import Canvas
from .adapters import Appearance, adapter_for
from .compile import BakeOptions, Compiled, LayerTargets, Occlusion, bake, compile_motion
from .correctives import ContourCorrection
from .errors import LimbError
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

    def __post_init__(self) -> None:
        adapter_for(self.style)
        if self.backend not in ("auto", "native", "baked"):
            raise LimbError(f"unknown limb backend {self.backend}")
        if self.backend == "native" and (self.occlusion or self.correctives):
            raise LimbError("native limb tracks do not support separated body/head layers or artist corrections")

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
    name = _LEGACY.get(pose, pose)
    if name not in ACTIONS:
        raise LimbError(f"legacy {style} arm pose {pose!r} has no action mapping")
    return Action(name, start, duration, **options)
