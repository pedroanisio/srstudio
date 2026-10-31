"""Toon rooms (ADR 0043): a living room at night and a service counter, each lit by lights a sketch keys over time
(on, off, flicker, dim, a screen's colour), the light reaching the character's side of the frame while the
signature on the desk stays as it is."""

import json
import math
import os
import shutil
import subprocess
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

import pytest
from sr_core.scene import Scene

from srstudio import (
    PEACH,
    TOON,
    Canvas,
    flat_counter,
    registry,
    toon,
    toon_everyday,
    toon_rooms,
    toon_sets,
    toon_sketch,
)
from srstudio.canvas import Signature
from srstudio.sample import SYSTEM_FONTS
from srstudio.toon import ToonDataError
from srstudio.toon_rooms import DIM, FADE, FLICKER, FLICKER_PERIOD, ROOMS, SHADE_MAX, Cue
from support.png import read_png

D = 8.0
EPISODES = Path(__file__).resolve().parent.parent / "episodes"
FIGURE = (-33, 462, 359, 808)  # the Toon figure's extent, reference pixels (x0, y0, x1, y1)
DESK = (415, 523, 660, 1122)  # the laptop and the desk below it, to the frame's foot
CAPTION = (toon.CAPTION_TOP - 8, toon.CAPTION_TOP + toon.CAPTION_H + 8)  # the pill's band and a margin


def canvas(signed: bool = True) -> Canvas:
    scene = Scene(version="auto")
    scene.add_project(width=1080, height=1920, fps="24", duration=D, background=PEACH.background)
    return Canvas(
        scene, PEACH, font_asset="comic-neue", namer=flat_counter("k"), signature=Signature() if signed else None
    )


def test_frozen_room_level_does_not_change(tmp_path, scene_render):
    cv = canvas()
    with cv.frozen():
        group = toon_rooms._level(cv, cv.comp, [(0, 0.0, 'hold'), (0.5, 1.0, 'hold')])
    path = tmp_path / 'level.scene.xml'
    path.write_bytes(cv.scene.to_bytes())
    values = []
    for time in (0, 1):
        output = subprocess.run(
            [str(scene_render), 'eval', str(path), '--time', str(time), '--json'],
            capture_output=True,
            text=True,
            check=True,
        )
        nodes = json.loads(output.stdout)['result']['nodes']
        values.append(next(n['opacity'] for n in nodes if n['id'] == group.id))
    assert values == pytest.approx([0, 0])


def tree(node) -> ET.Element:
    return ET.fromstring(node.scene.to_bytes(layout="pretty")) if isinstance(node, Canvas) else node


def animations(root, prop: str = "opacity"):
    return [a for a in tree(root).iter("animate") if a.get("property") == prop]


def keys_of(a):
    return [(float(k.get("time")), float(k.get("value"))) for k in a.iter("key")]


def staged(room: str, lights=None, end: float = D, **options):
    """A canvas with ``room`` staged into a back and a light group (in that order, the only children of the
    composition), and the parsed cues."""
    cv = canvas()
    back, light = cv.group(cv.comp, "back"), cv.group(cv.comp, "light")
    cues = toon_rooms.stage(cv, back, light, room, lights, end, **options)
    root = tree(cv)
    comp = root.find("composition")
    return cv, cues, comp.find("group[@id='back']"), comp.find("group[@id='light']")


def blended(node, blend: str):
    return [g for g in node.iter("group") if g.get("blend") == blend]


# -- registration and selection by name -----------------------------------------------------------------------------
def test_the_rooms_are_toon_locations():
    assert "toon_rooms" in TOON.parts
    entries = {e.name: e for e in registry.entries()}
    for name in ("toon-lounge", "toon-counter"):
        assert entries[name].kind == "location"
        assert entries[name].style == "toon"
    assert entries["toon-lounge"].builder is toon_rooms.lounge
    assert entries["toon-counter"].builder is toon_rooms.counter


def test_each_room_names_its_main_light_and_its_screen():
    assert set(ROOMS) == {"lounge", "counter"}
    assert (ROOMS["lounge"].main, ROOMS["lounge"].screen) == ("lamp", "tv")
    assert (ROOMS["counter"].main, ROOMS["counter"].screen) == ("tubes", "board")
    for room in ROOMS.values():
        assert set(room.defaults) == {room.main, room.screen}


