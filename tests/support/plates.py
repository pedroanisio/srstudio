"""A small plate, plain and printed, for the plate tests."""

from __future__ import annotations

from dataclasses import replace

from srstudio import clay, plates
from srstudio.plates import Camera, Material, Placed, Plate


def plate(size=(10.0, 10.0, 10.0), rotation=0.0, background=plates.CLEAR) -> Plate:
    m = clay.Model()
    m.box("clay", (0, 0, 0), size)
    return Plate(
        64,
        64,
        Camera((0.0, 0.0, -200.0), (0.0, 0.0, 0.0), 20.0),
        plates.stage_lights(),
        (Placed(m.meshes(), rotation_y=rotation),),
        (Material("clay", "#C88762"),),
        background,
    )


def printed_plate():
    text = plates.Print('#FFFFFF', 64, 64, (plates.Line('OK', 32, 32, 12, '#000000'),))
    original = plate()
    return replace(original, materials=(replace(original.materials[0], print=text),))
