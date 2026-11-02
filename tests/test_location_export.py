"""The exporter's own checks (ADR 0179), without srlocations: it exports exactly the pinned commit's files, refuses an
export that differs from that commit by one file, refuses code loaded from anywhere else, maps srlocations' blocking
keys one for one, and writes only a record ``srstudio.location_bridge`` reads."""

import importlib.util
import json
import os
import stat
import subprocess
import sys
import types
from pathlib import Path

import pytest

from srstudio import location_bridge as lb

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("location_export", ROOT / "tools" / "location_export.py")
assert spec is not None and spec.loader is not None
export = importlib.util.module_from_spec(spec)
sys.modules["location_export"] = export
spec.loader.exec_module(export)

FIXTURE = ROOT / "tests" / "data" / "location-bridge" / "airliner-1080x1920.json"
GIT_ENV = {
    "GIT_AUTHOR_NAME": "t",
    "GIT_AUTHOR_EMAIL": "t@example.invalid",
    "GIT_COMMITTER_NAME": "t",
    "GIT_COMMITTER_EMAIL": "t@example.invalid",
    "GIT_AUTHOR_DATE": "2026-01-01T00:00:00Z",
    "GIT_COMMITTER_DATE": "2026-01-01T00:00:00Z",
    "GIT_CONFIG_GLOBAL": os.devnull,
    "GIT_CONFIG_NOSYSTEM": "1",
}


def git(repo: Path, *words: str) -> str:
    done = subprocess.run(
        ["git", "-C", str(repo), *words], capture_output=True, text=True, check=True, env={**os.environ, **GIT_ENV}
    )
    return done.stdout.strip()


@pytest.fixture
def repo(tmp_path):
    """A small srlocations-shaped repository: a package, a catalog, and a file outside both that is never exported."""
    root = tmp_path / "srlocations-repo"
    (root / "srlocations").mkdir(parents=True)
    (root / "srlocations" / "__init__.py").write_text("NAME = 'srlocations'\n")
    (root / "srlocations" / "framing.py").write_text("def blocking():\n    return []\n")
    (root / "catalog" / "locations" / "row").mkdir(parents=True)
    (root / "catalog" / "catalog.json").write_text('{"schema": 1, "name": "studio"}\n')
    (root / "catalog" / "locations" / "row" / "1.0.0.json").write_text("{}\n")
    (root / "README.md").write_text("not exported\n")
    git(root, "init", "-q")
    git(root, "add", ".")
    git(root, "commit", "-q", "-m", "one")
    return root


def test_a_blob_id_is_gits_own(tmp_path):
    path = tmp_path / "f"
    path.write_bytes(b"some bytes\n\x00\xff")
    assert export.blob_id(path.read_bytes()) == git(tmp_path, "hash-object", str(path))


def test_an_export_holds_exactly_the_commits_package_and_catalog_private_to_the_operator(repo, tmp_path):
    commit = git(repo, "rev-parse", "HEAD")
    dest = export.export(repo, commit, tmp_path / "generated" / "srlocations" / commit)
    files = sorted(str(p.relative_to(dest)) for p in dest.rglob("*") if p.is_file())
    assert files == [
        "catalog/catalog.json",
        "catalog/locations/row/1.0.0.json",
        "srlocations/__init__.py",
        "srlocations/framing.py",
    ]
    assert all(stat.S_IMODE(p.stat().st_mode) == 0o600 for p in dest.rglob("*") if p.is_file())
    assert all(stat.S_IMODE(p.stat().st_mode) == 0o700 for p in [dest, *dest.rglob("*")] if p.is_dir())


def test_an_export_ignores_what_the_checkout_holds_uncommitted(repo, tmp_path):
    commit = git(repo, "rev-parse", "HEAD")
    (repo / "srlocations" / "framing.py").write_text("raise SystemExit('edited, never committed')\n")
    (repo / "srlocations" / "new.py").write_text("\n")
    dest = export.export(repo, commit, tmp_path / "x" / commit)
    assert (dest / "srlocations" / "framing.py").read_text() == "def blocking():\n    return []\n"
    assert not (dest / "srlocations" / "new.py").exists()


def test_an_existing_export_is_checked_again_and_reused(repo, tmp_path):
    commit = git(repo, "rev-parse", "HEAD")
    dest = export.export(repo, commit, tmp_path / commit)
    assert export.export(repo, commit, dest) == dest


