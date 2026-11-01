"""The Toon style: typed pose, script and art loaders, the room, the desk, the traced cat and the pill captions."""

import json
import xml.etree.ElementTree as ET

import pytest
from sr_core.scene import Scene

from srstudio import PEACH, STYLES, TOON, Canvas, EpisodeSpec, flat_counter, registry, toon

D = 2.0
POSES = [
    {"start": 0.0, "eyes": "wide", "mouth": "open", "arms": "desk"},
    {"start": 0.5, "eyes": "half", "mouth": "flat", "arms": "type"},
    {"start": 1.5, "eyes": "closed", "mouth": "none", "arms": "face"},
]
SCRIPT = [
    {"start": 0.0, "end": 0.8, "text": "Anonymous Employee Survey"},
    {"start": 0.8, "end": 1.6, "text": "Do you have any feed...", "caption": "Do you have any feed..."},
    {"start": 1.6, "end": 2.0, "text": "Payday..."},
]
SQUARE = [0, 0, 0, 0, 10, 0, 10, 0, 10, 0, 10, 10, 10, 10, 10, 10, 0, 10, 0, 10, 0, 10, 0, 0, 0, 0]  # a cubic square


def canvas(font="comic-neue") -> Canvas:
    scene = Scene(version="auto")
    scene.add_project(width=1080, height=1920, fps="24", duration=D, background=PEACH.background)
    return Canvas(scene, PEACH, font_asset=font, namer=flat_counter("k"))


def measure(text: str) -> float:
    return 20.0 * len(text)


def tree(cv: Canvas):
    return ET.fromstring(cv.scene.to_bytes(layout="pretty"))


def art_data() -> dict:
    """A minimal art file in the rig's shape: every body, eye and mouth drawn as squares."""
    body = {"ink": SQUARE, "fill": SQUARE, "inner": [SQUARE], "ears": [SQUARE], "nose_ink": [], "nose_pink": [SQUARE]}
    eyes = {"ink": [SQUARE], "white": [SQUARE], "pupil": [SQUARE]}
    return {
        "schema": toon.ART_SCHEMA,
        "generated_by": "test",
        "space": {"width": toon.REF_W, "top": toon.REF_TOP, "note": "squares"},
        "bodies": {b: json.loads(json.dumps(body)) for b in toon.BODIES},
        "eyes": {e: {**eyes, "ink": [] if e == "closed" else [SQUARE]} for e in toon.TRACED_EYES},
        "mouths": {
            m: {"ink": [] if m == "none" else [SQUARE], "white": [], "red": [SQUARE]} for m in toon.TRACED_MOUTHS
        },
    }


# -- parsing ------------------------------------------------------------------------------------------------
def test_poses_parse_into_typed_records():
    poses = toon.parse_poses(POSES)
    assert poses[0] == toon.Pose(0.0, "wide", "open", "desk")
    assert poses[1].arms == "type" and poses[2].arms == "face"
    assert toon.runs(poses, D) == [(poses[0], 0.0, 0.5), (poses[1], 0.5, 1.5), (poses[2], 1.5, D)]


@pytest.mark.parametrize(
    "change, match",
    [
        (lambda p: p[0].update(eyes="laser"), "eyes 'laser' is not one of"),
        (lambda p: p[1].update(mouth="beak"), "mouth 'beak'"),
        (lambda p: p[1].update(arms="wings"), "arms 'wings'"),
        (lambda p: p[0].update(gaze=0.5), "unknown fields"),
        (lambda p: p[0].pop("mouth"), "missing"),
        (lambda p: p[0].update(start=True), "start must be a number"),
        (lambda p: p[0].update(start=float("nan")), "must be finite"),
        (lambda p: p[0].update(start=0.1), "starts at 0.1, not 0"),
        (lambda p: p[2].update(start=0.5), "not after the pose before"),
        (lambda p: p.clear(), "non-empty list"),
    ],
)
def test_bad_poses_are_refused(change, match):
    poses = json.loads(json.dumps(POSES))
    change(poses)
    with pytest.raises(toon.ToonDataError, match=match):
        toon.parse_poses(poses)


def test_runs_need_the_project_to_outlast_the_last_pose():
    with pytest.raises(toon.ToonDataError, match="not before the end"):
        toon.runs(toon.parse_poses(POSES), 1.5)
    with pytest.raises(toon.ToonDataError, match="no poses"):
        toon.runs([], D)


