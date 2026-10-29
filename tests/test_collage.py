"""Collage: paper cut-out people and a glossy porcelain toilet with a paper head, on painted sets (ADR 0026)."""

import re
import xml.etree.ElementTree as ET

import pytest
from sr_core.scene import Scene

from srstudio import COLLAGE, STYLES, Canvas, collage, collage_sets, flat_counter, registry, sketch, toon
from srstudio.canvas import Signature
from srstudio.toon import Pose

D = 6.0
NUM = re.compile(r"-?\d+(?:\.\d+)?")


def canvas(signed: bool = True) -> Canvas:
    scene = Scene(version="auto")
    scene.add_project(width=1080, height=1920, fps="24", duration=D, background=collage.PAPER.background)
    return Canvas(
        scene,
        collage.PAPER,
        font_asset="luckiest-guy",
        namer=flat_counter("k"),
        signature=Signature() if signed else None,
    )


def tree(cv: Canvas):
    return ET.fromstring(cv.scene.to_bytes(layout="pretty"))


def opacity_keys(cv: Canvas):
    return [
        [(float(k.get("time")), float(k.get("value"))) for k in a.iter("key")]
        for a in tree(cv).iter("animate")
        if a.get("property") == "opacity"
    ]


def points(shapes):
    """Every (x, y) a list of shapes passes through."""
    out = []
    for d, *_ in shapes:
        values = [float(v) for v in NUM.findall(d)]
        out.extend(zip(values[0::2], values[1::2], strict=True))
    return out


def pose(eyes="open", mouth="flat", arms="down", start=0.0) -> Pose:
    return Pose(start, eyes, mouth, arms)


# -- the style and the cast -------------------------------------------------------------------------------------------
def test_the_style_is_registered_with_its_parts_and_font():
    assert STYLES["collage"] is COLLAGE
    assert COLLAGE.parts == ("collage", "collage_sets") and COLLAGE.palettes == (collage.PAPER,)
    assert (COLLAGE.width, COLLAGE.height, COLLAGE.fps) == (1080, 1920, 24)
    assert COLLAGE.font.google.family == "Luckiest Guy" and COLLAGE.font.id == "luckiest-guy"
    assert COLLAGE.font.src == f"assets/fonts/{COLLAGE.font.google.slug}.ttf"


def test_the_cast_is_a_sketch_cast_with_every_look_lip_synced():
    assert isinstance(collage.CAST, sketch.Cast)
    assert collage.CAST.characters == tuple(collage.LOOKS) == tuple(collage.DRAWERS)
    assert collage.CAST.lip_synced == collage.CAST.characters
    assert (collage.CAST.eyes, collage.CAST.mouths, collage.CAST.arms) == (collage.EYES, collage.MOUTHS, collage.ARMS)
    assert len(collage.LOOKS) >= 10


def test_the_cast_is_diverse_along_the_audited_dimensions():
    looks = collage.LOOKS.values()
    assert len({lk.skin for lk in looks}) >= 5
    assert len({lk.build for lk in looks}) >= 3
    assert len({lk.hair for lk in looks}) >= 5
    assert any("cane" in lk.accents for lk in looks)
    assert sum(lk.toilet for lk in looks) == 1


def test_every_character_is_a_registered_part_of_the_style():
    entries = {e.name: e for e in registry.entries()}
    for name in collage.LOOKS:
        entry = entries[f"collage-{name}"]
        assert entry.kind == "character" and entry.style == "collage" and entry.summary
    for name in collage_sets.SETS:
        entry = entries[f"collage-{name}"]
        assert entry.kind == "location" and entry.style == "collage"
    for name in ("collage-sign", "collage-chart", "collage-tv"):
        assert entries[name].kind == "prop" and entries[name].style == "collage"


@pytest.mark.parametrize(
    "fields, match",
    [
        (dict(skin="pink"), "colour"),
        (dict(hair="mohawk"), "hair"),
        (dict(build="tall"), "build"),
        (dict(accents=("jetpack",)), "accent"),
        (dict(blink=-1.0), "blink"),
    ],
)
def test_a_look_is_checked(fields, match):
    base = dict(name="x", summary="s", skin="#a0522d", hair="short", hair_color="#222222", top="#335577")
    with pytest.raises(collage.CollageError, match=match):
        collage.Look(**(base | fields))


# -- poses ------------------------------------------------------------------------------------------------------------
def test_poses_parse_against_the_collage_vocabulary():
    poses = collage.parse_poses(
        [
            {"start": 0, "eyes": "open", "mouth": "smile", "arms": "point"},
            {"start": 1.5, "eyes": "angry", "mouth": "grin", "arms": "fist"},
        ]
    )
    assert poses == [pose("open", "smile", "point"), pose("angry", "grin", "fist", 1.5)]


