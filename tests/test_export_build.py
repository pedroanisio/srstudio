"""`srstudio build-export EXPORT SCENE` builds a scene from the folder sreditor exports, with a default staging."""

import json
import struct
import subprocess
import wave
import xml.etree.ElementTree as ET
from pathlib import Path

import pytest

from srstudio.cli import main
from srstudio.export_build import ExportError, build_export

RATE = 48000
LONG = 'Ela se afasta quase quatro centímetros por ano, devagar demais para alguém notar numa noite comum.'
TAKES = (
    ('01', 'narrator', 'A Lua está indo embora.', 1.5),
    ('02', 'luma', 'E ninguém percebeu.', 2.0),
    ('03', 'narrator', LONG, 4.0),
)


def _wav(path: Path, seconds: float) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with wave.open(str(path), 'wb') as out:
        out.setnchannels(1)
        out.setsampwidth(2)
        out.setframerate(RATE)
        out.writeframes(struct.pack('<h', 0) * int(RATE * seconds))


def _export(folder: Path, *, style: dict | None = None, frame: tuple[int, int, int] = (1080, 1920, 30)) -> Path:
    """A folder laid out as sreditor's export: episode.json, timeline.json, a WAV per take and style.json."""
    width, height, fps = frame
    folder.mkdir(parents=True)
    episode = dict(slug='a-lua', title='A Lua', seed=3, style='cutout', width=width, height=height, fps=fps)
    (folder / 'episode.json').write_text(json.dumps({**episode, 'language': 'pt-BR'}))
    items, start = [], 0.0
    for take_id, actor, text, duration in TAKES:
        audio = f'audio/take-{take_id}.wav'
        _wav(folder / audio, duration)
        words = [{'text': word, 'start': 0.1 * i, 'end': 0.1 * i + 0.08} for i, word in enumerate(text.split())]
        items.append(
            dict(
                id=take_id,
                actor=actor,
                shot='hook',
                text=text,
                start=start,
                duration=duration,
                speech_duration=duration - 0.2,
                audio=audio,
                words=words,
            )
        )
        start += duration
    (folder / 'timeline.json').write_text(json.dumps({'duration': start, 'items': items}))
    if style is not None:
        (folder / 'style.json').write_text(json.dumps(style))
    (folder / 'bible').mkdir()
    (folder / 'bible/cast.json').write_text(json.dumps({'schema': '1.0.0', 'characters': []}))
    return folder


def _scene(path: Path) -> ET.Element:
    return ET.parse(path).getroot()


def _all(root: ET.Element, tag: str) -> list[ET.Element]:
    return [node for node in root.iter() if node.tag.rsplit('}', 1)[-1] == tag]


def test_build_export_writes_a_scene_with_the_main_output_in_the_exported_frame(tmp_path):
    export = _export(tmp_path / 'export', frame=(1080, 1080, 24))
    scene = build_export(export, tmp_path / 'job' / 'episode.scene.xml')
    root = _scene(scene)
    project = _all(root, 'project')[0]
    assert (project.get('width'), project.get('height'), project.get('fps')) == ('1080', '1080', '24')
    assert [output.get('id') for output in _all(root, 'output')] == ['main']


def test_build_export_plays_each_take_from_a_file_beside_the_scene(tmp_path):
    export = _export(tmp_path / 'export')
    scene = build_export(export, tmp_path / 'job' / 'episode.scene.xml')
    sources = sorted(audio.get('src') for audio in _all(_scene(scene), 'audio') if audio.get('src'))
    assert sources == [f'audio/take-{take_id}.wav' for take_id, *_ in TAKES]
    for source in sources:
        assert (scene.parent / source).read_bytes() == (export / source).read_bytes()


def test_build_export_burns_each_spoken_line_as_a_caption(tmp_path):
    export = _export(tmp_path / 'export')
    text = (build_export(export, tmp_path / 'job' / 'episode.scene.xml')).read_text(encoding='utf-8')
    for _, _, line, _ in TAKES:
        for word in line.split():
            assert word.rstrip('.') in text


def test_build_export_paints_the_stage_in_the_exported_palette(tmp_path):
    export = _export(tmp_path / 'export', style={'palette': {'background': '#1D2B4F'}})
    project = _all(_scene(build_export(export, tmp_path / 'job' / 'episode.scene.xml')), 'project')[0]
    assert project.get('background', '').upper() == '#1D2B4F'


def test_build_export_without_episode_json_names_the_missing_file(tmp_path):
    export = _export(tmp_path / 'export')
    (export / 'episode.json').unlink()
    with pytest.raises(ExportError) as caught:
        build_export(export, tmp_path / 'job' / 'episode.scene.xml')
    assert caught.value.path == 'episode.json'
    assert not (tmp_path / 'job' / 'episode.scene.xml').exists()


def test_build_export_with_a_take_audio_outside_the_export_is_refused(tmp_path):
    export = _export(tmp_path / 'export')
    timeline = json.loads((export / 'timeline.json').read_text())
    timeline['items'][0]['audio'] = '../elsewhere.wav'
    (export / 'timeline.json').write_text(json.dumps(timeline))
    with pytest.raises(ExportError) as caught:
        build_export(export, tmp_path / 'job' / 'episode.scene.xml')
    assert caught.value.path == 'items[0].audio'


def test_cli_build_export_takes_only_the_export_and_the_scene(tmp_path, capsys):
    export = _export(tmp_path / 'export')
    scene = tmp_path / 'job' / 'episode.scene.xml'
    assert main(['build-export', str(export), str(scene), '--json']) == 0
    assert json.loads(capsys.readouterr().out)['scene'] == str(scene)
    assert scene.is_file()


def test_cli_build_export_error_is_a_structured_diagnostic(tmp_path, capsys):
    assert main(['build-export', str(tmp_path / 'missing'), str(tmp_path / 's.scene.xml'), '--json']) == 2
    assert json.loads(capsys.readouterr().err)['remedy']


def test_build_export_scene_with_a_long_line_encodes_in_the_engine(tmp_path, scene_render):
    scene = build_export(_export(tmp_path / 'export'), tmp_path / 'job' / 'episode.scene.xml')
    encoded = subprocess.run(
        [
            str(scene_render),
            'encode',
            str(scene),
            '--output',
            'main',
            '-o',
            str(tmp_path / 'job' / 'video.mp4'),
            '--no-upload',
            '--quality',
            'draft',
        ],
        capture_output=True,
        text=True,
        timeout=600,
    )
    assert encoded.returncode == 0, encoded.stdout[-2000:] + encoded.stderr[-2000:]
    assert 'not rendered yet' not in encoded.stdout + encoded.stderr
