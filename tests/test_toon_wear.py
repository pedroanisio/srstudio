"""Things any Toon character can wear per pose: glasses, a sweat drop, a flush. The brush cast and the traced cat
take them alike, a sketch toggles them per beat, and an unknown or doubled item is refused."""

import json
import xml.etree.ElementTree as ET

import pytest
from sr_core.scene import Scene

from srstudio import PEACH, Canvas, brush, collage, flat_counter, scripting, sketch, toon, toon_cast, toon_wear
from srstudio.sketch import Beat, Line, Sketch, SketchError, Speaker
from srstudio.styles import TOON
from srstudio.toon import ToonDataError
from srstudio.voice import Voice, VoiceSettings


def canvas(duration: float = 3.0) -> Canvas:
    scene = Scene(version="auto")
    scene.add_project(width=1080, height=1920, fps="24", duration=duration, background=PEACH.background)
    return Canvas(scene, PEACH, font_asset=None, namer=flat_counter("k"))


def runs_of(cv: Canvas):
    root = ET.fromstring(cv.scene.to_bytes(layout="pretty"))
    return [g for g in root.find("composition").iter("group") if g.get("start") is not None]


def shapes(el) -> list[tuple[str, str]]:
    """(fill, path) of every shape under ``el``, in draw order."""
    return [(s.get("fill"), s.get("path")) for s in el.iter("shape")]


def test_the_wear_is_vocabulary_the_toon_cast_takes():
    assert toon.WEAR == ("glasses", "sweat", "flush")
    assert sketch.TOON_CAST.wear == toon.WEAR and collage.CAST.wear == ()
    assert "toon_wear" in TOON.parts


def test_poses_take_an_optional_list_of_things_worn():
    plain, dressed = toon.parse_poses(
        [
            {"start": 0, "eyes": "wide", "mouth": "flat", "arms": "desk"},
            {"start": 1, "eyes": "wide", "mouth": "flat", "arms": "desk", "wear": ["sweat", "glasses"]},
        ]
    )
    assert plain.wear == () and dressed.wear == ("sweat", "glasses")


@pytest.mark.parametrize(
    ("wear", "message"),
    [(["monocle"], "'monocle'"), (["sweat", "sweat"], "twice"), ("glasses", "must be a list"), ([3], "'3'|3")],
)
def test_unknown_doubled_or_mistyped_wear_is_refused(wear, message):
    with pytest.raises(ToonDataError, match=message):
        toon.parse_poses([{"start": 0, "eyes": "wide", "mouth": "flat", "arms": "desk", "wear": wear}])
    with pytest.raises(ToonDataError):
        toon_cast.figure_layers(toon_cast.FOX, "wide", "flat", "desk", wear=tuple(wear))


def test_the_cat_face_is_measured_from_the_traced_art():
    art = toon.art()
    for (cx, cy), white in zip(toon_wear.CAT_FACE.eyes, art.eyes["wide"].white, strict=True):
        x0, y0, x1, y1 = brush.bounds(white)
        assert cx == pytest.approx((x0 + x1) / 2, abs=1) and cy == pytest.approx((y0 + y1) / 2, abs=1)
        assert toon_wear.CAT_FACE.eye_r == pytest.approx((x1 - x0) / 2, abs=1.5)
    x0, y0, x1, y1 = brush.bounds(art.mouths["flat"].ink[0])
    assert toon_wear.CAT_FACE.mouth == pytest.approx(((x0 + x1) / 2, (y0 + y1) / 2), abs=1)
    assert toon_wear.CAT_FACE.mouth_w == pytest.approx(x1 - x0, abs=1)


@pytest.mark.parametrize("name", list(toon_cast.LOOKS))
def test_glasses_frame_each_eye_without_the_lenses_touching(name):
    look = toon_cast.LOOKS[name]
    under, over = toon_wear.wear_layers(toon_wear.face_of(look), ("glasses",))
    assert under == []
    lenses = [brush.bounds(s) for s, c in over if c == "ink"][:2]
    for (ex, ey), (x0, y0, x1, y1) in zip(look.eyes, lenses, strict=True):
        ring = look.eye_r + toon_cast.INK
        assert x0 < ex - ring and x1 > ex + ring and y0 < ey - ring and y1 > ey + ring
    assert lenses[0][2] < lenses[1][0]  # apart, the bridge between
    assert any(c == "white" for _, c in over)  # a glint on the glass


