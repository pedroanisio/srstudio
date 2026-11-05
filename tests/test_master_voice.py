"""Final-master voice evidence and delivery policy."""

import hashlib
import json
import wave
from dataclasses import asdict

import pytest

from srstudio import craft_bar, master_gate, prosody


def evidence(project, master, *, duration=1.0, end=0.9, key='three'):
    project.mkdir(exist_ok=True)
    words = [dict(text=t, start=a, end=b) for t, a, b in [('one', 0.0, 0.3), ('two', 0.3, 0.6), ('three', 0.6, end)]]
    (project / 'timeline.json').write_text(
        json.dumps(
            {
                'items': [
                    dict(id='line', start=0, duration=duration, direction={'stress': [key]}, prosody={'words': words})
                ]
            }
        )
    )
    data = dict(
        master_sha256=hashlib.sha256(master.read_bytes()).hexdigest(),
        source='final-master alignment',
        lines=[dict(id='line', start=0, duration=duration, words=words)],
    )
    (project / 'master-voice.json').write_text(json.dumps(data))
    return data


@pytest.fixture
def voice(tmp_path, monkeypatch):
    master = tmp_path / 'master.mp4'
    master.write_bytes(b'master')
    project = tmp_path / 'project'
    evidence(project, master)

    def measured(*args):
        return prosody.Measure(
            tuple(
                prosody.WordLevel(t, a, b, db, None)
                for t, a, b, db in [('one', 0, 0.3, -20), ('two', 0.3, 0.6, -20), ('three', 0.6, 0.9, -14)]
            ),
            (prosody.Stress('three', True, 6, None, 2),),
        )

    monkeypatch.setattr(craft_bar.prosody, 'measure', measured)

    def extract(cmd, *args):
        with wave.open(cmd[-1], 'wb') as audio:
            audio.setnchannels(1)
            audio.setsampwidth(2)
            audio.setframerate(16000)
            audio.writeframes(bytes(16000 * 2 * 3))

    monkeypatch.setattr(craft_bar.proof, '_run', extract)
    return master, project


def test_voice_report(voice):
    master, project = voice
    result = craft_bar.measure_voice(master, project)
    assert result.ok
    assert result.master_sha256 == hashlib.sha256(master.read_bytes()).hexdigest()
    line = result.voices[0]
    assert (line.count, line.phrase_duration, line.word_span) == (3, 1, 0.9)
    assert line.median_db == -20
    assert line.stress_margin == 6 and line.preceding_margin == 0
    assert line.words[2].text == 'three'
    assert result.fail_retakes == () and result.ship_retakes == ()
    assert asdict(result)['master_sha256']
    assert 'final-master alignment' in '\n'.join(result.lines())


@pytest.mark.parametrize(
    ('duration', 'end', 'status'),
    [(3 / 3.6, 0.8, 'PASS'), (3 / 4.2, 0.7, 'SHIP'), (0.7, 0.69, 'FAIL'), (1, 0.65, 'FAIL')],
)
def test_both_clocks(voice, duration, end, status):
    master, project = voice
    evidence(project, master, duration=duration, end=end)
    result = craft_bar.measure_voice(master, project)
    assert result.voices[0].pace_status == status
    assert bool(result.fail_retakes) == (status == 'FAIL')
    assert bool(result.ship_retakes) == (status == 'SHIP')


@pytest.mark.parametrize('bad', ['missing', 'stale', 'nan', 'zero', 'outside', 'duplicate'])
def test_invalid_alignment_refused(voice, bad):
    master, project = voice
    path = project / 'master-voice.json'
    data = json.loads(path.read_text())
    if bad == 'missing':
        path.write_text('{}')
    else:
        if bad == 'stale':
            master.write_bytes(b'replaced')
        elif bad == 'nan':
            data['lines'][0]['words'][0]['start'] = float('nan')
        elif bad == 'zero':
            data['lines'][0]['duration'] = 0
        elif bad == 'outside':
            data['lines'][0]['words'][0]['start'] = -1
        else:
            data['lines'] *= 2
        path.write_text(json.dumps(data))
    with pytest.raises(craft_bar.CraftError):
        craft_bar.measure_voice(master, project)


