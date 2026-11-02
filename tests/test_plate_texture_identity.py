"""Plate drawing and render identities bind texture dimensions and the pixels actually staged."""

import hashlib
import struct
import xml.etree.ElementTree as ET
from dataclasses import replace

import numpy as np
import pytest

from srstudio import plates
from support.plates import plate


def picture():
    return np.array([[[255, 0, 0, 255], [0, 255, 0, 255]], [[0, 0, 255, 255], [255, 255, 0, 255]]], np.uint8)


def textured(pixels, **kwargs):
    return replace(plate(), materials=(plates.Material('clay', '#FFFFFF', color_map=plates.Texture(pixels), **kwargs),))


@pytest.fixture
def rendering(tmp_path, monkeypatch):
    engine = tmp_path / 'engine'
    engine.write_bytes(b'texture-test-engine')
    calls = []

    def render(engine, source, out):
        document = source.read_bytes()
        maps = {}
        for node in ET.fromstring(document).findall('materials/material'):
            for field in ('baseColorMap', 'normalMap'):
                if path := node.get(field):
                    maps[path] = (source.parent / path).read_bytes()
        calls.append((document, maps))
        payload = document + b''.join(maps.values())
        colour = np.array([*hashlib.sha256(payload).digest()[:3], 255], np.uint8).reshape(1, 1, 4)
        plates.write_png(out, colour)

    monkeypatch.setattr(plates, '_engine_render', render)
    return engine, tmp_path / 'cache', calls


def test_texture_dimensions_distinguish_logical_drawings_and_canvas_assets():
    from sr_core.scene import Scene

    from srstudio import Canvas

    square, strip = picture(), picture().reshape(1, 4, 4)
    assert square.tobytes() == strip.tobytes()
    assert plates.Texture(square).sha256 != plates.Texture(strip).sha256
    a, b = textured(square), textured(strip)
    assert plates.digest(a) != plates.digest(b)
    cv = Canvas(Scene(version='auto'), font_asset=None)
    plates.place(cv, cv.comp, a)
    plates.place(cv, cv.comp, b)
    assert len(cv.assets.nodes) == 2


def test_texture_identity_follows_mutation_and_ignores_array_memory_layout():
    array = picture()
    texture = plates.Texture(array)
    first = texture.sha256
    assert plates.Texture(np.asfortranarray(array)).sha256 == first
    assert plates.Texture(array[:, ::-1].copy()[:, ::-1]).sha256 == first
    array[0, 0, 0] = 1
    assert texture.sha256 != first
    array[0, 0, 0] = 255
    assert texture.sha256 == first


def test_shared_maps_are_hashed_once_per_document_but_rechecked_on_the_next_call(monkeypatch):
    texture = plates.Texture(picture())
    made = textured(texture.pixels, normal_map=texture)
    made = replace(made, materials=(replace(made.materials[0], color_map=texture),))
    original = plates.Texture.sha256.fget
    calls = []

    def fingerprint(item):
        calls.append(item)
        return original(item)

    monkeypatch.setattr(plates.Texture, 'sha256', property(fingerprint))
    first = plates.document(made)
    assert len(calls) == 1
    texture.pixels[0, 0, 0] = 1
    assert plates.document(made) != first and len(calls) == 2


def test_one_plate_retains_distinct_color_and_normal_map_shapes(rendering, tmp_path):
    engine, cache, calls = rendering
    made = textured(picture(), normal_map=plates.Texture(picture().reshape(1, 4, 4)))
    plates.render(made, engine=engine, cache=cache, fonts=tmp_path)
    resources = calls[0][1]
    assert len(resources) == 2
    assert {struct.unpack('>II', data[16:24]) for data in resources.values()} == {(2, 2), (4, 1)}


def test_reshape_and_pixel_edits_invalidate_cache_without_losing_previous_outputs(rendering, tmp_path):
    engine, cache, calls = rendering
    array = picture()
    made = textured(array)
    first = plates.render(made, engine=engine, cache=cache, fonts=tmp_path)
    original = first.read_bytes()
    strip = plates.render(textured(array.reshape(1, 4, 4)), engine=engine, cache=cache, fonts=tmp_path)
    assert strip != first and len(calls) == 2
    array[0, 0, 0] = 1
    edited = plates.render(made, engine=engine, cache=cache, fonts=tmp_path)
    assert edited not in (first, strip) and len(calls) == 3
    array[0, 0, 0] = 255
    assert plates.render(made, engine=engine, cache=cache, fonts=tmp_path) == first
    assert first.read_bytes() == original and len(calls) == 3


