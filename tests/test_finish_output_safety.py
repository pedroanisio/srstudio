"""Finishing and the starter protect artifacts across failures and concurrent writes."""

import os
import subprocess
import sys
from pathlib import Path

import pytest

from srstudio import Episode, EpisodeSpec


def episode(project):
    return Episode(
        EpisodeSpec(slug='safety', title='Safety', description='test', root=project, seed=1, signature=False)
    )


def test_finish_scene_failure_preserves_existing_report(project, tmp_path):
    ep = episode(project)
    out = tmp_path / 'scene.xml'
    out.mkdir()
    report = tmp_path / 'report.json'
    report.write_text('previous report')
    with pytest.raises(OSError):
        ep.finish(out=out, report=report)
    assert report.read_text() == 'previous report'


def test_finish_rolls_back_scene_if_report_commit_fails(project, tmp_path, monkeypatch):
    ep = episode(project)
    out = tmp_path / 'scene.xml'
    report = tmp_path / 'report.json'
    out.write_text('previous scene')
    report.write_text('previous report')
    original = os.replace
    failed = False

    def fail_once(source, target):
        nonlocal failed
        if Path(target) == report and not failed:
            failed = True
            raise OSError('injected report failure')
        return original(source, target)

    monkeypatch.setattr(os, 'replace', fail_once)
    with pytest.raises(OSError, match='injected report failure'):
        ep.finish(out=out, report=report)
    assert out.read_text() == 'previous scene'
    assert report.read_text() == 'previous report'


def test_finish_keeps_backup_if_restoration_fails(project, tmp_path, monkeypatch):
    ep = episode(project)
    out = tmp_path / 'scene.xml'
    report = tmp_path / 'report.json'
    out.write_text('previous scene')
    report.write_text('previous report')
    original = os.replace

    def fail_report(source, target):
        if Path(target) == report:
            raise OSError('report is unavailable')
        return original(source, target)

    monkeypatch.setattr(os, 'replace', fail_report)
    with pytest.raises(OSError, match='backup'):
        ep.finish(out=out, report=report)
    backups = list(tmp_path.glob('.srstudio-output-*/old'))
    assert any(path.read_text() == 'previous report' for path in backups)


@pytest.mark.parametrize('name', ['scene.xml', 'report.json'])
def test_finish_without_overwrite_preserves_dangling_symlink(project, tmp_path, name):
    ep = episode(project)
    out = tmp_path / 'scene.xml'
    report = tmp_path / 'report.json'
    link = tmp_path / name
    link.symlink_to(tmp_path / 'missing')
    with pytest.raises(FileExistsError, match='overwrite=True'):
        ep.finish(out=out, report=report, overwrite=False)
    assert link.is_symlink()
    other = report if link == out else out
    assert not other.exists()


def test_finish_overwrite_follows_existing_symlink(project, tmp_path):
    ep = episode(project)
    out = tmp_path / 'scene.xml'
    target = tmp_path / 'target.xml'
    target.write_text('old scene')
    out.symlink_to(target)
    ep.finish(out=out, report=tmp_path / 'report.json')
    assert out.is_symlink()
    assert target.read_text() != 'old scene'


@pytest.mark.parametrize('name', ['coffee-review.scene.xml', 'sdk-validation.json'])
def test_starter_preserves_output_created_after_preflight(tmp_path, name):
    root = tmp_path / 'project'
    script = Path(__file__).resolve().parents[1] / 'examples' / 'new_episode.py'
    wrapper = tmp_path / 'race.py'
    wrapper.write_text(
        'import runpy, sys\n'
        'from pathlib import Path\n'
        'from srstudio import sample\n'
        'original = sample.write_sample_project\n'
        'def race(root, *args, **kwargs):\n'
        '    result = original(root, *args, **kwargs)\n'
        f'    (Path(root) / {name!r}).write_text("concurrent output")\n'
        '    return result\n'
        'sample.write_sample_project = race\n'
        f'sys.argv = [{str(script)!r}, {str(root)!r}]\n'
        f'runpy.run_path({str(script)!r}, run_name="__main__")\n'
    )
    result = subprocess.run([sys.executable, str(wrapper)], capture_output=True, text=True, timeout=60)
    assert result.returncode != 0
    assert '--overwrite' in result.stderr
    assert (root / name).read_text() == 'concurrent output'
    other = 'sdk-validation.json' if name == 'coffee-review.scene.xml' else 'coffee-review.scene.xml'
    assert not (root / other).exists()
