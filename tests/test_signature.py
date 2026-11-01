"""The signature marks (ADR 0001): present in every signed location, absent when unsigned, typed on bad input."""

import hashlib
import xml.etree.ElementTree as ET

import pytest
from sr_core.scene import Scene

from srstudio import CAFE, MONO, OFFICE, Canvas, Episode, EpisodeSpec, locations, signature
from srstudio.canvas import Signature
from support.build import office_episode
from support.signature import SPAN, TODAY, _canvas


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


DRAW = {
    "office_wide": (OFFICE, lambda cv: locations.office_wide(cv, cv.comp)),
    "office_wide_instanced": (OFFICE, lambda cv: locations.office_wide(cv, cv.comp, instanced=True)),
    "office_desk": (OFFICE, lambda cv: locations.office_desk(cv, cv.comp)),
    "office_desk_instanced": (OFFICE, lambda cv: locations.office_desk(cv, cv.comp, instanced=True)),
    "office_reverse": (OFFICE, lambda cv: locations.office_reverse(cv, cv.comp)),
    "cafe": (CAFE, lambda cv: locations.cafe(cv, cv.comp)),
    "park": (CAFE, lambda cv: locations.park(cv, cv.comp)),
    "cactus_mono": (MONO, lambda cv: signature.cactus(cv, cv.comp, 500, 900, 0.8)),
    "cactus_office": (OFFICE, lambda cv: signature.cactus(cv, cv.comp, 500, 900, 0.8)),
}


@pytest.mark.parametrize("name", sorted(TODAY))
def test_without_an_act_or_a_hand_off_every_drawing_keeps_todays_bytes(name):
    palette, draw = DRAW[name]
    cv = _canvas(palette)
    draw(cv)
    assert hashlib.sha256(cv.scene.to_bytes()).hexdigest() == TODAY[name]


def _group(root, id):
    (g,) = [el for el in root.iter("group") if el.get("id") == id]
    return g


def _keys(group, prop):
    (a,) = [a for a in group.iter("animate") if a.get("property") == prop]
    return [(float(k.get("time")), k.get("value")) for k in a.iter("key")]


def test_an_acting_cactus_turns_its_flower_blooms_on_its_beat_and_wears_the_code_on_its_pot():
    cv = _canvas()
    act = signature.Act(end=SPAN, turn=((1.0, 0), (1.6, -18)), bloom=4.5)
    g = signature.cactus(cv, cv.comp, 500, 900, 0.8, act=act)
    root = ET.fromstring(cv.scene.to_bytes())
    assert g.id == "sig-cactus" and signature.missing(cv.scene.to_bytes()) == []
    flower = _group(root, "flower-of-sig-cactus")
    assert _keys(flower, "rotation") == [(1.0, "0"), (1.6, "-18")]
    bud, bloom = _group(root, "bud-of-sig-cactus"), _group(root, "bloom-of-sig-cactus")
    assert _keys(bud, "opacity") == [(0.0, "1"), (4.5, "0")]
    assert _keys(bloom, "opacity") == [(0.0, "0"), (4.5, "1"), (SPAN, "0")]  # open to the end of the episode
    assert [t for t, _ in _keys(bloom, "scaleX")][1] == pytest.approx(4.5)  # the pop starts on the beat
    code = _group(_group(root, "sig-cactus"), "sig-code")  # on the pot, inside the cactus
    assert len(code.findall("shape")) == 7 and code.find(".//instance") is None
    assert root.find(".//instance") is None  # drawn inline: a camera can push in without softening it


def test_an_act_can_leave_the_bloom_and_the_code_out():
    cv = _canvas()
    signature.cactus(cv, cv.comp, 500, 900, act=signature.Act(end=SPAN, code=False))
    root = ET.fromstring(cv.scene.to_bytes())
    assert _ids(root, "sig-code") == [] and not [g for g in root.iter("group") if g.get("id", "").startswith("bloom")]