def test_a_room_is_selected_by_name_from_data():
    spec = json.loads(
        '{"room": "counter", "lights": {"tubes": [[0, "on"], [2, "flicker"]], "board": [[0, "on", "green"]]},'
        ' "serving": [[0, "A17"], [3, "B02"]]}'
    )
    cv, cues, back, light = staged(spec["room"], spec["lights"], **{"serving": spec["serving"]})
    assert cues["tubes"] == [Cue(0.0, "on"), Cue(2.0, "flicker")]
    assert {"A17", "B02"} <= {t.get("text") for t in tree(cv).iter("text")}
    assert len(back) and len(light)


@pytest.mark.parametrize("room", ["attic", "", None, "Lounge"])
def test_an_unknown_room_is_refused(room):
    cv = canvas()
    with pytest.raises(ToonDataError, match="room"):
        toon_rooms.stage(cv, cv.comp, cv.comp, room)


def test_an_option_the_room_does_not_take_is_refused():
    cv = canvas()
    with pytest.raises(ToonDataError, match="serving"):
        toon_rooms.stage(cv, cv.comp, cv.comp, "lounge", serving=[[0, "A17"]])


# -- the cues -------------------------------------------------------------------------------------------------------
def test_a_light_left_out_takes_the_rooms_default():
    assert toon_rooms.parse_lights("lounge", None, D) == {"lamp": [Cue(0.0, "on")], "tv": [Cue(0.0, "on", "blue")]}
    parsed = toon_rooms.parse_lights("lounge", {"lamp": [[0, "off"]]}, D)
    assert parsed == {"lamp": [Cue(0.0, "off")], "tv": [Cue(0.0, "on", "blue")]}


def test_a_screen_keeps_its_colour_until_a_cue_changes_it():
    parsed = toon_rooms.parse_lights("lounge", {"tv": [(0, "on", "blue"), (3, "off"), (4, "on", "red")]}, D)
    assert parsed["tv"] == [Cue(0.0, "on", "blue"), Cue(3.0, "off", None), Cue(4.0, "on", "red")]


@pytest.mark.parametrize(
    ("room", "lights", "end", "match"),
    [
        ("lounge", {"fridge": [[0, "on"]]}, D, "no light"),
        ("lounge", {"lamp": []}, D, "at least one cue"),
        ("lounge", {"lamp": [[1, "on"]]}, D, "from 0"),
        ("lounge", {"lamp": [[0, "on"], [2, "off"], [2, "on"]]}, D, "in order"),
        ("lounge", {"lamp": [[0, "on"], [True, "off"]]}, D, "number"),
        ("lounge", {"lamp": [[0, "on"], [math.nan, "off"]]}, D, "number"),
        ("lounge", {"lamp": [[0, "strobe"]]}, D, "state"),
        ("lounge", {"lamp": [[0, "on", "blue"]]}, D, "colour"),
        ("lounge", {"tv": [[0, "on", "mauve"]]}, D, "colour"),
        ("lounge", {"tv": [[0, "on"]]}, D, "colour"),
        ("lounge", {"lamp": [[0]]}, D, "cue"),
        ("lounge", {"lamp": [[0, "on", None, 4]]}, D, "cue"),
        ("lounge", {"lamp": "on"}, D, "cue"),
        ("lounge", {"lamp": [[0, "on"], [D, "off"]]}, D, "end"),
        ("lounge", {"lamp": [[0, "on"], [1, "off"]]}, 0.0, "end"),
        ("lounge", {"lamp": [[0, "on"], [2, "dim"], [2.5, "on"]]}, D, "dim"),
        ("lounge", None, -1.0, "end"),
        ("lounge", None, True, "end"),
        ("lounge", [["lamp", [[0, "on"]]]], D, "map"),
        ("counter", {"tubes": [[0, "on", "white"]]}, D, "colour"),
    ],
)
def test_bad_cues_are_refused(room, lights, end, match):
    with pytest.raises(ToonDataError, match=match):
        toon_rooms.parse_lights(room, lights, end)


def test_a_dim_may_run_into_the_end():
    assert toon_rooms.parse_lights("lounge", {"lamp": [[0, "on"], [D - 0.5, "dim"]]}, D)["lamp"][-1].state == "dim"


# -- the level a light is at, over time -----------------------------------------------------------------------------
def levels(*cues: Cue, end: float = D):
    return toon_rooms.level_keys(list(cues), end)


