"""``srstudio catalog --json/--plugins`` and ``srstudio build`` for a script file and a module."""

import json
import runpy
import sys

import pytest

from srstudio import registry
from srstudio.cli import main

PLUGIN = '''
from srstudio import register


@register("graphic", "plugin-badge", summary="A badge registered by a plugin")
def plugin_badge(cv, parent):
    return None
'''

EPISODE = '''
import sys
from pathlib import Path

from _helper import MARK

Path(sys.argv[1], "built.txt").write_text(MARK + " " + __name__)
'''


@pytest.fixture
def isolated(monkeypatch, tmp_path):
    """Registry, sys.argv, sys.path and sys.modules restored after each test."""
    monkeypatch.setitem(registry._REGISTRY, "graphic", dict(registry._REGISTRY["graphic"]))
    monkeypatch.setattr(sys, "argv", list(sys.argv))
    monkeypatch.setattr(sys, "path", list(sys.path))
    before = set(sys.modules)
    yield tmp_path
    for name in set(sys.modules) - before:
        if name.startswith(("_helper", "plugin_", "episode_")):
            del sys.modules[name]


def test_catalog_json_lists_every_entry_with_its_facts(capsys):
    assert main(["catalog", "--json"]) == 0
    rows = json.loads(capsys.readouterr().out)
    assert len(rows) == len(registry.entries())
    assert {"kind": "graphic", "name": "quiz-card"}.items() <= next(r for r in rows if r["name"] == "quiz-card").items()


def test_catalog_imports_plugins_before_listing(isolated, capsys):
    (isolated / "plugin_badges.py").write_text(PLUGIN)
    sys.path.insert(0, str(isolated))
    assert main(["catalog", "--kind", "graphic", "--plugins", "plugin_badges"]) == 0
    line = next(ln for ln in capsys.readouterr().out.splitlines() if "plugin-badge" in ln)
    assert line.split()[:3] == ["graphic", "any", "plugin-badge"]
    assert line.endswith("A badge registered by a plugin")


def test_catalog_with_an_unknown_plugin_fails_loudly(isolated):
    with pytest.raises(ModuleNotFoundError):
        main(["catalog", "--plugins", "plugin_does_not_exist"])


def test_build_runs_a_script_with_its_root_and_sibling_helpers(isolated):
    scripts, root = isolated / "episodes", isolated / "project"
    scripts.mkdir()
    root.mkdir()
    (scripts / "_helper.py").write_text('MARK = "helper"\n')
    (scripts / "episode_demo.py").write_text(EPISODE)
    assert main(["build", str(scripts / "episode_demo.py"), str(root)]) == 0
    assert (root / "built.txt").read_text() == "helper __main__"


def test_build_runs_a_module_by_name(isolated):
    root = isolated / "project"
    root.mkdir()
    (isolated / "_helper.py").write_text('MARK = "module"\n')
    (isolated / "episode_mod.py").write_text(EPISODE)
    sys.path.insert(0, str(isolated))
    assert main(["build", "episode_mod", str(root)]) == 0
    assert (root / "built.txt").read_text() == "module __main__"


def test_build_without_a_root_hands_the_episode_only_its_own_path(isolated):
    """The episode then builds next to itself (episodes/_common.project_root), never into srstudio's own words."""
    script = isolated / "episode_argv.py"
    script.write_text("import json, sys\nopen(__file__ + '.json', 'w').write(json.dumps(sys.argv))\n")
    sys.argv = ["srstudio", "build", "--scripts", str(isolated), str(script)]
    assert main(sys.argv[1:]) == 0
    assert json.loads((isolated / "episode_argv.py.json").read_text()) == [str(script)]


def test_build_propagates_a_failing_episode(isolated):
    (isolated / "episode_broken.py").write_text("raise RuntimeError('scene check failed')\n")
    with pytest.raises(RuntimeError, match="scene check failed"):
        main(["build", str(isolated / "episode_broken.py")])


@pytest.mark.filterwarnings(
    "ignore:'srstudio.cli' found in sys.modules:RuntimeWarning"
)  # re-running an imported module
@pytest.mark.parametrize("module", ["srstudio", "srstudio.cli"])
def test_python_dash_m_exits_with_the_command_status(isolated, module, capsys):
    sys.argv = [module, "styles", "--json"]
    with pytest.raises(SystemExit) as stop:
        runpy.run_module(module, run_name="__main__", alter_sys=True)
    assert stop.value.code == 0
    slugs = [s["slug"] for s in json.loads(capsys.readouterr().out)]
    assert slugs == ["cutout", "ink", "soft", "cel", "stick", "toon", "saga", "collage", "gloss"]


def test_catalog_shows_the_measured_episodes_from_a_usage_report(tmp_path, capsys):
    from srstudio.usage import Report

    report = tmp_path / "usage.json"
    Report({"camera-off": ("pip",), "focus-mode": ("pip", "soft-desk")}).write(report)
    assert main(["catalog", "--kind", "character", "--usage", str(report)]) == 0
    line = next(ln for ln in capsys.readouterr().out.splitlines() if ln.split()[2] == "pip")
    assert "[camera-off,focus-mode]" in line
    assert main(["catalog", "--json", "--usage", str(report)]) == 0
    rows = {r["name"]: r for r in json.loads(capsys.readouterr().out)}
    assert rows["soft-desk"]["episodes"] == ["focus-mode"] and rows["juno"]["episodes"] == []


def test_catalog_without_usage_claims_no_episodes(capsys):
    assert main(["catalog", "--kind", "character"]) == 0
    assert all("[" not in ln for ln in capsys.readouterr().out.splitlines())
    assert main(["catalog", "--json"]) == 0
    assert all("episodes" not in r for r in json.loads(capsys.readouterr().out))
