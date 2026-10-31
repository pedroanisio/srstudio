"""The Toon figure in nested groups (ADR 0050): a head that turns about its neck with its seam hidden, one kind of
motion per group, every rig run through the same checks, and the flat figure every published reel was drawn with left
byte for byte."""

import hashlib
import math
import xml.etree.ElementTree as ET
from dataclasses import replace

import pytest
from sr_core.scene import Scene

import srstudio
from srstudio import (
    PEACH,
    Canvas,
    flat_counter,
    head_motion,
    parts,
    toon,
    toon_cast,
    toon_critters,
    toon_head,
    toon_inked,
    toon_rigs,
)
from srstudio.head_motion import HeadMotionError, HeadPlan, limit
from srstudio.toon import Pose, ToonDataError, fh, fx, fy
from support.spring_curve import sample

RIG = toon_critters.SLOTH_RIG
STYLE = toon_critters.SLOTH_MOTION
POSES = [
    Pose(0.0, "sleepy", "flat", "desk"),
    Pose(2.0, "half", "smirk", "type", ("glasses",)),
    Pose(4.0, "wide", "yawn", "sigh"),
    Pose(5.0, "shock", "o", "lean", ("sweat", "flush")),
    Pose(6.0, "hearts", "kiss", "face"),
]
MOUTHS = [(0.4, "open"), (0.6, "round"), (0.9, "teeth"), (1.2, "closed"), (2.3, "open"), (2.6, "closed")]
TAPS = (2.2, 2.4, 2.9)
PINS = {
    "sloth": "711eec1f46d89602b625549f1a0ae92f56548561c1f41a54b3228415ab4936e0",
    "dog": "71a10718403490ee97635a2c8faecccb1fa0b83f2ef1b693a2b08cd1ee52cd7e",
}
RIGGED_SLOTH_PIN = "c0c168af21f402d1c4b4e9cfb366ae9f5771964d6bd5f619278d2bcc0df670c6"  # the approved clips' rig
HEAD_TOP = 170.0  # reference pixels from the neck to the crown
EVERY_RIG = pytest.mark.parametrize("rig", list(toon_rigs.RIGS.values()), ids=list(toon_rigs.RIGS))


def stage() -> tuple[Scene, Canvas]:
    scene = Scene(version="auto")
    scene.add_project(width=1080, height=1920, fps="24", duration=8.0, background=PEACH.background)
    return scene, Canvas(scene, PEACH, font_asset=None)


def drawn(plan: HeadPlan | None = None, poses=POSES, rig=RIG, **kw) -> ET.Element:
    scene, cv = stage()
    plan = hm_plan() if plan is None else plan
    toon_head.figure(cv, cv.comp, rig, poses, 8.0, plan, **kw)
    return ET.fromstring(scene.to_bytes(layout="pretty"))


def hm_plan(duration: float = 8.0) -> HeadPlan:
    return head_motion.plan(STYLE, [], duration)


def group(root: ET.Element, name: str) -> ET.Element:
    return next(node for node in root.iter("group") if node.get("id", "").startswith(f"{name}-"))


def animates(node: ET.Element) -> dict[str, ET.Element]:
    return {a.get("property"): a for a in node.findall("animate")}


# -- the published figure ----------------------------------------------------------------------------------------------
@pytest.mark.parametrize("name, look", (("sloth", toon_critters.SLOTH), ("dog", toon_cast.DOG)))
def test_the_flat_figure_is_byte_identical(name, look):
    scene = Scene(version="auto")
    scene.add_project(width=1080, height=1920, fps="24", duration=8.0, background=PEACH.background)
    cv = Canvas(scene, PEACH, font_asset=None, namer=flat_counter("k"))
    toon_cast.figure(cv, cv.comp, look, POSES, 8.0, TAPS, 0.0, (), MOUTHS)
    assert hashlib.sha256(scene.to_bytes(layout="pretty")).hexdigest() == PINS[name]


def test_the_rig_is_opt_in_the_sloth_itself_keeps_its_tilted_vertices():
    assert toon_critters.SLOTH_CRITTER.tilt == RIG.tilt != 0.0
    assert RIG.look.drawing is not None
    assert RIG.look != toon_critters.SLOTH


