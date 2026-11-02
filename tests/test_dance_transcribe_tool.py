"""``tools/dance_transcribe.py`` (ADR 0212): a ``dancepose.motion`` record and a window list read strictly, the
measured body in the skeleton's frame, a fit that lands inside every preset's limits, and a document that reads back.
The records here are synthetic: our own skeleton danced and written as an estimator would write a person."""

import importlib.util
import json
import math
import sys
from dataclasses import replace
from pathlib import Path

import numpy as np
import pytest

from srstudio import dance
from srstudio import dance_study as ds
from srstudio import skeleton as sk
from srstudio.dance_pose import dance_pose
from srstudio.music import Groove

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("dance_transcribe_tool", ROOT / "tools" / "dance_transcribe.py")
assert spec is not None and spec.loader is not None
tool = importlib.util.module_from_spec(spec)
sys.modules["dance_transcribe_tool"] = tool
spec.loader.exec_module(tool)

GROOVE = Groove(120)
FPS = 24
PROFILE = sk.preset("realistic")
SHA = "0" * 64


def turn(yaw):
    c, s = math.cos(yaw), math.sin(yaw)
    return np.array([[c, 0.0, s], [0.0, 1.0, 0.0], [-s, 0.0, c]])


def skeleton_points(frame):
    """The study's 13 points of ``frame`` on the realistic preset, in metres from the hips' middle."""
    points = ds._skeleton_points(PROFILE, dance_pose(PROFILE, frame, clamp=False).pose)
    return points - ds._mid(points[None], "left_hip", "right_hip")[0]


def person(points, yaw=0.0, track="p1"):
    """One tracked person as the estimator writes it: the 15 joints and 13 landmarks in its own axes, turned ``yaw``."""
    at = {name: points[ds._AT[name]] for name in ds.POINTS}
    turned = {k: (v @ turn(-yaw).T) * (-1.0, 1.0, -1.0) for k, v in at.items()}
    joints = {
        "head": turned["head"], "neck": (turned["left_shoulder"] + turned["right_shoulder"]) / 2,
        "LS": turned["left_shoulder"], "LE": turned["left_elbow"], "LW": turned["left_wrist"],
        "RS": turned["right_shoulder"], "RE": turned["right_elbow"], "RW": turned["right_wrist"],
        "LH": turned["left_hip"], "LK": turned["left_knee"], "LA": turned["left_ankle"],
        "RH": turned["right_hip"], "RK": turned["right_knee"], "RA": turned["right_ankle"],
        "pelvis": (turned["left_hip"] + turned["right_hip"]) / 2,
    }  # fmt: skip
    ear = np.array([0.07, 0.0, 0.0]) @ turn(-yaw).T * (-1.0, 1.0, -1.0)
    aux = {name: turned["head"] for name in tool.AUX_NAMES}
    aux["left_ear"], aux["right_ear"] = turned["head"] + ear, turned["head"] - ear
    world = [[float(v) for v in joints[n]] for n in tool.JOINT_NAMES]
    return {
        "track_id": track,
        "xy": [[500.0 + 400 * w[0], 500.0 + 400 * w[1]] for w in world],
        "confidence": [0.9] * 15,
        "torso_yaw_rad": yaw,
        "head_yaw_rad": yaw,
        "roll_rad": 0.0,
        "roll_confidence": 0.5,
        "measured": {"depth": True, "torso_yaw": True, "head_yaw": True, "axial_roll": False},
        "world_m": world,
        "aux_world_m": [[float(v) for v in aux[n]] for n in tool.AUX_NAMES],
    }


def record(move, seconds=3.0, yaw=0.0, lost=()):
    """``move`` danced for ``seconds`` as a ``dancepose.motion`` record; the frames in ``lost`` hold nobody."""
    frames = []
    for i in range(round(seconds * FPS)):
        frame = dance.sample(move, GROOVE, i / FPS)
        persons = {} if i in lost else {"p1": person(skeleton_points(frame), yaw)}
        frames.append({"frame": i, "time": i / FPS, "persons": persons})
    return {
        "format": "dancepose.motion",
        "format_version": 1,
        "fps": FPS,
        "width": 1000,
        "height": 1000,
        "joint_names": list(tool.JOINT_NAMES),
        "aux_landmark_names": list(tool.AUX_NAMES),
        "frames": frames,
    }


