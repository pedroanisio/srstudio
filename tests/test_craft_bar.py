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
            "aevalsrc='0.17*sin(2*PI*180*t)*(1+3*between(t,0.7,1.0))':s=16000:d=3",
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
    assert by['first_word'].value == pytest.approx(0.1, abs=0.002)
    assert by['pace:line-1'].value == pytest.approx(3 / 1.0)
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
    assert data['craft_bar']['master_sha256'] == hashlib.sha256(master.read_bytes()).hexdigest()
    assert data['craft_bar']['voices'][0]['median_db'] is not None
    assert data['craft_bar']['fail_retakes'] == []


@pytest.mark.parametrize(
    ('pace', 'status'),
    [(3.599999, 'PASS'), (3.6, 'PASS'), (3.600001, 'SHIP'), (4.199999, 'SHIP'), (4.2, 'SHIP'), (4.200001, 'FAIL')],
)
def test_thresholds(pace, status):
    measured = craft_bar.pace_measure('x', pace)
    assert measured.status == status
    assert measured.passed is (status == 'PASS')
    assert measured.ok is (status != 'FAIL')
    assert craft_bar.Result((measured,)).lines()[0].startswith(f'{status} pace:x:')


@pytest.mark.parametrize('json_output', [False, True])
@pytest.mark.parametrize(('pace', 'code'), [(3.6, 0), (3.600001, 0), (4.2, 0), (4.200001, 1)])
def test_cli_band_exit_and_retakes(monkeypatch, capsys, json_output, pace, code):
    measured = craft_bar.pace_measure('NN', pace)
    result = craft_bar.Result((measured,))
    monkeypatch.setattr(craft_bar, 'measure', lambda *a: result)
    monkeypatch.setattr(cli.proof, 'report', lambda *a, **kw: {'video': 'unused.mp4'})
    flags = ['--json'] if json_output else []
    assert cli.main(['proof', 'unused.mp4', '--project', 'unused', *flags]) == code
    output = capsys.readouterr().out
    retakes = ['pace:NN'] if 3.6 < pace <= 4.2 else []
    assert [m.name for m in result.retakes()] == retakes
    assert result.passed is (pace <= 3.6)
    assert result.ok is (code == 0)
    if json_output:
        craft = json.loads(output)['craft_bar']
        assert craft['ok'] is (code == 0)
        assert craft['passed'] is (pace <= 3.6)
        assert craft['retakes'] == retakes
        assert craft['measures'][0]['status'] == measured.status
        assert craft['measures'][0]['passed'] is measured.passed
    else:
        assert f'{measured.status} pace:NN:' in output
        if retakes:
            assert 'Next re-takes: pace:NN' in output


