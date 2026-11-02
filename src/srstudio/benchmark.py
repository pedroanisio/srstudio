"""Bounded, reproducible authoring-loop measurements; run with ``python -m srstudio.benchmark``.

Fresh workers isolate package import and application caches. Timing is evidence,
never a correctness threshold. Output equivalence is checked before publication.
"""

from __future__ import annotations

import argparse
import hashlib
import importlib
import importlib.metadata
import json
import math
import os
import platform
import signal
import statistics
import subprocess
import sys
import tempfile
import time
from collections.abc import Callable
from dataclasses import asdict, dataclass, fields
from pathlib import Path

from . import _benchmark_fixtures as fixtures
from . import gpu, plates, registry
from .acting import PerformancePlan
from .errors import SrstudioError
from .limbs.motion import Motion

WORKER_SCHEMA = 'srstudio.authoring-benchmark.worker/1.0.0'
EXPECTED_PHASES = (
    ('catalog', 'import'),
    ('catalog', 'cold-discovery'),
    ('catalog', 'warm-discovery'),
    *(
        (kind, phase)
        for kind in ('acting', 'contact')
        for phase in ('planning', 'compilation', 'recompilation', 'rendering')
    ),
    *(('plates', phase) for phase in ('planning', 'compilation', 'cold-cache', 'warm-cache', 'verify')),
)

_WORKER = '''import time
started = time.perf_counter()
import srstudio
import_seconds = time.perf_counter() - started
from srstudio.benchmark import _worker_main
_worker_main(import_seconds)
'''


class BenchmarkError(SrstudioError, ValueError):
    """Invalid benchmark inputs, failed bounded work or non-equivalent output."""


def _fail(message: str, code: str = 'benchmark.protocol') -> BenchmarkError:
    return BenchmarkError(
        message, code=code, remedy='Use the pinned fixture and a working renderer; inspect the failed phase.'
    )


@dataclass(frozen=True)
class BenchmarkSpec:
    repeats: int = 3
    worker_timeout: float = 300
    engine_timeout: float = 60

    def __post_init__(self) -> None:
        if type(self.repeats) is not int or not 1 <= self.repeats <= 7:
            raise _fail('repeats must be an integer in 1..7', 'benchmark.input')
        for value in (self.worker_timeout, self.engine_timeout):
            if type(value) not in (int, float) or not math.isfinite(value) or not 0 < value <= 600:
                raise _fail('timeouts must be finite seconds in (0, 600]', 'benchmark.input')
        if self.engine_timeout > self.worker_timeout:
            raise _fail('engine_timeout must not exceed worker_timeout', 'benchmark.input')


_DEFAULT_SPEC = BenchmarkSpec()


@dataclass(frozen=True)
class Counts:
    entries: int = 0
    state_samples: int = 0
    audited_motion_samples: int = 0
    frames: int = 0
    plates: int = 0
    engine_invocations: int = 0

    def __post_init__(self) -> None:
        if any(type(v) is not int or not 0 <= v <= 1_000_000 for v in asdict(self).values()):
            raise _fail('work counts must be bounded nonnegative integers')


@dataclass(frozen=True)
class Phase:
    fixture: str
    name: str
    seconds: float
    counts: Counts
    result_sha256: str

    def __post_init__(self) -> None:
        if (self.fixture, self.name) not in EXPECTED_PHASES:
            raise _fail('unknown benchmark phase')
        if type(self.seconds) not in (float, int) or not math.isfinite(self.seconds) or self.seconds < 0:
            raise _fail('phase duration must be finite nonnegative seconds')
        if not isinstance(self.counts, Counts):
            raise _fail('phase counts need their typed record')
        if (
            not isinstance(self.result_sha256, str)
            or len(self.result_sha256) != 64
            or any(c not in '0123456789abcdef' for c in self.result_sha256)
        ):
            raise _fail('phase output needs its SHA-256 digest')


def _hash(value: bytes | object) -> str:
    data = value if isinstance(value, bytes) else json.dumps(value, sort_keys=True, allow_nan=False).encode()
    return hashlib.sha256(data).hexdigest()


def _phase(rows: list[Phase], fixture: str, name: str, operation: Callable[[], tuple[object, Counts]]) -> object:
    start = time.perf_counter()
    result, counts = operation()
    digest = _hash(result)
    rows.append(Phase(fixture, name, time.perf_counter() - start, counts, digest))
    return result


def _discover() -> tuple[object, Counts]:
    entries = registry.entries()
    return [entry.describe() for entry in entries], Counts(entries=len(entries))


