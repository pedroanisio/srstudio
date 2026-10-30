"""Regression tests for safe onboarding and honest verification."""

import shutil
import struct
import subprocess
import sys
from dataclasses import replace
from pathlib import Path

import pytest

from srstudio import Episode, Timeline, characters, registry, sample, specimens
from srstudio.soundtrack import SoundtrackError, validate_wav
from support.audio import spec


@pytest.mark.parametrize('relative', ['dialogue.json', 'assets/dialogue.wav', 'assets/FONT-LICENSE.txt'])
def test_sample_does_not_clobber_a_concurrent_writer(tmp_path, monkeypatch, relative):
    root = tmp_path / 'project'
    target = root / relative
    original = sample.write_wav

    def race(*args, **kwargs):
        original(*args, **kwargs)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text('concurrent writer')

    monkeypatch.setattr(sample, 'write_wav', race)
    with pytest.raises(sample.SampleError, match='overwrite=True'):
        sample.write_sample_project(root, [sample.Line('a', 'hello')])
    assert target.read_text() == 'concurrent writer'
    for other in ('dialogue.json', 'assets/dialogue.wav', 'assets/DejaVuSans-Bold.ttf', 'assets/FONT-LICENSE.txt'):
        if other != relative:
            assert not (root / other).exists()


@pytest.mark.parametrize('name', ['coffee-review.scene.xml', 'sdk-validation.json'])
def test_example_refuses_existing_output_before_creating_inputs(tmp_path, name):
    target = tmp_path / name
    target.write_text('existing output')
    script = Path(__file__).resolve().parents[1] / 'examples' / 'new_episode.py'
    result = subprocess.run([sys.executable, str(script), str(tmp_path)], capture_output=True, text=True, timeout=60)
    assert result.returncode != 0
    assert '--overwrite' in result.stderr
    assert target.read_text() == 'existing output'
    assert not (tmp_path / 'dialogue.json').exists()
    result = subprocess.run(
        [sys.executable, str(script), str(tmp_path), '--overwrite'], capture_output=True, text=True, timeout=60
    )
    assert result.returncode == 0, result.stderr
    assert target.read_text() != 'existing output'


def test_successful_specimen_check_verifies_current_replacement(monkeypatch):
    monkeypatch.setitem(registry._REGISTRY, 'character', dict(registry._REGISTRY['character']))
    original = registry.get('character', 'toon-fox@2').builder
    registry.register('character', 'toon-fox@2', replace=True)(original)
    with pytest.raises(characters.UnverifiedBuilderError):
        characters.pin('toon-fox', 2)
    specimens.check('toon-fox', 2)
    assert characters.pin('toon-fox', 2).number == 2
    assert characters.part('toon-fox', 2).builder is original
    assert registry.describe('character', 'toon-fox@2')['character_version']['status'] == 'approved'
    character = characters.get('toon-fox')
    versions = tuple(replace(v, drawing='0' * 64) if v.number == 2 else v for v in character.versions)
    changed_table = {**characters.load(), 'toon-fox': replace(character, versions=versions)}
    with monkeypatch.context() as context:
        context.setattr(characters, 'load', lambda: changed_table)
        with pytest.raises(characters.UnverifiedBuilderError):
            characters.pin('toon-fox', 2)
    monkeypatch.setattr(registry.get('character', 'toon-fox@2'), 'builder', lambda: None)
    with pytest.raises(characters.UnverifiedBuilderError):
        characters.pin('toon-fox', 2)


def test_failed_specimen_check_does_not_verify(monkeypatch):
    monkeypatch.setitem(registry._REGISTRY, 'character', dict(registry._REGISTRY['character']))
    registry.register('character', 'toon-fox@2', replace=True)(lambda: None)
    monkeypatch.setattr(specimens, 'digest', lambda *args: 'wrong')
    with pytest.raises(specimens.DrawingChangedError):
        specimens.check('toon-fox', 2)
    with pytest.raises(characters.UnverifiedBuilderError):
        characters.pin('toon-fox', 2)


def test_later_failed_specimen_check_revokes_verification(monkeypatch):
    monkeypatch.setitem(registry._REGISTRY, 'character', dict(registry._REGISTRY['character']))
    original = registry.get('character', 'toon-fox@2').builder
    registry.register('character', 'toon-fox@2', replace=True)(original)
    specimens.check('toon-fox', 2)
    monkeypatch.setattr(specimens, 'digest', lambda *args: 'wrong')
    with pytest.raises(specimens.DrawingChangedError):
        specimens.check('toon-fox', 2)
    with pytest.raises(characters.UnverifiedBuilderError):
        characters.pin('toon-fox', 2)


def wav_bytes(code):
    fmt = struct.pack('<HHIIHH', code, 1, 24000, 48000, 2, 16)
    body = b'WAVEfmt ' + struct.pack('<I', len(fmt)) + fmt + b'data' + struct.pack('<I', 2) + b'\0\0'
    return b'RIFF' + struct.pack('<I', len(body)) + body


def test_unsupported_wav_encoding_is_rejected_before_episode_mutation(project, tmp_path):
    root = tmp_path / 'copy'
    shutil.copytree(project, root)
    ep = Episode(spec(root))
    path = root / 'assets' / 'dialogue.wav'
    path.write_bytes(wav_bytes(0xFFFF))
    with pytest.raises(SoundtrackError, match='encoding'):
        validate_wav(path)
    timeline = Timeline.from_dict(
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
    )
    before = ep.scene.to_bytes()
    with pytest.raises(SoundtrackError, match='encoding'):
        ep.take_audio(timeline.takes[0])
    assert ep.scene.to_bytes() == before


@pytest.mark.parametrize('subtype', [1, 3])
def test_extensible_pcm_and_float_are_accepted(tmp_path, subtype):
    guid = struct.pack('<I', subtype) + bytes.fromhex('00001000800000aa00389b71')
    bits = 16 if subtype == 1 else 32
    width = bits // 8
    fmt = struct.pack('<HHIIHHHHI', 0xFFFE, 1, 24000, 24000 * width, width, bits, 22, bits, 0) + guid
    body = b'WAVEfmt ' + struct.pack('<I', len(fmt)) + fmt + b'data' + struct.pack('<I', width) + bytes(width)
    path = tmp_path / 'extensible.wav'
    path.write_bytes(b'RIFF' + struct.pack('<I', len(body)) + body)
    validate_wav(path)


def test_extensible_unknown_subtype_is_rejected(tmp_path):
    guid = struct.pack('<I', 0xFFFF) + bytes.fromhex('00001000800000aa00389b71')
    fmt = struct.pack('<HHIIHHHHI', 0xFFFE, 1, 24000, 48000, 2, 16, 22, 16, 0) + guid
    body = b'WAVEfmt ' + struct.pack('<I', len(fmt)) + fmt + b'data' + struct.pack('<I', 2) + b'\0\0'
    path = tmp_path / 'extensible.wav'
    path.write_bytes(b'RIFF' + struct.pack('<I', len(body)) + body)
    with pytest.raises(SoundtrackError, match='encoding'):
        validate_wav(path)
