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


@pytest.mark.parametrize(
    ('frame_status', 'voice_status', 'stale_authority'),
    [
        ('PASS', 'SHIP', False),
        ('FAIL', 'SHIP', False),
        ('error', 'SHIP', False),
        ('PASS', 'FAIL', False),
        ('PASS', 'SHIP', True),
    ],
)
def test_read_combines_accept_master_voice_authority_and_frames(
    voice, monkeypatch, frame_status, voice_status, stale_authority
):
    from srstudio import final_frame_gate
    from srstudio.authority import Disposition, Message
    from srstudio.releases import Release
    from srstudio.social import InstagramPost

    master, project = voice
    duration, end = (0.75, 0.7) if voice_status == 'SHIP' else (0.65, 0.64)
    evidence(project, master, duration=duration, end=end)
    sha = hashlib.sha256(master.read_bytes()).hexdigest()
    measured = master_gate.Measured(
        (),
        (),
        0,
        5,
        first_word=0.1,
        lufs=-16.5,
        peak_dbtp=-1.1,
        crop=(64, 64, 0, 0),
        detector='fixture detector',
        freeze_raw='fixture EOF',
        loudness_raw='fixture loudness',
        speech_evidence=('fixture alignment',),
    )
    monkeypatch.setattr(master_gate, 'measure', lambda *a, **kw: measured)
    common = tuple(
        craft_bar.Measure(k, v, 'fixture bar', 'PASS', 'fixture')
        for k, v in dict(integrated_lufs=-16.5, lra=5, first_word=0.1, constant_bed=False).items()
    )
    monkeypatch.setattr(craft_bar, 'measure', lambda *a: craft_bar.Result(common))
    approval = Disposition(
        'a' * 64 if stale_authority else sha,
        'integrated_lufs',
        None,
        'approve measured fixture',
        None,
        'production',
        'fixture-builder',
        Message('arc4d3', 'fixture://approval', 'Approved this fixture.'),
        'Approved this fixture.',
    )
    frames = final_frame_gate.FinalFrameResult(
        'project',
        sha,
        64,
        64,
        (),
        (final_frame_gate.CheckResult('project', 'anatomy', frame_status, 0, 0, sha, 'fixture frame review', None),),
    )
    calls = []

    def review(path, **kwargs):
        calls.append((path, kwargs))
        if frame_status == 'error':
            raise final_frame_gate.FinalFrameError('unreadable fixture review')
        return frames

    monkeypatch.setattr(master_gate, 'check_master', review)
    readings = master_gate.read(
        {'project': Release('project', InstagramPost('t', 'd'))},
        project.parent,
        master.parent,
        {'project': 'master'},
        scopes={'project': 'production'},
        dispositions={'project': (approval,)},
    )
    result = readings['project']
    acceptance = result.acceptance
    assert acceptance.voices[0].pace_status == voice_status
    assert acceptance.ship_retakes == (('line',) if voice_status == 'SHIP' else ())
    assert acceptance.fail_retakes == (('line',) if voice_status == 'FAIL' else ())
    lufs = next(c for c in acceptance.checks if c.check == 'integrated_lufs')
    assert lufs.verdict == ('FAIL' if stale_authority else 'APPROVED')
    assert lufs.approval == (None if stale_authority else approval)
    assert acceptance.ok is (voice_status != 'FAIL' and not stale_authority)
    refused = frame_status != 'PASS' or voice_status == 'FAIL' or stale_authority
    assert result.refused is refused
    assert bool(master_gate.refusals(readings)) is refused
    report = '\n'.join(master_gate.lines(readings))
    assert 'VoiceLine(' in report and 'retakes:' in report
    assert 'pace:line' in report and 'stress:line:three' in report
    assert 'authority:' in report if stale_authority else 'fixture://approval' in report
    assert ('unreadable fixture review' if frame_status == 'error' else 'fixture frame review') in report
    assert calls == [
        (
            master,
            dict(slug='project', review_path=project / final_frame_gate.RECORD, ffmpeg='ffmpeg', ffprobe='ffprobe'),
        )
    ]


def one_word(project, monkeypatch, *, stress=(), db=-14.0):
    """A one-word line, "Okay.", 0.1 to 0.5 s in a 1 s phrase."""
    words = [dict(text='okay', start=0.1, end=0.5)]
    item = dict(id='line', start=0, duration=1, direction={'stress': list(stress)}, prosody={'words': words})
    (project / 'timeline.json').write_text(json.dumps({'items': [item]}))
    marks = tuple(prosody.Stress(w, True, 0, None, 0) for w in stress)
    monkeypatch.setattr(
        craft_bar.prosody,
        'measure',
        lambda *a: prosody.Measure((prosody.WordLevel('okay', 0.1, 0.5, db, None),), marks),
    )


@pytest.mark.parametrize('stress', [(), ('okay',)])
def test_a_one_word_line_is_exempt_from_stress_not_missing(voice, monkeypatch, stress):
    # videos.ruling.162 r4 (arc4d3, Slack 1793964550.718129): no median to stand over, so no stress bar.
    master, project = voice
    one_word(project, monkeypatch, stress=stress)
    result = craft_bar.measure_voice(master, project)
    assert result.ok and result.fail_retakes == ()
    exempt = next(m for m in result.measures if m.name == 'stress:line')
    assert exempt.value is None and exempt.status == 'PASS' and exempt.source.endswith('; N/A')
    assert not [m for m in result.measures if m.name.startswith(('stress:line:', 'preceding:'))]