def test_on_and_off_hold_their_level():
    assert levels(Cue(0, "on")) == [(0.0, 1.0, "hold")]
    assert levels(Cue(0, "off")) == [(0.0, 0.0, "hold")]
    keys = levels(Cue(0, "on"), Cue(3, "off"), Cue(5, "on"))
    assert keys == [(0.0, 1.0, "hold"), (3.0, 0.0, "hold"), (5.0, 1.0, "hold")]


def test_a_dim_fades_from_the_level_before_it():
    assert levels(Cue(0, "on"), Cue(2, "dim")) == [(0.0, 1.0, "hold"), (2.0, 1.0, "linear"), (2.0 + FADE, DIM, "hold")]
    assert levels(Cue(0, "off"), Cue(2, "dim"))[1:] == [(2.0, 0.0, "linear"), (2.0 + FADE, DIM, "hold")]
    assert levels(Cue(0, "dim")) == [(0.0, DIM, "hold")]


def test_a_dim_cut_by_the_end_stops_part_way():
    *_, last = levels(Cue(0, "on"), Cue(D - FADE / 2, "dim"))
    assert last == (D, pytest.approx(1.0 + (DIM - 1.0) / 2), "hold")


def test_a_flicker_runs_its_cycle_until_the_next_cue():
    keys = levels(Cue(0, "on"), Cue(2, "flicker"), Cue(5, "on"))
    cycle = [(t, v, "hold") for t, v in toon_sets.cycle_keys(FLICKER, FLICKER_PERIOD, 2.0, 5.0)][:-1]
    assert keys == [(0.0, 1.0, "hold"), *cycle, (5.0, 1.0, "hold")]
    assert len({v for _, v, _ in cycle}) >= 3
    to_end = levels(Cue(0, "flicker"))
    assert to_end[-1][0] == D and to_end[0] == (0.0, FLICKER[0][1], "hold")


def test_a_dim_after_a_flicker_starts_from_where_the_flicker_was():
    before = toon_sets.cycle_keys(FLICKER, FLICKER_PERIOD, 0.0, 2.0)[-1][1]
    keys = levels(Cue(0, "flicker"), Cue(2, "dim"))
    assert keys[-2] == (2.0, before, "linear") and keys[-1] == (2.0 + FADE, DIM, "hold")


@pytest.mark.parametrize(("state", "level"), [("on", 1.0), ("off", 0.0), ("dim", DIM), ("flicker", FLICKER[0][1])])
def test_a_still_rests_at_the_states_level(state, level):
    assert levels(Cue(0, state), end=0.0) == [(0.0, level, "hold")]


def test_every_level_is_in_range_and_in_time_order():
    cues = [Cue(0, "flicker"), Cue(1.2, "dim"), Cue(3, "off"), Cue(3.5, "flicker"), Cue(7.1, "dim")]
    keys = levels(*cues)
    times = [t for t, _, _ in keys]
    assert times == sorted(set(times)) and times[-1] == D
    assert all(0.0 <= v <= 1.0 for _, v, _ in keys)


def test_a_screens_colours_take_turns():
    cues = [Cue(0, "on", "blue"), Cue(3, "off"), Cue(4, "on", "red"), Cue(6, "on", "blue")]
    assert toon_rooms.colour_spans(cues, D) == {"blue": [(0.0, 4.0), (6.0, D)], "red": [(4.0, 6.0)]}


# -- the drawing ----------------------------------------------------------------------------------------------------
@pytest.mark.parametrize("room", sorted(ROOMS))
def test_a_still_room_holds_still_and_has_no_signature(room):
    cv, _, back, light = staged(room, end=0.0)
    # nothing moves: an animation in a still (the lounge speaker's ring) holds one key
    assert all(len(keys_of(a)) == 1 for a in animations(tree(cv)))
    assert not any((g.get("id") or "").startswith("sig-") for g in tree(cv).iter("group"))
    assert len(back) and len(light)
    shade, *_ = blended(light, "multiply")
    assert float(shade.get("opacity")) == 0.0  # the main light is on


@pytest.mark.parametrize("room", sorted(ROOMS))
def test_the_shade_deepens_as_the_main_light_goes_down(room):
    main = ROOMS[room].main
    cv, _, back, light = staged(room, {main: [[0, "on"], [2, "off"], [4, "dim"]]})
    (shade,) = blended(light, "multiply")
    (a,) = [a for a in shade.findall("animate") if a.get("property") == "opacity"]
    assert keys_of(a) == [
        (0.0, 0.0),
        (2.0, pytest.approx(SHADE_MAX)),
        (4.0, pytest.approx(SHADE_MAX)),
        (4.0 + FADE, pytest.approx(SHADE_MAX * (1 - DIM))),
    ]
    assert [k.get("interpolation") for k in a.iter("key")] == [None, None, "linear", None]


