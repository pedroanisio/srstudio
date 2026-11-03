"""``srstudio catalog --json/--plugins`` and ``srstudio build`` for a script file and a module."""

import json
import runpy
import sys
from dataclasses import replace
from pathlib import Path

import pytest

from srstudio import parts, registry, releases
from srstudio import usage as U
from srstudio.cli import main
from srstudio.releases import Release, Tags
from srstudio.social import InstagramPost

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


@pytest.mark.parametrize("args", [["--kind", "prop"], ["--kind", "character", "--style", "toon"]])
def test_catalog_json_lists_the_same_parts_as_the_text_listing(capsys, args):
    assert main(["catalog", *args]) == 0
    shown = [ln.split()[2] for ln in capsys.readouterr().out.splitlines()]
    assert main(["catalog", *args, "--json"]) == 0
    assert [r["name"] for r in json.loads(capsys.readouterr().out)] == shown


def test_catalog_imports_plugins_before_listing(isolated, capsys):
    (isolated / "plugin_badges.py").write_text(PLUGIN)
    sys.path.insert(0, str(isolated))
    assert main(["catalog", "--kind", "graphic", "--plugins", "plugin_badges"]) == 0
    line = next(ln for ln in capsys.readouterr().out.splitlines() if "plugin-badge" in ln)
    assert line.split()[:3] == ["graphic", "any", "plugin-badge"]
    assert line.endswith("A badge registered by a plugin")


def test_catalog_with_an_unknown_plugin_fails_loudly(isolated, capsys):
    assert main(["catalog", "--plugins", "plugin_does_not_exist"]) == 2
    assert "plugin_does_not_exist" in capsys.readouterr().err


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


def test_build_exits_1_with_the_findings_of_a_scene_that_fails_its_check(isolated, capsys):
    script = isolated / "episode_unchecked.py"
    script.write_text("from srstudio.episode import SceneCheckError\nraise SceneCheckError(['error: dup id'])\n")
    assert main(["build", str(script)]) == 1
    assert capsys.readouterr().err == "error: dup id\n"


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


def test_parts_lists_every_version_and_the_default(capsys):
    assert main(["parts"]) == 0
    out = capsys.readouterr().out
    fox = next(line for line in out.splitlines() if line.startswith("toon-fox "))
    assert fox.split() == ["toon-fox", "character", "toon", "2", "1,2"]
    assert "toon-bear " in out


def only_proposed(monkeypatch):
    bear = parts.get("toon-bear")
    version = replace(bear.versions[0], status="proposed", approval=None, proof="", drawing="")
    table = {**parts.load(), "toon-bear": replace(bear, versions=(version,))}
    monkeypatch.setattr(parts, "load", lambda: table)


def test_parts_lists_a_part_with_no_approved_version_without_a_default(capsys, monkeypatch):
    only_proposed(monkeypatch)
    assert main(["parts"]) == 0
    bear = next(line for line in capsys.readouterr().out.splitlines() if line.startswith("toon-bear "))
    assert bear.split() == ["toon-bear", "character", "toon", "-", "1?"]


def test_parts_json_gives_a_part_with_no_approved_version_no_default(capsys, monkeypatch):
    only_proposed(monkeypatch)
    assert main(["parts", "--json"]) == 0
    assert json.loads(capsys.readouterr().out)["toon-bear"]["default"] is None


def test_parts_json_is_the_table(capsys):
    assert main(["parts", "--json"]) == 0
    table = json.loads(capsys.readouterr().out)
    fox = table["toon-fox"]
    assert fox["default"] == 2 and [v["number"] for v in fox["versions"]] == [1, 2]
    assert fox["versions"][1]["approval"]["date"] == "2026-10-30"
    assert fox["versions"][0]["approval"] is None


def test_parts_lists_a_part_with_nothing_approved_and_no_default(capsys, monkeypatch):
    fresh = parts.Version(1, "2026-10-30", "First drawing.", "proposed", "", "")
    table = {"desk-lamp": parts.Part("desk-lamp", "prop", "cutout", (fresh,))}
    monkeypatch.setattr(parts, "load", lambda: table)
    assert main(["parts"]) == 0
    listed = capsys.readouterr().out.split()
    assert listed == ["desk-lamp", "prop", "cutout", "-", "1?"]
    assert main(["parts", "--json"]) == 0
    assert json.loads(capsys.readouterr().out)["desk-lamp"]["default"] is None


@pytest.mark.parametrize(("name", "number"), [("toon-fox", 1), ("toon-fox@2", 2)])
def test_parts_digest_prints_what_a_new_record_needs(name, number, capsys):
    assert main(["parts", "--digest", name]) == 0
    assert capsys.readouterr().out.strip() == parts.get("toon-fox").version(number).drawing


