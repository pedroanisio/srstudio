"""Wrongly typed input to public limb entry points fails as LimbError, never as a bare builtin."""

import pytest
from sr_core.scene import Scene

from srstudio import Canvas
from srstudio.limbs import HUMAN, ArmProfile, Camera, HandControl, LimbError, Vec3
from srstudio.limbs.adapters import Appearance, adapter_for
from srstudio.limbs.compile import compile_motion
from srstudio.limbs.correctives import ContourKey
from srstudio.limbs.integration import LimbTrack, legacy_action
from srstudio.limbs.interaction import Face, Participant, bake_interaction
from srstudio.limbs.math3d import Frame
from srstudio.limbs.model import DigitProfile
from srstudio.limbs.motion import Action, Motion, TransformKey, TransformTrack, WordRef
from srstudio.limbs.props import Anchor, Prop, Sphere


def _motion():
    return Motion(ArmProfile(), HUMAN, (Action("point", 0, 1),))


def _track():
    return TransformTrack((TransformKey(0, Frame()),))


def _word_without_start():
    from srstudio.timeline import Take

    take = Take("01", "actor", "wide", "No.", 0, 1, words=({"text": "No.", "end": 0.4},))
    return Action.on_word("point", WordRef("01", 0), [take], duration=1)


CASES = {
    "camera origin int": lambda: Camera(origin=5),
    "camera origin none": lambda: Camera(origin=None),
    "elbow limit float": lambda: ArmProfile(elbow_limit=1.0),
    "contour key vertex int": lambda: ContourKey(0, (1, 2, 3)),
    "contour key vertices int": lambda: ContourKey(0, 3),
    "curl override without value": lambda: HandControl(curls=(("index",),)),
    "curl override not a pair": lambda: HandControl(curls=("index",)),
    "joint override float angles": lambda: HandControl(joints=(("index", 0.5),)),
    "digit lengths int": lambda: DigitProfile("x", Vec3(), 5),
    "digit max_flex int": lambda: DigitProfile("x", Vec3(), (1.0,), max_flex=1),
    "word without start": _word_without_start,
    "adapter list": lambda: adapter_for([]),
    "track style list": lambda: LimbTrack(_motion(), style=[]),
    "legacy pose list": lambda: legacy_action("toon", [], start=0, duration=1),
    "appearance color int": lambda: Appearance(skin=5),
    "participant name int": lambda: Participant(7, _motion()),
    "interaction id int": lambda: bake_interaction(Canvas(Scene()), None, (), (), id=7),
    "compile id int": lambda: compile_motion(Canvas(Scene()), None, _motion(), id=7),
    "prop face color int": lambda: Face("face", (Vec3(), Vec3(1, 0, 0), Vec3(0, 1, 0)), fill=5),
    "anchor name int": lambda: Anchor(7, Frame()),
    "prop name tuple": lambda: Prop(("x",), _track(), (Anchor("a", Frame()),)),
    "sphere name list": lambda: Sphere([1], Vec3(), 1),
}


@pytest.mark.parametrize("case", CASES)
def test_wrongly_typed_input_raises_a_limb_error(case):
    with pytest.raises(LimbError) as caught:
        CASES[case]()
    assert isinstance(caught.value, ValueError)
    assert caught.value.code == "invalid"


@pytest.mark.parametrize("make", [lambda n: Anchor(n, Frame()), lambda n: Sphere(n, Vec3(), 1)])
def test_names_follow_the_shared_label_bounds(make):
    with pytest.raises(LimbError, match="1..128"):
        make("x" * 129)
    assert make("x").name == "x"
