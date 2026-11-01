"""Authoring benchmarks measure real phases, preserve output and refuse unbounded work."""

import importlib
import json
import stat
import subprocess
from dataclasses import asdict
from types import SimpleNamespace

import numpy as np
import pytest


def api():
    return importlib.import_module('srstudio.benchmark')


@pytest.mark.parametrize(
    'options',
    [
        {'repeats': 0},
        {'repeats': 8},
        {'repeats': True},
        {'repeats': 1.5},
        {'worker_timeout': float('inf')},
        {'worker_timeout': 0},
        {'worker_timeout': True},
        {'engine_timeout': 0},
        {'engine_timeout': 601},
        {'engine_timeout': 121, 'worker_timeout': 120},
    ],
)
def test_invalid_specs_refuse_before_work(options):
    bench = api()
    with pytest.raises(bench.BenchmarkError):
        bench.BenchmarkSpec(**options)


@pytest.mark.parametrize('kind', ['acting', 'contact'])
def test_pinned_fixtures_compile_identically_and_sample_real_performance(kind):
    fixture = importlib.import_module('srstudio._benchmark_fixtures')
    plan = fixture.plan(kind)
    first = fixture.compile_drawing(plan)
    assert fixture.compile_drawing(plan) == first
    states = fixture.states(plan)
    assert len(states) == fixture.FRAMES + 1
    assert states[0] != states[-2]
    assert first.audited_samples == (8 if kind == 'contact' else 0)


def test_worker_protocol_rejects_unknown_fields_nonfinite_values_and_missing_phases():
    bench = api()
    valid = {
        'schema': bench.WORKER_SCHEMA,
        'rss_bytes': 1000,
        'phases': [
            asdict(bench.Phase(fixture, phase, 0.1, bench.Counts(), 'a' * 64))
            for fixture, phase in bench.EXPECTED_PHASES
        ],
    }
    assert bench._parse_worker(json.dumps(valid))
    for change in ('unknown', 'missing', 'nonfinite', 'negative', 'duplicate', 'wrong-type'):
        value = json.loads(json.dumps(valid))
        if change == 'unknown':
            value['phases'][0]['surprise'] = 3
        elif change == 'missing':
            value['phases'].pop()
        elif change == 'nonfinite':
            value['phases'][0]['seconds'] = float('nan')
        elif change == 'negative':
            value['phases'][0]['counts']['frames'] = -1
        elif change == 'duplicate':
            value['phases'][-1] = value['phases'][0]
        else:
            value['phases'][0]['counts']['engine_invocations'] = True
        with pytest.raises(bench.BenchmarkError) as caught:
            bench._parse_worker(json.dumps(value))
        assert caught.value.to_dict()['code'] == 'benchmark.protocol'


def test_failure_keeps_previous_report_and_removes_private_work(tmp_path, monkeypatch):
    bench = api()
    engine = tmp_path / 'engine'
    engine.write_text('test engine')
    engine.chmod(0o700)
    report = tmp_path / 'report.json'
    report.write_text('previous complete report')

    def fail(*args, **kwargs):
        raise bench.BenchmarkError('worker failed')

    monkeypatch.setattr(bench, '_run_worker', fail)
    with pytest.raises(bench.BenchmarkError):
        bench.run_benchmark(engine=engine, output=report, spec=bench.BenchmarkSpec(repeats=1))
    assert report.read_text() == 'previous complete report'
    assert sorted(p.name for p in tmp_path.iterdir()) == ['engine', 'report.json']


def test_worker_timeout_terminates_without_publishing(tmp_path, monkeypatch):
    bench = api()
    monkeypatch.setattr(bench, '_WORKER', 'import signal\nsignal.pause()\n')
    with pytest.raises(bench.BenchmarkError) as caught:
        bench._run_worker(
            tmp_path / 'unused-engine',
            tmp_path,
            bench.BenchmarkSpec(repeats=1, worker_timeout=0.1, engine_timeout=0.05),
        )
    assert caught.value.to_dict()['code'] == 'benchmark.timeout'


def worker_report():
    bench = api()
    return {
        'schema': bench.WORKER_SCHEMA,
        'rss_bytes': 1000,
        'phases': [
            asdict(bench.Phase(fixture, phase, 0.1, bench.Counts(), 'a' * 64))
            for fixture, phase in bench.EXPECTED_PHASES
        ],
    }


