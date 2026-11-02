"""An ink pass built on a finished 3D group: flat id colours that outline what the eye reads as separate surfaces, in
the same document under the same cameras, with animation shared and nothing silently dropped."""

import subprocess

import numpy as np
import pytest
from scipy import ndimage
from sr_core.scene import io

from srstudio import ink_pass as ip
from srstudio import plates
from srstudio.errors import SrstudioError

SCENE = b"""<?xml version="1.0" encoding="UTF-8"?>
<scene version="1.1">
  <project width="64" height="64" fps="30" duration="1" seed="1" background="#202020" antialias3d="4"/>
  <assets><mesh id="m" src="m.obj" format="obj" sha256="%s"/></assets>
  <materials>
    <material id="skin" baseColor="#c08040" doubleSided="true"/>
    <material id="skin-warm" baseColor="#d09050"/>
    <material id="hair" baseColor="#101010"/>
    <material id="hide" baseColor="#000000"/>
  </materials>
  <composition>
    <group id="picture">
      <group id="world">
        <object3D id="rig" primitive="sphere" material="hide" radius="0.1" visible="false">
          <animate property="x" defaultInterpolation="linear">
            <key time="0" value="0"/><key time="1" value="9"/>
          </animate>
        </object3D>
        <object3D id="face" primitive="box" material="skin" width="9" height="9" depth="9" parent="rig"
          castShadow="true" receiveShadow="true"/>
        <object3D id="cheek" primitive="mesh" mesh="m" material="skin-warm" parent="rig" castShadow="true"/>
        <object3D id="fringe" primitive="mesh" mesh="m" material="hair" parent="rig"/>
        <object3D id="wheel" primitive="mesh" mesh="m" material="hair" parent="face">
          <animate property="rotation" defaultInterpolation="linear">
            <key time="0" value="0"/><key time="1" value="90"/>
          </animate>
        </object3D>
      </group>
      <group id="caption"/>
    </group>
    <camera id="lens" start="0" end="1" x="0" y="0" z="-90" projection="perspective" fov="40" near="5" far="900"/>
  </composition>
  <lights><light id="sun" type="directional" intensity="2" yaw="70" pitch="-24"/></lights>
</scene>
""" % (b"0" * 64)
SKIN = {"skin-warm": "skin"}


def build(**kw):
    scene = io.read(SCENE)
    return scene, ip.ink_pass(scene, "world", families=SKIN, **kw)


def objects(group):
    return {o.id: o for o in group.elements() if o.xml_name == "object3D"}


def section(scene, name):
    return next(n for n in scene.elements() if n.xml_name == name)


def material(scene, id_):
    found = [m for m in section(scene, "materials").elements() if m.id == id_]
    assert len(found) == 1
    return found[0]


def test_the_pass_sits_straight_above_its_world():
    scene, group = build()
    names = [g.id for g in group.owner.elements()]
    assert names == ["world", "ink", "caption"]


def test_a_copy_of_every_visible_object_and_none_of_the_rig():
    _, group = build()
    assert sorted(objects(group)) == ["i-cheek", "i-face", "i-fringe", "i-wheel"]


def test_a_copy_follows_the_shared_rig_and_its_own_copied_parent():
    _, group = build()
    by_id = objects(group)
    assert by_id["i-face"].parent == "rig"
    assert by_id["i-wheel"].parent == "i-face"


def test_a_copy_keeps_its_own_animation():
    _, group = build()
    keys = objects(group)["i-wheel"].elements()[0].elements()
    assert [k.value for k in keys] == ["0", "90"]


def test_a_copy_casts_no_shadow_and_receives_none():
    _, group = build()
    attrs = objects(group)["i-face"].attributes()
    assert "castShadow" not in attrs
    assert "receiveShadow" not in attrs


def test_surfaces_of_two_families_on_one_parent_differ():
    _, group = build()
    by_id = objects(group)
    assert by_id["i-cheek"].material != by_id["i-fringe"].material


def test_two_mesh_pieces_of_one_family_merge():
    scene = io.read(SCENE.replace(b'material="hair" parent="rig"', b'material="skin" parent="rig"'))
    by_id = objects(ip.ink_pass(scene, "world", families=SKIN))
    assert by_id["i-cheek"].material == by_id["i-fringe"].material


def test_a_primitive_keeps_its_own_colour():
    scene, group = build()
    by_id = objects(group)
    assert by_id["i-face"].material != by_id["i-cheek"].material


def test_id_materials_are_unlit_and_never_cull_a_face():
    scene, group = build()
    found = material(scene, objects(group)["i-face"].material)
    assert found.attributes()["unlit"] == "true"
    assert found.attributes()["doubleSided"] == "true"


def test_a_colour_comes_from_the_key_and_is_stable():
    assert ip.id_colour("rig|skin") == ip.id_colour("rig|skin")
    assert ip.id_colour("rig|skin") != ip.id_colour("rig|hair")
    assert len(ip.id_colour("rig|skin")) == 7


