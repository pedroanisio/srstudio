"""Which registered parts each episode really uses: traced from the calls a build makes, not declared by hand."""

from __future__ import annotations

import json
import shutil
import sys
import types
import xml.etree.ElementTree as ET

import pytest

from srstudio import Episode, EpisodeSpec, blob, figure_record, locations, parts, registry, specimens
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


PLANTS = (
    "import sys\nfrom pathlib import Path\nfrom srstudio import Episode, EpisodeSpec, props\n"
    "ep = Episode(EpisodeSpec(slug='t', title='t', description='t', root=Path(sys.argv[1]), seed=1))\n"
    "props.plant(ep.cv, ep.comp)\n"
)


def test_a_failing_episode_is_reported_unmeasured_and_cannot_abort_the_others(tmp_path, project):
    broken = tmp_path / "broken.py"
    broken.write_text("raise SystemExit('no inputs')\n")
    good = tmp_path / "good.py"
    good.write_text(PLANTS)
    empty = tmp_path / "p"
    empty.mkdir()
    runs = [U.Run("broken-ep", broken, empty), U.Run("good-ep", good, project)]
    report = U.measure(runs, tmp_path / "work")
    assert report.episodes == {"good-ep": ("plant",)}
    assert report.unmeasured == ("broken-ep",)
    assert "broken.py failed" in report.failures["broken-ep"] and "no inputs" in report.failures["broken-ep"]
    assert report.to_dict()["unmeasured"] == ["broken-ep"]  # the page marks it "not measured", never "uses nothing"
    assert U.Report.read(report.write(tmp_path / "usage.json")).unmeasured == ("broken-ep",)


def test_a_run_where_every_episode_fails_measures_nothing_and_says_so(tmp_path):
    """An environment that cannot build at all (a broken import) must not replace a good report with an empty one."""
    broken = tmp_path / "broken.py"
    broken.write_text("raise SystemExit('no inputs')\n")
    empty = tmp_path / "p"
    empty.mkdir()
    runs = [U.Run("one", broken, empty), U.Run("two", broken, empty)]
    with pytest.raises(U.UsageError, match="every episode failed.*one.*two"):
        U.measure(runs, tmp_path / "work")


def test_a_voiced_recording_means_the_episode_is_measured_from_it(tmp_path):
    """An episode's ``script.json`` can be the silent timing of an older sketch while the delivered master is built from
    ``voiced/``, so the silent build refuses to run: the measure follows the recording the project already has."""
    scripts = tmp_path / "scripts"
    scripts.mkdir()
    (scripts / "voiced_ep.py").write_text("# python3 voiced_ep.py PROJECT --voice\n")
    (scripts / "silent_ep.py").write_text("# python3 silent_ep.py PROJECT\n")
    (scripts / "no_flag_ep.py").write_text("# takes no options\n")
    (scripts / "named_ep.py").write_text("# python3 named_ep.py PROJECT --voice\n")
    episodes = tmp_path / "episodes"
    for slug in ("voiced-ep", "silent-ep", "no-flag-ep", "named-ep"):
        (episodes / slug).mkdir(parents=True)
    (episodes / "voiced-ep" / "voiced").mkdir()
    (episodes / "no-flag-ep" / "voiced").mkdir()
    (episodes / "named-ep" / "voiced").mkdir()
    runs, _ = U.discover(episodes, None, scripts, args={"named-ep": ("--voice",)})
    assert {r.slug: r.args for r in runs} == {
        "voiced-ep": ("--voice",),  # a recording and a script that takes --voice
        "silent-ep": (),  # no recording
        "no-flag-ep": (),  # a recording, but the script does not take --voice
        "named-ep": ("--voice",),  # an option given by name is not added twice
    }


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


def test_pilots_are_measured_from_their_series_folders_and_the_pilots_folder_is_no_project(tmp_path):
    scripts = tmp_path / "scripts"
    (scripts / "pilots").mkdir(parents=True)
    for name in ("off_and_on.py", "pilots/real_roast.py", "pilots/further_north.py"):
        (scripts / name).write_text("")
    episodes = tmp_path / "episodes"
    for p in (
        episodes / "off-and-on",
        episodes / "pilots" / "news" / "real-roast",
        episodes / "pilots" / "maps" / "further-north",
        episodes / "pilots" / "maps" / "no-script-yet",
    ):
        p.mkdir(parents=True)
    runs, missing = U.discover(episodes, None, scripts)
    assert [(r.slug, r.script.parent.name, r.project.parent.name) for r in runs] == [
        ("further-north", "pilots", "maps"),
        ("off-and-on", "scripts", "episodes"),
        ("real-roast", "pilots", "news"),
    ]
    assert missing == ["no-script-yet"]  # `pilots` itself is a folder of series, not an unmeasured project


