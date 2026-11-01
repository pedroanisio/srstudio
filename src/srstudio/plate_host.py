"""What a host shot on plates needs on a reel's clock: a picture file per drawing, and a frame list turned into gated
layers (ADR 0068, ADR 0072). Who the host is lives in the host's own module; this is the stop-motion clockwork."""

from __future__ import annotations

import os
import shutil
from collections.abc import Hashable, Mapping, Sequence
from pathlib import Path

from .canvas import Canvas
from .head_motion import Channel
from .plates import Patch

__all__ = ["Shelf", "blinks", "gated", "held", "nearest", "runs", "spoken", "value"]


class Shelf:
    """The picture files of one document, under ``assets/<name>`` of ``root``: each copied in once, one image asset."""

    def __init__(self, cv: Canvas, root: Path, name: str) -> None:
        self.cv = cv
        self.name_ = name
        self.folder = Path(root) / "assets" / name
        self.named: dict[Path, str] = {}

    def name(self, path: Path, width: int, height: int) -> str:
        if path in self.named:
            return self.named[path]
        self.folder.mkdir(parents=True, exist_ok=True)
        target = self.folder / path.name
        if not target.exists():
            try:
                os.link(path, target)
            except OSError:
                shutil.copyfile(path, target)
        id = f"{self.name_}-{path.stem[:20]}"
        self.cv.assets.add_image(id=id, src=f"assets/{self.name_}/{path.name}", width=width, height=height)
        self.named[path] = id
        return id


def value(channel: Channel, t: float) -> float:
    """A channel at second ``t``: eased between its keys, which is close enough to the spring for a stepped pose."""
    keys = channel.keys
    if not keys or t <= keys[0][0]:
        return keys[0][1] if keys else 0.0
    for (a, va), (b, vb) in zip(keys, keys[1:], strict=False):
        if t < b:
            x = (t - a) / (b - a)
            return va + (vb - va) * x * x * (3.0 - 2.0 * x)
    return keys[-1][1]


def nearest(wanted: float, steps: Sequence[float]) -> float:
    """The plate step closest to ``wanted``."""
    return min(steps, key=lambda step: abs(step - wanted))


def held(rows: Sequence[tuple[float, str]], t: float, default: str) -> str:
    """The state of a timed list at second ``t``."""
    return next((state for at, state in reversed(rows) if at <= t + 1e-9), default)


def blinks(end: float, fps: int, frames: Sequence[str], every: float, first: float) -> dict[int, str]:
    """The lid of each frame that has a blink on it, on a slow clock from second ``first``."""
    lids: dict[int, str] = {}
    t = first
    while t + len(frames) / fps < end:
        start = round(t * fps)
        lids.update({start + i: lid for i, lid in enumerate(frames)})
        t += every
    return lids


def spoken(mouths: Sequence[tuple[float, str]], end: float, fps: int, hush: float) -> Mapping[int, str]:
    """The mouth on each frame: the track's shape, or ``rest`` once he has been shut for ``hush`` seconds."""
    rows: dict[int, str] = {}
    timed = [*mouths, (end, "closed")]
    for (at, shape), (until, _) in zip(timed, timed[1:], strict=False):
        hushed = shape == "closed" and until - at >= hush
        for frame in range(round(at * fps), round(until * fps)):
            rows[frame] = "rest" if hushed else shape
    return rows


def runs(keys: Sequence[Hashable], fps: int, start: float = 0.0) -> dict[Hashable, list[tuple[float, float]]]:
    """Each key's ``(start, end)`` seconds in a frame list."""
    spans: dict[Hashable, list[tuple[float, float]]] = {}
    begun = 0
    for frame in range(1, len(keys) + 1):
        if frame == len(keys) or keys[frame] != keys[begun]:
            spans.setdefault(keys[begun], []).append((start + begun / fps, start + frame / fps))
            begun = frame
    return spans


def gated(cv: Canvas, parent, shelf: Shelf, picture: Patch, spans: list[tuple[float, float]]) -> None:
    """``picture`` in ``parent``, shown only over ``spans``."""
    g = cv.group(parent, cv.uid(f"{shelf.name_}-plate"), opacity=0.0)
    cv.gate(g, spans)
    name = shelf.name(picture.path, picture.width, picture.height)
    g.add_layer(id=cv.uid(f"{shelf.name_}-layer"), asset=name, x=picture.x, y=picture.y)