def test_script_parses_cues_and_strips_the_ellipsis_unless_a_caption_is_given():
    lines = toon.parse_script(SCRIPT)
    assert [q.id for q in lines] == ["01", "02", "03"]
    assert lines[1].text == "Do you have any feed..." and lines[2].text == "Payday"
    assert (lines[0].start, lines[0].end) == (0.0, 0.8)


@pytest.mark.parametrize(
    "change, match",
    [
        (lambda s: s[0].update(end=0.0), "0 <= start < end"),
        (lambda s: s[1].update(start=0.7), "before the cue before ends"),
        (lambda s: s[2].update(text="..."), "caption is empty"),
        (lambda s: s[0].update(text=3), "text must be a str"),
        (lambda s: s.append("Payday"), "expected an object"),
    ],
)
def test_bad_scripts_are_refused(change, match):
    script = json.loads(json.dumps(SCRIPT))
    change(script)
    with pytest.raises(toon.ToonDataError, match=match):
        toon.parse_script(script)


def test_files_are_read_and_unreadable_ones_refused(tmp_path):
    (tmp_path / "poses.json").write_text(json.dumps(POSES))
    (tmp_path / "script.json").write_text(json.dumps(SCRIPT))
    assert len(toon.load_poses(tmp_path / "poses.json")) == 3 and len(toon.load_script(tmp_path / "script.json")) == 3
    (tmp_path / "bad.json").write_text("{")
    with pytest.raises(toon.ToonDataError, match="not JSON"):
        toon.load_poses(tmp_path / "bad.json")
    with pytest.raises(toon.ToonDataError, match="missing"):
        toon.load_script(tmp_path / "none.json")


# -- the art file ---------------------------------------------------------------------------------------------
def test_the_art_file_parses_into_a_body_per_arm_pose_and_a_face_per_expression():
    drawn = toon.parse_art(art_data())
    assert set(drawn.bodies) == set(toon.BODIES) and set(drawn.eyes) == set(toon.TRACED_EYES)
    assert set(drawn.mouths) == set(toon.TRACED_MOUTHS)
    assert drawn.bodies["desk"].ink == tuple(float(v) for v in SQUARE) and drawn.eyes["closed"].ink == ()
    d = toon.shape_d(drawn.bodies["desk"].ink)
    assert d.startswith(f"M 0 {toon.fy(0):g} C 0 {toon.fy(0):g} {toon.fx(10):g} {toon.fy(0):g}") and d.endswith(" Z")
    assert d.count(" C ") == 4


@pytest.mark.parametrize(
    "change, match",
    [
        (lambda a: a.update(schema="toon-cat/2.0.0"), "schema 'toon-cat/2.0.0' is not"),
        (lambda a: a.update(extra=1), "unknown fields"),
        (lambda a: a["space"].update(width=1080), "drawn for 1080"),
        (lambda a: a["bodies"].pop("sigh"), "the rig draws"),
        (lambda a: a["bodies"].update(fly={}), "the rig draws"),
        (lambda a: a["eyes"]["wide"].update(ink=[]), "wide: no ink"),
        (lambda a: a["mouths"]["none"].update(ink=[SQUARE]), "none: has ink"),
        (lambda a: a["mouths"]["flat"].update(ink=[]), "flat: no ink"),
        (lambda a: a["bodies"]["desk"].update(ink=SQUARE[:7]), "whole cubic curves, got 7"),
        (lambda a: a["bodies"]["desk"].update(ink=SQUARE[:-1] + ["9"]), "coordinate '9' is not"),
        (lambda a: a["bodies"]["desk"].update(ink=SQUARE[:-1] + [float("inf")]), "coordinate inf is not"),
        (lambda a: a["bodies"]["desk"].update(ink=SQUARE[:-1] + [99999]), "coordinate 99999 is not"),
        (lambda a: a["bodies"]["desk"].update(inner="M 0 0"), "inner must be a list"),
        (lambda a: a["bodies"]["desk"].update(inner=[SQUARE, SQUARE[:5]]), r"inner\[1\]"),
        (lambda a: a["eyes"]["half"].pop("pupil"), "missing"),
        (lambda a: a.update(bodies=[]), "bodies must be a dict"),
        (lambda a: a["eyes"].update(wide=1), "expected an object"),
    ],
)
def test_bad_art_is_refused(change, match):
    data = art_data()
    change(data)
    with pytest.raises(toon.ToonDataError, match=match):
        toon.parse_art(data)


