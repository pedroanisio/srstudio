"""The lounge as numbers, shared by the plate script (srlocations' interpreter) and the study (srstudio's): no import
from either, so a test can hold the palette to the Toon set it copies and the plate names to what the study reads.

Colours are `toon-lounge`, `toon-sofa` and `toon-sofa-back` at the versions the release pins. Metres: x right, y up,
z away, with the sofa's right outer side at x = 0 and its front at z = 0.
"""

import subprocess
from pathlib import Path

SRLOCATIONS_COMMIT = (
    "8dfe7a19d111763f321e72a8dafb1015ada0617a"  # the plates are this code's; the plate script refuses any other
)
WIDTH, HEIGHT = 1080, 1920
LAYERS = ("far", "back", "front")  # bottom first; the rigs draw between back and front

# the camera: same side of the sofa as the approved shot, framed to its rows (arm top 1130, seat 1310, feet 1680)
EYE = (-0.29, 0.72, -3.0)
LOOK_AT = (-0.29, 0.855, 0.0)
LENS = 31.0  # a portrait frame fits the gate to its height: 80 px per mm at 1920

WALL_TOP, WALL_MID, WALL_LOW = "#1d3b4f", "#24526a", "#2f6a80"
STRIPE = "#3a7590"
SOFA, SOFA_DARK, SOFA_DEEP = "#7a4a7e", "#663d6a", "#4f2e53"
SOFA_LIGHT, SOFA_SEAM = "#946098", "#5e3762"
PILLOW = "#e6b450"
TABLE, TABLE_DARK, TABLE_LEG = "#d9a066", "#b67f4a", "#8a5c33"
FLOOR, FLOOR_LINE = "#8a5a3c", "#6f4630"
RUG, RUG_BAND = "#b5413f", "#e6b450"
SHELF, ROUTER, ROUTER_LED = "#c48a5a", "#2b2f38", "#5cff8a"
LAMP_POLE, LAMP_SHADE = "#3a3a46", "#c9b78f"
CONSOLE = "#6b4a3a"
SPEAKER = "#d8dde6"


class PinError(RuntimeError):
    """The srlocations in use is not the code the plates are pinned to."""


def pinned(package: Path) -> str:
    """The commit of the srlocations package at `package`. It must be the pinned one with its package folder unedited,
    so a plate can be traced to the code that made it."""

    def git(*words: str) -> str:
        return subprocess.run(
            ["git", "-C", str(package), *words], capture_output=True, text=True, check=True
        ).stdout.strip()

    commit = git("rev-parse", "HEAD")
    if commit != SRLOCATIONS_COMMIT:
        raise PinError(f"srlocations is at {commit}; these plates are pinned to {SRLOCATIONS_COMMIT}")
    edited = git("status", "--porcelain", "--", ".")
    if edited:
        raise PinError(f"srlocations at the pinned commit has uncommitted edits in its package:\n{edited}")
    return commit
