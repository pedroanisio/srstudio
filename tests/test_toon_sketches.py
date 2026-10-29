"""The Toon sketches (The Report, Logo Bigger, Quick Question) as data, and the build they share: shots, badges,
dressing, the lip-sync tracks, the recording run's effects and manifest (the sketch machinery itself is tested in
test_sketch.py)."""

import json
import sys
import xml.etree.ElementTree as ET
from dataclasses import replace
from pathlib import Path

import pytest
from sr_core.scene import Scene

from srstudio import PEACH, TOON, Canvas, flat_counter, sketch, toon, toon_dinner
from srstudio.narration import effect_cues, manifest_duration

EPISODES = Path(__file__).resolve().parent.parent / "episodes"


def measure(text: str, size: float) -> float:
    return 0.5 * size * len(text)


@pytest.fixture(scope="module")
def mods():
    sys.path.insert(0, str(EPISODES))
    try:
        import logo_bigger_data
        import quick_question_data
        import the_report_data
        from srstudio import toon_sketch

        return toon_sketch, the_report_data, logo_bigger_data, quick_question_data
    finally:
        sys.path.pop(0)


def canvas(duration: float) -> Canvas:
    scene = Scene(version="auto")
    scene.add_project(width=1080, height=1920, fps="24", duration=duration, background=PEACH.background)
    return Canvas(scene, PEACH, font_asset="comic-neue", namer=flat_counter("k"))


def tree(cv: Canvas):
    return ET.fromstring(cv.scene.to_bytes(layout="pretty"))


CASTS = {1: {"dog", "frog"}, 2: {"dog", "frog"}, 3: {"bear", "rabbit"}}


@pytest.mark.parametrize("which", [1, 2, 3])
def test_each_sketch_validates_opens_on_a_question_and_holds_before_its_punchline(mods, which):
    data = mods[which]
    data.validate()
    sk = data.SKETCH
    # the hook: a question, captioned from the first frame, spoken within two seconds
    assert sk.lines[0].text.endswith("?") and sk.beats[0].start == 0 and sk.beats[0].line == 0
    assert sk.beats[1].start <= 2.5
    # the voices are distinct premade voices and every speaker with a character plays a different one
    voices = [s.voice.id for s in sk.speakers]
    assert len(set(voices)) == len(voices) and all(s.voice.name for s in sk.speakers)
    # both coworkers appear, and the picture cuts between them more than once
    apps = sketch.appearances(sk.beats, sk.end)
    assert {a.who for a in apps} == CASTS[which] and len(apps) >= 6
    # a silent hold of at least 1.2 s before the punchline (the last spoken beat), and the sting after it
    spoken = [b for b in sk.beats if b.spoken]
    last = sk.beats.index(spoken[-1])
    before = sk.beats.index(spoken[-2])
    assert last - before >= 2 and spoken[-1].start - sk.beats[before + 1].start >= 1.2
    assert any(b.event == "hangup" and b.start > spoken[-1].start for b in sk.beats)
    assert sk.end - sk.beats[-1].start >= sketch.TAIL_AFTER_LAST
    # the caption script carries the line's speaker so the pills can be tinted
    cues = sketch.cues(sk.beats, sk.end, sk.lines)
    assert {c["speaker"] for c in cues if c["speaker"] in data.TINTS} == set(data.TINTS)
    assert toon.parse_script(cues)


def test_the_report_refuses_events_its_props_cannot_do(mods):
    _, data, *_ = mods
    sk = data.SKETCH
    beats = list(sk.beats)
    i = next(k for k, b in enumerate(beats) if b.event == "toast:0")
    with pytest.raises(sketch.SketchError, match="not one of"):
        data.validate(replace(sk, beats=tuple([*beats[:i], replace(beats[i], event="toast:9"), *beats[i + 1 :]])))
    j = next(k for k, b in enumerate(beats) if b.who == "frog")
    with pytest.raises(sketch.SketchError, match="off screen"):
        data.validate(replace(sk, beats=tuple([*beats[:j], replace(beats[j], event="toast:0"), *beats[j + 1 :]])))
    k = next(k for k, b in enumerate(beats) if b.event.startswith("clock:"))
    with pytest.raises(sketch.SketchError, match="backwards"):
        data.validate(replace(sk, beats=tuple([*beats[:k], replace(beats[k], event="clock:08:00"), *beats[k + 1 :]])))
    with pytest.raises(sketch.SketchError, match="exactly once"):
        data.validate(replace(sk, beats=tuple(replace(b, event="") if b.event == "hangup" else b for b in beats)))
    with pytest.raises(sketch.SketchError, match="unknown events"):
        data.validate(replace(sk, beats=tuple([replace(beats[0], event="fireworks"), *beats[1:]])))
    # the toasts of a shot: replaced by the next, gone with the shot
    app = next(a for a in sketch.appearances(sk.beats, sk.end) if a.start <= 10.0 < a.end)
    toasts = data.toasts_in(sk.beats, app)
    assert [(t.start, t.end, t.text) for t in toasts] == [
        (10.0, 12.6, data.TOASTS[0][1]),
        (12.6, app.end, data.TOASTS[1][1]),
    ]