def test_the_packaged_art_is_the_traced_cat():
    drawn = toon.art()
    assert toon.art() is drawn  # parsed once
    assert all(len(b.ink) > 200 and len(b.fill) > 200 and b.ears for b in drawn.bodies.values())
    assert len(drawn.eyes["wide"].white) == 2 and len(drawn.eyes["wide"].pupil) == 2 and not drawn.eyes["closed"].white
    assert drawn.mouths["grin"].red and drawn.mouths["o"].ink and not drawn.mouths["none"].ink
    # the whole cat sits in the reference's left two thirds, above the desk's edge line
    xs = drawn.bodies["desk"].ink[0::2]
    ys = drawn.bodies["desk"].ink[1::2]
    assert -5 <= min(xs) and max(xs) <= 372 and 440 <= min(ys) and max(ys) <= 805


def test_a_missing_or_broken_art_file_is_a_typed_error(monkeypatch):
    import srstudio.toon as module

    class Missing:
        def joinpath(self, _):
            return self

        def read_text(self):
            raise FileNotFoundError("gone")

    class Broken(Missing):
        def read_text(self):
            return "{"

    toon.art.cache_clear()
    try:
        monkeypatch.setattr(module, "files", lambda _: Missing())
        with pytest.raises(toon.ToonDataError, match="not in the package"):
            toon.art()
        monkeypatch.setattr(module, "files", lambda _: Broken())
        with pytest.raises(toon.ToonDataError, match="not JSON"):
            toon.art()
    finally:
        toon.art.cache_clear()


# -- drawing ------------------------------------------------------------------------------------------------
def test_the_reference_pixels_map_to_the_frame():
    assert toon.fx(592) == 1080 and toon.fy(toon.REF_TOP) == 0 and toon.fy(1128) == pytest.approx(1930, abs=1)
    assert toon.fh(52) == toon.fx(52) > 0


def test_the_room_and_the_desk_are_drawn_in_the_reference_colours():
    cv = canvas()
    toon.room(cv, cv.comp)
    toon.desk(cv, cv.comp)
    root = tree(cv)
    shapes = list(root.find("composition").iter("shape"))
    fills = [s.get("fill") for s in shapes]
    assert fills[0] == "url(#toon-wall)" and toon.SKY in fills and toon.CHAIR in fills
    assert toon.LAPTOP in fills and toon.DESK_TOP in fills and toon.DESK_FRONT in fills
    chair = next(s for s in shapes if s.get("fill") == toon.CHAIR)
    assert chair.get("path") == toon.CHAIR_D and float(chair.get("strokeWidth")) == toon.INK_W
    grad = root.find("paints").find("linearGradient")
    assert grad.get("id") == "toon-wall" and [st.get("color") for st in grad.iter("stop")] == [c for _, c in toon.WALL]


def layers(run):
    """(fill, path) of every shape in a run, in draw order."""
    return [(s.get("fill"), s.get("path")) for s in run.iter("shape")]


def test_the_cat_holds_one_group_per_pose_drawn_from_the_traced_art():
    cv = canvas()
    poses = toon.parse_poses(POSES)
    groups = toon.cat(cv, cv.comp, poses, D)
    root = tree(cv)
    runs = [g for g in root.find("composition").iter("group") if g.get("start") is not None]
    assert len(groups) == 3 and [(g.get("start"), g.get("end")) for g in runs] == [
        ("0", "0.5"),
        ("0.5", "1.5"),
        ("1.5", "2"),
    ]
    drawn = toon.art()
    wide, typing, face = runs
    # the body: its ink band first, the blue fill over it, then the ink inside, the ears and the nose
    fills = [f for f, _ in layers(wide)]
    assert fills[:2] == [PEACH.ink, PEACH.shade] and toon.EAR in fills
    assert layers(wide)[0][1] == toon.shape_d(drawn.bodies["desk"].ink)
    # wide eyes: two whites and two pupils over the ink rings; the open mouth has its red
    assert fills.count(PEACH.white) == 2 and fills[-1] == toon.LIPS
    assert layers(wide)[-1][1] == toon.shape_d(drawn.mouths["open"].red[0])
    # every shape is filled, none stroked: the brush is traced into the shape
    assert all(s.get("stroke") == PEACH.clear for s in wide.iter("shape"))
    # with no keystrokes the typing pose draws one body (type_a) and no animation
    assert typing.find("group").find("animate") is None and len(typing.findall("group")) == 1
    assert layers(typing.find("group"))[0][1] == toon.shape_d(drawn.bodies["type_a"].ink)
    # paws on the face: no mouth, closed eyes have no whites
    assert not [f for f, _ in layers(face) if f in (toon.LIPS, PEACH.white)]
    assert layers(face)[0][1] == toon.shape_d(drawn.bodies["face"].ink)