# -- the nesting -------------------------------------------------------------------------------------------------------
def test_each_group_carries_one_kind_of_motion_and_the_head_goes_behind_the_body():
    root = drawn()
    lean, breath = group(root, "lean"), group(root, "breath")
    assert breath in list(lean)
    children = [node.get("id", "").split("-")[0] for node in breath.findall("group")]
    assert children == ["turn", "trunk", "front"]  # the trunk paints over the head chain
    assert group(group(root, "turn"), "nod") is group(root, "nod")
    assert group(group(root, "nod"), "idle") is group(root, "idle")
    assert group(group(root, "idle"), "lift") is group(root, "lift")
    assert [n.get("id", "").split("-")[0] for n in group(root, "lift").findall("group")] == ["skull", "face"]
    for name in ("lean", "breath", "turn", "nod", "idle", "lift", "face"):
        kinds = list(animates(group(root, name)))
        assert len(kinds) == len(set(kinds))  # never two sources on one property


def test_the_head_turns_about_the_neck_with_its_drawn_tilt_at_rest():
    turn = group(drawn(), "turn")
    assert float(turn.get("anchorX")) == pytest.approx(fx(RIG.neck[0]), abs=0.01)
    assert float(turn.get("anchorY")) == pytest.approx(fy(RIG.neck[1]), abs=0.01)
    assert float(turn.get("rotation")) == RIG.tilt
    keys = animates(turn)["rotation"].findall("key")
    assert float(keys[0].get("value")) == pytest.approx(RIG.tilt)


def test_spring_keys_are_the_engine_s_own_and_carry_their_momentum_after_the_first():
    speech = head_motion.Speech(1.0, head_motion.words_of(_take(), 1.0), (-20.0,) * 300)
    plan = head_motion.plan(STYLE, [speech], 8.0)
    a = animates(group(drawn(plan), "nod"))["y"]
    assert a.get("defaultInterpolation") == "spring"
    keys = a.findall("key")
    assert len(keys) == len(plan.nod.keys)
    assert keys[0].get("carry") is None
    assert all(k.get("carry") == "true" for k in keys[1:])
    assert keys[1].get("stiffness") == STYLE.head.attributes()["stiffness"]


def test_spring_cut_after_restart_matches_in_renderer(tmp_path, scene_render):
    import json
    import subprocess

    scene = Scene(version='auto')
    scene.add_project(width=100, height=100, fps='24', duration=12)
    cv = Canvas(scene, font_asset=None)
    channel = head_motion.Channel(tuple((float(i), float(i % 2) * 10) for i in range(13)), head_motion.Spring(0.5, 0.2))
    toon_head._animate(cv, cv.group(cv.comp, 'first'), 'y', channel.during(0, 8.5))
    toon_head._animate(cv, cv.group(cv.comp, 'second'), 'y', channel.during(8.5, 12))
    path = tmp_path / 'cut.scene.xml'
    path.write_bytes(scene.to_bytes())
    for time in (8.49, 8.5, 8.51):
        result = subprocess.run(
            [str(scene_render), 'eval', str(path), '--time', str(time), '--json'],
            capture_output=True,
            text=True,
            check=True,
        )
        nodes = json.loads(result.stdout)['result']['nodes']
        values = {node['id']: node['world'][5] for node in nodes if node['id'] in ('first', 'second')}
        assert values['first'] == pytest.approx(values['second'], abs=1e-5)


@pytest.mark.parametrize('damping', [0.2, 1.0, 1.4])
def test_long_spring_preserves_carried_motion_at_restart(tmp_path, scene_render, damping):
    import json
    import subprocess

    scene = Scene(version='auto')
    scene.add_project(width=100, height=100, fps='24', duration=12)
    cv = Canvas(scene, font_asset=None)
    channel = head_motion.Channel(
        tuple((float(i), float(i % 2) * 10) for i in range(13)), head_motion.Spring(0.5, damping)
    )
    toon_head._animate(cv, cv.group(cv.comp, 'actual'), 'y', channel)
    expected = cv.group(cv.comp, 'expected')
    a = expected.add_animate(property='y', defaultInterpolation='spring')
    for i, (t, value) in enumerate(channel.keys):
        a.add_key(time=t, value=str(value), **channel.spring.attributes(), **({'carry': 'true'} if i else {}))
    path = tmp_path / 'spring.scene.xml'
    path.write_bytes(scene.to_bytes())
    for time in (7.99, 8.001, 8.1, 8.5):
        result = subprocess.run(
            [str(scene_render), 'eval', str(path), '--time', str(time), '--json'],
            capture_output=True,
            text=True,
            check=True,
        )
        nodes = json.loads(result.stdout)['result']['nodes']
        values = {node['id']: node['world'][5] for node in nodes if node['id'] in ('actual', 'expected')}
        assert values['actual'] == pytest.approx(values['expected'], abs=0.01)


