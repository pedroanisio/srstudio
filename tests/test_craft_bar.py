"""Offline craft bar tests: timing, mix stress, both recording layouts and CLI."""

import hashlib
import json
import subprocess
from dataclasses import asdict

import pytest

from srstudio import cli, craft_bar


def write(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data))


@pytest.fixture
def master(tmp_path):
    video = tmp_path / 'master.mp4'
    subprocess.run(
        [
            'ffmpeg',
            '-v',
            'error',
            '-y',
            '-f',
            'lavfi',
            '-i',
            'testsrc2=s=1080x1340:r=10:d=3',
            '-f',
            'lavfi',
            '-i',
            "aevalsrc='0.05*sin(2*PI*180*t)*(1+3*between(t,0.7,1.0))':s=16000:d=3",
            '-c:v',
            'libx264',
            '-preset',
            'ultrafast',
            '-c:a',
            'aac',
            str(video),
        ],
        check=True,
    )
    return video


def project(tmp_path, kind):
    p = tmp_path / kind
    ws = [
        {'text': x, 'start': a, 'end': b, 'type': 'word'}
        for x, a, b in [('one', 0.1, 0.4), ('two', 0.4, 0.7), ('three', 0.7, 1.0)]
    ]
    if kind == 'flat':
        audio = p / 'assets/generated/line-1.wav'
        audio.parent.mkdir(parents=True)
        audio.write_bytes(b'cached audio identity')
        key = hashlib.sha256(
            json.dumps(
                {
                    'stt': {'model_id': 'scribe_v1', 'language_code': 'en'},
                    'audio': hashlib.sha256(audio.read_bytes()).hexdigest(),
                },
                sort_keys=True,
            ).encode()
        ).hexdigest()[:20]
        write(p / f'assets/elevenlabs/stt-{key}.json', {'response': {'words': ws}})
        write(
            p / 'dialogue.json',
            {
                'language': 'en-US',
                'clips': [
                    {
                        'generated': {'id': 'line-1', 'kind': 'speech', 'cache': 'assets/generated/line-1.wav'},
                        'placement': {'start': 0.0, 'clip_in': 0, 'clip_out': 1.0},
                    }
                ],
                'stress': [{'line': 1, 'words': {'three': 5}}],
            },
        )
    else:
        write(
            p / 'voiced/speech.json',
            {
                'takes': [
                    {
                        'id': 'line-1',
                        'at': 0,
                        'kept': 1,
                        'characters': ['one', ' ', 'two', ' ', 'three'],
                        'starts': [0.1, 0.4, 0.4, 0.7, 0.7],
                        'ends': [0.4, 0.4, 0.7, 0.7, 1],
                        'direction': {'stress': ['three']},
                    }
                ]
            },
        )
    return p


@pytest.mark.parametrize('kind', ['flat', 'narration'])
def test_both_layouts_measure_master_mix(tmp_path, master, kind):
    result = craft_bar.measure(master, project(tmp_path, kind))
    by = {m.name: m for m in result.measures}
    assert by['first_word'].value == pytest.approx(0.1)
    assert by['pace:line-1'].value == pytest.approx(3 / 0.9, abs=0.001)
    assert by['stress:line-1:three'].value > 8
    assert by['stress:line-1:three'].passed
    assert by['frozen'].value == 0
    assert by['lra'].passed
    assert result.passed
    assert asdict(result)['measures'][0]['bar']


def test_no_recorded_lines(tmp_path):
    write(tmp_path / 'timeline.json', {'items': []})
    with pytest.raises(craft_bar.NoRecordedLines):
        craft_bar.recorded_lines(tmp_path)


def test_unheard_line(tmp_path):
    write(tmp_path / 'timeline.json', {'items': [{'id': '1', 'start': 0, 'duration': 1, 'prosody': {'words': []}}]})
    with pytest.raises(craft_bar.WordsNotHeard):
        craft_bar.recorded_lines(tmp_path)


def test_no_audio(tmp_path, master):
    video = tmp_path / 'silent.mp4'
    subprocess.run(['ffmpeg', '-v', 'error', '-i', str(master), '-c:v', 'copy', '-an', str(video)], check=True)
    with pytest.raises(craft_bar.NoAudio):
        craft_bar.measure(video, project(tmp_path, 'narration'))


def test_cli_project_json(tmp_path, master, capsys):
    p = project(tmp_path, 'narration')
    assert cli.main(['proof', str(master), '--project', str(p), '--json']) == 0
    data = json.loads(capsys.readouterr().out)
    assert data['craft_bar']['passed'] is True
    assert data['craft_bar']['measures']


def test_thresholds():
    assert craft_bar.pace_measure('x', 3.6).passed
    assert not craft_bar.pace_measure('x', 3.601).passed
    assert 'retake' in craft_bar.pace_measure('x', 4.201).bar
    assert craft_bar.pace_measure('x', 4.2).bar != craft_bar.pace_measure('x', 4.201).bar


