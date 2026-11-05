"""Juno v2 wears a home outfit as part of her look (ADR 0240, arc4d3's ruling 1793854854.581609: "Juno reads as naked").

The top and trousers are drawn by the rig on the torso and limbs, drawing by drawing, so they follow every pose and
in-between; a collar line sits under the chin and a cuff line at each wrist and ankle; hands, feet, head and face stay
skin. Version 1 draws byte for byte as it did before the outfit existed.
"""

import hashlib
import math
import xml.etree.ElementTree as ET

import pytest

from srstudio import blob, parts, registry, specimens
from srstudio.parts import Part, PartError
from support.soft_props import canvas

SCALE = 1.6
MOUTHS = [(0.0, "rest"), (1.0, "open")]
EVERY_POSE = [
    blob.cue(0.4 * i, p, (540.0, 1500.0), scale=SCALE, ease=0.2 if i else 0.0) for i, p in enumerate(blob.POSES)
]
END = 0.4 * len(blob.POSES)

# sha256 of each look's scene bytes over EVERY_POSE, measured on develop a455e253 before the outfit was added
BEFORE = {
    "juno": "20e0789e6213907a562ee89e84a90f7317f9ea34365cffe8062403bd46453924",
    "pip": "9335287de2084cc8859aa6b0b67e55c3a98b28223b9031a4fc5ff9739580caa2",
    "bo": "2be78384394d3400f1486cc858050a041ee33728a833f324f603145c7ee2a6fc",
    "remy": "b0bd68a86fa3e98edcba6e4bc7afcb1dd80874cd69b26b4fed65b660bb5bfef0",
}


def drawn(builder, cues=EVERY_POSE, end=END, id="juno"):
    cv = canvas()
    builder(cv, cv.comp, cues, end=end, scale=SCALE, mouth_states=MOUTHS, id=id)
    return cv, ET.fromstring(cv.scene.to_bytes(layout="pretty"))


def group(root, id: str):
    found = [g for g in root.iter("group") if g.get("id") == id]
    assert len(found) == 1, f"one group {id!r}, found {len(found)}"
    return found[0]


def shapes(node) -> list:
    return [e for e in node.iter() if e.tag == "shape"]


def path_keys(shape) -> list[tuple[float, str]]:
    keyed = [a for a in shape.findall("animate") if a.get("property") == "path"]
    if not keyed:
        return [(0.0, shape.get("path"))]
    return [(float(k.get("time")), k.get("value")) for k in keyed[0].findall("key")]


def points(d: str) -> list[tuple[float, float]]:
    nums = [float(v) for v in d.replace("M", " ").replace("L", " ").replace("Z", " ").split()]
    return list(zip(nums[0::2], nums[1::2], strict=True))


# -- version 1 is untouched ---------------------------------------------------------------------------------------
@pytest.mark.parametrize("name", sorted(BEFORE))
def test_version_one_looks_draw_byte_for_byte_as_before_the_outfit(name):
    _, root = drawn(getattr(blob, name), id=name)
    cv, _ = drawn(getattr(blob, name), id=name)
    assert hashlib.sha256(cv.scene.to_bytes()).hexdigest() == BEFORE[name]
    assert not [g for g in root.iter("group") if "cloth" in (g.get("id") or "")]


def test_version_one_juno_has_no_outfit_and_version_two_is_juno_in_one():
    assert blob.JUNO.outfit is None
    assert blob.JUNO_V2.outfit == blob.JUNO_HOME
    # her head, hair and face are exactly version 1's
    for field in ("name", "fill", "blush", "topper", "topper_id", "hair", "features", "features_id", "shade"):
        assert getattr(blob.JUNO_V2, field) == getattr(blob.JUNO, field), field
    assert (blob.JUNO_V2.catchlights, blob.JUNO_V2.lashes, blob.JUNO_V2.gloss) == (True, True, False)


