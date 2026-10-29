"""Optional typed limb performances replace only the selected legacy arms and preserve existing actor APIs."""

import xml.etree.ElementTree as ET

import pytest
from sr_core.scene import Scene

from srstudio import CAFE, OFFICE, Canvas, Episode, EpisodeSpec, cast, locations, signature
from srstudio.canvas import Signature
from srstudio.limbs.compile import BakeOptions, Occlusion
from srstudio.limbs.integration import LimbTrack, legacy_action
from srstudio.limbs.model import HUMAN, ArmProfile, LimbError
from srstudio.limbs.motion import Action, Motion
from srstudio.limbs.projection import Camera
from srstudio.rig import Performance


def track():
    return LimbTrack(
        Motion(ArmProfile(width=0.05), HUMAN, (Action("facepalm", 0, 2),)),
        style="cutout",
        camera=Camera(scale=80, origin=(-66, 148)),  # the right shoulder, on screen-left
        options=BakeOptions(fps=2),
        occlusion=(Occlusion("palm", 0, 2, layer="front"),),
    )


@pytest.mark.parametrize("actor", [cast.Manager, cast.Candidate, cast.Barista, cast.Customer])
def test_actors_accept_limb_tracks_without_drawing_the_replaced_legacy_arm(actor):
    scene = Scene(version="auto")
    scene.add_project(width=1080, height=1920, fps="24", duration=2)
    cv = Canvas(scene)
    a = actor(cv)
    extras = {"name": None} if actor is cast.Barista else {}
    a.build(cv.comp, 500, 700, 1, Performance(limbs=(track(),), extras=extras))
    assert scene.check() == []
    xml = ET.fromstring(scene.to_bytes())
    assert xml.find(f".//group[@id='{a.tag}-limb-right-front']") is not None
    assert xml.find(f".//group[@id='{a.tag_base}-forearm']") is None
    if actor is cast.Customer:
        # Only the prop in the customer's own right hand, the phone drawn on screen-left, was replaced.
        assert a.phone is None and a.cup is not None


def test_episode_perform_passes_typed_tracks_to_the_rig_instead_of_hiding_them_in_extras(project):
    ep = Episode(EpisodeSpec(slug="limbs", title="limbs", description="t", root=project, seed=1))
    actor = cast.Candidate(ep.cv)
    ep.perform(actor, ep.comp, 500, 700, 1, mouth=[(0, "rest")], limbs=(track(),))
    xml = ET.fromstring(ep.scene.to_bytes())
    assert xml.find(f".//group[@id='{actor.tag}-limb-right-front']") is not None


def test_legacy_gesture_names_have_explicit_conversion_and_conflicting_controls_fail():
    assert legacy_action("toon", "face", start=1, duration=2).name == "facepalm"
    assert legacy_action("gloss", "point", start=1, duration=2).name == "point"
    with pytest.raises(LimbError, match="legacy"):
        legacy_action("toon", "missing", start=1, duration=2)
    with pytest.raises(LimbError, match="duplicate"):
        Performance(limbs=(track(), track()))
    with pytest.raises(LimbError, match="legacy"):
        Performance(limbs=(track(),), extras={"forearm": [(0, 1)]})


@pytest.mark.parametrize(
    ("location", "palette", "slot", "actor"),
    [("office_wide", OFFICE, "at_desk", cast.Manager), ("cafe", CAFE, "at_counter", cast.Customer)],
)
def test_a_limb_tracked_actor_and_a_cactus_hand_off_share_one_signed_set(location, palette, slot, actor):
    scene = Scene(version="auto")
    scene.add_project(width=1080, height=1920, fps="24", duration=2, background=palette.background)
    cv = Canvas(scene, palette, signature=Signature())
    cv.assets.add_font(id="caption-font", src="f.ttf", family="DejaVu Sans", weight="700")  # the café's lettering
    a = actor(cv)
    getattr(locations, location)(
        cv,
        cv.comp,
        **{slot: lambda g: a.build(g, 500, 700, 1, Performance(limbs=(track(),)))},
        cactus=lambda g: signature.cactus(cv, g, 333, 777, 0.4),
    )
    assert scene.check() == []
    xml = ET.fromstring(scene.to_bytes())
    assert [g.get("id") for g in xml.iter("group") if g.get("id", "").startswith("sig-cactus")] == ["sig-cactus"]
    assert xml.find(f".//group[@id='{a.tag}-limb-right-front']") is not None
