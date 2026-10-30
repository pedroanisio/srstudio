"""Payday as data: the crash zoom crops the phone, so no lettering on it reaches the close."""

import sys
from pathlib import Path
from types import SimpleNamespace

import pytest
from sr_core.scene import Scene

from srstudio import PEACH, Canvas, collage_sets, flat_counter
from srstudio.sketch import events

EPISODES = Path(__file__).resolve().parent.parent / "episodes"


@pytest.fixture(scope="module")
def data():
    sys.path.insert(0, str(EPISODES))
    try:
        import payday_data

        return payday_data
    finally:
        sys.path.pop(0)


def test_no_lettering_on_the_phone_reaches_the_close(data, monkeypatch):
    scene = Scene(version="auto")
    scene.add_project(width=1080, height=1920, fps="24", duration=20.0, background=PEACH.background)
    cv = Canvas(scene, PEACH, font_asset="comic-neue", namer=flat_counter("k"))
    spans, signs = {}, []
    gate = cv.gate

    def gated(group, on):
        spans[id(group)] = on
        return gate(group, on)

    monkeypatch.setattr(cv, "gate", gated)
    monkeypatch.setattr(collage_sets, "sign", lambda _cv, parent, text, *_a, **_k: signs.append((text, id(parent))))
    sketch = data.SKETCH
    shot = SimpleNamespace(
        cv=cv,
        front=cv.group(cv.comp, "front"),
        back=cv.group(cv.comp, "back"),
        app=SimpleNamespace(start=0.0, end=sketch.end),
        beats=sketch.beats,
    )
    data.dress(shot)
    zoom = events(sketch.beats, "zoom")[0][0]
    assert {"BALANCE", "PAID 0:11 AGO", "$3.12"} <= {text for text, _ in signs}
    assert all(spans[parent][-1][1] <= zoom for _, parent in signs)
