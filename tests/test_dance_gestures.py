"""The preset moves on the shared skeleton (ADR 0186, ADR 0192): every preset stays inside the limits of every preset
character without clamping, at a dense set of times and mirrored."""

import pytest

from srstudio import dance
from srstudio import skeleton as sk
from srstudio.dance_pose import dance_pose
from srstudio.music import Groove

GRID = Groove(120)  # half a second a beat
PROFILES = {name: sk.preset(name) for name in sk.PRESETS}
STEPS = 48  # samples a beat: finer than any stroke of the presets


def posed(profile, source, beat):
    """``source`` danced at ``beat`` on ``profile``, unclamped: a value past a limit raises."""
    return dance_pose(profile, dance.sample(source, GRID, beat * GRID.beat)).pose


@pytest.mark.parametrize("character", sk.PRESETS)
@pytest.mark.parametrize("name", list(dance.moves()))
def test_every_preset_dances_within_every_characters_limits_unclamped(name, character):
    move = dance.moves()[name]
    for source in (move, move.mirror()):
        for step in range(round(move.loop_beats * STEPS)):
            posed(PROFILES[character], source, step / STEPS)
