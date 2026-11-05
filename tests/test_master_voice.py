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
    assert 'timeline recorded word timing' in '\n'.join(result.lines())


@pytest.mark.parametrize(
    ('duration', 'end', 'status'), [(1, 0.8, 'PASS'), (3 / 4.2, 0.7, 'SHIP'), (0.7, 0.69, 'FAIL'), (1, 0.65, 'FAIL')]
)
def test_both_clocks(voice, duration, end, status):
    master, project = voice
    evidence(project, master, duration=duration, end=end)
    result = craft_bar.measure_voice(master, project)
    assert result.voices[0].pace_status == status
    assert bool(result.fail_retakes) == (status == 'FAIL')
    assert bool(result.ship_retakes) == (status == 'SHIP')


@pytest.mark.parametrize('bad', ['missing', 'nan', 'zero', 'outside', 'unordered'])
def test_invalid_alignment_refused(voice, bad):
    master, project = voice
    path = project / 'timeline.json'
    data = json.loads(path.read_text())
    line = data['items'][0]
    if bad == 'missing':
        line['prosody']['words'] = []
    elif bad == 'nan':
        line['duration'] = float('nan')
    elif bad == 'zero':
        line['duration'] = 0
    elif bad == 'outside':
        line['prosody']['words'][0]['start'] = -1
    else:
        line['prosody']['words'][1]['start'] = 0
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


@pytest.mark.parametrize('value', [None, float('nan'), float('inf'), True, 0, -1, '3.6'])
def test_pace_rejects_invalid_measurement(value):
    with pytest.raises(craft_bar.CraftError):
        craft_bar.pace_measure('line', value)


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


@pytest.mark.parametrize('status', ['PASS', 'SHIP', 'FAIL'])
def test_common_delivery_acceptance(voice, monkeypatch, status):
    master, project = voice
    duration, end = {'PASS': (1, 0.9), 'SHIP': (0.75, 0.7), 'FAIL': (0.65, 0.64)}[status]
    evidence(project, master, duration=duration, end=end)
    monkeypatch.setattr(master_gate, 'measure', lambda *a, **kw: master_gate.Measured((), (), 0, 5))
    monkeypatch.setattr(master_gate, '_checks', lambda *a: ())
    result = master_gate.accept_master(master, project)
    assert result.ok is (status != 'FAIL')
    assert result.voices[0].pace_status == status
    assert result.ship_retakes == (('line',) if status == 'SHIP' else ())
    reading = master_gate.judge('master', master, None, project=project)
    assert reading.refused is (status == 'FAIL')
    old = result.master_sha256
    master.write_bytes(b'replaced')
    assert master_gate.accept_master(master, project).master_sha256 != old


def test_absent_project_refuses(voice, monkeypatch):
    master, _ = voice
    monkeypatch.setattr(master_gate, 'measure', lambda *a, **kw: master_gate.Measured((), (), 0, 5))
    result = master_gate.accept_master(master)
    assert not result.ok
    assert {c.check for c in result.checks if c.check in ('pace', 'stress')} == {'pace', 'stress'}


def test_pace_exemption_does_not_waive_stress(voice):
    master, project = voice
    path = project / 'timeline.json'
    data = json.loads(path.read_text())
    data['items'][0]['prosody']['words'] = data['items'][0]['prosody']['words'][:2]
    data['items'][0]['direction']['stress'] = []
    path.write_text(json.dumps(data))
    result = craft_bar.measure_voice(master, project)
    assert result.voices[0].pace_status == 'exempt'
    assert not result.ok


def test_phrase_beyond_master_refused(voice):
    master, project = voice
    evidence(project, master, duration=4)
    with pytest.raises(craft_bar.WordsNotHeard, match='past master'):
        craft_bar.measure_voice(master, project)


def test_master_changes_during_measurement_refused(voice, monkeypatch):
    master, project = voice
    original = craft_bar.prosody.measure

    def replace_master(*args):
        master.write_bytes(b'changed during measurement')
        return original(*args)

    monkeypatch.setattr(craft_bar.prosody, 'measure', replace_master)
    with pytest.raises(craft_bar.CraftError, match='master changed'):
        craft_bar.measure_voice(master, project)


def test_preceding_verdict_is_independent(voice, monkeypatch):
    master, project = voice
    monkeypatch.setattr(
        craft_bar.prosody,
        'measure',
        lambda *a: prosody.Measure(
            tuple(
                prosody.WordLevel(t, i * 0.3, (i + 1) * 0.3, -20, None) for i, t in enumerate(['one', 'two', 'three'])
            ),
            (prosody.Stress('three', True, 0, None, 2),),
        ),
    )
    result = craft_bar.measure_voice(master, project)
    by = {m.name: m for m in result.measures}
    assert by['stress:line:three'].status == 'FAIL'
    assert by['preceding:line:three'].status == 'PASS'


@pytest.mark.parametrize('status', ['PASS', 'SHIP', 'FAIL'])
def test_release_keeps_voice_verdicts_and_first_key_na(voice, monkeypatch, status):
    master, project = voice
    duration, end = {'PASS': (1, 0.9), 'SHIP': (0.75, 0.7), 'FAIL': (0.65, 0.64)}[status]
    evidence(project, master, duration=duration, end=end, key='one')
    monkeypatch.setattr(master_gate, 'measure', lambda *a, **kw: master_gate.Measured((), (), 0, 5))
    monkeypatch.setattr(master_gate, '_checks', lambda *a: ())
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
    measured = craft_bar.measure_voice(master, project)
    common = tuple(
        craft_bar.Measure(k, v, 'fixture bar', 'PASS', 'fixture')
        for k, v in dict(integrated_lufs=-16, lra=9, first_word=0.1, constant_bed=False).items()
    )
    monkeypatch.setattr(craft_bar, 'measure', lambda *a: craft_bar.Result(common + measured.measures))
    result = master_gate.evaluate_release(master, project)
    by = {c.check: c for c in result.checks}
    assert by['pace:line'].verdict == by['c7.pace:line'].verdict == status
    assert by['c7.preceding:line:one'].verdict == 'PASS'
    assert by['c7.preceding:line:one'].measured is None
    assert result.refused is (status == 'FAIL')
