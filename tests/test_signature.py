"""The signature marks (ADR 0001): present in every signed location, absent when unsigned, typed on bad input."""

import xml.etree.ElementTree as ET

import pytest
from sr_core.scene import Scene

from srstudio import MONO, Canvas, Episode, EpisodeSpec, locations, signature
from srstudio.canvas import Signature
from test_build import office_episode


def _ids(root, prefix):
    """Ids of the signature *groups* (the paints they use carry a ``-paint`` suffix and are not marks)."""
    return sorted(el.get("id") for el in root.iter("group") if (el.get("id") or "").startswith(prefix))


def test_signed_office_episode_marks_every_location(project, tmp_path):
    ep, path = office_episode(project, tmp_path)
    root = ET.parse(path).getroot()
    assert ep.check() == []
    assert _ids(root, "sig-code") == ["sig-code", "sig-code-2"]  # wide-office-angle, candidate-reverse-angle
    assert _ids(root, "sig-cactus") == ["sig-cactus", "sig-cactus-2"]
    code = next(el for el in root.iter("group") if el.get("id") == "sig-code")
    assert len(code.findall("shape")) == 7  # S R - 1 0 2 8, one stroked path each
    assert all(s.get("shape") == "path" and s.get("fill") == "#00000000" for s in code)
    gradients = {g.get("id") for g in root.find("paints")}
    assert {"sig-pot-paint", "sig-cactus-paint"} <= gradients


def test_unsigned_episode_draws_no_marks(project):
    ep = Episode(
        EpisodeSpec(slug="t", title="t", description="t", root=project, seed=1, background="#D5DFDF", signature=False)
    )
    locations.office_wide(ep.cv, ep.comp)
    locations.office_reverse(ep.cv, ep.comp)
    root = ET.fromstring(ep.scene.to_bytes())
    assert _ids(root, "sig-") == []


def test_signature_code_is_configurable_and_typed(project):
    ep = Episode(
        EpisodeSpec(
            slug="t", title="t", description="t", root=project, seed=1, background="#D5DFDF", signature_code="PA-2026"
        )
    )
    g = signature.code(ep.cv, ep.comp, 10, 10, 12)
    root = ET.fromstring(ep.scene.to_bytes())
    code = next(el for el in root.iter("group") if el.get("id") == "sig-code")
    assert g.id == "sig-code" and len(code.findall("shape")) == 7  # P A - 2 0 2 6
    cv = Canvas(Scene(version="auto"), signature=Signature(code="S@"))
    with pytest.raises(ValueError, match="without a glyph"):
        signature.code(cv, cv.comp, 0, 0)


def test_mono_palette_uses_pen_stroke_without_paints():
    cv = Canvas(Scene(version="auto"), palette=MONO, width=1080, height=1080, signature=Signature())
    signature.cactus(cv, cv.comp, 940, 986, 0.45)
    signature.code(cv, cv.comp, 330, 329, 11, angle=5)
    root = ET.fromstring(cv.scene.to_bytes())
    assert root.find("paints") is None  # no gradients in the hand-drawn family
    fills = {s.get("fill") for s in root.iter("shape")}
    assert fills <= {MONO.white, MONO.ink, MONO.shade, MONO.clear}
    assert _ids(root, "sig-") == ["sig-cactus", "sig-code"]


def test_glyph_set_covers_the_default_code():
    assert all(c in signature.GLYPHS for c in Signature().code)
    assert signature.text_width("SR-1028", 16) == pytest.approx(7 * signature.ADVANCE - 3.5)


# -- the gate: a signed episode is not written without both marks ------------------------------------------------
def _bare(project, **spec):
    return Episode(
        EpisodeSpec(slug="t", title="t", description="t", root=project, seed=1, background="#D5DFDF", **spec)
    )


def test_missing_names_each_mark_the_document_lacks():
    signed = b'<scene><group id="sig-code"/><group id="sig-cactus-2"/></scene>'
    assert signature.missing(signed) == []
    assert signature.missing(b'<scene><group id="sig-code"/></scene>') == ["sig-cactus"]
    assert signature.missing(b'<scene><paints><linearGradient id="sig-cactus-paint"/></paints></scene>') == [
        "sig-cactus",
        "sig-code",
    ]  # a paint is not a mark


def test_a_signed_episode_whose_locations_draw_no_marks_is_refused(project, tmp_path):
    ep = _bare(project)
    ep.cv.rect(ep.comp, 0, 0, 100, 100, "#FFFFFF")  # a set that forgot ADR 0001
    with pytest.raises(signature.SignatureError, match="sig-cactus, sig-code"):
        ep.finish(tmp_path / "t.scene.xml")
    assert not (tmp_path / "t.scene.xml").exists()


def test_a_signed_episode_with_both_marks_and_an_unsigned_one_are_written(project, tmp_path):
    ep = _bare(project)
    locations.office_wide(ep.cv, ep.comp)
    assert ep.finish(tmp_path / "signed.scene.xml").exists()
    plain = _bare(project, signature=False)
    plain.cv.rect(plain.comp, 0, 0, 100, 100, "#FFFFFF")
    assert plain.finish(tmp_path / "plain.scene.xml").exists()


# -- the Toon sets: every shot is a backdrop behind the shared desk, and the desk carries both marks -----------------
def _toon_shot(back, signed=True):
    from srstudio import PEACH, toon, toon_props

    scene = Scene(version="auto")
    scene.add_project(width=1080, height=1920, fps="24", duration=1, background=PEACH.background)
    cv = Canvas(scene, PEACH, font_asset="comic-neue", signature=Signature("SR-1028") if signed else None)
    {"room": toon.room, "meeting": toon_props.meeting}[back](cv, cv.comp)
    toon.desk(cv, cv.comp)
    return ET.fromstring(scene.to_bytes())


@pytest.mark.parametrize("back", ["room", "meeting"])
def test_every_toon_shot_is_signed_clear_of_the_character_and_the_captions(back):
    from srstudio.toon import fx, fy

    root = _toon_shot(back)
    assert signature.missing(ET.tostring(root)) == []
    for mark in ("sig-cactus", "sig-code"):
        (group,) = [g for g in root.iter("group") if g.get("id") == mark]  # one of each per shot, never doubled
        x, y = float(group.get("x")), float(group.get("y"))
        assert 0 < x < 1080 and 0 < y < 1920, mark
        assert not (fx(30) <= x <= fx(340) and y >= fy(360)), f"{mark} sits in the character's corner"
        assert not (fy(253) <= y <= fy(352)), f"{mark} sits in the caption and badge band"


def test_an_unsigned_toon_shot_draws_no_marks():
    assert _ids(_toon_shot("room", signed=False), "sig-") == []
