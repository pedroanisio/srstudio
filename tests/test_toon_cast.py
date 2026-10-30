"""The dog, the frog, the bear and the rabbit: brush-drawn Toon characters with the cat's vocabulary and contract,
the polish of the later two (brows, highlights, blush, teeth, whiskers, blinks) and the lip sync they all take."""

import math
import xml.etree.ElementTree as ET

import pytest
from sr_core.scene import Scene

from srstudio import PEACH, Canvas, brush, flat_counter, registry, toon, toon_cast

D = 3.0
POSES = [
    {"start": 0.0, "eyes": "wide", "mouth": "open", "arms": "desk"},
    {"start": 1.0, "eyes": "half", "mouth": "flat", "arms": "type"},
    {"start": 2.0, "eyes": "closed", "mouth": "none", "arms": "face"},
]


def canvas() -> Canvas:
    scene = Scene(version="auto")
    scene.add_project(width=1080, height=1920, fps="24", duration=D, background=PEACH.background)
    return Canvas(scene, PEACH, font_asset=None, namer=flat_counter("k"))


def tree(cv: Canvas):
    return ET.fromstring(cv.scene.to_bytes(layout="pretty"))


def runs_of(cv: Canvas):
    return [g for g in tree(cv).find("composition").iter("group") if g.get("start") is not None]


@pytest.mark.parametrize("look", toon_cast.LOOKS.values(), ids=list(toon_cast.LOOKS))
@pytest.mark.parametrize("arms", toon.ARMS)
@pytest.mark.parametrize("eyes", toon.EYES)
@pytest.mark.parametrize("mouth", toon.MOUTHS)
def test_every_expression_is_drawn_inside_the_character_s_corner(look, eyes, mouth, arms):
    layers = toon_cast.figure_shapes(look, eyes, mouth, arms)
    assert layers and all(len(s) >= 8 and (len(s) - 2) % 6 == 0 for s, _ in layers)
    boxes = [brush.bounds(s) for s, _ in layers]
    # the figure sits in the room's left half under the pill and the call badge (which ends at y 352); the typing
    # far arm may run under the laptop lid (x 415-440) and a sigh or a lean may dip under the desk top (y 801-860),
    # both drawn over it by toon.desk
    assert min(b[0] for b in boxes) > -40 and max(b[2] for b in boxes) < 440
    assert min(b[1] for b in boxes) > 360 and max(b[3] for b in boxes) < 860
    colours = [c for _, c in layers]
    eye_whites = {"closed": 0, "wince": 0, "hearts": 0, "teary": 2 * 3}.get(eyes, 2 + 2 * look.shine)
    whites = eye_whites + (mouth in ("grin", "grimace")) + (1 if look.nose else 0)
    whites += 2 * (look.teeth and mouth not in ("none", "grimace", "kiss"))
    assert colours[0] == "ink" and look.coat in colours and colours.count("white") == whites
    assert (look.blush in colours) == bool(look.blush) and (look.ear_inner in colours) == bool(look.ear_inner)
    assert (toon.LIPS in colours) == (mouth in ("open", "round", "o"))
    # the paws over the mouth come last; a sigh drops the figure, a lean turns it toward the laptop
    rest = toon_cast.figure_shapes(look, eyes, mouth, "desk")
    if arms in ("face", "face2"):
        assert colours[-1] == look.coat or colours[-1] == "ink"  # a paw or its toes
    if arms == "sigh":
        assert brush.bounds(layers[0][0])[1] == pytest.approx(
            brush.bounds(rest[0][0])[1] + toon_cast.SIGH_DROP, abs=0.01
        )
    if arms == "lean":  # the turn is clockwise about the hips: the shoulders and the head swing right
        assert brush.bounds(layers[0][0])[0] > brush.bounds(rest[0][0])[0]
        assert brush.bounds(layers[0][0])[1] < brush.bounds(rest[0][0])[1] + toon_cast.LEAN_DEGREES


def test_the_two_typing_frames_differ_only_in_the_arms():
    a = toon_cast.figure_shapes(toon_cast.DOG, "half", "flat", "type", 0)
    b = toon_cast.figure_shapes(toon_cast.DOG, "half", "flat", "type", 1)
    assert len(a) == len(b) and a != b
    same = [x == y for x, y in zip(a, b, strict=True)]
    assert same[0] and same[-1] and not all(same)  # the ears and the mouth hold; the arms move
    assert max(brush.bounds(s)[3] for s, _ in a) >= 800  # the far arm lies along the desk's edge