def test_long_spring_budget_failure_does_not_mutate_scene():
    scene, cv = stage()
    before = scene.to_bytes()
    channel = head_motion.Channel(tuple((float(i * 100), float(i)) for i in range(10)), head_motion.Spring(0.5, 0.7))
    with pytest.raises(HeadMotionError, match='sampling budget'):
        toon_head.figure(cv, cv.comp, RIG, POSES, 8, HeadPlan(turn=channel))
    assert scene.to_bytes() == before


def _take():
    text = "Everyone knows I rested"
    return head_motion.Alignment(
        tuple(text), *zip(*((i * 0.08, (i + 1) * 0.08) for i in range(len(text))), strict=True)
    )


def test_a_still_plan_draws_the_same_figure_with_nothing_moving_on_the_head():
    root = drawn(HeadPlan.still())
    for name in ("lean", "breath", "turn", "nod", "idle", "lift", "face"):
        assert animates(group(root, name)) == {}


def test_frozen_canvas_holds_spring_head_motion(tmp_path, scene_render):
    import json
    import subprocess

    scene, cv = stage()
    channel = head_motion.Channel(((0.0, 0.0), (1.0, 10.0), (2.0, 0.0)), head_motion.Spring(1.0, 0.8))
    with cv.frozen():
        toon_head.figure(cv, cv.comp, RIG, [Pose(0, 'wide', 'flat', 'desk')], 2, HeadPlan(nod=channel))
    assert scene.check(schema=True) == []
    nod = next(n.id for n in scene.iter('group') if str(n.id).startswith('nod-'))
    path = tmp_path / 'head.scene.xml'
    path.write_bytes(scene.to_bytes())
    values = []
    for time in (0, 0.5, 1):
        output = subprocess.run(
            [str(scene_render), 'eval', str(path), '--time', str(time), '--json'],
            capture_output=True,
            text=True,
            check=True,
        )
        nodes = json.loads(output.stdout)['result']['nodes']
        values.append(next(n['world'][5] for n in nodes if n['id'] == nod))
    assert values == pytest.approx([values[0]] * len(values), abs=1e-5)


def test_frozen_head_rejects_curve_across_zero_before_scene_mutation():
    from srstudio.canvas import CanvasError

    scene, cv = stage()
    channel = head_motion.Channel(((-0.5, 0), (0.5, 10)), head_motion.Spring(1, 0.8))
    before = scene.to_bytes()
    with cv.frozen(), pytest.raises(CanvasError, match='across 0'):
        toon_head.figure(cv, cv.comp, RIG, [Pose(0, 'wide', 'flat', 'desk')], 2, HeadPlan(nod=channel))
    assert scene.to_bytes() == before


def test_frozen_head_does_not_sample_unused_future_spring_history():
    scene, cv = stage()
    channel = head_motion.Channel(tuple((float(i * 100), float(i)) for i in range(10)), head_motion.Spring(0.5, 0.7))
    with cv.frozen():
        toon_head.figure(cv, cv.comp, RIG, [Pose(0, 'wide', 'flat', 'desk')], 2, HeadPlan(nod=channel))
    assert all(len(list(a.iter('key'))) == 1 for a in scene.iter('animate'))


@pytest.mark.parametrize('rigged', [False, True])
def test_frozen_toon_character_keeps_its_initial_pose(tmp_path, scene_render, rigged):
    import json
    import subprocess

    scene, cv = stage()
    poses = [Pose(0, 'wide', 'flat', 'desk'), Pose(0.5, 'sleepy', 'yawn', 'sigh')]
    with cv.frozen():
        if rigged:
            toon_head.figure(cv, cv.comp, RIG, poses, 2, HeadPlan.still())
        else:
            toon_cast.dog(cv, cv.comp, poses, 2)
    path = tmp_path / 'character.scene.xml'
    path.write_bytes(scene.to_bytes())
    frames = []
    for time in (0, 1):
        output = subprocess.run(
            [str(scene_render), 'eval', str(path), '--time', str(time), '--json'],
            capture_output=True,
            text=True,
            check=True,
        )
        nodes = json.loads(output.stdout)['result']['nodes']
        frames.append(
            {
                n['id']
                for n in nodes
                if n.get('kind') == 'shape' and n.get('draw', True) and n.get('world_opacity', 1) > 0.5
            }
        )
    assert frames[0] and frames[0] == frames[1]