def test_an_unheard_one_word_line_still_fails(voice, monkeypatch):
    master, project = voice
    one_word(project, monkeypatch, db=-90.0)
    result = craft_bar.measure_voice(master, project)
    assert not result.ok and result.fail_retakes == ('line',)
    assert next(m for m in result.measures if m.name == 'stress:line').status == 'FAIL'


def test_release_reads_a_one_word_line_as_exempt_not_missing(voice, monkeypatch):
    master, project = voice
    one_word(project, monkeypatch)
    monkeypatch.setattr(master_gate, 'measure', lambda *a, **kw: master_gate.Measured((), (), 0, 5))
    monkeypatch.setattr(master_gate, '_checks', lambda *a: ())
    measured = craft_bar.measure_voice(master, project)
    common = tuple(
        craft_bar.Measure(k, v, 'fixture bar', 'PASS', 'fixture')
        for k, v in dict(integrated_lufs=-16, lra=9, first_word=0.1, constant_bed=False).items()
    )
    monkeypatch.setattr(craft_bar, 'measure', lambda *a: craft_bar.Result(common + measured.measures))
    result = master_gate.evaluate_release(master, project)
    by = {c.check: c for c in result.checks}
    assert by['c7.stress:line'].verdict == 'PASS' and by['c7.stress:line'].measured is None
    assert not result.refused


def by_source(monkeypatch, margins):
    """Each line's audio cut from one source; the stressed word stands ``margins[source name]`` dB over the median."""
    seen = {}

    def extract(cmd, *args):
        seen['src'] = cmd[cmd.index('-i') + 1]
        with wave.open(cmd[-1], 'wb') as audio:
            audio.setnchannels(1)
            audio.setsampwidth(2)
            audio.setframerate(16000)
            audio.writeframes(bytes(16000 * 2 * 3))

    def measured(*args):
        db = -20 + margins[seen['src'].rsplit('/', 1)[-1]]
        return prosody.Measure(
            tuple(
                prosody.WordLevel(t, a, b, d, None)
                for t, a, b, d in [('one', 0, 0.3, -20), ('two', 0.3, 0.6, -20), ('three', 0.6, 0.9, db)]
            ),
            (prosody.Stress('three', True, db + 20, None, 2),),
        )

    monkeypatch.setattr(craft_bar.proof, '_run', extract)
    monkeypatch.setattr(craft_bar.prosody, 'measure', measured)


def test_stress_is_measured_on_the_authored_mix_and_pace_on_the_master(voice, monkeypatch, tmp_path):
    # videos.ruling.162 r5: the bar stands before the master's loudness stage, which can flatten a lifted word
    master, project = voice
    mix = tmp_path / 'authored.wav'
    mix.write_bytes(b'authored mix')
    by_source(monkeypatch, {'master.mp4': 0.5, 'authored.wav': 4.0})
    assert not craft_bar.measure_voice(master, project).ok  # on the master the limiter took it back
    result = craft_bar.measure_voice(master, project, stress_from=mix)
    assert result.ok and result.voices[0].stress_margin == 4.0
    assert result.master_sha256 == hashlib.sha256(b'master').hexdigest()
    stress = next(m for m in result.measures if m.name == 'stress:line:three')
    assert f'authored mix sha256={hashlib.sha256(b"authored mix").hexdigest()}' in stress.source
    assert f'master mix sha256={result.master_sha256}' in stress.source
    pace = next(m for m in result.measures if m.name == 'pace:line')
    assert 'authored mix' not in pace.source


def test_an_authored_mix_shorter_than_a_line_is_refused(voice, monkeypatch, tmp_path):
    master, project = voice
    mix = tmp_path / 'authored.wav'
    mix.write_bytes(b'authored mix')
    by_source(monkeypatch, {'master.mp4': 4.0, 'authored.wav': 4.0})
    evidence(project, master, duration=4)
    with pytest.raises(craft_bar.WordsNotHeard, match='past the authored mix|past master'):
        craft_bar.measure_voice(master, project, stress_from=mix)


def test_acceptance_reads_the_authored_mix_named_by_the_master_sha(voice, monkeypatch):
    master, project = voice
    monkeypatch.setattr(master_gate, 'measure', lambda *a, **kw: master_gate.Measured((), (), 0, 5))
    monkeypatch.setattr(master_gate, '_checks', lambda *a: ())
    sha = hashlib.sha256(master.read_bytes()).hexdigest()
    by_source(monkeypatch, {'master.mp4': 0.5, f'authored-mix-{sha}.wav': 4.0, 'authored-mix-other.wav': 4.0})
    assert not master_gate.accept_master(master, project).ok  # no authored mix: the master itself, stricter
    (project / 'qa').mkdir()
    (project / 'qa' / 'authored-mix-other.wav').write_bytes(b'another master')
    assert not master_gate.accept_master(master, project).ok  # another master's mix is not this one's
    (project / 'qa' / f'authored-mix-{sha}.wav').write_bytes(b'authored mix')
    result = master_gate.accept_master(master, project)
    assert result.ok and result.voices[0].stress_margin == 4.0