def test_bad_expressions_and_frames_are_refused():
    with pytest.raises(toon.ToonDataError, match="no expression"):
        toon_cast.figure_shapes(toon_cast.FROG, "laser", "flat", "desk")
    with pytest.raises(toon.ToonDataError, match="no expression"):
        toon_cast.figure_shapes(toon_cast.FROG, "half", "flat", "wings")
    with pytest.raises(toon.ToonDataError, match="typing frame is 0 or 1"):
        toon_cast.figure_shapes(toon_cast.FROG, "half", "flat", "type", 2)


def test_the_looks_differ_where_they_should():
    assert toon_cast.DOG.ears and not toon_cast.FROG.ears and toon_cast.DOG.nose and not toon_cast.FROG.nose
    assert toon_cast.FROG.eyes[0][1] < toon_cast.DOG.eyes[0][1]  # the frog's eyes sit on its bumps
    assert toon_cast.FROG.mouth_w > toon_cast.DOG.mouth_w
    assert toon_cast.DOG.coat != toon_cast.FROG.coat != PEACH.shade


@pytest.mark.parametrize("draw", [toon_cast.dog, toon_cast.frog])
def test_a_character_holds_one_group_per_pose_and_swaps_typing_frames_on_the_keystrokes(draw):
    cv = canvas()
    poses = toon.parse_poses(POSES)
    groups = draw(cv, cv.comp, poses, D, taps=(1.2, 1.3, 1.7))
    runs = runs_of(cv)
    assert len(groups) == 3 and [(g.get("start"), g.get("end")) for g in runs] == [("0", "1"), ("1", "2"), ("2", "3")]
    assert all(s.get("stroke") == PEACH.clear for g in runs for s in g.iter("shape"))  # filled brush, no strokes
    assert [len(g.findall("group")) for g in runs] == [0, 2, 0]
    rest, struck = runs[1].findall("group")
    for g, first in ((rest, 1), (struck, 0)):
        a = g.find("animate")
        assert (a.get("property"), a.get("timeBase")) == ("opacity", None)
        keys = [(float(k.get("time")), float(k.get("value"))) for k in a.iter("key")]
        assert keys[0] == (1.0, first) and keys[1][0] == 1.2
    # without keystrokes the typing pose is one frame
    cv2 = canvas()
    draw(cv2, cv2.comp, poses, D)
    assert [len(g.findall("group")) for g in runs_of(cv2)] == [0, 1, 0]
    with pytest.raises(toon.ToonDataError, match="taps"):
        draw(canvas(), cv.comp, poses, D, taps=(-1,))


def test_a_character_can_enter_later_and_its_poses_count_from_then():
    cv = canvas()
    poses = toon.parse_poses(POSES[:2])
    toon_cast.frog(cv, cv.comp, poses, D, taps=(1.2, 1.5), enter=1.0)
    runs = runs_of(cv)
    assert [(g.get("start"), g.get("end")) for g in runs] == [("1", "2"), ("2", "3")]
    assert len(runs[1].findall("group")) == 1  # the typing pose now runs 2-3 s; the taps fall before it: one frame
    with pytest.raises(toon.ToonDataError, match="not before the end"):
        toon_cast.frog(canvas(), cv.comp, toon.parse_poses(POSES), D, enter=1.0)  # the pose at 2 s has no room
    with pytest.raises(toon.ToonDataError, match="enter must be"):
        toon_cast.frog(canvas(), cv.comp, poses, D, enter=3.0)
    with pytest.raises(toon.ToonDataError, match="enter must be"):
        toon_cast.frog(canvas(), cv.comp, poses, D, enter=-0.5)
    with pytest.raises(toon.ToonDataError, match="enter must be"):  # a bool is not a second
        toon_cast.frog(canvas(), cv.comp, poses, D, enter=True)


def test_the_characters_are_registered_with_the_toon_style():
    names = {e["name"]: e for e in registry.catalog(style="toon")}
    assert {"toon-dog", "toon-frog", "toon-bear", "toon-rabbit"} <= set(names)
    assert names["toon-dog"]["kind"] == "character" and names["toon-dog"]["style"] == "toon"
    assert all(names[n]["kind"] == "character" for n in ("toon-frog", "toon-bear", "toon-rabbit"))


def test_a_sticky_note_sticks_to_the_figure_and_moves_with_it():
    note = toon_cast.sticky_note(185, 500, size=40, tilt=-8)
    assert len(note) == 5 and [c for _, c in note] == ["ink", toon_cast.NOTE_PAPER, "ink", "ink", "ink"]
    x0, y0, x1, y1 = brush.bounds(note[1][0])
    assert 155 < x0 < 170 and 200 < x1 < 215 and 470 < y0 < 485 and 515 < y1 < 530  # a turned, rounded 40 px square
    plain = toon_cast.figure_shapes(toon_cast.DOG, "half", "flat", "sigh")
    stuck = toon_cast.figure_shapes(toon_cast.DOG, "half", "flat", "sigh", stickers=note)
    assert len(stuck) == len(plain) + 5 and stuck[: len(plain)] == plain
    assert brush.bounds(stuck[-1][0])[1] == pytest.approx(brush.bounds(note[-1][0])[1] + toon_cast.SIGH_DROP, abs=0.01)
    typing = toon_cast.figure_shapes(toon_cast.DOG, "half", "flat", "type", 1, stickers=note)
    assert typing[-5:] == note
    with pytest.raises(toon.ToonDataError, match="size over 8"):
        toon_cast.sticky_note(0, 0, size=4)


