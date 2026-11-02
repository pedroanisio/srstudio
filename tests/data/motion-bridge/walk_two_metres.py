"""A mannequin walking two metres straight ahead in two seconds: the motion bridge's walk fixture (ADR 0187).

An srlocations location module, run only by ``tools/motion_export.py`` in srlocations' interpreter; srstudio never
imports it. The record made from it is ``walk-2m-30fps.json`` beside it, and that record holds this file's SHA-256, so
a change here is a re-export of the record.
"""

from srlocations import Location
from srlocations.stock.mannequin import Mannequin

NAME = "walk-two-metres"
VERSION = "1.0.0"


def location() -> Location:
    walk = Location(NAME)
    walk.add(Mannequin(name="walker", at=(0.0, 0.0, 0.0), yaw=0.0))
    walk.walk("walker", (0.0, 0.0, 2.0), speed=1.0)
    return walk
