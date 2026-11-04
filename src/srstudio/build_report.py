"""Scoped build evidence: executed checks and published artifacts, never inferred from old files (ADR 0229)."""

from __future__ import annotations

from collections.abc import Iterator, Sequence
from contextlib import contextmanager
from contextvars import ContextVar
from dataclasses import asdict, dataclass, field, fields
from pathlib import Path
from typing import TYPE_CHECKING, Any, Literal

from .errors import SrstudioError

if TYPE_CHECKING:
    from .limbs.validation import MotionReport, QualityProfile

CHECKS = ('sdk', 'schema', 'usage', 'anatomy', 'text', 'motion-quality')
Status = Literal['passed', 'failed', 'skipped']


@dataclass
class BuildReport:
    artifacts: list[dict[str, str]] = field(default_factory=list)
    results: dict[str, list[dict[str, Any]]] = field(default_factory=lambda: {name: [] for name in CHECKS})

    def to_dict(self) -> dict[str, Any]:
        checks = {}
        for name, results in self.results.items():
            rows = results or [
                {'status': 'skipped', 'reason': 'No execution of this check was recorded in this build.'}
            ]
            statuses = {r['status'] for r in rows}
            status = 'failed' if 'failed' in statuses else 'skipped' if 'skipped' in statuses else 'passed'
            checks[name] = {'status': status, 'results': rows}
        return {'artifacts': list(self.artifacts), 'checks': checks}

    def require(self, names: Sequence[str]) -> None:
        checks = self.to_dict()['checks']
        unmet = {name: checks[name]['status'] for name in names if checks[name]['status'] != 'passed'}
        if unmet:
            raise SrstudioError(
                'Required build checks did not pass.',
                code='build.required_checks',
                path='require_check',
                actual=unmet,
                expected='passed',
                remedy='Supply a project root and required dependencies; repair failures and rebuild.',
            )


_active: ContextVar[BuildReport | None] = ContextVar('srstudio_build_report', default=None)


@contextmanager
def capture() -> Iterator[BuildReport]:
    report = BuildReport()
    token = _active.set(report)
    try:
        yield report
    finally:
        _active.reset(token)


def check(
    name: str, status: Status, *, path: Path | None = None, reason: str = '', findings: Sequence[object] = ()
) -> None:
    report = _active.get()
    if report is not None:
        report.results[name].append(
            {
                'status': status,
                'path': str(path.resolve()) if path else None,
                'reason': reason,
                'findings': [str(f) for f in findings],
            }
        )


def artifact(kind: str, path: Path) -> None:
    report = _active.get()
    if report is not None:
        row = {'kind': kind, 'path': str(path.resolve())}
        if row not in report.artifacts:
            report.artifacts.append(row)


def motion_quality(
    profile: QualityProfile | None,
    *,
    sampling: dict[str, Any],
    measured: MotionReport | None = None,
    error: SrstudioError | None = None,
    cached: bool = False,
) -> None:
    """Record sampled limits, including refusals and preflight evidence reused by emission."""
    report = _active.get()
    if report is None:
        return
    if profile is None:
        status, reason = 'skipped', 'No motion quality profile was selected.'
    elif error is not None:
        status, reason = 'failed', str(error)
    elif not any(
        f.name.startswith('max_') and f.name != 'max_collision_checks' and getattr(profile, f.name) is not None
        for f in fields(profile)
    ):
        status, reason = 'skipped', 'The selected profile declares no quality limits.'
    elif measured is None:
        status, reason = 'skipped', 'No sampled motion audit was completed.'
    else:
        status = 'failed' if measured.quality_findings else 'passed'
        reason = 'Sampled numeric limits only; perceptual realism and visual quality require review.'
    report.results['motion-quality'].append(
        {
            'status': status,
            'reason': reason,
            'evidence': {
                'profile': asdict(profile) if profile is not None else None,
                'sampling': dict(sampling),
                'cached': cached,
                'report': measured.to_dict() if measured is not None else None,
                'error': error.to_dict() if error is not None else None,
            },
        }
    )
