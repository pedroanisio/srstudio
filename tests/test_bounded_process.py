"""Real subprocesses verify memory, deadline, pipe and descendant lifetime bounds."""

import importlib
import json
import os
import sys
import time
from pathlib import Path

import pytest


def api():
    return importlib.import_module('srstudio._bounded_process')


def run(code, *, input=b'', **limits):
    module = api()
    return module.run((sys.executable, '-c', code), input=input, limits=module.ProcessLimits(**limits))


def test_binary_input_and_output_round_trip_under_limits():
    data = bytes(range(256)) * 4096
    result = run('import sys; sys.stdout.buffer.write(sys.stdin.buffer.read()[::-1])', input=data)
    assert result.stdout == data[::-1] and result.stderr == b''
    assert result.returncode == 0


def test_worker_directory_resolves_relative_resources_without_changing_parent(tmp_path):
    module = api()
    before = Path.cwd()
    (tmp_path / 'resource').write_bytes(b'local resource')
    result = module.run(
        (sys.executable, '-c', 'from pathlib import Path; print(Path("resource").read_text())'),
        input=b'',
        limits=module.ProcessLimits(),
        cwd=tmp_path,
    )
    assert result.stdout == b'local resource\n'
    assert Path.cwd() == before


def test_invalid_worker_directory_is_typed():
    module = api()
    with pytest.raises(module.BoundedProcessError) as caught:
        module.run((sys.executable, '-c', 'pass'), input=b'', limits=module.ProcessLimits(), cwd=123)
    assert caught.value.to_dict()['code'] == 'process.input'


def test_kernel_address_space_limit_is_hard_and_the_parent_limit_is_unchanged():
    import resource

    before = resource.getrlimit(resource.RLIMIT_AS)
    limit = 128 * 1024**2
    result = run(
        '''import json, resource
print(json.dumps(resource.getrlimit(resource.RLIMIT_AS)))
try:
    bytearray(256 * 1024**2)
except MemoryError:
    print('allocation refused')
else:
    raise AssertionError('allocation exceeded the hard limit')
''',
        memory_bytes=limit,
    )
    first, second = result.stdout.decode().splitlines()
    assert json.loads(first) == [limit, limit]
    assert second == 'allocation refused'
    assert resource.getrlimit(resource.RLIMIT_AS) == before


def inactive(pid):
    path = Path(f'/proc/{pid}/stat')
    try:
        # A killed grandchild can await reaping by the host's init process.
        return path.read_text().split(') ', 1)[1][0] == 'Z'
    except (FileNotFoundError, ProcessLookupError):
        # Gone before the open, or reaped between the open and the read (ESRCH).
        return True


@pytest.mark.parametrize('leader_exits', [False, True])
def test_timeout_kills_descendants_even_if_the_leader_already_exited(leader_exits):
    module = api()
    code = '''import os, time
child = os.fork()
if child == 0:
    while True:
        time.sleep(60)
print(child, flush=True)
'''
    if not leader_exits:
        code += 'while True: time.sleep(60)\n'
    with pytest.raises(module.BoundedProcessError) as caught:
        run(code, timeout=1)
    assert caught.value.to_dict()['code'] == 'process.timeout'
    pid = int(caught.value.stdout.strip())
    # SIGKILL delivery to an orphan is asynchronous. Observe actual termination,
    # without treating the helper's return or signal request as evidence of it.
    deadline = time.monotonic() + 2
    while not inactive(pid) and time.monotonic() < deadline:
        time.sleep(0.01)
    assert inactive(pid)


@pytest.mark.parametrize('stream', ['stdout', 'stderr'])
def test_excessive_output_is_stopped_and_retained_output_is_bounded(stream):
    module = api()
    with pytest.raises(module.BoundedProcessError) as caught:
        run(f'import sys\nwhile True: sys.{stream}.buffer.write(b"x" * 4096)', stdout_bytes=8192, stderr_bytes=8192)
    assert caught.value.to_dict()['code'] == 'process.output'
    assert len(caught.value.stdout) <= 8192
    assert len(caught.value.stderr) <= 8192


