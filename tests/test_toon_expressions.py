"""The Toon expressions past the traced set: eyes that roll, tear up, wince and fall in love, mouths that grimace,
frown, stick out a tongue and pucker. Every brush character draws them; the traced cat refuses them by name."""

import xml.etree.ElementTree as ET

import pytest
from sr_core.scene import Scene

from srstudio import PEACH, Canvas, brush, flat_counter, sketch, toon, toon_cast
from srstudio.sketch import Beat, Line, Sketch, Speaker
from srstudio.toon import ToonDataError
from srstudio.voice import Voice, VoiceSettings

NEW_EYES = ("roll", "teary", "wince", "hearts")
NEW_MOUTHS = ("grimace", "frown", "tongue", "kiss")


def canvas(duration: float = 3.0) -> Canvas:
    scene = Scene(version="auto")
    scene.add_project(width=1080, height=1920, fps="24", duration=duration, background=PEACH.background)
    return Canvas(scene, PEACH, font_asset=None, namer=flat_counter("k"))


def runs_of(cv: Canvas):
    root = ET.fromstring(cv.scene.to_bytes(layout="pretty"))
    return [g for g in root.find("composition").iter("group") if g.get("start") is not None]


def test_the_vocabulary_grows_past_what_the_cat_was_traced_with():
    assert toon.EYES == (*toon.TRACED_EYES, *NEW_EYES, "sleepy")  # sleepy: ADR 0045, tests/test_toon_critters.py
    assert toon.MOUTHS == (*toon.TRACED_MOUTHS, *NEW_MOUTHS, "yawn", "scream", "puff")
    assert set(toon.art().eyes) == set(toon.TRACED_EYES) and set(toon.art().mouths) == set(toon.TRACED_MOUTHS)
    assert sketch.TOON_CAST.eyes == toon.EYES and sketch.TOON_CAST.mouths == toon.MOUTHS
    poses = toon.parse_poses([{"start": 0, "eyes": "hearts", "mouth": "kiss", "arms": "face"}])
    assert (poses[0].eyes, poses[0].mouth) == ("hearts", "kiss")


@pytest.mark.parametrize("name", list(toon_cast.LOOKS))
def test_every_brush_character_draws_every_new_eye_unlike_any_older_one(name):
    look = toon_cast.LOOKS[name]
    older = {kind: toon_cast.figure_layers(look, kind, "flat", "desk")[0] for kind in toon.TRACED_EYES}
    for kind in NEW_EYES:
        mine = toon_cast.figure_layers(look, kind, "flat", "desk")[0]
        assert all(mine != theirs for theirs in older.values()), f"{name}'s {kind} eyes repeat an older pair"


@pytest.mark.parametrize("name", list(toon_cast.LOOKS))
def test_every_brush_character_draws_every_new_mouth_unlike_any_older_one(name):
    look = toon_cast.LOOKS[name]
    older = [toon_cast.figure_layers(look, "wide", kind, "desk")[1] for kind in toon.TRACED_MOUTHS]
    for kind in NEW_MOUTHS:
        mine = toon_cast.figure_layers(look, "wide", kind, "desk")[1]
        assert mine and all(mine != theirs for theirs in older), f"{name}'s {kind} mouth repeats an older one"


def eye_layers(look, kind):
    """The layers of the left eye of ``kind``, its brow first when the look has brows."""
    return toon_cast._eye(look, look.eyes[0], kind, 1.0)


