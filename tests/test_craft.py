"""Comic craft: the crash zoom, its whoosh, and the measurement of camera moves and pauses (``srstudio craft``)."""

import json
import math
import subprocess
import xml.etree.ElementTree as ET

import numpy as np
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


def test_measure_reports_moves_and_pauses_with_their_level(tmp_path, monkeypatch):
    root = project(tmp_path)
    monkeypatch.setattr(craft, "luminance", lambda path: (np.zeros((3, 4, 4)), 30.0))
    report = craft.measure(root, levels=lambda video, spans: [-80.0 for _ in spans], video=tmp_path / "v.mp4")
    assert report.slug == "show"
    assert [m.kind for m in report.moves] == ["crash"]
    assert report.pauses == [craft.Pause(1.0, 3.0, -80.0)]
    assert report.pauses[0].quiet
    data = report.to_dict()
    assert data["schema"] == craft.SCHEMA and data["pauses"][0]["quiet"] is True


def test_a_line_with_no_breath_before_it_is_crowded():
    spoken = [(0.0, 1.0), (1.04, 2.0), (2.5, 3.0), (2.9, 4.0)]
    assert craft.crowded(spoken) == [(1.04, 0.04), (2.9, -0.1)]


def test_a_line_a_breath_after_the_last_is_not_crowded():
    assert craft.crowded([(0.0, 1.0), (1.2, 2.0)]) == []
    assert craft.crowded([]) == [] and craft.crowded([(0.0, 1.0)]) == []


def test_the_report_and_the_command_name_a_crowded_line(tmp_path, monkeypatch, capsys):
    folder = project(tmp_path)
    monkeypatch.setattr(craft, "lines", lambda path: [(0.0, 1.0), (1.05, 2.0)])
    report = craft.measure(folder)
    assert report.crowded == [(1.05, 0.05)]
    assert report.to_dict()["crowded"] == [{"start": 1.05, "gap": 0.05}]
    monkeypatch.setattr(craft, "measure", lambda *a, **k: report)
    assert main(["craft", str(folder)]) == 0
    assert "crowded line at 1.05: 0.05 s after the line before" in capsys.readouterr().out


SHORT_SCENE = """<scene version="1.1">
  <project width="1080" height="1920" fps="30" duration="3"/>
  <metadata title="t" description="t"><accessibility description="t" {check}/></metadata>
  <assets>
    <text id="a" text="NESTED"/><text id="b" text="GROUP"/><text id="c" text="CLAMPED"/><text id="d" text="FINE"/>
    <image id="p" src="p.png"/>
  </assets>
  <composition>
    <group id="ga" start="1" end="2"><layer id="la" asset="a" start="0.2" end="0.7"/></group>
    <group id="gb" start="0.5" end="1"><layer id="lb" asset="b"/></group>
    <layer id="lc" asset="c" start="2.7" end="4"/>
    <layer id="ld" asset="d" start="0" end="2"/>
    <layer id="lp" asset="p" start="0" end="0.1"/>
  </composition>
</scene>"""


def short_scene(check: str = 'legibilityCheck="warn"') -> bytes:
    return SHORT_SCENE.format(check=check).encode()


def test_short_text_agrees_with_the_engine_on_a_scene_it_encoded():
    """scene-render 0.8.0 reported lb at 0.500 s and lc at 0.300 s on this document, and nothing for la, which a group
    closed before it could start, or ld. Windows are absolute, cut by the ancestors and by the project's end."""
    assert craft.short_text(short_scene()) == [
        craft.Short("lb", "GROUP", 0.5, 0.5),
        craft.Short("lc", "CLAMPED", 2.7, 0.3),
    ]


def test_a_stated_minimum_replaces_the_default():
    assert [s.layer for s in craft.short_text(short_scene('legibilityCheck="warn" minDisplayTime="0.4"'))] == ["lc"]


@pytest.mark.parametrize("check", ["", 'legibilityCheck="off"'])
def test_a_scene_with_the_check_off_has_no_short_text(check):
    assert craft.short_text(short_scene(check)) == []


def test_short_text_refuses_what_is_not_a_scene():
    with pytest.raises(craft.CraftError, match="not a scene"):
        craft.short_text(b"<scene")