@pytest.mark.parametrize(
    "spoil",
    [
        lambda d: (d / "srlocations" / "framing.py").write_text("def blocking():\n    return [1]\n"),
        lambda d: (d / "srlocations" / "extra.py").write_text("\n"),
        lambda d: (d / "catalog" / "locations" / "row" / "1.0.0.json").unlink(),
        lambda d: (d / "srlocations" / "__pycache__").mkdir(),
    ],
    ids=["edited", "extra file", "missing file", "extra folder"],
)
def test_an_export_that_differs_from_the_commit_is_refused(repo, tmp_path, spoil):
    commit = git(repo, "rev-parse", "HEAD")
    dest = export.export(repo, commit, tmp_path / commit)
    spoil(dest)
    with pytest.raises(export.ExportError, match="differs from srlocations"):
        export.export(repo, commit, dest)


def test_a_repository_without_the_pinned_commit_is_refused(repo):
    with pytest.raises(export.ExportError, match=lb.SRLOCATIONS_COMMIT):
        export.require_commit(repo, lb.SRLOCATIONS_COMMIT)
    head = git(repo, "rev-parse", "HEAD")
    assert export.require_commit(repo, head) == head


def test_a_link_in_the_commit_is_refused(repo, tmp_path):
    (repo / "srlocations" / "link.py").symlink_to("framing.py")
    git(repo, "add", ".")
    git(repo, "commit", "-q", "-m", "link")
    with pytest.raises(export.ExportError, match="link.py"):
        export.export(repo, git(repo, "rev-parse", "HEAD"), tmp_path / "linked")


def test_srlocations_code_loaded_from_outside_the_export_is_refused(tmp_path):
    inside = tmp_path / "export" / "srlocations" / "framing.py"
    outside = tmp_path / "studio" / "srlocations" / "location.py"
    modules = {
        "srlocations.framing": types.SimpleNamespace(__file__=str(inside)),
        "srlocationsx": types.SimpleNamespace(__file__=str(outside)),  # another package: not srlocations
        "json": json,
    }
    export.check_loaded(modules, tmp_path / "export")
    modules["srlocations.location"] = types.SimpleNamespace(__file__=str(outside))
    with pytest.raises(export.ExportError, match="srlocations.location"):
        export.check_loaded(modules, tmp_path / "export")


BLOCKED = {
    "mark": "aisle",
    "at": [0.0, 0.0, 3.0],
    "facing": 0.0,
    "framing": "",
    "height": 1.7,
    "feet": [540.0, 1500.0],
    "head": [540.0, 400.0],
    "scale": 600.0,
    "in_frame": True,
}


def test_a_blocked_mark_is_renamed_to_its_units_one_for_one():
    assert export.mark_record(BLOCKED) == {
        "mark": "aisle",
        "at_m": [0.0, 0.0, 3.0],
        "facing_deg": 0.0,
        "framing": "",
        "height_m": 1.7,
        "feet_px": [540.0, 1500.0],
        "head_px": [540.0, 400.0],
        "pixels_per_metre": 600.0,
        "in_frame": True,
    }


@pytest.mark.parametrize(
    "blocked",
    [{**BLOCKED, "colour": "red"}, {k: v for k, v in BLOCKED.items() if k != "scale"}],
    ids=["a key srlocations added", "a key srlocations dropped"],
)
def test_a_blocked_mark_of_another_shape_is_refused(blocked):
    with pytest.raises(export.ExportError, match="blocking"):
        export.mark_record(blocked)


class View:
    """srlocations' compiler.Projection as the exporter reads it: eye, basis rows, focal length, near plane, gate."""

    NEAR, SENSOR = 0.05, (36.0, 24.0)

    def __init__(self, width, height, lens):
        self.eye, self.width, self.height = (0.0, 1.22, -1.3), width, height
        self.basis = ((1.0, 0.0, 0.0), (0.0, 1.0, 0.0), (0.0, 0.0, 1.0))
        self.focal = lens * (width / 36.0 if width / height >= 1.5 else height / 24.0)


@pytest.mark.parametrize(("width", "height", "fit"), [(1080, 1920, "height"), (1920, 1080, "width")])
def test_a_camera_is_written_with_its_fit_read_from_the_focal_length(width, height, fit):
    shot = types.SimpleNamespace(eye=(0.0, 1.22, -1.3), look_at=(0.0, 1.22, 8.0), lens=15.0)
    camera = export.camera_record(shot, View(width, height, 15.0), width, height)
    assert camera["fit"] == fit
    assert (camera["right"], camera["up"], camera["forward"]) == ([1.0, 0.0, 0.0], [0.0, 1.0, 0.0], [0.0, 0.0, 1.0])
    assert camera["gate_mm"] == [36.0, 24.0] and camera["near_m"] == 0.05


def test_a_camera_whose_focal_fits_neither_side_is_refused():
    shot = types.SimpleNamespace(eye=(0.0, 1.22, -1.3), look_at=(0.0, 1.22, 8.0), lens=15.0)
    view = View(1080, 1920, 15.0)
    view.focal = 123.0
    with pytest.raises(export.ExportError, match="fit"):
        export.camera_record(shot, view, 1080, 1920)