def test_logo_bigger_refuses_events_its_logo_cannot_do(mods):
    _, _, data, _ = mods
    sk = data.SKETCH
    beats = list(sk.beats)
    assert data.logo_sizes(sk.beats) == [(0.0, 1.0), (4.8, 1.6), (8.3, 2.3), (15.1, 4.6), (26.0, 1.0)]
    assert data.shadow_span(sk.beats, sk.end) == (20.6, 26.0)
    i = next(k for k, b in enumerate(beats) if b.event == "logo:1.6")
    with pytest.raises(sketch.SketchError, match="take a number"):
        data.validate(replace(sk, beats=tuple([*beats[:i], replace(beats[i], event="logo:huge"), *beats[i + 1 :]])))
    with pytest.raises(toon.ToonDataError, match="positive"):
        data.validate(replace(sk, beats=tuple([*beats[:i], replace(beats[i], event="logo:0"), *beats[i + 1 :]])))
    j = next(k for k, b in enumerate(beats) if b.who == "dog" and not b.event)
    with pytest.raises(sketch.SketchError, match="off screen"):
        data.validate(replace(sk, beats=tuple([*beats[:j], replace(beats[j], event="logo:3"), *beats[j + 1 :]])))
    with pytest.raises(sketch.SketchError, match="pops exactly once"):
        data.validate(replace(sk, beats=tuple(replace(b, event="") if b.event == "pop" else b for b in beats)))
    assert data.shadow_span([replace(beats[0], event="pop")], 5.0) == (0.0, 5.0)
    assert data.shadow_span(beats[:2], 5.0) is None


def test_badge_spans_follow_the_hangup(mods):
    build, data, *_ = mods
    beats = [
        sketch.Beat(0.0, "dog", "", "wide", "flat", "desk"),
        sketch.Beat(4.0, "frog", "", "wide", "flat", "desk", event="hangup"),
    ]
    texts = {"dog": "Fern calling"}
    app = sketch.Appearance("dog", 0.0, 2.0, [])
    assert build.badge_spans(beats, app, texts, "Call ended", "hangup") == [(0.0, 2.0, "Fern calling")]
    assert build.badge_spans(beats, sketch.Appearance("dog", 2.0, 6.0, []), texts, "Call ended", "hangup") == [
        (2.0, 4.0, "Fern calling"),
        (4.0, 6.0, "Call ended"),
    ]
    assert build.badge_spans(beats, sketch.Appearance("frog", 4.0, 6.0, []), texts, "Call ended", "hangup") == [
        (4.0, 6.0, "Call ended")
    ]
    assert build.badge_spans(beats, sketch.Appearance("frog", 0.0, 2.0, []), texts, "Call ended", "hangup") == []
    assert build.badge_spans(beats[:1], sketch.Appearance("frog", 0.0, 2.0, []), texts, "Call ended", "hangup") == []


@pytest.mark.parametrize("which", [1, 2, 3])
def test_dressing_a_shot_draws_its_set_props_and_badge(mods, which):
    build, *datas = mods
    data = datas[which - 1]
    sk = data.SKETCH
    for app in sketch.appearances(sk.beats, sk.end)[:4]:
        cv = canvas(sk.end)
        back, front = cv.group(cv.comp, "back"), cv.group(cv.comp, "front")
        data.dress(build.Shot(cv, app, back, front, sk.beats, sk.end, measure))
        t = tree(cv)
        texts = [a.get("text") for a in t.iter("text")]
        shapes = list(t.find("composition").iter("shape"))
        assert shapes and shapes[0].get("width") == "1080"  # the set's wall comes first, behind everything
        if app.who == "bear":
            assert set(data.NOTES) <= set(texts) and "PIP CALLING" in texts
            assert len([a for a in t.iter("animate") if a.get("property") == "rotation"]) == 2  # the clock
        elif app.who == "rabbit":
            assert data.BOARD in texts and "BRUNO ON THE LINE" in texts
        elif app.who == "dog":
            if which == 1:
                assert set(data.NOTES) <= set(texts) and "FERN CALLING" in texts
                assert len([a for a in t.iter("animate") if a.get("property") == "rotation"]) == 2  # the clock
            else:
                assert texts == []  # Rex's room carries no badge in Logo Bigger
        else:
            assert data.BOARD in texts and any(x in texts for x in ("REX ON THE LINE", "CLIENT ON SPEAKER"))
            if which == 2:
                assert [a.get("property") for a in t.iter("animate")].count("scaleX") == 2  # the logo and its shadow