@pytest.mark.parametrize('rigged', [False, True])
def test_frozen_toon_character_entering_later_stays_hidden(tmp_path, scene_render, rigged):
    import json
    import subprocess

    scene, cv = stage()
    poses = [Pose(0, 'wide', 'flat', 'desk')]
    with cv.frozen():
        if rigged:
            toon_head.figure(cv, cv.comp, RIG, poses, 2, HeadPlan.still(), enter=0.5)
        else:
            toon_cast.dog(cv, cv.comp, poses, 2, enter=0.5)
    path = tmp_path / 'later.scene.xml'
    path.write_bytes(scene.to_bytes())
    for time in (0, 1):
        output = subprocess.run(
            [str(scene_render), 'eval', str(path), '--time', str(time), '--json'],
            capture_output=True,
            text=True,
            check=True,
        )
        nodes = json.loads(output.stdout)['result']['nodes']
        visible = [
            n for n in nodes if n.get('kind') == 'shape' and n.get('draw', True) and n.get('world_opacity', 1) > 0.5
        ]
        assert not visible


def test_the_face_slides_further_than_the_skull_on_a_nod():
    speech = head_motion.Speech(1.0, head_motion.words_of(_take(), 1.0), (-20.0,) * 300)
    plan = head_motion.plan(STYLE, [speech], 8.0)
    root = drawn(plan)
    skull = [float(k.get("value")) - fy(RIG.neck[1]) for k in animates(group(root, "nod"))["y"].findall("key")]
    face = [float(k.get("value")) for k in animates(group(root, "face"))["y"].findall("key")]
    biggest = max(range(len(skull)), key=lambda i: abs(skull[i]))
    assert face[biggest] == pytest.approx(skull[biggest] * toon_head.FACE_SLIDE, abs=0.05)
    assert skull[biggest] == pytest.approx(max(v for _, v in plan.nod.keys) * fh(1.0), abs=0.05)


# -- the seam ----------------------------------------------------------------------------------------------------------
def test_the_approved_sloth_rig_draws_the_same_scene():
    speech = head_motion.Speech(1.0, head_motion.words_of(_take(), 1.0), (-20.0,) * 300)
    scene, cv = stage()
    plan = head_motion.plan(STYLE, [speech], 8.0)
    toon_head.figure(cv, cv.comp, RIG, POSES, 8.0, plan, mouths=MOUTHS, taps=TAPS, stickers=[RIG.skull()[0]])
    assert hashlib.sha256(scene.to_bytes(layout="pretty")).hexdigest() == RIGGED_SLOTH_PIN


@EVERY_RIG
def test_the_seam_stays_shut_with_the_head_at_every_bound(rig):
    assert toon_head.open_seam(rig) == []


def test_a_rig_whose_head_cannot_reach_its_cover_is_found_out():
    short = replace(RIG, head=tuple((x, y - 60.0) for x, y in RIG.head))
    assert {point for point, _, _ in toon_head.open_seam(short)}
    assert toon_head.open_seam(replace(short, free=1000.0)) == []
    over = replace(RIG, head_over=True, free=0.0, cover=((185.0, 900.0), (190.0, 900.0), (195.0, 900.0)))
    assert toon_head.open_seam(over)


def test_the_head_stays_inside_its_bounds_with_every_channel_at_the_limit():
    assert limit(STYLE, "turn") + limit(STYLE, "roll") + limit(STYLE, "idle_roll") < 12.0
    assert limit(STYLE, "nod") < 30.0


# -- the idle ----------------------------------------------------------------------------------------------------------
def test_the_sloth_never_sits_stock_still():
    plan = hm_plan(12.0)

    def crown(t: float) -> tuple[float, float]:
        across = HEAD_TOP * math.radians(sample(plan.idle_roll, t))
        return across, sample(plan.idle_y, t) - STYLE.breath_px * sample(plan.breath, t)

    for start in range(11):
        seen = [crown(start + k * 0.1) for k in range(11)]
        assert max(max(axis) - min(axis) for axis in zip(*seen, strict=True)) >= 0.5, start


