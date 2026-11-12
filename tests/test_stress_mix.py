"""Integrated mastering keeps the target and verifies words before installation."""

import json
import subprocess
import wave

import numpy as np
import pytest

from srstudio import craft_bar, emphasis, master, master_gate, prosody
from support.emphasis_clip import _clip


def project(tmp_path, target='-15', stress=True):
    wav = tmp_path / 'voice.wav'
    words = _clip(wav)
    emphasis.lean(wav, words, ['weeks'])
    # A brief transient in the stressed word drives the peak, without changing its RMS much.
    with wave.open(str(wav), 'rb') as w:
        params = w.getparams()
        pcm = np.frombuffer(w.readframes(w.getnframes()), dtype='<i2').copy()
    pcm[round(words[-1].start * params.framerate) + 100] = 32000
    with wave.open(str(wav), 'wb') as w:
        w.setparams(params)
        w.writeframes(pcm.tobytes())
    (tmp_path / 'timeline.json').write_text(
        json.dumps(
            {
                'items': [
                    {
                        'id': 'line-1',
                        'start': 0,
                        'duration': 2.1,
                        'direction': {'stress': ['weeks'] if stress else []},
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
    return scene, words


def test_peak_driving_word_keeps_target_and_contrast(tmp_path, monkeypatch, scene_render):
    monkeypatch.setenv('SRSTUDIO_GPU_LOCK', str(tmp_path / 'gpu.lock'))
    scene, words = project(tmp_path)
    before = scene.read_bytes()
    made = master.encode(scene, tmp_path / 'out', engine=scene_render, args=['--no-upload'])
    lufs, _, peak, _ = master_gate.audio_levels(made.paths[0])
    assert abs(lufs - -15) <= 0.2
    assert peak <= -1.4
    mono = tmp_path / 'mono.wav'
    subprocess.run(
        ['ffmpeg', '-v', 'error', '-i', str(made.paths[0]), '-ac', '1', '-ar', '16000', str(mono)], check=True
    )
    got = prosody.measure(mono, words, ['weeks']).stressed[0].db
    assert got is not None and got >= prosody.STRESS_DB
    assert 'target=-15' in made.output and 'line-1:weeks' in made.output and 'before=' in made.output
    assert scene.read_bytes() == before
    assert not list(tmp_path.glob('.stress-*'))


@pytest.mark.parametrize('target', ['-3', '-15'])
def test_impossible_stress_refuses_before_install(tmp_path, monkeypatch, scene_render, target):
    monkeypatch.setenv('SRSTUDIO_GPU_LOCK', str(tmp_path / 'gpu.lock'))
    scene, _ = project(tmp_path, target=target)
    if target == '-15':
        _clip(tmp_path / 'voice.wav')  # a flat take cannot be rescued by a quieter master
    with pytest.raises(craft_bar.CraftError, match=r'line-1.*weeks.*before=.*after='):
        master.encode(scene, tmp_path / 'out', engine=scene_render, args=['--no-upload'])
    assert not list((tmp_path / 'out').rglob('*.wav'))


def test_without_named_stress_is_byte_identical(tmp_path, monkeypatch, scene_render):
    monkeypatch.setenv('SRSTUDIO_GPU_LOCK', str(tmp_path / 'gpu.lock'))
    scene, _ = project(tmp_path, stress=False)
    direct = tmp_path / 'direct'
    subprocess.run([str(scene_render), 'encode', str(scene), '--no-upload', '--out-dir', str(direct)], check=True)
    made = master.encode(scene, tmp_path / 'out', engine=scene_render, args=['--no-upload'])
    assert made.paths[0].read_bytes() == (direct / 'mix.wav').read_bytes()


def test_ducking_is_additive_and_merges_close_words():
    import xml.etree.ElementTree as ET

    from srstudio import _stress_mix
    from srstudio.voice import Word

    root = ET.fromstring('''<scene><audioMix>
        <audioTrack id="bed" role="music" gain="-20"><animate property="gain">
          <key time="0" value="-22"/><key time="5" value="-18"/>
        </animate></audioTrack>
        <audioTrack id="foley" role="effects" gain="-12"/>
        <audioTrack id="voice" role="dialogue"/>
    </audioMix></scene>''')
    line = craft_bar.RecordedLine(
        'one', 2, 1, (Word('salt', 0.1, 0.3, 'word'), Word('now', 0.31, 0.5, 'word')), ('salt', 'now'), 'test'
    )
    original = ET.tostring(root.find('audioMix/audioTrack/animate'))
    _stress_mix._duck(root, [line])
    bed, foley, voice = root.findall('audioMix/audioTrack')
    assert ET.tostring(bed.find('animate')) == original
    for track in (bed, foley):
        animation = track.findall('animate')[-1]
        assert animation.get('additive') == 'true'
        keys = animation.findall('key')
        assert [float(k.get('time')) for k in keys] == pytest.approx([2.085, 2.1, 2.5, 2.515])
        assert [float(k.get('value')) for k in keys] == [0, -6, -6, 0]
    assert voice.find('animate') is None


def test_ducking_covers_the_whole_stressed_line_so_the_bed_does_not_flatten_its_words():
    # The stress meter compares each word with the line's other words on the mixed master. A bed under the
    # unstressed words alone raises them more than the stressed word, so the duck spans the line's words.
    import xml.etree.ElementTree as ET

    from srstudio import _stress_mix
    from srstudio.voice import Word

    root = ET.fromstring('''<scene><audioMix>
        <audioTrack id="bed" role="music"/><audioTrack id="voice" role="dialogue"/>
    </audioMix></scene>''')
    words = (Word('pass', 0.1, 0.3, 'word'), Word('the', 0.35, 0.45, 'word'), Word('salt', 0.6, 0.9, 'word'))
    stressed = craft_bar.RecordedLine('one', 2, 1.2, words, ('salt',), 'test')
    plain = craft_bar.RecordedLine('two', 5, 1, (Word('ok', 0.1, 0.3, 'word'),), (), 'test')
    _stress_mix._duck(root, [stressed, plain])
    keys = root.find('audioMix/audioTrack/animate').findall('key')
    assert [float(k.get('time')) for k in keys] == pytest.approx([2.085, 2.1, 2.9, 2.915])
    assert [float(k.get('value')) for k in keys] == [0, -6, -6, 0]


def test_ducking_refuses_a_stressed_word_that_was_not_timed():
    import xml.etree.ElementTree as ET

    from srstudio import _stress_mix
    from srstudio.voice import Word

    root = ET.fromstring('<scene><audioMix><audioTrack id="bed" role="music"/></audioMix></scene>')
    line = craft_bar.RecordedLine('one', 2, 1, (Word('pass', 0.1, 0.3, 'word'),), ('salt',), 'test')
    with pytest.raises(craft_bar.CraftError, match="one: 'salt': no timed stressed word"):
        _stress_mix._duck(root, [line])


def test_engine_ducks_foley_only_during_word(tmp_path, scene_render):
    import xml.etree.ElementTree as ET

    from srstudio import _stress_mix
    from srstudio.voice import Word

    _clip(tmp_path / 'bed.wav')
    root = ET.fromstring('''<scene version="1.1">
        <project width="16" height="16" fps="30" duration="2.1"/>
        <metadata title="Ducking regression"/>
        <output id="mix" path="mix.wav" codec="audio-only" container="wav"/>
        <assets><audio id="bed" src="bed.wav"/></assets><composition/>
        <audioMix sampleRate="48000" channels="2"><master normalize="none"/>
          <audioTrack id="foley" asset="bed" role="effects" gain="-10">
            <animate property="gain"><key time="0" value="-10"/><key time="3" value="-10"/></animate>
          </audioTrack>
        </audioMix></scene>''')
    scene = tmp_path / 'duck.scene.xml'
    samples = []
    for name, duck in [('before', False), ('after', True)]:
        if duck:
            _stress_mix._duck(
                root, [craft_bar.RecordedLine('one', 0, 2.1, (Word('weeks', 1.65, 1.95, 'word'),), ('weeks',), 'test')]
            )
        ET.ElementTree(root).write(scene, encoding='unicode')
        subprocess.run(
            [str(scene_render), 'encode', str(scene), '--no-upload', '--out-dir', str(tmp_path / name)],
            capture_output=True,
            check=True,
        )
        mono = tmp_path / f'{name}.wav'
        subprocess.run(
            ['ffmpeg', '-v', 'error', '-i', str(tmp_path / name / 'mix.wav'), '-ac', '1', str(mono)], check=True
        )
        with wave.open(str(mono), 'rb') as w:
            rate = w.getframerate()
            samples.append(np.frombuffer(w.readframes(w.getnframes()), dtype='<i2').astype(float))
    before, after = samples
    for start, end, expected in [(0.1, 0.3, 0), (1.7, 1.9, -6)]:
        a, b = round(start * rate), round(end * rate)
        delta = 20 * np.log10(np.linalg.norm(after[a:b]) / np.linalg.norm(before[a:b]))
        assert delta == pytest.approx(expected, abs=0.02)


@pytest.mark.parametrize(
    ('lufs', 'peak', 'verdict'),
    [
        (-15.0, -1.6, None),
        (-14.0, -1.6, None),
        (-16.0, -1.6, None),
        (-16.3, -1.5, 'below the -16 LUFS band, inside the -16.6 floor: accepted case by case'),
        (-16.6, -1.6, 'below the -16 LUFS band, inside the -16.6 floor: accepted case by case'),
    ],
)
def test_loudness_is_judged_by_arc4d3_band_not_the_authored_target(lufs, peak, verdict):
    from srstudio import _stress_mix

    assert _stress_mix.loudness_verdict(lufs, peak, ceiling=-1.5) == verdict


@pytest.mark.parametrize(
    ('lufs', 'peak', 'reason'),
    [
        (-16.7, -1.6, 'below the -16.6 LUFS floor'),
        (-19.5, -2.0, 'below the -16.6 LUFS floor'),
        (-13.9, -1.6, 'above the -14 LUFS band'),
        (-15.0, -1.3, 'true peak -1.3 dBTP over the -1.5 dBTP ceiling'),
        (-15.0, -0.9, 'true peak -0.9 dBTP over the -1.5 dBTP ceiling'),
        (float('nan'), -1.6, 'non-finite'),
    ],
)
def test_loudness_outside_the_band_or_over_the_peak_is_refused(lufs, peak, reason):
    from srstudio import _stress_mix

    with pytest.raises(craft_bar.CraftError, match=reason):
        _stress_mix.loudness_verdict(lufs, peak, ceiling=-1.5)


def test_the_engine_reports_the_ducked_document_the_strict_gate_derives(tmp_path, monkeypatch, scene_render):
    import hashlib

    from srstudio import _stress_mix

    monkeypatch.setenv('SRSTUDIO_GPU_LOCK', str(tmp_path / 'gpu.lock'))
    scene, _ = project(tmp_path)
    ducked = _stress_mix.ducked_document(scene)
    assert ducked is not None and hashlib.sha256(ducked).hexdigest() != hashlib.sha256(scene.read_bytes()).hexdigest()
    report = tmp_path / 'report.json'
    master.encode(scene, tmp_path / 'out', engine=scene_render, args=['--no-upload', '--report', str(report)])
    assert json.loads(report.read_text())['scene']['sha256'] == hashlib.sha256(ducked).hexdigest()


def test_a_scene_with_no_named_stress_is_rendered_as_built(tmp_path):
    from srstudio import _stress_mix

    scene, _ = project(tmp_path, stress=False)
    assert _stress_mix.ducked_document(scene) is None
    (tmp_path / 'timeline.json').unlink()
    assert _stress_mix.ducked_document(scene) is None


def test_a_master_not_normalised_to_a_target_is_rendered_as_built(tmp_path):
    from srstudio import _stress_mix

    scene, _ = project(tmp_path)
    scene.write_text(scene.read_text().replace('normalize="integrated"', 'normalize="none"'))
    assert _stress_mix.ducked_document(scene) is None


def contrasts(monkeypatch, authored: float, mastered: float) -> None:
    """The stressed word's margin as measured on the authored mix (the analysis render) and on the staged master."""
    from srstudio import _stress_mix

    monkeypatch.setattr(
        _stress_mix,
        '_contrasts',
        lambda audio, project: {'line-1:weeks': authored if '.stress-mix-' in str(audio) else mastered},
    )


def test_stress_is_judged_on_the_authored_mix_and_the_mix_is_kept_by_the_master_sha(
    tmp_path, monkeypatch, scene_render
):
    # videos.ruling.162 r5: the bar stands before the loudness stage; the master's limiter may take some back
    monkeypatch.setenv('SRSTUDIO_GPU_LOCK', str(tmp_path / 'gpu.lock'))
    scene, _ = project(tmp_path)
    contrasts(monkeypatch, authored=4.0, mastered=1.0)
    made = master.encode(scene, tmp_path / 'out', engine=scene_render, args=['--no-upload'])
    assert 'line-1:weeks before=4.0 dB after=1.0 dB' in made.output
    kept = master_gate.authored_mix(tmp_path, master_gate.sha256(made.paths[0]))
    assert kept.is_file() and master_gate.audio_levels(kept)[0] < -15  # the mix before normalising, not the master
    assert kept.stat().st_mode & 0o777 == 0o600


def test_a_word_short_on_the_authored_mix_is_refused_however_the_master_reads(tmp_path, monkeypatch, scene_render):
    monkeypatch.setenv('SRSTUDIO_GPU_LOCK', str(tmp_path / 'gpu.lock'))
    scene, _ = project(tmp_path)
    contrasts(monkeypatch, authored=2.0, mastered=4.0)
    with pytest.raises(craft_bar.CraftError, match=r'failed: line-1:weeks before=2.0 dB after=4.0 dB'):
        master.encode(scene, tmp_path / 'out', engine=scene_render, args=['--no-upload'])
    assert not list((tmp_path / 'qa').glob('authored-mix-*')) if (tmp_path / 'qa').exists() else True


def test_ducking_finds_a_stressed_number_heard_as_a_clock():
    import xml.etree.ElementTree as ET

    from srstudio import _stress_mix
    from srstudio.voice import Word

    root = ET.fromstring('<scene><audioMix><audioTrack id="bed" role="music"/></audioMix></scene>')
    words = (Word("It's", 0.1, 0.3, 'word'), Word('6:00,', 0.4, 0.8, 'word'), Word('Juno', 0.9, 1.2, 'word'))
    _stress_mix._duck(root, [craft_bar.RecordedLine('three', 2, 1.4, words, ('six',), 'test')])
    assert root.find('audioMix/audioTrack/animate') is not None
