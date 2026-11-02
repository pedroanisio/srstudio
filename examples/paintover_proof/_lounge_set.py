"""The lounge as numbers, shared by the plate script (srlocations' interpreter) and the study (srstudio's): no import
from either, so a test can hold the palette to the Toon set it copies and the plate names to what the study reads.

Colours are `toon-lounge`, `toon-sofa` and `toon-sofa-back` at the versions the release pins. Metres: x right, y up,
z away, with the sofa's right outer side at x = 0 and its front at z = 0.
"""

import subprocess
from math import cos, pi
from pathlib import Path

SRLOCATIONS_COMMIT = (
    "8dfe7a19d111763f321e72a8dafb1015ada0617a"  # the plates are this code's; the plate script refuses any other
)
WIDTH, HEIGHT = 1080, 1920
LAYERS = (
    "far",
    "back",
    "near",
)  # what the plate script renders; plate_fronts.py cuts the front plate from the last two
RIG_Z = 0.3  # the plane the rigs sit on: the seat's middle, in metres

# the camera: same side of the sofa as the approved shot, framed to its rows (arm top 1130, seat 1310, feet 1680)
EYE = (-0.29, 0.72, -3.0)
LOOK_AT = (-0.29, 0.855, 0.0)
LENS = 31.0  # a portrait frame fits the gate to its height: 80 px per mm at 1920

# what the two cameras agree on: metres in the room, frame pixels on the reel's own close-ups
CLOSE_RATIO = 1 / 0.66  # the reel's close-up rig at scale 1.0 over its two-shot rig at PAIR_SCALE
CLOSE_LENS, CLOSE_RISE = 31.0, 0.02
BRUNO_YAW, MAE_YAW = (
    -16.0,
    16.0,
)  # degrees round the rig: the camera stands off the side that keeps the other rig's seat
RIG_MAE, RIG_BRUNO = (-0.808, 0.6, 0.3), (-0.391, 0.6, 0.3)  # where each rig sits, on the plane of the seat's middle
SEAT_MAE, SEAT_BRUNO = (-0.808, 0.374, 0.3), (-0.391, 0.374, 0.3)  # where each rig meets the seat
MAE_FRAME, BRUNO_FRAME = (297.0, 1311.0), (423.0, 1311.0)  # where the reel's close-ups put that point
RIG_MIDDLE = (-0.6, 0.374, 0.3)
CACTUS, CODE = (0.26, 0.35, 0.16), (0.34, 0.255, 0.02)  # the signature marks' places on the side table
TRACKS = {"mae": (-0.808, 0.374, 0.3), "bruno": (-0.391, 0.374, 0.3)}
TRACK_COLOURS = {"mae": "#ff00ff", "bruno": "#00ffff"}
TRACK_RADIUS = 0.012

PUSH_FPS, PUSH_FRAMES = 24, 110  # 0.000 to 4.583 s: the opening two-shot, whole, up to the cut to her close-up
PUSH_SCALE = 1.3  # how much the rigs' depth grows over the move


def magnification(frame: int) -> float:
    """The push at a frame, the same curve for the 3D camera and the 2D `camera.push_in`: a sine ease from 1."""
    t = frame / (PUSH_FRAMES - 1)
    return 1.0 + (PUSH_SCALE - 1.0) * (1.0 - cos(pi * t)) / 2.0


def plate(take: str, layer: str) -> str:
    """A still plate's path under plates/: the two-shot keeps the proof's names."""
    return f"{layer}.png" if take == "two" else f"{take}/{layer}.png"


def push_plate(frame: int, layer: str) -> str:
    return f"push/{layer}/{frame:04d}.png"


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
SPEAKER_CAP = "#2b2d35"  # the speaker's lid: toon_everyday.CAP


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