def _render_frames(engine: Path, source: Path, timeout: float) -> tuple[object, Counts]:
    output = source.parent / 'frame-%04d.png'
    try:
        with gpu.held():
            result = subprocess.run(
                [
                    str(engine),
                    'render',
                    str(source),
                    '--frames',
                    f'0..{fixtures.FRAMES}',
                    '--output',
                    str(output),
                    '--strict',
                ],
                capture_output=True,
                text=True,
                timeout=timeout,
            )
    except (OSError, subprocess.TimeoutExpired) as error:
        raise _fail(f'renderer failed: {error}', 'benchmark.render') from error
    if result.returncode:
        raise _fail(f'renderer refused fixture: {result.stderr[-1200:]}', 'benchmark.render')
    hashes = []
    for i in range(fixtures.FRAMES):
        image = plates.pixels(source.parent / f'frame-{i:04d}.png')
        if image.shape != (fixtures.HEIGHT, fixtures.WIDTH, 4) or not image[..., 3].any():
            raise _fail('renderer produced an empty or incorrectly sized frame', 'benchmark.output')
        hashes.append(_hash(image.tobytes()))
    return hashes, Counts(frames=len(hashes), engine_invocations=1)


def _drawing_phases(rows: list[Phase], kind: str, engine: Path, root: Path, timeout: float) -> None:
    values: list[PerformancePlan | Motion] = []

    def make_plan() -> tuple[object, Counts]:
        value = fixtures.plan(kind)
        assert not isinstance(value, tuple)
        values.append(value)
        return fixtures.states(value), Counts(state_samples=fixtures.FRAMES + 1)

    _phase(rows, kind, 'planning', make_plan)
    compiled: list[fixtures.CompiledFixture] = []

    def compile_() -> tuple[object, Counts]:
        value = fixtures.compile_drawing(values[0])
        compiled.append(value)
        return value.xml, Counts(audited_motion_samples=value.audited_samples, frames=fixtures.FRAMES)

    _phase(rows, kind, 'compilation', compile_)
    _phase(rows, kind, 'recompilation', compile_)
    folder = root / kind
    folder.mkdir(mode=0o700)
    source = folder / 'scene.xml'
    source.write_bytes(compiled[0].xml)
    _phase(rows, kind, 'rendering', lambda: _render_frames(engine, source, timeout))


def _worker(engine: Path, root: Path, timeout: float, import_seconds: float) -> dict:
    rows = [Phase('catalog', 'import', import_seconds, Counts(), _hash('srstudio imported'))]
    _phase(rows, 'catalog', 'cold-discovery', _discover)
    _phase(rows, 'catalog', 'warm-discovery', _discover)
    for kind in ('acting', 'contact'):
        _drawing_phases(rows, kind, engine, root, timeout)

    planned: list[plates.Plate] = []

    def make_plates() -> tuple[object, Counts]:
        value = fixtures.plan('plates')
        assert isinstance(value, tuple)
        planned.extend(value)
        return [[mesh.sha256 for placed in plate.placed for mesh in placed.meshes] for plate in value], Counts(
            plates=len(value)
        )

    _phase(rows, 'plates', 'planning', make_plates)
    _phase(rows, 'plates', 'compilation', lambda: ([plates.digest(p) for p in planned], Counts(plates=len(planned))))
    cache = root / 'plate-cache'

    def cached(warm: bool) -> tuple[object, Counts]:
        with plates.render_session(max_invocations=0 if warm else len(planned), timeout=timeout) as stats:
            images = [plates.render(p, engine=engine, cache=cache, fonts=root) for p in planned]
        hashes = []
        for image in images:
            rgba = plates.pixels(image)
            if rgba.shape != (64, 64, 4) or not rgba[..., 3].any():
                raise _fail('plate fixture produced empty or incorrectly sized pixels', 'benchmark.output')
            hashes.append(_hash(rgba.tobytes()))
        return hashes, Counts(plates=len(images), engine_invocations=stats.invocations)

    _phase(rows, 'plates', 'cold-cache', lambda: cached(False))
    _phase(rows, 'plates', 'warm-cache', lambda: cached(True))

    def verify() -> tuple[object, Counts]:
        with plates.render_session(max_invocations=len(planned), timeout=timeout) as stats:
            hashes = [plates.verify(p, engine=engine, cache=cache, fonts=root) for p in planned]
        return hashes, Counts(plates=len(planned), engine_invocations=stats.invocations)

    _phase(rows, 'plates', 'verify', verify)
    import resource

    rss = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    return {
        'schema': WORKER_SCHEMA,
        'phases': [asdict(row) for row in rows],
        'rss_bytes': int(rss * (1 if sys.platform == 'darwin' else 1024)),
    }