def test_failed_process_keeps_bounded_diagnostics():
    module = api()
    with pytest.raises(module.BoundedProcessError) as caught:
        run('import sys; print("failed", file=sys.stderr); sys.exit(7)')
    assert caught.value.to_dict()['code'] == 'process.exit'
    assert caught.value.stderr == b'failed\n'


@pytest.mark.parametrize(
    'options',
    [
        {'timeout': 0},
        {'timeout': True},
        {'timeout': float('nan')},
        {'memory_bytes': True},
        {'memory_bytes': 0},
        {'stdout_bytes': -1},
        {'stderr_bytes': 100 * 1024**2},
    ],
)
def test_invalid_limits_are_refused_before_launch(options):
    module = api()
    with pytest.raises(module.BoundedProcessError):
        module.ProcessLimits(**options)


def test_a_deadline_does_not_wait_for_the_child_to_read_stdin():
    module = api()
    with pytest.raises(module.BoundedProcessError) as caught:
        run('import time; time.sleep(60)', input=b'x' * 1024**2, timeout=0.2)
    assert caught.value.to_dict()['code'] == 'process.timeout'


def test_caller_environment_is_unchanged():
    before = dict(os.environ)
    result = run('import os; print(os.environ["OPENBLAS_NUM_THREADS"])')
    assert result.stdout == b'1\n'
    assert dict(os.environ) == before


@pytest.mark.parametrize('inherited,expected', [((-1, -1), 256), ((128, 512), 128), ((512, 512), 256)])
def test_bootstrap_never_raises_an_inherited_limit(monkeypatch, inherited, expected):
    from srstudio import _process_bootstrap as bootstrap

    calls = []
    monkeypatch.setattr(bootstrap.sys, 'argv', ['bootstrap', '256', 'worker', 'arg'])
    monkeypatch.setattr(bootstrap.resource, 'getrlimit', lambda which: inherited)
    monkeypatch.setattr(bootstrap.resource, 'setrlimit', lambda which, value: calls.append((which, value)))
    monkeypatch.setattr(bootstrap.os, 'execvpe', lambda *args: calls.append(args))
    bootstrap.main()
    assert calls[0] == (bootstrap.resource.RLIMIT_AS, (expected, expected))
    assert calls[1] == (bootstrap.resource.RLIMIT_CORE, (0, 0))
    assert calls[2][:2] == ('worker', ['worker', 'arg'])


@pytest.mark.parametrize('command,input', [((), b''), (('worker',), 'text'), ((None,), b''), (('a\x00b',), b'')])
def test_invalid_command_or_input_is_typed(command, input):
    module = api()
    with pytest.raises(module.BoundedProcessError):
        module.run(command, input=input, limits=module.ProcessLimits())


def test_launch_failure_is_typed(monkeypatch):
    module = api()

    def fail(*args, **kwargs):
        raise OSError('launch refused')

    monkeypatch.setattr(module.subprocess, 'Popen', fail)
    with pytest.raises(module.BoundedProcessError) as caught:
        run('pass')
    assert caught.value.to_dict()['code'] == 'process.launch'
    assert isinstance(caught.value.__cause__, OSError)


def test_kernel_file_limit_stops_a_writer_without_changing_parent(tmp_path):
    import resource

    before = resource.getrlimit(resource.RLIMIT_FSIZE)
    target = tmp_path / 'output'
    with pytest.raises(api().BoundedProcessError):
        run(f'from pathlib import Path; Path({str(target)!r}).write_bytes(b"x" * 65536)', file_bytes=4096)
    assert target.stat().st_size <= 4096
    assert resource.getrlimit(resource.RLIMIT_FSIZE) == before


@pytest.mark.parametrize('value', [0, -1, True, 1.5, 1024**4 + 1])
def test_file_limits_are_positive_bounded_integers(value):
    with pytest.raises(api().BoundedProcessError):
        api().ProcessLimits(file_bytes=value)