# -- gaze --------------------------------------------------------------------------------------------------------------
def test_gaze_states_are_hold_keys_with_ahead_first():
    states = toon_head.gaze_states(((1.0, "left"), (2.0, "ahead"), (3.0, "up")), 0.0, 8.0)
    assert states["ahead"] == [(0.0, 1), (1.0, 0), (2.0, 1), (3.0, 0)]
    assert states["left"] == [(0.0, 0), (1.0, 1), (2.0, 0), (3.0, 0)]
    assert states["up"] == [(0.0, 0), (1.0, 0), (2.0, 0), (3.0, 1)]


def test_a_run_that_starts_mid_glance_starts_looking_that_way_and_ignores_what_comes_after():
    states = toon_head.gaze_states(((1.0, "left"), (9.0, "right")), 2.0, 8.0)
    assert states == {"ahead": [(2.0, 0)], "left": [(2.0, 1)]}


def test_an_unknown_gaze_is_refused_by_name():
    with pytest.raises(HeadMotionError, match="sideways"):
        toon_head.gaze_states(((1.0, "sideways"),), 0.0, 8.0)


def test_a_glance_draws_one_pair_of_eyes_a_gaze_and_moves_the_pupils():
    plan = HeadPlan(gaze=((1.0, "left"), (2.0, "ahead")))
    root = drawn(plan, poses=[Pose(0.0, "half", "flat", "desk")])
    run = next(iter(group(root, "face").findall("group")))
    eyes = [g for g in run.findall("group") if "opacity" in animates(g)]
    held = [g for g in eyes if len(animates(g)["opacity"].findall("key")) == 3]
    assert len(held) == 2
    assert ET.tostring(held[0]) != ET.tostring(held[1])
    ahead = [p for p in toon_head._gazing(RIG.look, "ahead").drawing.pupil(RIG.look, 100.0, 100.0, 5.0) if len(p) == 2]
    left = [p for p in toon_head._gazing(RIG.look, "left").drawing.pupil(RIG.look, 100.0, 100.0, 5.0) if len(p) == 2]
    assert ahead != left


def test_shut_eyes_have_no_pupils_to_move():
    plan = HeadPlan(gaze=((1.0, "left"), (2.0, "ahead")))
    root = drawn(plan, poses=[Pose(0.0, "closed", "flat", "desk")])
    run = next(iter(group(root, "face").findall("group")))
    assert not any(len(animates(g).get("opacity", ET.Element("a")).findall("key")) == 3 for g in run.findall("group"))


def test_a_look_with_no_drawing_of_its_own_cannot_glance():
    with pytest.raises(ToonDataError, match="pupils"):
        toon_head._gazing(toon_cast.DOG, "left")


@EVERY_RIG
def test_every_rig_moves_its_eyes_when_it_glances(rig):
    def eyes(name):
        look = toon_head._gazing(rig.look, name)
        return toon_cast._eye(look, look.eyes[0], "half", 1.0)

    assert eyes("left") != eyes("ahead") != eyes("right")


def test_a_fox_s_glance_stays_inside_its_almond_and_changes_nothing_at_rest():
    assert toon_inked.FOX_INK.glance == (0.0, 0.0)
    fox = toon_inked.FOX_RIG.look.drawing
    assert fox.looking(-0.42, 0.04)._iris("left")[0] == -toon_inked.GLANCE_ROOM
    assert fox.looking(0.42, 0.04)._iris("wide") == (0.42, pytest.approx(0.06))
    assert fox._iris("left") == toon_inked._LOOK["left"]


# -- the poses ---------------------------------------------------------------------------------------------------------
@EVERY_RIG
def test_every_pose_kind_draws_through_every_rig(rig):
    root = drawn(mouths=MOUTHS, taps=TAPS, rig=rig, stickers=[rig.skull()[0]])
    for name, count in (("skull", 5), ("face", 5), ("trunk", 5)):
        assert len(group(root, name).findall("group")) == count


@EVERY_RIG
def test_every_rig_has_the_whole_vocabulary(rig):
    for eyes in toon.EYES:
        for mouth in toon.MOUTHS:
            drawn_mouth = toon_cast._mouth(rig.look, mouth)
            assert isinstance(drawn_mouth, list)
        assert toon_cast._eye(rig.look, rig.look.eyes[0], eyes, 1.0) is not None
    for arms in toon.ARMS:
        assert toon_cast._arms(rig.look, arms, 0)


@pytest.mark.parametrize("rig", [r for r in toon_rigs.RIGS.values() if r.head_over], ids=lambda r: r.look.name)
def test_a_head_over_the_body_comes_after_the_trunk(rig):
    breath = list(group(drawn(rig=rig), "breath"))
    names = [node.get("id").split("-")[0] for node in breath if node.tag == "group"]
    assert names == ["trunk", "turn", "front"]


