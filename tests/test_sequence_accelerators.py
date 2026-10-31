"""Sequence assets stay usable and representative catalog accelerators run."""

import shutil
import xml.etree.ElementTree as ET

import pytest

from srstudio import Episode, EpisodeSpec, registry
from srstudio.episode import EpisodeArgumentError


def make_episode(project, tmp_path):
    root = tmp_path / 'project space'
    shutil.copytree(project, root)
    return root, Episode(EpisodeSpec(slug='x', title='x', description='x', root=root, seed=1, signature=False))


@pytest.mark.parametrize('output', ['out', 'report'])
@pytest.mark.parametrize('alias', ['direct', 'symlink', 'hardlink'])
def test_volume_source_cannot_be_replaced(project, tmp_path, output, alias):
    root, ep = make_episode(project, tmp_path)
    volume = root / 'assets' / 'cloud.srvol'
    volume.write_bytes(b'volume input')
    ep.cv.assets.add_volume(id='cloud', src='assets/cloud.srvol', format='srvol')
    target = volume
    if alias != 'direct':
        target = tmp_path / 'alias'
        (target.symlink_to if alias == 'symlink' else target.hardlink_to)(volume)
    with pytest.raises(EpisodeArgumentError, match='input'):
        ep.finish(**{output: target})
    assert volume.read_bytes() == b'volume input'


@pytest.mark.parametrize('pattern', ['frame_%04d.png', 'frame_####.png'])
@pytest.mark.parametrize('alias', ['direct', 'symlink', 'hardlink'])
def test_image_sequence_frame_cannot_be_replaced(project, tmp_path, pattern, alias):
    root, ep = make_episode(project, tmp_path)
    frame = root / 'assets' / 'frame_0001.png'
    frame.write_bytes(b'frame input')
    ep.cv.assets.add_imageSequence(id='frames', src=f'assets/{pattern}', first=1, last=3, fps='24', width=10, height=10)
    target = frame
    if alias != 'direct':
        target = tmp_path / 'alias'
        (target.symlink_to if alias == 'symlink' else target.hardlink_to)(frame)
    with pytest.raises(EpisodeArgumentError, match='input'):
        ep.finish(report=target)
    assert frame.read_bytes() == b'frame input'


@pytest.mark.parametrize('target_kind', ['frame_link', 'link_target', 'target_symlink', 'target_hardlink'])
def test_image_sequence_frame_symlink_targets_are_protected(project, tmp_path, target_kind):
    root, ep = make_episode(project, tmp_path)
    original = tmp_path / 'shared.png'
    original.write_bytes(b'shared input')
    frame = root / 'assets' / 'frame_0001.png'
    frame.symlink_to(original)
    ep.cv.assets.add_imageSequence(
        id='frames', src='assets/frame_%04d.png', first=1, last=1, fps='24', width=10, height=10
    )
    output = {'frame_link': frame, 'link_target': original}.get(target_kind)
    if output is None:
        output = tmp_path / 'alias'
        (output.symlink_to if target_kind == 'target_symlink' else output.hardlink_to)(original)
    with pytest.raises(EpisodeArgumentError, match='input'):
        ep.finish(report=output)
    assert original.read_bytes() == b'shared input'


def test_sequence_frame_inside_numbered_symlink_directory_is_protected(project, tmp_path):
    root, ep = make_episode(project, tmp_path)
    shared = tmp_path / 'shared'
    shared.mkdir()
    original = shared / 'frame.png'
    original.write_bytes(b'shared input')
    (root / 'assets' / 'seq_01').symlink_to(shared, target_is_directory=True)
    ep.cv.assets.add_imageSequence(
        id='frames', src='assets/seq_%02d/frame.png', first=1, last=1, fps='24', width=10, height=10
    )
    with pytest.raises(EpisodeArgumentError, match='input'):
        ep.finish(report=original)
    assert original.read_bytes() == b'shared input'


@pytest.mark.parametrize('protect', [False, True])
def test_sequence_parent_component_after_placeholder(project, tmp_path, protect):
    root, ep = make_episode(project, tmp_path)
    (root / 'assets' / '0001').mkdir()
    frame = root / 'assets' / 'frame.png'
    frame.write_bytes(b'frame input')
    ep.cv.assets.add_imageSequence(
        id='frames', src='assets/%04d/../frame.png', first=1, last=1, fps='24', width=10, height=10
    )
    if protect:
        with pytest.raises(EpisodeArgumentError, match='input'):
            ep.finish(report=frame)
        assert frame.read_bytes() == b'frame input'
    else:
        ep.finish()
        assert frame.read_bytes() == b'frame input'


