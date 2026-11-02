"""The demonstration keeps real performance clocks and exactly thirty seconds."""

import importlib
from pathlib import Path

import pytest


def show(monkeypatch):
    monkeypatch.syspath_prepend(str(Path(__file__).parents[1]))
    return importlib.import_module('examples.sdk_showreel')


def test_chapters_cover_thirty_seconds_without_repeating_a_clip(monkeypatch):
    reel = show(monkeypatch)
    assert len(reel.CHAPTERS) == 5
    assert len({chapter[0] for chapter in reel.CHAPTERS}) == 5
    assert reel.FPS * reel.SECONDS * len(reel.CHAPTERS) == 720


def test_face_cut_preserves_the_authored_blend(monkeypatch):
    plan = show(monkeypatch).face_plan()
    assert plan.duration == 6
    assert plan.window(4, 6).sample(0) == plan.sample(4)
    assert 0 < plan.sample(4).face_blend.weight < 1


def test_demonstration_builds_valid_portable_scenes(monkeypatch, tmp_path):
    from sr_core.scene import read

    reel = show(monkeypatch)
    for name in ('face', 'gestures', 'body', 'contact'):
        path, report = reel.build_chapter(tmp_path / name, name)
        assert not read(path).check(schema=True)
        assert report['duration'] == 6 and report['fps'] == 24
        assert report['drawing_approval'] is None
    with pytest.raises(FileExistsError):
        reel.build_chapter(tmp_path / 'face', 'face')


def test_hybrid_import_scopes_paints_and_preserves_schema_order(monkeypatch, tmp_path):
    from sr_core.scene import Scene, read

    from srstudio import Canvas

    source = Scene(version='auto')
    source.add_project(width=1080, height=1920, fps='24', duration=6)
    cv = Canvas(source, font_asset=None)
    paint = cv.grad('fill', [(0, '#ffffff'), (1, '#123456')])
    cv.rect(cv.group(cv.comp, 'world'), 0, 0, 100, 100, paint)
    path = tmp_path / 'source.xml'
    path.write_bytes(source.to_bytes())
    result, _ = show(monkeypatch).build_chapter(tmp_path / 'hybrid', 'hybrid', hybrid=path)
    assert not read(result).check(schema=True)
    assert b'hybrid__world' in result.read_bytes()
    assert b'url(#hybrid__fill)' in result.read_bytes()


@pytest.mark.parametrize('name', ['unknown', 'hybrid'])
def test_missing_input_is_refused_before_creating_files(monkeypatch, tmp_path, name):
    with pytest.raises(ValueError):
        show(monkeypatch).build_chapter(tmp_path / 'missing', name)
    assert list(tmp_path.iterdir()) == []


@pytest.mark.parametrize('variant', ['portable', 'outside', 'duration', 'missing-world'])
def test_hybrid_assets_are_portable_and_invalid_inputs_are_refused(monkeypatch, tmp_path, variant):
    import xml.etree.ElementTree as ET

    import numpy as np
    from sr_core.scene import read

    from srstudio import plates

    source = tmp_path / 'source'
    source.mkdir()
    plates.write_png(source / 'image.png', np.full((2, 2, 4), 255, dtype=np.uint8))
    root = ET.fromstring(
        '<scene version="1.1"><project width="1080" height="1920" fps="24" duration="6"/>'
        '<assets><image id="image" src="image.png" width="2" height="2"/></assets>'
        '<composition><group id="world"><layer id="picture" asset="image"/></group></composition></scene>'
    )
    if variant == 'outside':
        root.find('assets/image').set('src', '../outside.png')
    elif variant == 'duration':
        root.find('project').set('duration', '5')
    elif variant == 'missing-world':
        root.find('composition/group').set('id', 'unrelated')
    path = source / 'scene.xml'
    path.write_bytes(ET.tostring(root))
    if variant != 'portable':
        with pytest.raises(ValueError):
            show(monkeypatch).build_chapter(tmp_path / 'result', 'hybrid', hybrid=path)
    else:
        result, _ = show(monkeypatch).build_chapter(tmp_path / 'result', 'hybrid', hybrid=path)
        assert not read(result).check(schema=True)
        image = ET.parse(result).find('assets/image')
        assert (result.parent / image.get('src')).read_bytes() == (source / 'image.png').read_bytes()
