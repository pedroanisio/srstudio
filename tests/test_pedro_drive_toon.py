"""Pedro drives, then flies, in the layered drawing: the ramp is stepped and covers every luminance, the light is the
sculpt's key, the finish is one group the captions are not in, and a vehicle's plates are written once by content."""

from __future__ import annotations

import math
import os
import re
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
PILOTS = ROOT / "episodes" / "pilots"
if str(PILOTS) not in sys.path:
    sys.path.insert(0, str(PILOTS))

import pedro_drive as base  # noqa: E402
import pedro_drive_toon as toon  # noqa: E402

from srstudio import pedro_host  # noqa: E402
from srstudio.wire_draw import Plate  # noqa: E402


@pytest.fixture(autouse=True)
def caption_font(tmp_path_factory, monkeypatch):
    """A stand-in caption font: the piece only copies it and reads it for its hash, so no machine's fonts are needed."""
    fonts = tmp_path_factory.mktemp("fonts")
    (fonts / f"{base.FONT}.ttf").write_bytes(b"not a font, only read for its hash")
    monkeypatch.setenv("SRSTUDIO_FONTS", str(fonts))


def scene(piece: toon.TonePiece) -> str:
    return piece.cv.scene.to_bytes().decode()


def test_the_ramp_is_stepped_covers_zero_to_one_and_repeats_each_colour_at_both_ends_of_its_band():
    stops = toon.TonePiece.ramp()
    offsets = [o for o, _ in stops]
    assert offsets[0] == 0.0 and offsets[-1] == 1.0 and offsets == sorted(offsets)
    assert len(stops) == 2 * len(toon.PEDRO_BANDS)
    for (_, first), (_, second) in zip(stops[::2], stops[1::2], strict=True):
        assert first == second  # a band is one colour from its start to its end
    assert [c for _, c in stops[::2]] == [c for _, c in toon.PEDRO_BANDS]


def test_the_key_light_is_unit_length_and_up_toward_the_lens_and_to_the_left():
    x, y, z = toon.key_light()
    assert math.isclose(math.sqrt(x * x + y * y + z * z), 1.0)
    assert x < 0 < y and z > 0


def test_a_key_light_without_a_place_is_refused_with_a_typed_error(monkeypatch):
    class Lamp:
        id = "key"
        at = None

    monkeypatch.setattr(pedro_host, "LIGHTS", (Lamp(),))
    with pytest.raises(base.DriveError, match="no place"):
        toon.key_light()


def test_the_finish_is_one_group_whose_effects_are_bloom_vignette_and_grain(tmp_path):
    xml = scene(toon.TonePiece(tmp_path))
    for kind in ("bloom", "vignette", "film-grain"):
        assert len(re.findall(rf'type="{kind}"', xml)) == 1
    assert "0.12" in xml  # the grain amount


def test_grain_can_be_removed_or_set_and_a_bare_piece_has_no_finish_at_all(tmp_path):
    assert 'type="film-grain"' not in scene(toon.TonePiece(tmp_path / "a", grain=0))
    assert 'type="bloom"' in scene(toon.TonePiece(tmp_path / "a2", grain=0))
    assert re.search(r'type="film-grain" amount="0\.3"', scene(toon.TonePiece(tmp_path / "b", grain=0.3)))
    bare = scene(toon.TonePiece(tmp_path / "c", finish=False))
    assert not any(f'type="{k}"' in bare for k in toon.FINISH)


def test_the_finish_defaults_are_not_changed_by_a_piece_that_removes_its_grain(tmp_path):
    toon.TonePiece(tmp_path, grain=0)
    assert toon.FINISH["film-grain"]["amount"] == 0.12


def test_pedros_two_effects_are_declared_once_and_the_ring_is_ink(tmp_path):
    xml = scene(toon.TonePiece(tmp_path))
    assert xml.count('type="gradient-map"') == 1 and xml.count('type="outline"') == 1
    assert toon.INK in xml and re.fullmatch(r"#[0-9a-f]{6}", toon.INK)