def test_a_record_is_written_only_when_srstudio_reads_it(tmp_path):
    data = json.loads(FIXTURE.read_text())
    out = tmp_path / "made" / "record.json"
    export.write(data, out, lb)
    assert out.read_text() == FIXTURE.read_text()
    assert stat.S_IMODE(out.stat().st_mode) == 0o600 and stat.S_IMODE(out.parent.stat().st_mode) == 0o700
    data["shots"][0]["marks"][0]["in_frame"] = not data["shots"][0]["marks"][0]["in_frame"]
    with pytest.raises(lb.RecordValueError):
        export.write(data, tmp_path / "bad.json", lb)
    assert not (tmp_path / "bad.json").exists()


def test_a_size_is_width_by_height():
    assert export.size("1080x1920") == (1080, 1920)
    for text in ("1080", "x1920", "0x10", "1080x1920x3", "big"):
        with pytest.raises(export.ExportError):
            export.size(text)


def test_the_command_refuses_a_repository_without_the_pin(repo, tmp_path, capsys):
    argv = [
        "--repo",
        str(repo),
        "--location",
        "row",
        "--shot",
        "a",
        "--size",
        "1080x1920",
        "--out",
        str(tmp_path / "o"),
    ]
    assert export.main([*argv, "--export-root", str(tmp_path / "exports")]) == 2
    assert lb.SRLOCATIONS_COMMIT in capsys.readouterr().err
    assert not (tmp_path / "o").exists() and not (tmp_path / "exports").exists()


# --- blocking (ADR 0184) -------------------------------------------------------------------------------------------


def test_a_figures_leaf_is_named_by_its_joint():
    assert export.limb_of("bench/left_hand") == "left_hand"
    assert export.limb_of("bench/left_hand.ball") == "left_hand"
    assert export.limb_of("walker/hips") == "hips"


def test_tangled_limbs_are_read_as_pairs():
    lines = ["left_hand passes through chest", "right_lower_leg passes through left_lower_leg"]
    assert export.tangles(lines) == [
        {"limb": "left_hand", "other": "chest"},
        {"limb": "right_lower_leg", "other": "left_lower_leg"},
    ]


@pytest.mark.parametrize(
    "line", ["left_hand overlaps chest", "left_hand passes through chest!", "", "Hand passes through x"]
)
def test_a_tangle_of_another_shape_is_refused_not_guessed(line):
    with pytest.raises(export.ExportError, match="tangle"):
        export.tangles([line])


class Dof:
    def __init__(self, turn, low, high):
        self.turn, self.low, self.high = turn, low, high


def test_controls_at_an_end_of_their_range_are_listed_and_moves_left_out():
    ranges = {
        "left_lower_arm.stretch": Dof("yaw", -150, 5),
        "head.nod_down_up": Dof("pitch", -20, 20),
        "neck.turn_left_right": Dof("yaw", -40, 40),
        "hips.forward": Dof("forward", -5, 5),
    }
    values = {
        "left_lower_arm.stretch": -150.0,
        "head.nod_down_up": 20.0,
        "neck.turn_left_right": 39.9,
        "hips.forward": 5.0,
    }
    assert export.at_limits(values, ranges, {"right", "up", "forward"}) == [
        {"control": "head.nod_down_up", "value_deg": 20.0, "bound": "high", "bound_deg": 20.0},
        {"control": "left_lower_arm.stretch", "value_deg": -150.0, "bound": "low", "bound_deg": -150.0},
    ]


def test_a_pixel_is_none_behind_the_camera():
    class Ahead:
        def pixel(self, point):
            return (1, 2)

    class Behind:
        def pixel(self, point):
            return None

    assert export.pixel(Ahead(), (0, 0, 1)) == [1.0, 2.0]
    assert export.pixel(Behind(), (0, 0, -1)) is None


def test_a_missing_request_is_an_export_error(tmp_path):
    with pytest.raises(export.ExportError, match="blocking request"):
        export.read_request(tmp_path / "none.json", lb)


def test_a_record_without_blocking_is_written_as_the_schema_without_it(tmp_path):
    data = json.loads(FIXTURE.read_text())
    assert data["schema_version"] == lb.SCHEMA_WITHOUT_BLOCKING
    blocked = json.loads((ROOT / "tests" / "data" / "location-bridge" / "park-blocking-1080x1920.json").read_text())
    assert blocked["schema_version"] == lb.SCHEMA_VERSION and "blocking" in blocked
    export.write(blocked, tmp_path / "blocked.json", lb)
