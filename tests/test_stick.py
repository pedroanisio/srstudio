"""The Stick style: traced stick figures on painted sets, badge-headed dancers, outlined captions."""

import inspect
import json
import xml.etree.ElementTree as ET

import pytest
from sr_core.scene import Scene

from srstudio import DAYLIGHT, SPEECH_MOUTH, STICK, STYLES, Canvas, EpisodeSpec, flat_counter, registry, stick
from srstudio.canvas import CanvasError
from srstudio.errors import SrstudioError
from srstudio.soundtrack import INK_MOUTH

PLATE = {"fill": "#050506", "path": "M 0 0 L 10 0 L 10 10 Z"}
ROOM_POSE = {"start": 0.0, "end": 0.5, "shot": "room", "legs": [[519.2, 471.8], [540.0, 500.0]],
             "head": [PLATE], "ink": []}  # fmt: skip
YARD_POSE = {"start": 0.5, "end": 1.0, "shot": "yard", "cx": 200.0, "cy": 820.0, "angle": -4.5,
             "centers": [[460.0, 830.0], [680.0, 826.0]], "head": [PLATE], "body": [PLATE]}  # fmt: skip
ICON = stick.Icon((430.0, 834.0), (stick.Plate("#fffdf7", "M 1 1 L 2 2 Z"),))
GRADIENT = stick.Gradient("g", ((0, "#000000"), (1, "#ffffff")), 0, 0, 10, 10)


def canvas() -> Canvas:
    scene = Scene(version="auto")
    scene.add_project(width=1080, height=1920, fps="24", duration=1.0, background="#bda77a")
    return Canvas(scene, DAYLIGHT, font_asset="inter", namer=flat_counter("n"))


# -- parsing ------------------------------------------------------------------------------------------------
def test_poses_parse_into_typed_room_and_yard_poses():
    room, yard = stick.parse_poses([ROOM_POSE, YARD_POSE])
    assert isinstance(room, stick.RoomPose) and room.legs == ((519.2, 471.8), (540.0, 500.0)) and room.ink == ()
    assert isinstance(yard, stick.YardPose) and yard.centers == ((460.0, 830.0), (680.0, 826.0)) and yard.angle == -4.5
    assert yard.head == (stick.Plate("#050506", "M 0 0 L 10 0 L 10 10 Z"),)


@pytest.mark.parametrize(
    "change, match",
    [
        (lambda p: p[0].update(shot="kitchen"), "shot"),
        (lambda p: p[0].update(colour="red"), "unknown"),
        (lambda p: p[0].pop("legs"), "missing"),
        (lambda p: p[0].update(start=True), "start must be a number"),
        (lambda p: p[0].update(end=0.0), "after start"),
        (lambda p: p[0].update(start=float("nan")), "start must be a number"),
        (lambda p: p[0].update(end=float("inf")), "end must be a number"),
        (lambda p: (p[0].update(start=-0.5), p[0].update(end=0.0)), "start -0.5 must be a second from 0"),
        (lambda p: p[0].update(legs=[[float("nan"), 1.0]]), r"\[x, y\]"),
        (lambda p: p[1].update(angle=float("inf")), "angle must be a number"),
        (lambda p: p[1].update(start=0.6), "the pose before ends"),
        (lambda p: p[0].update(legs=[[1.0]]), r"\[x, y\]"),
        (lambda p: p[0].update(head=[]), "non-empty"),
        (lambda p: p[0].update(head=[{"fill": "red", "path": "M 0 0"}]), "not a colour"),
        (lambda p: p[0].update(head=[{"fill": "#000000", "path": "L 0 0"}]), "starting with M"),
        (lambda p: p.append({**YARD_POSE, "start": 1.0, "end": 1.5, "centers": [[1.0, 2.0]]}), "dancers"),
    ],
)
def test_bad_poses_are_refused(change, match):
    poses = json.loads(json.dumps([ROOM_POSE, YARD_POSE]))
    change(poses)
    with pytest.raises(stick.StickDataError, match=match):
        stick.parse_poses(poses)