def test_a_vehicle_plate_is_written_once_by_its_content_and_laid_with_its_corner(tmp_path):
    piece = toon.TonePiece(tmp_path)
    rig = piece.cv.group(piece.cv.comp, "rig")
    png = b"\x89PNG-one"
    piece.slab(rig, Plate(png, 12.5, -7.0, 40, 30))
    piece.slab(rig, Plate(png, 12.5, -7.0, 40, 30))
    piece.slab(rig, Plate(b"\x89PNG-two", 0.0, 0.0, 8, 8))
    files = sorted((tmp_path / "assets" / "vehicle").glob("*.png"))
    assert len(files) == 2 and {f.read_bytes() for f in files} == {png, b"\x89PNG-two"}
    xml = scene(piece)
    assert xml.count('src="assets/vehicle/') == 2  # an asset for each content, not each use
    assert len(re.findall(r'<layer id="[^"]+" asset="vehicle-', xml)) == 3  # but a layer for each use
    assert 'x="12.5" y="-7"' in xml


def test_far_throws_the_road_out_of_focus_with_a_haze_and_leaves_the_sky_sharp(tmp_path):
    piece = toon.TonePiece(tmp_path)
    stage = piece.cv.group(piece.cv.comp, "stage")
    assert piece.far(stage, "road") is not stage
    assert piece.far(stage, "sky") is stage
    xml = scene(piece)
    assert all(f"{name}{tail}" in xml for name in ("road-haze", "sky-haze") for tail in ("", "-below"))


def test_occupied_cuts_at_the_measured_edge_the_upper_half_before_him_and_the_lower_half_after(tmp_path):
    calls: list[str] = []
    seen: list[tuple[float, float]] = []
    piece = toon.TonePiece(tmp_path)
    rig = piece.cv.group(piece.cv.comp, "rig")
    shot = {"at": (540.0, 960.0), "width": 900.0}

    class Spot:
        y, scale = 900.0, 100.0

    def find(anchor, **_):
        return Spot()

    def edge(anchor, below, reach, **_):
        seen.append((below, reach))
        return -35.0, 0.07

    def plate(light, rows, tilt, **_):
        calls.append(f"plate{rows[0]:.0f}@{tilt}")
        return Plate(f"p{rows}".encode(), 0.0, 0.0, 1, 1)

    def prop(cv, parent, rows, tilt, **_):
        calls.append("lines")

    piece.man = lambda *a, **k: calls.append("man")  # type: ignore[method-assign]
    toon.PLATE_OF[prop] = plate
    toon.EDGE_OF[prop] = edge
    try:
        piece.occupied(rig, prop, find, shot, "driver-head", 0.5, 1.0, (), None, None)
    finally:
        del toon.PLATE_OF[prop], toon.EDGE_OF[prop]
    assert seen == [(0.5, toon.REACH)]  # looked for 0.5 m under his head
    assert calls == ["plate-100000@0.07", "lines", "man", "plate-35@0.07", "lines"]


needs_engine = pytest.mark.skipif(
    not os.environ.get("SRSTUDIO_ENGINE")
    or not (os.environ.get("SRSTUDIO_RENDERS") or os.environ.get("SRSTUDIO_PLATES")),
    reason="set SRSTUDIO_ENGINE and SRSTUDIO_RENDERS (or SRSTUDIO_PLATES) to render the plates",
)


@needs_engine
def test_the_whole_piece_builds_twice_to_the_same_bytes_and_its_scene_is_well_formed(tmp_path):
    import hashlib
    import xml.etree.ElementTree as ET

    first = toon.TonePiece(tmp_path / "a").build()
    second = toon.TonePiece(tmp_path / "b").build()
    assert first.read_bytes() == second.read_bytes()
    root = ET.fromstring(first.read_bytes())
    project = root.find("project")
    assert project is not None and project.get("duration") == "30" and project.get("fps") == "30"
    digests = {
        d.name: sorted(hashlib.sha256(f.read_bytes()).hexdigest() for f in (d / "assets" / "vehicle").glob("*.png"))
        for d in (tmp_path / "a", tmp_path / "b")
    }
    assert digests["a"] == digests["b"] and len(digests["a"]) >= 2  # the car's and the jet's plates, written the same
    captions = [e for e in root.iter() if e.tag == "text"]
    assert captions  # the captions are in the scene