def test_ship_does_not_mask_other_failure():
    ship = craft_bar.pace_measure('ship', 4.0)
    failed = craft_bar.pace_measure('failed', 4.3)
    result = craft_bar.Result((ship, failed))
    assert not result.ok
    assert not result.passed
    assert result.retakes() == (ship,)


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
    result = craft_bar.measure(silent, project(tmp_path, 'narration'))
    assert not result.ok and result.fail_retakes == ('line-1',)


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
    from srstudio.master_gate import Run

    monkeypatch.setattr(
        craft_bar.master_gate,
        'frozen_content',
        lambda *a, **kw: ((Run(0.5, 2.0),), (160, 198, 0, 0), 'detector', 'raw'),
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


@pytest.mark.parametrize(
    ('count', 'duration', 'span', 'phrase_passed', 'span_passed'),
    [
        (3, 2.0, 0.9, True, True),
        (1, 1.0, 0.1, None, None),
        (2, 1.0, 0.2, None, None),
        (3, 2.0, 0.6, True, False),
        (9, 2.5, 2.0, True, True),
        (9, 2.5, 1.9999, True, False),
        (9, 2.4, 2.0, False, True),
        (9, 2.5, 2.0001, True, True),
    ],
    ids=[
        'phrase-edges',
        'one-word',
        'two-words',
        'span-guard',
        'boundaries',
        'span-just-over',
        'phrase-ship',
        'span-just-under',
    ],
)
def test_phrase_pace_and_word_span_guard(tmp_path, master, count, duration, span, phrase_passed, span_passed):
    words = [
        {'text': f'word-{i}', 'start': 0.1 + i * span / count, 'end': 0.1 + (i + 1) * span / count}
        for i in range(count)
    ]
    write(
        tmp_path / 'timeline.json',
        {'items': [{'id': 'take', 'start': 0, 'duration': duration, 'prosody': {'words': words}}]},
    )
    result = craft_bar.measure(master, tmp_path)
    by = {m.name: m for m in result.measures}
    if count < 3:
        assert not any('pace' in m.name for m in result.measures)
        assert not any('pace:' in line or 'pace_span:' in line for line in result.lines())
        return
    phrase = by['pace:take']
    assert phrase.value == pytest.approx(count / duration)
    assert phrase.passed is phrase_passed
    assert '<= 3.6' in phrase.bar
    assert phrase.status == ('PASS' if phrase_passed else 'SHIP')
    assert 'phrase duration' in phrase.source
    guard = by['pace_span:take']
    assert guard.value == pytest.approx(count / span)
    assert guard.passed is span_passed
    assert guard.bar == '<= 4.5 words/s'
    assert 'word span' in guard.source
    assert any(line.startswith(f"{'PASS' if span_passed else 'FAIL'} pace_span:take:") for line in result.lines())
    assert result.voices[0].pace_status == ('FAIL' if not span_passed else 'PASS' if phrase_passed else 'SHIP')
    assert not result.ok  # no key word identified in this pace-only fixture


def test_ship_phrase_can_still_fail_span_guard(tmp_path, master):
    words = [{'text': f'w{i}', 'start': i * 0.19, 'end': (i + 1) * 0.19} for i in range(4)]
    write(
        tmp_path / 'timeline.json', {'items': [{'id': 'take', 'start': 0, 'duration': 1, 'prosody': {'words': words}}]}
    )
    result = craft_bar.measure(master, tmp_path)
    by = {m.name: m for m in result.measures}
    assert by['pace:take'].status == 'SHIP'
    assert by['pace_span:take'].status == 'FAIL'
    assert not result.ok
    assert [m.name for m in result.retakes()] == ['pace:take']
    assert 'stretch the take by 1.2 to reach 4.5 words/s (ADR 0251)' in by['pace_span:take'].source


@pytest.mark.parametrize(
    'rate,factor', [(4.5, None), (4.2, None), (4.55, 1.05), (4.84, 1.1), (5.36, 1.2), (5.625, 1.25), (5.7, None)]
)
def test_stretch_for_names_the_smallest_factor_that_meets_the_span_bar(rate, factor):
    """The least slowing, in 0.05 steps, that brings a fast span to 4.5 words/s; none past the 1.25 cap."""
    assert craft_bar.stretch_for(rate) == factor
    if factor is not None:
        assert rate / factor <= craft_bar.SPAN_BAR < rate / (factor - 0.05)


def test_a_span_past_the_stretch_cap_asks_for_a_new_take(tmp_path, master):
    words = [{'text': f'w{i}', 'start': i * 0.15, 'end': (i + 1) * 0.15} for i in range(4)]
    write(
        tmp_path / 'timeline.json', {'items': [{'id': 'take', 'start': 0, 'duration': 1, 'prosody': {'words': words}}]}
    )
    guard = {m.name: m for m in craft_bar.measure(master, tmp_path).measures}['pace_span:take']
    assert guard.status == 'FAIL'
    assert 'past the 1.25 stretch: a new take' in guard.source


@pytest.mark.parametrize('bad', [None, True, '0.1', float('inf'), float('nan')])
def test_alignment_numbers_are_typed_and_finite(tmp_path, bad):
    write(
        tmp_path / 'timeline.json',
        {
            'items': [
                {
                    'id': 'voice',
                    'start': bad,
                    'duration': 1,
                    'prosody': {'words': [{'text': 'hello', 'start': 0.1, 'end': 0.4}]},
                }
            ]
        },
    )
    with pytest.raises(craft_bar.CraftError):
        craft_bar.recorded_lines(tmp_path)


def test_craft_refuses_finite_out_of_band_loudness(tmp_path, master):
    quiet = tmp_path / 'quiet.mp4'
    subprocess.run(
        ['ffmpeg', '-v', 'error', '-i', str(master), '-af', 'volume=0.5', '-c:v', 'copy', str(quiet)], check=True
    )
    result = craft_bar.measure(quiet, project(tmp_path, 'narration'))
    assert not next(m for m in result.measures if m.name == 'integrated_lufs').ok
    assert not result.ok
    assert any(m.name == 'true_peak' for m in result.measures)


@pytest.mark.parametrize('kind', ['flat', 'narration'])
def test_actual_voice_passes_common_delivery(tmp_path, master, kind):
    from srstudio import master_gate

    p = project(tmp_path, kind)
    result = master_gate.accept_master(master, p)
    assert result.ok
    assert result.voices[0].stress_margin > 3
    assert result.voices[0].preceding_margin >= -3
    assert not master_gate.judge('master', master, None, project=p).refused


@pytest.mark.parametrize('kind', ['flat', 'narration'])
def test_release_consumes_shared_voice_measures(tmp_path, master, kind):
    from srstudio import master_gate

    result = master_gate.evaluate_release(master, project(tmp_path, kind))
    assert not result.refused
    by = {c.check: c for c in result.checks}
    for name in ('pace:line-1', 'pace_span:line-1', 'stress:line-1:three', 'preceding:line-1:three'):
        assert by[name].measured == by['c7.' + name].measured
        assert by[name].verdict == by['c7.' + name].verdict == 'PASS'
    assert result.acceptance.voices[0].stress_status == 'PASS'


def _slowed(tmp_path, *, stressed):
    """A flat project whose line 1 plays its take 1.25 times slower (interview.stretch), leaned on top if
    ``stressed``."""
    p = project(tmp_path, 'flat')
    d = json.loads((p / 'dialogue.json').read_text())
    source = p / 'assets/generated/line-1.wav'
    slowed = p / 'assets/stretched/line-1.wav'
    slowed.parent.mkdir()
    slowed.write_bytes(b'slowed take')

    def digest(path):
        return hashlib.sha256(path.read_bytes()).hexdigest()

    d['clips'][0]['placement']['clip_out'] = 1.25
    d['stretch'] = [
        {
            'line': 1,
            'factor': 1.25,
            'clip': 'assets/stretched/line-1.wav',
            'sha256': digest(slowed),
            'source': 'assets/generated/line-1.wav',
            'source_sha256': digest(source),
        }
    ]
    d['clips'][0]['generated']['cache'] = 'assets/stretched/line-1.wav'
    if stressed:
        leaned = p / 'assets/stressed/line-1.wav'
        leaned.parent.mkdir()
        leaned.write_bytes(b'slowed and leaned')
        d['clips'][0]['generated']['cache'] = 'assets/stressed/line-1.wav'
        d['stress'][0].update(
            clip='assets/stressed/line-1.wav',
            source='assets/stretched/line-1.wav',
            sha256=digest(leaned),
            source_sha256=digest(slowed),
        )
    write(p / 'dialogue.json', d)
    return p, slowed, source


@pytest.mark.parametrize('stressed', [False, True])
def test_a_slowed_line_reads_its_take_s_words_slowed_by_its_factor(tmp_path, stressed):
    p, _, _ = _slowed(tmp_path, stressed=stressed)
    (line,) = craft_bar.recorded_lines(p)
    assert [t for w in line.words for t in (w.start, w.end)] == pytest.approx([0.125, 0.5, 0.5, 0.875, 0.875, 1.25])


@pytest.mark.parametrize('changed', ['slowed', 'source'])
def test_a_slowed_line_whose_clip_or_take_changed_is_refused(tmp_path, changed):
    p, slowed, source = _slowed(tmp_path, stressed=False)
    (slowed if changed == 'slowed' else source).write_bytes(b'changed')
    with pytest.raises(craft_bar.WordsNotHeard, match='stretch source identity mismatch'):
        craft_bar.recorded_lines(p)