# -- the colours ---------------------------------------------------------------------------------------------------
def test_delta_e_is_cie76_in_lab():
    assert blob.delta_e("#000000", "#000000") == 0
    assert blob.delta_e("#000000", "#FFFFFF") == pytest.approx(100.0, abs=0.01)
    assert blob.delta_e("#FF0000", "#00FF00") == pytest.approx(170.58, abs=0.05)


@pytest.mark.parametrize("cloth", ["top", "trousers"])
def test_the_outfit_stands_apart_from_her_skin(cloth):
    colour = getattr(blob.JUNO_HOME, cloth)
    assert blob.delta_e(colour, blob.JUNO_FILL) >= blob.MIN_CLOTH_DISTANCE
    assert blob.delta_e(colour, blob.JUNO_SHADE) >= blob.MIN_CLOTH_DISTANCE
    assert blob.MIN_CLOTH_DISTANCE >= 40  # far past "a slightly different peach"


def test_top_and_trousers_read_as_two_garments():
    assert blob.delta_e(blob.JUNO_HOME.top, blob.JUNO_HOME.trousers) >= blob.MIN_CLOTH_DISTANCE


def test_a_look_refuses_an_outfit_in_its_own_skin_tone():
    skin_tone = blob.Outfit(top="#F2C9B0", trousers="#3E4C6B", trim="#F3E6CF")
    with pytest.raises(blob.BlobError, match="top .* too close to its fill"):
        blob.Look("nude", fill=blob.JUNO_FILL, outfit=skin_tone)


@pytest.mark.parametrize(
    "kw", [{"top": "teal"}, {"hand": 0.0}, {"hand": -4.0}, {"foot": 120.0}, {"cuff": 0.0}, {"cuff": 30.0}]
)
def test_an_outfit_refuses_what_it_cannot_draw(kw):
    with pytest.raises(blob.BlobError):
        blob.Outfit(**{"top": "#3F8F8A", "trousers": "#D29B2A", "trim": "#F3E6CF", **kw})


# -- the drawing ------------------------------------------------------------------------------------------------------
def test_juno_two_is_registered_as_juno_at_2():
    entry = registry.get("character", "juno@2")
    assert entry.builder is blob.juno_v2
    assert entry.style == "soft"


def test_every_limb_and_the_torso_wear_cloth_on_every_drawing():
    _, root = drawn(blob.juno_v2)
    frames = blob.drawings(EVERY_POSE, end=END, fps=15)
    wear = {"torso": blob.JUNO_HOME.top, "arm_l": blob.JUNO_HOME.top, "arm_r": blob.JUNO_HOME.top,
            "leg_l": blob.JUNO_HOME.trousers, "leg_r": blob.JUNO_HOME.trousers}  # fmt: skip
    for limb, colour in wear.items():
        cloth = group(root, f"juno-fill-{limb}-cloth")
        fills = [s for s in shapes(cloth) if s.get("fill") == colour]
        assert fills, f"{limb} wears {colour}"
        keyed = path_keys(fills[0])
        assert len(keyed) == len(frames), f"{limb}'s cloth is redrawn on every drawing"
        for (t, d), frame in zip(keyed, frames, strict=True):
            assert t == pytest.approx(frame.time, abs=1e-5)
            stroke = frame.pose.limbs[limb]
            cloth = blob.clothed(stroke, blob.JUNO_HOME, limb)
            want = cloth.outline() if limb == "torso" else blob.cut(cloth)  # cloth stops square at the cuff
            assert d == want