@pytest.mark.parametrize("room", sorted(ROOMS))
def test_each_light_glows_onto_the_characters_side_at_its_level(room):
    r = ROOMS[room]
    cv, _, back, light = staged(room, {r.main: [[0, "on"], [2, "off"]], r.screen: [[0, "on", "blue"], [5, "off"]]})
    glows = blended(light, "screen")
    assert len(glows) == 2
    falling = sorted(tuple(keys_of(a)[-1]) for g in glows for a in g.findall("animate"))
    assert [t for t, _ in falling] == [2.0, 5.0] and all(v == 0.0 for _, v in falling)
    # the source itself follows its level too, in the set behind the character
    sources = [keys_of(a) for a in animations(back)]
    assert any(k[0][1] > 0 and k[-1] == (2.0, 0.0) for k in sources)
    assert any(k[0][1] > 0 and k[-1] == (5.0, 0.0) for k in sources)


@pytest.mark.parametrize("room", sorted(ROOMS))
def test_a_screens_colour_is_gated_on_the_screen_and_in_its_glow(room):
    screen = ROOMS[room].screen
    cv, _, back, light = staged(room, {screen: [[0, "on", "blue"], [3, "on", "red"]]})
    blue, red = [(0.0, 1.0), (3.0, 0.0)], [(0.0, 0.0), (3.0, 1.0)]
    for part in (back, light):
        gates = [keys_of(a) for a in animations(part)]
        assert blue in gates and red in gates


def test_the_lounge_router_blinks_until_the_end():
    cv, _, back, light = staged("lounge")
    blinks = [k for k in map(keys_of, animations(back)) if k[0][0] == 0.0 and k[-1][0] == D]
    assert blinks and all(len({v for _, v in k}) == 2 for k in blinks)


def ring(cv: Canvas, colour: str = "lit", k: int = 0):
    """The opacity keys of every speaker ring segment ``k`` of ``colour`` on the canvas."""
    return [
        keys_of(a)
        for g in tree(cv).iter("group")
        if (g.get("id") or "").endswith(f"-ring-{colour}-{k}")
        for a in g.findall("animate")
    ]


def test_the_lounge_router_can_hold_still_through_a_held_opening():
    cv, _, back, light = staged("lounge", blink_from=1.0)
    blinks = [
        k for k in map(keys_of, animations(back)) if k[-1][0] == D and len({v for _, v in k}) == 2 and k[0][0] == 1.0
    ]
    assert len(blinks) == 4 and all(k[0][0] == 1.0 for k in blinks)


@pytest.mark.parametrize("blink_from", [-1.0, D, D + 1, float("nan")])
def test_the_lounge_refuses_a_blink_start_outside_its_clock(blink_from):
    with pytest.raises(ToonDataError, match="blink"):
        staged("lounge", blink_from=blink_from)


def test_the_lounge_shelf_holds_the_libraries_smart_speaker():
    cv, _, back, light = staged("lounge")
    assert ring(cv) == [[(0.0, 0.0)]]  # one speaker, off by default
    x, y = toon_rooms.LOUNGE_SPEAKER
    s = toon_rooms.LOUNGE_SPEAKER_SCALE
    b = toon_everyday.SPEAKER_BOX
    foot = (x + s * b[0], y + s * b[1], x + s * b[2], y + s * b[3])
    shelf = ROOMS["lounge"].objects["shelf"]
    assert shelf[0] <= foot[0] and shelf[1] <= foot[1] and foot[2] <= shelf[2] and foot[3] <= shelf[3]


def test_the_lounge_speaker_follows_its_states():
    cv, _, back, light = staged("lounge", speaker=[[0, "off"], [2, "listen"], [4, "error"]])
    assert ring(cv) == [[(0.0, 0.0), (2.0, 1.0), (4.0, 0.0)]]
    assert ring(cv, "alarm") == [[(0.0, 0.0), (4.0, 1.0)]]