def test_the_shaders_arrive_with_the_group_in_order():
    scene, group = build(ink=ip.Ink(pixels=(540, 960), radius=1.5))
    assert group.attributes()["effects"] == "ink-clean ink-lines"
    effects = {e.id: e for e in section(scene, "effects").elements()}
    assert effects["ink-clean"].src == "clean.fs"
    params = {p.name: p.value for p in effects["ink-lines"].elements()}
    assert params["pixelsX"] == "540"
    assert params["pixelsY"] == "960"
    assert params["radius"] == "1.5"


def test_two_passes_under_two_names_stay_apart():
    scene = io.read(SCENE)
    one = ip.ink_pass(scene, "world", families=SKIN)
    two = ip.ink_pass(scene, "world", families=SKIN, name="ink2", prefix="j-")
    assert sorted(objects(two)) == ["j-cheek", "j-face", "j-fringe", "j-wheel"]
    assert one.attributes()["effects"] != two.attributes()["effects"]


def test_the_files_land_beside_the_scene(tmp_path):
    written = ip.shaders(tmp_path)
    assert sorted(p.name for p in written) == ["clean.fs", "ink.fs"]
    assert all(p.parent == tmp_path and p.stat().st_size for p in written)


@pytest.mark.parametrize(
    "call, match",
    [
        (lambda s: ip.ink_pass(s, "nowhere"), "no group"),
        (lambda s: ip.ink_pass(s, "lens"), "no group"),
        (lambda s: ip.ink_pass(s, "caption"), "nothing visible"),
        (lambda s: ip.ink_pass(s, "world", name="caption"), "already"),
        (lambda s: ip.ink_pass(s, "world", prefix=""), "prefix"),
        (lambda s: ip.ink_pass(s, "world", name=""), "name"),
    ],
)
def test_a_pass_that_cannot_be_drawn_is_refused(call, match):
    with pytest.raises(ip.InkPassError, match=match):
        call(io.read(SCENE))


def test_a_clash_with_an_existing_id_is_refused():
    scene = io.read(SCENE.replace(b'id="cheek"', b'id="i-face"'))
    with pytest.raises(ip.InkPassError, match="already"):
        ip.ink_pass(scene, "world")


def test_a_refused_pass_leaves_the_scene_as_it_was():
    scene = io.read(SCENE.replace(b'id="cheek"', b'id="i-face"'))
    before = io.to_bytes(scene)
    with pytest.raises(ip.InkPassError):
        ip.ink_pass(scene, "world")
    assert io.to_bytes(scene) == before


@pytest.mark.parametrize(
    "kw",
    [
        {"pixels": (0, 10)},
        {"radius": 0},
        {"radius": float("nan")},
        {"wobble": -1},
        {"vary": -0.1},
        {"colour": (0.0, 0.0, 2.0)},
    ],
)
def test_bad_ink_is_refused(kw):
    with pytest.raises(ip.InkPassError):
        ip.Ink(**kw)


def test_the_error_is_a_library_error():
    assert issubclass(ip.InkPassError, SrstudioError)
    assert issubclass(ip.InkPassError, ValueError)


MOVING = b"""<?xml version="1.0" encoding="UTF-8"?>
<scene version="1.1">
  <project width="96" height="96" fps="30" duration="1" seed="1" background="#000000" antialias3d="1"/>
  <materials><material id="clay" baseColor="#c08040"/><material id="hide" baseColor="#000000"/></materials>
  <composition>
    <group id="world">
      <object3D id="aim" primitive="sphere" material="hide" radius="0.1" visible="false"/>
      <object3D id="rig" primitive="sphere" material="hide" radius="0.1" visible="false">
        <animate property="x" defaultInterpolation="linear">
          <key time="0" value="-30"/><key time="1" value="30"/>
        </animate>
      </object3D>
      <object3D id="box" primitive="box" material="clay" width="30" height="30" depth="30" parent="rig"/>
    </group>
    <camera id="lens" start="0" end="1" x="0" y="0" z="-160" projection="perspective" fov="40" near="5" far="900"
      target="aim"/>
  </composition>
  <lights><light id="sun" type="directional" intensity="2" yaw="70" pitch="-24"/></lights>
</scene>
"""


def test_the_pass_follows_a_moving_rig_on_the_engine(scene_render, tmp_path):
    scene = io.read(MOVING)
    ip.ink_pass(scene, "world", ink=ip.Ink(pixels=(96, 96)))
    ip.shaders(tmp_path)
    path = tmp_path / "scene.xml"
    path.write_bytes(io.to_bytes(scene))
    (tmp_path / "plain.xml").write_bytes(MOVING)
    for name in ("scene", "plain"):
        command = [scene_render, "render", tmp_path / f"{name}.xml", "--strict", "--frames", "25..=25"]
        command += ["-o", tmp_path / f"{name}%04d.png"]
        done = subprocess.run(command, capture_output=True, text=True, timeout=120)
        assert done.returncode == 0, done.stdout + done.stderr
    inked = plates.pixels(tmp_path / "scene0025.png")[..., :3].astype(int)
    plain = plates.pixels(tmp_path / "plain0025.png")[..., :3].astype(int)
    drawn = plain.sum(-1) > 20
    assert drawn.any()
    lines = np.abs(inked - plain).max(-1) > 40
    edge = drawn ^ ndimage.binary_erosion(drawn, iterations=3)
    assert lines.any()
    assert (lines & edge).sum() / lines.sum() > 0.8  # the ink is on the moved box, not where the rig began
