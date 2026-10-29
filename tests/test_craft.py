"""Comic craft: the crash zoom, its whoosh, and the measurement of camera moves and pauses (``srstudio craft``)."""

import json
import math
import subprocess

import pytest
from sr_core.scene import Scene

from srstudio import Canvas, camera, craft, foley
from srstudio.cli import main
from srstudio.music import write_wav

RATE = 8000


def canvas() -> Canvas:
    scene = Scene(version="auto")
    scene.add_project(width=1080, height=1920, fps="30", duration=10, background="#FFFFFF")
    return Canvas(scene)


def document(cv: Canvas) -> bytes:
    return cv.scene.to_bytes()


# -- the crash zoom ---------------------------------------------------------------------------------------------------
def test_a_crash_zoom_holds_then_snaps_onto_the_subject_and_returns_its_cue():
    cv = canvas()
    g = cv.group(cv.comp, "wide-office-angle")
    assert camera.crash_zoom(cv, g, 2.0, 1.8) == 2.0  # the whoosh's cue: the moment the lens starts to move
    moves = craft.moves(document(cv))
    assert moves == [craft.Move("crash", "wide-office-angle", 2.0, 2.15, 1.8, True)]


def test_a_crash_zoom_can_snap_back_out():
    cv = canvas()
    g = cv.group(cv.comp, "location-cafe")
    camera.crash_zoom(cv, g, 1.0, 2.0, back=3.0)
    kinds = [(m.kind, m.ratio) for m in craft.moves(document(cv))]
    assert kinds == [("crash", 2.0), ("crash", 0.5)]


@pytest.mark.parametrize(
    "args, match",
    [
        ((2.0, 1.8), None),
        ((-1.0, 1.8), "at"),
        ((2.0, 0.0), "scale"),
        ((2.0, 1.8, {"duration": 0.6}), "push_in"),  # slower than a snap is a push, not a crash
        ((2.0, 1.8, {"duration": 0.0}), "duration"),
        ((2.0, 1.8, {"back": 2.1}), "back"),
        ((2.0, 1.8, {"start_scale": -1}), "scale"),
    ],
)
def test_a_crash_zoom_refuses_what_is_not_one(args, match):
    cv = canvas()
    g = cv.group(cv.comp, "wide-office-angle")
    *pos, kw = args if isinstance(args[-1], dict) else (*args, {})
    if match is None:
        camera.crash_zoom(cv, g, *pos, **kw)
        return
    with pytest.raises(ValueError, match=match):
        camera.crash_zoom(cv, g, *pos, **kw)


# -- the whoosh -------------------------------------------------------------------------------------------------------
def test_a_whoosh_is_silent_outside_its_cues_and_swells_into_the_landing():
    out = foley.whoosh([1.0], 2.0, rate=RATE)
    assert len(out) == 2 * RATE
    begin, end = RATE, RATE + int(foley.WHOOSH * RATE)
    assert not any(out[:begin]) and not any(out[end:])
    assert math.isclose(max(abs(v) for v in out), foley.PEAK)
    third = (end - begin) // 3
    rms = [math.sqrt(sum(v * v for v in out[a : a + third]) / third) for a in (begin, end - third)]
    assert rms[1] > 2 * rms[0]  # it grows toward the end of the zoom, where the lens lands


def test_a_whoosh_is_the_same_for_the_same_seed_and_differs_for_another():
    assert foley.whoosh([0.1], 1.0, rate=RATE, seed=3) == foley.whoosh([0.1], 1.0, rate=RATE, seed=3)
    assert foley.whoosh([0.1], 1.0, rate=RATE, seed=3) != foley.whoosh([0.1], 1.0, rate=RATE, seed=4)


@pytest.mark.parametrize(
    "kw, match",
    [
        ({"times": [1.9], "duration": 2.0}, "duration"),
        ({"times": [-0.1], "duration": 2.0}, "duration"),
        ({"times": [0.1], "duration": 2.0, "rate": 100}, "rate"),
        ({"times": [0.1], "duration": 2.0, "peak": 1.5}, "peak"),
        ({"times": [0.1], "duration": 2.0, "length": 5.0}, "length"),
    ],
)
def test_a_whoosh_refuses_bad_input(kw, match):
    with pytest.raises(ValueError, match=match):
        foley.whoosh(**kw)