def test_worn_items_turn_with_a_tilted_head_and_sit_level_on_a_level_one():
    level = toon_wear.Face(((100.0, 600.0), (200.0, 600.0)), 18.0, (150.0, 650.0), 40.0)
    assert level.tilt == 0.0 and toon_wear.face_of(toon_cast.FOX).tilt == 0.0
    tilt, (cx, cy) = -6.0, (150.0, 600.0)

    def turned(p: tuple[float, float]) -> tuple[float, float]:
        x0, y0, *_ = brush.rotate((*p, *p, *p, *p), cx, cy, tilt)
        return x0, y0

    tilted = toon_wear.Face((turned(level.eyes[0]), turned(level.eyes[1])), 18.0, turned(level.mouth), 40.0, tilt)
    for items in (("glasses",), ("sweat",), ("flush",)):
        under, over = toon_wear.wear_layers(level, items)
        want = [(brush.rotate(s, cx, cy, tilt), c) for s, c in under + over]
        under, over = toon_wear.wear_layers(tilted, items)
        got = under + over
        assert [c for _, c in got] == [c for _, c in want] and [len(s) for s, _ in got] == [len(s) for s, _ in want]
        assert all(
            abs(a - b) < 0.05 for (s, _), (t, _) in zip(got, want, strict=True) for a, b in zip(s, t, strict=True)
        )


def test_a_sweat_drop_runs_down_the_temple_and_a_flush_sits_on_the_cheeks_below_the_lids():
    look = toon_cast.FOX
    (lx, ly), (rx, ry) = look.eyes
    r = look.eye_r
    under, over = toon_wear.wear_layers(toon_wear.face_of(look), ("sweat",))
    drop = [brush.bounds(s) for s, c in over if c == toon_wear.SWEAT]
    assert under == [] and len(drop) == 1 and drop[0][0] > rx + r and drop[0][3] < ry
    under, over = toon_wear.wear_layers(toon_wear.face_of(look), ("flush",))
    cheeks = [brush.bounds(s) for s, c in under if c == toon_wear.FLUSH]
    assert over == [] and len(cheeks) == 2
    for (_, y0, _, y1), (_, ey) in zip(cheeks, look.eyes, strict=True):
        assert y0 > ey + r + toon_cast.INK + 1  # clear of a blink's lids
        assert y1 < look.mouth[1] + 8
    assert cheeks[0][2] < look.mouth[0] < cheeks[1][0]


def test_the_items_draw_in_one_order_whatever_order_they_are_listed_in():
    face = toon_wear.face_of(toon_cast.BEAR)
    assert toon_wear.wear_layers(face, ("sweat", "glasses", "flush")) == toon_wear.wear_layers(
        face, ("flush", "glasses", "sweat")
    )


@pytest.mark.parametrize("name", list(toon_cast.LOOKS))
@pytest.mark.parametrize("arms", toon.ARMS)
def test_every_brush_character_wears_all_three_in_every_pose_inside_its_corner(name, arms):
    look = toon_cast.LOOKS[name]
    bare = toon_cast.figure_layers(look, "wide", "flat", arms)
    under, mouth, over = toon_cast.figure_layers(look, "wide", "flat", arms, wear=toon.WEAR)
    assert mouth == bare[1] and len(under) > len(bare[0]) and len(over) > len(bare[2])
    boxes = [brush.bounds(s) for s, _ in under + mouth + over]
    assert min(b[0] for b in boxes) > -40 and max(b[2] for b in boxes) < 440
    assert min(b[1] for b in boxes) > 360 and max(b[3] for b in boxes) < 860
    paws = bare[2][len(toon_cast._teeth(look)) if look.teeth else 0 :]
    if paws:  # paws on the face cover the glasses
        assert over[-len(paws) :] == paws


def test_the_flush_goes_under_the_nose_and_whiskers():
    look = toon_cast.RABBIT
    under, _, _ = toon_cast.figure_layers(look, "wide", "flat", "desk", wear=("flush",))
    colours = [c for _, c in under]
    assert colours.index(toon_wear.FLUSH) < len(colours) - len(look.nose) - len(toon_cast._whiskers(look))


def test_a_sigh_takes_the_glasses_down_with_the_head():
    look = toon_cast.DOG
    rest = toon_cast.figure_layers(look, "wide", "flat", "desk", wear=("glasses",))[2]
    sigh = toon_cast.figure_layers(look, "wide", "flat", "sigh", wear=("glasses",))[2]
    assert brush.bounds(sigh[0][0])[1] == pytest.approx(brush.bounds(rest[0][0])[1] + toon_cast.SIGH_DROP, abs=0.01)


def test_glasses_stay_on_over_a_blink():
    cv = canvas(8.0)
    toon_cast.fox(cv, cv.comp, [toon.Pose(0.0, "wide", "flat", "desk", ("glasses",))], 8.0)
    (run,) = runs_of(cv)
    children = list(run)
    shut = next(i for i, el in enumerate(children) if el.tag == "group" and el.find("animate") is not None)
    glasses = toon_wear.wear_layers(toon_wear.face_of(toon_cast.FOX), ("glasses",))[1]
    later = [d for el in children[shut + 1 :] for _, d in shapes(el)]
    assert all(toon.shape_d(shape) in later for shape, _ in glasses)  # drawn after the lids, never under them


