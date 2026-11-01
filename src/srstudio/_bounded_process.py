"""Bounded binary IPC and POSIX process-group lifetime for trusted worker programs.

RLIMIT_AS caps each process's virtual address space, including mappings and
runtime overhead. It is not an aggregate RSS/GPU cap or a sandbox for hostile
programs that deliberately escape their process group.
"""

from __future__ import annotations

import math
import os
import selectors
import signal
import subprocess
import sys
import time
from dataclasses import dataclass
from pathlib import Path

from .errors import SrstudioError

MAX_INPUT_BYTES = 32 * 1024**2


class BoundedProcessError(SrstudioError, RuntimeError):
    """A launch, deadline, output or exit failure, with bounded captured diagnostics."""

    stdout: bytes = b''
    stderr: bytes = b''


def _fail(code: str, path: str, actual: object, expected: object) -> BoundedProcessError:
    return BoundedProcessError(
        f'{path}: expected {expected}',
        code='process.' + code,
        path=path,
        actual=actual,
        expected=expected,
        remedy='Repair the worker inputs or choose an explicit finite resource budget before retrying.',
    )


@dataclass(frozen=True)
class ProcessLimits:
    timeout: float = 60
    memory_bytes: int = 8 * 1024**3
    stdout_bytes: int = 16 * 1024**2
    stderr_bytes: int = 65536
    file_bytes: int | None = None

    def __post_init__(self) -> None:
        if self.file_bytes is not None and (type(self.file_bytes) is not int or not 1 <= self.file_bytes <= 1024**4):
            raise _fail('input', 'file_bytes', self.file_bytes, 'None or an integer in 1..1099511627776')
        if type(self.timeout) not in (int, float) or not math.isfinite(self.timeout) or not 0 < self.timeout <= 600:
            raise _fail('input', 'timeout', self.timeout, 'finite seconds in (0, 600]')
        for name, maximum in (('memory_bytes', 1024**4), ('stdout_bytes', 32 * 1024**2), ('stderr_bytes', 1024**2)):
            value = getattr(self, name)
            if type(value) is not int or not 1 <= value <= maximum:
                raise _fail('input', name, value, f'an integer in 1..{maximum}')


@dataclass(frozen=True)
class ProcessResult:
    stdout: bytes
    stderr: bytes
    returncode: int


def _kill_group(process: subprocess.Popen) -> None:
    try:
        os.killpg(process.pid, signal.SIGKILL)
    except ProcessLookupError:
        pass


def run(command: tuple[str, ...], *, input: bytes, limits: ProcessLimits, cwd: Path | None = None) -> ProcessResult:
    if os.name != 'posix':
        raise _fail('platform', 'runtime', os.name, 'POSIX process groups and RLIMIT_AS')
    try:
        import resource

        resource.getrlimit(resource.RLIMIT_AS)
    except (ImportError, AttributeError, OSError, ValueError) as error:
        raise _fail('platform', 'runtime', None, 'an available kernel address-space limit') from error
    if type(limits) is not ProcessLimits:
        raise _fail('input', 'limits', None, 'ProcessLimits')
    limits.__post_init__()
    if (
        type(command) is not tuple
        or not 1 <= len(command) <= 128
        or any(type(arg) is not str or not arg or len(arg) > 16384 or '\x00' in arg for arg in command)
    ):
        raise _fail('input', 'command', None, '1..128 nonempty bounded arguments')
    if type(input) is not bytes or len(input) > MAX_INPUT_BYTES:
        raise _fail('input', 'input', None, f'immutable bytes, at most {MAX_INPUT_BYTES}')
    if cwd is not None and (not isinstance(cwd, Path) or '\x00' in str(cwd)):
        raise _fail('input', 'cwd', None, 'a working-directory Path or None')
    environment = dict(os.environ)
    for name in ('OPENBLAS_NUM_THREADS', 'OMP_NUM_THREADS', 'MKL_NUM_THREADS', 'NUMEXPR_NUM_THREADS'):
        environment[name] = '1'
    bootstrap = Path(__file__).with_name('_process_bootstrap.py')
    file_limit = () if limits.file_bytes is None else (f'--file-bytes={limits.file_bytes}',)
    argv = (sys.executable, '-I', str(bootstrap), str(limits.memory_bytes), *file_limit, *command)
    deadline = time.monotonic() + limits.timeout
    stdout, stderr = bytearray(), bytearray()
    try:
        process = subprocess.Popen(
            argv,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            start_new_session=True,
            env=environment,
            cwd=cwd,
        )
    except OSError as error:
        raise _fail('launch', 'command', command[0], 'an executable worker runtime') from error
    assert process.stdin is not None and process.stdout is not None and process.stderr is not None
    try:
        with selectors.DefaultSelector() as selector:
            for stream, event, kind in (
                (process.stdin, selectors.EVENT_WRITE, 'input'),
                (process.stdout, selectors.EVENT_READ, 'stdout'),
                (process.stderr, selectors.EVENT_READ, 'stderr'),
            ):
                os.set_blocking(stream.fileno(), False)
                selector.register(stream, event, kind)
            position = 0
            while selector.get_map():
                remaining = deadline - time.monotonic()
                if remaining <= 0:
                    raise _fail('timeout', 'timeout', limits.timeout, 'worker completion within the deadline')
                for key, _ in selector.select(remaining):
                    if key.data == 'input':
                        try:
                            position += (
                                os.write(key.fd, input[position : position + 65536]) if position < len(input) else 0
                            )
                        except BrokenPipeError:
                            position = len(input)
                        if position == len(input):
                            selector.unregister(key.fileobj)
                            process.stdin.close()
                        continue
                    chunk = os.read(key.fd, 65536)
                    if not chunk:
                        selector.unregister(key.fileobj)
                        continue
                    buffer, maximum = (
                        (stdout, limits.stdout_bytes) if key.data == 'stdout' else (stderr, limits.stderr_bytes)
                    )
                    available = maximum - len(buffer)
                    buffer.extend(chunk[:available])
                    if len(chunk) > available:
                        raise _fail('output', key.data, maximum, 'output within the declared byte cap')
            try:
                code = process.wait(timeout=max(0, deadline - time.monotonic()))
            except subprocess.TimeoutExpired as error:
                raise _fail('timeout', 'timeout', limits.timeout, 'worker exit within the deadline') from error
            if code:
                raise _fail('exit', 'returncode', code, 'a successful worker exit')
            return ProcessResult(bytes(stdout), bytes(stderr), code)
    except BoundedProcessError as error:
        error.stdout, error.stderr = bytes(stdout), bytes(stderr)
        raise
    except OSError as error:
        failure = _fail('io', 'pipes', None, 'working binary worker pipes')
        failure.stdout, failure.stderr = bytes(stdout), bytes(stderr)
        raise failure from error
    finally:
        # Descendants may hold pipes open after their leader exits. Stop the
        # entire owned group on every terminal path, including interruptions.
        _kill_group(process)
        process.wait()
        for stream in (process.stdin, process.stdout, process.stderr):
            stream.close()