def test_write_whoosh_writes_a_wav(tmp_path):
    path = foley.write_whoosh(tmp_path / "whoosh.wav", [0.2], 1.0, rate=RATE)
    assert path.stat().st_size > 2 * RATE * 0.9


# -- measuring the camera --------------------------------------------------------------------------------------------
def test_moves_tell_a_crash_a_punch_in_and_a_push_apart_and_mark_the_camera():
    cv = canvas()
    camera.zoom_holds(cv, cv.group(cv.comp, "location-reception"), [(0, 1), (3, 1.45)])
    camera.push_in(cv, cv.group(cv.comp, "candidate-reverse-angle"), scale=[(4, 1), (6, 1.5)])
    pop, breath, sig = (cv.group(cv.comp, gid) for gid in ("k12", "breath", "sig-cactus"))
    for prop in ("scaleX", "scaleY"):
        cv.keys(pop, prop, [(5, 1), (5.1, 2.0)], hold=False)  # a prop that pops: a gag
        cv.keys(breath, prop, [(1, 1), (2, 1.05)], hold=False)  # under 15 %: not a move
        cv.keys(sig, prop, [(1, 1), (1.1, 3)], hold=False)  # the signature never counts
    assert craft.moves(document(cv)) == [
        craft.Move("punch-in", "location-reception", 3.0, 3.0, 1.45, True),
        craft.Move("push", "candidate-reverse-angle", 4.0, 6.0, 1.5, True),
        craft.Move("crash", "k12", 5.0, 5.1, 2.0, False),
    ]


def test_moves_inside_a_sequence_are_placed_on_the_episode_clock():
    cv = canvas()
    shots = cv.comp.add_sequence(id="shots", start=1, timeGap=0.5)
    first = shots.add_group(id="shot-01", end=2)
    second = shots.add_group(id="shot-02", start=0.25, end=3)  # its contents keep their clock: shifted by the slot
    shots.add_transition(type="crossfade", from_="shot-01", to="shot-02", duration=0.3)  # moves no shot
    for shot, at in ((first, 0.5), (second, 1.0)):
        frame = cv.group(shot, f"{shot.id}-camera")
        camera.crash_zoom(cv, frame, at, 1.4)
    open_ended = shots.add_group(id="shot-03")  # placed, but with no end what follows it cannot be
    marked = shots.add_group(id="shot-04", startMarker="m", end=1)  # the engine places it on its marker
    after = shots.add_group(id="shot-05", end=1)
    for shot in (open_ended, marked, after):
        camera.crash_zoom(cv, cv.group(shot, f"{shot.id}-camera"), 0.5, 1.4)
    found = {m.group: m.start for m in craft.moves(document(cv)) if m.ratio > 1}
    assert found == {
        "shot-01-camera": 1.5,
        "shot-02-camera": 1 + 2 + 0.5 + 1.0,
        "shot-03-camera": 1 + 2 + 0.5 + 3 + 0.5 + 0.5,
        "shot-04-camera": 0.5,  # on its own clock: craft does not resolve markers
        "shot-05-camera": 0.5,
    }
    assert all(m.camera for m in craft.moves(document(cv)))


def test_a_sequence_time_that_is_not_a_number_is_a_typed_error():
    doc = b'<scene><sequence id="shots" timeGap="soon"><group id="shot-01" end="1"/></sequence></scene>'
    with pytest.raises(craft.CraftError, match="timeGap"):
        craft.moves(doc)


