"""Plates: named by what they draw, rendered once, and a rebuild proves itself."""

from __future__ import annotations

import os
import stat
from pathlib import Path

import numpy as np
import pytest
from sr_core.scene import Scene

from srstudio import plates
from srstudio.canvas import Canvas
from srstudio.plates import Line, Material, Plate, PlateError, Print
from support.plates import plate


def test_a_digest_is_stable_and_follows_every_input():
    assert plates.digest(plate()) == plates.digest(plate())
    base = plates.digest(plate())
    assert plates.digest(plate(size=(11.0, 10.0, 10.0))) != base
    assert plates.digest(plate(rotation=2.0)) != base
    assert plates.digest(plate(background="#FFFFFF")) != base


def test_a_print_is_named_by_its_words():
    a = Print("#FFFFFF", 64, 64, (Line("GREAT", 32, 32, 12, "#000000"),))
    b = Print("#FFFFFF", 64, 64, (Line("FINE", 32, 32, 12, "#000000"),))
    assert plates.print_name(a) == plates.print_name(a) and plates.print_name(a) != plates.print_name(b)


@pytest.mark.parametrize("words", ("", "   ", "SEM CAFÉ", "Pão"))
def test_a_print_refuses_no_words_and_anything_but_english_letters(words):
    with pytest.raises(PlateError):
        Line(words, 0, 0, 10, "#000000")


def test_a_print_needs_a_size():
    with pytest.raises(PlateError):
        Line("OK", 0, 0, 0, "#000000")


def test_a_plate_refuses_nothing_in_it_and_an_unknown_material():
    good = plate()
    with pytest.raises(PlateError, match="something"):
        Plate(64, 64, good.camera, good.lights, (), good.materials)
    with pytest.raises(PlateError, match="material"):
        Plate(64, 64, good.camera, good.lights, good.placed, (Material("other", "#000000"),))
    with pytest.raises(PlateError, match="size"):
        Plate(0, 64, good.camera, good.lights, good.placed, good.materials)


def test_a_png_is_the_same_bytes_for_the_same_pixels_and_reads_back(tmp_path):
    rgba = np.zeros((3, 5, 4), np.uint8)
    rgba[1, 2] = (10, 20, 30, 40)
    first = plates.write_png(tmp_path / "a.png", rgba).read_bytes()
    second = plates.write_png(tmp_path / "b.png", rgba).read_bytes()
    assert first == second
    assert np.array_equal(plates.pixels(tmp_path / "a.png"), rgba)
    assert stat.S_IMODE(os.stat(tmp_path / "a.png").st_mode) == 0o600


def two(tmp_path: Path) -> tuple[Path, Path]:
    base = np.zeros((60, 60, 4), np.uint8)
    base[..., 3] = 255
    over = base.copy()
    over[20:30, 25:35, :3] = 200
    return plates.write_png(tmp_path / "base.png", base), plates.write_png(tmp_path / "over.png", over)


def test_a_patch_is_what_changed_with_a_feathered_rim(tmp_path):
    base, over = two(tmp_path)
    cut = plates.patch(base, over, tmp_path / "cache")
    assert cut is not None
    assert cut.x < 25 and cut.y < 20 and cut.x + cut.width > 35 and cut.y + cut.height > 30
    alpha = plates.pixels(cut.path)[..., 3]
    assert alpha[25 - cut.y, 30 - cut.x] == 255
    assert alpha[0, 0] < 255
    assert plates.patch(base, over, tmp_path / "cache") == cut


def test_a_patch_of_nothing_is_none(tmp_path):
    base, _ = two(tmp_path)
    assert plates.patch(base, base, tmp_path / "cache") is None
    assert plates.patch(base, base, tmp_path / "cache") is None


def test_a_patch_keeps_inside_its_box(tmp_path):
    base, over = two(tmp_path)
    assert plates.patch(base, over, tmp_path / "cache", within=(40, 40, 60, 60)) is None


def test_one_plate_placed_twice_is_one_asset_and_two_layers():
    """Two faces can be the same picture. The engine refuses a repeated id, so the second place reuses the first."""
    scene = Scene(version="auto")
    scene.add_project(width=64, height=64, fps="1", duration=1)
    cv = Canvas(scene, width=64, height=64)
    same = plate()
    plates.place(cv, cv.comp, same)
    plates.place(cv, cv.comp, same, y=5.0)
    plates.place(cv, cv.comp, plate(size=(20.0, 10.0, 10.0)))
    images = [node for node in cv.assets.nodes if getattr(node, "src", "").startswith("plates/")]
    assert [node.src for node in images] == [
        f"plates/{plates.digest(same)}.png",
        f"plates/{plates.digest(plate(size=(20.0, 10.0, 10.0)))}.png",
    ]
    layers = [node for node in cv.comp.nodes if getattr(node, "asset", "")]
    assert [(node.asset, node.y) for node in layers] == [(images[0].id, 0.0), (images[0].id, 5.0), (images[1].id, 0.0)]