@pytest.mark.parametrize('change', ['hash', 'count', 'rebuild'])
def test_non_equivalent_work_is_refused(change):
    bench = api()
    first, second = worker_report(), worker_report()
    if change == 'hash':
        second['phases'][0]['result_sha256'] = 'b' * 64
    elif change == 'count':
        second['phases'][0]['counts']['frames'] = 1
    else:
        for report in (first, second):
            report['phases'][-1]['result_sha256'] = 'b' * 64
    with pytest.raises(bench.BenchmarkError) as caught:
        bench._aggregate([first, second])
    assert caught.value.to_dict()['code'] == 'benchmark.equivalence'


def test_identity_change_preserves_existing_report(tmp_path, monkeypatch):
    bench = api()
    engine = tmp_path / 'engine'
    engine.write_text('test engine')
    engine.chmod(0o700)
    output = tmp_path / 'report.json'
    output.write_text('previous')
    identities = iter([{'engine': 'before'}, {'engine': 'after'}])
    monkeypatch.setattr(bench, '_toolchain', lambda _: next(identities))
    monkeypatch.setattr(bench, '_run_worker', lambda *args: worker_report())
    with pytest.raises(bench.BenchmarkError) as caught:
        bench.run_benchmark(engine=engine, output=output, spec=bench.BenchmarkSpec(repeats=1))
    assert caught.value.to_dict()['code'] == 'benchmark.identity'
    assert output.read_text() == 'previous'


def test_cli_reports_typed_refusals_and_success(tmp_path, monkeypatch, capsys):
    bench = api()
    args = ['--engine', str(tmp_path / 'engine'), '--output', str(tmp_path / 'report.json')]
    assert bench.main(args + ['--repeats', '0']) == 2
    assert json.loads(capsys.readouterr().err)['code'] == 'benchmark.input'
    monkeypatch.setattr(bench, 'run_benchmark', lambda **kwargs: {'phases': [1, 2]})
    assert bench.main(args) == 0
    assert json.loads(capsys.readouterr().out)['phases'] == 2


def test_report_cannot_replace_renderer(tmp_path):
    bench = api()
    engine = tmp_path / 'engine'
    engine.write_text('renderer bytes')
    engine.chmod(0o700)
    with pytest.raises(bench.BenchmarkError) as caught:
        bench.run_benchmark(engine=engine, output=engine, spec=bench.BenchmarkSpec(repeats=1))
    assert caught.value.to_dict()['code'] == 'benchmark.input'
    assert engine.read_text() == 'renderer bytes'


def test_protocol_rejects_duplicate_json_keys():
    bench = api()
    serialized = json.dumps(worker_report())
    duplicate = serialized.replace('"rss_bytes": 1000', '"rss_bytes": 0, "rss_bytes": 1000')
    with pytest.raises(bench.BenchmarkError):
        bench._parse_worker(duplicate)


@pytest.mark.parametrize('case', ['envelope', 'memory', 'counts', 'phase', 'hash', 'json', 'size'])
def test_worker_protocol_refuses_malformed_measurements(case):
    bench = api()
    value = worker_report()
    if case == 'envelope':
        value['surprise'] = 1
    elif case == 'memory':
        value['rss_bytes'] = True
    elif case == 'counts':
        value['phases'][0]['counts']['surprise'] = 1
    elif case == 'phase':
        value['phases'][0]['fixture'] = 'not-a-fixture'
    elif case == 'hash':
        value['phases'][0]['result_sha256'] = 'not-a-hash'
    serialized = json.dumps(value)
    if case == 'json':
        serialized = '{broken'
    elif case == 'size':
        serialized = ' ' * 1_000_001
    with pytest.raises(bench.BenchmarkError):
        bench._parse_worker(serialized)