@pytest.mark.parametrize(
    "data, match",
    [
        ([{"start": 0, "eyes": "shock", "mouth": "flat", "arms": "down"}], "eyes"),  # a Toon eye
        ([{"start": 0, "eyes": "open", "mouth": "flat", "arms": "desk"}], "arms"),
        ([{"start": 0.5, "eyes": "open", "mouth": "flat", "arms": "down"}], "0"),
        (
            [
                {"start": 0, "eyes": "open", "mouth": "flat", "arms": "down"},
                {"start": 0, "eyes": "open", "mouth": "flat", "arms": "down"},
            ],
            "after",
        ),
        ([{"start": 0, "eyes": "open", "mouth": "flat"}], "arms"),
        ("poses", "list"),
    ],
)
def test_malformed_poses_are_refused(data, match):
    with pytest.raises(collage.CollageError, match=match):
        collage.parse_poses(data)


# -- the drawing as data ----------------------------------------------------------------------------------------------
@pytest.mark.parametrize("name", list(collage.LOOKS))
@pytest.mark.parametrize("arms", collage.ARMS)
def test_every_figure_stays_in_its_box_below_the_captions(name, arms):
    under, mouth, over = collage.figure_shapes(collage.LOOKS[name], "open", "flat", arms)
    assert under and mouth
    x0, y0, x1, y1 = collage.FIGURE_BOX
    assert y0 > collage.CAPTION_BOTTOM
    for x, y in points(under + mouth + over):
        assert x0 <= x <= x1 and y0 <= y <= y1, (name, arms, x, y)


@pytest.mark.parametrize("eyes", collage.EYES)
@pytest.mark.parametrize("mouth", collage.MOUTHS)
def test_every_expression_draws_and_differs(eyes, mouth):
    look = collage.LOOKS["gary"]
    shapes = collage.figure_shapes(look, eyes, mouth, "down")
    other_eyes = collage.EYES[(collage.EYES.index(eyes) + 1) % len(collage.EYES)]
    other_mouth = collage.MOUTHS[(collage.MOUTHS.index(mouth) + 1) % len(collage.MOUTHS)]
    assert shapes != collage.figure_shapes(look, other_eyes, mouth, "down")
    assert shapes[1] != collage.figure_shapes(look, eyes, other_mouth, "down")[1]


def test_the_drawing_is_deterministic_and_each_character_is_cut_differently():
    a = collage.figure_shapes(collage.LOOKS["deb"], "open", "flat", "down")
    assert a == collage.figure_shapes(collage.LOOKS["deb"], "open", "flat", "down")
    b = collage.figure_shapes(collage.LOOKS["priya"], "open", "flat", "down")
    assert a[0][0][0] != b[0][0][0]  # the jittered paper edges come from the name


def test_jitter_is_a_closed_ring_near_the_ellipse():
    d = collage.jitter("k", 100, 200, 50, 40, n=24, amount=0.05)
    assert d.startswith("M") and d.endswith("Z")
    pts = points([(d,)])
    assert len(pts) == 24
    for x, y in pts:
        r = ((x - 100) / 50) ** 2 + ((y - 200) / 40) ** 2
        assert 0.8 <= r <= 1.2
    assert d != collage.jitter("j", 100, 200, 50, 40, n=24, amount=0.05)
    with pytest.raises(collage.CollageError):
        collage.jitter("k", 0, 0, 10, 10, n=2)


def test_the_toilet_is_glossy_porcelain_and_the_people_are_paper():
    flush = collage.figure_shapes(collage.LOOKS["flush"], "open", "grin", "down")
    fills = [f for _, f, *_ in flush[0]]
    assert any(f.startswith("url(#") for f in fills)  # the "CGI" gradient on the porcelain
    people = collage.figure_shapes(collage.LOOKS["brent"], "open", "grin", "down")
    assert not any(f.startswith("url(#") for _, f, *_ in people[0])


def test_accents_are_drawn():
    plain = collage.Look(name="p", summary="s", skin="#c68642", hair="short", hair_color="#111111", top="#446688")
    for accent in collage.ACCENTS:
        dressed = collage.Look(**{**plain.__dict__, "accents": (accent,)})
        assert collage.figure_shapes(dressed, "open", "flat", "down") != collage.figure_shapes(
            plain, "open", "flat", "down"
        ), accent


