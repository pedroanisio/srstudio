"""A Soft figure's "look" eyes point the way the cue says: screen left, as every reel so far drew them, or screen
right, so a figure can look at someone on its right whichever way it faces (ADR 0235)."""

import hashlib
import xml.etree.ElementTree as ET

import pytest

from srstudio import blob
from srstudio.blob import BlobError, Cue
from support.soft_props import canvas

RIGS = ("pip", "bo", "juno", "remy")


def eyes(rig: str, cues, group: str) -> list[tuple[float, float]]:
    """(white centre x, pupil centre x) of each eye in the figure's ``group``."""
    cv = canvas()
    getattr(blob, rig)(cv, cv.comp, cues, end=float(len(cues)))
    found = [g for g in ET.fromstring(cv.scene.to_bytes(layout="pretty")).iter("group") if g.get("id") == group]
    assert len(found) == 1, f"no {group} group"
    shapes = [s for s in found[0] if s.get("shape") == "ellipse"]
    centres = [float(s.get("x")) + float(s.get("width")) / 2 for s in shapes]
    whites = [i for i, s in enumerate(shapes) if s.get("fill") == "#FFFFFF" and s.get("strokeWidth") == "4.5"]
    return [(centres[i], centres[i + 1]) for i in whites]


@pytest.mark.parametrize("rig", RIGS)
@pytest.mark.parametrize("flip", [False, True])
def test_look_right_puts_both_pupils_right_of_their_eyes_whichever_way_the_figure_faces(rig, flip):
    pairs = eyes(rig, [Cue(0, "stand", eyes="look", gaze="right", flip=flip)], f"{rig}-eyes-look-right")
    assert len(pairs) == 2 and all(pupil - white == pytest.approx(8) for white, pupil in pairs)


@pytest.mark.parametrize("flip", [False, True])
def test_look_left_is_the_default_and_draws_as_before(flip):
    pairs = eyes("pip", [Cue(0, "stand", eyes="look", flip=flip)], "pip-eyes-look")
    assert all(pupil - white == pytest.approx(-8) for white, pupil in pairs)
    assert Cue(0, "stand").gaze == "left"


def test_one_figure_can_look_left_then_right():
    cues = [Cue(0, "stand", eyes="look"), Cue(1, "stand", eyes="look", gaze="right")]
    left, right = eyes("pip", cues, "pip-eyes-look"), eyes("pip", cues, "pip-eyes-look-right")
    assert [p - w for w, p in left] == pytest.approx([-8, -8]) and [p - w for w, p in right] == pytest.approx([8, 8])


def test_a_gaze_the_rig_has_not_is_refused():
    with pytest.raises(BlobError, match="gaze"):
        blob._check([Cue(0, "stand", eyes="look", gaze="up")], end=1.0)


def test_a_gaze_on_eyes_that_do_not_look_is_refused_rather_than_ignored():
    with pytest.raises(BlobError, match="gaze"):
        blob._check([Cue(0, "stand", eyes="open", gaze="right")], end=1.0)


def test_the_contract_names_the_gazes():
    from srstudio import registry

    contract = registry.get("character", "pip").contract
    fields = dict(contract.operations[0].contract.parameters)
    assert fields["gaze"].enum == blob.GAZES == ("left", "right")


# Taken on develop 0d120676, before the cue had a gaze: every eye shape, "look" facing both ways, on all four rigs.
BEFORE = {
    "pip": "4d82703a8ca56615ceda3fe815a18d4188f9f218ce718199022f289ca0c2008e",
    "bo": "1492ad216c2618185b4eef879e45568d16713020ffdbba953ec7d9be2335d4c3",
    "juno": "feea65ca295c1e7fd6d3b785e0312b522b4cd158e2b070295d89530391be9439",
    "remy": "e03590cbcac4d107bf1166ac6e47cf4bd4eb5b408bc26270a40f41276b6e890c",
}


@pytest.mark.parametrize("rig", RIGS)
def test_a_performance_that_names_no_gaze_draws_byte_for_byte_as_before(rig):
    kinds = ("open", "look", "wide", "happy", "squint", "closed")
    cues = [Cue(float(i), "stand", eyes=e, flip=bool(i % 2)) for i, e in enumerate(kinds)]
    cues += [Cue(6.0 + i, "sit", eyes="look", flip=f) for i, f in enumerate((False, True))]
    cv = canvas()
    getattr(blob, rig)(cv, cv.comp, cues, end=9.0)
    assert hashlib.sha256(cv.scene.to_bytes(layout="pretty")).hexdigest() == BEFORE[rig]
