"""An installed package can scaffold and check a project without a repository or system font."""

import json
import os
import subprocess
import sys
from importlib.resources import files

from srstudio import sample
from srstudio.cli import main


def test_init_bundles_a_font_and_builds_from_another_directory(tmp_path, monkeypatch, capsys):
    monkeypatch.setattr(sample, 'SYSTEM_FONTS', ())
    root = tmp_path / 'my-first-episode'
    assert main(['init', str(root), '--json']) == 0
    result = json.loads(capsys.readouterr().out)
    assert result['root'] == str(root)
    assert (root / 'assets/DejaVuSans-Bold.ttf').read_bytes() == files('srstudio').joinpath(
        'assets/fonts/DejaVuSans-Bold.ttf'
    ).read_bytes()
    assert (root / 'assets/FONT-LICENSE.txt').read_text() == sample.dejavu_license()
    built = subprocess.run(
        [sys.executable, str(root / 'build.py')], cwd=tmp_path, capture_output=True, text=True, timeout=30
    )
    assert built.returncode == 0, built.stdout + built.stderr
    assert (root / 'my-first-episode.scene.xml').is_file()
    assert json.loads((root / 'sdk-validation.json').read_text()) == []


def test_init_refuses_existing_artifacts_without_partial_changes(tmp_path, capsys):
    root = tmp_path / 'demo'
    root.mkdir()
    (root / 'build.py').write_text('my custom builder')
    assert main(['init', str(root), '--json']) == 2
    assert json.loads(capsys.readouterr().err)['remedy']
    assert sorted(p.name for p in root.iterdir()) == ['build.py']
    assert (root / 'build.py').read_text() == 'my custom builder'
    assert main(['init', str(root), '--overwrite', '--json']) == 0
    assert (root / 'build.py').read_text() != 'my custom builder'


def test_init_invalid_font_leaves_no_project(tmp_path, capsys):
    font = tmp_path / 'bad.ttf'
    font.write_bytes(b'not a font')
    root = tmp_path / 'demo'
    assert main(['init', str(root), '--font', str(font), '--json']) == 2
    assert json.loads(capsys.readouterr().err)['path'] == 'font'
    assert not root.exists()


def test_doctor_distinguishes_build_from_render_readiness(tmp_path, monkeypatch, capsys):
    monkeypatch.setenv('PATH', '')
    monkeypatch.delenv('SRSTUDIO_ENGINE', raising=False)
    monkeypatch.setattr(sample, 'SYSTEM_FONTS', ())
    assert main(['doctor', '--json']) == 1
    report = json.loads(capsys.readouterr().out)
    assert report['ready_to_build'] is True
    assert report['ready_to_render'] is False
    engine = next(c for c in report['checks'] if c['name'] == 'engine')
    assert engine['remedy']
    executable = tmp_path / 'scene-render'
    executable.write_text('#!/bin/sh\necho scene-render-test\n')
    executable.chmod(0o755)
    assert main(['doctor', '--engine', str(executable), '--json']) == 0
    report = json.loads(capsys.readouterr().out)
    assert report['ready_to_render'] is True
    assert next(c for c in report['checks'] if c['name'] == 'engine')['path'] == str(executable)


def test_doctor_refuses_a_nonexecutable_engine(tmp_path, capsys):
    executable = tmp_path / 'scene-render'
    executable.write_text('not executable')
    assert not os.access(executable, os.X_OK)
    assert main(['doctor', '--engine', str(executable), '--json']) == 1
    assert json.loads(capsys.readouterr().out)['ready_to_render'] is False
