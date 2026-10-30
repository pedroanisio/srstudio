"""Regressions for nested episode state, RF64 input, and character records."""

import struct

import pytest

from srstudio import Episode, EpisodeSpec, locations, parts, releases
from srstudio.parts import PartError
from srstudio.social import InstagramPost
from srstudio.soundtrack import SoundtrackError, validate_wav

POST = InstagramPost(title="A title", description="A description.")


def ep_for(project):
    return Episode(EpisodeSpec(slug='agent', title='agent', description='test', root=project, seed=1, signature=False))


def test_failed_setup_restores_nested_caption_and_cover_state(project):
    ep = ep_for(project)
    existing = ep.cv.group(ep.comp, 'existing')
    ep.captions([(0, 0.2, 'before', 'before')])
    original_specs = ep.caption_specs
    original_hidden = ep._cover_hidden
    before = ep.scene.to_bytes()

    def bad(_):
        ep.captions([(0.3, 0.6, 'hello', 'hello')])
        ep.hide_on_cover(existing)
        raise ValueError('bad callback')

    with pytest.raises(ValueError, match='bad callback'):
        ep.setup(locations.office_wide, [(0, 1)], at_desk=bad)
    assert ep.scene.to_bytes() == before
    assert ep.caption_specs is original_specs and ep.caption_specs == [(0, 0.2, 'before', 'before')]
    assert ep._cover_hidden is original_hidden and ep._cover_hidden == []
    ep.captions([(0.3, 0.6, 'hello', 'hello')])
    ep.markers()
    assert ep.check() == []


def rf64_bytes():
    fmt = struct.pack('<HHIIHH', 1, 1, 48000, 96000, 2, 16)
    data = b'\0' * 20
    body = (
        b'WAVE'
        + b'ds64'
        + struct.pack('<I', 28)
        + b'\0' * 28
        + b'fmt '
        + struct.pack('<I', 16)
        + fmt
        + b'data'
        + struct.pack('<I', 0xFFFFFFFF)
        + data
    )
    total = b'RF64' + struct.pack('<I', 0xFFFFFFFF) + body
    ds64 = struct.pack('<QQQI', len(total) - 8, len(data), len(data) // 2, 0)
    return total[:20] + ds64 + total[48:]


def test_valid_rf64_audio_is_accepted(tmp_path):
    path = tmp_path / 'audio.wav'
    path.write_bytes(rf64_bytes())
    validate_wav(path)


@pytest.mark.parametrize('damage', ['truncated', 'missing_ds64', 'oversized_data', 'bad_table'])
def test_invalid_rf64_audio_is_refused(tmp_path, damage):
    data = bytearray(rf64_bytes())
    if damage == 'truncated':
        del data[-1:]
    elif damage == 'missing_ds64':
        data[12:16] = b'junk'
    elif damage == 'oversized_data':
        data[28:36] = struct.pack('<Q', 100000)
    else:
        data[44:48] = struct.pack('<I', 1)
    path = tmp_path / 'broken.wav'
    path.write_bytes(data)
    with pytest.raises(SoundtrackError, match='broken.wav'):
        validate_wav(path)


def test_missing_record_remains_legacy_but_directory_blocks_release(tmp_path):
    project = tmp_path / 'a-b'
    project.mkdir()
    assert parts.read_record(project) is None
    (project / 'parts.json').mkdir()
    with pytest.raises(PartError, match='parts.json'):
        parts.read_record(project)
    drift = releases.unpinned({'a-b': releases.Release('a-b', POST, characters={})}, tmp_path)
    assert len(drift) == 1 and 'parts.json' in drift[0].reason


def test_dangling_record_symlink_is_not_a_legacy_project(tmp_path):
    (tmp_path / 'parts.json').symlink_to(tmp_path / 'missing.json')
    with pytest.raises(PartError, match='parts.json'):
        parts.read_record(tmp_path)


def test_episode_accepts_rf64_take(project, tmp_path):
    import shutil

    from srstudio import Timeline

    root = tmp_path / 'project'
    shutil.copytree(project, root)
    (root / 'speech.wav').write_bytes(rf64_bytes())
    ep = ep_for(root)
    timeline = Timeline.from_dict(
        {
            'duration': 1,
            'items': [
                {
                    'id': '01',
                    'actor': 'speaker',
                    'shot': 'wide',
                    'text': 'hello',
                    'start': 0,
                    'duration': 1,
                    'audio': 'speech.wav',
                }
            ],
        }
    )
    ep.take_audio(timeline.takes[0])
    assert ep.check() == []


def test_nested_setup_success_keeps_caption_changes(project):
    ep = ep_for(project)
    ep.setup(locations.office_wide, [(0, 1)], at_desk=lambda _: ep.captions([(0, 1, 'hello', 'hello')]))
    assert ep.caption_specs == [(0, 1, 'hello', 'hello')]
    ep.markers()
    assert ep.check() == []