def test_two_shots_of_the_lounge_draw_two_speakers_without_a_clash():
    cv = canvas()
    for _ in range(2):
        toon_rooms.stage(cv, cv.group(cv.comp, cv.uid("g")), cv.group(cv.comp, cv.uid("g")), "lounge", None, D)
    ids = [n.get("id") for n in tree(cv).iter() if n.get("id")]
    assert len(ring(cv)) == 2 and len(ids) == len(set(ids))


@pytest.mark.parametrize(
    ("speaker", "end", "match"),
    [
        ([[0, "sing"]], D, "state"),
        ([], D, "at least one"),
        ([[0, "off"], [1, "listen"]], 0.0, "still"),
        ([[1, "listen"]], 0.0, "still"),
    ],
)
def test_bad_speaker_states_are_refused(speaker, end, match):
    cv = canvas()
    with pytest.raises(ToonDataError, match=match):
        toon_rooms.stage(cv, cv.comp, cv.comp, "lounge", None, end, speaker=speaker)


def test_a_still_speaker_shows_its_one_state_without_moving():
    cv, _, back, light = staged("lounge", end=0.0, speaker=[[0, "think"]])
    lit = [ring(cv, "lit", k)[0] for k in range(toon_everyday.RING)]
    assert lit[0] == [(0.0, 1.0)] and all(k == [(0.0, 0.0)] for k in lit[1:])


def test_the_counter_shows_each_ticket_in_turn():
    cv, _, back, light = staged("counter", serving=[(0, "A17"), (4.5, "B02")])
    texts = [t.get("text") for t in tree(cv).iter("text")]
    assert "A17" in texts and "B02" in texts and "NOW SERVING" in texts
    gates = [keys_of(a) for a in animations(back)]
    assert [(0.0, 1.0), (4.5, 0.0)] in gates and [(0.0, 0.0), (4.5, 1.0)] in gates


@pytest.mark.parametrize(
    ("serving", "match"),
    [
        ([], "at least one"),
        ([(1, "A17")], "from 0"),
        ([(0, "A17"), (0, "B02")], "in order"),
        ([(0, "a17")], "ticket"),
        ([(0, "A1234")], "ticket"),
        ([(0, 17)], "ticket"),
        ([(0, "A17"), (D, "B02")], "end"),
        ([("0", "A17")], "number"),
        ([(0,)], "pairs"),
    ],
)
def test_bad_tickets_are_refused(serving, match):
    cv = canvas()
    with pytest.raises(ToonDataError, match=match):
        toon_rooms.stage(cv, cv.comp, cv.comp, "counter", None, D, serving=serving)


@pytest.mark.parametrize("room", sorted(ROOMS))
def test_a_rooms_objects_leave_the_figure_the_pill_and_the_desk_clear(room):
    def overlaps(a, b):
        return a[0] < b[2] and b[0] < a[2] and a[1] < b[3] and b[1] < a[3]

    objects = ROOMS[room].objects
    assert objects
    for name, box in objects.items():
        assert box[0] < box[2] and box[1] < box[3], name
        assert not overlaps(box, FIGURE), name
        assert not overlaps(box, DESK), name
        assert box[3] <= CAPTION[0] or box[1] >= CAPTION[1], name


# -- the shot ---------------------------------------------------------------------------------------------------------
def test_a_staging_is_unlit_unless_it_asks():
    assert toon_sketch.Staging.__dataclass_fields__["lit"].default is False
    assert toon_sketch.Shot.__dataclass_fields__["light"].default is None


def test_dressing_an_unlit_shot_is_refused():
    cv = canvas()
    shot = toon_sketch.Shot(cv, None, cv.group(cv.comp, "b"), cv.group(cv.comp, "f"), (), D, len)
    with pytest.raises(ToonDataError, match="lit"):
        toon_rooms.dress(shot, "lounge")


def test_dressing_a_lit_shot_draws_the_room_behind_and_the_light_in_its_layer():
    cv = canvas()
    back, light, front = (cv.group(cv.comp, n) for n in ("b", "l", "f"))
    shot = toon_sketch.Shot(cv, None, back, front, (), D, len, light=light)
    cues = toon_rooms.dress(shot, "lounge", {"lamp": [[0, "on"], [3, "off"]]})
    assert cues["lamp"] == [Cue(0.0, "on"), Cue(3.0, "off")]
    comp = tree(cv).find("composition")
    assert len(comp.find("group[@id='b']")) and blended(comp.find("group[@id='l']"), "multiply")
    assert len(comp.find("group[@id='f']")) == 0