def _worker_main(import_seconds: float) -> None:
    os.umask(0o077)
    print(
        json.dumps(_worker(Path(sys.argv[1]), Path(sys.argv[2]), float(sys.argv[3]), import_seconds), allow_nan=False)
    )


def _unique_keys(pairs: list[tuple[str, object]]) -> dict:
    result: dict = {}
    for name, value in pairs:
        if name in result:
            raise _fail(f'duplicate worker field: {name}')
        result[name] = value
    return result


def _parse_worker(text: str) -> dict:
    try:
        if len(text) > 1_000_000:
            raise _fail('worker report exceeds one megabyte')
        value = json.loads(text, object_pairs_hook=_unique_keys)
        if (
            not isinstance(value, dict)
            or set(value) != {'schema', 'phases', 'rss_bytes'}
            or value['schema'] != WORKER_SCHEMA
        ):
            raise _fail('invalid worker report envelope')
        if type(value['rss_bytes']) is not int or not 0 < value['rss_bytes'] < 2**60:
            raise _fail('invalid worker memory measurement')
        if not isinstance(value['phases'], list) or len(value['phases']) != len(EXPECTED_PHASES):
            raise _fail('worker must report every expected phase exactly once')
        parsed = []
        for item in value['phases']:
            if not isinstance(item, dict) or set(item) != {f.name for f in fields(Phase)}:
                raise _fail('unknown or missing phase fields')
            counts = item['counts']
            if not isinstance(counts, dict) or set(counts) != {f.name for f in fields(Counts)}:
                raise _fail('unknown or missing count fields')
            parsed.append(Phase(**{**item, 'counts': Counts(**counts)}))
        if {(p.fixture, p.name) for p in parsed} != set(EXPECTED_PHASES):
            raise _fail('worker phases are duplicated or incomplete')
        return value
    except (TypeError, json.JSONDecodeError) as error:
        raise _fail(f'cannot parse worker report: {error}') from error


def _run_worker(engine: Path, root: Path, spec: BenchmarkSpec) -> dict:
    command = [sys.executable, '-c', _WORKER, str(engine), str(root), str(spec.engine_timeout)]
    with subprocess.Popen(
        command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, start_new_session=True
    ) as process:
        try:
            stdout, stderr = process.communicate(timeout=spec.worker_timeout)
        except BaseException as error:
            # The worker and renderer share this private process group; stop both before cleanup.
            try:
                os.killpg(process.pid, signal.SIGKILL)
            except ProcessLookupError:
                pass
            process.communicate()
            if isinstance(error, subprocess.TimeoutExpired):
                raise _fail('benchmark worker exceeded its timeout', 'benchmark.timeout') from error
            raise
        if process.returncode:
            raise _fail(f'benchmark worker failed: {stderr[-2000:]}', 'benchmark.worker')
    return _parse_worker(stdout)


def _source_hash(name: str) -> str:
    package = importlib.import_module(name)
    if package.__file__ is None:
        raise _fail(f'cannot fingerprint package source: {name}', 'benchmark.identity')
    folder = Path(package.__file__).parent
    return _hash([(str(path.relative_to(folder)), _hash(path.read_bytes())) for path in sorted(folder.rglob('*.py'))])


def _toolchain(engine: Path) -> dict:
    return {
        'engine_sha256': _hash(engine.read_bytes()),
        'srstudio_source_sha256': _source_hash('srstudio'),
        'sr_core_source_sha256': _source_hash('sr_core'),
        'python': sys.version,
        'packages': {
            name: importlib.metadata.version(name) for name in ('srstudio', 'sr-core', 'numpy', 'scipy', 'shapely')
        },
        'platform': platform.platform(),
        'machine': platform.machine(),
        'cpu_count': os.cpu_count(),
        'renderer_environment': {
            name: os.environ.get(name)
            for name in ('WGPU_BACKEND', 'WGPU_ADAPTER_NAME', 'SR_THREADS', 'VK_ICD_FILENAMES')
        },
    }