def test_the_recording_run_writes_the_effects_and_the_manifest(mods, tmp_path, monkeypatch):
    build, data, *_ = mods
    sk = data.SKETCH
    spans = [(a, min(b, a + 1.2)) for a, b in sketch.line_spans(sk)]  # each line heard for 1.2 s at most
    fake = sketch.Recorded(items=[], beats=list(sk.beats), end=sk.end, speech=spans, voices={}, heard=[])
    seen = {}

    def record(sketch_, root, client, *, key, ffmpeg, mouth):
        seen.update(sketch=sketch_, root=root, key=key, ffmpeg=ffmpeg, mouth=mouth)
        return fake

    monkeypatch.setattr(sketch, "record", record)
    with pytest.raises(SystemExit, match="SRSTUDIO_ALLOW_CLOUD"):
        build.record_episode(sk, tmp_path, {}, "ffmpeg", 7, "note")
    manifest = build.record_episode(sk, tmp_path, {"SRSTUDIO_ALLOW_CLOUD": "1"}, "ffmpeg", 7, "note")
    assert seen["sketch"] is sk and seen["root"] == tmp_path and seen["key"] == "" and seen["ffmpeg"] == "ffmpeg"
    assert seen["mouth"] == sketch.MOUTH_STYLE  # the shipped reading unless an episode opts in
    *_, quick = mods
    build.record_episode(sk, tmp_path, {"SRSTUDIO_ALLOW_CLOUD": "1"}, "ffmpeg", 7, "note", mouth=quick.MOUTH)
    assert seen["mouth"].close_bilabials and seen["mouth"].rate == sketch.VISEME_RATE
    assert seen["mouth"].round_letters == sketch.MOUTH_STYLE.round_letters
    assert json.loads((tmp_path / "narration.json").read_text()) == manifest
    assert manifest_duration(tmp_path / "narration.json") == sk.end
    effects = {fx.id: fx for fx in effect_cues(tmp_path / "narration.json", tmp_path)}
    assert set(effects) == {"typing", "buzz", "sting"}
    typing = effects["typing"]
    typing_spans = [
        (b.start, n.start if n else sk.end)
        for b, n in zip(sk.beats, list(sk.beats[1:]) + [None], strict=True)
        if b.arms in sketch.TYPING_ARMS
    ]
    assert typing.taps and all(any(a < at < z for a, z in typing_spans) for at in typing.taps)  # paws on the keys
    assert all(not any(a - 0.2 < at < b + 0.2 for a, b in spans) for at in typing.taps)  # never under a line
    assert (tmp_path / "audio" / "buzz.wav").stat().st_mode & 0o077 == 0
    assert manifest["voice_note"] == "note" and manifest["model"] and manifest["items"] == []


