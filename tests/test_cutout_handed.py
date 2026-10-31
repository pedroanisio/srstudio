"""Cutout, what changes hands: each prop draws, is registered, and refuses what it cannot draw."""

import xml.etree.ElementTree as ET

import pytest

from srstudio import cutout_handed, registry
from support.tip_tablet import canvas

CHECKED = cutout_handed.CutoutHandedError


def ids(cv) -> set[str]:
    return {e.get("id") for e in ET.fromstring(cv.scene.to_bytes()).iter() if e.get("id")}


def texts(cv) -> list[str]:
    root = ET.fromstring(cv.scene.to_bytes())
    return [t.get("text") for t in root.iter() if t.tag.rsplit("}", 1)[-1] == "text"]


@pytest.mark.parametrize("name", ["cv-folder"])
def test_each_is_a_registered_cutout_prop(name):
    entry = registry.get("prop", name)
    assert entry.style == "cutout" and entry.summary


def test_a_folder_is_shut_and_opens_in_its_spans():
    cv = canvas()
    cutout_handed.cv_folder(cv, cv.comp, open_spans=[(1.0, 2.0)], label="RESUME")
    assert {"cv-folder-shut", "cv-folder-open"} <= ids(cv) and "RESUME" in texts(cv)


@pytest.mark.parametrize(
    "kw",
    [
        {"scale": 0},
        {"scale": "big"},
        {"label": ""},
        {"label": "CURRICULUM"},
        {"open_spans": [(2.0, 1.0)]},
        {"open_spans": [(3.0, 4.0), (1.0, 2.0)]},
    ],
)
def test_a_folder_refuses_what_it_cannot_draw(kw):
    cv = canvas()
    with pytest.raises(CHECKED):
        cutout_handed.cv_folder(cv, cv.comp, **kw)