def test_typing_frames_alternate_while_keys_are_heard():
    assert toon.typing_frames(0.5, 1.5, []) == [(0.5, 0)]
    assert toon.typing_frames(0.5, 1.5, [2.0]) == [(0.5, 0)]  # outside the run
    keys = toon.typing_frames(0.5, 1.5, [0.6, 0.7, 1.0])
    assert keys == [(0.5, 0), (0.6, 1), (0.933333, 0), (1.266667, 1), (1.333333, 0)]
    # a burst ending at the run's end never rests again; a gap wider than TYPE_GAP starts a new burst
    assert toon.typing_frames(0.0, 1.0, [0.9]) == [(0.0, 0), (0.9, 1)]
    assert toon.typing_frames(0.0, 3.0, [0.1, 2.0])[1:] == [(0.1, 1), (0.433333, 0), (2.0, 1), (2.333333, 0)]


def test_a_typing_pose_swaps_its_two_bodies_on_the_keystrokes_it_contains():
    cv = canvas()
    toon.cat(cv, cv.comp, toon.parse_poses(POSES), D, taps=(0.2, 0.6, 0.7, 1.0, 1.7))
    runs = [g for g in tree(cv).find("composition").iter("group") if g.get("start") is not None]
    assert [len(g.findall("group")) for g in runs] == [0, 2, 0]  # only the typing pose has body frames
    rest, struck = runs[1].findall("group")
    drawn = toon.art()
    assert layers(rest)[0][1] == toon.shape_d(drawn.bodies["type_a"].ink)
    assert layers(struck)[0][1] == toon.shape_d(drawn.bodies["type_b"].ink)
    for g, first in ((rest, 1), (struck, 0)):
        a = g.find("animate")
        assert (a.get("property"), a.get("timeBase")) == ("opacity", None)  # on the composition clock
        keys = [(float(k.get("time")), float(k.get("value"))) for k in a.iter("key")]
        assert keys[0] == (0.5, first) and len(keys) == 5
    assert [float(k.get("time")) for k in struck.find("animate").iter("key")] == [
        0.5,
        0.6,
        0.933333,
        1.266667,
        1.333333,
    ]
    # the face is drawn once, outside the frames
    assert sum(1 for s in runs[1].findall("shape") if s.get("fill") == PEACH.white) == 2
    with pytest.raises(toon.ToonDataError, match="taps"):
        toon.cat(canvas(), cv.comp, toon.parse_poses(POSES), D, taps=(-1,))
    with pytest.raises(toon.ToonDataError, match="taps"):
        toon.cat(canvas(), cv.comp, toon.parse_poses(POSES), D, taps=(True,))


def test_captions_sit_in_measured_pills_in_the_style_font():
    cv = canvas()
    lines = toon.parse_script(SCRIPT)
    toon.captions(cv, cv.comp, lines, measure)
    root = tree(cv)
    pills = [s for s in root.find("composition").iter("shape") if s.get("shape") == "rect"]
    assert len(pills) == 3
    width = toon.pill_width(measure, "Anonymous Employee Survey")
    assert width == 20 * 25 + toon.CAPTION_PAD
    assert float(pills[0].get("width")) == width and float(pills[0].get("x")) == pytest.approx(540 - width / 2)
    assert float(pills[0].get("radius")) == toon.CAPTION_RADIUS and pills[0].get("fill") == PEACH.white
    assert toon.pill_width(measure, "I") >= round(toon.fh(toon.CAPTION_H))  # never narrower than it is tall
    texts = root.find("assets").findall("text")
    assert [t.get("text") for t in texts] == ["Anonymous Employee Survey", "Do you have any feed...", "Payday"]
    assert texts[0].get("fontAsset") == "comic-neue" and texts[0].get("size") == str(toon.CAPTION_SIZE)
    layers = [g for g in root.find("composition").iter("group") if g.get("start") is not None]
    assert [(g.get("start"), g.get("end")) for g in layers] == [("0", "0.8"), ("0.8", "1.6"), ("1.6", "2")]
    with pytest.raises(ValueError, match="no caption font"):
        toon.captions(canvas(font=None), cv.comp, lines, measure)