def test_rolled_eyes_look_up_and_aside_over_a_raised_lower_lid():
    look = toon_cast.FOX
    (ex, ey), r = look.eyes[0], look.eye_r
    layers = [(s, c) for s, c in eye_layers(look, "roll")]
    pupils = [brush.bounds(s) for s, c in layers if c == "ink" and brush.bounds(s)[2] - brush.bounds(s)[0] < r]
    px = (pupils[-1][0] + pupils[-1][2]) / 2
    py = (pupils[-1][1] + pupils[-1][3]) / 2
    assert py < ey - 0.4 * r and px > ex + 0.2 * r  # up and to the side, the same side for both eyes
    right = toon_cast._eye(look, look.eyes[1], "roll", -1.0)
    rpupil = [brush.bounds(s) for s, c in right if c == "ink" and brush.bounds(s)[2] - brush.bounds(s)[0] < r][-1]
    assert (rpupil[0] + rpupil[2]) / 2 > look.eyes[1][0] + 0.2 * r
    lid = [brush.bounds(s) for s, c in layers if c == look.coat]
    assert lid and lid[0][1] > ey and lid[0][3] >= ey + r  # a lid rising from below, not falling from above


def test_teary_eyes_glisten_and_shed_a_tear():
    look = toon_cast.DOG
    layers = eye_layers(look, "teary")
    assert sum(1 for _, c in layers if c == "white") >= 3  # the white and two highlights, shine or not
    tears = [brush.bounds(s) for s, c in layers if c == toon_cast.TEAR]
    assert tears and tears[0][1] > look.eyes[0][1] + look.eye_r * 0.5  # under the eye


def test_a_wince_squeezes_each_eye_shut_toward_the_nose():
    look = toon_cast.BEAR
    left = eye_layers(look, "wince")
    assert not any(c == "white" for _, c in left)
    chevron = brush.bounds([s for s, c in left if c == "ink"][-1])
    ex, ey = look.eyes[0]
    assert chevron[2] > ex and chevron[0] < ex  # a > on the left eye, pointing at the nose
    assert chevron[1] < ey - 0.3 * look.eye_r and chevron[3] > ey + 0.3 * look.eye_r


def test_heart_eyes_are_red_hearts_in_ink():
    look = toon_cast.RABBIT
    layers = eye_layers(look, "hearts")
    hearts = [brush.bounds(s) for s, c in layers if c == toon_cast.HEART]
    assert len(hearts) == 1
    x0, y0, x1, y1 = hearts[0]
    ex, ey = look.eyes[0]
    assert x0 < ex < x1 and y0 < ey < y1
    assert not any(c == "white" for _, c in layers)  # no eye white behind them


@pytest.mark.parametrize("kind", ["teary", "wince"])
def test_pained_brows_lift_at_the_inner_end(kind):
    look = toon_cast.FOX
    ex, _ = look.eyes[0]
    shape, _ = toon_cast._brow(look, look.eyes[0], kind, 1.0)
    path = [(shape[i], shape[i + 1]) for i in range(0, len(shape), 2)]
    inner = [y for x, y in path if x > ex + look.eye_r * 0.5]
    outer = [y for x, y in path if x < ex - look.eye_r * 0.5]
    assert min(inner) < min(outer) - 4


def test_the_frown_brow_is_unchanged():
    look = toon_cast.FOX
    narrow = toon_cast._brow(look, look.eyes[0], "narrow", 1.0)[0]
    assert narrow == brush.stroke(
        [(look.eyes[0][0] - look.eye_r * 1.05, look.eyes[0][1] - look.eye_r - toon_cast.INK - 7.0 - 5.0),
         (look.eyes[0][0] + look.eye_r * 0.9, look.eyes[0][1] - look.eye_r - toon_cast.INK - 7.0 + 9.0)],
        toon_cast.INK * 0.95,
    )  # fmt: skip


def test_the_new_mouths_read_as_what_they_are():
    look = toon_cast.FOX
    mx, my = look.mouth
    grimace = toon_cast._mouth(look, "grimace")
    assert [c for _, c in grimace[:2]] == ["ink", "white"] and len(grimace) >= 5  # clenched teeth between lines
    assert brush.bounds(grimace[0][0])[2] - brush.bounds(grimace[0][0])[0] > look.mouth_w
    frown = toon_cast._mouth(look, "frown")[0][0]
    x0, y0, x1, y1 = brush.bounds(frown)
    assert y0 < my - 4 and (x1 - x0) > look.mouth_w * 0.8  # the middle rides above the corners
    tongue = toon_cast._mouth(look, "tongue")
    assert toon_cast.TONGUE in [c for _, c in tongue]
    assert max(brush.bounds(s)[3] for s, c in tongue if c == toon_cast.TONGUE) > my + 12  # hanging out
    kiss = toon_cast._mouth(look, "kiss")
    assert all(brush.bounds(s)[2] - brush.bounds(s)[0] < look.mouth_w * 0.6 for s, _ in kiss)  # a small pucker


