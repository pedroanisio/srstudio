"""Direct API retries, document rollback, audio inputs and Unicode timing."""

import hashlib
import json

import pytest
from sr_core.scene import SchemaValueError

from srstudio import Episode, EpisodeSpec, Timeline, locations, native
from srstudio.generated import Generated, PlacedClip, Placement
from srstudio.soundtrack import SoundtrackError
from support.generated import write_wav


def episode(project):
    return Episode(EpisodeSpec(slug='retry', title='retry', description='test', root=project, seed=1, signature=False))


def test_setup_restores_removed_and_moved_existing_nodes(project):
    ep = episode(project)
    one = ep.cv.group(ep.comp, 'one')
    two = ep.cv.group(ep.comp, 'two')
    child = ep.cv.group(one, 'child')
    before = ep.scene.to_bytes()

    def bad(_group):
        ep.comp.remove(one)
        one.remove(child)
        two.nodes.append(child)
        two.id = 'changed'
        raise ValueError('bad callback')

    with pytest.raises(ValueError, match='bad callback'):
        ep.setup(locations.office_wide, [(0, 1)], at_desk=bad)
    assert ep.scene.to_bytes() == before
    assert one._owner is ep.comp and child._owner is one and two.id == 'two'
    ep.setup(locations.office_wide, [(0, 1)])
    assert ep.check() == []


def test_direct_take_audio_rolls_back_invalid_track(project):
    ep = episode(project)
    take = Timeline.from_dict(
        {
            'duration': 1,
            'items': [
                {
                    'id': 'a',
                    'actor': 'a',
                    'shot': '',
                    'text': 'hi',
                    'start': 0,
                    'duration': 1,
                    'audio': 'assets/dialogue.wav',
                }
            ],
        }
    ).takes[0]
    before = ep.scene.to_bytes()
    with pytest.raises(SchemaValueError):
        ep.take_audio(take, pan='invalid')
    assert ep.scene.to_bytes() == before
    assert ep._mix is None
    ep.take_audio(take, pan=0.1)
    assert ep.check() == []


def test_direct_generated_audio_failure_can_retry(project, tmp_path):
    import shutil

    root = tmp_path / 'ep'
    shutil.copytree(project, root)
    path = write_wav(root / 'audio' / 'speech.wav', [0.1] * 480)
    gen = Generated(id='speech', kind='speech', provider='p', model='m', prompt='hello', cache='audio/speech.wav')
    clip = PlacedClip(gen, hashlib.sha256(path.read_bytes()).hexdigest(), Placement(start=0))
    ep = episode(root)
    before = ep.scene.to_bytes()
    with pytest.raises(OSError):
        ep.generated_audio([clip], extra=[('bad', 'missing.wav', {})])
    assert ep.scene.to_bytes() == before and ep._mix is None
    ep.generated_audio([clip])
    assert ep.check() == []


def test_episode_native_caption_failure_can_retry(project):
    ep = episode(project)
    before = ep.scene.to_bytes()
    with pytest.raises(SchemaValueError):
        ep.native_captions(look=native.CaptionLook(weight='bogus'))
    assert ep.scene.to_bytes() == before
    ep.native_captions()
    assert ep.check() == []


def test_native_caption_track_direct_failure_rolls_back(project):
    ep = episode(project)
    before = ep.scene.to_bytes()
    with pytest.raises(SchemaValueError):
        native.caption_track(
            ep.scene,
            [native.Cue(0, 1, 'hello')],
            font_asset=ep.cv.font_asset,
            safe_area=None,
            width=1080,
            height=1920,
            look=native.CaptionLook(weight='bogus'),
            output=ep.output,
            canvas=ep.cv,
        )
    assert ep.scene.to_bytes() == before


def test_corrupt_wav_rejected_before_adding_take(project, tmp_path):
    import shutil

    root = tmp_path / 'ep'
    shutil.copytree(project, root)
    (root / 'bad.wav').write_bytes(b'not a wav')
    ep = episode(root)
    take = Timeline.from_dict(
        {
            'duration': 1,
            'items': [
                {'id': 'a', 'actor': 'a', 'shot': '', 'text': 'hi', 'start': 0, 'duration': 1, 'audio': 'bad.wav'}
            ],
        }
    ).takes[0]
    before = ep.scene.to_bytes()
    with pytest.raises(SoundtrackError, match='bad.wav'):
        ep.take_audio(take)
    assert ep.scene.to_bytes() == before


def test_word_time_handles_unicode_lowercase_expansion(tmp_path):
    (tmp_path / 'align.json').write_text(
        json.dumps({'alignment': {'characters': ['İ', ' ', 'x'], 'character_start_times_seconds': [0, 0.1, 0.2]}})
    )
    t = Timeline.from_dict(
        {'duration': 1, 'phrases': [{'role': 'a', 'text': 'İ x', 'start': 0, 'end': 1, 'timing_file': 'align.json'}]},
        root=tmp_path,
    )
    assert t.word_time(0, 'x') == pytest.approx(0.2)


@pytest.mark.parametrize('format_code,bits', [(1, 16), (1, 24), (1, 32), (3, 32)])
def test_take_audio_accepts_common_wav_formats(project, tmp_path, format_code, bits):
    import shutil
    import struct

    root = tmp_path / 'ep'
    shutil.copytree(project, root)
    align = bits // 8
    fmt = struct.pack('<HHIIHH', format_code, 1, 48000, 48000 * align, align, bits)
    data = b'\0' * (align * 10)
    payload = b'WAVE' + b'fmt ' + struct.pack('<I', len(fmt)) + fmt + b'data' + struct.pack('<I', len(data)) + data
    (root / 'valid.wav').write_bytes(b'RIFF' + struct.pack('<I', len(payload)) + payload)
    ep = episode(root)
    take = Timeline.from_dict(
        {
            'duration': 1,
            'items': [
                {'id': 'a', 'actor': 'a', 'shot': '', 'text': 'hi', 'start': 0, 'duration': 1, 'audio': 'valid.wav'}
            ],
        }
    ).takes[0]
    ep.take_audio(take)
    assert ep.check() == []


def test_truncated_wav_data_is_rejected(project, tmp_path):
    import shutil

    root = tmp_path / 'ep'
    shutil.copytree(project, root)
    path = write_wav(root / 'truncated.wav', [0.1] * 100)
    path.write_bytes(path.read_bytes()[:-1])
    ep = episode(root)
    take = Timeline.from_dict(
        {
            'duration': 1,
            'items': [
                {'id': 'a', 'actor': 'a', 'shot': '', 'text': 'hi', 'start': 0, 'duration': 1, 'audio': 'truncated.wav'}
            ],
        }
    ).takes[0]
    with pytest.raises(SoundtrackError, match='truncated.wav'):
        ep.take_audio(take)
