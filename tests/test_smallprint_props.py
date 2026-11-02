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