def windows(*rows):
    return {
        "schema": "srstudio.dance-windows/1.0.0",
        "source": {"title": "a synthetic dance", "sha256": SHA},
        "windows": [
            {"name": name, "track": "p1", "start_s": t0, "end_s": t1, "seen": 2, "dancers": 2} for name, t0, t1 in rows
        ],
    }


def written(tmp_path, name, data):
    path = tmp_path / name
    path.write_text(json.dumps(data))
    return path


@pytest.fixture(scope="module")
def point_up():
    return dance.moves()["point-up"]


@pytest.fixture(scope="module")
def motion(point_up):
    return tool.read_motion(
        written(
            Path(__import__("tempfile").mkdtemp(dir=ROOT / "_tmp" if (ROOT / "_tmp").is_dir() else None)),
            "motion.json",
            record(point_up, yaw=0.4),
        )
    )


# --- the record ------------------------------------------------------------------------------------------------------


def test_a_record_reads_its_frames_and_finds_a_track_by_time(motion):
    assert len(motion.times) == 72 and motion.fps == FPS
    assert motion.nearest("p1", 1.0) is motion.persons[24]["p1"]
    assert motion.nearest("p1", 1.02) is motion.persons[24]["p1"]
    assert motion.nearest("p2", 1.0) is None


def test_a_lost_frame_is_bridged_from_a_neighbour_within_the_bound(point_up, tmp_path):
    lost = tool.read_motion(written(tmp_path, "lost.json", record(point_up, lost=(24, 25, 26, 27))))
    assert lost.nearest("p1", 24 / FPS) is lost.persons[23]["p1"]  # one frame away
    assert lost.nearest("p1", 25.5 / FPS) is not None  # two or three frames away either side
    gone = tool.read_motion(written(tmp_path, "gone.json", record(point_up, lost=tuple(range(20, 40)))))
    assert gone.nearest("p1", 30 / FPS) is None  # ten frames from anyone


@pytest.mark.parametrize(
    "change",
    [
        lambda r: r.update(format="other.motion"),
        lambda r: r.update(format_version=2),
        lambda r: r.update(fps=0),
        lambda r: r.update(extra=1),
        lambda r: r.pop("joint_names"),
        lambda r: r.update(joint_names=list(reversed(tool.JOINT_NAMES))),
        lambda r: r.update(frames=[]),
        lambda r: r["frames"][0].update(frame=5),  # frames out of order
        lambda r: r["frames"][1].update(time=-1.0),
        lambda r: r["frames"][0]["persons"].update({"Bad Name": r["frames"][0]["persons"]["p1"]}),
        lambda r: r["frames"][0]["persons"]["p1"].update(unknown=1),
        lambda r: r["frames"][0]["persons"]["p1"].pop("world_m"),
        lambda r: r["frames"][0]["persons"]["p1"]["world_m"][3].__setitem__(0, "0.1"),
        lambda r: r["frames"][0]["persons"]["p1"]["world_m"][3].__setitem__(0, 7.0),
        lambda r: r["frames"][0]["persons"]["p1"]["world_m"].pop(),
        lambda r: r["frames"][0]["persons"]["p1"]["confidence"].__setitem__(0, 1.5),
        lambda r: r["frames"][0]["persons"]["p1"]["measured"].update(depth=False),  # a 2D pose
        lambda r: r["frames"][0]["persons"]["p1"].update(torso_yaw_rad=True),
    ],
)
def test_a_malformed_record_is_refused_at_a_path(point_up, tmp_path, change):
    data = record(point_up, seconds=0.5)
    change(data)
    with pytest.raises(tool.TranscribeError) as caught:
        tool.read_motion(written(tmp_path, "bad.json", data))
    assert caught.value.to_dict()["path"]


@pytest.mark.parametrize(
    "text", ['{"format": "dancepose.motion", "fps": NaN}', '{"format": 1, "format": 2}', "[]", "{", "\xff"]
)
def test_a_record_with_a_non_finite_number_or_a_repeated_key_is_refused(tmp_path, text):
    (tmp_path / "text.json").write_bytes(text.encode("latin-1"))
    with pytest.raises(tool.TranscribeError):
        tool.read_motion(tmp_path / "text.json")


