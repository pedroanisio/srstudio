"""Placement geometry shared by Collage group shots and photo contracts without build imports."""

from __future__ import annotations

from dataclasses import dataclass

from . import collage

FRAME_H = 1920.0  # a scaled bust keeps its cut-off bottom on its place's base


@dataclass(frozen=True)
class Place:
    """Where one character stands in the group: its centre line at ``x``, the bottom of its bust on ``base`` (frame
    pixels; the frame's bottom is :data:`FRAME_H`), drawn at ``scale`` of its single-shot size."""

    x: float
    base: float
    scale: float

    def transform(self) -> tuple[float, float]:
        """The offset of the character's group: its single-shot drawing moved and scaled into this place."""
        return self.x - collage.CX * self.scale, self.base - FRAME_H * self.scale

    def seen(self, point: collage.Point) -> collage.Point:
        """Where ``point`` of the single-shot drawing lands on screen in this place."""
        x, y = self.transform()
        return x + point[0] * self.scale, y + point[1] * self.scale


# Keep the established public record name, including existing and newly written pickles.
Place.__module__ = 'srstudio.collage_group'