def test_icons_lettering_and_script_parse_and_refuse():
    icons = stick.parse_icons({"a": {"center": [1, 2], "paths": [{"fill": "url(#g)", "path": "M 0 0 Z"}]}})
    assert icons["a"].center == (1.0, 2.0) and icons["a"].paths[0].fill == "url(#g)"
    with pytest.raises(stick.StickDataError, match="non-empty object"):
        stick.parse_icons([])
    with pytest.raises(stick.StickDataError, match="url"):
        stick.parse_icons({"a": {"center": [1, 2], "paths": [{"fill": "url(g)", "path": "M 0 0 Z"}]}})
    letters = stick.parse_lettering({"hook": PLATE}, names=("hook",))
    assert letters["hook"].fill == "#050506"
    with pytest.raises(stick.StickDataError, match="team"):
        stick.parse_lettering({"hook": PLATE}, names=("hook", "team"))
    with pytest.raises(stick.StickDataError, match="non-empty object"):
        stick.parse_lettering([PLATE])
    lines = stick.parse_script([{"start": 0, "end": 0.5, "text": "let me just", "size": 86}])
    assert lines == [stick.Line(0.0, 0.5, "let me just", 86.0)]


@pytest.mark.parametrize(
    "items, match",
    [
        ([{"start": 0, "end": 0.5, "text": "a"}], "missing"),
        ([{"start": 0, "end": 0.5, "text": " ", "size": 80}], "empty text"),
        ([{"start": 0, "end": 0.5, "text": "a", "size": 0}], "positive"),
        ([{"start": 0, "end": 0.5, "text": "a", "size": float("nan")}], "size must be a number"),
        ([{"start": -1, "end": 0.5, "text": "a", "size": 80}], "start -1.0 must be a second from 0"),
        ([{"start": 0, "end": float("inf"), "text": "a", "size": 80}], "end must be a number"),
        ([{"start": 0, "end": 0.5, "text": "a", "size": 80}, {"start": 0.4, "end": 1, "text": "b", "size": 80}],
         "before the cue"),
        ([], "non-empty"),
    ],
)  # fmt: skip
def test_bad_scripts_are_refused(items, match):
    with pytest.raises(stick.StickDataError, match=match):
        stick.parse_script(items)


def test_files_are_read_and_unreadable_ones_refused(tmp_path):
    (tmp_path / "foliage.json").write_text(json.dumps([PLATE]))
    assert len(stick.load_plates(tmp_path / "foliage.json")) == 1
    (tmp_path / "poses.json").write_text(json.dumps([ROOM_POSE]))
    assert len(stick.load_poses(tmp_path / "poses.json")) == 1
    (tmp_path / "icons.json").write_text(json.dumps({"a": {"center": [0, 0], "paths": [PLATE]}}))
    assert list(stick.load_icons(tmp_path / "icons.json")) == ["a"]
    (tmp_path / "lettering.json").write_text(json.dumps({"hook": PLATE}))
    assert list(stick.load_lettering(tmp_path / "lettering.json", ("hook",))) == ["hook"]
    (tmp_path / "script.json").write_text(json.dumps([{"start": 0, "end": 1, "text": "a", "size": 80}]))
    assert len(stick.load_script(tmp_path / "script.json")) == 1
    (tmp_path / "bad.json").write_text("{nope")
    with pytest.raises(stick.StickDataError, match="not JSON"):
        stick.load_plates(tmp_path / "bad.json")
    with pytest.raises(stick.StickDataError, match="missing"):
        stick.load_poses(tmp_path / "absent.json")


# -- drawing conventions ------------------------------------------------------------------------------------
def xml(cv: Canvas) -> ET.Element:
    return ET.fromstring(cv.scene.to_bytes(layout="pretty"))


def by_id(root: ET.Element, id: str) -> ET.Element:
    found = root.find(f".//*[@id='{id}']")
    assert found is not None, id
    return found


def shapes(node: ET.Element) -> list[ET.Element]:
    return list(node.iter("shape"))


