"""What test_ink_meter.py shares with other test modules."""

from sr_core.scene import Scene

from srstudio import MONO, Canvas, shared_counter
from srstudio.canvas import Signature
from srstudio.timeline import Take


def canvas() -> Canvas:
    scene = Scene(version="auto")
    scene.add_project(width=1080, height=1080, fps="24", duration=6.0, background=MONO.background)
    return Canvas(scene, MONO, font_asset="patrick-hand", namer=shared_counter(), signature=Signature())


def take(actor: str = "meter", duration: float = 2.0, shot: str = "kerb", mood: str = "calm") -> Take:
    return Take("01", actor, shot, "Scan me.", 0.0, duration, mood=mood)