def test_a_record_over_the_byte_bound_or_unreadable_is_refused(tmp_path, monkeypatch):
    with pytest.raises(tool.TranscribeError, match="cannot read"):
        tool.read_motion(tmp_path / "missing.json")
    monkeypatch.setattr(tool, "MAX_MOTION_BYTES", 10)
    with pytest.raises(tool.TranscribeError, match="over 10 bytes"):
        tool.read_motion(written(tmp_path, "big.json", {"format": "dancepose.motion"}))


# --- the windows -----------------------------------------------------------------------------------------------------


def test_a_window_list_reads_in_order(tmp_path):
    found = tool.read_windows(written(tmp_path, "w.json", windows(("a-move", 0.0, 1.0), ("b-move", 1.0, 2.5))))
    assert [w.name for w in found] == ["a-move", "b-move"]
    assert found[1] == tool.Window("b-move", "p1", 1.0, 2.5, 2, 2)


@pytest.mark.parametrize(
    "change",
    [
        lambda w: w.update(schema="srstudio.dance-windows/2.0.0"),
        lambda w: w.update(extra=1),
        lambda w: w["source"].update(sha256="abc"),
        lambda w: w["windows"].clear(),
        lambda w: w["windows"][0].update(name="Bad"),
        lambda w: w["windows"].append(dict(w["windows"][0])),  # a name twice
        lambda w: w["windows"][0].update(end_s=0.1),  # shorter than a quarter second
        lambda w: w["windows"][0].update(end_s=20.0),  # longer than eight seconds
        lambda w: w["windows"][0].update(seen=0),
        lambda w: w["windows"][0].update(seen=1.5),
        lambda w: w["windows"][0].pop("dancers"),
    ],
)
def test_a_malformed_window_list_is_refused_at_a_path(tmp_path, change):
    data = windows(("a-move", 0.0, 1.0))
    change(data)
    with pytest.raises(tool.TranscribeError) as caught:
        tool.read_windows(written(tmp_path, "bad.json", data))
    assert caught.value.to_dict()["path"]


# --- the measured body -----------------------------------------------------------------------------------------------


def test_the_measured_body_is_the_skeletons_own_points_whatever_the_facing(motion, point_up):
    """Axes, facing, hip centre and torso scale all undone: what the estimator saw is what the skeleton did."""
    window = tool.Window("strike", "p1", 0.0, 1.0, 2, 2)
    body = tool.measured_body(motion, window, 5)
    for k, t in enumerate(np.linspace(0.0, 1.0, 5)):
        points = skeleton_points(dance.sample(point_up, GROOVE, float(t)))
        expected = points * (ds.torso_head_radii() / float(ds._torso(points[None])[0]))
        assert np.allclose(body[k], expected, atol=1e-6)


def test_the_measured_body_is_refused_when_the_track_is_missing_or_no_person(point_up, tmp_path, motion):
    with pytest.raises(tool.TranscribeError, match="not seen"):
        tool.measured_body(motion, tool.Window("late", "p1", 2.0, 4.0, 2, 2), 4)
    with pytest.raises(tool.TranscribeError, match="not seen"):
        tool.measured_body(motion, tool.Window("other", "p9", 0.0, 1.0, 2, 2), 4)
    giant = record(point_up, seconds=1.0)
    for frame in giant["frames"]:
        p = frame["persons"]["p1"]
        p["world_m"] = [[v * 4 for v in row] for row in p["world_m"]]
        p["aux_world_m"] = [[v * 4 for v in row] for row in p["aux_world_m"]]
    with pytest.raises(tool.TranscribeError, match="no person"):
        tool.measured_body(
            tool.read_motion(written(tmp_path, "giant.json", giant)), tool.Window("g", "p1", 0.0, 0.5, 2, 2), 4
        )
    shaky = record(point_up, seconds=1.0)
    p = shaky["frames"][4]["persons"]["p1"]  # the second of four samples over half a second
    p["world_m"] = [[v * 1.6 for v in row] for row in p["world_m"]]
    with pytest.raises(tool.TranscribeError, match="off the window's median"):
        tool.measured_body(
            tool.read_motion(written(tmp_path, "shaky.json", shaky)), tool.Window("s", "p1", 0.0, 0.5, 2, 2), 4
        )
    with pytest.raises(tool.TranscribeError, match="samples"):
        tool.measured_body(motion, tool.Window("few", "p1", 0.0, 1.0, 2, 2), 2)


# --- the bounds and the fit ------------------------------------------------------------------------------------------


