"""Input URIs, style diagnostics, and sequence checks for agent workflows."""

import shutil
import xml.etree.ElementTree as ET

import pytest

from srstudio import Episode, EpisodeSpec, SrstudioError
from srstudio import episode as episode_module
from srstudio.episode import EpisodeArgumentError


@pytest.mark.parametrize('filename', ['art#1.png', 'art?1.png', '#cover.png'])
@pytest.mark.parametrize('output', ['out', 'report'])
@pytest.mark.parametrize('alias', ['direct', 'symlink', 'hardlink'])
def test_literal_uri_punctuation_does_not_bypass_input_protection(project, tmp_path, filename, output, alias):
    root = tmp_path / 'project'
    shutil.copytree(project, root)
    image = root / 'assets' / filename
    image.write_bytes(b'asset contents')
    ep = Episode(EpisodeSpec(slug='x', title='x', description='x', root=root, seed=1, signature=False))
    ep.cv.assets.add_image(id='image', src='assets/' + filename, width=1, height=1)
    target = image
    if alias != 'direct':
        target = tmp_path / 'alias'
        (target.symlink_to if alias == 'symlink' else target.hardlink_to)(image)
    with pytest.raises(EpisodeArgumentError, match='input'):
        ep.finish(**{output: target})
    assert image.read_bytes() == b'asset contents'


def test_export_rebases_asset_src_starting_with_hash(project, tmp_path):
    root = tmp_path / 'project'
    shutil.copytree(project, root)
    (root / '#cover.png').write_bytes(b'cover')
    ep = Episode(EpisodeSpec(slug='x', title='x', description='x', root=root, seed=1, signature=False))
    ep.cv.assets.add_image(id='image', src='#cover.png', width=1, height=1)
    out = tmp_path / 'export' / 'scene.xml'
    ep.finish(out=out)
    source = ET.parse(out).getroot().find('.//image').get('src')
    assert (out.parent / source).resolve() == (root / '#cover.png').resolve()


@pytest.mark.parametrize('reference', ['leading_hash', 'file_uri'])
def test_hash_filename_is_protected_in_root_and_file_uri(project, tmp_path, reference):
    root = tmp_path / 'project'
    shutil.copytree(project, root)
    image = root / '#cover.png'
    image.write_bytes(b'asset contents')
    source = '#cover.png' if reference == 'leading_hash' else 'file://' + str(image)
    ep = Episode(EpisodeSpec(slug='x', title='x', description='x', root=root, seed=1, signature=False))
    ep.cv.assets.add_image(id='image', src=source, width=1, height=1)
    with pytest.raises(EpisodeArgumentError, match='input'):
        ep.finish(report=image)
    assert image.read_bytes() == b'asset contents'


def test_material_hash_reference_is_not_mistaken_for_an_input_file(project, tmp_path):
    root = tmp_path / 'project'
    shutil.copytree(project, root)
    (root / 'assets' / 'tex.png').write_bytes(b'texture')
    ep = Episode(EpisodeSpec(slug='x', title='x', description='x', root=root, seed=1, signature=False))
    ep.cv.assets.add_image(id='tex', src='assets/tex.png', width=1, height=1)
    ep.scene.add_materials().add_material(id='mat', baseColorMap='#tex')
    out = tmp_path / 'export' / 'scene.xml'
    ep.finish(out=out, report=root / '#tex')
    assert ET.parse(out).getroot().find('.//material').get('baseColorMap') == '#tex'


def test_sequence_alias_scan_is_shared_across_output_paths(project, tmp_path, monkeypatch):
    root = tmp_path / 'project'
    shutil.copytree(project, root)
    for index in range(200):
        (root / 'assets' / f'frame_{index:04d}.png').touch()
    ep = Episode(EpisodeSpec(slug='x', title='x', description='x', root=root, seed=1, signature=False))
    ep.cv.assets.add_imageSequence(
        id='frames', src='assets/frame_%04d.png', first=0, last=199, fps='24', width=1, height=1
    )
    original = episode_module.glob.iglob
    scans = []

    def counting(pattern, *args, **kwargs):
        scans.append(pattern)
        return original(pattern, *args, **kwargs)

    monkeypatch.setattr(episode_module.glob, 'iglob', counting)
    ep.finish(out=tmp_path / 'scene.xml', report=tmp_path / 'report.json')
    assert len(scans) == 1


@pytest.mark.parametrize('value', ['toon', 'unknown-style', None, 123])
def test_invalid_style_has_actionable_srstudio_error(tmp_path, value):
    with pytest.raises(SrstudioError, match='style') as caught:
        EpisodeSpec(slug='x', title='x', description='x', root=tmp_path, seed=1, style=value)
    assert 'Style' in str(caught.value) and 'STYLES' in str(caught.value)