@pytest.mark.parametrize('kind', ['image', 'mesh', 'volume'])
def test_numbered_asset_respects_negative_frames_and_step(project, tmp_path, kind):
    root, ep = make_episode(project, tmp_path)
    source = 'assets/frame_%04d.dat'
    if kind == 'image':
        ep.cv.assets.add_imageSequence(id='seq', src=source, first=-5, last=5, step=2, fps='24', width=1, height=1)
    elif kind == 'mesh':
        ep.cv.assets.add_meshSequence(id='seq', src=source, first=-5, last=5, fps='24', format='obj')
    else:
        ep.cv.assets.add_volume(id='seq', src=source, first=-5, last=5, fps='24', format='openvdb')
    frame = root / 'assets' / 'frame_-003.dat'
    frame.write_bytes(b'frame')
    with pytest.raises(EpisodeArgumentError, match='input'):
        ep.finish(report=frame)
    assert frame.read_bytes() == b'frame'


def test_sequence_guard_does_not_expand_large_frame_range(project, tmp_path):
    root, ep = make_episode(project, tmp_path)
    ep.cv.assets.add_imageSequence(
        id='seq', src='assets/frame_%04d.png', first=0, last=2_000_000_000, fps='24', width=1, height=1
    )
    frame = root / 'assets' / 'frame_1999999999.png'
    frame.write_bytes(b'frame')
    with pytest.raises(EpisodeArgumentError, match='input'):
        ep.finish(report=frame)
    assert frame.read_bytes() == b'frame'


def test_sequence_guard_does_not_claim_frames_outside_the_step(project, tmp_path):
    root, ep = make_episode(project, tmp_path)
    ep.cv.assets.add_imageSequence(
        id='seq', src='assets/frame_%04d.png', first=1, last=3, step=2, fps='24', width=1, height=1
    )
    unrelated = root / 'assets' / 'frame_0002.png'
    unrelated.write_bytes(b'other file')
    ep.finish(report=unrelated)
    assert unrelated.read_text().strip() == '[]'


@pytest.mark.parametrize('root_name', ['project#space', 'project%space'])
def test_unrepresentable_rebased_sequence_path_fails_before_writing(project, tmp_path, root_name):
    root = tmp_path / root_name
    shutil.copytree(project, root)
    ep = Episode(EpisodeSpec(slug='x', title='x', description='x', root=root, seed=1, signature=False))
    ep.cv.assets.add_imageSequence(id='seq', src='assets/frame_%04d.png', first=1, last=1, fps='24', width=1, height=1)
    out = tmp_path / 'export' / 'scene.xml'
    with pytest.raises(EpisodeArgumentError, match="'%' or '#'"):
        ep.finish(out=out)
    assert not out.exists()


def test_rebased_volume_and_sequence_sources_resolve_from_export(project, tmp_path):
    root, ep = make_episode(project, tmp_path)
    ep.cv.assets.add_volume(id='cloud', src='assets/cloud.srvol', format='srvol')
    ep.cv.assets.add_volume(
        id='volume-frames', src='assets/cloud_%04d.vdb', format='openvdb', first=1, last=2, fps='24'
    )
    ep.cv.assets.add_imageSequence(
        id='frames', src='assets/frame_####.png', first=1, last=2, fps='24', width=10, height=10
    )
    ep.cv.assets.add_meshSequence(id='meshes', src='assets/mesh_%04d.obj', first=1, last=2, fps='24', format='obj')
    out = tmp_path / 'export' / 'scene.xml'
    ep.finish(out=out)
    doc = ET.parse(out).getroot()
    assert doc.find('.//volume[@id="cloud"]').get('src') == '../project%20space/assets/cloud.srvol'
    assert doc.find('.//volume[@id="volume-frames"]').get('src') == '../project space/assets/cloud_%04d.vdb'
    assert doc.find('.//imageSequence').get('src') == '../project space/assets/frame_####.png'
    assert doc.find('.//meshSequence').get('src') == '../project space/assets/mesh_%04d.obj'


@pytest.mark.parametrize('name', ['coffee-cup', 'office-mug', 'stick-mug', 'toon-mug', 'soft-coffee-machine'])
def test_representative_prop_has_runnable_inspection_example(project, name):
    examples = registry.describe('prop', name)['examples']
    assert examples
    ep = Episode(EpisodeSpec(slug='x', title='x', description='x', root=project, seed=1, signature=False))
    for example in examples:
        exec(compile(example, '<catalog example>', 'exec'), {'ep': ep})
    assert ep.check() == []