def test_a_window_counts_whole_frames_as_the_engine_does():
    window = b'start="0" end="2"'
    assert craft.Short("ld", "FINE", 0.0, 0.8) in craft.short_text(
        short_scene().replace(window, b'start="0" end="0.79"')
    )
    assert "ld" not in [s.layer for s in craft.short_text(short_scene().replace(window, b'start="0" end="0.82"'))]


def test_the_report_and_the_command_name_short_text(tmp_path, monkeypatch, capsys):
    folder = project(tmp_path)
    (folder / f"{folder.name}.scene.xml").write_bytes(short_scene())
    report = craft.measure(folder)
    assert [s["layer"] for s in report.to_dict()["short"]] == ["lb", "lc"]
    monkeypatch.setattr(craft, "measure", lambda *a, **k: report)
    assert main(["craft", str(folder)]) == 0
    assert "short text at 0.50: 'GROUP' for 0.500 s" in capsys.readouterr().out


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


def caption_layers(*layers):
    body = "".join(f'<layer id="{i}-caption" start="{a}" end="{b}" y="{y}" asset="{i}"/>' for i, a, b, y in layers)
    return f"<scene>{body}</scene>".encode()


def test_two_captions_in_one_band_at_once_are_named():
    found = craft.doubled_captions(caption_layers(("a", 1.0, 2.1, 1420), ("b", 2.0, 3.0, 1420)))
    assert found == ["a-caption and b-caption share the band for 0.10 s"]


def test_captions_that_meet_or_sit_in_other_bands_are_not_doubled():
    assert craft.doubled_captions(caption_layers(("a", 1.0, 2.0, 1420), ("b", 2.0, 3.0, 1420))) == []
    assert craft.doubled_captions(caption_layers(("a", 1.0, 2.5, 300), ("b", 2.0, 3.0, 1420))) == []


def test_doubled_captions_refuse_what_is_not_a_scene():
    with pytest.raises(craft.CraftError, match="not a scene"):
        craft.doubled_captions(b"<scene")


# -- the opening ------------------------------------------------------------------------------------------------------
def test_the_opening_counts_the_silence_before_the_first_line():
    assert craft.opening_silences([(3.0, 4.5)]) == [(0.0, 3.0)]


def test_the_opening_counts_gaps_and_the_silence_after_the_last_line():
    assert craft.opening_silences([(0.0, 1.0), (2.5, 3.0)]) == [(1.0, 2.5), (3.0, 5.0)]


def test_a_gap_is_cut_off_where_the_opening_ends():
    assert craft.opening_silences([(0.0, 3.5), (9.0, 10.0)]) == [(3.5, 5.0)]


def test_lines_after_the_opening_leave_it_silent():
    assert craft.opening_silences([(6.0, 7.0)]) == [(0.0, 5.0)]


def test_no_lines_at_all_is_a_silent_opening():
    assert craft.opening_silences([]) == [(0.0, 5.0)]


def test_a_gap_under_the_limit_is_no_silence():
    assert craft.opening_silences([(0.5, 2.0), (2.5, 5.0)]) == []


def test_overlapping_lines_are_one_line():
    assert craft.opening_silences([(0.0, 4.0), (1.0, 2.0), (4.5, 5.5)]) == []


@pytest.mark.parametrize("kw", [{"within": 0}, {"limit": 0}, {"limit": float("nan")}])
def test_an_opening_that_is_not_one_is_refused(kw):
    with pytest.raises(craft.CraftError):
        craft.opening_silences([], **kw)


def test_measure_reports_the_opening_and_the_command_says_so(tmp_path, capsys):
    folder = project(tmp_path)
    report = craft.measure(folder)
    assert report.to_dict()["schema"] == craft.SCHEMA
    assert report.to_dict()["opening"] == [{"start": a, "end": b} for a, b in report.opening]
    assert main(["craft", str(folder)]) == 0
    assert "opening" in capsys.readouterr().out


def steady(frames: int = 60) -> list:
    return [np.full((4, 4), 0.5) for _ in range(frames)]


