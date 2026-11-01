"""Scoped plate work is measurable, bounded and does not publish failed renders."""

from pathlib import Path

import numpy as np
import pytest

from srstudio import _bounded_process, plates
from support.plates import plate


@pytest.fixture
def renderer(tmp_path, monkeypatch):
    engine = tmp_path / 'engine'
    engine.write_text('pinned test engine')
    seen = []

    def run(command, **options):
        seen.append(options)
        plates.write_png(Path(command[command.index('--output') + 1]), np.zeros((64, 64, 4), dtype=np.uint8))
        return _bounded_process.ProcessResult(stdout=b'', stderr=b'', returncode=0)

    monkeypatch.setattr(_bounded_process, 'run', run)
    return engine, seen


def test_nested_sessions_count_actual_attempts_and_warm_hits_consume_no_budget(renderer, tmp_path):
    engine, seen = renderer
    with plates.render_session(max_invocations=2, timeout=5) as outer:
        with plates.render_session(max_invocations=1, timeout=2) as inner:
            first = plates.render(plate(), engine=engine, cache=tmp_path / 'cache', fonts=tmp_path)
        with plates.render_session(max_invocations=0, timeout=1) as warm:
            assert plates.render(plate(), engine=engine, cache=tmp_path / 'cache', fonts=tmp_path) == first
        assert outer.invocations == inner.invocations == 1
        assert warm.invocations == 0
        assert outer.completed == inner.completed == 1 and outer.failed == 0
        assert outer.engine_seconds >= 0
    assert seen[0]['limits'].timeout == 2


def test_exhausted_inner_budget_does_not_count_a_renderer_launch(renderer, tmp_path):
    engine, seen = renderer
    with plates.render_session(max_invocations=3, timeout=1) as outer:
        with plates.render_session(max_invocations=0, timeout=1) as inner:
            with pytest.raises(plates.PlateError) as caught:
                plates.render(plate(), engine=engine, cache=tmp_path / 'cache', fonts=tmp_path)
        assert caught.value.to_dict()['code'] == 'plate.render.budget'
        assert outer.invocations == inner.invocations == 0 and seen == []
    assert list((tmp_path / 'cache').rglob('*.png')) == []


def test_changing_report_cannot_restore_budget(renderer, tmp_path):
    engine, seen = renderer
    with plates.render_session(max_invocations=1) as stats:
        plates.render(plate(), engine=engine, cache=tmp_path / 'first', fonts=tmp_path)
        stats.invocations = 0
        with pytest.raises(plates.PlateError) as caught:
            plates.render(plate(), engine=engine, cache=tmp_path / 'second', fonts=tmp_path)
        assert caught.value.to_dict()['code'] == 'plate.render.budget'
    assert len(seen) == 1


@pytest.mark.parametrize('failure', ['timeout', 'launch', 'exit'])
def test_failures_are_counted_and_context_restores(renderer, tmp_path, monkeypatch, failure):
    engine, _ = renderer
    success = _bounded_process.run

    def fail(command, **options):
        raise _bounded_process.BoundedProcessError('render failed', code=f'process.{failure}')

    monkeypatch.setattr(_bounded_process, 'run', fail)
    with plates.render_session(max_invocations=1, timeout=1) as stats:
        with pytest.raises(plates.PlateError):
            plates.render(plate(), engine=engine, cache=tmp_path / 'cache', fonts=tmp_path)
    assert stats.invocations == stats.failed == 1 and stats.completed == 0
    assert list((tmp_path / 'cache').rglob('*.png')) == []
    monkeypatch.setattr(_bounded_process, 'run', success)
    with plates.render_session(max_invocations=1, timeout=1) as retry:
        plates.render(plate(), engine=engine, cache=tmp_path / 'cache', fonts=tmp_path)
    assert retry.invocations == retry.completed == 1
    assert stats.invocations == 1


@pytest.mark.parametrize(
    'options',
    [
        {'max_invocations': -1},
        {'max_invocations': True},
        {'max_invocations': 10001},
        {'timeout': 0},
        {'timeout': float('inf')},
        {'timeout': True},
        {'timeout': '2'},
    ],
)
def test_invalid_session_limits_fail_before_work(options):
    with pytest.raises(plates.PlateError):
        with plates.render_session(**options):
            pytest.fail('invalid render limits must not enter')


def test_nested_sessions_apply_the_smallest_file_limit(renderer, tmp_path):
    engine, seen = renderer
    with plates.render_session(max_file_bytes=8192):
        with plates.render_session(max_file_bytes=16384):
            plates.render(plate(), engine=engine, cache=tmp_path / 'cache', fonts=tmp_path)
    assert seen[0]['limits'].file_bytes == 8192


@pytest.mark.parametrize('limit', [True, 0, -1, 1.5, 1024**4 + 1])
def test_invalid_file_limits_are_typed_refusals(limit):
    with pytest.raises(plates.PlateError):
        with plates.render_session(max_file_bytes=limit):
            pass