def test_a_shot_can_lower_the_caption_band():
    default, lowered = canvas(), canvas()
    lines = toon.parse_script(SCRIPT)
    toon.captions(default, default.comp, lines, measure)
    toon.captions(lowered, lowered.comp, lines, measure, band=toon.CAPTION_TOP + 12)
    pill = lambda cv: next(s for s in tree(cv).find("composition").iter("shape") if s.get("shape") == "rect")  # noqa: E731
    assert float(pill(default).get("y")) == round(toon.fy(toon.CAPTION_TOP))
    assert float(pill(lowered).get("y")) == round(toon.fy(toon.CAPTION_TOP + 12))


# -- the style ------------------------------------------------------------------------------------------------
def test_the_style_value(tmp_path):
    assert STYLES["toon"] is TOON and TOON.silent and TOON.font.google.italic and TOON.font.style == "italic"
    spec = EpisodeSpec(slug="x", title="x", description="x", root=tmp_path, seed=1, style=TOON)
    assert (spec.width, spec.height, spec.fps, spec.dialogue) == (1080, 1920, 24, "script.json")
    assert spec.font_id == "comic-neue" and spec.font_style == "italic" and spec.font_policy == "pinned"
    assert spec.mouth_style is None and spec.background == PEACH.background
    names = {e["name"] for e in registry.catalog(style="toon")}
    assert {"toon-room", "toon-desk", "toon-cat", "toon-captions"} <= names


@pytest.mark.parametrize("arms", toon.ARMS)
@pytest.mark.parametrize("eyes", toon.TRACED_EYES)
@pytest.mark.parametrize("mouth", toon.TRACED_MOUTHS)
def test_every_expression_draws_from_its_traced_part(eyes, mouth, arms):
    cv = canvas()
    pose = toon.Pose(0.0, eyes, mouth, arms)
    (g,) = toon.cat(cv, cv.comp, [pose], D)
    (run,) = [g for g in tree(cv).find("composition").iter("group") if g.get("start") is not None]
    drawn = toon.art()
    paths = [p for _, p in layers(run)]
    body = drawn.bodies["type_a" if arms == "type" else arms]
    assert paths[:2] == [toon.shape_d(body.ink), toon.shape_d(body.fill)]
    for shape in drawn.eyes[eyes].ink + drawn.eyes[eyes].pupil + drawn.mouths[mouth].ink + drawn.mouths[mouth].red:
        assert toon.shape_d(shape) in paths
    whites = [p for f, p in layers(run) if f == PEACH.white]
    assert len(whites) == len(drawn.eyes[eyes].white) + len(drawn.mouths[mouth].white)
    assert (eyes == "closed") == (not whites) and (mouth == "none") == (not drawn.mouths[mouth].ink)


def test_a_cue_may_name_its_speaker_and_the_pills_take_that_speaker_s_tint():
    script = [dict(q) for q in SCRIPT]
    script[1]["speaker"] = "boss"
    lines = toon.parse_script(script)
    assert [q.speaker for q in lines] == ["", "boss", ""]
    cv = canvas()
    toon.captions(cv, cv.comp, lines, measure, tints={"boss": "#dff1ff"})
    pills = [s for s in tree(cv).find("composition").iter("shape") if s.get("shape") == "rect"]
    assert [p.get("fill") for p in pills] == [PEACH.white, "#dff1ff", PEACH.white]
    with pytest.raises(toon.ToonDataError, match="speaker must be a str"):
        toon.parse_script([{**script[0], "speaker": 3}])


def test_the_cat_can_enter_later_and_its_poses_count_from_then():
    cv = canvas()
    poses = toon.parse_poses([{"start": 0.0, "eyes": "wide", "mouth": "open", "arms": "desk"}])
    toon.cat(cv, cv.comp, poses, D, enter=1.0)
    runs = [g for g in tree(cv).find("composition").iter("group") if g.get("start") is not None]
    assert [(g.get("start"), g.get("end")) for g in runs] == [("1", str(D).rstrip("0").rstrip("."))]
    with pytest.raises(toon.ToonDataError, match="enter must be"):
        toon.cat(canvas(), cv.comp, poses, D, enter=D)