def strobe(rate: float, seconds: float = 2.0, fps: int = 30) -> "np.ndarray":
    """A picture that swings from dark to bright ``rate`` times a second."""
    count = round(seconds * fps)
    wave = (np.sin(2 * np.pi * rate * np.arange(count) / fps) > 0).astype(float)
    return np.broadcast_to(wave[:, None, None] * 0.9, (count, 4, 4)).copy()


def test_a_steady_picture_does_not_flash():
    assert craft.flashing(np.array(steady()), 30.0) == []


def test_five_flashes_a_second_are_found_and_placed():
    found = craft.flashing(strobe(5.0), 30.0)
    assert len(found) == 1 and found[0].share == 1.0
    assert 0.0 <= found[0].start < found[0].end <= 2.0


def test_three_flashes_a_second_are_within_the_limit():
    assert craft.flashing(strobe(3.0), 30.0) == []


def test_flashes_too_small_to_matter_are_left_out():
    picture = strobe(5.0)
    calm = np.full_like(picture, 0.5)
    calm[:, 0, 0] = picture[:, 0, 0]  # one pixel in sixteen
    assert craft.flashing(calm, 30.0, share=0.1) == []


def test_a_swing_over_bright_ground_is_not_a_flash():
    """Above 0.8 of white the guideline does not count the swing: both states are bright."""
    assert craft.flashing(0.85 + strobe(5.0) / 9.0, 30.0) == []


def test_two_bad_stretches_are_two_windows():
    bad = strobe(5.0, seconds=1.5)
    calm = np.zeros((90, 4, 4))
    found = craft.flashing(np.concatenate([bad, calm, bad]), 30.0)
    assert len(found) == 2 and found[0].end <= found[1].start


def test_a_picture_with_no_frames_is_refused():
    with pytest.raises(craft.CraftError):
        craft.flashing(np.zeros((0, 4, 4)), 30.0)


def test_luminance_refuses_a_video_ffmpeg_cannot_read(tmp_path):
    with pytest.raises(craft.CraftError):
        craft.luminance(tmp_path / "missing.mp4")


def test_measure_lists_the_flashes_of_a_render_and_the_command_says_so(tmp_path, monkeypatch, capsys):
    folder = project(tmp_path)
    monkeypatch.setattr(craft, "luminance", lambda path: (strobe(5.0), 30.0))
    report = craft.measure(folder, video=tmp_path / "v.mp4", levels=lambda path, spans: [-40.0] * len(spans))
    assert report.to_dict()["schema"] == craft.SCHEMA == "1.6.0"
    assert report.to_dict()["flashes"][0]["share"] == 1.0
    monkeypatch.setattr(craft, "measure", lambda *a, **k: report)
    assert main(["craft", str(folder)]) == 0
    assert "flash" in capsys.readouterr().out


def still(seconds: float, level: float = 0.5, fps: float = 30.0) -> np.ndarray:
    """A picture that does not change."""
    return np.full((round(seconds * fps), 40, 40), level)


def test_a_picture_that_stands_is_one_hold():
    assert craft.holding(still(3.0), 30.0) == [craft.Hold(0.0, 3.0)]


def test_a_moving_picture_holds_nowhere():
    frames = still(3.0)
    for i in range(len(frames)):
        frames[i, i % 40, :] = 1.0
    assert craft.holding(frames, 30.0) == []


def test_a_hold_shorter_than_the_least_is_not_listed():
    assert craft.holding(still(0.9), 30.0) == []


def test_a_cut_ends_a_hold_and_starts_the_next():
    frames = np.concatenate([still(1.5, 0.2), still(2.0, 0.8)])
    assert craft.holding(frames, 30.0) == [craft.Hold(0.0, 1.5), craft.Hold(1.5, 3.5)]


def test_a_keyframe_does_not_break_a_hold():
    """An encoder repaints the picture a level or two at each keyframe: frame to frame that looks like change."""
    frames = still(4.0)
    frames[60:] += 0.002
    assert craft.holding(frames, 30.0) == [craft.Hold(0.0, 4.0)]


def test_a_slow_change_breaks_a_hold_though_no_two_frames_differ_much():
    frames = still(4.0, 0.2) + (np.arange(120) * 0.001)[:, None, None]
    assert craft.holding(frames, 30.0) == []


