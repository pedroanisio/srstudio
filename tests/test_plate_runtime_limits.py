"""Real renderer stand-ins exercise scoped process limits and cache failure boundaries."""

import json
import sys
import time
from pathlib import Path

import numpy as np
import pytest

from srstudio import plates
from support.plates import plate


def renderer(tmp_path, body):
    engine = tmp_path / 'engine'
    engine.write_text(f'#!{sys.executable}\n' + body)
    engine.chmod(0o700)
    return engine


def test_nested_memory_limits_reach_the_engine_and_warm_cache_uses_no_process(tmp_path):
    log = tmp_path / 'limit.json'
    fixture = tmp_path / 'fixture.png'
    plates.write_png(fixture, np.full((64, 64, 4), 255, dtype=np.uint8))
    engine = renderer(
        tmp_path,
        f'''import json, os, resource, sys
from pathlib import Path
assert Path(sys.argv[2]).is_file()
Path({str(log)!r}).write_text(json.dumps({{'limit': resource.getrlimit(resource.RLIMIT_AS), 'cwd': os.getcwd()}}))
Path(sys.argv[sys.argv.index('--output') + 1]).write_bytes(Path({str(fixture)!r}).read_bytes())
''',
    )
    memory = 128 * 1024**2
    with plates.render_session(max_invocations=2, max_memory_bytes=memory * 2) as outer:
        with plates.render_session(max_invocations=1, max_memory_bytes=memory) as inner:
            first = plates.render(plate(), engine=engine, cache=tmp_path / 'cache', fonts=tmp_path)
        observed = json.loads(log.read_text())
        assert observed['limit'] == [memory, memory]
        assert not Path(observed['cwd']).exists()
        log.unlink()
        with plates.render_session(max_invocations=0, max_memory_bytes=1) as warm:
            assert plates.render(plate(), engine=engine, cache=tmp_path / 'cache', fonts=tmp_path) == first
        assert not log.exists()
        assert outer.invocations == inner.invocations == 1 and warm.invocations == 0
    assert first.read_bytes() == fixture.read_bytes()


def test_kernel_memory_failure_removes_partial_output_and_consumes_one_attempt(tmp_path):
    log = tmp_path / 'memory.json'
    memory = 128 * 1024**2
    engine = renderer(
        tmp_path,
        f'''import json, resource, sys
from pathlib import Path
Path(sys.argv[sys.argv.index('--output') + 1]).write_bytes(b'partial png')
limit = resource.getrlimit(resource.RLIMIT_AS)
try:
    bytearray({memory * 2})
except MemoryError:
    Path({str(log)!r}).write_text(json.dumps({{'limit': limit, 'allocation_refused': True}}))
    print('allocation refused under address-space limit', file=sys.stderr)
    sys.exit(7)
raise AssertionError('memory allocation escaped its budget')
''',
    )
    with plates.render_session(max_invocations=1, max_memory_bytes=memory) as stats:
        with pytest.raises(plates.PlateError) as caught:
            plates.render(plate(), engine=engine, cache=tmp_path / 'cache', fonts=tmp_path)
    assert json.loads(log.read_text()) == {'limit': [memory, memory], 'allocation_refused': True}
    assert stats.invocations == stats.failed == 1 and stats.completed == 0
    assert caught.value.to_dict()['code'] == 'plate.render.engine'
    assert 'allocation refused' in caught.value.to_dict()['actual']['stderr']
    assert list((tmp_path / 'cache').rglob('*.png')) == []


def inactive(pid):
    try:
        return Path(f'/proc/{pid}/stat').read_text().split(') ', 1)[1][0] == 'Z'
    except FileNotFoundError:
        return True


def test_timeout_stops_renderer_descendants_and_removes_partial_output(tmp_path):
    log = tmp_path / 'child.json'
    engine = renderer(
        tmp_path,
        f'''import json, os, sys, time
from pathlib import Path
Path(sys.argv[sys.argv.index('--output') + 1]).write_bytes(b'partial png')
child = os.fork()
if child == 0:
    while True: time.sleep(60)
Path({str(log)!r}).write_text(json.dumps({{'child': child, 'cwd': os.getcwd()}}))
''',
    )
    with plates.render_session(max_invocations=1, timeout=1, max_memory_bytes=128 * 1024**2) as stats:
        with pytest.raises(plates.PlateError) as caught:
            plates.render(plate(), engine=engine, cache=tmp_path / 'cache', fonts=tmp_path)
    details = json.loads(log.read_text())
    deadline = time.monotonic() + 2
    while not inactive(details['child']) and time.monotonic() < deadline:
        time.sleep(0.01)
    assert inactive(details['child'])
    assert not Path(details['cwd']).exists()
    assert caught.value.to_dict()['code'] == 'plate.render.timeout'
    assert stats.failed == stats.invocations == 1
    assert list((tmp_path / 'cache').rglob('*.png')) == []


def test_excessive_renderer_diagnostics_are_bounded_and_cannot_publish(tmp_path):
    engine = renderer(
        tmp_path,
        '''import sys
from pathlib import Path
Path(sys.argv[sys.argv.index('--output') + 1]).write_bytes(b'partial png')
while True: sys.stderr.buffer.write(b'x' * 4096)
''',
    )
    with plates.render_session(max_invocations=1, max_memory_bytes=128 * 1024**2) as stats:
        with pytest.raises(plates.PlateError) as caught:
            plates.render(plate(), engine=engine, cache=tmp_path / 'cache', fonts=tmp_path)
    assert caught.value.to_dict()['code'] == 'plate.render.output'
    assert stats.failed == stats.invocations == 1
    assert list((tmp_path / 'cache').rglob('*.png')) == []


@pytest.mark.parametrize('memory', [0, -1, True, 1.5, float('inf'), 1024**4 + 1])
def test_invalid_memory_limits_refuse_before_entering_scope(memory):
    with pytest.raises(plates.PlateError):
        with plates.render_session(max_memory_bytes=memory):
            pytest.fail('invalid budget entered a render scope')


def test_retries_cannot_bypass_the_outer_attempt_budget(tmp_path):
    engine = renderer(tmp_path, 'import sys\nsys.exit(7)\n')
    with plates.render_session(max_invocations=2, max_memory_bytes=128 * 1024**2) as stats:
        for _ in range(2):
            with plates.render_session(max_invocations=1):
                with pytest.raises(plates.PlateError):
                    plates.render(plate(), engine=engine, cache=tmp_path / 'cache', fonts=tmp_path)
        with pytest.raises(plates.PlateError) as caught:
            plates.render(plate(), engine=engine, cache=tmp_path / 'cache', fonts=tmp_path)
    assert caught.value.to_dict()['code'] == 'plate.render.budget'
    assert stats.invocations == stats.failed == 2


def test_real_plate_renders_under_explicit_limits_and_reuses_its_pixels(tmp_path, scene_render):
    with plates.render_session(max_invocations=2, timeout=120, max_memory_bytes=8 * 1024**3) as stats:
        image = plates.render(plate(), engine=scene_render, cache=tmp_path / 'cache', fonts=tmp_path)
        digest = plates.verify(plate(), engine=scene_render, cache=tmp_path / 'cache', fonts=tmp_path)
    assert len(digest) == 64
    assert plates.pixels(image).shape == (64, 64, 4)
    assert stats.invocations == stats.completed == 2 and stats.failed == 0
    with plates.render_session(max_invocations=0, max_memory_bytes=1) as warm:
        assert plates.render(plate(), engine=scene_render, cache=tmp_path / 'cache', fonts=tmp_path) == image
    assert warm.invocations == 0
