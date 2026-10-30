"""The Cutout finish: an opt-in grade (a warm vignette and a soft bloom) over a group the episode draws its sets
into; no grain, so a still opening stays still, and no blur, so the signature marks stay sharp."""

import xml.etree.ElementTree as ET

from srstudio import CAFE, locations, signature
from support.signature import _canvas


def effects(cv) -> dict[str, str]:
    root = ET.fromstring(cv.scene.to_bytes())
    return {e.get("id"): e.get("type") for e in root.iter("effect")}


def test_the_finish_grades_a_group_that_the_sets_are_drawn_into():
    cv = _canvas(CAFE)
    graded = locations.finish(cv, cv.comp)
    locations.cafe(cv, graded)
    assert set(graded.effects) == {"cutout-vignette", "cutout-bloom"}
    assert effects(cv) == {"cutout-vignette": "vignette", "cutout-bloom": "bloom"}
    assert signature.missing(cv.scene.to_bytes()) == []


def test_the_finish_never_moves_on_its_own():
    assert set(locations.FINISH) == {"vignette", "bloom"}  # no film grain: arm A's first second stays still
    assert all(kind != "blur" for kind in locations.FINISH)


def test_two_finished_groups_share_one_declaration():
    cv = _canvas(CAFE)
    locations.finish(cv, cv.comp, id="finish-a")
    locations.finish(cv, cv.comp, id="finish-b")
    assert list(effects(cv)) == ["cutout-vignette", "cutout-bloom"]


def test_a_set_drawn_without_the_finish_is_unchanged():
    cv = _canvas(CAFE)
    locations.cafe(cv, cv.comp)
    assert effects(cv) == {}