def test_a_ruff_over_the_head_comes_after_it():
    names = [node.get("id").split("-")[0] for node in group(drawn(), "breath") if node.tag == "group"]
    assert names == ["turn", "trunk", "front"]


def test_a_look_with_its_own_nose_keeps_it_on_the_face():
    fox = toon_inked.FOX_RIG
    assert len(fox.look.nose) == 2
    plain = len(group(drawn(rig=replace(fox, look=replace(fox.look, nose=()))), "face").findall(".//shape"))
    assert len(group(drawn(rig=fox), "face").findall(".//shape")) == plain + 2 * 5


def test_something_held_in_front_goes_over_the_face():
    root = drawn(poses=[Pose(0.0, "half", "flat", "face")])
    assert len(group(root, "front").findall("group")) == 1


def test_typing_swaps_arms_on_the_taps_and_keeps_inside_the_trunk():
    typed = drawn(poses=[Pose(0.0, "half", "flat", "type")], taps=TAPS)
    idle = drawn(poses=[Pose(0.0, "half", "flat", "type")])
    assert len(ET.tostring(group(typed, "trunk"))) > len(ET.tostring(group(idle, "trunk"))) / 2
    assert group(typed, "front").findall("group") == []


def test_lips_and_blinks_stay_on_the_face_group():
    face = group(drawn(poses=[Pose(0.0, "half", "flat", "desk")], mouths=MOUTHS), "face")
    held = [g for g in face.iter("group") if "opacity" in animates(g)]
    assert len(held) >= 4  # the visemes and the lids


def test_an_entrance_starts_the_runs_late():
    root = drawn(poses=[Pose(0.0, "half", "flat", "desk")], enter=1.5)
    assert group(root, "skull").find("group").get("start") == "1.5"
    assert group(root, "trunk").find("group").get("end") == "8"


def test_a_character_with_no_rig_is_refused_by_name():
    with pytest.raises(ToonDataError, match="toon-cat version 1 has no head rig"):
        toon_rigs.rig_of("toon-cat")


def test_a_rig_the_operator_has_not_approved_moves_no_reel(monkeypatch):
    goat = parts.get("toon-goat")
    held = replace(goat.versions[0].rig, status="proposed", approval=None)
    table = {**parts.load(), "toon-goat": replace(goat, versions=(replace(goat.versions[0], rig=held),))}
    monkeypatch.setattr(parts, "load", lambda: table)
    with pytest.raises(ToonDataError, match="toon-goat version 1's head rig is not approved"):
        toon_rigs.rig_of("toon-goat")


def test_reach_starts_at_rest_and_visits_each_corner_of_a_rig_s_bounds():
    rig = toon_rigs.RIGS["toon-goat"]
    plan = toon_head.reach(rig)
    assert plan.turn.keys[0] == (0.0, 0.0) and plan.nod.keys[0] == (0.0, 0.0)
    assert [
        (rig.tilt + turn, drop) for (_, turn), (_, drop) in zip(plan.turn.keys[1:], plan.nod.keys[1:], strict=True)
    ] == (toon_head._bounds(rig))


@EVERY_RIG
@pytest.mark.parametrize("name", head_motion.CHANNELS)
def test_every_style_stays_inside_its_bounds_through_its_springs(rig, name):
    style = rig.style
    words = head_motion.words_of(_take(), 1.0)
    plan = head_motion.plan(style, [head_motion.Speech(1.0, words, (-20.0,) * 300)], 8.0)
    channel = getattr(plan, name)
    assert max(abs(sample(channel, k / 100.0)) for k in range(800)) <= limit(style, name) + 1e-6


def test_each_character_moves_its_own_way():
    styles = {part: rig.style for part, rig in toon_rigs.RIGS.items()}
    sloth, goat, hamster = styles["toon-sloth"], styles["toon-goat"], styles["toon-hamster"]
    fox = styles["toon-fox@2"]
    assert len({s.seed for s in styles.values()}) == len(styles)
    assert goat.head.frequency > sloth.head.frequency  # abrupt against slow
    assert goat.head.damping > sloth.head.damping  # and it stops dead
    assert hamster.nod_px < min(s.nod_px for s in (sloth, goat, fox))  # small
    assert hamster.idle_hz > max(s.idle_hz for s in (sloth, goat, fox))  # and quick
    assert hamster.breath_period < min(s.breath_period for s in (sloth, goat, fox))
    assert fox.nod_roll > fox.nod_px / 3  # more a cock of the head than a nod
    assert fox.glance_face < goat.glance_face and fox.glance_hold > goat.glance_hold  # the eyes do the work