def test_a_lit_sketch_draws_its_light_between_the_character_and_the_desk(tmp_path):
    """On a copy of the generated The Report project (``SRSTUDIO_EPISODES``): in every shot the light layer comes
    after the set and the character and right before the desk that carries the signature, so no light state can
    tint the signature."""
    env = os.environ.get("SRSTUDIO_EPISODES")
    if not env or not (Path(env) / "the-report" / "narration.json").is_file():
        pytest.skip("set SRSTUDIO_EPISODES to the folder of generated episode projects")
    sys.path.insert(0, str(EPISODES))
    try:
        import the_report_data as data
    finally:
        sys.path.pop(0)
    root = tmp_path / "the-report"
    shutil.copytree(Path(env) / "the-report", root, ignore=shutil.ignore_patterns("*.scene.xml", "*.srt"))
    lights = {
        "lamp": [[0, "on"], [6, "dim"], [12, "flicker"], [20, "off"]],
        "tv": [[0, "on", "blue"], [9, "on", "red"]],
    }
    staging = toon_sketch.Staging(
        data.SKETCH, data.SEED, data.DESCRIPTION, data.ACCESSIBILITY, data.NARRATION, data.TINTS,
        lambda shot: toon_rooms.dress(shot, "lounge", lights), {}, stickers={"dog": data.STICKER}, lit=True,
    )  # fmt: skip
    ep = toon_sketch.build(root, staging, {"--voice"})
    comp = tree(ep.cv).find("composition")

    def signed(node):
        return any((n.get("id") or "").startswith("sig-") for n in node.iter())

    shots = [g for g in comp.findall("group") if g.get("start") is not None and signed(g)]  # not the captions
    assert len(shots) > 1 and len(blended(comp, "multiply")) == len(shots)
    for g in shots:
        children = [c for c in g if c.tag != "animate"]
        lit = [i for i, c in enumerate(children) if blended(c, "multiply")]
        desk = [i for i, c in enumerate(children) if signed(c)]
        assert len(lit) == 1 and len(desk) == 1
        assert 2 <= lit[0] == desk[0] - 1  # the set, the character, then the light, then the desk
        assert not blended(children[0], "multiply") and not blended(children[-1], "screen")


# -- on the engine: the light reaches the character, never the signature ----------------------------------------------
MAIN_CUES = [[0, "on"], [1, "off"], [2, "dim"], [4, "flicker"]]
SCREEN_CUES = [[0, "on", "blue"], [1, "on", "red"], [2, "off"], [4, "on", "green"]]
LOW = min(FLICKER, key=lambda kv: kv[1])
AT = {"on": 0.5, "off": 1.5, "dim": 2.0 + FADE + 0.25, "flicker": 4.0 + LOW[0] + 0.02}
SIGNATURE_CROP = (880, 1240, 200, 240)  # x, y, width, height in frame pixels: the cactus and the code
FIGURE_CROP = (260, 960, 160, 160)  # the character's chest
DESK_FRONT = toon.fy(848) - SIGNATURE_CROP[1]  # the crop's rows from here down are the desk's front panel


def render_crop(
    engine, folder: Path, room: str, crop, *, signed=True, light_over_desk=False, times=AT, main=MAIN_CUES,
    screen=SCREEN_CUES,
) -> dict:  # fmt: skip
    """Render ``times`` of a scene cropped to ``crop``: the room lit by the ``main`` and ``screen`` cues, a stand-in
    figure, the light and the desk, in the shot's order (or the light over the desk, the arrangement the rooms
    avoid); returns the rows of each frame."""
    folder.mkdir(parents=True, exist_ok=True)
    font = next((f for f in SYSTEM_FONTS if f.exists()), None)
    if font is None:
        pytest.skip("renders text: needs a DejaVu Sans Bold system font")
    shutil.copy(font, folder / "f.ttf")
    x0, y0, w, h = crop
    scene = Scene(version="auto")
    scene.add_project(width=w, height=h, fps="24", duration=6, background=PEACH.background)
    cv = Canvas(scene, PEACH, font_asset="f", namer=flat_counter("k"), signature=Signature() if signed else None)
    cv.assets.add_font(id="f", src="f.ttf", family="DejaVu Sans", weight="700")
    frame = cv.group(cv.comp, "frame", x=-x0, y=-y0)
    back = cv.group(frame, "back")
    cv.ellipse(frame, toon.fx(60), toon.fy(520), toon.fh(260), toon.fh(300), "#f2efe9", cv.ink, 10)  # a pale shirt
    light = cv.group(frame, "light") if not light_over_desk else None
    toon.desk(cv, frame)
    if light is None:
        light = cv.group(frame, "light")
    r = ROOMS[room]
    toon_rooms.stage(cv, back, light, room, {r.main: main, r.screen: screen}, 6.0)
    path = folder / "crop.scene.xml"
    path.write_bytes(scene.to_bytes(layout="pretty"))
    frames = {}
    for state, t in times.items():
        out = folder / f"{state}.png"
        command = [str(engine), "render", "-t", str(t), "-o", str(out), str(path)]
        subprocess.run(command, check=True, capture_output=True)
        frames[state] = read_png(out)[2]
    return frames