def test_a_small_thing_moving_breaks_a_hold():
    frames = still(3.0)
    frames[45:, 0, 0] = 1.0  # one pixel in 1,600, and still more than the picture's share at this scan
    frames[45:, 0, 1:4] = 1.0
    frames[45:, 1, 0:4] = 1.0
    assert craft.holding(frames, 30.0) == [craft.Hold(0.0, 1.5), craft.Hold(1.5, 3.0)]


def test_a_picture_with_no_frames_has_no_holds():
    with pytest.raises(craft.CraftError):
        craft.holding(np.zeros((0, 4, 4)), 30.0)


def test_measure_lists_the_holds_of_a_render_and_the_command_says_so(tmp_path, monkeypatch, capsys):
    folder = project(tmp_path)
    monkeypatch.setattr(craft, "luminance", lambda path: (still(2.5), 30.0))
    report = craft.measure(folder, video=tmp_path / "v.mp4", levels=lambda path, spans: [-40.0] * len(spans))
    assert report.to_dict()["holds"] == [{"start": 0.0, "end": 2.5}]
    monkeypatch.setattr(craft, "measure", lambda *a, **k: report)
    assert main(["craft", str(folder)]) == 0
    assert "hold 0.00–2.50  2.50 s" in capsys.readouterr().out


# -- a line the recording cut short -----------------------------------------------------------------------------------
def narrated(tmp_path, items) -> object:
    root = project(tmp_path)
    (root / "dialogue.json").unlink()
    (root / "narration.json").write_text(json.dumps({"items": items}))
    return root


def said(id: str = "01", speech: float = 2.0, kept: float = 2.0, cut: bool = False, phase: str = "line") -> dict:
    return {"id": id, "phase": phase, "start": 0.0, "speech_duration": speech, "duration": kept, "cut": cut}


def test_a_line_cut_short_is_reported_with_what_it_lost(tmp_path):
    root = narrated(tmp_path, [said("01"), said("03", 2.5, 2.41, True)])
    assert craft.clipped(root) == [("03", 0.09)]
    assert craft.measure(root).clipped == [("03", 0.09)]
    assert craft.measure(root).to_dict()["clipped"] == [{"line": "03", "lost": 0.09}]


def test_the_command_names_the_line_that_lost_its_tail(tmp_path, capsys):
    root = narrated(tmp_path, [said("03", 2.5, 2.41, True)])
    assert main(["craft", str(root)]) == 0
    assert "clipped line 03: 0.09 s of speech lost" in capsys.readouterr().out


def test_a_line_that_ran_whole_is_not_reported(tmp_path):
    assert craft.clipped(narrated(tmp_path, [said(), said("02", 1.0, 1.4)])) == []


def test_an_episode_without_a_narration_has_nothing_to_clip(tmp_path):
    assert craft.clipped(project(tmp_path)) == []


def test_an_item_that_is_not_a_line_is_not_read(tmp_path):
    assert craft.clipped(narrated(tmp_path, [{"phase": "intro"}, said()])) == []


@pytest.mark.parametrize(
    "item",
    [
        "a string",
        {"phase": "line", "id": "01", "speech_duration": 1.0, "duration": 1.0},
        {"phase": "line", "id": "01", "speech_duration": 1.0, "duration": 1.0, "cut": "yes"},
        {"phase": "line", "id": "01", "speech_duration": "long", "duration": 1.0, "cut": True},
        {"phase": "line", "id": 7, "speech_duration": 1.0, "duration": 0.5, "cut": True},
    ],
)
def test_a_narration_that_cannot_be_read_is_an_error_not_a_clean_report(tmp_path, item):
    with pytest.raises(craft.CraftError):
        craft.clipped(narrated(tmp_path, [item]))


def test_items_that_are_no_list_are_an_error(tmp_path):
    with pytest.raises(craft.CraftError, match="items must be a list"):
        craft.clipped(narrated(tmp_path, {"phase": "line"}))


