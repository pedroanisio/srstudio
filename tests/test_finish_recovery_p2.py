"""Output permissions, concurrent modifications and actionable validation failures."""

import os
import stat
from pathlib import Path

import pytest

from srstudio import Episode, EpisodeSpec, signature
from srstudio._outputs import write_outputs
from srstudio.episode import SceneCheckError


def make_episode(project, *, signed=False):
    return Episode(EpisodeSpec(slug='x', title='x', description='x', root=project, seed=1, signature=signed))


def test_finish_keeps_existing_output_permissions(project, tmp_path):
    out, report = tmp_path / 'scene.xml', tmp_path / 'report.json'
    for path in (out, report):
        path.write_text('old')
        path.chmod(0o600)
    previous = os.umask(0o022)
    try:
        make_episode(project).finish(out=out, report=report)
    finally:
        os.umask(previous)
    assert [stat.S_IMODE(path.stat().st_mode) for path in (out, report)] == [0o600, 0o600]


def test_finish_preserves_symlink_target_permissions(project, tmp_path):
    target = tmp_path / 'target.xml'
    target.write_text('old')
    target.chmod(0o600)
    out = tmp_path / 'scene.xml'
    out.symlink_to(target)
    make_episode(project).finish(out=out, report=tmp_path / 'report.json')
    assert out.is_symlink()
    assert stat.S_IMODE(target.stat().st_mode) == 0o600


@pytest.mark.parametrize('update', ['other', 'other writer update'])
def test_no_overwrite_rollback_preserves_concurrent_in_place_edit(tmp_path, monkeypatch, update):
    out, report = tmp_path / 'scene.xml', tmp_path / 'report.json'
    original_link = os.link

    def race(source, destination, *args, **kwargs):
        if Path(destination) == report:
            out.write_text(update)
            report.write_text('other writer report')
        return original_link(source, destination, *args, **kwargs)

    monkeypatch.setattr(os, 'link', race)
    with pytest.raises(FileExistsError, match='preserved'):
        write_outputs([(out, b'scene'), (report, b'report')], overwrite=False)
    assert out.read_text() == update
    assert report.read_text() == 'other writer report'


def test_existing_report_does_not_mask_scene_findings(project, tmp_path):
    ep = make_episode(project)
    ep.comp.add_group(id='duplicate')
    ep.comp.add_group(id='duplicate')
    report = tmp_path / 'report.json'
    report.write_text('old report')
    with pytest.raises(SceneCheckError) as caught:
        ep.finish(out=tmp_path / 'scene.xml', report=report, overwrite=False)
    assert caught.value.findings
    assert isinstance(caught.value.__cause__, FileExistsError)
    assert 'validation report could not be written' in str(caught.value)
    assert report.read_text() == 'old report'


def test_existing_report_does_not_mask_signature_error(project, tmp_path):
    ep = make_episode(project, signed=True)
    report = tmp_path / 'report.json'
    report.write_text('old report')
    with pytest.raises(signature.SignatureError) as caught:
        ep.finish(out=tmp_path / 'scene.xml', report=report, overwrite=False)
    assert isinstance(caught.value.__cause__, FileExistsError)
    assert 'validation report could not be written' in str(caught.value)
    assert report.read_text() == 'old report'