def test_visemes_draw_a_mouth_each():
    look = collage.LOOKS["omar"]
    seen = [collage.viseme_shapes(look, v) for v in collage.VISEMES if v != "closed"]
    assert all(seen) and len({tuple(s) for s in seen}) == len(seen)
    with pytest.raises(collage.CollageError):
        collage.viseme_shapes(look, "shout")


# -- on a canvas ------------------------------------------------------------------------------------------------------
def test_figure_draws_one_group_per_pose_run_from_its_entrance():
    cv = canvas()
    poses = [pose(), pose("side", "smug", "point", 1.0)]
    groups = collage.figure(cv, cv.comp, collage.LOOKS["jun"], poses, D, enter=2.0)
    assert [(g.start, g.end) for g in groups] == [(2.0, 3.0), (3.0, D)]
    assert all(list(g.effects) == ["collage-figure-shadow"] for g in groups)  # each pose casts a soft shadow


def test_figure_keys_the_mouth_on_the_viseme_track_and_blinks():
    cv = canvas()
    mouths = [(0.0, "closed"), (0.4, "open"), (0.6, "round"), (0.9, "closed")]
    collage.figure(cv, cv.comp, collage.LOOKS["priya"], [pose()], D, mouths=mouths)
    keys = opacity_keys(cv)
    assert [(0.0, 0.0), (0.4, 1.0), (0.6, 0.0), (0.9, 0.0)] in keys  # the open mouth
    assert any(k[0] == (0.0, 0.0) and k[1][1] == 1.0 for k in keys if len(k) > 2 and k[1][0] > 1.0)  # a blink


def test_figure_breathes_inside_each_pose_run():
    cv = canvas()
    collage.figure(cv, cv.comp, collage.LOOKS["gary"], [pose(), pose("side", "smug", "point", 1.0)], D)
    bobs = [
        [(float(k.get("time")), float(k.get("value"))) for k in a.iter("key")]
        for a in tree(cv).iter("animate")
        if a.get("property") == "y"
    ]
    assert [b[0][0] for b in bobs] == [0.0, 1.0]  # each run starts at rest
    for b in bobs:
        assert {v for _, v in b} <= {0.0, -collage.BREATH}
        assert all(round(t1 - t0, 6) <= collage.BREATH_PERIOD / 2 for (t0, _), (t1, _) in zip(b, b[1:], strict=False))


def test_a_closed_eyed_pose_does_not_blink_and_a_quiet_one_has_no_visemes():
    cv = canvas()
    collage.figure(cv, cv.comp, collage.LOOKS["feld"], [pose("closed")], D)
    assert opacity_keys(cv) == []


@pytest.mark.parametrize("enter", [-1.0, D, float("nan")])
def test_a_figure_enters_inside_the_project(enter):
    cv = canvas()
    with pytest.raises(collage.CollageError, match="enter"):
        collage.figure(cv, cv.comp, collage.LOOKS["kai"], [pose()], D, enter=enter)


def test_the_drawers_follow_the_sketch_drawer_contract():
    cv = canvas()
    for name, draw in collage.DRAWERS.items():
        groups = draw(cv, cv.comp, [pose()], D, (), enter=0.0, mouths=())
        assert len(groups) == 1, name


# -- sets and props ---------------------------------------------------------------------------------------------------
def _box(g):
    return float(g.get("x", 0)), float(g.get("y", 0)), float(g.get("scaleY", 1))


@pytest.mark.parametrize("name", list(collage_sets.SETS))
def test_every_set_signs_itself_clear_of_the_captions_and_the_figure(name):
    cv = canvas()
    collage_sets.SETS[name](cv, cv.comp)
    groups = {g.get("id"): g for g in tree(cv).iter("group")}
    cactus = [g for i, g in groups.items() if i.startswith("sig-cactus")]
    code = [g for i, g in groups.items() if i.startswith("sig-code")]
    assert len(cactus) == 1 and len(code) == 1, name
    x, y, scale = _box(cactus[0])
    top = y - collage_sets.CACTUS_HEIGHT * scale
    assert top > collage.CAPTION_BOTTOM or y < collage.CAPTION_TOP
    fx0, fy0, fx1, _ = collage.FIGURE_BOX
    assert y < fy0 or x + 60 * scale < fx0 or x - 60 * scale > fx1
    assert 0 < x < 1080 and 0 < top and y < 1920