def test_the_traced_cat_wears_them_too():
    cv = canvas(4.0)
    toon.cat(cv, cv.comp, [toon.Pose(0.0, "wide", "flat", "desk", toon.WEAR)], 4.0)
    (run,) = runs_of(cv)
    drawn = shapes(run)
    fills, ds = [f for f, _ in drawn], [d for _, d in drawn]
    assert toon_wear.FLUSH in fills and toon_wear.SWEAT in fills
    mouth = ds.index(toon.shape_d(toon.art().mouths["flat"].ink[0]))
    assert fills.index(toon_wear.FLUSH) < mouth < fills.index(toon_wear.SWEAT)  # cheeks under, the drop over
    glasses = toon_wear.wear_layers(toon_wear.CAT_FACE, ("glasses",))[1]
    assert ds.index(toon.shape_d(glasses[0][0])) > mouth


def speaker(name, who):
    return Speaker(name, Voice(role=name, id=f"id-{name}", name=name), VoiceSettings(0.5, 0.75, 0.2), who)


def test_a_sketch_toggles_the_wear_per_beat():
    lines = (Line("a", "My password expired again."),)
    beats = (
        Beat(0.0, "raccoon", lines[0].text, "half", "flat", "type", 0, 0),
        Beat(1.0, "raccoon", lines[0].text, "half", "flat", "type", 0, 2, wear=("glasses",)),
        Beat(2.0, "raccoon", lines[0].text, "shock", "grimace", "type", 0, 3, wear=("glasses", "sweat")),
        Beat(3.0, "raccoon", lines[0].text, "shock", "grimace", "type", None, None),
    )
    sk = Sketch("password", "Password", (speaker("a", "raccoon"),), lines, beats, 5.0)
    sketch.check(sk)
    (app,) = sketch.appearances(sk.beats, sk.end)
    assert [p.get("wear") for p in app.poses] == [None, ["glasses"], ["glasses", "sweat"], None]
    assert "wear" not in app.poses[0]  # nothing worn writes nothing: older poses files stay as they are
    cv = canvas(5.0)
    groups = sketch.draw_cast(cv, cv.comp, sk.beats, sk.end)  # one group per pose run
    assert len(groups) == 4
    worn = [{f for f, _ in shapes(g)} for g in runs_of(cv)]
    assert [toon_wear.SWEAT in fills for fills in worn] == [False, False, True, False]


def test_a_sketch_refuses_wear_its_cast_does_not_have():
    lines = (Line("a", "Hi."),)
    bad = (Beat(0.0, "fox", lines[0].text, "wide", "flat", "desk", 0, 0, wear=("hat",)),)
    with pytest.raises(SketchError, match="hat"):
        sketch.check(Sketch("hat", "Hat", (speaker("a", "fox"),), lines, bad, 3.0))
    twice = (Beat(0.0, "fox", lines[0].text, "wide", "flat", "desk", 0, 0, wear=("sweat", "sweat")),)
    with pytest.raises(SketchError, match="sweat"):
        sketch.check(Sketch("twice", "Twice", (speaker("a", "fox"),), lines, twice, 3.0))


def test_placed_beats_keep_their_wear_and_write_none_when_bare(tmp_path):
    beats = [
        Beat(0.0, "fox", "Hi.", "wide", "flat", "desk", 0, 0),
        Beat(1.0, "fox", "Hi.", "wide", "flat", "desk", None, None, "", ("flush",)),
    ]
    sketch.write_voiced(tmp_path, beats, 3.0)
    data = json.loads((tmp_path / "voiced" / "beats.json").read_text())
    assert "wear" not in data["beats"][0] and data["beats"][1]["wear"] == ["flush"]
    loaded, end = sketch.load_beats(tmp_path / "voiced" / "beats.json")
    assert loaded == beats and end == 3.0
    data["beats"][1]["wear"] = "flush"
    (tmp_path / "bad.json").write_text(json.dumps(data))
    with pytest.raises(SketchError, match="wear"):
        sketch.load_beats(tmp_path / "bad.json")


def test_the_script_helpers_take_wear():
    lines = (Line("a", "Swipe left on my bank."),)
    s = scripting.Script(lines)
    assert s.say(0.0, "fox", 0, "wide", "flat", "desk", wear=("sweat",)).wear == ("sweat",)
    assert s.first(0.0, "fox", 0, "Swipe left", "wide", "flat", "desk", wear=("glasses",)).wear == ("glasses",)
    assert s.part(0.0, "fox", 0, 2, "on my bank.", "wide", "flat", "desk", wear=("flush",)).wear == ("flush",)
    assert scripting.hold(0.0, "fox", "", "wide", "flat", "desk", wear=("flush",)).wear == ("flush",)
    assert scripting.hold(0.0, "fox", "", "wide", "flat", "desk").wear == ()


def test_the_whole_drawing_in_one_run_wears_them_too():
    under, mouth, over = toon_cast.figure_layers(toon_cast.FOX, "wide", "flat", "face", wear=toon.WEAR)
    assert toon_cast.figure_shapes(toon_cast.FOX, "wide", "flat", "face", wear=toon.WEAR) == under + mouth + over