def test_resource_pixels_are_snapshotted_before_any_cache_or_render_work(rendering, tmp_path, monkeypatch):
    engine, cache, calls = rendering
    array = picture()
    expected = plates._png_bytes(array)
    original = plates._lay_out

    def changed(*args, **kwargs):
        array[:] = 0
        return original(*args, **kwargs)

    monkeypatch.setattr(plates, '_lay_out', changed)
    plates.render(textured(array), engine=engine, cache=cache, fonts=tmp_path)
    assert list(calls[0][1].values()) == [expected]


def test_verify_reuses_one_snapshot_even_when_caller_pixels_change(rendering, tmp_path, monkeypatch):
    engine, cache, calls = rendering
    array = picture()
    original = plates._engine_render

    def changed(*args):
        original(*args)
        array[:] = 0

    monkeypatch.setattr(plates, '_engine_render', changed)
    assert len(plates.verify(textured(array), engine=engine, cache=cache, fonts=tmp_path)) == 64
    assert len(calls) == 2 and calls[0] == calls[1]


@pytest.mark.parametrize(
    'bad',
    [
        None,
        [[1]],
        np.zeros((2, 2, 4)),
        np.zeros((2, 2, 3), np.uint8),
        np.zeros((0, 2, 4), np.uint8),
        np.zeros((2, 2, 4, 1), np.uint8),
    ],
)
def test_invalid_texture_is_a_typed_failure_before_cache_creation(rendering, tmp_path, bad):
    engine, cache, calls = rendering
    with pytest.raises(plates.PlateError) as caught:
        plates.render(textured(bad), engine=engine, cache=cache, fonts=tmp_path)
    diagnostic = caught.value.to_dict()
    assert diagnostic['code'] == 'plate.texture.pixels'
    assert diagnostic['path'] == 'texture.pixels' and diagnostic['remedy']
    assert not calls and not cache.exists()


@pytest.mark.parametrize('authored', [False, True])
def test_ambiguous_legacy_texture_cache_is_not_reused(rendering, tmp_path, authored):
    from srstudio import rafa

    engine, cache, calls = rendering
    pixels = rafa._KNIT_MAP.pixels if authored else picture()
    made = textured(pixels)
    new_name = made.materials[0].color_map.sha256
    old_name = hashlib.sha256(pixels.tobytes()).hexdigest()
    legacy_source = plates.document(made).replace(new_name.encode(), old_name.encode())
    inputs = plates._render_inputs(engine, tmp_path, printed=False)
    legacy = inputs.folder(cache) / f'{inputs.key("plate", legacy_source)}.png'
    legacy.write_bytes(b'previous artifact with ambiguous texture dimensions')
    actual = plates.render(made, engine=engine, cache=cache, fonts=tmp_path)
    assert actual != legacy and len(calls) == 1
    assert legacy.read_bytes() == b'previous artifact with ambiguous texture dimensions'


@pytest.fixture(scope='module')
def authored_textures():
    from srstudio import pedro, rafa, rafa_skin

    return {
        'rafa-knit': rafa._KNIT_MAP,
        'rafa-clay': rafa._CLAY_MAP,
        'rafa-skin': rafa_skin.paint(rafa._SKIN_TONES),
        'pedro-scalp': pedro.scalp_picture(),
        'pedro-goatee': pedro.goatee_picture(),
    }


@pytest.mark.parametrize('name', ['rafa-knit', 'rafa-clay', 'rafa-skin', 'pedro-scalp', 'pedro-goatee'])
def test_existing_authored_textures_keep_names_only_for_exact_pixels_and_shape(authored_textures, name):
    texture = authored_textures[name]
    previous = hashlib.sha256(texture.pixels.tobytes()).hexdigest()
    assert texture.sha256 == previous
    assert plates.Texture(texture.pixels.reshape(1, -1, 4)).sha256 != previous
    edited = texture.pixels.copy()
    edited[0, 0, 0] ^= 1
    assert plates.Texture(edited).sha256 != previous
    assert plates.Texture(texture.pixels.copy()).sha256 == previous


