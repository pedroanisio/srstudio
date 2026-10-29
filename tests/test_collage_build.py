"""The shared Collage build with a group shot: a staging's casting is made from the beats the build draws (scripted
or voiced), every group-shot appearance draws the whole lineup in the same places, and a zoom lands on the
speaker's face in its place; the ``timer`` and ``flash`` events are known, and a flash is heard as a shutter."""

import os
import shutil
import xml.etree.ElementTree as ET
from pathlib import Path

import pytest

from srstudio import COLLAGE, collage, collage_sketch, sketch
from srstudio.collage_group import Lineup, Place
from srstudio.collage_sketch import Staging, check_staging, make_sketch, solo, sound_effects, timed

PLACES = {"gary": Place(240.0, 1800.0, 0.55), "kai": Place(845.0, 1800.0, 0.56), "rosa": Place(540.0, 1800.0, 0.6)}
LINES = (
    sketch.Line("gary", "Natural, everyone!"),
    sketch.Line("rosa", "I am natural."),
    sketch.Line("gary", "Kai, headset off."),
)
BEATS, END = timed(
    LINES,
    (
        (1.6, "gary", 0, "open", "grin", "point", "timer"),
        (1.4, "rosa", 1, "half", "smug", "hold"),
        (1.8, "gary", 2, "wide", "o", "shrug", "zoom"),
        (0.8, "gary", "", "wide", "o", "shrug", "flash"),
    ),
    tail=1.0,
)


def still(eyes, mouth, arms):
    return ({"start": 0.0, "eyes": eyes, "mouth": mouth, "arms": arms},)


def casting(beats, end):
    """The whole sketch is one group shot; the lineup is made from the beats it is given."""
    return Lineup(
        PLACES,
        {
            "gary": still("open", "grin", "point"),
            "rosa": still("half", "flat", "hold"),
            "kai": still("side", "flat", "down"),
        },
        spans=((0.0, end),),
    )


def staging(cast=casting) -> Staging:
    sk = make_sketch("lineup-test", "Lineup test", ("gary", "rosa"), LINES, BEATS, END)
    return Staging(
        sk, 7, "d", "a", "n", collage_sketch.TINTS, {"gary": "living-room", "rosa": "living-room"}, cast=cast
    )


@pytest.fixture(scope="module")
def pinned_fonts() -> Path:
    """The pinned fonts folder of a generated Collage project (``SRSTUDIO_EPISODES``), or skip: the build measures
    its captions in the real font, and fetching it is network. With the pin in place, installing fetches nothing."""
    env = os.environ.get("SRSTUDIO_EPISODES")
    if not env:
        pytest.skip("set SRSTUDIO_EPISODES to the folder of generated episode projects")
    folder = Path(env) / "the-will" / "assets" / "fonts"
    if COLLAGE.font is None or not (folder / Path(COLLAGE.font.src).name).is_file():
        pytest.skip(f"no pinned Collage font in {folder}")
    return folder


def built(root: Path, st: Staging, fonts: Path):
    shutil.copytree(fonts, root / "assets" / "fonts")
    with pytest.raises(SystemExit):
        collage_sketch.build(root, st, ["--init"])
    return collage_sketch.build(root, st, [])


def test_every_group_shot_draws_the_whole_lineup_in_fixed_places_and_zooms_on_the_speaker(pinned_fonts, tmp_path):
    ep = built(tmp_path, staging(), pinned_fonts)
    root = ET.fromstring(ep.scene.to_bytes(layout="pretty"))
    shots = sketch.appearances(BEATS, END)

    def at(g, place) -> bool:
        x, y = place.transform()
        return (
            g.get("x") is not None
            and float(g.get("x")) == pytest.approx(x)
            and float(g.get("y")) == pytest.approx(y)
            and float(g.get("scaleX") or 1) == pytest.approx(place.scale)
        )

    for name, place in PLACES.items():
        # in every appearance, whoever speaks, and always in the same place
        assert sum(at(g, place) for g in root.iter("group")) == len(shots), name
    zoomed = [
        g
        for g in root.iter("group")
        if g.get("anchorX") is not None and g.find("animate[@property='scaleX']") is not None
    ]
    assert len(zoomed) == 1
    fx, fy = collage.face(collage.LOOKS["gary"])
    p = PLACES["gary"]
    x, y = p.transform()
    assert float(zoomed[0].get("anchorX")) == pytest.approx(x + fx * p.scale)
    assert float(zoomed[0].get("anchorY")) == pytest.approx(y + fy * p.scale)


def test_the_casting_is_made_from_the_beats_the_build_draws(pinned_fonts, tmp_path):
    seen = []

    def spy(beats, end):
        seen.append((tuple(beats), end))
        return solo

    built(tmp_path, staging(spy), pinned_fonts)
    assert seen == [(tuple(BEATS), END)]


def test_the_default_casting_is_the_speaker_alone():
    st = Staging(staging().sketch, 7, "d", "a", "n", {}, {"gary": "living-room", "rosa": "living-room"})
    assert st.cast(BEATS, END) is solo


def test_timer_and_flash_are_known_events_and_a_flash_is_heard_as_a_shutter(tmp_path):
    check_staging(staging())  # the timer and flash beats pass
    effects = sound_effects(BEATS, END, tmp_path, 7)
    assert [e["id"] for e in effects] == ["whoosh", "shutter"]
    assert (tmp_path / effects[-1]["audio"]).is_file()