def test_the_bounds_keep_every_preset_inside_its_limits_from_its_own_rest_pose():
    limits = tool.bounds()
    for target in tool.TARGETS:
        low, high = limits.low[target], limits.high[target]
        assert low < high
        mirror, sign = dance.mirrored(target, 1.0)
        for name in sk.PRESETS:
            profile = sk.preset(name)
            rest = sk.rest_pose(profile)
            for key, value in ((target, low), (target, high), (mirror, sign * low), (mirror, sign * high)):
                if key in profile.controls:
                    lo, hi = profile.limits_of(key)
                    assert lo - 1e-9 <= rest.value(key) + value <= hi + 1e-9, (name, key, value)


def test_settling_keeps_the_extremes_inside_the_bounds_and_drops_the_unseen():
    assert tool._settle(0.5, 0.1, -1.0, 1.0) == (0.3, 0.2)
    assert tool._settle(0.31, 0.3, -1.0, 1.0) == (0.305, 0.0)  # a swing under MIN_AMPLITUDE holds its middle
    assert tool._settle(0.01, -0.01, -1.0, 1.0) == (0.0, 0.0)  # nothing to see
    assert tool._settle(0.01, -0.01, 0.005, 1.0)[0] >= 0.005  # a bias of nothing is not inside: it stays
    for hit, far, low, high in [
        (0.99996, -0.99996, -1.0, 1.0),  # rounding would reach the bound exactly
        (0.0872665, -2.6, -2.61799, 0.0872665),  # the bound is not a four-place number: never round up to it
        (-1.3962634, 0.2, -1.3962634, 1.3962634),
        (0.5235988, 0.1, -2.33874, 0.5235988),
    ]:
        bias, amplitude = tool._settle(hit, far, low, high)
        assert low + tool.MARGIN <= bias - abs(amplitude) and bias + abs(amplitude) <= high - tool.MARGIN
    with pytest.raises(tool.TranscribeError, match="no value"):
        tool._inward(0.5, 0.50001, 0.50002)


def test_resettling_pulls_an_older_documents_extremes_inside_and_proves_the_move():
    limits = tool.bounds()
    high = limits.high["left_upper_arm.twist_in_out"]
    old = dance.Move(
        "fein-old",
        "feet",
        (
            dance.Pattern("left_upper_arm.twist_in_out", amplitude=0.2, bias=round(high, 4) - 0.2, cycles=0.25),
            dance.Pattern("neck.turn_left_right", amplitude=0.0, bias=0.005),  # a hold of nothing, dropped
        ),
        loop_beats=4.0,
        contacts=(dance.Contact("left_foot", 0, 4), dance.Contact("right_foot", 0, 4)),
    )
    new = tool.resettled(old, limits)
    assert [p.target for p in new.patterns] == ["left_upper_arm.twist_in_out"]
    p = new.patterns[0]
    assert p.bias + p.amplitude <= high - tool.MARGIN and p.bias + p.amplitude > high - 1e-3
    assert new.name == old.name and new.loop_beats == old.loop_beats
    with pytest.raises(tool.TranscribeError, match="nothing is left"):
        tool.resettled(replace(old, patterns=old.patterns[1:]), limits)
    foreign = (dance.Pattern("head.turn_left_right", amplitude=0.1),)
    with pytest.raises(tool.TranscribeError, match="not a target"):
        tool.resettled(replace(old, patterns=foreign), limits)


def test_the_prover_reads_every_patterns_own_extremes_not_only_the_grid():
    limits = tool.bounds()
    high = limits.high["right_upper_arm.down_up"]
    hit = dance.Pattern("right_upper_arm.down_up", amplitude=0.3, bias=high - 0.3 + 1e-4, cycles=0.25, phase=0.013)
    contacts = (dance.Contact("left_foot", 0, 4), dance.Contact("right_foot", 0, 4))
    move = dance.Move("fein-edge", "feet", (hit,), loop_beats=4.0, contacts=contacts)
    assert any(abs(t - 0.013 * 0.5) < 1e-9 for t in tool._extremes(move, 0.5))
    with pytest.raises(tool.TranscribeError, match="leaves"):
        tool.prove(move)


