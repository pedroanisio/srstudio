"""Do not discard ambiguous takes or other writers' output during recovery."""

import json
import os
from pathlib import Path

import pytest

from srstudio import Episode, EpisodeSpec, Timeline
from srstudio._outputs import write_outputs
from srstudio.timeline import TimelineError


@pytest.mark.parametrize('loader', ['dict', 'file', 'episode'])
def test_ambiguous_timeline_reports_both_formats(project, tmp_path, loader):
    data = {
        'duration': 1,
        'phrases': [{'role': 'a', 'text': 'hello', 'start': 0, 'end': 1}],
        'items': [
            {
                'id': '1',
                'actor': 'b',
                'shot': 'wide',
                'text': 'bye',
                'start': 0,
                'duration': 1,
                'audio': 'assets/dialogue.wav',
            }
        ],
    }
    with pytest.raises(TimelineError, match=r'phrases.*items|items.*phrases'):
        if loader == 'dict':
            Timeline.from_dict(data)
        elif loader == 'file':
            path = tmp_path / 'timeline.json'
            path.write_text(json.dumps(data))
            Timeline.load(path)
        else:
            import shutil

            root = tmp_path / 'project'
            shutil.copytree(project, root)
            (root / 'dialogue.json').write_text(json.dumps(data))
            Episode(EpisodeSpec(slug='x', title='x', description='x', root=root, seed=1, audio=None))


def test_overwrite_failure_keeps_concurrent_scene_and_prior_backup(tmp_path, monkeypatch):
    scene, report = tmp_path / 'scene.xml', tmp_path / 'report.json'
    scene.write_text('old scene')
    report.write_text('old report')
    link = os.link
    failed = False

    def race(source, destination, *args, **kwargs):
        nonlocal failed
        if Path(destination) == report and Path(source).name == 'new' and not failed:
            failed = True
            scene.write_text('concurrent update')
            raise OSError('report install failed')
        return link(source, destination, *args, **kwargs)

    monkeypatch.setattr(os, 'link', race)
    with pytest.raises(OSError, match='backup'):
        write_outputs([(scene, b'new scene'), (report, b'new report')], overwrite=True)
    assert scene.read_text() == 'concurrent update'
    assert report.read_text() == 'old report'
    assert any(p.read_text() == 'old scene' for p in tmp_path.glob('.srstudio-output-*/old'))


def test_overwrite_preserves_file_created_after_backup(tmp_path, monkeypatch):
    scene, report = tmp_path / 'scene.xml', tmp_path / 'report.json'
    scene.write_text('old scene')
    replace = os.replace

    def race(source, destination):
        result = replace(source, destination)
        if Path(source) == scene and Path(destination).name == 'old':
            scene.write_text('concurrent update')
        return result

    monkeypatch.setattr(os, 'replace', race)
    with pytest.raises(FileExistsError, match='backup'):
        write_outputs([(scene, b'new scene'), (report, b'new report')], overwrite=True)
    assert scene.read_text() == 'concurrent update'
    assert any(p.read_text() == 'old scene' for p in tmp_path.glob('.srstudio-output-*/old'))


def test_overwrite_recovery_preserves_concurrent_report_and_both_backups(tmp_path, monkeypatch):
    scene, report = tmp_path / 'scene.xml', tmp_path / 'report.json'
    scene.write_text('old scene')
    report.write_text('old report')
    link = os.link

    def race(source, destination, *args, **kwargs):
        if Path(destination) == report and Path(source).name == 'new':
            report.write_text('concurrent report')
        return link(source, destination, *args, **kwargs)

    monkeypatch.setattr(os, 'link', race)
    with pytest.raises(FileExistsError, match='backup') as caught:
        write_outputs([(scene, b'new scene'), (report, b'new report')], overwrite=True)
    assert scene.read_text() == 'new scene'
    assert report.read_text() == 'concurrent report'
    backups = list(tmp_path.glob('.srstudio-output-*/old'))
    assert {p.read_text() for p in backups} == {'old scene', 'old report'}
    assert all(str(path) in str(caught.value) for path in backups)


def test_no_overwrite_collision_never_unlinks_published_output(tmp_path, monkeypatch):
    scene, report = tmp_path / 'scene.xml', tmp_path / 'report.json'
    link = os.link
    unlink = Path.unlink

    def collide(source, destination, *args, **kwargs):
        if Path(destination) == report:
            report.write_text('concurrent report')
        return link(source, destination, *args, **kwargs)

    def late_write(path, *args, **kwargs):
        if path == scene:
            path.write_text('late concurrent update')
        return unlink(path, *args, **kwargs)

    monkeypatch.setattr(os, 'link', collide)
    monkeypatch.setattr(Path, 'unlink', late_write)
    with pytest.raises(FileExistsError, match='preserved'):
        write_outputs([(scene, b'new scene'), (report, b'new report')], overwrite=False)
    assert scene.read_text() == 'new scene'
    assert report.read_text() == 'concurrent report'
