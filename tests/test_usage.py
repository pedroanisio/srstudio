"""Which registered parts each episode really uses: traced from the calls a build makes, not declared by hand."""

from __future__ import annotations

import json
import shutil
import sys

import pytest

from srstudio import Episode, EpisodeSpec, blob, locations, registry
from srstudio import usage as U


def episode(project) -> Episode:
    return Episode(EpisodeSpec(slug="t", title="t", description="t", root=project, seed=1))


def test_trace_records_every_part_called_however_it_is_reached(project):
    ep = episode(project)
    with U.trace() as used:
        locations.reception(ep.cv, ep.comp)  # a location draws its props: they count as used too
        registry.get("prop", "chair")(ep.cv, ep.comp)  # through the registry
    assert {"reception", "reception-counter", "slat-wall", "globe-pendant", "chair"} <= used
    assert "soft-office" not in used


def test_a_class_part_counts_when_its_own_drawing_runs_not_when_it_is_looked_up():
    manager = registry.get("character", "manager").builder
    with U.trace() as used:
        assert manager.__name__ == "Manager"
    assert "manager" not in used
    with U.trace() as used:
        try:
            manager.draw_eyes(None, None, None)  # its own method runs (and fails on the dummy arguments)
        except Exception:
            pass
    assert used == {"manager"}


def test_trace_stops_recording_and_restores_the_profiler(project):
    before = sys.getprofile()
    with U.trace() as used:
        pass
    ep = episode(project)
    blob.office(ep.cv, ep.comp)
    assert used == set() and sys.getprofile() is before


def test_probe_runs_a_script_on_its_project_and_writes_what_it_used(tmp_path, project):
    script = tmp_path / "ep.py"
    script.write_text(
        "import sys\nfrom pathlib import Path\nfrom srstudio import Episode, EpisodeSpec, props\n"
        "root = Path(sys.argv[1])\n"
        "ep = Episode(EpisodeSpec(slug='t', title='t', description='t', root=root, seed=1))\n"
        "props.plant(ep.cv, ep.comp)\n"
        "(root / 'flag').write_text(' '.join(sys.argv[2:]))\n"
    )
    project = shutil.copytree(project, tmp_path / "project")
    out = tmp_path / "used.json"
    U.probe(script, project, ["--voice"], out)
    assert json.loads(out.read_text()) == ["plant"] and (project / "flag").read_text() == "--voice"


def test_measure_runs_each_episode_on_a_copy_and_reports_used_and_unused(tmp_path, project):
    script = tmp_path / "scripts" / "my_ep.py"
    script.parent.mkdir()
    script.write_text(
        "import sys\nfrom pathlib import Path\nfrom srstudio import Episode, EpisodeSpec, props\n"
        "root = Path(sys.argv[1])\n"
        "ep = Episode(EpisodeSpec(slug='t', title='t', description='t', root=root, seed=1))\n"
        "props.plant(ep.cv, ep.comp)\n"
        "(root / 'out.txt').write_text('built')\n"
    )
    project = shutil.copytree(project, tmp_path / "episodes" / "my-ep")
    report = U.measure([U.Run("my-ep", script, project)], tmp_path / "work")
    assert report.episodes == {"my-ep": ("plant",)}
    assert not (project / "out.txt").exists()  # built on a copy: the project is untouched
    parts = {p["name"]: p for p in report.to_dict()["parts"]}
    assert parts["plant"]["episodes"] == ["my-ep"] and parts["chair"]["episodes"] == []
    assert set(parts) == {e.name for e in registry.entries()}
    assert report.unused("prop") and "plant" not in report.unused("prop")


def test_a_failing_episode_stops_the_measurement_with_its_name(tmp_path):
    script = tmp_path / "broken.py"
    script.write_text("raise SystemExit('no inputs')\n")
    project = tmp_path / "p"
    project.mkdir()
    with pytest.raises(U.UsageError, match="broken-ep"):
        U.measure([U.Run("broken-ep", script, project)], tmp_path / "work")


def test_runs_are_found_from_projects_packages_and_the_scripts_folder(tmp_path):
    scripts = tmp_path / "scripts"
    scripts.mkdir()
    for name in ("off_and_on.py", "printer_recreation.py", "the_report.py"):
        (scripts / name).write_text("")
    episodes, packages = tmp_path / "episodes", tmp_path / "packages"
    for p in (
        episodes / "off-and-on",
        episodes / "the-report",
        episodes / "no-script",
        packages / "printer-recreation-1.0.0" / "project",
    ):
        p.mkdir(parents=True)
    runs, missing = U.discover(episodes, packages, scripts, args={"the-report": ("--voice",)})
    assert [(r.slug, r.script.name, r.args) for r in runs] == [
        ("off-and-on", "off_and_on.py", ()),
        ("printer-recreation", "printer_recreation.py", ()),
        ("the-report", "the_report.py", ("--voice",)),
    ]
    assert missing == ["no-script"]


def test_a_report_round_trips_and_refuses_an_unknown_schema(tmp_path):
    report = U.Report({"a": ("plant",)}, ("b",))
    path = tmp_path / "usage.json"
    report.write(path)
    assert U.Report.read(path) == report
    data = json.loads(path.read_text())
    data["schema"] = "9.0.0"
    path.write_text(json.dumps(data))
    with pytest.raises(U.UsageError, match="schema"):
        U.Report.read(path)


def test_the_command_writes_the_report_and_lists_the_unused_parts(tmp_path, project, capsys):
    from srstudio import cli

    scripts = tmp_path / "scripts"
    scripts.mkdir()
    (scripts / "my_ep.py").write_text(
        "import sys\nfrom pathlib import Path\nfrom srstudio import Episode, EpisodeSpec, props\n"
        "ep = Episode(EpisodeSpec(slug='t', title='t', description='t', root=Path(sys.argv[1]), seed=1))\n"
        "props.plant(ep.cv, ep.comp)\nassert sys.argv[2:] == ['--voice'], sys.argv\n"
    )
    episodes = tmp_path / "episodes"
    shutil.copytree(project, episodes / "my-ep")
    (episodes / "orphan").mkdir()
    out = tmp_path / "usage.json"
    common = ["usage", "--episodes", str(episodes), "--scripts", str(scripts), "--work", str(tmp_path / "w")]
    assert cli.main([*common, "--out", str(out), "--arg", "my-ep=--voice"]) == 0
    printed = capsys.readouterr().out
    assert "not measured (no script): orphan" in printed and "prop:" in printed
    assert U.Report.read(out).episodes == {"my-ep": ("plant",)}
    with pytest.raises(SystemExit):
        cli.main([*common, "--out", str(out), "--arg", "my-ep"])
    assert cli.main([*common, "--out", str(out)]) == 2  # the script refuses to run without its option