def test_the_build_refuses_a_voiced_project_whose_files_disagree(mods, tmp_path, monkeypatch):
    build, data, *_ = mods
    staging = build.Staging(data.SKETCH, 1, "d", "a", "n", data.TINTS, data.dress)
    installed = []
    monkeypatch.setattr(sketch.fonts, "install", lambda font, folder: installed.append(Path(folder)))
    with pytest.raises(SystemExit):
        build.build(tmp_path, staging, {"--init"})
    assert installed == [tmp_path / "assets" / "fonts"] and (tmp_path / "script.json").is_file()
    # a voiced build needs the placed beats, then a manifest of the same length
    with pytest.raises(sketch.SketchError, match="beats.json"):
        build.build(tmp_path, staging, {"--voice"})
    beats = list(data.SKETCH.beats)
    # ... and the viseme tracks recorded with them, of the same length
    sketch.write_voiced(tmp_path, beats, data.END + 1.0, data.SKETCH.lines)
    with pytest.raises(sketch.SketchError, match="mouths.json"):
        build.build(tmp_path, staging, {"--voice"})
    sketch.write_voiced(tmp_path, beats, data.END, data.SKETCH.lines, {"dog": []})
    sketch.write_voiced(tmp_path / "x", beats, data.END + 1.0, data.SKETCH.lines)
    (tmp_path / "voiced" / "beats.json").write_bytes((tmp_path / "x" / "voiced" / "beats.json").read_bytes())
    with pytest.raises(build.StagingError, match=r"mouths.json runs 33.5 s, voiced/beats.json 34.5 s"):
        build.build(tmp_path, staging, {"--voice"})
    sketch.write_voiced(tmp_path, beats, data.END + 1.0, data.SKETCH.lines, {"dog": [(1.0, "open"), (1.5, "closed")]})
    (tmp_path / "assets" / "fonts").mkdir(parents=True)
    (tmp_path / TOON.font.src).write_bytes(b"")
    (tmp_path / "narration.json").write_text(json.dumps({"duration": data.END, "items": [], "effects": []}))
    with pytest.raises(build.StagingError, match="narration.json runs"):
        build.build(tmp_path, staging, {"--voice"})


def test_captions_wider_than_the_frame_are_refused_and_a_long_line_may_be_split(mods):
    build, data, *_ = mods
    lines = toon.parse_script(sketch.cues(data.SKETCH.beats, data.END, data.SKETCH.lines))
    build.fit_captions(lines, lambda text: 30.0 * len(text), 1080)  # the widest caption, 28 characters, fits
    with pytest.raises(build.StagingError, match="too wide.*eleven messages"):
        build.fit_captions(lines, lambda text: 34.0 * len(text), 1080)
    # the long line is captioned in two pills, the second starting on its third word
    two = [b for b in data.SKETCH.beats if b.line == 2]
    assert [(b.word, b.caption) for b in two] == [(0, "The report."), (2, "You asked me to remind you.")]
    with pytest.raises(sketch.SketchError, match="not line 2 from word"):
        data.part(5.0, "frog", 2, 1, "You asked me", "wide", "flat", "desk")


def test_quick_question_refuses_events_its_props_cannot_do_and_lets_the_coffee_go_cold(mods):
    *_, data = mods
    sk = data.SKETCH
    beats = list(sk.beats)
    i = next(k for k, b in enumerate(beats) if b.event.startswith("clock"))
    for event, match in (("clock:08:00", "backwards"), ("clock:9", "clock"), ("wave", "unknown events")):
        bad = beats[:i] + [replace(beats[i], event=event)] + beats[i + 1 :]
        with pytest.raises((sketch.SketchError, ValueError), match=match):
            data.validate(replace(sk, beats=tuple(bad)))
    on_pip = next(k for k, b in enumerate(beats) if b.who == "rabbit" and k > 0)
    bad = list(beats)
    bad[on_pip] = replace(beats[on_pip], event="clock:09:10")
    with pytest.raises(sketch.SketchError, match="Bruno's shot"):
        data.validate(replace(sk, beats=tuple(bad)))
    no_hangup = [replace(b, event="") if b.event == "hangup" else b for b in beats]
    with pytest.raises(sketch.SketchError, match="exactly once"):
        data.validate(replace(sk, beats=tuple(no_hangup)))
    # the mug steams until the clock first jumps, then never again
    cold = data.cold_at(sk.beats)
    assert cold == beats[i].start
    apps = [a for a in sketch.appearances(sk.beats, sk.end) if a.who == "bear"]
    spans = [data.steam_spans(sk.beats, a) for a in apps]
    assert spans[0] == [(apps[0].start, apps[0].end)] and all(
        s == [] for a, s in zip(apps, spans, strict=True) if a.start >= cold
    )
    assert data.cold_at(no_hangup[:1]) is None and data.steam_spans(no_hangup[:1], apps[0]) == [
        (apps[0].start, apps[0].end)
    ]
    # the answer is on the board from the first frame and the clock ends after it
    assert "9:45" in data.BOARD and sketch.events(sk.beats, "clock")[-2][1] == "09:48"


def test_a_staging_stands_the_office_desk_in_front_unless_it_lays_another(mods):
    build, data, *_ = mods
    assert build.Staging(data.SKETCH, 1, "d", "a", "n", data.TINTS, data.dress).desk is toon.desk
    laid = build.Staging(data.SKETCH, 1, "d", "a", "n", data.TINTS, data.dress, desk=toon_dinner.table)
    assert laid.desk is toon_dinner.table