def test_shapes_follow_the_stick_conventions():
    cv = canvas()
    ids = [
        stick.shape(cv, cv.comp, "M 0 0 Z", "#123456").id,
        stick.shape(cv, cv.comp, "M 0 0 L 1 1", sw=3).id,
        stick.shape(cv, cv.comp, "M 0 0 L 1 1", sw=16, stroke=cv.ink).id,
        stick.box(cv, cv.comp, 0, 0, 10, 10, "#ffffff").id,
        stick.box(cv, cv.comp, 0, 0, 10, 10, "#ffffff", 3, r=8).id,
        stick.oval(cv, cv.comp, 0, 0, 4, 4, "#000000").id,
    ]
    assert ids == ["n1", "n2", "n3", "n4", "n5", "n6"]
    root = xml(cv)
    filled, stroked, inked, plain, outlined, oval = (by_id(root, i).attrib for i in ids)
    assert filled["fillRule"] == "evenodd" and filled["stroke"] == cv.clear and "strokeCap" not in filled
    assert filled["width"] == "1080" and filled["height"] == "1920"
    assert stroked["stroke"] == DAYLIGHT.shade and stroked["strokeCap"] == "round" and stroked["fill"] == cv.clear
    assert inked["stroke"] == "#070708"
    assert float(plain["radius"]) == 0 and plain["stroke"] == cv.clear
    assert outlined["stroke"] == DAYLIGHT.shade and float(outlined["radius"]) == 8
    assert oval["stroke"] == cv.clear


def test_a_gradient_is_defined_once_in_user_space():
    cv = canvas()
    assert stick.paint(cv, GRADIENT) == stick.paint(cv, GRADIENT) == "url(#g)"
    gradients = xml(cv).findall("paints/linearGradient")
    assert (
        len(gradients) == 1 and gradients[0].get("units") == "user" and "interpolationSpace" not in gradients[0].attrib
    )
    assert [float(s.get("offset")) for s in gradients[0]] == [0, 1]


# -- parts --------------------------------------------------------------------------------------------------
def test_the_sets_are_drawn_and_the_fence_follows_the_seed():
    cv = canvas()
    stick.room(cv, cv.comp)
    drawn = shapes(xml(cv).find("composition"))
    assert len(drawn) > 60 and "url(#wall)" in [s.get("fill") for s in drawn]

    def fence(seed):
        c = canvas()
        stick.yard(c, c.comp, (stick.Plate("#7e925d", "M 0 0 Z"),), seed)
        return [s.get("path") for s in shapes(xml(c)) if s.get("path", "").endswith(" 1169")]

    assert len(fence(1336)) == 19 and fence(1336) == fence(1336) != fence(7)


def test_figures_draw_one_group_per_pose_and_a_badge_per_dancer():
    cv = canvas()
    room, yard = stick.parse_poses([ROOM_POSE, YARD_POSE])
    badges = [stick.Badge(ICON, "#70a599", 47, -5.0), stick.Badge(ICON, "#fffefd", None, -5.0, GRADIENT)]
    stick.figures(cv, cv.comp, [room, yard], badges, duration=0.75)
    root = xml(cv)
    poses = root.findall("composition/group")
    assert [(float(g.get("start")), float(g.get("end"))) for g in poses] == [(0.0, 0.5), (0.5, 0.75)]  # clipped
    legs = [s for s in shapes(poses[0]) if s.get("strokeWidth") == "16"]
    assert legs[0].get("path") == "M 519.20 1382 L 471.80 1698 L 533.80 1706" and legs[0].get("stroke") == cv.ink
    bodies = [g for g in poses[1].findall("group") if g.get("rotation") is None]
    assert [(float(g.get("x")), float(g.get("y"))) for g in bodies] == [(0, 0), (260, 10), (480, 6)]
    heads = [g for g in poses[1].findall("group") if g.get("rotation") is not None]
    assert [float(h.get("rotation")) for h in heads] == [-4.5, -4.5]
    assert [h.find("shape").get("shape") for h in heads] == ["rect", "ellipse"]
    assert float(heads[0].find("shape").get("radius")) == 47
    counter = heads[0].find("group")
    assert float(counter.get("rotation")) == 5.0 and float(counter.find("group").get("x")) == -430.0
    assert [g.get("id") for g in root.findall("paints/linearGradient")] == ["g"]  # the badge's paint, once
    with pytest.raises(stick.StickDataError, match="2 dancers besides the leader, 1 badges"):
        stick.figures(cv, cv.comp, [yard], badges[:1], duration=1.0)