def test_trailing_freeze(master, tmp_path):
    frozen = tmp_path / 'freeze.mp4'
    subprocess.run(
        [
            'ffmpeg',
            '-v',
            'error',
            '-i',
            str(master),
            '-vf',
            'tpad=stop_mode=clone:stop_duration=2',
            '-an',
            '-c:v',
            'libx264',
            '-preset',
            'ultrafast',
            str(frozen),
        ],
        check=True,
    )
    assert craft_bar.frozen_run(frozen) >= 1.5


def test_trimmed_words_use_placement_clock(tmp_path):
    p = project(tmp_path, 'flat')
    d = json.loads((p / 'dialogue.json').read_text())
    d['clips'][0]['placement'].update(start=0.2, clip_in=0.1, clip_out=1)
    write(p / 'dialogue.json', d)
    (line,) = craft_bar.recorded_lines(p)
    assert line.words[0].start == 0
    assert line.start == 0.2
    assert line.words[-1].end == 0.9


def test_cache_miss_is_typed_and_offline(tmp_path):
    p = project(tmp_path, 'flat')
    (p / 'assets/generated/line-1.wav').write_bytes(b'a different take')
    with pytest.raises(craft_bar.WordsNotHeard, match='no cached transcript'):
        craft_bar.recorded_lines(p)


def test_silent_mix_words_are_unheard(tmp_path, master):
    silent = tmp_path / 'silent-audio.mp4'
    subprocess.run(
        ['ffmpeg', '-v', 'error', '-i', str(master), '-af', 'volume=0', '-c:v', 'copy', str(silent)], check=True
    )
    with pytest.raises(craft_bar.WordsNotHeard, match='not audible'):
        craft_bar.measure(silent, project(tmp_path, 'narration'))


def test_cli_failed_bar_returns_one(tmp_path, master, capsys):
    p = project(tmp_path, 'narration')
    d = json.loads((p / 'voiced/speech.json').read_text())
    d['takes'][0]['at'] = 0.3
    write(p / 'voiced/speech.json', d)
    assert cli.main(['proof', str(master), '--project', str(p), '--json']) == 1
    assert not json.loads(capsys.readouterr().out)['craft_bar']['passed']


def test_constant_declared_music_fails(tmp_path, master):
    p = project(tmp_path, 'narration')
    bed = p / 'music.wav'
    subprocess.run(
        ['ffmpeg', '-v', 'error', '-f', 'lavfi', '-i', 'sine=frequency=220:duration=3', '-c:a', 'pcm_s16le', str(bed)],
        check=True,
    )
    write(p / 'narration.json', {'effects': [{'role': 'music', 'audio': 'music.wav'}]})
    result = craft_bar.measure(master, p)
    m = next(m for m in result.measures if m.name == 'constant_bed')
    assert m.value is True
    assert not m.passed


def test_exact_freeze_boundary(monkeypatch):
    from subprocess import CompletedProcess

    monkeypatch.setattr(
        craft_bar.proof, '_run', lambda *a: CompletedProcess([], 0, '', 'freeze_start: 0.5\nfreeze_end: 2.0')
    )
    assert craft_bar.frozen_run('unused') == 1.5


def test_emphasis_reuses_only_verified_source_timing(tmp_path):
    p = project(tmp_path, 'flat')
    d = json.loads((p / 'dialogue.json').read_text())
    source = p / 'assets/generated/line-1.wav'
    target = p / 'assets/stressed/line-1.wav'
    target.parent.mkdir()
    target.write_bytes(b'gain-only output')
    d['clips'][0]['generated']['cache'] = 'assets/stressed/line-1.wav'
    d['stress'][0].update(
        clip='assets/stressed/line-1.wav',
        source='assets/generated/line-1.wav',
        sha256=hashlib.sha256(target.read_bytes()).hexdigest(),
        source_sha256=hashlib.sha256(source.read_bytes()).hexdigest(),
    )
    write(p / 'dialogue.json', d)
    (line,) = craft_bar.recorded_lines(p)
    assert len(line.words) == 3
    target.write_bytes(b'changed')
    with pytest.raises(craft_bar.WordsNotHeard, match='identity mismatch'):
        craft_bar.recorded_lines(p)


def test_timeline_records_use_master_placement(tmp_path):
    write(
        tmp_path / 'timeline.json',
        {
            'items': [
                {'id': 'effect', 'actor': 'sfx'},
                {
                    'id': 'take',
                    'start': 0.2,
                    'duration': 1,
                    'direction': {'stress': ['two']},
                    'prosody': {
                        'words': [{'text': 'one', 'start': 0.1, 'end': 0.4}, {'text': 'two', 'start': 0.4, 'end': 0.8}]
                    },
                },
            ]
        },
    )
    (line,) = craft_bar.recorded_lines(tmp_path)
    assert line.start + line.words[0].start == pytest.approx(0.3)
    assert line.stress == ('two',)