# -- the polished looks -----------------------------------------------------------------------------------------------
def test_the_bear_and_the_rabbit_carry_their_polish_and_the_older_two_do_not():
    for look in (toon_cast.BEAR, toon_cast.RABBIT):
        assert look.brows and look.shine and look.blush and look.ear_inner and look.blink > 0
    assert toon_cast.RABBIT.teeth and toon_cast.RABBIT.whiskers and not toon_cast.BEAR.teeth
    for look in (toon_cast.DOG, toon_cast.FROG):
        assert not (look.brows or look.shine or look.blush or look.teeth or look.whiskers or look.blink)
    # the rabbit's ears stand up (above the head) and the bear's sit round on top of it
    assert min(y for _, y in toon_cast.RABBIT.ears[0]) < 400 < min(y for _, y in toon_cast.BEAR.ears[0])

    # a brow follows the eyes: it rises for a shock and tilts down toward the nose in a frown
    def brow_box(kind):
        return brush.bounds(toon_cast.figure_shapes(toon_cast.BEAR, kind, "flat", "desk")[toon_cast.BEAR_BROW][0])

    assert brow_box("shock")[1] < brow_box("half")[1]
    frown = toon_cast.figure_shapes(toon_cast.BEAR, "narrow", "flat", "desk")[toon_cast.BEAR_BROW][0]
    calm = toon_cast.figure_shapes(toon_cast.BEAR, "half", "flat", "desk")[toon_cast.BEAR_BROW][0]
    assert brush.bounds(frown)[3] - brush.bounds(frown)[1] > brush.bounds(calm)[3] - brush.bounds(calm)[1] + 8


def test_viseme_keys_follow_the_track_inside_a_run_and_a_closed_run_needs_no_keys():
    track = [(0.5, "open"), (0.8, "teeth"), (1.1, "closed"), (2.5, "round"), (2.9, "closed")]
    assert toon_cast.viseme_keys(track, 0.0, 0.4) == {}  # nothing said yet
    assert toon_cast.viseme_keys(track, 1.2, 2.4) == {}  # between the lines the mouth holds the pose
    keys = toon_cast.viseme_keys(track, 0.0, 2.0)
    assert keys == {
        "closed": [(0.0, 1), (0.5, 0), (0.8, 0), (1.1, 1)],
        "open": [(0.0, 0), (0.5, 1), (0.8, 0), (1.1, 0)],
        "teeth": [(0.0, 0), (0.5, 0), (0.8, 1), (1.1, 0)],
    }
    # a run starting mid-sound opens on that sound; one starting on a change takes it
    assert toon_cast.viseme_keys(track, 0.6, 1.0)["open"][0] == (0.6, 1)
    assert toon_cast.viseme_keys(track, 2.5, 3.5)["round"] == [(2.5, 1), (2.9, 0)]
    with pytest.raises(toon.ToonDataError, match="viseme among"):
        toon_cast.viseme_keys([(0.5, "smile")], 0.0, 1.0)
    with pytest.raises(toon.ToonDataError, match="time order"):
        toon_cast.viseme_keys([(0.8, "open"), (0.5, "closed")], 0.0, 1.0)
    with pytest.raises(toon.ToonDataError, match="time order"):  # two states at one second: two keys at one time
        toon_cast.viseme_keys([(0.5, "open"), (0.5, "round")], 0.0, 1.0)
    with pytest.raises(toon.ToonDataError, match="non-negative"):
        toon_cast.viseme_keys([(-1.0, "open")], 0.0, 1.0)