@pytest.mark.parametrize('failure', ['timeout', 'launch', 'exit', 'empty', 'dimensions'])
def test_frame_render_failures_have_typed_diagnostics(tmp_path, monkeypatch, failure):
    bench = api()

    def run(command, **options):
        if failure == 'timeout':
            raise subprocess.TimeoutExpired(command, options['timeout'])
        if failure == 'launch':
            raise OSError('launch refused')
        return SimpleNamespace(returncode=1 if failure == 'exit' else 0, stderr='refused')

    monkeypatch.setattr(bench.subprocess, 'run', run)
    shape = (1, 1, 4) if failure == 'dimensions' else (640, 360, 4)
    monkeypatch.setattr(bench.plates, 'pixels', lambda _: np.zeros(shape, dtype=np.uint8))
    with pytest.raises(bench.BenchmarkError) as caught:
        bench._render_frames(tmp_path / 'engine', tmp_path / 'scene.xml', 1)
    assert caught.value.to_dict()['code'] == (
        'benchmark.output' if failure in ('empty', 'dimensions') else 'benchmark.render'
    )


def test_failed_worker_and_missing_engine_are_typed(tmp_path, monkeypatch):
    bench = api()
    with pytest.raises(bench.BenchmarkError) as caught:
        bench.run_benchmark(engine=tmp_path / 'absent', output=tmp_path / 'report.json')
    assert caught.value.to_dict()['code'] == 'benchmark.input'
    monkeypatch.setattr(bench, '_WORKER', 'raise RuntimeError("fixture refused")')
    with pytest.raises(bench.BenchmarkError) as caught:
        bench._run_worker(tmp_path / 'engine', tmp_path, bench.BenchmarkSpec())
    assert caught.value.to_dict()['code'] == 'benchmark.worker'
    assert not (tmp_path / 'report.json').exists()


def test_real_worker_reports_the_same_counts_and_pixels(scene_render, tmp_path):
    bench = api()
    report = bench._worker(scene_render, tmp_path, 120, 0)
    assert bench._parse_worker(json.dumps(report)) == report
    phases = {(p['fixture'], p['name']): p for p in report['phases']}
    assert phases['plates', 'cold-cache']['counts']['engine_invocations'] == 2
    assert phases['plates', 'warm-cache']['counts']['engine_invocations'] == 0
    assert phases['plates', 'verify']['result_sha256'] == phases['plates', 'cold-cache']['result_sha256']


def test_real_benchmark_separates_phases_and_proves_warm_cache_reuse(scene_render, tmp_path):
    bench = api()
    output = tmp_path / 'report.json'
    report = bench.run_benchmark(
        engine=scene_render, output=output, spec=bench.BenchmarkSpec(repeats=2, worker_timeout=600, engine_timeout=120)
    )
    assert json.loads(output.read_text()) == report
    assert stat.S_IMODE(output.stat().st_mode) == 0o600
    assert report['schema'] == 'srstudio.authoring-benchmark/1.0.0'
    assert report['spec']['repeats'] == 2
    assert report['equivalence_verified'] is True
    assert len(report['toolchain']['engine_sha256']) == 64
    assert len(report['toolchain']['srstudio_source_sha256']) == 64
    phases = {(p['fixture'], p['name']): p for p in report['phases']}
    assert set(phases) == set(bench.EXPECTED_PHASES)
    for phase in phases.values():
        assert phase['min_seconds'] >= 0 and phase['max_seconds'] >= phase['median_seconds'] >= phase['min_seconds']
        assert len(phase['observations_seconds']) == 2
    assert phases['plates', 'cold-cache']['counts']['engine_invocations'] == 2
    assert phases['plates', 'warm-cache']['counts']['engine_invocations'] == 0
    assert phases['plates', 'verify']['counts']['engine_invocations'] == 2
    assert phases['contact', 'compilation']['counts']['audited_motion_samples'] == 8
    assert phases['acting', 'planning']['counts']['state_samples'] == 9
    assert phases['acting', 'rendering']['counts']['frames'] == 8
    assert phases['acting', 'rendering']['counts']['engine_invocations'] == 1
    assert phases['catalog', 'cold-discovery']['result_sha256'] == phases['catalog', 'warm-discovery']['result_sha256']
    assert phases['plates', 'cold-cache']['result_sha256'] == phases['plates', 'warm-cache']['result_sha256']
    assert phases['plates', 'verify']['result_sha256'] == phases['plates', 'warm-cache']['result_sha256']
    assert list(tmp_path.iterdir()) == [output]
