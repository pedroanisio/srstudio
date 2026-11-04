"""Scoped build evidence: record executed checks and published artifacts, never infer from old files."""

from __future__ import annotations

from collections.abc import Iterator, Sequence
from contextlib import contextmanager
from contextvars import ContextVar
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Literal

from .errors import SrstudioError

CHECKS = ('sdk', 'schema', 'usage', 'anatomy', 'text')
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
