"""Which registered parts each episode really uses: traced from the calls a build makes, not declared by hand."""

from __future__ import annotations

import json
import shutil
import sys
import types

import pytest

from srstudio import Episode, EpisodeSpec, blob, locations, parts, registry, specimens
from srstudio import usage as U
from srstudio.releases import Release
from srstudio.social import InstagramPost


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


def test_parts_made_by_one_factory_count_as_themselves_not_as_the_last_one_registered():
    gary, kai = (registry.get("character", f"collage-{name}").builder for name in ("gary", "kai"))
    assert gary.__code__ is kai.__code__  # one closure per look: the code object alone cannot tell them apart
    for drawer, name in ((gary, "collage-gary"), (kai, "collage-kai")):
        with U.trace() as used:
            try:
                drawer(None, None, (), 1.0)  # its own drawing runs (and fails on the dummy arguments)
            except Exception:
                pass
        assert used == {name}


def test_an_unregistered_closure_of_a_part_s_code_counts_as_no_part():
    gary = registry.get("character", "collage-gary").builder
    stranger = types.FunctionType(gary.__code__, gary.__globals__, closure=(types.CellType(object()),))
    with U.trace() as used:
        try:
            stranger(None, None, (), 1.0)
        except Exception:
            pass
    assert used == set()


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


def test_a_skipped_project_is_not_built_and_is_reported_unmeasured(tmp_path):
    scripts = tmp_path / "scripts"
    scripts.mkdir()
    for name in ("done_ep.py", "half_done.py"):
        (scripts / name).write_text("")
    episodes = tmp_path / "episodes"
    for slug in ("done-ep", "half-done"):
        (episodes / slug).mkdir(parents=True)
    runs, missing = U.discover(episodes, None, scripts, skip=("half-done",))
    assert [r.slug for r in runs] == ["done-ep"]
    assert missing == ["half-done"]
    with pytest.raises(U.UsageError, match="no-such-ep"):  # a mistyped skip is refused, never ignored
        U.discover(episodes, None, scripts, skip=("no-such-ep",))


def test_arguments_for_a_project_that_does_not_exist_are_refused(tmp_path):
    scripts = tmp_path / "scripts"
    scripts.mkdir()
    (scripts / "done_ep.py").write_text("")
    (tmp_path / "episodes" / "done-ep").mkdir(parents=True)
    runs, _ = U.discover(tmp_path / "episodes", None, scripts, args={"done-ep": ["--fast"]})
    assert runs[0].args == ("--fast",)
    with pytest.raises(U.UsageError, match="--arg names no project: done-epp"):  # a typo, never silently dropped
        U.discover(tmp_path / "episodes", None, scripts, args={"done-epp": ["--fast"]})


def test_the_command_skips_a_project_it_is_told_to(tmp_path, project, capsys):
    from srstudio import cli

    scripts = tmp_path / "scripts"
    scripts.mkdir()
    (scripts / "my_ep.py").write_text(
        "import sys\nfrom pathlib import Path\nfrom srstudio import Episode, EpisodeSpec, props\n"
        "ep = Episode(EpisodeSpec(slug='t', title='t', description='t', root=Path(sys.argv[1]), seed=1))\n"
        "props.plant(ep.cv, ep.comp)\n"
    )
    (scripts / "unfinished.py").write_text("raise SystemExit('no timeline.json yet')\n")
    episodes = tmp_path / "episodes"
    shutil.copytree(project, episodes / "my-ep")
    (episodes / "unfinished").mkdir()
    out = tmp_path / "usage.json"
    common = ["usage", "--episodes", str(episodes), "--scripts", str(scripts), "--work", str(tmp_path / "w")]
    assert cli.main([*common, "--out", str(out)]) == 2  # without the skip, the unfinished build stops it
    assert cli.main([*common, "--out", str(out), "--skip", "unfinished"]) == 0
    assert "not measured (skipped): unfinished" in capsys.readouterr().out
    report = U.Report.read(out)
    assert report.episodes == {"my-ep": ("plant",)} and report.unmeasured == ("unfinished",)
    assert cli.main([*common, "--out", str(out), "--skip", "typo"]) == 2


