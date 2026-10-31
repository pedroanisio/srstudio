"""IMA ADPCM take WAVs supported by the renderer are usable in episodes."""

import shutil
import struct
import subprocess

import pytest

from srstudio import Episode, EpisodeSpec, Timeline
from srstudio.soundtrack import SoundtrackError, validate_wav


def ima_wav(fmt):
    data = bytes(8)  # one mono block: predictor, index, reserved byte and four ADPCM bytes
    body = b'WAVEfmt ' + struct.pack('<I', len(fmt)) + fmt + b'data' + struct.pack('<I', len(data)) + data
    return b'RIFF' + struct.pack('<I', len(body)) + body


def test_ima_adpcm_take_builds_and_is_decodable(project, tmp_path):
    root = tmp_path / 'project'
    shutil.copytree(project, root)
    fmt = struct.pack('<HHIIHHHH', 0x11, 1, 8000, 7111, 8, 4, 2, 9)
    path = root / 'take.wav'
    path.write_bytes(ima_wav(fmt))
    ffmpeg = shutil.which('ffmpeg')
    if ffmpeg:
        result = subprocess.run([ffmpeg, '-v', 'error', '-i', str(path), '-f', 'null', '-'], capture_output=True)
        assert result.returncode == 0, result.stderr.decode()
    ep = Episode(EpisodeSpec(slug='ima', title='ima', description='test', root=root, seed=1, signature=False))
    take = Timeline.from_dict(
        {
            'duration': 1,
            'items': [
                {'id': 'a', 'actor': 'a', 'shot': '', 'text': 'hi', 'start': 0, 'duration': 1, 'audio': 'take.wav'}
            ],
        }
    ).takes[0]
    ep.take_audio(take)
    assert ep.check() == []


@pytest.mark.parametrize('extension', [b'', b'\x02\x00', b'\x00\x00\x09\x00', b'\x02\x00\x00\x00'])
def test_incomplete_ima_adpcm_format_is_rejected(tmp_path, extension):
    fmt = struct.pack('<HHIIHH', 0x11, 1, 8000, 7111, 8, 4) + extension
    path = tmp_path / 'bad.wav'
    path.write_bytes(ima_wav(fmt))
    with pytest.raises(SoundtrackError, match='IMA ADPCM'):
        validate_wav(path)
