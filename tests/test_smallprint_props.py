"""Small Print's worktop props and Rafa's tears: each state builds, stands where a phone shows it, and refuses what
it does not have (ADR 0195)."""

import numpy as np
import pytest

from srstudio import clay, host_kit, layout, plates, rafa, rafa_host, registry
from srstudio import smallprint_props as sp

STATED = [(prop, state) for prop, states in sp.STATES.items() for state in states]


def drawn(prop, state):
    m = clay.Model()
    x, y, z, yaw, scale = sp.PLACES[prop]
    with m.at(x, y, z, yaw=yaw, scale=scale):
        sp.draw(m, prop, state)
    return m.meshes()


def face_rows() -> dict[int, tuple[float, float]]:
    """His head as the lens sees it, placed at his neck as his plates place it: each 10 px row's left and right."""
    m = clay.Model()
    rafa.skull(m)
    pts = rafa_host.project(np.concatenate([mesh.vertices for mesh in m.meshes()]) + np.array(rafa.NECK))
    rows: dict[int, tuple[float, float]] = {}
    for x, y in pts:
        lo, hi = rows.get(int(y // 10), (np.inf, -np.inf))
        rows[int(y // 10)] = (min(lo, x), max(hi, x))
    return rows


def test_his_face_is_where_his_plates_put_it():
    rows = face_rows()
    assert 300 < min(rows) * 10 and max(rows) * 10 < 1100, "his head is in the upper middle of the frame"


@pytest.mark.parametrize(("prop", "state"), STATED)
def test_every_state_builds_from_known_materials_and_stands_above_the_captions(prop, state):
    meshes = drawn(prop, state)
    assert {mesh.material for mesh in meshes} <= sp.materials().keys()
    box = rafa_host.project(np.concatenate([mesh.vertices for mesh in meshes]))
    region = layout.VERTICAL.region(rafa_host.WIDTH, rafa_host.HEIGHT)
    assert box[:, 1].max() < region.y1 - host_kit.CAPTION_LOOK.block
    if prop != "smallprint-roll":  # the roll's sheet runs out of the frame on purpose
        assert box[:, 0].min() >= region.x0 and box[:, 0].max() <= region.x1


@pytest.mark.parametrize(("prop", "state"), STATED)
def test_no_prop_stands_over_his_face(prop, state):
    rows = face_rows()
    pts = rafa_host.project(np.concatenate([mesh.vertices for mesh in drawn(prop, state)]))
    over = [(x, y) for x, y in pts if (row := rows.get(int(y // 10))) and row[0] < x < row[1]]
    assert not over, f"{prop} {state} covers his face at {over[0]}"


def test_the_roll_runs_out_of_the_frame_at_the_left():
    pts = rafa_host.project(np.concatenate([mesh.vertices for mesh in drawn("smallprint-roll", "roll")]))
    assert pts[:, 0].min() < 0.0


def test_the_penny_falls_down_past_the_tower_and_lands():
    heights = []
    for state in sp.TOWER_STATES:
        m = clay.Model()
        sp.tower(m, state)
        copper = next(mesh for mesh in m.meshes() if mesh.material == "copper")
        heights.append(copper.vertices[:, 1].mean())
    assert heights == sorted(heights), "y grows downwards: each state is lower than the one before"
    assert heights[-1] > -2.0, "it ends on the worktop"


def test_each_fold_halves_the_sheet_and_thickens_it():
    for a, b in zip(sp._SHEETS, sp._SHEETS[1:], strict=False):
        assert b[0] * b[1] < a[0] * a[1] and b[2] > a[2]
    m = clay.Model()
    sp.paper(m, "fold-7")
    lines = next(mesh for mesh in m.meshes() if mesh.material == "cream")
    assert len(lines.vertices) == 7 * len(clay_box_vertices())


def clay_box_vertices():
    m = clay.Model()
    m.box("cream", (0, 0, 0), (0.3, 1.0, 0.18), 0.0)
    return m.meshes()[0].vertices


@pytest.mark.parametrize("state", sp.ONION_STATES)
def test_his_fist_rides_with_the_knife(state):
    plate = sp.worktop("smallprint-onion", state)
    flesh = np.concatenate([m.vertices for item in plate.placed for m in item.meshes if m.material == "flesh"])
    steel = np.concatenate([m.vertices for item in plate.placed for m in item.meshes if m.material == "steel"])
    assert abs(flesh[:, 1].mean() - steel[:, 1].mean()) < 20.0
    assert flesh[:, 0].min() > steel[:, 0].min(), "the blade reaches past his fist towards the onion"


def test_the_knife_is_lower_when_it_is_down():
    up = sp.worktop("smallprint-onion", "half-up")
    down = sp.worktop("smallprint-onion", "half-down")

    def blade(plate):
        return np.concatenate([m.vertices for item in plate.placed for m in item.meshes if m.material == "steel"])

    assert blade(down)[:, 1].mean() > blade(up)[:, 1].mean() + 10.0


@pytest.mark.parametrize("prop", sp.STATES)
def test_the_worktop_carries_his_hand_his_cuff_and_the_room_edge(prop):
    plate = sp.worktop(prop, sp.STATES[prop][0])
    names = {mesh.material for item in plate.placed for mesh in item.meshes}
    assert {"flesh", "teal", "teallight", "oak", "lemon"} <= names
    assert plate.camera == rafa_host.CAMERA
    assert plate.background == plates.CLEAR


def test_a_new_clay_material_gets_the_clay_finish_and_his_own_keep_theirs():
    m = clay.Model()
    sp.tower(m)
    stone = next(mesh for mesh in m.meshes() if mesh.material == "towerstone")
    assert sp.finished(stone).uvs is not None
    copper = next(mesh for mesh in m.meshes() if mesh.material == "copper")
    assert sp.finished(copper) is copper
    m = clay.Model()
    rafa.counter(m)
    oak = next(mesh for mesh in m.meshes() if mesh.material == "oak")
    np.testing.assert_array_equal(sp.finished(oak).uvs, rafa.finished(oak).uvs)


def test_his_own_materials_are_unchanged():
    for name, material in rafa.materials().items():
        assert sp.materials()[name] is material


def test_the_tears_lie_on_his_skin_one_under_each_eye():
    m = clay.Model()
    sp.tears(m)
    tear = m.meshes()[0]
    assert tear.material == "tear"
    x = tear.vertices[:, 0]
    assert (x < 0).any() and (x > 0).any()
    np.testing.assert_allclose(np.sort(x[x > 0])[-1], -np.sort(x[x < 0])[0], atol=1e-6)
    eyes = rafa.mood("public-smile").eye_y - rafa.NECK[1]
    assert (tear.vertices[:, 1] > eyes).all(), "every tear is under his eyes"
    off = np.array([vz + rafa.NECK[2] - sp._skin_z(vx, vy + rafa.NECK[1]) for vx, vy, vz in tear.vertices[::7]])
    assert off.min() > -3.0, "no bead floats off his skin towards the lens"
    assert (off < 0).mean() > 0.4, "the beads stand out of his skin, where the lens sees them, not sunk in it"


def test_a_tear_plate_turns_with_his_head_and_holds_his_own_body():
    a, b = sp.tear_plate(0.0, 0.0), sp.tear_plate(4.0, 1.5)
    assert plates.digest(a) != plates.digest(b)
    assert a.placed[0].meshes == rafa_host._body()
    assert b.placed[1].rotation_y == -4.0 and b.placed[1].rotation_x == 1.5


@pytest.mark.parametrize(
    ("call", "error"),
    [
        (lambda: sp.tower(clay.Model(), "flying"), "tower's states"),
        (lambda: sp.paper(clay.Model(), "fold-8"), "paper's states"),
        (lambda: sp.onion(clay.Model(), "diced-up"), "onion's states"),
        (lambda: sp.roll(clay.Model(), "unrolled"), "one state"),
        (lambda: sp.tears(clay.Model(), "sobbing"), "one state"),
        (lambda: sp.phone(clay.Model(), "ringing"), "phone's states"),
        (lambda: sp.bowl(clay.Model(), "dry"), "bowl's states"),
        (lambda: sp.wall(clay.Model(), "fog"), "wall's states"),
        (lambda: sp.goldfish(clay.Model(), "asleep"), "goldfish's states"),
        (lambda: sp.apple(clay.Model(), "rotten"), "apple's states"),
        (lambda: sp.can(clay.Model(), "crushed"), "can's states"),
        (lambda: sp.draw(clay.Model(), "rafa-mug", "x"), "worktop props"),
        (lambda: sp.worktop("smallprint-roll", "roll", "garage"), "his rooms"),
        (lambda: sp._skin_z(400.0, 0.0), "no skin"),
    ],
)
def test_what_is_not_there_is_refused(call, error):
    with pytest.raises(sp.PropError, match=error):
        call()


def test_the_parts_are_registered_with_contracts():
    for name in (*sp.STATES, "smallprint-tears"):
        entry = registry.get("prop", name)
        assert entry.contract is not None
        assert entry.describe()["contract"]["capabilities"]["animation"] is False


def test_the_catalog_shows_each_part_from_its_own_plate_and_nothing_for_another_part():
    for prop, states in sp.STATES.items():
        (plate,) = sp.part_plates(prop)
        assert plates.digest(plate) == plates.digest(sp.worktop(prop, states[0]))
    (tears,) = sp.part_plates("smallprint-tears")
    assert plates.digest(tears) == plates.digest(sp.tear_plate(0.0, 0.0))
    assert sp.part_plates("rafa-mug") == ()


def materials_of(plate) -> dict[str, np.ndarray]:
    rows: dict[str, list[np.ndarray]] = {}
    for item in plate.placed:
        for mesh in item.meshes:
            rows.setdefault(mesh.material, []).append(mesh.vertices)
    return {name: np.concatenate(v) for name, v in rows.items()}


def test_the_phone_shows_a_red_dot_while_it_records_and_the_take_while_it_plays():
    def made(state):
        m = clay.Model()
        sp.phone(m, state)
        return {mesh.material: mesh for mesh in m.meshes()}

    recording, playing = made("recording"), made("playing")
    assert "red" in recording and "mint" not in recording
    assert "mint" in playing and "red" not in playing
    bars = playing["mint"].vertices
    assert np.ptp(bars[:, 0]) > 18.0 and np.ptp(bars[:, 1]) > 15.0, "a row of bars across the screen, of many heights"
    screen = recording["screen"].vertices
    for mark in (recording["red"], playing["mint"]):
        assert mark.vertices[:, 2].max() < screen[:, 2].min(), "the marks sit on the screen's face, to the lens"


def test_the_soaking_hand_is_under_the_water_inside_the_bowl_and_the_wrinkled_one_is_out_with_ridged_tips():
    x, y, z, _, _ = sp.PLACES["smallprint-bowl"]
    soaking = materials_of(sp.worktop("smallprint-bowl", "soaking"))
    water_top = soaking["water"][:, 1].min()
    hand = soaking["flesh"]
    assert (hand[:, 1] > water_top).all(), "every bit of his hand is under the water's surface"
    assert (np.hypot(hand[:, 0] - x, hand[:, 2] - z) < 30.0).all(), "and inside the bowl's rim"
    assert "lip" not in soaking
    wrinkled = materials_of(sp.worktop("smallprint-bowl", "wrinkled"))
    out = wrinkled["flesh"]
    assert (np.hypot(out[:, 0] - x, out[:, 2] - z) > 30.0).all(), "out of the bowl, on the worktop"
    ridges = wrinkled["lip"]
    assert abs(ridges[:, 0].mean() - out[:, 0].mean()) < 15.0 and ridges[:, 1].max() <= y
    m = clay.Model()
    sp.wrinkles(m, 0.0, 0.0, 0.0)
    assert len(m.meshes()) == 1 and len(m.meshes()[0].vertices) % 15 == 0, "three ridges on each of five tips"


def test_his_hand_moves_only_for_the_states_that_say_so():
    for (prop, state), (kind, _) in sp.HANDS.items():
        assert state in sp.STATES[prop] and kind in ("dip", "wrinkled", "hold")
    a, b = (materials_of(sp.worktop("smallprint-phone", state))["flesh"] for state in sp.PHONE_STATES)
    np.testing.assert_array_equal(a, b)
    c, d = (materials_of(sp.worktop("smallprint-bowl", state))["flesh"] for state in sp.BOWL_STATES)
    assert c.shape != d.shape or not np.allclose(c, d)


def test_on_snow_the_land_goes_white_and_the_wall_stays_as_it_was():
    def made(state):
        m = clay.Model()
        sp.wall(m, state)
        return {mesh.material: mesh.vertices for mesh in m.meshes()}

    land, snow = made("land"), made("snow")
    assert "snow" not in land and "snow" in snow
    np.testing.assert_array_equal(land["wallstone"], snow["wallstone"])
    assert snow["wallstone"][:, 1].min() < snow["snow"][:, 1].min(), "the wall stands up out of the snow"
    stone, ground = (sp.materials()[name].color for name in ("wallstone", "land"))
    assert _contrast(stone, ground) < 1.3, "on bare land the wall is the land's own colour"
    assert _contrast(stone, sp.materials()["snow"].color) > 1.8, "on snow it stands out"


def _contrast(a: str, b: str) -> float:
    def lum(colour: str) -> float:
        rgb = [int(colour[i : i + 2], 16) / 255 for i in (1, 3, 5)]
        lin = [c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4 for c in rgb]
        return 0.2126 * lin[0] + 0.7152 * lin[1] + 0.0722 * lin[2]

    hi, lo = sorted((lum(a), lum(b)), reverse=True)
    return (hi + 0.05) / (lo + 0.05)


def test_the_goldfish_swims_at_the_top_of_its_water_and_comes_to_the_front_for_its_flakes():
    def made(state):
        m = clay.Model()
        sp.goldfish(m, state)
        return {mesh.material: mesh.vertices for mesh in m.meshes()}

    rows = {state: made(state) for state in sp.GOLDFISH_STATES}
    for state, parts in rows.items():
        water_top = parts["water"][:, 1].min()
        fish = parts["goldfish"]
        assert fish[:, 1].min() < water_top, f"{state}: his back breaks the surface, where the lens sees him"
        assert (np.hypot(fish[:, 0], fish[:, 2]) < sp.FISHBOWL_RIM).all(), f"{state}: inside the bowl"
    assert "flake" in rows["fed"] and "flake" not in rows["swim"] and "flake" not in rows["turn"]
    assert rows["fed"]["goldfish"][:, 2].mean() < rows["swim"]["goldfish"][:, 2].mean() - 8.0, "he comes to the front"
    swim, turn = rows["swim"]["goldfish"][:, 0].mean(), rows["turn"]["goldfish"][:, 0].mean()
    assert abs(swim - turn) > 10.0, "he crosses the bowl between swim and turn"


def test_the_goldfish_comes_up_nose_first_with_his_mouth_open_so_he_reads_alive():
    for state in sp.GOLDFISH_STATES:
        m = clay.Model()
        sp.goldfish(m, state)
        parts = {mesh.material: mesh.vertices for mesh in m.meshes()}
        fish, facing = parts["goldfish"], sp._FISH[state][2]
        ahead = facing * fish[:, 0]
        nose, tail = fish[ahead >= ahead.max() - 1.0], fish[ahead <= ahead.min() + 1.0]
        assert nose[:, 1].mean() < tail[:, 1].mean() - 4.0, f"{state}: nose up, not lying flat on the water"
        mouth = parts["fishmouth"]
        assert facing * (mouth[:, 0].mean() - fish[:, 0].mean()) > 4.0, f"{state}: his mouth is at his nose"
        assert mouth[:, 1].mean() < parts["water"][:, 1].min(), f"{state}: his mouth is out of the water"


def test_a_cut_apple_is_pale_then_brown_and_the_lemon_half_stays_pale():
    def made(state):
        m = clay.Model()
        sp.apple(m, state)
        return {mesh.material: mesh.vertices for mesh in m.meshes()}

    fresh, brown, lemon = (made(state) for state in sp.APPLE_STATES)
    assert "appleflesh" in fresh and "applebrown" not in fresh
    assert "applebrown" in brown and "appleflesh" not in brown
    assert "appleflesh" in lemon and "applebrown" in lemon and "lemon" in lemon
    pale, browned = lemon["appleflesh"][:, 0].mean(), lemon["applebrown"][:, 0].mean()
    squeezed = lemon["lemon"][:, 0].mean()
    assert abs(squeezed - pale) < abs(squeezed - browned), "the lemon is by the half that stays pale"
    for parts in (fresh, brown, lemon):
        face = parts.get("appleflesh", parts.get("applebrown"))
        assert face[:, 2].min() < parts["appleskin"][:, 2].min() + 1.0, "the cut face looks at the lens"
    stone, flesh = (sp.materials()[name].color for name in ("applebrown", "appleflesh"))
    assert _contrast(stone, flesh) > 1.6, "brown reads as brown against the fresh flesh"


def can_parts(state):
    return materials_of(sp.worktop("smallprint-can", state))


def test_the_shaken_can_is_in_his_hand_off_the_worktop_and_goes_up_and_down():
    y = sp.PLACES["smallprint-can"][1]
    up, down = can_parts("shake-up"), can_parts("shake-down")
    for parts in (up, down):
        can = parts["canpaint"]
        assert can[:, 1].max() < y - 10.0, "lifted off the worktop"
        hand = parts["flesh"]
        middle = can.mean(axis=0)
        assert np.hypot(*(hand.mean(axis=0) - middle)[[0, 2]]) < 22.0, "his hand is round the can"
        assert can[:, 1].min() < hand[:, 1].min() < can[:, 1].max(), "and holds it between its top and its foot"
    assert up["canpaint"][:, 1].mean() < down["canpaint"][:, 1].mean() - 6.0, "a shake moves it"
    assert "foam" not in up and "foam" not in down


def test_the_opened_can_foams_over_its_rim_and_down_its_side_and_after_a_wait_it_does_not():
    y = sp.PLACES["smallprint-can"][1]
    foamed, calm = can_parts("foam"), can_parts("calm")
    for parts in (foamed, calm):
        assert parts["canpaint"][:, 1].max() == pytest.approx(y, abs=1.5), "it stands on the worktop"
    foam = foamed["foam"]
    top = foamed["canpaint"][:, 1].min()
    assert foam[:, 1].min() < top - 3.0, "the foam stands up over the top"
    assert foam[:, 1].max() > top + 15.0, "and runs down its side"
    assert "foam" not in calm and "black" in calm, "open, and nothing came out"
    for state in sp.CAN_STATES:
        assert "canpaint" in can_parts(state)


def test_only_the_shaken_can_moves_his_hand_off_the_worktop():
    rest = can_parts("calm")["flesh"]
    held = can_parts("shake-up")["flesh"]
    assert held[:, 1].mean() < rest[:, 1].mean() - 10.0


def test_the_flies_sit_on_the_bare_horse_and_hang_over_the_striped_coat_without_touching_it():
    bare, coated = (materials_of(sp.worktop("smallprint-horse", state)) for state in sp.HORSE_STATES)
    y, scale = sp.PLACES["smallprint-horse"][1], sp.PLACES["smallprint-horse"][4]
    back = y + (sp.HORSE_BACK - sp.HORSE_BODY[1]) * scale  # the top of his back
    assert bare["fly"][:, 1].max() > back, "on him, not over him"
    assert "coat" not in bare and "coatstripe" not in bare
    coat = np.concatenate([coated["coat"], coated["coatstripe"]])
    assert coated["fly"][:, 1].max() < coat[:, 1].min(), "over the coat, every one clear of it"
    assert coated["wing"][:, 1].max() < coat[:, 1].min()
    stripes = coated["coatstripe"]
    assert np.ptp(stripes[:, 0]) > 0.5 * np.ptp(coated["coat"][:, 0]), "stripes run the coat's length"
    ink, white = (sp.materials()[name].color for name in ("coatstripe", "coat"))
    assert _contrast(ink, white) > 4.5, "black on white, a zebra's stripes"


def test_the_grown_sunflower_faces_east_and_the_lit_lamp_to_its_west_does_not_turn_it():
    dark, lit = (materials_of(sp.worktop("smallprint-sunflower", state)) for state in sp.SUNFLOWER_STATES)
    for parts in (dark, lit):
        seeds, petals, lamp = parts["seedhead"], parts["petal"], parts["lampbody"]
        assert seeds[:, 0].mean() < petals[:, 0].mean() - 0.5, "its middle is to the east (frame left) of its petals"
        assert lamp[:, 0].min() > seeds[:, 0].max(), "the lamp stands to its west"
    assert np.allclose(dark["seedhead"], lit["seedhead"]) and np.allclose(dark["petal"], lit["petal"]), (
        "a grown sunflower does not turn to the light"
    )
    assert "bulb" in lit and "bulb" not in dark and "bulboff" in dark, "the lamp is off, then on"
    y = sp.PLACES["smallprint-sunflower"][1]
    pool = lit["bulb"][np.abs(lit["bulb"][:, 1] - y) < 1.0]
    assert len(pool) and np.ptp(pool[:, 0]) > 20.0, "and lights the worktop under it"