def test_hands_feet_and_head_stay_skin():
    """The cloth stops short of each hand and foot, so the limb's own skin fill shows past the cuff, and the head is
    drawn in her skin over the top."""
    frames = blob.drawings(EVERY_POSE, end=END, fps=15)
    for frame in frames:
        for limb in (*blob.ARMS, *blob.FEET):
            stroke = frame.pose.limbs[limb]
            reach = blob.JUNO_HOME.reach(limb, stroke)
            along = [stroke.point(reach + (1 - reach) * k / 64) for k in range(65)]
            bare = sum(math.dist(a, b) for a, b in zip(along, along[1:], strict=False))
            whole = [stroke.point(k / 64) for k in range(65)]
            length = sum(math.dist(a, b) for a, b in zip(whole, whole[1:], strict=False))
            want = blob.JUNO_HOME.hand if limb in blob.ARMS else blob.JUNO_HOME.foot
            if length < 2 * want:  # an in-between folds the limb up: the sleeve keeps half of it, the hand the rest
                want = length / 2
            assert bare == pytest.approx(want, abs=1.0), (
                f"{frame.pose.name} {limb}: the same hand or foot every drawing"
            )
    _, root = drawn(blob.juno_v2)
    head = group(root, "juno-head-fill")
    assert [s.get("fill") for s in shapes(head)][0] == blob.JUNO_FILL


def test_a_collar_line_sits_under_the_chin_inside_the_body_on_every_drawing():
    _, root = drawn(blob.juno_v2)
    frames = blob.drawings(EVERY_POSE, end=END, fps=15)
    collar = group(root, "juno-collar")
    trim = [s for s in shapes(collar) if s.get("fill") == blob.JUNO_HOME.trim]
    line = [s for s in shapes(collar) if s.get("fill") == "#00000000" and s.get("stroke") == "#231E19"]
    assert trim and line
    keyed = path_keys(trim[0])
    assert len(keyed) == len(frames)
    for (_, d), frame in zip(keyed, frames, strict=True):
        hx, hy = frame.pose.head
        torso = frame.pose.limbs["torso"]
        for x, y in points(d):
            r = math.hypot(x - hx, y - hy)
            assert blob.HEAD - 3 <= r <= blob.HEAD + blob.COLLAR + 0.5, f"{frame.pose.name}: collar off the chin"
            assert blob.inside(torso, (x, y)), f"{frame.pose.name}: the collar pokes out of the body at {x:.0f},{y:.0f}"


@pytest.mark.parametrize("limb", ["arm_l", "arm_r", "leg_l", "leg_r"])
def test_a_cuff_line_crosses_each_wrist_and_ankle(limb):
    _, root = drawn(blob.juno_v2)
    frames = blob.drawings(EVERY_POSE, end=END, fps=15)
    cloth = group(root, f"juno-fill-{limb}-cloth")
    lines = [s for s in shapes(cloth) if s.get("fill") == "#00000000" and s.get("stroke") == "#231E19"]
    assert lines, f"{limb} has a cuff line"
    keyed = path_keys(lines[0])
    assert len(keyed) == len(frames)
    for (_, d), frame in zip(keyed, frames, strict=True):
        stroke = frame.pose.limbs[limb]
        (ax, ay), (bx, by) = points(d)
        across = math.dist((ax, ay), (bx, by))
        cloth_end = blob.clothed(stroke, blob.JUNO_HOME, limb)
        width = cloth_end.w1
        assert across == pytest.approx(width, abs=0.6), f"{frame.pose.name}: the cuff line spans the limb"
        mid = ((ax + bx) / 2, (ay + by) / 2)
        assert math.dist(mid, cloth_end.point(1.0)) < 0.6


def test_a_limb_in_front_dresses_in_front_too():
    cues = [blob.cue(0.0, "stand", (540.0, 1500.0), scale=SCALE), blob.cue(1.0, "sit", (540.0, 1400.0), scale=SCALE,
            ease=0.4)]  # fmt: skip
    _, root = drawn(blob.juno_v2, cues, end=2.0)
    for limb in ("arm_l", "arm_r", "leg_l"):
        front = group(root, f"juno-front-{limb}")
        assert [s for s in shapes(front) if s.get("fill") in (blob.JUNO_HOME.top, blob.JUNO_HOME.trousers)], limb