def test_a_fit_moves_from_rest_toward_the_measured_body_and_proves_on_every_preset(motion):
    window = tool.Window("fein-test", "p1", 0.0, 1.0, 3, 2)
    body = tool.measured_body(motion, window, 4)
    fitter = tool.Fitter(body, tool.bounds())
    x0, lo, hi = fitter.start()
    assert np.all(lo <= x0) and np.all(x0 <= hi)
    params, rms = fitter.fit(2)
    assert np.all(lo <= params) and np.all(params <= hi)
    assert rms < fitter.rms(x0)
    move = tool.move_from(params, window, rms, fitter.limits)
    assert move.name == "fein-test" and move.support == "feet" and move.loop_beats == tool.LOOP_BEATS
    assert {c.foot for c in move.contacts} == {"left_foot", "right_foot"}
    assert all(p.target in tool.TARGETS and p.cycles == tool.CYCLES for p in move.patterns)
    assert "Seen 3 times by 2 dancers" in move.description and f"{rms:.2f} head radii" in move.description
    tool.prove(move)


def test_a_fit_that_leaves_a_presets_limits_is_refused_by_the_proof():
    too_far = dance.Move(
        "over", "feet", (dance.Pattern("left_upper_arm.down_up", 0.0, bias=3.0),),
        loop_beats=4, contacts=(dance.Contact("left_foot", 0, 4), dance.Contact("right_foot", 0, 4)),
    )  # fmt: skip
    with pytest.raises(tool.TranscribeError, match="leaves"):
        tool.prove(too_far)


def test_the_fit_budget_is_bounded(motion):
    body = tool.measured_body(motion, tool.Window("w", "p1", 0.0, 1.0, 2, 2), 4)
    with pytest.raises(tool.TranscribeError, match="max_nfev"):
        tool.Fitter(body, tool.bounds()).fit(0)


# --- the document and the command ------------------------------------------------------------------------------------


def test_the_document_reads_back_as_the_moves_it_was_written_from():
    patterns = (
        dance.Pattern("chest.front_back", 0.1, cycles=0.25, snap=0.3, bias=0.05),
        dance.Pattern("neck.nod_down_up", 0.0, bias=0.1),
    )
    contacts = (dance.Contact("left_foot", 0, 4), dance.Contact("right_foot", 0, 4))
    move = dance.Move("fein-00", "feet", patterns, loop_beats=4, contacts=contacts, description="a test")
    text = tool.document([move])
    top = json.loads(text)
    assert top["schema"] == dance.MOVES_SCHEMA and top["generated_by"]["tool"] == tool.TOOL
    assert dance.parse_moves(text)["fein-00"] == move


def test_the_command_writes_a_library_and_reports_refusals(point_up, tmp_path, capsys):
    motion = written(tmp_path, "motion.json", record(point_up, seconds=1.5))
    rows = written(tmp_path, "windows.json", windows(("fein-a", 0.0, 1.0), ("fein-b", 1.0, 2.5)))
    out = tmp_path / "lib" / "fein.json"
    assert tool.main([str(motion), str(rows), "--out", str(out), "--samples", "4", "--max-nfev", "2"]) == 0
    printed = capsys.readouterr()
    assert "refused fein-b" in printed.err and "not seen" in printed.err
    assert list(dance.load_moves(out)) == ["fein-a"]
    assert tool.main([str(motion), str(rows), "--out", str(out), "--jobs", "0"]) == 2
    assert tool.main([str(tmp_path / "missing.json"), str(rows), "--out", str(out)]) == 1
    assert "cannot read" in capsys.readouterr().err
    # resume keeps what was written and fits only the rest, in the windows' order
    both = written(tmp_path, "both.json", windows(("fein-c", 0.0, 1.0), ("fein-a", 0.2, 1.2)))
    before = dance.load_moves(out)["fein-a"]
    assert tool.main([str(motion), str(both), "--out", str(out), "--samples", "4", "--max-nfev", "2", "--resume"]) == 0
    assert "fitted fein-c" in capsys.readouterr().err
    after = dance.load_moves(out)
    assert list(after) == ["fein-c", "fein-a"] and after["fein-a"] == before
    (tmp_path / "broken.json").write_text("{")
    assert tool.main([str(motion), str(both), "--out", str(tmp_path / "broken.json"), "--resume"]) == 1
    assert "cannot resume" in capsys.readouterr().err
    only_b = written(tmp_path, "b.json", windows(("fein-b", 1.0, 2.5)))
    assert tool.main([str(motion), str(only_b), "--out", str(out), "--samples", "4", "--max-nfev", "2"]) == 1
    assert "no window could be transcribed: fein-b: " in capsys.readouterr().err
