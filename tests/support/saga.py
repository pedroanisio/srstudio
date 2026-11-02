"""What the Saga tests share with other test modules."""

from __future__ import annotations

from sr_core.scene import Scene

from srstudio import VOID, Canvas, flat_counter
from srstudio.canvas import Signature
from srstudio.timeline import Take

D = 4.0
SECONDS_A_WORD = 0.35  # a calm speaking rate for the synthetic recording


def canvas(signed: bool = True) -> Canvas:
    scene = Scene(version="auto")
    scene.add_project(width=1080, height=1920, fps="24", duration=D, background=VOID.background)
    cv = Canvas(scene, VOID, font_asset="f", namer=flat_counter("s"), signature=Signature() if signed else None)
    cv.assets.add_font(id="f", src="f.ttf", family="DejaVu Sans", weight="700")
    return cv


def recorded(reel, rate: float = SECONDS_A_WORD) -> list[Take]:
    """A synthetic recording of ``reel``: every word at ``rate``, the hold after the last, effects at their kept
    length; letters stand in for phones."""
    out, start = [], 0.0
    for t in reel.takes:
        if t.is_effect:
            words, length = (), t.longest
        else:
            words = tuple(
                {"text": w, "start": round(0.05 + i * rate, 3), "end": round(0.05 + (i + 1) * rate, 3)}
                for i, w in enumerate(t.text.split())
            )
            length = words[-1]["end"] + 0.05
        phones = tuple({"c": c, "start": 0.05 + i * 0.06, "end": 0.11 + i * 0.06} for i, c in enumerate(t.text.lower()))
        duration = round(length + t.hold, 3)
        out.append(Take(t.id, t.actor, "", t.text, round(start, 3), duration, words=words, phones=phones))
        start += duration
    return out