def test_a_near_instant_step_is_a_cut_and_a_spin_is_not_a_zoom():
    cv = canvas()
    cut = [(0, 1), (7.335, 1), (7.336, 1.62)]  # a 1 ms linear step: the cut from a wide to a close-up
    wide = cv.group(cv.comp, "wide-office-angle")
    for prop in ("scaleX", "scaleY"):
        cv.keys(wide, prop, cut, hold=False)
    spin = [(0, 1), (8.5, 1), (8.6, 0.1), (8.7, 1)]  # a turn squeezes only the width
    cv.keys(cv.group(cv.comp, "executive-spin"), "scaleX", spin, hold=False)
    lopsided = cv.group(cv.comp, "shot-close")
    cv.keys(lopsided, "scaleX", [(1, 1), (1.1, 2)], hold=False)
    cv.keys(lopsided, "scaleY", [(1, 1), (1.1, 1)], hold=False)  # a stretch, not a zoom
    assert craft.moves(document(cv)) == [craft.Move("punch-in", "wide-office-angle", 7.336, 7.336, 1.62, True)]


# -- measuring the pauses --------------------------------------------------------------------------------------------
def test_lines_come_from_the_dialogue_or_the_narration(tmp_path):
    (tmp_path / "dialogue.json").write_text(
        json.dumps({"phrases": [{"start": 2.0, "end": 3.0}, {"start": 0.5, "end": 1.5}]})
    )
    assert craft.lines(tmp_path) == [(0.5, 1.5), (2.0, 3.0)]
    (tmp_path / "dialogue.json").unlink()
    items = [
        {"phase": "line", "start": 0.0, "speech_duration": 1.25},
        {"phase": "beat", "start": 1.0, "speech_duration": 9.0},  # not spoken
        {"phase": "line", "start": 4.0, "speech_duration": 1.0},
    ]
    (tmp_path / "narration.json").write_text(json.dumps({"items": items}))
    assert craft.lines(tmp_path) == [(0.0, 1.25), (4.0, 5.0)]


def test_lines_come_from_the_takes_timeline_without_its_effects(tmp_path):
    items = [
        {"id": "01", "actor": "ana", "start": 0.0, "speech_duration": 2.0, "duration": 2.3},
        {"id": "02", "actor": "sfx", "start": 2.3, "speech_duration": 0, "duration": 1.2},  # an effect, not a line
        {"id": "03", "actor": "bo", "start": 3.5, "speech_duration": 1.0, "duration": 2.4},  # held 1.4 s after it
        {"id": "04", "actor": "ana", "start": 5.9, "speech_duration": 0.5, "duration": 0.8},
    ]
    (tmp_path / "timeline.json").write_text(json.dumps({"items": items}))
    assert craft.lines(tmp_path) == [(0.0, 2.0), (3.5, 4.5), (5.9, 6.4)]
    assert craft.pauses(craft.lines(tmp_path), craft.PAUSE) == [(2.0, 3.5), (4.5, 5.9)]


@pytest.mark.parametrize(
    "name, data",
    [
        ("dialogue.json", "{"),
        ("dialogue.json", json.dumps({"phrases": [{"start": "soon", "end": 1}]})),
        ("dialogue.json", json.dumps({"phrases": [{"start": 2, "end": 1}]})),
        ("narration.json", json.dumps({"items": "lines"})),
        ("narration.json", json.dumps({"items": [{"phase": "line", "start": 1}]})),
        ("timeline.json", json.dumps({"items": {"01": {}}})),
        ("timeline.json", json.dumps({"items": ["take"]})),
        ("timeline.json", json.dumps({"items": [{"start": 1}]})),
        ("timeline.json", json.dumps({"items": [{"start": 1, "speech_duration": -1}]})),
    ],
)
def test_unreadable_line_times_are_a_typed_error(tmp_path, name, data):
    (tmp_path / name).write_text(data)
    with pytest.raises(craft.CraftError):
        craft.lines(tmp_path)


def test_a_project_without_spoken_lines_has_none(tmp_path):
    assert craft.lines(tmp_path) == []


def test_pauses_are_the_gaps_between_lines_at_least_the_threshold():
    spoken = [(0.0, 1.0), (1.3, 2.0), (3.6, 4.0), (3.9, 6.0), (8.0, 9.0)]
    assert craft.pauses(spoken) == [(2.0, 3.6), (6.0, 8.0)]
    assert craft.pauses(spoken, threshold=0.25) == [(1.0, 1.3), (2.0, 3.6), (6.0, 8.0)]
    with pytest.raises(ValueError, match="threshold"):
        craft.pauses(spoken, threshold=0)


