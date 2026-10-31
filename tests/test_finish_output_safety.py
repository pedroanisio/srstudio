"""Finishing and the starter protect artifacts across failures and concurrent writes."""

import os
import shutil
import stat
import subprocess
import sys
from pathlib import Path

import pytest

from srstudio import Episode, EpisodeSpec
from srstudio.episode import SceneCheckError


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


def test_finish_preserves_scene_and_backup_if_report_commit_fails(project, tmp_path, monkeypatch):
    ep = episode(project)
    out = tmp_path / 'scene.xml'
    report = tmp_path / 'report.json'
    out.write_text('previous scene')
    report.write_text('previous report')
    original = os.link
    failed = False

    def fail_once(source, target, *args, **kwargs):
        nonlocal failed
        if Path(target).name == report.name and not failed:
            failed = True
            raise OSError('injected report failure')
        return original(source, target, *args, **kwargs)

    monkeypatch.setattr(os, 'link', fail_once)
    with pytest.raises(OSError, match='backup'):
        ep.finish(out=out, report=report)
    assert '<scene ' in out.read_text()
    assert any(path.read_text() == 'previous scene' for path in tmp_path.glob('.srstudio-output-*/old'))
    assert report.read_text() == 'previous report'


def test_finish_keeps_backup_if_restoration_fails(project, tmp_path, monkeypatch):
    ep = episode(project)
    out = tmp_path / 'scene.xml'
    report = tmp_path / 'report.json'
    out.write_text('previous scene')
    report.write_text('previous report')
    original = os.link

    def fail_report(source, target, *args, **kwargs):
        if Path(target).name == report.name:
            raise OSError('report is unavailable')
        return original(source, target, *args, **kwargs)

    monkeypatch.setattr(os, 'link', fail_report)
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


@pytest.mark.parametrize('name', ['scene.xml', 'report.json'])
def test_finish_does_not_follow_symlink_created_after_input_checks(project, tmp_path, monkeypatch, name):
    import srstudio.episode as episode_module

    root = tmp_path / 'project'
    shutil.copytree(project, root)
    ep = episode(root)
    source = root / 'dialogue.json'
    original = source.read_bytes()
    out = tmp_path / 'scene.xml'
    report = tmp_path / 'report.json'
    target = tmp_path / name
    write = episode_module.write_outputs

    def swap(outputs, **kwargs):
        target.symlink_to(source)
        return write(outputs, **kwargs)

    monkeypatch.setattr(episode_module, 'write_outputs', swap)
    ep.finish(out=out, report=report)
    assert source.read_bytes() == original


def test_validation_report_does_not_follow_late_symlink(project, tmp_path, monkeypatch):
    import srstudio.episode as episode_module

    root = tmp_path / 'project'
    shutil.copytree(project, root)
    ep = episode(root)
    ep.comp.add_group(id='duplicate')
    ep.comp.add_group(id='duplicate')
    source = root / 'dialogue.json'
    original = source.read_bytes()
    report = tmp_path / 'report.json'
    write = episode_module.write_outputs

    def swap(outputs, **kwargs):
        report.symlink_to(source)
        return write(outputs, **kwargs)

    monkeypatch.setattr(episode_module, 'write_outputs', swap)
    with pytest.raises(SceneCheckError):
        ep.finish(out=tmp_path / 'scene.xml', report=report)
    assert source.read_bytes() == original


@pytest.mark.parametrize('output', ['scene', 'report'])
def test_finish_rejects_output_directory_swapped_after_checks(project, tmp_path, monkeypatch, output):
    import srstudio.episode as episode_module

    root = tmp_path / 'project'
    shutil.copytree(project, root)
    ep = episode(root)
    source = root / 'dialogue.json'
    original = source.read_bytes()
    directory = tmp_path / 'export'
    directory.mkdir()
    selected = directory / 'dialogue.json'
    out = selected if output == 'scene' else tmp_path / 'scene.xml'
    report = selected if output == 'report' else tmp_path / 'report.json'
    write = episode_module.write_outputs

    def swap(outputs, **kwargs):
        directory.rename(tmp_path / 'original-export')
        directory.symlink_to(root, target_is_directory=True)
        return write(outputs, **kwargs)

    monkeypatch.setattr(episode_module, 'write_outputs', swap)
    with pytest.raises(OSError, match='directory'):
        ep.finish(out=out, report=report)
    assert source.read_bytes() == original


def test_finish_private_writes_private_scene_and_report(project, tmp_path):
    out = tmp_path / 'private' / 'scene.xml'
    report = tmp_path / 'private' / 'qa' / 'nested' / 'report.json'
    episode(project).finish(out=out, report=report, private=True)
    assert stat.S_IMODE(out.stat().st_mode) & 0o077 == 0
    assert stat.S_IMODE(report.stat().st_mode) & 0o077 == 0
    assert stat.S_IMODE(report.parent.stat().st_mode) & 0o077 == 0
    assert stat.S_IMODE(report.parent.parent.stat().st_mode) & 0o077 == 0


def test_directory_swap_during_install_cannot_redirect_output(project, tmp_path, monkeypatch):
    root = tmp_path / 'project'
    shutil.copytree(project, root)
    ep = episode(root)
    source = root / 'dialogue.json'
    original = source.read_bytes()
    directory = tmp_path / 'export'
    directory.mkdir()
    link = os.link
    swapped = False

    def swap(src, dst, *args, **kwargs):
        nonlocal swapped
        if dst == 'dialogue.json' and not swapped:
            swapped = True
            directory.rename(tmp_path / 'original-export')
            directory.symlink_to(root, target_is_directory=True)
        return link(src, dst, *args, **kwargs)

    monkeypatch.setattr(os, 'link', swap)
    with pytest.raises(OSError, match='directory'):
        ep.finish(out=directory / 'dialogue.json', report=tmp_path / 'report.json')
    assert swapped
    assert source.read_bytes() == original


def test_directory_move_reports_where_to_find_retained_backup(project, tmp_path, monkeypatch):
    root = tmp_path / 'project'
    shutil.copytree(project, root)
    source = root / 'dialogue.json'
    original = source.read_bytes()
    directory = tmp_path / 'export'
    moved = tmp_path / 'moved-export'
    directory.mkdir()
    (directory / 'dialogue.json').write_text('old output')
    link = os.link

    def swap(src, dst, *args, **kwargs):
        if src == 'new' and dst == 'dialogue.json':
            directory.rename(moved)
            directory.symlink_to(root, target_is_directory=True)
        return link(src, dst, *args, **kwargs)

    monkeypatch.setattr(os, 'link', swap)
    with pytest.raises(OSError, match='moved directory'):
        episode(root).finish(out=directory / 'dialogue.json', report=tmp_path / 'report.json')
    assert source.read_bytes() == original
    assert any(path.read_text() == 'old output' for path in moved.glob('.srstudio-output-*/old'))


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
