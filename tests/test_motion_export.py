"""The motion exporter (ADR 0187). Without srlocations: it parses exactly the BVH ``save_bvh`` writes, turns its Euler
turns into the quaternions of srlocations' frame, shares location_export's pinned export, loads only srstudio's reader
in a foreign interpreter, and writes only a record ``srstudio.motion_bridge`` reads. With srlocations' interpreter and
the pinned commit at hand, it re-runs both recorded fixtures and a BVH take end to end; without them those tests skip
and say why."""

import importlib.util
import itertools
import json
import math
import os
import stat
import subprocess
import sys
import types
from pathlib import Path

import pytest

from srstudio import motion_bridge as mb

ROOT = Path(__file__).resolve().parents[1]
TOOL = ROOT / "tools" / "motion_export.py"
spec = importlib.util.spec_from_file_location("motion_export", TOOL)
assert spec is not None and spec.loader is not None
export = importlib.util.module_from_spec(spec)
sys.modules["motion_export"] = export
spec.loader.exec_module(export)

DATA = ROOT / "tests" / "data" / "motion-bridge"
WALK = DATA / "walk-2m-30fps.json"
STUDIO = Path(os.environ.get("SRLOCATIONS_REPO", "/home/pals/src/studio"))
STUDIO_PYTHON = Path(os.environ.get("SRLOCATIONS_PYTHON", str(STUDIO / ".venv" / "bin" / "python")))
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


def bvh_text(root_channels="Xposition Yposition Zposition Zrotation Xrotation Yrotation", rows=("0 90 0 0 0 0 0 0 0",)):
    """A two-joint BVH in save_bvh's layout: hips and a spine with an end site, one frame a 30th of a second long."""
    return "\n".join(
        [
            "HIERARCHY",
            "ROOT hips",
            "{",
            "  OFFSET 0 0 0",
            f"  CHANNELS {len(root_channels.split())} {root_channels}",
            "  JOINT spine",
            "  {",
            "    OFFSET 0 7 -2.5",
            "    CHANNELS 3 Zrotation Xrotation Yrotation",
            "    End Site",
            "    {",
            "      OFFSET 0 10 0",
            "    }",
            "  }",
            "}",
            "MOTION",
            f"Frames: {len(rows)}",
            "Frame Time: 0.0333333",
            *rows,
        ]
    )


# --- the BVH ---------------------------------------------------------------------------------------------------------


def test_a_bvh_in_save_bvh_layout_parses_into_bones_and_rows():
    bones, rows = export.parse_bvh(bvh_text(rows=("1 90 -2 10 20 30 0 0 45", "0 90 0 0 0 0 0 0 0")), 30.0)
    assert [(bone.name, bone.parent, bone.offset) for bone in bones] == [
        ("hips", None, (0.0, 0.0, 0.0)),
        ("spine", "hips", (0.0, 7.0, -2.5)),
    ]
    assert rows == [[1.0, 90.0, -2.0, 10.0, 20.0, 30.0, 0.0, 0.0, 45.0], [0.0, 90.0] + [0.0] * 7]


@pytest.mark.parametrize(
    ("text", "match"),
    [
        (bvh_text(root_channels="Xposition Yposition Zposition Xrotation Yrotation Zrotation"), "channels"),
        (bvh_text(rows=("0 90 0 0 0 0 0 0",)), "ends in the middle"),
        (bvh_text(rows=("0 90 0 0 0 0 0 0 0 7",)), "past its"),
        (bvh_text(rows=("0 nan 0 0 0 0 0 0 0",)), "finite number"),
        (bvh_text(rows=("0 1e999 0 0 0 0 0 0 0",)), "finite number"),
        (bvh_text(rows=("0 0x10 0 0 0 0 0 0 0",)), "finite number"),
        (bvh_text(rows=()), "frames"),
        (bvh_text().replace("Frame Time: 0.0333333", "Frame Time: 0.04"), "apart"),
        (bvh_text().replace("HIERARCHY", "HIERARCHIES"), "HIERARCHY"),
        (bvh_text().replace("End Site", "Site End"), "inside joint"),
        (bvh_text().replace("CHANNELS 3 Zrotation", "CHANNELS three Zrotation"), "channels"),
        (
            bvh_text().replace(
                "    End Site", "    JOINT neck\n    {\n    OFFSET 0 1 0\n    CHANNELS 1 Zrotation\n    }"
            ),
            "channels",
        ),
    ],
    ids=[
        "root turns in another order",
        "a frame short",
        "a word past the frames",
        "NaN",
        "overflow",
        "hex",
        "no frames",
        "another frame time",
        "another header",
        "an unknown word in a joint",
        "a channel count that is not a number",
        "a joint with one channel",
    ],
)
def test_a_bvh_of_another_layout_is_refused(text, match):
    with pytest.raises(export.ExportError, match=match):
        export.parse_bvh(text, 30.0)


