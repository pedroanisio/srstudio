"""Rosa, the neighbour: an office-family actor with a grey bob, round glasses and her name stitched on her
cardigan, so a close-up can show the name nobody in the scene has read."""

import xml.etree.ElementTree as ET

import pytest
from sr_core.scene import Scene

from srstudio import OFFICE, Canvas, cast, registry
from srstudio.canvas import CanvasError
from srstudio.rig import Performance


def canvas(font: str | None = "font") -> Canvas:
    scene = Scene(version="auto")
    scene.add_project(width=1080, height=1920, fps="30", duration=4, background=OFFICE.background)
    return Canvas(scene, OFFICE, font_asset=font)


def texts(cv) -> dict[str, str]:
    root = ET.fromstring(cv.scene.to_bytes())
    return {t.get("id"): t.get("text") for t in root.iter() if t.tag.rsplit("}", 1)[-1] == "text"}


def test_rosa_is_a_registered_cutout_character_of_the_office_family():
    entry = registry.get("character", "rosa")
    assert entry.style == "cutout" and entry.summary
    assert issubclass(cast.Rosa, cast.OfficeActor)


def test_her_cardigan_carries_her_name_and_she_stands_on_her_own_legs():
    cv = canvas()
    rosa = cast.Rosa(cv)
    rosa.build(cv.comp, 400, 900, 1.2, Performance(extras={"legs": "standing"}))
    assert "ROSA" in texts(cv).values()
    ids = [el.get("id") for el in ET.fromstring(cv.scene.to_bytes()).iter() if el.get("id")]
    assert f"{rosa.tag_base}-legs" in ids
    assert [f for f in cv.scene.check() if f.severity == "error" and "fontAsset" not in f.message] == []


def test_the_stitch_can_name_someone_else_or_nobody():
    cv = canvas()
    cast.Rosa(cv).build(cv.comp, 400, 900, 1.2, Performance(extras={"stitch": "MUM"}))
    assert "MUM" in texts(cv).values()
    silent = canvas(None)
    cast.Rosa(silent).build(silent.comp, 400, 900, 1.2, Performance(extras={"stitch": None}))
    assert texts(silent) == {}  # no text layer: a silent canvas draws her too


@pytest.mark.parametrize("bad", ["", "  ", "X" * (cast.Rosa.STITCH + 1), 7])
def test_a_stitch_her_pocket_cannot_hold_is_refused(bad):
    with pytest.raises(cast.CastError, match="stitch"):
        cast.Rosa(canvas()).build(None, 0, 0, 1, Performance(extras={"stitch": bad}))


def test_the_stitch_needs_a_font():
    with pytest.raises(CanvasError, match="font"):
        cast.Rosa(canvas(None)).build(canvas(None).comp, 0, 0, 1, Performance())
