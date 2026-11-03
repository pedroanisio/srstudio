"""The engine comes out of its published image: checked against its tag, smoke-rendered, installed once (ADR 0224)."""

import importlib.util
import json
import os
import stat
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("engine_install", ROOT / "tools" / "engine_install.py")
assert spec is not None and spec.loader is not None
engine_install = importlib.util.module_from_spec(spec)
sys.modules["engine_install"] = engine_install
spec.loader.exec_module(engine_install)

COMMIT = "af179e456d29f5bbc82c86187cccd620cf0e3124"
DIGEST = "pedroanisio/scene-render@sha256:" + "8" * 64
SOURCE = "https://github.com/pedroanisio/scene-render.git"


class Docker:
    """Stands in for subprocess.run: a registry holding one image, a GitHub tag, and the engine copied out of it."""

    def __init__(self, *, version="0.9.0", commit=COMMIT, tag_commit=COMMIT, smoke_code=0, cp_code=0):
        self.version, self.commit, self.tag_commit = version, commit, tag_commit
        self.smoke_code, self.cp_code, self.calls = smoke_code, cp_code, []

    def __call__(self, argv, **kwargs):
        argv = [str(a) for a in argv]
        self.calls.append(argv)
        out, code = "", 0
        if argv[:2] == ["docker", "image"]:
            out = json.dumps({"digest": DIGEST, "source": SOURCE}) + "\n"
        elif argv[:2] == ["docker", "create"]:
            out = "c0ffee\n"
        elif argv[:2] == ["docker", "cp"]:
            code = self.cp_code
            if not code:
                target = Path(argv[3])
                if argv[2].endswith("/COMMIT"):
                    target.write_text(self.commit + "\n")
                else:
                    target.write_text("#!/bin/sh\n")
                    target.chmod(0o755)
        elif argv[:2] == ["git", "ls-remote"]:
            out = f"{'1' * 40}\trefs/tags/v0.9.0\n{self.tag_commit}\trefs/tags/v0.9.0^{{}}\n"
        elif argv[0].endswith("/scene-render") and argv[1] == "--version":
            out = f"scene-render {self.version}\n"
        elif argv[0].endswith("/scene-render") and argv[1] == "render":
            code = self.smoke_code
            if not code:
                Path(argv[argv.index("-o") + 1]).write_bytes(b"\x89PNG")
        return subprocess.CompletedProcess(argv, code, out, "smoke failed" if code else "")

    def ran(self, *words):
        return [c for c in self.calls if c[: len(words)] == list(words)]


def test_install_copies_the_engine_out_of_its_image_and_records_where_it_came_from(tmp_path):
    docker = Docker()
    installed = engine_install.install("0.9.0", bin_dir=tmp_path, run=docker)

    assert installed == tmp_path / "scene-render-v0.9.0"
    assert docker.ran("docker", "pull", "-q", "pedroanisio/scene-render:0.9.0")
    record = json.loads((installed / "engine.json").read_text())
    assert record == {
        "schema_version": "1.0.0",
        "version": "0.9.0",
        "image": "pedroanisio/scene-render:0.9.0",
        "digest": DIGEST,
        "commit": COMMIT,
        "source": SOURCE,
    }
    assert stat.S_IMODE(installed.stat().st_mode) == 0o700
    assert stat.S_IMODE((installed / "scene-render").stat().st_mode) == 0o700
    assert stat.S_IMODE((installed / "engine.json").stat().st_mode) == 0o600
    assert docker.ran("docker", "rm", "-f", "c0ffee")
    assert not (tmp_path / "scene-render").exists(), "installing never switches the engine in use"
    assert [p.name for p in tmp_path.iterdir()] == ["scene-render-v0.9.0"], "the stage is gone"


def test_activate_points_the_engine_link_at_the_installed_version_atomically(tmp_path):
    old = tmp_path / "scene-render-v0.8.0"
    old.mkdir()
    (tmp_path / "scene-render").symlink_to("scene-render-v0.8.0/scene-render")

    engine_install.install("0.9.0", bin_dir=tmp_path, run=Docker(), activate=True)

    assert os.readlink(tmp_path / "scene-render") == "scene-render-v0.9.0/scene-render"
    assert old.is_dir(), "the previous engine stays for a switch back"