@pytest.mark.parametrize(("name", "match"), [("nobody", "no part 'nobody'"), ("toon-fox@9", "no version 9")])
def test_parts_digest_refuses_what_it_does_not_know(name, match, capsys):
    assert main(["parts", "--digest", name]) == 2
    assert match in capsys.readouterr().err


def pins_folder(tmp_path, pins: str) -> Path:
    posts = tmp_path / "posts"
    posts.mkdir(exist_ok=True)
    (posts / "__init__.py").write_text("")
    (posts / "a_b.py").write_text(
        "from srstudio.releases import Release\nfrom srstudio.social import InstagramPost\n"
        f'RELEASE = Release("a-b", InstagramPost(title="T", description="D."), parts={pins})\n'
    )
    return tmp_path


def usage_report(tmp_path, parts) -> Path:
    report = U.Report({"a-b": tuple(parts)})
    return report.write(tmp_path / "usage.json")


def test_parts_usage_passes_when_every_measured_character_is_pinned(tmp_path, capsys):
    folder = pins_folder(tmp_path, '{"toon-bear": 1}')
    args = ["parts", "--usage", str(usage_report(tmp_path, ["toon-bear"])), "--scripts", str(folder)]
    assert main(args) == 0
    assert "1 episodes measured, every part pinned" in capsys.readouterr().out


def test_parts_usage_fails_on_a_measured_character_with_no_pin(tmp_path, capsys):
    folder = pins_folder(tmp_path, "{}")
    args = ["parts", "--usage", str(usage_report(tmp_path, ["toon-bear"])), "--scripts", str(folder)]
    assert main(args) == 1
    assert "a-b: draws toon-bear version 1 but pins nothing for it" in capsys.readouterr().out


def test_parts_usage_refuses_a_folder_with_no_releases(tmp_path, capsys):
    assert main(["parts", "--usage", str(usage_report(tmp_path, [])), "--scripts", str(tmp_path)]) == 2
    assert "srstudio parts:" in capsys.readouterr().err


def test_parts_usage_reports_an_unreadable_report(tmp_path, capsys):
    folder = pins_folder(tmp_path, "{}")
    (tmp_path / "bad.json").write_text("not json")
    assert main(["parts", "--usage", str(tmp_path / "bad.json"), "--scripts", str(folder)]) == 2
    assert "srstudio parts:" in capsys.readouterr().err


def test_parts_refused_lists_each_part_with_no_drawing_and_why(capsys):
    assert main(["parts", "--refused"]) == 0
    lines = capsys.readouterr().out.splitlines()
    assert len(lines) == sum(1 for p in parts.load().values() if p.refused)
    assert any(line.startswith("captions: overlay: ") for line in lines)


def test_arms_prints_the_split_and_fails_on_a_lopsided_one(tmp_path, monkeypatch, capsys):
    post = InstagramPost(title="A title", description="A description.")
    split = {"p": "a", "q": "b", "r": "a"}
    tagged = {s: Tags("family", "protagonist", "recognition", test="sp-hook_motion", arm=a) for s, a in split.items()}
    run = {slug: Release(f"{slug}-x", post, tags=tag) for slug, tag in tagged.items()}
    monkeypatch.setattr(releases, "load", lambda folder: run)
    assert main(["arms", "sp-hook_motion", "--scripts", str(tmp_path)]) == 1
    out = capsys.readouterr()
    assert "a   2  p r" in out.out and "arm a has 2 and arm b has 1" in out.err
    del run["r"]
    order = tmp_path / "order.txt"
    order.write_text("p\nq\n")
    assert main(["arms", "sp-hook_motion", "--scripts", str(tmp_path), "--order", str(order)]) == 0


def test_arms_reads_a_declared_share_and_refuses_an_impossible_one(tmp_path, monkeypatch, capsys):
    post = InstagramPost(title="A title", description="A description.")
    split = {"p": "a", "q": "b", "r": "b", "s": "b", "t": "b"}
    tagged = {s: Tags("family", "protagonist", "recognition", test="sp-hook_motion", arm=a) for s, a in split.items()}
    run = {slug: Release(f"{slug}-x", post, tags=tag) for slug, tag in tagged.items()}
    monkeypatch.setattr(releases, "load", lambda folder: run)
    assert main(["arms", "sp-hook_motion", "--scripts", str(tmp_path), "--share", "0.2"]) == 0
    capsys.readouterr()
    assert main(["arms", "sp-hook_motion", "--scripts", str(tmp_path), "--share", "1"]) == 1
    assert "share" in capsys.readouterr().err