def test_a_print_whose_font_is_not_in_the_folder_is_a_typed_error_that_names_the_folder(tmp_path):
    printed = Print("#ffffff", 64, 64, (Line("Hi", 32.0, 32.0, 12.0, "#000000"),))
    (tmp_path / "engine").write_bytes(b"engine")
    with pytest.raises(PlateError, match=str(tmp_path / "nowhere") + r"/fredoka-600\.ttf"):
        plates.print_png(printed, engine=tmp_path / "engine", cache=tmp_path / "cache", fonts=tmp_path / "nowhere")


def test_a_broken_engine_is_a_typed_error(tmp_path):
    engine = tmp_path / "engine"
    engine.write_text("#!/bin/sh\necho nope >&2\nexit 3\n")
    engine.chmod(0o755)
    with pytest.raises(PlateError, match="nope"):
        plates.render(plate(), engine=engine, cache=tmp_path / "cache", fonts=tmp_path)
    assert not list((tmp_path / "cache").glob("*.png")), "a failed render leaves no plate behind"


def test_a_cached_plate_is_not_rendered_again(tmp_path, monkeypatch):
    cache = tmp_path / "cache"
    made = plate()
    engine = tmp_path / "engine"
    engine.write_text("#!/bin/sh\nexit 9\n")
    engine.chmod(0o755)
    monkeypatch.setattr(
        plates, '_engine_render', lambda engine, source, out: plates.write_png(out, np.zeros((1, 1, 4)))
    )
    kept = plates.render(made, engine=engine, cache=cache, fonts=tmp_path)
    monkeypatch.setattr(plates, '_engine_render', lambda *args: pytest.fail('rendered again'))
    assert plates.render(made, engine=engine, cache=cache, fonts=tmp_path) == kept


def test_a_rebuild_gives_the_same_plate(scene_render, tmp_path):
    engine = scene_render
    made = plate()
    cache = tmp_path / "cache"
    fonts = tmp_path
    first = plates.render(made, engine=engine, cache=cache, fonts=fonts)
    assert first.suffix == '.png' and len(first.stem) == 64
    assert first.name != f"{plates.digest(made)}.png", 'render identity includes the selected engine'
    assert plates.pixels(first)[..., 3].max() == 255, "something was drawn"
    assert plates.pixels(first)[0, 0, 3] == 0, "a clear plate has real alpha"
    assert stat.S_IMODE(os.stat(first).st_mode) == 0o600
    assert stat.S_IMODE(os.stat(cache).st_mode) == 0o700
    pixels = plates.verify(made, engine=engine, cache=cache, fonts=fonts)
    first.unlink()
    again = plates.render(made, engine=engine, cache=cache, fonts=fonts)
    assert again == first
    assert plates.verify(made, engine=engine, cache=cache, fonts=fonts) == pixels


def test_a_texture_is_named_by_its_pixels_and_changes_a_digest():
    from srstudio.plates import Texture

    flat = np.full((4, 4, 4), 200, np.uint8)
    other = flat.copy()
    other[0, 0, 0] = 1
    assert Texture(flat).sha256 == Texture(flat.copy()).sha256 != Texture(other).sha256


def test_a_falloff_keeps_the_top_sharp_blurs_the_bottom_and_is_made_once(tmp_path):
    rows = np.zeros((60, 40, 4), np.uint8)
    rows[..., 3] = 255
    rows[:, 18:22, 0] = 255
    source = plates.write_png(tmp_path / "a.png", rows)
    out = plates.soften(source, tmp_path, sharp_to=10, soft_from=30, sigma=3.0)
    picture = plates.pixels(out)
    assert (picture[5, :, 0] == rows[5, :, 0]).all()
    assert picture[50, 20, 0] < 255 and picture[50, 14, 0] > 0
    stamp = out.stat().st_mtime_ns
    assert plates.soften(source, tmp_path, sharp_to=10, soft_from=30, sigma=3.0) == out
    assert out.stat().st_mtime_ns == stamp


def test_a_falloff_that_cannot_exist_is_refused(tmp_path):
    with pytest.raises(plates.PlateError, match="falloff"):
        plates.soften(tmp_path / "a.png", tmp_path, sharp_to=30, soft_from=10, sigma=3.0)