def test_warm_cache_does_not_reencode_unchanged_texture_pixels(rendering, tmp_path, monkeypatch):
    engine, cache, calls = rendering
    made = textured(picture())
    first = plates.render(made, engine=engine, cache=cache, fonts=tmp_path)
    monkeypatch.setattr(plates, '_png_bytes', lambda *args: pytest.fail('warm cache encoded a PNG'))
    assert plates.render(made, engine=engine, cache=cache, fonts=tmp_path) == first
    assert len(calls) == 1


def test_pixel_edits_reuse_an_unchanged_print_dependency(rendering, tmp_path):
    from support.plates import printed_plate

    engine, cache, calls = rendering
    (tmp_path / plates.PRINT_FONT[2]).write_bytes(b'test-font')
    array = picture()
    made = textured(array, print=printed_plate().materials[0].print)
    plates.render(made, engine=engine, cache=cache, fonts=tmp_path)
    assert len(calls) == 2
    array[0, 0, 0] = 1
    plates.render(made, engine=engine, cache=cache, fonts=tmp_path)
    assert len(calls) == 3


def test_real_renderer_draws_reshaped_textures_as_different_images(scene_render, tmp_path, monkeypatch):
    from srstudio import clay

    monkeypatch.setattr(plates, 'SAMPLES', 4)
    mesh = clay.Mesh(
        'clay',
        np.array([[-25.0, -25.0, 0], [25.0, -25.0, 0], [25.0, 25.0, 0], [-25.0, 25.0, 0]]),
        np.tile([0.0, 0.0, -1.0], (4, 1)),
        np.array([[0, 2, 1], [0, 3, 2]]),
        np.array([[0.0, 1.0], [1.0, 1.0], [1.0, 0.0], [0.0, 0.0]]),
    )
    made = replace(
        textured(picture()),
        camera=plates.Camera((0, 0, -100), (0, 0, 0), 40),
        placed=(plates.Placed((mesh,)),),
        lights=(plates.Light('ambient', 'ambient', '#FFFFFF', 1),),
    )
    reshaped = replace(
        made, materials=(replace(made.materials[0], color_map=plates.Texture(picture().reshape(1, 4, 4))),)
    )
    cache = tmp_path / 'cache'
    with plates.render_session(max_invocations=3, timeout=120) as cold:
        first = plates.render(made, engine=scene_render, cache=cache, fonts=tmp_path)
        second = plates.render(reshaped, engine=scene_render, cache=cache, fonts=tmp_path)
        # Reproduce the previous square-texture document and resource names to
        # prove that the identity correction preserves an unambiguous drawing.
        inputs, source, prints = plates._prepare(made, scene_render, tmp_path)
        legacy = tmp_path / 'legacy'
        legacy.mkdir()
        plates._lay_out(made, legacy, inputs, inputs.folder(cache), prints)
        new_name = made.materials[0].color_map.sha256
        old_name = hashlib.sha256(picture().tobytes()).hexdigest()
        (legacy / 'textures' / f'{new_name}.png').rename(legacy / 'textures' / f'{old_name}.png')
        document = legacy / 'legacy.scene.xml'
        document.write_bytes(source.replace(new_name.encode(), old_name.encode()))
        plates._engine_render(scene_render, document, legacy / 'legacy.png')
    assert cold.completed == 3 and first != second
    a, b = plates.pixels(first), plates.pixels(second)
    assert np.array_equal(a, plates.pixels(legacy / 'legacy.png'))
    assert a.shape == b.shape == (64, 64, 4)
    assert a[32, 32, 3] == b[32, 32, 3] == 255
    assert np.count_nonzero(np.any(a != b, axis=-1)) > 200
    with plates.render_session(max_invocations=0) as warm:
        assert plates.render(made, engine=scene_render, cache=cache, fonts=tmp_path) == first
        assert plates.render(reshaped, engine=scene_render, cache=cache, fonts=tmp_path) == second
    assert warm.invocations == 0
