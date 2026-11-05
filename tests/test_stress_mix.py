"""Master gain must preserve stress measured on the encoded mix."""

import json
import subprocess

import pytest

from srstudio import emphasis, master, prosody
from support.emphasis_clip import _clip


@pytest.mark.parametrize('target', ['-3', '-24'])
@pytest.mark.parametrize('aac', [False, True])
def test_integrated_master_preserves_stressed_word(tmp_path, monkeypatch, target, aac, scene_render):
    engine = str(scene_render)
    monkeypatch.setenv('SRSTUDIO_GPU_LOCK', str(tmp_path / 'gpu.lock'))
    wav = tmp_path / 'voice.wav'
    words = _clip(wav)
    emphasis.lean(wav, words, ['weeks'])
    (tmp_path / 'timeline.json').write_text(
        json.dumps(
            {
                'items': [
                    {
                        'id': '1',
                        'start': 0,
                        'duration': 2.1,
                        'direction': {'stress': ['weeks']},
                        'prosody': {'words': [dict(text=w.text, start=w.start, end=w.end) for w in words]},
                    }
                ]
            }
        )
    )
    scene = tmp_path / 'test.scene.xml'
    scene.write_text(f'''<scene version="1.1">
      <project width="16" height="16" fps="30" duration="2.1"/>
      <metadata title="Stress regression"/>
      <output id="mix" path="mix.wav" codec="audio-only" container="wav"/>
      <assets><audio id="voice" src="voice.wav"/></assets><composition/>
      <audioMix sampleRate="48000" channels="2">
        <master normalize="integrated" loudness="{target}" truePeak="-1.5" limiter="true"/>
        <audioTrack id="voice-track" asset="voice" role="dialogue"/>
      </audioMix></scene>''')
    before = scene.read_bytes()
    made = master.encode(scene, tmp_path / 'out', engine=engine, args=['--no-upload'])
    audio = made.paths[0]
    if aac:
        audio = tmp_path / 'mix.m4a'
        subprocess.run(
            ['ffmpeg', '-v', 'error', '-i', str(made.paths[0]), '-c:a', 'aac', '-b:a', '192k', str(audio)], check=True
        )
    mono = tmp_path / 'mono.wav'
    subprocess.run(['ffmpeg', '-v', 'error', '-i', str(audio), '-ac', '1', '-ar', '16000', str(mono)], check=True)
    got = prosody.measure(mono, words, ['weeks']).stressed[0].db
    assert got is not None and got >= prosody.STRESS_DB, f'master stress {got} dB'
    assert ('stress mix: loudness capped' in made.output) == (target == '-3')
    assert scene.read_bytes() == before
    assert not list(tmp_path.glob('.stress-*'))
    assert not list((tmp_path / 'out').glob('.stress-mix-*'))