@pytest.mark.parametrize('bad', ['key', 'unheard', 'quiet', 'preceding', 'nan', 'none'])
def test_stress_refusals_on_every_line(voice, monkeypatch, bad):
    master, project = voice
    if bad == 'key':
        data = json.loads((project / 'timeline.json').read_text())
        data['items'][0]['direction']['stress'] = []
        (project / 'timeline.json').write_text(json.dumps(data))
    levels = [-20, -20, -14]
    if bad == 'quiet':
        levels[2] = -19
    if bad == 'preceding':
        levels[1] = -30
    if bad == 'nan':
        levels[1] = float('nan')
    if bad == 'none':
        levels[1] = None
    monkeypatch.setattr(
        craft_bar.prosody,
        'measure',
        lambda *a: prosody.Measure(
            tuple(
                prosody.WordLevel(t, i * 0.3, (i + 1) * 0.3, db, None)
                for i, (t, db) in enumerate(zip(['one', 'two', 'three'], levels, strict=True))
            ),
            (prosody.Stress('three', bad != 'unheard', 6, None, 2 if bad != 'unheard' else None),),
        ),
    )
    result = craft_bar.measure_voice(master, project)
    assert not result.ok and result.fail_retakes == ('line',)


def test_missing_voice_evidence_refuses_delivery(voice, monkeypatch):
    master, project = voice
    monkeypatch.setattr(master_gate, 'measure', lambda *a, **k: master_gate.Measured((), (), 0, 5))
    (project / 'master-voice.json').write_text('{}')
    reading = master_gate.judge('master', master, None, project=project)
    assert reading.refused


@pytest.mark.parametrize('value', [None, float('nan'), float('inf'), True, 0, -1, '3.6'])
def test_pace_rejects_invalid_measurement(value):
    with pytest.raises(craft_bar.CraftError):
        craft_bar.pace_measure('line', value)


def test_ship_is_accepted_by_master_gate(voice, monkeypatch):
    master, project = voice
    evidence(project, master, duration=3 / 4.0, end=0.7)
    monkeypatch.setattr(master_gate, 'measure', lambda *a, **k: master_gate.Measured((), (), 0, 5))
    reading = master_gate.judge('master', master, None, project=project)
    assert not reading.refused
    assert reading.voice.ship_retakes == ('line',)
    assert reading.voice.voices[0].pace_status == 'SHIP'


def test_first_key_reports_preceding_na(voice, monkeypatch):
    master, project = voice
    evidence(project, master, key='one')
    monkeypatch.setattr(
        craft_bar.prosody,
        'measure',
        lambda *a: prosody.Measure(
            tuple(
                prosody.WordLevel(t, i * 0.3, (i + 1) * 0.3, db, None)
                for i, (t, db) in enumerate(zip(['one', 'two', 'three'], [-14, -20, -20], strict=True))
            ),
            (prosody.Stress('one', True, 6, None, 0),),
        ),
    )
    result = craft_bar.measure_voice(master, project)
    assert result.ok
    previous = next(m for m in result.measures if m.name.startswith('preceding:'))
    assert previous.value is None and 'N/A' in previous.source


@pytest.mark.parametrize(
    ('levels', 'ok'),
    [([-20, -23, -17], True), ([-20, -23.01, -17], False), ([-20, -23, -17.01], False), ([-60, -60, -54], False)],
)
def test_stress_and_preceding_boundaries(voice, monkeypatch, levels, ok):
    master, project = voice
    monkeypatch.setattr(
        craft_bar.prosody,
        'measure',
        lambda *a: prosody.Measure(
            tuple(
                prosody.WordLevel(t, i * 0.3, (i + 1) * 0.3, db, None)
                for i, (t, db) in enumerate(zip(['one', 'two', 'three'], levels, strict=True))
            ),
            (prosody.Stress('three', True, 3, None, 2),),
        ),
    )
    result = craft_bar.measure_voice(master, project)
    assert result.ok is ok