def test_lettering_and_captions():
    cv = canvas()
    card = stick.hook(cv, cv.comp, stick.Plate("#050506", "M 0 0 Z"), 0.0, 1.0).id
    title = stick.headline(cv, cv.comp, stick.Plate("#050506", "M 0 0 Z"), stick.Plate("#fffdfb", "M 1 1 Z"), 0, 1).id
    stick.captions(cv, cv.comp, [stick.Line(0.0, 0.5, "let me just", 86)])
    root = xml(cv)
    hook = shapes(by_id(root, card))
    assert [s.get("shape") for s in hook] == ["rect", "path"] and float(hook[0].get("radius")) == 50
    edge = shapes(by_id(root, title))[1]
    assert edge.get("stroke") == "#fffdfb" and float(edge.get("strokeWidth")) == 1.2
    text = root.find("assets/text")
    assert (text.get("text"), text.get("fontAsset"), text.get("color"), text.get("strokeColor")) == (
        "let me just", "inter", "#ffffff", "#070708")  # fmt: skip
    assert text.get("strokePosition") == "outside" and text.get("wrap") == "none"
    layer = next(root.iter("layer"))
    assert layer.get("asset") == text.get("id") and float(layer.get("y")) == stick.CAPTION_Y
    silent = Canvas(Scene(version="auto"), DAYLIGHT, font_asset=None)
    with pytest.raises(ValueError, match="caption font"):
        stick.captions(silent, silent.comp, [stick.Line(0.0, 0.5, "a", 80)])


# -- the style ----------------------------------------------------------------------------------------------
def test_the_style_value(tmp_path):
    assert STYLES["stick"] is STICK and STICK.palette() is DAYLIGHT and STICK.frame == "1080×1920 @ 24 fps"
    spec = EpisodeSpec(slug="x", title="t", description="d", root=tmp_path, seed=1, style=STICK)
    assert (spec.font, spec.font_id, spec.font_policy, spec.font_style) == (
        "assets/Inter-Bold.ttf", "inter", "pinned", "normal")  # fmt: skip
    assert spec.mouth_style is None and spec.namer is not None and spec.namer("anything") == "n1"
    assert STICK.facts()["parts"] == [
        "stick",
        "stick_airport",
        "stick_bed",
        "stick_car",
        "stick_door",
        "stick_flat",
        "stick_gym",
        "stick_home",
        "stick_office",
        "stick_roadtrip",
        "stick_school",
        "stick_shop",
        "stick_street",
        "stick_windshield",
    ]
    parts = {e.name for e in registry.entries(style="stick") if e.style == "stick"}
    assert parts == {
        "stick-room",
        "stick-yard",
        "stick-figure",
        "stick-hook",
        "stick-headline",
        "stick-captions",
        "stick-rig",
        "stick-card",
        "stick-call",
        "stick-words",
        "stick-car",
        "stick-car-seat",
        "stick-laptop",
        "stick-phone",
        "stick-cockpit",
        "stick-ride",
        "stick-studio-flat",
        "stick-murphy-bed",
        "stick-checkout",
        "stick-kiosk",
        "stick-avocado",
        "stick-name-badge",
        "stick-gym",
        "stick-gym-counter",
        "stick-classroom",
        "stick-tiny-chair",
        "stick-teacher-desk",
        "stick-essay",
        "stick-gate",
        "stick-gate-podium",
        "stick-carry-on",
        "stick-cabin",
        "stick-armrests",
        "stick-windshield",
        "stick-windshield-dash",
        "stick-entrance",
        "stick-street-lens",
        "stick-glass-door",
        "stick-snow-cap",
        "stick-marathon",
        "stick-home-street",
        "stick-side-car",
        "stick-suitcases",
        "stick-road-plan",
        "stick-top-car",
        "stick-stove-knob",
        "stick-door-lock",
        "stick-road-ahead",
        "stick-road-sign",
        "stick-coffee-corner",
        "stick-coffee-counter",
        "stick-mug",
        "stick-arm-cast",
        "stick-neck-brace",
        "stick-parrot",
        "stick-flames",
        "stick-tombstone",
        "stick-meteor",
        "stick-kitchen",
        "stick-kitchen-plan",
        "stick-from-above",
        "stick-table",
        "stick-fridge-open",
        "stick-safe-open",
        "stick-handset",
        "stick-key",
        "stick-reply-screen",
    }


# -- the rig, the camera and the hook card --------------------------------------------------------------------
TYPE = stick.RigKey(0, "type-a")
TURN = stick.RigKey(0.5, "turn", stick.Face("wide", "raised", "frown", (0, 0)))