def test_a_character_speaks_through_viseme_layers_while_its_pose_holds():
    cv = canvas()
    poses = toon.parse_poses(POSES)
    track = [(0.3, "open"), (0.6, "round"), (0.9, "closed"), (1.4, "teeth"), (1.7, "closed")]
    toon_cast.bear(cv, cv.comp, poses, D, taps=(1.2, 1.3), mouths=track)
    runs = runs_of(cv)
    # the first run: the lips group holds one layer per viseme heard (closed, open, round), each keyed
    lips = runs[0].findall("group")[0]
    layers = lips.findall("group")
    assert len(layers) == 3
    keyed = []
    for layer in layers:
        a = layer.find("animate")
        assert a.get("property") == "opacity" and a.get("timeBase") is None
        keyed.append([(float(k.get("time")), float(k.get("value"))) for k in a.iter("key")])
    assert keyed[0] == [(0.0, 1), (0.3, 0), (0.6, 0), (0.9, 1)]  # the pose's open mouth (closed viseme)
    assert keyed[1] == [(0.0, 0), (0.3, 1), (0.6, 0), (0.9, 0)]
    # the typing run keeps its two frames and adds the lips (teeth from 1.4 s); one second is too short to blink in
    second = runs[1].findall("group")
    assert len(second) == 3
    teeth = second[2].findall("group")
    assert len(teeth) == 2  # closed and teeth
    # the last run (eyes closed, mouth none, paws on the face): nothing is said, no lips group, no blink
    assert runs[2].findall("group") == []
    # without a track the drawing is the plain one: no lips groups
    cv2 = canvas()
    toon_cast.dog(cv2, cv2.comp, poses, D, taps=(1.2, 1.3))
    assert [len(g.findall("group")) for g in runs_of(cv2)] == [0, 2, 0]
    with pytest.raises(toon.ToonDataError, match="viseme among"):
        toon_cast.bear(canvas(), cv.comp, poses, D, mouths=[(0.1, "smile")])


def test_blink_times_fall_inside_the_run_and_the_lids_are_keyed():
    assert toon_cast.blink_times(0.0, 10.0, 0.0) == []
    times = toon_cast.blink_times(2.0, 10.0, 3.0)
    assert times == [pytest.approx(2.0 + 0.55 * 3.0 + k * 3.0) for k in range(3)]
    assert all(2.0 < t and t + toon_cast.BLINK_HOLD < 10.0 for t in times)
    assert toon_cast.blink_times(0.0, 1.0, 3.0) == []  # a short run has no room
    with pytest.raises(toon.ToonDataError, match="blink period"):
        toon_cast.blink_times(0.0, 1.0, -1.0)
    cv = canvas()
    scene = cv.scene
    scene.find("project").duration = 8.0
    poses = toon.parse_poses([{"start": 0.0, "eyes": "wide", "mouth": "flat", "arms": "desk"}])
    toon_cast.rabbit(cv, cv.comp, poses, 8.0)
    (run,) = runs_of(cv)
    (shut,) = run.findall("group")
    a = shut.find("animate")
    keys = [(float(k.get("time")), float(k.get("value"))) for k in a.iter("key")]
    period = toon_cast.RABBIT.blink
    assert keys[0] == (0.0, 0) and keys[1] == (pytest.approx(0.55 * period), 1)
    assert keys[2] == (pytest.approx(0.55 * period + toon_cast.BLINK_HOLD), 0)
    assert len(keys) == 1 + 2 * len(toon_cast.blink_times(0.0, 8.0, period))
    # closed eyes never blink
    cv3 = canvas()
    toon_cast.rabbit(
        cv3, cv3.comp, toon.parse_poses([{"start": 0.0, "eyes": "closed", "mouth": "flat", "arms": "desk"}]), 3.0
    )
    assert runs_of(cv3)[0].findall("group") == []


# -- the headset ------------------------------------------------------------------------------------------------------
@pytest.mark.parametrize("look", [toon_cast.DOG, toon_cast.FROG, toon_cast.BEAR, toon_cast.RABBIT])
def test_a_headset_sits_over_the_head_with_its_mic_at_the_mouth(look):
    layers = toon_cast.headset(look)
    top = min(y for _, y in look.silhouette)
    left = min(x for x, y in look.silhouette if y < look.mouth[1])
    right = max(x for x, y in look.silhouette if y < look.mouth[1])
    band = brush.bounds(layers[0][0])
    assert top - 16 < band[1] < top and left - 20 < band[0] and band[2] < right + 20  # just over the crown
    mic = brush.bounds(layers[-1][0])
    cx, cy = (mic[0] + mic[2]) / 2, (mic[1] + mic[3]) / 2
    assert math.dist((cx, cy), look.mouth) < look.mouth_w  # the mic hangs by the mouth
    assert len(toon_cast.headset(look, mic=False)) < len(layers)
    assert all(c in ("ink", toon_cast.HEADSET, toon_cast.HEADSET_LIGHT) for _, c in layers)


def test_a_headset_is_a_sticker_and_a_registered_toon_prop():
    stuck = toon_cast.figure_shapes(toon_cast.DOG, "half", "flat", "desk", stickers=toon_cast.headset(toon_cast.DOG))
    assert len(stuck) == len(toon_cast.figure_shapes(toon_cast.DOG, "half", "flat", "desk")) + len(
        toon_cast.headset(toon_cast.DOG)
    )
    entry = {e.name: e for e in registry.entries()}["toon-headset"]
    assert entry.kind == "prop" and entry.style == "toon"