def test_the_exporter_shares_location_exports_error_and_pinned_export():
    assert export.ExportError is export.location_export.ExportError
    for name in ("export", "verify", "check_loaded", "tree", "require_commit"):
        assert callable(getattr(export.location_export, name))


ANGLES = [-170.0, -90.0, -33.3, 0.0, 12.5, 90.0, 180.0]


def _matrix_of(q):
    return [list(mb._rotate(q, axis)) for axis in ((1.0, 0.0, 0.0), (0.0, 1.0, 0.0), (0.0, 0.0, 1.0))]


@pytest.mark.parametrize("angles", list(itertools.product(ANGLES, [-45.0, 0.0, 89.0], [-120.0, 0.0, 60.0])))
def test_a_quaternion_is_the_turn_it_was_made_from(angles):
    """Through all four branches of the matrix-to-quaternion conversion, and w is never negative."""
    m = export.turn(export.BONE_CHANNELS, angles)
    q = export.quaternion(m)
    assert q[0] >= 0 and math.isclose(math.fsum(c * c for c in q), 1.0, abs_tol=1e-7)
    columns = _matrix_of(tuple(q))
    for c in range(3):
        for r in range(3):
            assert columns[c][r] == pytest.approx(m[r][c], abs=2e-7)


def test_a_turn_leaves_the_file_frame_for_srlocations_frame():
    """A file's z is srlocations' -z: a turn about z reads the same, a turn about x or y the other way."""
    assert export.quaternion(export.turn(export.BONE_CHANNELS, (90.0, 0.0, 0.0))) == pytest.approx(
        [math.sqrt(0.5), 0.0, 0.0, math.sqrt(0.5)]
    )
    assert export.quaternion(export.turn(export.BONE_CHANNELS, (0.0, 90.0, 0.0))) == pytest.approx(
        [math.sqrt(0.5), -math.sqrt(0.5), 0.0, 0.0]
    )
    assert export.quaternion(export.turn(export.BONE_CHANNELS, (0.0, 0.0, 90.0))) == pytest.approx(
        [math.sqrt(0.5), 0.0, -math.sqrt(0.5), 0.0]
    )
    assert export.quaternion(export.turn(export.BONE_CHANNELS, (0.0, 0.0, 0.0))) == [1.0, 0.0, 0.0, 0.0]


def test_a_frame_and_skeleton_leave_the_file_in_metres_and_srlocations_axes():
    bones, rows = export.parse_bvh(bvh_text(rows=("1 90 -2 0 0 0 0 0 0",)), 30.0)
    order = ("hips", "spine")
    assert export.skeleton(bones, order) == [
        {"name": "hips", "parent": None, "rest_offset_m": [0.0, 0.0, 0.0]},
        {"name": "spine", "parent": "hips", "rest_offset_m": [0.0, 0.07, 0.025]},
    ]
    frame = export.frame_record(bones, rows[0], order)
    assert frame == {"root_translation_m": [0.01, 0.9, 0.02], "local_rotations_wxyz": [[1.0, 0.0, 0.0, 0.0]] * 2}
    assert not any(math.copysign(1.0, v) < 0 for v in frame["root_translation_m"] if v == 0), "no negative zero"


def test_a_skeleton_other_than_the_mannequins_is_refused():
    bones, _ = export.parse_bvh(bvh_text(), 30.0)
    with pytest.raises(export.ExportError, match="mannequin"):
        export.skeleton(bones, ("hips", "spine", "chest"))


def test_world_positions_are_srlocations_own_unflipped():
    class Transform:
        def __init__(self, position):
            self.position = position

        def then(self, other):
            return Transform(tuple(a + b for a, b in zip(self.position, other.position, strict=True)))

    figure = types.SimpleNamespace(
        transform=Transform((1.0, 0.0, 2.0)),
        frames=lambda: {"hips": Transform((0.0, 0.9, 0.0)), "head": Transform((0.0, 1.6, 0.0875))},
    )
    assert export.world_positions(figure, ("hips", "head")) == [[1.0, 0.9, 2.0], [1.0, 1.6, 2.0875]]


def test_frame_times_are_srlocations_clip_sampling():
    assert export._times_of(0.0, 2.0, 30.0)[-1] == pytest.approx(2.0) and len(export._times_of(0.0, 2.0, 30.0)) == 61
    assert export._times_of(0.5, 0.5, 24.0) == [0.5]