def test_the_rig_switches_poses_and_moves_the_head_with_them():
    cv = canvas()
    g = stick.rig(cv, cv.comp, [TYPE, TURN], 1.0, blinks=(0.2,))
    root = by_id(xml(cv), g.id)
    bodies = [n for n in root.findall("group") if n.find("shape") is not None and n.get("x") is None]
    assert len(bodies) == 2  # one body per key, each gated to its span
    gates = [[(k.get("time"), k.get("value")) for k in b.find("animate").findall("key")] for b in bodies]
    assert gates == [[("0", "1"), ("0.5", "0")], [("0", "0"), ("0.5", "1"), ("1", "0")]]
    head = next(n for n in root.findall("group") if n.get("x") == "372")
    xs = [k.get("value") for a in head.findall("animate") if a.get("property") == "x" for k in a.findall("key")]
    assert xs == ["372", "360"]  # the head follows the pose: (372, 905) typing, (360, 900) turned
    blink = [a for a in head.iter("animate") if a.get("property") == "scaleY"]
    assert len(blink) == 1  # the blink at 0.2 s falls in the first span only


def test_every_blink_in_one_span_plays_not_only_the_last():
    cv = canvas()
    g = stick.rig(cv, cv.comp, [stick.RigKey(0, "type-a")], 1.0, blinks=(0.1, 0.4, 0.7))
    (blink,) = [a for a in by_id(xml(cv), g.id).iter("animate") if a.get("property") == "scaleY"]
    keys = [float(k.get(field)) for k in blink.findall("key") for field in ("time", "value")]
    dips = [v for t in (0.1, 0.4, 0.7) for v in (t, 1.0, t + 0.05, 0.1, t + 0.12, 1.0)]
    assert keys == pytest.approx([0.0, 1.0, *dips])


@pytest.mark.parametrize(
    "blinks, match",
    [
        ((0.4, 0.2), "blink 1 at 0.2"),
        ((0.2, 0.3), "blink at 0.3 must come 0.12 s after the one at 0.2"),
        ((-0.1,), "blink 0 at -0.1"),
        ((1.0,), "blink 0 at 1.0"),
        ((float("nan"),), "blink 0 at nan"),
        ((True,), "blink 0 at True"),
    ],
)
def test_blinks_must_rise_inside_the_shot_a_blink_apart(blinks, match):
    cv = canvas()
    with pytest.raises(stick.StickDataError, match=match):
        stick.rig(cv, cv.comp, [TYPE, TURN], 1.0, blinks=blinks)


def test_the_mouth_speaks_the_phones_and_closes_to_the_current_face():
    cv = canvas()
    phones = [{"c": "o", "start": 0.1, "end": 0.3}, {"c": "a", "start": 0.6, "end": 0.8}]
    stick.rig(cv, cv.comp, [TYPE, TURN], 1.0, phones=phones)
    root = xml(cv)
    paths = [s.get("path") for s in root.iter("shape")]
    assert stick.CLOSED_MOUTHS["flat"] in paths and stick.CLOSED_MOUTHS["frown"] in paths  # both faces close
    assert any(p and p.startswith("M -16 -6") for p in paths)  # open, for the 'a'
    assert any(e.get("width") == "18" for e in root.iter("shape") if e.get("shape") == "ellipse")  # round, the 'o'


def test_the_mouth_model_is_the_rigs_choice_and_ink_by_default():
    phones = [{"c": c, "start": 0.1 * i, "end": 0.1 * i + 0.09} for i, c in enumerate("mama", start=1)]

    def mouth(**kw) -> list:
        cv = canvas()
        stick.rig(cv, cv.comp, [TYPE], 1.0, phones=phones, **kw)
        return [[(k.get("time"), k.get("value")) for k in a.iter("key")] for a in xml(cv).iter("animate")]

    assert mouth() == mouth(mouth=INK_MOUTH)
    assert mouth(mouth=SPEECH_MOUTH) != mouth()  # its lead and its closed m's move the keys


