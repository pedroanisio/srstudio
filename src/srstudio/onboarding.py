"""Offline project scaffolding and read-only checks for a first build and render."""

from __future__ import annotations

import importlib.metadata
import importlib.util
import os
import re
import subprocess
import sys
import tempfile
from contextlib import nullcontext
from importlib.resources import as_file, files
from pathlib import Path
from typing import Any

from ._outputs import write_outputs
from .errors import SrstudioError
from .fonts import FontError, inspect_ttf
from .layout import LayoutError, find_engine
from .sample import Line, SampleError, write_sample_project

FONT = 'assets/fonts/DejaVuSans-Bold.ttf'


class OnboardingError(SrstudioError, ValueError):
    """A starter project cannot be created with the supplied inputs."""


def _check_font(path: Path) -> None:
    try:
        facts = inspect_ttf(path.read_bytes())
        if facts.family != 'DejaVu Sans' or facts.weight != 700 or facts.italic:
            raise FontError('expected upright DejaVu Sans weight 700')
    except (OSError, FontError) as exc:
        raise OnboardingError(
            f'{path}: cannot use the starter font: {exc}',
            code='init.font',
            path='font',
            actual=str(path),
            expected='upright DejaVu Sans weight 700',
            remedy='Omit --font to use the bundled face, or supply DejaVuSans-Bold.ttf.',
        ) from exc


def init_project(
    root: Path, *, slug: str | None = None, font: Path | None = None, overwrite: bool = False
) -> dict[str, Any]:
    """Write a runnable Cutout starter, staging and checking every artifact before publication."""
    root = Path(root).resolve()
    slug = slug if slug is not None else re.sub(r'[^a-z0-9]+', '-', root.name.lower()).strip('-') or 'hello'
    if not re.fullmatch(r'[a-z0-9]+(?:-[a-z0-9]+)*', slug):
        raise OnboardingError(
            'slug: use lowercase letters, numbers and single hyphens',
            code='init.slug',
            path='slug',
            actual=slug,
            expected='lowercase hyphenated slug',
            remedy='Choose a slug such as my-first-episode.',
        )
    font_source = nullcontext(Path(font)) if font is not None else as_file(files('srstudio').joinpath(FONT))
    try:
        with font_source as source, tempfile.TemporaryDirectory(prefix='srstudio-init-') as directory:
            _check_font(source)
            stage = Path(directory) / 'project'
            write_sample_project(stage, [Line('manager', 'Hello there.', 1.2)], angles=['wide'], font=source)
            template = files('srstudio').joinpath('assets/starter/build.py.txt').read_text(encoding='utf-8')
            (stage / 'build.py').write_text(template.replace('__SLUG__', repr(slug)), encoding='utf-8')
            outputs = [(root / p.relative_to(stage), p.read_bytes()) for p in sorted(stage.rglob('*')) if p.is_file()]
            write_outputs(outputs, overwrite=overwrite, follow_symlinks=False)
    except (OSError, SampleError) as exc:
        raise OnboardingError(
            f'{root}: cannot initialize project: {exc}',
            code='init.write',
            path='root',
            actual=str(root),
            remedy='Choose an empty project directory, or pass --overwrite to replace starter files deliberately.',
        ) from exc
    return {
        'schema': 'srstudio.init/1.0.0',
        'root': str(root),
        'slug': slug,
        'files': [str(p.relative_to(root)) for p, _ in outputs],
        'build': ['srstudio', 'build', str(root / 'build.py'), str(root)],
        'render': ['scene-render', 'encode', str(root / f'{slug}.scene.xml')],
    }


def doctor(*, engine: Path | None = None, font: Path | None = None) -> dict[str, Any]:
    """Check local prerequisites; never download, render, or change configuration.

    Engine readiness means its version command succeeds, not that a particular scene
    or GPU backend is supported. Schema validation is optional and reported separately.
    """
    checks: list[dict[str, Any]] = []
    checks.append(
        {
            'name': 'python',
            'status': 'ok' if sys.version_info >= (3, 10) else 'error',
            'version': sys.version.split()[0],
            'remedy': 'Use Python 3.10 or later.',
        }
    )
    for package in ('srstudio', 'sr-core', 'scipy', 'shapely'):
        try:
            version = importlib.metadata.version(package)
            checks.append({'name': package, 'status': 'ok', 'version': version})
        except importlib.metadata.PackageNotFoundError:
            checks.append({'name': package, 'status': 'missing', 'remedy': 'Install srstudio with its dependencies.'})
    try:
        source = nullcontext(Path(font)) if font is not None else as_file(files('srstudio').joinpath(FONT))
        with source as font_path:
            _check_font(font_path)
        checks.append({'name': 'font', 'status': 'ok', 'path': str(font) if font else f'srstudio/{FONT}'})
    except (OnboardingError, OSError) as exc:
        checks.append(
            {
                'name': 'font',
                'status': 'error',
                'message': str(exc),
                'remedy': 'Reinstall srstudio or pass --font with DejaVuSans-Bold.ttf.',
            }
        )
    ready_to_build = all(c['status'] == 'ok' for c in checks)
    checks.append(
        {
            'name': 'schema_validation',
            'status': 'ok' if importlib.util.find_spec('lxml') else 'optional',
            'remedy': 'Install srstudio[validate] for XSD and Schematron checks.',
        }
    )
    try:
        binary = find_engine(engine).resolve()
        if not binary.is_file() or not os.access(binary, os.X_OK):
            raise LayoutError(f'{binary}: engine is not an executable file')
        with tempfile.TemporaryFile() as output:
            result = subprocess.run([str(binary), '--version'], stdout=output, stderr=output, timeout=5, check=False)
            output.seek(0)
            version = output.read(4096).decode('utf-8', errors='replace').strip()
        if result.returncode:
            raise LayoutError(f'{binary}: --version exited {result.returncode}: {version}')
        checks.append({'name': 'engine', 'status': 'ok', 'path': str(binary), 'version': version})
    except (LayoutError, OSError, subprocess.TimeoutExpired) as exc:
        checks.append(
            {
                'name': 'engine',
                'status': 'error',
                'message': str(exc),
                'remedy': 'Install scene-render, then pass --engine or set SRSTUDIO_ENGINE (or PATH).',
            }
        )
    return {
        'schema': 'srstudio.doctor/1.0.0',
        'ready_to_build': ready_to_build,
        'ready_to_render': ready_to_build and checks[-1]['status'] == 'ok',
        'checks': checks,
    }