# -- when the first statement ends ------------------------------------------------------------------------------------
def spoken(tmp_path, *takes) -> object:
    (tmp_path / "voiced").mkdir(exist_ok=True)
    (tmp_path / "voiced" / "speech.json").write_text(json.dumps({"end": 9.0, "takes": list(takes)}))
    return tmp_path


def take(id: str, at: float, text: str, ends: list[float]) -> dict:
    return {"id": id, "who": "vera", "at": at, "kept": ends[-1], "characters": list(text), "starts": ends, "ends": ends}


def test_a_statement_ends_on_its_last_letter_not_on_the_full_stop(tmp_path):
    root = spoken(tmp_path, take("01", 0.0, "In total.", [0.1 * n for n in range(1, 10)]))
    assert craft.statement(root, ("01",)) == craft.Statement("In total.", 0.8)


def test_a_statement_of_two_lines_ends_with_the_second_in_the_masters_time(tmp_path):
    root = spoken(tmp_path, take("01", 0.0, "Hi.", [0.1, 0.2, 0.3]), take("02", 2.0, "No!", [0.1, 0.2, 0.3]))
    assert craft.statement(root, ("01", "02")) == craft.Statement("Hi. No!", 2.2)


def test_only_the_named_lines_count(tmp_path):
    root = spoken(tmp_path, take("01", 0.0, "Hi.", [0.1, 0.2, 0.3]), take("02", 2.0, "No!", [0.1, 0.2, 0.3]))
    assert craft.statement(root, ("01",)).end == 0.2


@pytest.mark.parametrize(
    "lines, takes, needle",
    [
        (("09",), [take("01", 0.0, "Hi.", [0.1, 0.2, 0.3])], "no take"),
        ((), [take("01", 0.0, "Hi.", [0.1, 0.2, 0.3])], "at least one line"),
        (("01",), [take("01", 0.0, "...", [0.1, 0.2, 0.3])], "no letters"),
        (("01",), [{"id": "01", "at": 0.0, "characters": ["H"], "ends": []}], "a time for every letter"),
        (("01",), [take("01", "soon", "Hi.", [0.1, 0.2, 0.3])], "must be a number"),  # type: ignore[arg-type]
    ],
)
def test_a_statement_that_cannot_be_measured_is_an_error_never_a_pass(tmp_path, lines, takes, needle):
    with pytest.raises(craft.CraftError, match=needle):
        craft.statement(spoken(tmp_path, *takes), lines)


def test_a_project_without_takes_is_an_error(tmp_path):
    with pytest.raises(craft.CraftError):
        craft.statement(tmp_path, ("01",))


# -- the hush ------------------------------------------------------------------------------------------------
def hushed(spoken, gain=-10.0, **kw):
    cv = canvas()
    track = cv.group(cv.comp, "bed")
    craft.hush(cv, track, spoken, gain, **kw)
    animate = ET.fromstring(cv.scene.to_bytes(layout="pretty")).find(".//animate[@property='gain']")
    assert animate.get("defaultInterpolation") == "linear" and animate.get("timeBase") is None
    return [(float(k.get("time")), float(k.get("value"))) for k in animate.findall("key")]


def test_a_bed_stays_flat_through_a_gap_under_the_threshold_and_drops_through_a_pause():
    assert hushed([(0.0, 2.0), (2.5, 4.0)]) == [(0.0, -10.0)]
    assert hushed([(0.0, 2.0), (4.0, 5.0)]) == [(0.0, -10.0), (2.0, -10.0), (2.15, -22.0), (3.85, -22.0), (4.0, -10.0)]


def test_a_short_hold_keeps_its_ramps_inside_it():
    keys = hushed([(0.0, 1.0), (1.3, 2.0)], threshold=0.25, ramp=0.15)
    assert keys == [(0.0, -10.0), (1.0, -10.0), (1.1, -22.0), (1.2, -22.0), (1.3, -10.0)]


@pytest.mark.parametrize("kw, match", [({"drop": 3.0}, "drop"), ({"drop": 0}, "drop"), ({"ramp": 0}, "ramp")])
def test_a_hush_refuses_a_rise_or_no_ramp(kw, match):
    with pytest.raises(craft.CraftError, match=match):
        hushed([(0.0, 1.0)], **kw)