def rgb(rows, x, y):
    return tuple(rows[y][4 * x : 4 * x + 3])


def signature_change(frames: dict, bare: list[bytes]) -> dict:
    """For each state, against the light-on frame: the share of the signature's pixels (those the signature
    changes in an unsigned frame) left exactly as they were, their mean change, and how many of the code's pixels
    (on the desk's front panel) changed at all."""
    w, h = SIGNATURE_CROP[2], SIGNATURE_CROP[3]
    on = frames["on"]
    mark = [(x, y) for y in range(h) for x in range(w) if rgb(on, x, y) != rgb(bare, x, y)]
    out = {}
    for state, rows in frames.items():
        delta = [max(abs(a - b) for a, b in zip(rgb(on, x, y), rgb(rows, x, y), strict=True)) for x, y in mark]
        code = sum(1 for (x, y), d in zip(mark, delta, strict=True) if y >= DESK_FRONT and d)
        out[state] = (sum(d == 0 for d in delta) / len(mark), sum(delta) / len(mark), code, len(mark))
    return out


@pytest.mark.parametrize("room", sorted(ROOMS))
def test_the_signature_reads_the_same_under_every_light_state(scene_render, tmp_path, room):
    frames = render_crop(scene_render, tmp_path / "signed", room, SIGNATURE_CROP)
    unsigned = render_crop(scene_render, tmp_path / "bare", room, SIGNATURE_CROP, signed=False, times={"on": 0.5})
    bare = unsigned["on"]
    change = signature_change(frames, bare)
    for state, (same, mean, code, marked) in change.items():
        assert marked > 2000, state  # the crop holds the whole signature
        assert code == 0, state
        assert same >= 0.95 and mean <= 4.0, (state, same, mean)
    # the control: the same light drawn over the desk fails the check
    over = signature_change(
        render_crop(scene_render, tmp_path / "over", room, SIGNATURE_CROP, light_over_desk=True), bare
    )
    assert over["off"][0] < 0.5 and over["off"][2] > 0


@pytest.mark.parametrize("room", sorted(ROOMS))
def test_the_light_visibly_reaches_the_character(scene_render, tmp_path, room):
    w, h = FIGURE_CROP[2], FIGURE_CROP[3]

    def mean(rows, channel):
        return sum(rows[y][4 * x + channel] for y in range(h) for x in range(w)) / (w * h)

    def brightness(rows):
        return sum(mean(rows, c) for c in range(3)) / 3

    # the main light alone (the screen off): the character darkens as it goes down
    main = render_crop(
        scene_render, tmp_path / "main", room, FIGURE_CROP, times={"on": 0.5, "off": 1.5, "dim": AT["dim"]},
        main=[[0, "on"], [1, "off"], [2, "dim"]], screen=[[0, "off", "blue"]],
    )  # fmt: skip
    on, off, dim = (brightness(main[k]) for k in ("on", "off", "dim"))
    assert off < 0.8 * on and off < dim < on
    # the screen alone (the main light off): its glow lights the character in its colour
    screen = render_crop(
        scene_render, tmp_path / "screen", room, FIGURE_CROP, times={"blue": 0.5, "red": 1.5, "dark": 2.5},
        main=[[0, "off"]], screen=[[0, "on", "blue"], [1, "on", "red"], [2, "off"]],
    )  # fmt: skip
    blue, red, dark = screen["blue"], screen["red"], screen["dark"]
    assert mean(blue, 2) > 1.05 * mean(dark, 2) and mean(red, 0) > 1.05 * mean(dark, 0)
    assert mean(red, 0) / mean(red, 2) > 1.15 * (mean(blue, 0) / mean(blue, 2))
