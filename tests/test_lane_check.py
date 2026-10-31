"""A lane leaves merge and delivery on real evidence: its branch in develop, a clean check, Drive equal to the stage."""

import importlib.util
import json
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("lane_check", ROOT / "tools" / "govern" / "lane_check.py")
assert spec is not None and spec.loader is not None
lane_check = importlib.util.module_from_spec(spec)
sys.modules["lane_check"] = lane_check
spec.loader.exec_module(lane_check)

PROCESSES = ROOT / "tools" / "govern" / "processes"


class Commands:
    """Stands in for subprocess.run: answers with a fixed exit code and keeps every call."""

    def __init__(self, code=0):
        self.code, self.calls = code, []

    def __call__(self, argv, **kwargs):
        self.calls.append((list(argv), kwargs))
        return subprocess.CompletedProcess(argv, self.code, "out\n", "err\n")


def lane(tmp_path, **fields):
    (tmp_path / "lane.json").write_text(json.dumps(fields))
    return tmp_path


def test_a_merged_branch_passes_and_is_asked_of_develop(tmp_path):
    run = Commands()
    lane_check.check("merged", lane(tmp_path, branch="feat/maps"), run=run)
    argv = run.calls[-1][0]
    assert argv[-4:] == ["merge-base", "--is-ancestor", "feat/maps", "develop"]


def test_a_branch_not_in_develop_is_refused(tmp_path):
    with pytest.raises(lane_check.LaneError, match="feat/maps is not in develop"):
        lane_check.check("merged", lane(tmp_path, branch="feat/maps"), run=Commands(1))


def test_a_lane_without_its_file_is_refused(tmp_path):
    with pytest.raises(lane_check.LaneError, match="no lane.json"):
        lane_check.check("merged", tmp_path, run=Commands())


@pytest.mark.parametrize(
    "text",
    ["not json", "[]", '{"branch": 3}', '{"branch": "-x"}', '{"branch": "a", "extra": "b"}', '{"series": "maps"}'],
)
def test_a_malformed_lane_file_is_refused(tmp_path, text):
    (tmp_path / "lane.json").write_text(text)
    with pytest.raises(lane_check.LaneError):
        lane_check.check("merged", tmp_path, run=Commands())


def test_the_publish_check_runs_from_the_workspace_with_its_paths(tmp_path):
    run = Commands()
    lane_check.check("published", lane(tmp_path, branch="feat/x"), run=run)
    argv, kwargs = run.calls[-1]
    assert argv[0] == sys.executable
    assert argv[1:] == [
        str(lane_check.REPO / "episodes" / "instagram_posts.py"),
        "check",
        "generated/renders/ig",
        "generated/renders",
        "--fonts",
        "generated/fonts",
    ]
    assert kwargs["cwd"] == lane_check.WORKSPACE
    assert kwargs["env"]["SRSTUDIO_ENGINE"] == "generated/bin/scene-render"


def test_a_failed_publish_check_is_refused(tmp_path):
    with pytest.raises(lane_check.LaneError, match="publish check"):
        lane_check.check("published", lane(tmp_path, branch="feat/x"), run=Commands(1))


def test_pilots_on_drive_are_compared_with_the_stage_one_way(tmp_path):
    run = Commands()
    lane_check.check("on-drive", lane(tmp_path, branch="feat/maps", series="maps"), run=run)
    argv, kwargs = run.calls[-1]
    assert argv == [
        "rclone",
        "check",
        "generated/pilots/maps",
        "gdrive:srstudio/pilots/maps",
        "--checksum",
        "--one-way",
    ]
    assert kwargs["cwd"] == lane_check.WORKSPACE


def test_a_difference_on_drive_is_refused(tmp_path):
    with pytest.raises(lane_check.LaneError, match="differs"):
        lane_check.check("on-drive", lane(tmp_path, branch="feat/maps", series="maps"), run=Commands(1))


def test_a_drive_check_nobody_faked_meets_the_stand_in_and_not_drive(tmp_path):
    with pytest.raises(lane_check.LaneError, match="a test reached rclone"):
        lane_check.check("on-drive", lane(tmp_path, branch="feat/maps", series="maps"))


def test_the_drive_check_needs_a_series(tmp_path):
    with pytest.raises(lane_check.LaneError, match="series"):
        lane_check.check("on-drive", lane(tmp_path, branch="feat/maps"), run=Commands())


@pytest.mark.parametrize("series", ["../ready-to-publish", "Maps", "a/b", ""])
def test_a_series_cannot_leave_the_pilots_folder(tmp_path, series):
    with pytest.raises(lane_check.LaneError, match="series"):
        lane_check.check("on-drive", lane(tmp_path, branch="feat/maps", series=series), run=Commands())


def test_an_unknown_check_is_refused(tmp_path):
    with pytest.raises(lane_check.LaneError, match="unknown check"):
        lane_check.check("looks-fine", lane(tmp_path, branch="feat/x"), run=Commands())


def test_the_command_exits_2_with_the_reason(tmp_path, capsys):
    assert lane_check.main(["merged", str(tmp_path)]) == 2
    assert "no lane.json" in capsys.readouterr().err


def test_the_command_exits_0_when_the_check_passes(tmp_path, capsys):
    assert lane_check.main(["merged", str(lane(tmp_path, branch="feat/x"))], run=Commands()) == 0
    assert capsys.readouterr().out.startswith("merged: ok")


def process(name):
    return json.loads((PROCESSES / f"{name}.json").read_text())


@pytest.mark.parametrize(("name", "last"), [("reel", "published"), ("pilot", "on-drive")])
def test_merge_and_delivery_cannot_be_passed_on_a_note(name, last):
    stages = {stage["name"]: stage for stage in process(name)["stages"]}
    assert stages["merge"]["check"] == "merged" and stages["merge"]["requires"] == "check"
    assert stages["deliver"]["check"] == last and stages["deliver"]["requires"] == "check"


@pytest.mark.parametrize("name", ["reel", "pilot"])
def test_every_check_a_process_names_is_a_check_this_tool_has(name):
    definition = process(name)
    commands = {key: argv for block in definition["setup"] for key, argv in block["commands"].items()}
    for stage in definition["stages"]:
        if "check" in stage:
            assert stage["check"] in lane_check.CHECKS
            assert commands[stage["check"]][2:] == [stage["check"], "{dir}"]


def test_a_reel_waits_for_nobody():
    assert process("reel")["gates"] == []
