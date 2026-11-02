"""A mannequin standing, waving, then crossing its arms: the motion bridge's posed fixture (ADR 0187).

An srlocations location module, run only by ``tools/motion_export.py`` in srlocations' interpreter; srstudio never
imports it. The record made from it is ``stand-wave-crossed-30fps.json`` beside it, and that record holds this file's
SHA-256, so a change here is a re-export of the record.
"""

from srlocations import Location
from srlocations.stock.mannequin import Mannequin

NAME = "stand-wave-crossed"
VERSION = "1.0.0"


def location() -> Location:
    posed = Location(NAME)
    figure = posed.add(Mannequin(name="poser", pose="stand"))
    posed.move(figure, 0.5, pose="wave")
    posed.move(figure, 1.0, pose="arms-crossed")
    posed.move(figure, 1.5)
    return posed