def test_a_rig_with_no_held_tilts_has_no_group_for_them():
    assert not [g for g in drawn().iter("group") if g.get("id", "").startswith("tilt-")]


def test_a_rig_s_held_tilts_ease_in_on_its_settle_and_count_toward_its_bounds():
    held = {"half": -4.0, "wide": 6.0}
    rig = replace(RIG, pose_tilt=held.__getitem__, tilt_reach=(-4.0, 6.0))
    root = drawn(poses=[Pose(0.0, "half", "flat", "desk"), Pose(3.0, "wide", "grin", "desk")], rig=rig)
    tilt = group(root, "tilt")
    assert tilt in list(group(root, "turn")) and group(root, "nod") in list(tilt)
    rotation = animates(tilt)["rotation"]
    assert rotation.get("defaultInterpolation") == "spring"
    ease = toon_head.TILT_EASE
    keys = [(float(k.get("time")), float(k.get("value"))) for k in rotation.findall("key")]
    assert keys == [(0.0, -4.0), (3.0, -4.0), (3.0 + ease, 6.0)]  # a key at a pose's start would spring on to the next
    plain, wide = toon_head._bounds(RIG), toon_head._bounds(rig)
    assert wide[0][0] == pytest.approx(plain[0][0] - 4.0) and wide[3][0] == pytest.approx(plain[3][0] + 6.0)


def test_a_held_tilt_keeps_to_its_own_pose_when_poses_come_quickly():
    held = {"half": -4.0, "wide": 6.0}
    rig = replace(RIG, pose_tilt=held.__getitem__)
    gap = toon_head.TILT_EASE / 2.0
    poses = [
        Pose(0.0, "half", "flat", "desk"),
        Pose(1.0, "wide", "flat", "desk"),
        Pose(1.0 + gap, "half", "flat", "desk"),
    ]
    rotation = animates(group(drawn(poses=poses, rig=rig), "tilt"))["rotation"]
    keys = [(float(k.get("time")), float(k.get("value"))) for k in rotation.findall("key")]
    assert keys == [
        (0.0, -4.0),
        (1.0, -4.0),
        (pytest.approx(1.0 + gap / 2.0), 6.0),
        (pytest.approx(1.0 + gap), 6.0),
        (pytest.approx(1.0 + gap + toon_head.TILT_EASE), -4.0),
    ]


def test_a_rig_sets_how_far_its_face_slides_on_a_nod():
    speech = head_motion.Speech(1.0, head_motion.words_of(_take(), 1.0), (-20.0,) * 300)
    plan = head_motion.plan(STYLE, [speech], 8.0)
    face = animates(group(drawn(plan, rig=replace(RIG, face_slide=0.4)), "face"))["y"]
    full = animates(group(drawn(plan), "face"))["y"]
    for slid, slide in zip(face.findall("key"), full.findall("key"), strict=True):
        assert float(slid.get("value")) == pytest.approx(
            float(slide.get("value")) * 0.4 / toon_head.FACE_SLIDE, abs=1e-3
        )


def test_a_ramp_paints_as_a_gradient_and_reads_as_its_flat_colour():
    ramp = toon_cast.Ramp("#123456", "test-ramp", ((0.0, "#000000"), (1.0, "#ffffff")), (10.0, 80.0, 20.0, 90.0))
    assert ramp == "#123456"
    scene, cv = stage()
    toon_cast._draw(
        cv,
        cv.comp,
        [((0.0, 0.0, 1.0, 1.0, 2.0, 2.0, 3.0, 0.0), ramp), ((0.0, 0.0, 1.0, 1.0, 2.0, 2.0, 3.0, 0.0), ramp)],
    )
    root = ET.fromstring(scene.to_bytes(layout="pretty"))
    paints = [g for g in root.iter("linearGradient")]
    assert len(paints) == 1 and paints[0].get("id") == "test-ramp" and paints[0].get("units") == "user"
    assert [s.get("fill") for s in root.iter("shape")] == ["url(#test-ramp)"] * 2