def test_a_pilot_may_not_take_a_library_episodes_slug(tmp_path):
    episodes = tmp_path / "episodes"
    for p in (episodes / "real-roast", episodes / "pilots" / "news" / "real-roast"):
        p.mkdir(parents=True)
    with pytest.raises(U.UsageError, match="real-roast"):
        U.discover(episodes, None, tmp_path)


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
    assert cli.main([*common, "--out", str(out)]) == 2  # the only episode refuses to run without its option: no report
    assert "every episode failed" in capsys.readouterr().err


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
    assert (
        cli.main([*common, "--out", str(out)]) == 1
    )  # without the skip it is reported, and the report is still written
    failed = capsys.readouterr().out
    assert "not measured (failed): unfinished" in failed and "no timeline.json yet" in failed
    report = U.Report.read(out)
    assert report.episodes == {"my-ep": ("plant",)} and report.unmeasured == ("unfinished",)
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


# -- parts drawn through a performer ----------------------------------------------------------------------
def _entry(name, builder):
    return types.SimpleNamespace(name=name, builder=builder)


def _draw(cv, who, size=1.0):
    return (who, size)


def _vera(cv, size=1.0):
    """A one-pose convenience: the registered part, which only calls the drawing the shots call."""
    return _draw(cv, "vera", size)


def _gus(cv, size=1.0):
    return _draw(cv, "gus", size)


def _lone(cv):
    return _draw(cv, who=None)


def _also_lone(cv):
    return _draw(cv, who=None)


def _opens_with_it(cv):
    _draw(cv, "dan")
    return None


def _elsewhere(cv):
    return U.json.dumps(cv)  # a call into another module is a library, not the part's drawing


def _frame_of(function, **local_values):
    """A profiler frame as the hook sees one: the function's own code object with the given locals."""
    return types.SimpleNamespace(f_code=function.__code__, f_locals=local_values)


def test_a_part_that_only_calls_a_drawing_counts_when_a_shot_calls_that_drawing_as_it_does():
    entries = [_entry("anchor-vera", _vera), _entry("anchor-gus", _gus)]
    delegates = U._delegates(entries, {_vera.__code__, _gus.__code__})
    assert set(delegates) == {_draw.__code__}
    assert U._performed(_frame_of(_draw, who="vera"), delegates[_draw.__code__]) == "anchor-vera"
    assert U._performed(_frame_of(_draw, who="gus"), delegates[_draw.__code__]) == "anchor-gus"
    assert U._performed(_frame_of(_draw, who="someone else"), delegates[_draw.__code__]) is None


def test_a_drawing_two_parts_call_alike_credits_neither_and_one_called_by_a_single_part_credits_it():
    both = U._delegates([_entry("a", _lone), _entry("b", _also_lone)], {_lone.__code__, _also_lone.__code__})
    assert both == {}
    alone = U._delegates([_entry("a", _lone)], {_lone.__code__})
    assert U._performed(_frame_of(_draw, who=None), alone[_draw.__code__]) == "a"


def test_only_a_tail_call_into_the_parts_own_module_is_a_drawing_the_part_delegates_to():
    entries = [_entry("opens", _opens_with_it), _entry("lib", _elsewhere)]
    assert U._delegates(entries, {_opens_with_it.__code__, _elsewhere.__code__}) == {}


def test_a_drawing_that_is_itself_a_part_is_traced_as_that_part_not_as_a_delegate():
    assert U._delegates([_entry("vera", _vera), _entry("draw", _draw)], {_vera.__code__, _draw.__code__}) == {}


def test_the_anchors_and_the_host_count_when_the_shared_performer_draws_them(project):
    from srstudio import host_kit, news_kit

    ep = episode(project)
    acts = ((0.0, news_kit.Pose()),)
    for who in ("vera", "gus"):
        with U.trace() as used:
            news_kit.perform(ep.cv, ep.comp, who, 540.0, acts, 0.0, 2.0)  # as a shot draws them, not the one-pose part
        assert {"news-vera", "news-gus"} & used == {f"news-{who}"}
    with U.trace() as used:
        host_kit.perform(ep.cv, ep.comp, ep.comp, ((0.0, host_kit.Pose()),), 0.0, 2.0)
    assert "host-lint" in used


def test_a_trace_names_the_ids_each_character_drew(project):
    ep = episode(project)
    figures: list[figure_record.Figure] = []
    with U.trace(figures):
        locations.reception(ep.cv, ep.comp)  # no character: its ids are nobody's
        canvas = specimens.SPECIMENS["toon-goat"](registry.get("character", "toon-goat"))
    assert [figure.part for figure in figures] == ["toon-goat"]
    drawn = set(figures[0].ids)
    assert len(drawn) == len(figures[0].ids)
    assert drawn <= {node.get("id") for node in ET.fromstring(canvas.scene.to_bytes(layout="pretty")).iter()}


def test_a_recorded_build_leaves_its_figures(project, tmp_path):
    with U.recorded(tmp_path):
        specimens.rig_digest("toon-fox", 2)
    assert {figure.part for figure in figure_record.read(tmp_path)} == {"toon-fox@2"}


def test_a_failed_build_leaves_no_older_record_of_its_figures(tmp_path):
    figure_record.write(tmp_path, [figure_record.Figure("fox", ("k1",))])
    with pytest.raises(RuntimeError), U.recorded(tmp_path):
        raise RuntimeError("the build broke")
    assert figure_record.read(tmp_path) is None