def test_an_arm_held_behind_the_body_is_drawn_behind_the_top():
    """With one colour a back arm's hand over the body never showed; dressed, it would float on the top. So an
    outfit draws the back arms first in the merged fill and the torso over them."""
    _, root = drawn(blob.juno_v2)
    fill = group(root, "juno-fill")
    order = [g.get("id") for g in fill.findall("group")]
    assert order.index("juno-fill-arm_r-cloth") < order.index("juno-fill-torso-cloth")
    assert order.index("juno-fill-arm_l-cloth") < order.index("juno-fill-torso-cloth")


# -- the version record ---------------------------------------------------------------------------------------------
def test_juno_two_is_a_proposed_version_and_version_one_stays_the_default():
    juno = parts.get("juno")
    assert [v.number for v in juno.versions] == [1, 2]
    assert juno.version(2).status == "proposed" and juno.version(2).approval is None
    assert juno.latest().number == 1  # arc4d3 approves version 2, not the agent that drew it
    assert "1793854854.581609" in juno.version(2).note


def test_juno_takes_a_second_version_because_a_reel_calls_it_by_name():
    assert parts.routed("juno", "character", "soft")
    assert not parts.routed("pip", "character", "soft")
    with pytest.raises(PartError, match="pip.*does not read pins"):
        Part("pip", "character", "soft", parts.get("juno").versions)


def test_juno_two_has_a_specimen_and_its_record_is_its_drawing():
    assert "juno@2" in specimens.SPECIMENS
    assert parts.get("juno").version(2).drawing  # a record to hold, not a blank that checks nothing
    specimens.check_record("juno", 2)


@pytest.mark.parametrize("pose", blob.POSES)
def test_top_draws_over_every_trouser_group_with_an_ink_hem(pose):
    _, root = drawn(blob.juno_v2, [blob.cue(0, pose, (540, 1400), scale=SCALE)], end=0.2)
    ordered = list(root.iter())
    top = group(root, "juno-fill-torso-cloth")
    for node in root.iter("group"):
        if any(s.get("fill") == blob.JUNO_HOME.trousers for s in node.findall("shape")):
            assert ordered.index(node) < ordered.index(top), pose
    seam = [s for s in shapes(top) if s.get("stroke") == "#231E19"]
    assert seam, f"{pose}: ink at the waist"
    assert float(seam[0].get("strokeWidth")) > 0


def _contains(poly, x, y):
    inside = False
    for (ax, ay), (bx, by) in zip(poly, poly[1:] + poly[:1], strict=True):
        if (ay > y) != (by > y) and x < (bx - ax) * (y - ay) / (by - ay) + ax:
            inside = not inside
    return inside


@pytest.mark.parametrize("pose", ["sit", "lounge", "floor"])
def test_no_trouser_fill_above_the_seated_hem_across_the_lap(pose):
    _, root = drawn(blob.juno_v2, [blob.cue(0, pose, (540, 1400), scale=SCALE)], end=0.2)
    # Evaluate the actual garment polygons in painter order at the hip and across the lap.
    polygons = []

    def visit(node, visible=True):
        visible = visible and node.get("opacity") != "0"
        if not visible:
            return
        if node.tag == "shape" and node.get("fill") in (blob.JUNO_HOME.top, blob.JUNO_HOME.trousers):
            polygons.append((node.get("fill"), points(path_keys(node)[0][1])))
        for child in node:
            visit(child, visible)

    visit(root)
    top = points(path_keys(shapes(group(root, "juno-fill-torso-cloth"))[0])[0][1])
    checked = 0
    for x in range(int(min(x for x, _ in top)), int(max(x for x, _ in top)), 3):
        for y in range(int(sum(y for _, y in top) / len(top)), int(max(y for _, y in top)), 3):
            if _contains(top, x, y):
                colours = [colour for colour, poly in polygons if _contains(poly, x, y)]
                assert colours[-1] == blob.JUNO_HOME.top, (pose, x, y)
                checked += 1
    assert checked > 0