def test_a_drawing_with_its_own_gestures_answers_first_and_passes_on_the_shared_ones():
    class Own:
        def gesture(self, arms):
            return ([(("under",), "#000000")], []) if arms == "bow" else None

        def shut(self, eyes):
            return False

    look = replace(toon_cast.DOG, drawing=Own())
    assert isinstance(look.drawing, toon_cast.Posing)
    assert toon_cast._arms(look, "bow", 0) == ([(("under",), "#000000")], [])
    assert not isinstance(toon_critters.SLOTH.drawing, toon_cast.Posing)


def test_a_second_glance_at_another_rig_keeps_the_rig_s_look():
    assert replace(RIG, tilt=0.0).look is RIG.look


def test_the_modules_are_reachable_from_the_package():
    assert srstudio.head_motion is head_motion and srstudio.toon_head is toon_head


def _top_colour(layers, x: float, y: float) -> str | None:
    """The colour on top at a reference point: the last layer whose polygon holds it."""
    for shape, colour in reversed(list(layers)):
        points = list(zip(shape[0::2], shape[1::2], strict=True))
        crossings = sum(
            (y0 > y) != (y1 > y) and x < x0 + (y - y0) * (x1 - x0) / (y1 - y0)
            for (x0, y0), (x1, y1) in zip(points, points[1:] + points[:1], strict=True)
        )
        if crossings % 2:
            return colour
    return None


@pytest.mark.parametrize("x", [150.0, 185.0, 220.0])
def test_the_fox_white_runs_from_face_to_bib_as_in_its_flat_drawing(x):
    """The operator approved a fox whose cream runs unbroken from the face into the bib. The rig closes the head under
    the chin, and that line must not read as a collar across the chest."""
    fox = toon_rigs.rig_of("toon-fox")
    for y in (696.0, 700.0, 704.0):
        assert _top_colour(fox.skull(), x, y) in (toon_inked.FOX.light, toon_inked.CREAM_SHADE)


@pytest.mark.parametrize("x", [112.0, 258.0])
def test_the_fox_cheek_has_no_ink_line_under_it(x):
    fox = toon_rigs.rig_of("toon-fox")
    top = next(y for y in (y / 2 for y in range(1320, 1440)) if _top_colour(fox.skull(), x, y) is None)
    assert all(_top_colour(fox.skull(), x, y) == toon_inked.FOX.coat for y in (top - 2.0, top - 4.0, top - 6.0))


def _long_spring(keys: int):
    scene, cv = stage()
    group = cv.group(cv.comp, "head")
    spring = group.add_animate(property="y", defaultInterpolation="spring")
    for i in range(keys):
        spring.add_key(time=i, value="0", stiffness="50", damping="10", mass="1", carry="true" if i else None)
    return group, spring


def test_a_long_shot_keeps_its_runs_of_carried_springs_short():
    group, spring = _long_spring(25)
    toon_head.rest_springs(group)
    carried, longest = 0, 0
    for key in spring.iter("key"):
        carried = carried + 1 if key.carry else 0
        longest = max(longest, carried)
    assert 0 < longest < toon_head.SPRING_RUN


def test_a_short_shot_keeps_every_carried_spring():
    group, spring = _long_spring(toon_head.SPRING_RUN)
    toon_head.rest_springs(group)
    assert sum(1 for key in spring.iter("key") if key.carry) == toon_head.SPRING_RUN - 1


@pytest.mark.parametrize("run", [0, 1, -3])
def test_a_run_too_short_to_carry_anything_is_refused(run):
    group, _ = _long_spring(3)
    with pytest.raises(ToonDataError, match="run"):
        toon_head.rest_springs(group, run)


@EVERY_RIG
def test_the_chest_is_under_the_head_wherever_the_head_goes(rig):
    x, y = toon_head.chest(rig)
    assert x == rig.neck[0]
    for turn, drop in toon_head._bounds(rig):
        a = math.radians(turn)
        for px, py in rig.head:
            dx, dy = px - rig.neck[0], py - rig.neck[1]
            assert rig.neck[1] + dx * math.sin(a) + dy * math.cos(a) + drop <= y + 1e-9


def test_on_face_draws_inside_the_face_group_and_unset_changes_nothing():
    marks = []

    def mark(face) -> None:
        marks.append(face.get("id") if hasattr(face, "get") else face)

    plain = ET.tostring(drawn(hm_plan()))
    assert not marks
    assert ET.tostring(drawn(hm_plan(), on_face=None)) == plain
    drawn(hm_plan(), on_face=mark)
    assert len(marks) == 1
