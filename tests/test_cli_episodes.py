"""``srstudio build SLUG`` and ``srstudio record SLUG``: an episode named by its slug, its scripts found in the
episodes folder (by its release when it has one), and its own options passed through."""

import sys
import textwrap

import pytest

from srstudio.cli import main

BUILDER = """
import sys
from pathlib import Path

from _helper import MARK

Path(sys.argv[1], "built.txt").write_text(" ".join([MARK, Path(sys.argv[0]).name, *sys.argv[2:]]))
"""

RECORDER = """
import sys
from pathlib import Path


def main(argv=None):
    args = sys.argv[1:] if argv is None else argv
    Path(args[0], "recorded.txt").write_text(" ".join([Path(sys.argv[0]).name, *args[1:]]))
    if "--refuse" in args:
        raise SystemExit("set SRSTUDIO_ALLOW_CLOUD=1 to allow it")
    return 3 if "--fail" in args else 0


if __name__ == "__main__":
    sys.exit(main())
"""

RELEASE = """
from srstudio.releases import Release
from srstudio.social import InstagramPost

RELEASE = Release("scene", InstagramPost(title="T", description="D."), builder="printer_recreation")
"""


@pytest.fixture
def episodes(monkeypatch, tmp_path):
    """An episodes folder with a helper, a builder and a recorder for ``my-ep``, and a release that builds the
    ``scene`` project with ``printer_recreation.py``; argv, path and modules restored after each test. The
    operator's own ``SRSTUDIO_SCRIPTS`` is cleared: the folder is found from the working directory."""
    monkeypatch.delenv("SRSTUDIO_SCRIPTS", raising=False)
    monkeypatch.setattr(sys, "argv", list(sys.argv))
    monkeypatch.setattr(sys, "path", list(sys.path))
    before = set(sys.modules)
    folder = tmp_path / "episodes"
    (folder / "posts").mkdir(parents=True)
    (folder / "posts" / "__init__.py").write_text("")
    (folder / "posts" / "scene.py").write_text(textwrap.dedent(RELEASE))
    (folder / "_helper.py").write_text('MARK = "helper"\n')
    (folder / "my_ep.py").write_text(BUILDER)
    (folder / "printer_recreation.py").write_text(BUILDER)
    (folder / "my_ep_audio.py").write_text(RECORDER)
    (tmp_path / "project").mkdir()
    monkeypatch.chdir(tmp_path)
    yield tmp_path
    for name in set(sys.modules) - before:
        if name.startswith(("_helper", "my_ep", "printer_")):
            del sys.modules[name]


def test_build_finds_an_episode_by_its_slug_and_passes_its_options(episodes):
    assert main(["build", "my-ep", "project", "--voice"]) == 0
    assert (episodes / "project" / "built.txt").read_text() == "helper my_ep.py --voice"


def test_build_follows_the_release_to_a_builder_named_otherwise(episodes):
    assert main(["build", "scene", "project"]) == 0
    assert (episodes / "project" / "built.txt").read_text() == "helper printer_recreation.py"


def test_the_episodes_folder_can_be_named(episodes, monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path / "project")
    assert main(["build", "--scripts", str(episodes / "episodes"), "my-ep", str(episodes / "project")]) == 0
    assert (episodes / "project" / "built.txt").is_file()


def test_record_runs_the_episode_recorder_and_returns_its_status(episodes):
    assert main(["record", "my-ep", "project", "--key-stdin"]) == 0
    assert (episodes / "project" / "recorded.txt").read_text() == "my_ep_audio.py --key-stdin"
    assert main(["record", "my-ep", "project", "--fail"]) == 3


def test_record_shows_the_reason_a_recorder_exits_with(episodes, capsys):
    assert main(["record", "my-ep", "project", "--refuse"]) == 1
    assert capsys.readouterr().err == "set SRSTUDIO_ALLOW_CLOUD=1 to allow it\n"


@pytest.mark.parametrize("command", ["build", "record"])
def test_an_unknown_slug_is_refused(episodes, command, capsys):
    assert main([command, "no-such-ep", "project"]) == 2
    assert "no-such-ep" in capsys.readouterr().err


def test_record_refuses_an_episode_without_a_recorder(episodes, capsys):
    assert main(["record", "scene", "project"]) == 2
    assert "printer_recreation_audio.py" in capsys.readouterr().err