def _aggregate(runs: list[dict]) -> list[dict]:
    rows = []
    for fixture, name in EXPECTED_PHASES:
        observations = [next(p for p in run['phases'] if (p['fixture'], p['name']) == (fixture, name)) for run in runs]
        first = observations[0]
        if any(p['counts'] != first['counts'] or p['result_sha256'] != first['result_sha256'] for p in observations):
            raise _fail(f'{fixture}/{name} changed across repeated runs', 'benchmark.equivalence')
        seconds = [p['seconds'] for p in observations]
        rows.append(
            {
                'fixture': fixture,
                'name': name,
                'observations_seconds': seconds,
                'min_seconds': min(seconds),
                'median_seconds': statistics.median(seconds),
                'max_seconds': max(seconds),
                'counts': first['counts'],
                'result_sha256': first['result_sha256'],
            }
        )
    for fixture, names in (
        ('catalog', ('cold-discovery', 'warm-discovery')),
        ('acting', ('compilation', 'recompilation')),
        ('contact', ('compilation', 'recompilation')),
        ('plates', ('cold-cache', 'warm-cache', 'verify')),
    ):
        hashes = {r['result_sha256'] for r in rows if r['fixture'] == fixture and r['name'] in names}
        if len(hashes) != 1:
            raise _fail(f'{fixture} rebuild output differs', 'benchmark.equivalence')
    return rows


def run_benchmark(*, engine: Path, output: Path, spec: BenchmarkSpec = _DEFAULT_SPEC) -> dict:
    """Measure pinned fixtures in fresh workers; atomically publish only a complete equivalent report.

    Requires a POSIX process-group runtime so a timeout also stops renderer descendants.
    Existing reports survive any failure. Each repeat uses a new private application cache.
    """
    if not isinstance(spec, BenchmarkSpec) or os.name != 'posix':
        raise _fail('benchmark needs a BenchmarkSpec and POSIX process groups', 'benchmark.input')
    engine, output = Path(engine).resolve(), Path(output).absolute()
    if not engine.is_file() or not os.access(engine, os.X_OK):
        raise _fail('engine must name an executable renderer', 'benchmark.input')
    if output.resolve() == engine or (output.exists() and output.samefile(engine)):
        raise _fail('report output must not replace the renderer', 'benchmark.input')
    try:
        toolchain = _toolchain(engine)
        output.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
        with tempfile.TemporaryDirectory(prefix='.authoring-benchmark-', dir=output.parent) as directory:
            root = Path(directory)
            runs = []
            for repeat in range(spec.repeats):
                work = root / str(repeat)
                work.mkdir(mode=0o700)
                runs.append(_run_worker(engine, work, spec))
            if _toolchain(engine) != toolchain:
                raise _fail('toolchain changed during the benchmark', 'benchmark.identity')
            report = {
                'schema': 'srstudio.authoring-benchmark/1.0.0',
                'generated_by': {'tool': 'srstudio.benchmark'},
                'spec': asdict(spec),
                'profile': fixtures.PROFILE,
                'fixture_sha256': _hash(fixtures.PROFILE),
                'toolchain': toolchain,
                'phases': _aggregate(runs),
                'equivalence_verified': True,
                'peak_worker_rss_bytes': [run['rss_bytes'] for run in runs],
                'measurement_scope': {
                    'cold': 'Fresh process and application plate cache; OS and GPU caches are uncontrolled.',
                    'warm': 'Same worker and unchanged inputs; includes identity hashing and lookup work.',
                    'seconds': 'Wall seconds including result hashing; no correctness or performance threshold.',
                    'samples': 'Explicit plan-state grid and compiler audit samples; excludes internal sampler calls.',
                    'plates': 'Unique requested plate definitions; verification rerenders each once.',
                    'engine_invocations': 'Observed renderer launch attempts; excludes worker startup.',
                    'rss': 'Process lifetime peak RSS; excludes renderer-child and GPU allocations.',
                    'hardware': 'Platform and renderer selectors recorded; pin driver and GPU identity externally.',
                },
            }
            staged = root / 'report.json'
            staged.write_text(json.dumps(report, indent=2, allow_nan=False) + '\n')
            staged.chmod(0o600)
            os.replace(staged, output)
        return report
    except OSError as error:
        raise _fail(f'benchmark I/O failed: {error}', 'benchmark.io') from error


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--engine', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--repeats', type=int, default=3)
    parser.add_argument('--worker-timeout', type=float, default=_DEFAULT_SPEC.worker_timeout)
    parser.add_argument('--engine-timeout', type=float, default=_DEFAULT_SPEC.engine_timeout)
    args = parser.parse_args(argv)
    try:
        report = run_benchmark(
            engine=args.engine,
            output=args.output,
            spec=BenchmarkSpec(args.repeats, args.worker_timeout, args.engine_timeout),
        )
    except BenchmarkError as error:
        print(json.dumps(error.to_dict(), allow_nan=False), file=sys.stderr)
        return 2
    print(json.dumps({'output': str(args.output), 'phases': len(report['phases']), 'equivalence_verified': True}))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