def test_a_performance_the_rig_cannot_draw_is_refused():
    cases = [
        ([], "starts with a key at 0"),
        ([stick.RigKey(0.1, "type-a")], "starts with a key at 0"),
        ([TYPE, stick.RigKey(0, "lean")], "time order"),
        ([TYPE, stick.RigKey(1.0, "lean")], "at or after the end"),
        ([stick.RigKey(0, "dance")], "unknown pose"),
        ([stick.RigKey(0, "type-a", stick.Face(eyes="lasers"))], "unknown eyes"),
        ([stick.RigKey(0, "type-a", stick.Face(brows="none"))], "unknown brows"),
        ([stick.RigKey(0, "type-a", stick.Face(mouth="o"))], "unknown mouth"),
        ([stick.RigKey(0, "type-a", stick.Face(look=(2, 0)))], "look"),
        ([stick.RigKey(0, "type-a", stick.Face(look=(0,)))], "look must be two numbers"),
        ([stick.RigKey(0, "type-a", stick.Face(look=(0, 0, 0)))], "look must be two numbers"),
        ([stick.RigKey(0, "type-a", stick.Face(look=(float("nan"), 0)))], "look must be two numbers"),
        ([TYPE, stick.RigKey(float("nan"), "lean")], "time order"),
    ]
    for keys, match in cases:
        with pytest.raises(stick.StickDataError, match=match):
            stick.rig(canvas(), None, keys, 1.0)
    for end in (float("nan"), float("inf"), 0.0, True):
        with pytest.raises(stick.StickDataError, match="end must be a number of seconds over 0"):
            stick.rig(canvas(), None, [TYPE], end)


def test_every_seated_pose_and_face_draws():
    for name in stick.SEATED:
        for eyes in stick.EYES:
            for brows in stick.BROWS:
                cv = canvas()
                face = stick.Face(eyes, brows, "smirk", (-1, 1))
                stick.rig(cv, cv.comp, [stick.RigKey(0, name, face)], 1.0)
                assert len(list(xml(cv).iter("shape"))) > 10


def test_the_camera_takes_no_end_it_would_never_read():
    assert "end" not in inspect.signature(stick.camera).parameters


def test_the_camera_frames_or_pushes_in():
    cv = canvas()
    still = stick.camera(cv, cv.comp, (372, 905), zoom=2.0)
    pushed = stick.camera(cv, cv.comp, (372, 905), zoom=2.0, push=0.6)
    root = xml(cv)
    s = by_id(root, still.id)
    assert (s.get("anchorX"), s.get("x"), s.get("y"), s.get("scaleX")) == ("372", "540", "760", "2")
    p = by_id(root, pushed.id)
    assert p.get("scaleX") == "1" and {a.get("property") for a in p.findall("animate")} == {
        "scaleX",
        "scaleY",
        "x",
        "y",
    }
    for kw in (dict(zoom=0.5), dict(push=-1)):
        with pytest.raises(stick.StickDataError, match="zoom"):
            stick.camera(cv, cv.comp, (0, 0), **kw)


def test_the_hook_card_sets_its_text_in_the_caption_font():
    cv = canvas()
    g = stick.card(cv, cv.comp, "When the call runs over")
    root = xml(cv)
    text = next(root.iter("text"))
    assert (text.get("fontAsset"), text.get("color"), text.get("wrap"), text.get("maxLines")) == (
        "inter",
        DAYLIGHT.ink,
        "balance",
        "3",
    )
    assert text.get("text") == "When the call runs over" or text.text == "When the call runs over"
    assert by_id(root, g.id).find("shape").get("fill") == "#ffffff"
    x, y, w, h, _ = stick.CARD
    assert float(text.get("height")) * 1 >= 3 * 62 * 1.14  # three lines at the episode's size fit the box
    assert float(next(root.iter("layer")).get("y")) + float(text.get("height")) / 2 == y + h / 2  # centred
    with pytest.raises(stick.StickDataError, match="text"):
        stick.card(cv, cv.comp, "  ")
    cv.font_asset = None  # a silent canvas
    with pytest.raises(ValueError, match="font"):
        stick.card(cv, cv.comp, "x")


def test_the_rig_parts_are_registered():
    names = {e.name: e for e in registry.entries()}
    assert names["stick-rig"].kind == "character" and names["stick-rig"].style == "stick"
    assert names["stick-card"].kind == "graphic" and names["stick-card"].style == "stick"