@pytest.mark.parametrize("eyes", ["wince", "hearts", "closed"])
def test_eyes_that_are_not_open_do_not_blink(eyes):
    cv = canvas(8.0)
    toon_cast.fox(cv, cv.comp, [toon.Pose(0.0, eyes, "flat", "desk")], 8.0)  # the fox blinks every 3.8 s
    (run,) = runs_of(cv)
    assert not [g for g in run.findall("group") if g.find("animate") is not None]


@pytest.mark.parametrize("eyes", ["roll", "teary"])
def test_open_new_eyes_still_blink(eyes):
    cv = canvas(8.0)
    toon_cast.fox(cv, cv.comp, [toon.Pose(0.0, eyes, "flat", "desk")], 8.0)  # the fox blinks every 3.8 s
    (run,) = runs_of(cv)
    assert [g for g in run.findall("group") if g.find("animate") is not None]


@pytest.mark.parametrize(("eyes", "mouth", "named"), [("hearts", "flat", "hearts"), ("wide", "tongue", "tongue")])
def test_the_traced_cat_refuses_what_it_was_not_traced_with_by_name_drawing_nothing(eyes, mouth, named):
    cv = canvas(4.0)
    poses = [toon.Pose(0.0, "wide", "flat", "desk"), toon.Pose(2.0, eyes, mouth, "desk")]
    with pytest.raises(ToonDataError, match=f"traced cat has no {named!r}"):
        toon.cat(cv, cv.comp, poses, 4.0)
    assert runs_of(cv) == []


def test_the_cat_still_draws_every_traced_expression():
    cv = canvas(4.0)
    poses = [
        toon.Pose(float(i) * 0.2, e, m, "desk")
        for i, (e, m) in enumerate(zip(toon.TRACED_EYES, toon.TRACED_MOUTHS, strict=True))
    ]
    assert len(toon.cat(cv, cv.comp, poses, 4.0)) == len(poses)


def test_a_sketch_plays_new_expressions_and_the_cat_refuses_them_at_the_draw():
    lines = (Line("a", "Swipe right."), Line("b", "No."))

    def speaker(name, who):
        return Speaker(name, Voice(role=name, id=f"id-{name}", name=name), VoiceSettings(0.5, 0.75, 0.2), who)

    beats = (
        Beat(0.0, "fox", lines[0].text, "hearts", "kiss", "face", 0, 0),
        Beat(2.0, "cat", lines[1].text, "roll", "frown", "crossed", 1, 0),
    )
    sk = Sketch("swipe", "Swipe", (speaker("a", "fox"), speaker("b", "cat")), lines, beats, 4.0)
    sketch.check(sk)
    cv = canvas(4.0)
    with pytest.raises(ToonDataError, match="traced cat has no 'roll'"):
        sketch.draw_cast(cv, cv.comp, sk.beats, sk.end)
    cv = canvas(4.0)
    assert len(sketch.draw_cast(cv, cv.comp, sk.beats[:1], sk.end)) == 1


@pytest.mark.parametrize(("mouth", "teeth"), [("grimace", False), ("kiss", False), ("tongue", True), ("frown", True)])
def test_front_teeth_stay_out_of_a_clenched_or_puckered_mouth(mouth, teeth):
    over = toon_cast.figure_layers(toon_cast.RABBIT, "wide", mouth, "desk")[2]
    assert (over[: len(toon_cast._teeth(toon_cast.RABBIT))] == toon_cast._teeth(toon_cast.RABBIT)) == teeth
