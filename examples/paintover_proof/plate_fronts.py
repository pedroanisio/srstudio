#!/usr/bin/env python3
"""The front plates: the back plate's own pixels where the seat and arm stand in front of the rigs' plane, inked round.

    python plate_fronts.py PROJECT      # every near picture under PROJECT/plates → its front picture

The back plate holds the whole sofa. A front plate repeats the part of it nearer the camera than the rigs, so a rig is
hidden by exactly that. The cut is a line in the picture, as the seat's edge is in the approved set: where the shape is
the sofa's own outline the line falls on the ink already there, and where it crosses the seat or the arm it is what a
rig sits behind. Runs in srstudio's interpreter: srlocations' has no Pillow.
"""

import os
import sys
from pathlib import Path

import numpy as np
from PIL import Image
from scipy.ndimage import distance_transform_edt

os.umask(0o077)  # generated outputs are private: folders 700, files 600

LINE = 8.0  # px, the width of the cut's line: the heavy ink's


def front_of(back: np.ndarray, near: np.ndarray) -> np.ndarray:
    """`back` (RGBA) where `near`'s alpha is solid, with a black line of width LINE along that shape's edge."""
    shape = near >= 128
    edge = distance_transform_edt(shape) - distance_transform_edt(~shape)
    line = np.clip(LINE / 2 + 0.5 - np.abs(edge), 0.0, 1.0)
    out = back.astype(float)
    out[..., :3] *= 1.0 - line[..., None]
    out[..., 3] = np.maximum(np.where(shape, back[..., 3], 0.0), line * 255.0)
    return out.round().astype(np.uint8)


def main(argv: list[str]) -> None:
    plates = Path(argv[1]).resolve() / "plates"
    done = 0
    for near in (p for p in plates.rglob("*.png") if "near" in p.relative_to(plates).as_posix()):
        rest = near.relative_to(plates).as_posix()
        back = plates / rest.replace("near", "back")
        front = plates / rest.replace("near", "front")
        front.parent.mkdir(parents=True, exist_ok=True)
        picture = front_of(
            np.asarray(Image.open(back).convert("RGBA")), np.asarray(Image.open(near).convert("RGBA"))[..., 3]
        )
        Image.fromarray(picture).save(front, compress_level=1)
        done += 1
    print(f"{done} front plates")


if __name__ == "__main__":
    main(sys.argv)