# -- captions whose outline is measured apart, looks, standing figures and the call screen -------------------
def test_captions_can_draw_their_outline_as_a_layer_of_its_own():
    cv = canvas()
    stick.captions(cv, cv.comp, [stick.Line(0.0, 0.5, "see my screen?", 60)], outline="layer")
    root = xml(cv)
    under, over = root.findall("assets/text")
    assert (under.get("color"), under.get("strokeColor"), under.get("strokePosition")) == (
        "#070708", "#070708", "outside")  # fmt: skip
    assert over.get("color") == "#ffffff" and over.get("strokeColor") is None
    assert under.get("text") == over.get("text") == "see my screen?"
    layers = [layer.get("asset") for layer in root.iter("layer")]
    assert layers == [under.get("id"), over.get("id")]  # the outline is drawn first, under the white text
    plain = canvas()
    stick.captions(plain, plain.comp, [stick.Line(0.0, 0.5, "inbox.", 60)], outline="none")  # on a dark backdrop
    (only,) = xml(plain).findall("assets/text")
    assert only.get("color") == "#ffffff" and only.get("strokeColor") is None
    with pytest.raises(stick.StickDataError, match="outline"):
        stick.captions(cv, cv.comp, [stick.Line(0.0, 0.5, "a", 60)], outline="shadow")


def test_a_look_dresses_the_rig():
    plain, dressed = canvas(), canvas()
    stick.rig(plain, plain.comp, [TYPE], 1.0)
    boss = stick.Look(hair="bald", glasses=True, tie="#b8433a")
    stick.rig(dressed, dressed.comp, [TYPE, TURN], 1.0, look=boss)
    plain_paths = [s.get("path") for s in xml(plain).iter("shape")]
    dressed_shapes = list(xml(dressed).iter("shape"))
    assert stick.HAIR["cowlick"] in plain_paths
    assert stick.HAIR["cowlick"] not in [s.get("path") for s in dressed_shapes]  # bald
    assert sum(s.get("fill") == "#b8433a" for s in dressed_shapes) == 2  # a tie on each key's body
    lenses = [s for s in dressed_shapes if s.get("shape") == "rect" and s.get("stroke") == "#070708"]
    assert len(lenses) == 4  # two lenses on each key's face
    for hair in stick.HAIRS:
        cv = canvas()
        stick.rig(cv, cv.comp, [TYPE], 1.0, look=stick.Look(hair=hair))
    for look, match in ((stick.Look(hair="mohawk"), "hair"), (stick.Look(tie="red"), "tie")):
        with pytest.raises(stick.StickDataError, match=match):
            stick.rig(canvas(), None, [TYPE], 1.0, look=look)


def test_a_standing_figure_is_placed_and_scaled_anywhere():
    cv = canvas()
    keys = [stick.RigKey(0, "stand"), stick.RigKey(0.5, "wave", stick.Face(look=(-1, 0)))]
    g = stick.rig(cv, cv.comp, keys, 1.0, poses=stick.STANDING, at=(-120, 40), scale=0.9)
    node = by_id(xml(cv), g.id)
    assert (node.get("x"), node.get("y"), node.get("scaleX"), node.get("scaleY")) == ("-120", "40", "0.9", "0.9")
    assert by_id(xml(canvas_with_rig()), "n1").get("x") is None  # in place at full size: no transform
    cv = canvas()
    g = stick.rig(cv, cv.comp, keys, 1.0, poses=stick.STANDING, at=(1400, 0), flip=True)
    node = by_id(xml(cv), g.id)
    assert (node.get("x"), node.get("scaleX"), node.get("scaleY")) == ("1400", "-1", "1")  # mirrored to face left
    for name in stick.STANDING:
        cv = canvas()
        stick.rig(cv, cv.comp, [stick.RigKey(0, name)], 1.0, poses=stick.STANDING)
    with pytest.raises(stick.StickDataError, match="unknown pose"):
        stick.rig(canvas(), None, [stick.RigKey(0, "type-a")], 1.0, poses=stick.STANDING)
    with pytest.raises(stick.StickDataError, match="scale"):
        stick.rig(canvas(), None, [TYPE], 1.0, scale=0)


def canvas_with_rig() -> Canvas:
    cv = canvas()
    stick.rig(cv, cv.comp, [TYPE], 1.0)
    return cv


TILES = (stick.Tile("Boss", stick.Look(hair="bald", glasses=True)), stick.Tile("Dev", stick.Look()),
         stick.Tile("Kim", stick.Look(hair="bun")))  # fmt: skip
INBOX = (stick.Mail("HR", "Re: Dev — concerns", unread=True), stick.Mail("IT", "Your password expires"))