@pytest.mark.parametrize("name", list(collage_sets.SETS))
def test_every_set_paints_a_blurred_backdrop_and_keeps_the_signature_sharp(name):
    cv = canvas()
    collage_sets.SETS[name](cv, cv.comp)
    blurred = [g for g in tree(cv).iter("group") if "collage-depth" in (g.get("effects") or "")]
    assert len(blurred) == 1, name
    assert float(blurred[0].get("scaleX")) == collage_sets.OVERSCAN  # its blur never reaches the frame's edge
    assert not [g for g in blurred[0].iter("group") if g.get("id", "").startswith("sig-")], name


def test_an_unsigned_canvas_draws_the_set_without_the_marks():
    cv = canvas(signed=False)
    collage_sets.SETS["boardroom"](cv, cv.comp)
    assert not [g for g in tree(cv).iter("group") if g.get("id", "").startswith("sig-")]


def test_props_draw_their_words_and_data():
    cv = canvas()
    collage_sets.sign(cv, cv.comp, "BOWLHEADS", 100, 900, 300, 120, size=60, tilt=-4)
    collage_sets.chart(cv, cv.comp, 600, 500, 360, 260, (0.2, 0.5, 1.0))
    collage_sets.tv(cv, cv.comp, 700, 600, 300)
    texts = [t.get("text") for t in tree(cv).iter("text")]
    assert "BOWLHEADS" in texts
    with pytest.raises(collage.CollageError, match="chart"):
        collage_sets.chart(cv, cv.comp, 0, 0, 10, 10, ())
    with pytest.raises(collage.CollageError, match="chart"):
        collage_sets.chart(cv, cv.comp, 0, 0, 10, 10, (0.5, 1.5))


# -- captions ---------------------------------------------------------------------------------------------------------
def measure(text: str) -> float:
    return 30.0 * len(text)  # a stand-in advance width: 30 px a character


def test_a_caption_wraps_into_at_most_two_lines_that_fit_the_frame():
    assert collage.caption_lines(measure, "Short one.", 1080) == ["Short one."]
    long = "We are rebranding the bank as a singing toilet"
    lines = collage.caption_lines(measure, long, 1080)
    assert len(lines) == 2 and " ".join(lines) == long
    assert all(measure(t) + collage.CAPTION_PAD <= 1080 - 2 * collage.CAPTION_MARGIN for t in lines)
    with pytest.raises(collage.CollageError, match="two lines"):
        collage.caption_lines(measure, long * 3, 1080)
    with pytest.raises(collage.CollageError, match="word"):
        collage.caption_lines(measure, "x" * 40, 1080)


def test_captions_draw_a_tinted_pill_per_cue_above_the_figure():
    cv = canvas()
    lines = [
        toon.Line("01", "Q3 was flush.", 0.0, 1.5, "brent"),
        toon.Line("02", "We are rebranding the bank as a singing toilet", 1.5, 3.0, "rosa"),
    ]
    collage.captions(cv, cv.comp, lines, measure, tints={"brent": "#ffd6a5"})
    root = tree(cv)
    shown = [t.get("text") for t in root.iter("text")]
    assert shown == ["Q3 was flush.", "We are rebranding the", "bank as a singing toilet"]
    rects = [s for s in root.iter("shape") if s.get("shape") == "rect"]
    assert [r.get("fill") for r in rects] == ["#ffd6a5", collage.PAPER.white]
    assert collage.CAPTION_TOP + float(rects[1].get("height")) <= collage.CAPTION_BOTTOM < collage.FIGURE_BOX[1]
    groups = [g for g in root.iter("group") if g.get("start") is not None]
    assert [(float(g.get("start")), float(g.get("end"))) for g in groups] == [(0.0, 1.5), (1.5, 3.0)]
    assert all(g.get("effects") == "collage-caption-shadow" for g in groups)  # each pill lifts off the set


def test_captions_need_the_style_font():
    scene = Scene(version="auto")
    scene.add_project(width=1080, height=1920, fps="24", duration=D, background="#ffffff")
    cv = Canvas(scene, collage.PAPER, font_asset=None, namer=flat_counter("k"))
    with pytest.raises(collage.CollageError, match="font"):
        collage.captions(cv, cv.comp, [toon.Line("01", "Hi.", 0.0, 1.0, "brent")], measure)


def test_the_bathroom_is_a_registered_set_with_a_shelf_for_the_signature():
    assert "bathroom" in collage_sets.SETS and "bathroom" in collage_sets.SHELVES
    entry = next(e for e in registry.entries() if e.name == "collage-bathroom")
    assert entry.kind == "location" and "goldfish-funeral" in entry.episodes
    x0, y0, x1, y1 = collage_sets.signature_box("bathroom")
    assert 0 <= x0 < x1 <= 1080 and y1 < collage.FIGURE_BOX[1] + 400
