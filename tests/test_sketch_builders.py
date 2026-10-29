"""The Toon and Collage sketch builders are library code (ADR 0016): episodes import them from :mod:`srstudio`, they
raise the shared :class:`srstudio.staging.StagingError`, and the Collage beat helpers are
:mod:`srstudio.scripting`'s."""

from pathlib import Path

import pytest

from srstudio import collage_sketch, scripting, staging, toon_sketch
from srstudio.errors import FlagError

EPISODES = Path(__file__).resolve().parent.parent / "episodes"


def test_the_builders_raise_the_shared_staging_error():
    assert toon_sketch.StagingError is staging.StagingError
    assert collage_sketch.StagingError is staging.StagingError


def test_the_collage_beat_helpers_are_the_shared_ones():
    assert collage_sketch.say is scripting.say
    assert collage_sketch.hold is scripting.hold


def test_no_episode_keeps_a_private_copy_of_a_builder():
    assert not list(EPISODES.glob("_*_sketch.py"))


def test_a_builder_refuses_a_mistyped_flag_before_building(tmp_path):
    for builder in (toon_sketch, collage_sketch):
        with pytest.raises(FlagError, match="unknown flag --voiced"):
            builder.build(tmp_path, None, {"--voiced"})
    assert list(tmp_path.iterdir()) == []