def test_the_call_screen_shares_an_inbox_above_the_tiles():
    cv = canvas()
    g = stick.call(cv, cv.comp, TILES, INBOX, speaking="Boss", title="Inbox (1,204)")
    root = xml(cv)
    texts = {t.get("text"): t for t in root.iter("text")}
    assert {"Boss", "Dev", "Kim", "HR", "Re: Dev — concerns", "IT", "Your password expires", "Inbox (1,204)"} <= set(
        texts
    )
    assert texts["Re: Dev — concerns"].get("weight") == "700" and texts["Your password expires"].get("weight") == "400"
    rings = [s for s in by_id(root, g.id).iter("shape") if s.get("stroke") == stick.SPEAKING]
    assert len(rings) == 1  # only the speaker's tile is ringed
    assert any(s.get("fill") == stick.LEAVE for s in root.iter("shape"))  # the red leave button
    marked = canvas()
    stick.call(marked, marked.comp, TILES, INBOX, highlight=0)
    bands = [s for s in xml(marked).iter("shape") if s.get("fill") == stick.HIGHLIGHT]
    assert len(bands) == 1 and float(bands[0].get("y")) == stick.SCREEN[1] + stick.ROW_TOP + 4
    assert not any(s.get("fill") == stick.HIGHLIGHT for s in root.iter("shape"))


def test_a_call_the_screen_cannot_show_is_refused():
    cases = [
        (dict(tiles=()), "1 to 4 tiles"),
        (dict(tiles=TILES * 2), "1 to 4 tiles"),
        (dict(inbox=()), "1 to 7 mails"),
        (dict(inbox=INBOX * 4), "1 to 7 mails"),
        (dict(speaking="Ana"), "speaking"),
        (dict(tiles=(TILES[0], TILES[0])), "names"),
        (dict(tiles=(stick.Tile(" ", stick.Look()),)), "name"),
        (dict(inbox=(stick.Mail("HR", ""),)), "subject"),
        (dict(highlight=2), "highlight"),
        (dict(highlight=-1), "highlight"),
    ]
    for change, match in cases:
        kw = dict(tiles=TILES, inbox=INBOX, speaking="Boss", highlight=None)
        kw.update(change)
        with pytest.raises(stick.StickDataError, match=match):
            stick.call(canvas(), None, kw["tiles"], kw["inbox"], speaking=kw["speaking"], highlight=kw["highlight"])
    silent = canvas()
    silent.font_asset = None
    with pytest.raises(ValueError, match="font"):
        stick.call(silent, silent.comp, TILES, INBOX)


def test_the_new_parts_are_registered():
    names = {e.name: e for e in registry.entries()}
    assert names["stick-call"].kind == "graphic" and names["stick-call"].style == "stick"
    assert "standing" in names["stick-rig"].tags and "looks" in names["stick-rig"].tags


def test_an_apron_dresses_the_torso_under_the_tie_and_is_off_by_default():
    plain, aproned = canvas(), canvas()
    stick.rig(plain, plain.comp, [TYPE], 1.0)
    stick.rig(aproned, aproned.comp, [TYPE, TURN], 1.0, look=stick.Look(apron="#2f7d57", tie="#b8433a"))
    assert stick.Look().apron is None
    assert not any(s.get("fill") == "#2f7d57" for s in xml(plain).iter("shape"))
    fills = [s.get("fill") for s in xml(aproned).iter("shape")]
    assert fills.count("#2f7d57") == 2  # an apron on each key's body
    first_apron, first_tie = fills.index("#2f7d57"), fills.index("#b8433a")
    assert first_apron < first_tie  # the tie hangs over the apron
    with pytest.raises(stick.StickDataError, match="apron"):
        stick.rig(canvas(), None, [TYPE], 1.0, look=stick.Look(apron="green"))


def test_stick_refusals_are_srstudio_errors_and_still_value_errors():
    with pytest.raises(stick.StickDataError) as caught:
        stick.parse_script([])
    with pytest.raises(CanvasError, match="no caption font") as silent:
        scene = Scene(version="auto")
        scene.add_project(width=1080, height=1920, fps="24", duration=1.0, background="#bda77a")
        cv = Canvas(scene, DAYLIGHT, font_asset=None, namer=flat_counter("n"))
        stick.card(cv, cv.comp, "hook")
    for error in (caught.value, silent.value):
        assert isinstance(error, SrstudioError) and isinstance(error, ValueError)