# --- writing ---------------------------------------------------------------------------------------------------------


def test_a_record_is_written_only_when_srstudio_reads_it(tmp_path):
    data = json.loads(WALK.read_text())
    out = tmp_path / "made" / "record.json"
    export.write(data, out, mb)
    assert out.read_text() == WALK.read_text()
    assert stat.S_IMODE(out.stat().st_mode) == 0o600 and stat.S_IMODE(out.parent.stat().st_mode) == 0o700
    data["frames"][3]["world_positions_m"][20][0] += 0.01
    with pytest.raises(mb.RecordValueError):
        export.write(data, tmp_path / "bad.json", mb)
    assert not (tmp_path / "bad.json").exists()


def test_the_reader_loads_as_srstudios_own_here():
    assert export.load_bridge() is mb


def test_a_foreign_srstudio_is_refused(monkeypatch):
    foreign = types.ModuleType("srstudio")
    foreign.__path__ = ["/somewhere/else/srstudio"]
    monkeypatch.setitem(sys.modules, "srstudio", foreign)
    with pytest.raises(export.ExportError, match="already imported"):
        export.load_bridge()


def test_in_a_bare_interpreter_only_the_reader_and_its_two_modules_load():
    """As in srlocations' interpreter, where there is no srstudio: an empty package on this repository's src, and the
    reader, srstudio.errors and srstudio.location_bridge in it, nothing else of srstudio."""
    script = (
        "import importlib.util, sys\n"
        f"spec = importlib.util.spec_from_file_location('motion_export', {str(TOOL)!r})\n"
        "module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module)\n"
        "bridge = module.load_bridge()\n"
        "print(bridge.__file__)\n"
        "print(sorted(name for name in sys.modules if name == 'srstudio' or name.startswith('srstudio.')))\n"
    )
    done = subprocess.run([sys.executable, "-I", "-c", script], capture_output=True, text=True, check=True)
    path, loaded = done.stdout.splitlines()
    assert Path(path) == ROOT / "src" / "srstudio" / "motion_bridge.py"
    assert loaded == "['srstudio', 'srstudio.errors', 'srstudio.location_bridge', 'srstudio.motion_bridge']"


# --- the command -----------------------------------------------------------------------------------------------------


@pytest.fixture
def repo(tmp_path):
    root = tmp_path / "srlocations-repo"
    (root / "srlocations").mkdir(parents=True)
    (root / "srlocations" / "__init__.py").write_text("\n")
    (root / "catalog").mkdir()
    (root / "catalog" / "catalog.json").write_text("{}\n")
    for words in (["init", "-q"], ["add", "."], ["commit", "-q", "-m", "one"]):
        subprocess.run(["git", "-C", str(root), *words], check=True, capture_output=True, env={**os.environ, **GIT_ENV})
    return root


@pytest.mark.parametrize(
    ("words", "match"),
    [
        (["--module", "walk.py", "--fps", "30"], "--figure"),
        (["--bvh", "take.bvh", "--figure", "walker", "--fps", "30"], "stock mannequin"),
        (["--module", "walk.py", "--figure", "walker", "--fps", "0"], "--fps"),
        (["--module", "walk.py", "--figure", "walker", "--fps", "30", "--start", "-1"], "--start"),
        (["--module", "walk.py", "--figure", "walker", "--fps", "30", "--end", "inf"], "--end"),
        (["--module", "walk.py", "--figure", "walker", "--fps", "30", "--start", "2", "--end", "1"], "--end"),
        (["--module", "walk.py", "--figure", "walker", "--fps", "30"], mb.SRLOCATIONS_COMMIT),
    ],
    ids=[
        "a module with no figure",
        "a take with a figure",
        "no frame rate",
        "a start before 0",
        "an endless end",
        "an end before the start",
        "no pin",
    ],
)
def test_the_command_refuses_before_it_exports(repo, tmp_path, capsys, words, match):
    argv = ["--repo", str(repo), *words, "--out", str(tmp_path / "o.json"), "--export-root", str(tmp_path / "x")]
    assert export.main(argv) == 2
    assert match in capsys.readouterr().err
    assert not (tmp_path / "o.json").exists() and not (tmp_path / "x").exists()


def test_a_clip_past_the_frames_a_record_holds_is_refused_before_it_is_sampled():
    export._bounded(0.0, (mb.MAX_FRAMES - 1) / 30.0, 30.0, mb)
    with pytest.raises(export.ExportError, match=str(mb.MAX_FRAMES)):
        export._bounded(0.0, mb.MAX_FRAMES / 30.0, 30.0, mb)


# --- end to end, in srlocations' interpreter -------------------------------------------------------------------------


