"""What a blob wears rides its head, drawing by drawing, as what it holds rides its hands."""

import xml.etree.ElementTree as ET

import pytest

from srstudio import blob
from support.soft_props import canvas

SCALE = 2.0
CUES = [blob.cue(0, "stand", (200.0, 1000.0), scale=SCALE), blob.cue(1.0, "sit", (300.0, 900.0), scale=SCALE, ease=0.4)]


def keys(cv, id: str, prop: str) -> list[tuple[float, float]]:
    root = ET.fromstring(cv.scene.to_bytes(layout="pretty"))
    group = next(g for g in root.iter("group") if g.get("id") == id)
    animate = next(a for a in group.findall("animate") if a.get("property") == prop)
    return [(float(k.get("time")), float(k.get("value"))) for k in animate.findall("key")]


def test_a_worn_group_lands_on_the_head_of_every_drawing():
    cv = canvas()
    blob.worn(cv, cv.comp, CUES, end=2.0, scale=SCALE, fps=15, id="scarf-at")
    frames = blob.drawings(CUES, end=2.0, fps=15)
    xs, ys = keys(cv, "scarf-at", "x"), keys(cv, "scarf-at", "y")
    assert len(xs) == len(ys) == len(frames)
    for (t, x), (_, y), d in zip(xs, ys, frames, strict=True):
        assert t == pytest.approx(d.time)
        assert x == pytest.approx(SCALE * d.pose.head[0], abs=0.01)
        assert y == pytest.approx(SCALE * d.pose.head[1], abs=0.01)


def test_a_worn_group_moves_through_the_inbetweens_with_the_character():
    cv = canvas()
    blob.worn(cv, cv.comp, CUES, end=2.0, scale=SCALE, id="scarf-at")
    distinct = {x for _, x in keys(cv, "scarf-at", "x")}
    assert len(distinct) > 2  # the group eases, it does not cut


@pytest.mark.parametrize("scale", [0.0, -1.0, float("nan")])
def test_a_worn_group_refuses_a_scale_it_cannot_map(scale):
    cv = canvas()
    with pytest.raises(blob.BlobError):
        blob.worn(cv, cv.comp, CUES, end=2.0, scale=scale, id="scarf-at")
