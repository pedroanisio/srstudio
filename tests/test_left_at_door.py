"""Left at the Door: the text the reel depends on stays clear of the weather."""

from __future__ import annotations

import sys
import xml.etree.ElementTree as ET
from pathlib import Path
from types import SimpleNamespace

from sr_core.scene import Scene

from srstudio import PEACH, Canvas

EPISODES = Path(__file__).resolve().parents[1] / "episodes"


def data():
    sys.path.insert(0, str(EPISODES))
    try:
        import left_at_door_data
    finally:
        sys.path.pop(0)
    return left_at_door_data


def index(names: list[str], prefix: str) -> int:
    return next(i for i, name in enumerate(names) if name.startswith(prefix))


def test_the_street_phone_stands_in_front_of_the_rain():
    """A streak crossing "Green door" dropped it to 2.3:1 in the frames it passed; the rain has to fall behind."""
    scene = Scene(version="auto")
    scene.add_project(width=1080, height=1920, fps="24", duration=12.0, background=PEACH.background)
    cv = Canvas(scene, PEACH, font_asset="comic-neue")
    shot = SimpleNamespace(cv=cv, back=cv.comp, front=cv.comp, measure=lambda text, size: len(text) * size * 0.5)
    data().street(shot, 1.0, 3.0)
    order = [n.get("id", "") for n in ET.fromstring(scene.to_bytes(layout="pretty")).iter("group")]
    assert index(order, "rain") < index(order, "phone")