def _srlocations_or_skip() -> None:
    if not STUDIO_PYTHON.is_file():
        pytest.skip(f"srlocations' interpreter is not at {STUDIO_PYTHON} (set SRLOCATIONS_PYTHON)")
    done = subprocess.run(
        ["git", "-C", str(STUDIO), "cat-file", "-e", f"{mb.SRLOCATIONS_COMMIT}^{{commit}}"], capture_output=True
    )
    if done.returncode:
        pytest.skip(f"{STUDIO} does not hold the pinned srlocations commit {mb.SRLOCATIONS_COMMIT} (SRLOCATIONS_REPO)")


@pytest.fixture(scope="module")
def exports(tmp_path_factory):
    _srlocations_or_skip()
    return tmp_path_factory.mktemp("srlocations-exports")


def _run(*words: str) -> subprocess.CompletedProcess:
    command = [str(STUDIO_PYTHON), "-I", str(ROOT / "tools" / "motion_export.py"), "--repo", str(STUDIO), *words]
    return subprocess.run(command, capture_output=True, text=True, timeout=600)


@pytest.mark.parametrize(
    ("module", "figure", "record"),
    [
        ("walk_two_metres.py", "walker", "walk-2m-30fps.json"),
        ("stand_wave_cross.py", "poser", "stand-wave-crossed-30fps.json"),
    ],
)
def test_the_fixtures_are_what_the_exporter_makes_at_the_pin(exports, tmp_path, module, figure, record):
    out = tmp_path / record
    done = _run(
        "--module",
        str(DATA / module),
        "--figure",
        figure,
        "--fps",
        "30",
        "--out",
        str(out),
        "--export-root",
        str(exports),
    )
    assert done.returncode == 0, done.stderr
    assert out.read_bytes() == (DATA / record).read_bytes()


def test_a_bvh_take_is_recorded_on_the_stock_mannequin(exports, tmp_path):
    """A take of the walk's first half second, written by srlocations' save_bvh, read back by its load_bvh."""
    take = tmp_path / "walk-take.bvh"
    script = (
        "import importlib.util, sys\n"
        "sys.dont_write_bytecode = True\n"
        f"sys.path.insert(0, {str(exports / mb.SRLOCATIONS_COMMIT)!r})\n"
        "from srlocations.interchange import save_bvh\n"
        f"spec = importlib.util.spec_from_file_location('walk', {str(DATA / 'walk_two_metres.py')!r})\n"
        "walk = importlib.util.module_from_spec(spec); spec.loader.exec_module(walk)\n"
        f"save_bvh({str(take)!r}, 'walker', walk.location(), fps=30, end=0.5)\n"
    )
    made = subprocess.run([str(STUDIO_PYTHON), "-I", "-c", script], capture_output=True, text=True, timeout=600)
    assert made.returncode == 0, made.stderr
    out = tmp_path / "take.json"
    done = _run("--bvh", str(take), "--fps", "30", "--start", "0.1", "--out", str(out), "--export-root", str(exports))
    assert done.returncode == 0, done.stderr
    clip = mb.load(out)
    assert (clip.source.kind, clip.source.name, clip.source.unknown_bones) == ("bvh", "walk-take.bvh", ())
    assert clip.frame_count == 13 and clip.start_s == pytest.approx(0.1)
    assert all(frame.world_positions is not None for frame in clip.frames)
    wrong = _run("--bvh", str(take), "--fps", "24", "--out", str(tmp_path / "no.json"), "--export-root", str(exports))
    assert wrong.returncode == 2 and "its own rate" in wrong.stderr


@pytest.mark.parametrize(
    "text",
    ["not a bvh", "HIERARCHY\nROOT a\n{\nCHANNELS inf Xposition\n}\nMOTION\n", ""],
    ids=["no hierarchy", "an infinite channel count", "empty"],
)
def test_a_take_srlocations_cannot_read_is_refused_without_a_record(exports, tmp_path, text):
    take = tmp_path / "bad.bvh"
    take.write_text(text)
    out = tmp_path / "no.json"
    done = _run("--bvh", str(take), "--fps", "30", "--out", str(out), "--export-root", str(exports))
    assert done.returncode == 2 and "cannot read" in done.stderr and "Traceback" not in done.stderr
    assert not out.exists()


def test_a_figure_the_location_does_not_have_is_named(exports, tmp_path):
    args = ("--fps", "30", "--out", str(tmp_path / "no.json"), "--export-root", str(exports))
    done = _run("--module", str(DATA / "walk_two_metres.py"), "--figure", "dancer", *args)
    assert done.returncode == 2 and "dancer" in done.stderr and "Traceback" not in done.stderr