@pytest.mark.parametrize(
    ("docker", "says"),
    [
        (Docker(version="0.8.0"), "reports scene-render 0.8.0"),
        (Docker(tag_commit="2" * 40), "tag v0.9.0 is " + "2" * 40),
        (Docker(commit="not a commit"), "commit"),
        (Docker(smoke_code=1), "smoke render failed"),
        (Docker(cp_code=1), "docker cp"),
    ],
)
def test_an_engine_that_fails_a_check_is_never_installed_and_its_container_is_removed(tmp_path, docker, says):
    with pytest.raises(engine_install.EngineInstallError, match=says):
        engine_install.install("0.9.0", bin_dir=tmp_path, run=docker, activate=True)

    assert list(tmp_path.iterdir()) == []
    assert docker.ran("docker", "rm", "-f", "c0ffee")


def test_an_installed_version_is_never_replaced_by_a_different_image(tmp_path):
    engine_install.install("0.9.0", bin_dir=tmp_path, run=Docker())
    record = tmp_path / "scene-render-v0.9.0" / "engine.json"
    record.write_text(json.dumps({**json.loads(record.read_text()), "digest": "other@sha256:" + "0" * 64}))

    with pytest.raises(engine_install.EngineInstallError, match="already holds another image"):
        engine_install.install("0.9.0", bin_dir=tmp_path, run=Docker())


def test_the_same_image_again_only_activates_what_is_installed(tmp_path):
    engine_install.install("0.9.0", bin_dir=tmp_path, run=Docker())
    again = Docker()

    engine_install.install("0.9.0", bin_dir=tmp_path, run=again, activate=True)

    assert not again.ran("docker", "create")
    assert os.readlink(tmp_path / "scene-render") == "scene-render-v0.9.0/scene-render"


def test_activate_refuses_an_engine_path_that_is_not_a_link(tmp_path):
    (tmp_path / "scene-render").write_text("a real binary someone put here")

    with pytest.raises(engine_install.EngineInstallError, match="not a symbolic link"):
        engine_install.install("0.9.0", bin_dir=tmp_path, run=Docker(), activate=True)

    assert (tmp_path / "scene-render").read_text() == "a real binary someone put here"


@pytest.mark.parametrize("version", ["v0.9.0", "0.9", "latest", "0.9.0; rm -rf /"])
def test_a_version_is_three_numbers(tmp_path, version):
    with pytest.raises(engine_install.EngineInstallError, match="major.minor.patch"):
        engine_install.install(version, bin_dir=tmp_path, run=Docker())


def test_main_installs_and_reports_the_engine(tmp_path, capsys):
    code = engine_install.main(["0.9.0", "--bin-dir", str(tmp_path), "--activate"], run=Docker())

    assert code == 0
    assert "scene-render 0.9.0" in capsys.readouterr().out
    assert (tmp_path / "scene-render").is_symlink()


def test_main_names_the_failure_and_exits_one(tmp_path, capsys):
    assert engine_install.main(["0.9.0", "--bin-dir", str(tmp_path)], run=Docker(smoke_code=1)) == 1
    assert "smoke render failed" in capsys.readouterr().err


def test_the_smoke_render_holds_the_gpu_lock(tmp_path, monkeypatch):
    """The smoke render opens the GPU like any render, so it runs inside ``gpu.held()`` (ADR 0171)."""
    from srstudio import gpu

    lock = tmp_path / "gpu.lock"
    monkeypatch.setenv(gpu.LOCK_ENV, str(lock))
    docker, holding = Docker(), []

    def run(argv, **kwargs):
        if str(argv[0]).endswith("/scene-render") and argv[1] == "render":
            holding.append([h.pid for h in gpu.holders(lock) if not h.waiting])
        return docker(argv, **kwargs)

    engine_install.install("0.9.0", bin_dir=tmp_path / "bin", run=run)

    assert holding == [[os.getpid()]]