def test_levels_measure_the_rendered_sound_inside_each_pause(tmp_path):
    rate = 8000
    tone = [0.5 * math.sin(2 * math.pi * 440 * k / rate) for k in range(rate)]
    wav = write_wav(tmp_path / "a.wav", [0.0] * rate + tone, rate)  # 1 s of silence, then 1 s of tone
    quiet, loud = craft.levels(wav, [(0.1, 0.9), (1.1, 1.9)])
    assert quiet == -math.inf or quiet < -60
    assert loud > -20


def test_levels_report_ffmpeg_failures_as_a_typed_error(tmp_path):
    def broken(cmd, **kw):
        return subprocess.CompletedProcess(cmd, 1, "", "no such file\n")

    with pytest.raises(craft.CraftError, match="no such file"):
        craft.levels(tmp_path / "x.mp4", [(0, 1)], run=broken)

    def mute(cmd, **kw):
        return subprocess.CompletedProcess(cmd, 0, "", "nothing measured\n")

    with pytest.raises(craft.CraftError, match="mean_volume"):
        craft.levels(tmp_path / "x.mp4", [(0, 1)], run=mute)
    assert craft.levels(tmp_path / "x.mp4", []) == []


# -- the report and the command ----------------------------------------------------------------------------------------
def project(tmp_path):
    root = tmp_path / "show"
    root.mkdir()
    cv = canvas()
    camera.crash_zoom(cv, cv.group(cv.comp, "wide-office-angle"), 2.0, 1.6)
    (root / "show.scene.xml").write_bytes(document(cv))
    (root / "dialogue.json").write_text(json.dumps({"phrases": [{"start": 0, "end": 1}, {"start": 3, "end": 4}]}))
    return root


def test_measure_reports_moves_and_pauses_with_their_level(tmp_path):
    root = project(tmp_path)
    report = craft.measure(root, levels=lambda video, spans: [-80.0 for _ in spans], video=tmp_path / "v.mp4")
    assert report.slug == "show"
    assert [m.kind for m in report.moves] == ["crash"]
    assert report.pauses == [craft.Pause(1.0, 3.0, -80.0)]
    assert report.pauses[0].quiet
    data = report.to_dict()
    assert data["schema"] == craft.SCHEMA and data["pauses"][0]["quiet"] is True


def test_measure_without_a_video_leaves_levels_unmeasured(tmp_path):
    report = craft.measure(project(tmp_path))
    assert report.pauses == [craft.Pause(1.0, 3.0, None)]
    assert report.pauses[0].quiet is None


def test_measure_needs_the_scene(tmp_path):
    with pytest.raises(craft.CraftError, match="scene"):
        craft.measure(tmp_path)


def test_the_command_prints_moves_and_pauses_and_json(tmp_path, capsys):
    root = project(tmp_path)
    assert main(["craft", str(root)]) == 0
    out = capsys.readouterr().out
    assert "crash" in out and "wide-office-angle" in out and "pause 1.00–3.00" in out
    assert main(["craft", str(root), "--json"]) == 0
    assert json.loads(capsys.readouterr().out)[0]["slug"] == "show"
    assert main(["craft", str(tmp_path / "nothing")]) == 2


def test_the_command_folds_groups_that_make_the_same_move_into_one_line(tmp_path, capsys):
    root = tmp_path / "logo"
    root.mkdir()
    cv = canvas()
    for gid in ("k1", "k2", "k3"):
        g = cv.group(cv.comp, gid)
        for prop in ("scaleX", "scaleY"):
            cv.keys(g, prop, [(4.8, 1), (5.1, 1.6)], hold=False)
    (root / "logo.scene.xml").write_bytes(document(cv))
    assert main(["craft", str(root)]) == 0
    out = capsys.readouterr().out
    assert out.count("push") == 1 and "k1 +2 more" in out
    assert main(["craft", str(root), "--json"]) == 0
    assert len(json.loads(capsys.readouterr().out)[0]["moves"]) == 3  # the data keeps every group
