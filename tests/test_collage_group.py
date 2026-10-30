"""The Collage group shot: several of the cast on one set in fixed places, held across every change of speaker, the
speaker on its beats and the others on their reactions; a zoom lands on the speaker's face in its place."""

import pytest
from sr_core.scene import Scene

from srstudio import Canvas, collage, collage_group, sketch
from srstudio.canvas import Signature
from srstudio.collage_group import GroupError, Lineup, Place
from srstudio.collage_sketch import solo, timed
from support.collage_group import PLACES, REACTIONS

LINES = (
    sketch.Line("gary", "Natural, everyone."),
    sketch.Line("rosa", "I am natural."),
    sketch.Line("gary", "Kai, headset off."),
)


def beats():
    return timed(
        LINES,
        (
            (1.5, "gary", 0, "open", "smile", "point"),
            (1.5, "rosa", 1, "half", "smug", "hold"),
            (2.0, "gary", 2, "wide", "o", "shrug", "zoom"),
        ),
        tail=1.0,
    )


def canvas(end: float) -> Canvas:
    scene = Scene(version="auto")
    scene.add_project(width=1080, height=1920, fps="24", duration=end, background=collage.PAPER.background)
    return Canvas(scene, collage.PAPER, signature=Signature())  # prefixed ids: the lineup names its places


def placed(cv: Canvas, parent, name: str):
    (g,) = [g for g in parent.find_all("group") if g.id.startswith(f"lineup-{name}")]
    return (g.x, g.y, g.scaleX, g.scaleY)


def test_every_character_holds_its_place_across_speaker_changes():
    bs, end = beats()
    lineup = Lineup(PLACES, REACTIONS, spans=((0.0, end),))
    cv = canvas(end)
    seen = {}
    for app in sketch.appearances(bs, end):
        g = cv.group(cv.comp, cv.uid("g"), start=app.start, end=app.end)
        lineup(cv, g, app, {})
        for name, place in PLACES.items():
            at = placed(cv, g, name)
            assert at == seen.setdefault(name, at)  # the same place in every shot
            s = place.scale
            assert at == (place.x - collage.CX * s, place.base - collage_group.FRAME_H * s, s, s)
    assert set(seen) == set(PLACES)


def test_the_speaker_plays_its_beats_and_the_others_their_reactions():
    bs, end = beats()
    lineup = Lineup(PLACES, REACTIONS, spans=((0.0, end),))
    apps = sketch.appearances(bs, end)
    last = apps[-1]  # Gary, from 3.0 s: Kai's reaction changed at 2.5 s, before this shot
    assert lineup.poses("gary", last) == last.poses
    assert lineup.poses("kai", last) == [{"start": 0.0, "eyes": "wide", "mouth": "o", "arms": "face"}]
    first = apps[0]  # 0 to 1.5 s
    assert lineup.poses("kai", first) == [{"start": 0.0, "eyes": "side", "mouth": "flat", "arms": "down"}]
    rosa = apps[1]  # 1.5 to 3.0 s: Kai changes 1.0 s into the shot
    assert [p["start"] for p in lineup.poses("kai", rosa)] == [0.0, 1.0]


def test_the_zoom_anchor_is_the_speaker_s_face_in_its_place():
    bs, end = beats()
    lineup = Lineup(PLACES, REACTIONS, spans=((0.0, end),))
    cv = canvas(end)
    app = sketch.appearances(bs, end)[-1]
    fx, fy = collage.face(collage.LOOKS["gary"])
    p = PLACES["gary"]
    gx, gy = p.x - collage.CX * p.scale, p.base - collage_group.FRAME_H * p.scale
    assert lineup(cv, cv.comp, app, {}) == pytest.approx((gx + fx * p.scale, gy + fy * p.scale))


def test_outside_its_spans_a_lineup_draws_the_speaker_alone_as_the_default_does():
    bs, end = beats()
    lineup = Lineup(PLACES, REACTIONS, spans=((10.0, 12.0),))
    app = sketch.appearances(bs, end)[0]
    one, two = canvas(end), canvas(end)
    assert lineup(one, one.comp, app, {}) == solo(two, two.comp, app, {})
    assert one.scene.to_bytes() == two.scene.to_bytes()


@pytest.mark.parametrize(
    "places, reactions, spans, match",
    [
        ({}, {}, ((0.0, 1.0),), "no one"),
        ({"moon": Place(540.0, 1920.0, 0.5)}, {}, ((0.0, 1.0),), "not in the Collage cast"),
        ({"gary": Place(540.0, 1920.0, 0.0)}, {"gary": REACTIONS["gary"]}, ((0.0, 1.0),), "scale"),
        ({"gary": Place(float("nan"), 1920.0, 0.5)}, {"gary": REACTIONS["gary"]}, ((0.0, 1.0),), "finite"),
        ({"gary": PLACES["gary"]}, {}, ((0.0, 1.0),), "no reactions for gary"),
        ({"gary": PLACES["gary"]}, {"gary": REACTIONS["gary"], "kai": REACTIONS["kai"]}, ((0.0, 1.0),), "kai"),
        ({"gary": PLACES["gary"]}, {"gary": REACTIONS["gary"]}, (), "span"),
        ({"gary": PLACES["gary"]}, {"gary": REACTIONS["gary"]}, ((2.0, 1.0),), "span"),
        (
            {"gary": PLACES["gary"]},
            {"gary": ({"start": 1.0, "eyes": "open", "mouth": "flat", "arms": "down"},)},
            ((0.0, 1.0),),
            "start",
        ),  # fmt: skip
        (
            {"gary": PLACES["gary"]},
            {"gary": ({"start": 0.0, "eyes": "x", "mouth": "flat", "arms": "down"},)},
            ((0.0, 1.0),),
            "eyes",
        ),  # fmt: skip
    ],
)
def test_a_lineup_refuses_what_it_cannot_stage(places, reactions, spans, match):
    with pytest.raises((GroupError, collage.CollageError), match=match):
        Lineup(places, reactions, spans=spans)


def test_a_lineup_refuses_a_speaker_it_has_no_place_for():
    bs, end = beats()
    lineup = Lineup({"rosa": PLACES["rosa"]}, {"rosa": REACTIONS["rosa"]}, spans=((0.0, end),))
    cv = canvas(end)
    with pytest.raises(GroupError, match="gary"):
        lineup(cv, cv.comp, sketch.appearances(bs, end)[0], {})