@needs_engine
def test_the_captions_are_outside_the_finish_group(tmp_path):
    import xml.etree.ElementTree as ET

    root = ET.fromstring(toon.TonePiece(tmp_path).build().read_bytes())
    picture = next(e for e in root.iter("group") if e.get("id") == "picture")
    inside = {e.tag for e in picture.iter()}
    assert "text" not in inside  # information stays above the finish, in the composition itself


# -- the camera, his head and the wheels ---------------------------------------------------------------------------
def test_every_shot_has_its_camera_in_perspective_and_a_shot_the_piece_does_not_know_has_none(tmp_path):
    piece = toon.TonePiece(tmp_path)
    assert set(toon.OPTICS) == {"car-wide", "car-close", "jet-wide", "cockpit", "jet-away"}
    assert all(piece.optics(name)["distance"] > 0 for name in toon.OPTICS)
    assert piece.optics("car-wide")["view"] == "side-high"
    assert base.Piece(tmp_path / "flat").optics("car-wide") == {}  # the lines-only piece is as it was


def test_the_optics_are_a_copy_so_one_shot_cannot_change_the_next(tmp_path):
    piece = toon.TonePiece(tmp_path)
    piece.optics("cockpit")["distance"] = 1.0
    assert toon.OPTICS["cockpit"]["distance"] == 14.0


def test_his_head_moves_through_the_three_shots_he_is_in_and_the_others_keep_their_cast(tmp_path):
    piece = toon.TonePiece(tmp_path)
    for name, span in (("car-wide", base.CAR_WIDE), ("car-close", base.CAR_CLOSE), ("cockpit", base.COCKPIT)):
        cast = piece.cast(name, [("car-calm", *span)])
        assert cast[0][1] == span[0] and cast[-1][2] == span[1] and len(cast) > 3
        assert all(isinstance(plate, tuple) for plate, _, _ in cast)
    other = [("x", 0.0, 1.0)]
    assert piece.cast("jet-wide", other) == other


def test_the_cockpit_has_him_in_a_puffer_with_glasses_and_the_car_in_a_blazer_without(tmp_path):
    piece = toon.TonePiece(tmp_path)
    assert {p[2:] for p, _, _ in piece.cast("cockpit", [("jet-calm", *base.COCKPIT)])} == {("puffer", True)}
    assert {p[2:] for p, _, _ in piece.cast("car-close", [("car-calm", *base.CAR_CLOSE)])} == {("blazer", False)}


def test_the_wheels_turn_forward_in_layers_and_stand_still_when_the_traffic_stops(tmp_path):
    piece = toon.TonePiece(tmp_path)
    rig = piece.cv.group(piece.cv.comp, "rig")
    shot = {"at": (540.0, 1000.0), "width": 320, "seed": "monday", "view": "side-high", "distance": 6.5}
    piece.rolling(rig, shot, (0.0, 3.0))
    xml = scene(piece)
    layers = re.findall(r'<group id="[^"]+"[^>]*opacity="0"', xml)
    assert 2 <= len(layers) <= toon.PHASES + 1  # one layer of the pair of wheels for each angle they reach
    still = toon.TonePiece(tmp_path / "still")
    still.rolling(still.cv.group(still.cv.comp, "rig"), shot, (7.0, 8.5))  # the queue is at a halt from 6.6 s to 8.9 s
    assert len(re.findall(r'<group id="[^"]+"[^>]*opacity="0"', scene(still))) == 1  # one angle for the whole span


def test_each_wheel_layer_is_gated_to_the_frames_it_is_at_and_together_they_cover_every_frame(tmp_path):
    piece = toon.TonePiece(tmp_path)
    shot = {"at": (540.0, 1000.0), "width": 320, "seed": "monday", "view": "side-high", "distance": 6.5}
    piece.rolling(piece.cv.group(piece.cv.comp, "rig"), shot, (0.0, 1.0))
    import xml.etree.ElementTree as ET

    root = ET.fromstring(piece.cv.scene.to_bytes())
    frames = set()
    for group in root.iter("group"):
        if group.get("opacity") != "0":
            continue
        for animate in group.iter("animate"):
            if animate.get("property") == "opacity":
                keys = [(float(k.get("time")), k.get("value")) for k in animate.iter("key")]
                on = [t for t, v in keys if float(v) == 1.0]
                frames.update(round(t * base.FPS) for t in on)
    assert frames and max(frames) < base.FPS  # every layer's on-times lie inside the second asked for