@pytest.mark.parametrize(
    "kw, match",
    [
        (dict(end=0), "end"),
        (dict(end=float("nan")), "end"),
        (dict(end=SPAN, turn=((1.0, 0), (0.5, 10))), "turn"),  # times go back
        (dict(end=SPAN, turn=((1.0, 0), (1.0, 10))), "turn"),  # a time repeats
        (dict(end=SPAN, turn=((-0.1, 0),)), "turn"),
        (dict(end=SPAN, turn=((SPAN, 0),)), "turn"),  # at the end is past the span
        (dict(end=SPAN, turn=((1.0, "left"),)), "turn"),
        (dict(end=SPAN, turn=((1.0,),)), "turn"),
        (dict(end=SPAN, bloom=-1.0), "bloom"),
        (dict(end=SPAN, bloom=SPAN), "bloom"),
        (dict(end=SPAN, bloom=True), "bloom"),
    ],
)
def test_an_act_outside_the_episode_or_out_of_order_is_refused(kw, match):
    with pytest.raises(signature.SignatureError, match=match):
        signature.Act(**kw)


def test_an_acting_cactus_on_an_unsigned_canvas_is_refused():
    cv = _canvas(signed=False)
    with pytest.raises(signature.SignatureError, match="signed"):
        signature.cactus(cv, cv.comp, 0, 0, act=signature.Act(end=SPAN))
    assert signature.cactus(cv, cv.comp, 0, 0) is None  # the resting mark stays silent, as before


def test_a_home_cactus_is_the_locations_own_or_exactly_one_from_the_slot():
    cv = _canvas()
    assert signature.home_cactus(cv, cv.comp, 10, 20, 0.5).id == "sig-cactus"
    signature.home_cactus(cv, cv.comp, 10, 20, 0.5, slot=lambda g: signature.cactus(cv, g, 300, 400))
    assert _ids(ET.fromstring(cv.scene.to_bytes()), "sig-cactus") == ["sig-cactus", "sig-cactus-2"]
    with pytest.raises(signature.SignatureError, match="drew 0"):
        signature.home_cactus(cv, cv.comp, 10, 20, 0.5, slot=lambda g: None)

    def two(g):
        signature.cactus(cv, g, 1, 1)
        signature.cactus(cv, g, 2, 2)

    with pytest.raises(signature.SignatureError, match="drew 2"):
        signature.home_cactus(cv, cv.comp, 10, 20, 0.5, slot=two)
    plain = _canvas(signed=False)  # unsigned, the slot draws no mark and owes none
    assert signature.home_cactus(plain, plain.comp, 10, 20, 0.5, slot=lambda g: None) is None


HANDED = {  # each location that takes cactus=, with its palette
    "office_wide": (OFFICE, locations.office_wide),
    "office_desk": (OFFICE, locations.office_desk),
    "office_reverse": (OFFICE, locations.office_reverse),
    "cafe": (CAFE, locations.cafe),
    "park": (CAFE, locations.park),
    "reception": (OFFICE, locations.reception),
}


@pytest.mark.parametrize("name", sorted(HANDED))
def test_a_location_hands_its_cactus_to_the_slot_and_still_shows_exactly_one(name):
    palette, location = HANDED[name]
    cv = _canvas(palette)
    g = location(cv, cv.comp, cactus=lambda g: signature.cactus(cv, g, 333, 777, 0.4))
    root = ET.fromstring(cv.scene.to_bytes())
    (mark,) = [el for el in _group(root, g.id).iter("group") if el.get("id", "").startswith("sig-cactus")]
    assert (float(mark.get("x")), float(mark.get("y"))) == (333, 777)
    with pytest.raises(signature.SignatureError, match="drew 0"):
        location(_canvas(palette), cv.comp, cactus=lambda g: None)


@pytest.mark.parametrize("location", [locations.office_wide, locations.office_desk])
def test_an_instanced_office_refuses_a_hand_off(location):
    cv = _canvas()
    with pytest.raises(signature.SignatureError, match="instanced"):
        location(cv, cv.comp, instanced=True, cactus=lambda g: signature.cactus(cv, g, 0, 0))
