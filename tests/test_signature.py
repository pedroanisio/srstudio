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