def test_a_release_names_the_builder_of_a_project_whose_script_is_not_its_slug(tmp_path):
    scripts = tmp_path / "scripts"
    (scripts / "posts").mkdir(parents=True)
    (scripts / "posts" / "__init__.py").write_text("")
    (scripts / "posts" / "scene.py").write_text(
        "from srstudio.releases import Release\nfrom srstudio.social import InstagramPost\n"
        'RELEASE = Release("scene", InstagramPost(title="T", description="D."), builder="printer_recreation")\n'
    )
    (scripts / "printer_recreation.py").write_text("")
    (scripts / "plain_ep.py").write_text("")
    episodes = tmp_path / "episodes"
    for slug in ("scene", "plain-ep"):
        (episodes / slug).mkdir(parents=True)
    runs, missing = U.discover(episodes, None, scripts)
    assert {r.slug: r.script.name for r in runs} == {"scene": "printer_recreation.py", "plain-ep": "plain_ep.py"}
    assert missing == []


def test_unreadable_releases_stop_the_discovery(tmp_path):
    scripts = tmp_path / "scripts"
    (scripts / "posts").mkdir(parents=True)
    (scripts / "posts" / "__init__.py").write_text("")
    (scripts / "posts" / "one.py").write_text("X = 1\n")
    (tmp_path / "episodes").mkdir()
    with pytest.raises(U.UsageError, match="RELEASE"):
        U.discover(tmp_path / "episodes", None, scripts)


def released(**pins):
    post = InstagramPost(title="T", description="D.")
    return {"a-b": Release("a-b", post, parts=pins.get("pins"))}


def test_every_measured_character_must_be_pinned_at_the_version_drawn():
    report = U.Report({"a-b": ("toon-bear", "toon-fox@2", "desk"), "not-released": ("toon-cat",)})
    assert report.pin_drift(released(pins={"toon-bear": 1, "toon-fox": 2})) == []
    assert report.pin_drift(released(pins={"toon-bear": 1, "toon-fox": 1})) == [
        "a-b: draws toon-fox version 2 but pins version 1"
    ]
    assert report.pin_drift(released()) == [
        "a-b: draws toon-bear version 1 but pins nothing for it",
        "a-b: draws toon-fox version 2 but pins nothing for it",
    ]


def test_a_release_built_by_another_script_is_matched_by_its_builder():
    post = InstagramPost(title="T", description="D.")
    release = Release("scene", post, builder="printer_recreation", parts={})
    assert U.Report({"printer-recreation": ("toon-bear",)}).pin_drift({"scene": release}) == [
        "printer-recreation: draws toon-bear version 1 but pins nothing for it"
    ]


def test_a_recorded_build_leaves_what_it_drew(project, tmp_path):
    ep = episode(project)
    with U.recorded(tmp_path):
        locations.reception(ep.cv, ep.comp)
    assert {"reception": 1, "reception-counter": 1, "slat-wall": 1}.items() <= parts.read_record(tmp_path).items()


def test_a_failed_build_leaves_no_record_of_an_older_one(tmp_path):
    parts.write_record(tmp_path, {"toon-fox": 1})
    with pytest.raises(RuntimeError), U.recorded(tmp_path):
        raise RuntimeError("the build stopped")
    assert parts.read_record(tmp_path) is None


@pytest.mark.parametrize(("code", "recorded"), [(0, True), (None, True), (3, False)])
def test_a_script_that_exits_is_recorded_only_if_it_succeeded(tmp_path, code, recorded):
    with pytest.raises(SystemExit), U.recorded(tmp_path):
        sys.exit(code)
    assert (parts.read_record(tmp_path) is not None) == recorded


def test_a_character_moving_its_head_counts_as_the_part_its_rig_belongs_to():
    with U.trace() as used:
        specimens.rig_digest("toon-fox", 2)
    assert "toon-fox@2" in used and "toon-fox" not in used
