"""A sketch names the cast it is checked against: the Toon cast by default, another style's cast when it says so."""

import json

import pytest

from srstudio import sketch
from srstudio.sketch import Beat, Cast, Line, Sketch, Speaker
from srstudio.voice import Voice, VoiceSettings

PAPER = Cast(
    name="Collage",
    characters=("gary", "kai"),
    lip_synced=("gary", "kai"),
    eyes=("open", "side"),
    mouths=("flat", "smile"),
    arms=("down", "point"),
)


def speaker(name: str, character: str | None) -> Speaker:
    return Speaker(name, Voice(role=name, id=f"id-{name}", name=name.title()), VoiceSettings(0.5, 0.75, 0.2), character)


def paper_sketch(**kw) -> Sketch:
    lines = (Line("gary", "Name every episode."), Line("kai", "Nobody watches that."))
    beats = (
        Beat(0.0, "gary", lines[0].text, "open", "smile", "point", 0, 0),
        Beat(2.0, "kai", lines[1].text, "side", "flat", "down", 1, 0),
    )
    fields = dict(
        slug="the-lore",
        title="The Lore",
        speakers=(speaker("gary", "gary"), speaker("kai", "kai")),
        lines=lines,
        beats=beats,
        end=4.0,
        cast=PAPER,
    )
    return Sketch(**(fields | kw))


def test_the_default_cast_is_the_toon_cast():
    assert sketch.TOON_CAST.characters == sketch.CHARACTERS and sketch.TOON_CAST.lip_synced == sketch.LIP_SYNCED
    assert paper_sketch(cast=sketch.TOON_CAST).cast is sketch.TOON_CAST
    assert Sketch("s", "t", (), (), (), 1.0).cast is sketch.TOON_CAST


def test_a_sketch_is_checked_against_its_own_cast():
    sketch.check(paper_sketch())
    with pytest.raises(sketch.SketchError, match="among"):
        sketch.check(paper_sketch(cast=sketch.TOON_CAST))  # gary is not a Toon character
    toon_beat = Beat(0.0, "cat", "Name every episode.", "wide", "flat", "desk", 0, 0)
    with pytest.raises(sketch.SketchError, match="not in the Collage vocabulary"):
        sketch.check(paper_sketch(beats=(toon_beat, paper_sketch().beats[1])))
    with pytest.raises(sketch.SketchError, match="among"):
        sketch.check(paper_sketch(speakers=(speaker("gary", "cat"), speaker("kai", "kai"))))


@pytest.mark.parametrize(
    "beat",
    [
        Beat(0.0, "gary", "x", "wide", "smile", "point", 0, 0),  # a Toon eye, not a Collage one
        Beat(0.0, "gary", "x", "open", "grin", "point", 0, 0),
        Beat(0.0, "gary", "x", "open", "smile", "desk", 0, 0),
    ],
)
def test_every_expression_comes_from_the_cast_vocabulary(beat):
    with pytest.raises(sketch.SketchError, match="Collage vocabulary"):
        sketch.check(paper_sketch(beats=(beat, paper_sketch().beats[1])))


def test_place_keeps_the_cast():
    sk = paper_sketch()
    beats = sketch.place(sk, [[0.1, 0.5, 0.9], [2.2, 2.6, 2.9]], [1.4, 3.2])
    assert [b.who for b in beats] == ["gary", "kai"]


def test_the_mouth_tracks_are_read_against_the_cast(tmp_path):
    path = tmp_path / "mouths.json"
    path.write_text(json.dumps({"end": 4.0, "mouths": {"gary": [[0.0, "closed"], [0.5, "open"]]}}))
    mouths, end = sketch.load_mouths(path, PAPER)
    assert mouths == {"gary": [(0.0, "closed"), (0.5, "open")]} and end == 4.0
    with pytest.raises(sketch.SketchError, match="lip-synced"):
        sketch.load_mouths(path)  # the Toon cast has no gary


def test_a_cast_must_be_coherent():
    with pytest.raises(sketch.SketchError, match="lip-synced"):
        Cast("X", ("a",), ("b",), ("open",), ("flat",), ("down",))
    with pytest.raises(sketch.SketchError, match="vocabulary"):
        Cast("X", ("a",), (), (), ("flat",), ("down",))
