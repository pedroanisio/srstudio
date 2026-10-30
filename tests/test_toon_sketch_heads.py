"""A sketch moves its characters' heads through the normal build (ADR 0050): one line in the staging, each named
character planned from its own lines and what it hears, drawn through the head rig in every shot, and everyone else
drawn flat, with the camera, the lips and the recording left as they were."""

import json
import math
import os
import shutil
import xml.etree.ElementTree as ET
from pathlib import Path
from types import SimpleNamespace

import pytest

from srstudio import (
    TOON,
    camera,
    characters,
    craft,
    music,
    registry,
    sketch,
    toon,
    toon_head,
    toon_inked,
    toon_rigs,
    toon_sketch,
)
from srstudio.sketch import Beat, Line, Sketch, Speaker
from srstudio.voice import MODEL, Alignment, Transcript, Voice, VoiceSettings

SPEAKERS = (
    Speaker("bo", Voice(role="bo", id="a1", name="Roger"), VoiceSettings(0.5, 0.75, 0.3), "sloth"),
    Speaker("mo", Voice(role="mo", id="b2", name="River"), VoiceSettings(0.5, 0.75, 0.3), "goat"),
)
LINES = (Line("bo", "The quarterly report is finished."), Line("mo", "Nobody asked for that report."),
         Line("bo", "It has a really lovely chart."))  # fmt: skip
BEATS = (
    Beat(0.0, "sloth", "The quarterly report is finished.", "half", "flat", "desk", 0, 0),
    Beat(2.2, "goat", "Nobody asked for that report.", "narrow", "flat", "crossed", 1, 0),
    Beat(4.4, "sloth", "It has a really lovely chart.", "half", "grin", "type", 2, 0),
    Beat(6.0, "goat", "", "half", "flat", "lean"),
)
SK = Sketch("heads-test", "Heads test", SPEAKERS, LINES, BEATS, 8.0)
BOTH = ("sloth", "goat")


class Client:
    """Says each line as a tone, 0.3 s a word, and hears back what it said."""

    def __init__(self, folder: Path):
        self.folder, self.said = folder, {}

    def synthesize(self, text, voice, settings):
        seconds, rate = 0.3 * len(text.split()), 8000
        samples = [0.5 * math.sin(2 * math.pi * 220 * k / rate) for k in range(int(seconds * rate))]
        wav = self.folder / f"take-{len(self.said)}.wav"
        music.write_wav(wav, samples, rate)
        self.said[wav] = text
        starts = tuple(round(k * seconds / len(text), 6) for k in range(len(text)))
        ends = tuple(round(s + seconds / len(text), 6) for s in starts)
        return SimpleNamespace(wav=wav, alignment=Alignment(tuple(text), starts, ends))

    def transcribe(self, audio, language="en"):
        return Transcript("en", 1.0, self.said[Path(audio)], ())


def staged(sk: Sketch = SK, versions=None, **kw) -> toon_sketch.Staging:
    tints = {"bo": "#ffe3b3", "mo": "#d6f5dc"}
    return toon_sketch.Staging(sk, 3, "d", "a", "n", tints, lambda shot: None, versions or {}, **kw)


def recorded(root: Path, sk: Sketch = SK) -> None:
    def clip(src, dst, clip_in, clip_out, length, gain_db, ffmpeg):
        shutil.copy(src, dst)
        return length

    def confirm(cache, key, voice):
        return {"voice_id": voice.id, "name": f"{voice.name} - premade", "category": "premade"}

    root.mkdir(parents=True, exist_ok=True)
    rec = sketch.record(sk, root, Client(root), confirm=confirm, conform_clip=clip)
    effects = toon_sketch.sound_effects(rec.beats, rec.end, rec.speech, root, 3)
    (root / "narration.json").write_text(json.dumps(sketch.manifest(sk, rec, effects, MODEL, "note"), indent=2))


@pytest.fixture(scope="module")
def pinned_fonts() -> Path:
    env = os.environ.get("SRSTUDIO_EPISODES")
    if not env:
        pytest.skip("set SRSTUDIO_EPISODES to the folder of generated episode projects")
    folder = Path(env) / "the-report" / "assets" / "fonts"
    if TOON.font is None or not (folder / Path(TOON.font.src).name).is_file():
        pytest.skip(f"no pinned Toon font in {folder}")
    return folder


def project(root: Path, fonts: Path, voiced: bool = False) -> Path:
    root.mkdir(parents=True, exist_ok=True)
    shutil.copytree(fonts, root / "assets" / "fonts")
    assert toon_sketch.build(root, staged(), {"--init"}) is None
    if voiced:
        recorded(root)
    return root


def tree(ep) -> ET.Element:
    return ET.fromstring(ep.scene.to_bytes(layout="pretty"))


def shots(xml: ET.Element) -> list[ET.Element]:
    return [g for g in xml.find("composition").findall("group") if g.get("start") is not None][: len(BEATS)]


def idle_of(shot: ET.Element) -> ET.Element | None:
    """The rig's wandering group, if the shot has one: only a moving head rotates on a catmull-rom curve."""
    for node in shot.iter("group"):
        for a in node.findall("animate"):
            if a.get("property") == "rotation" and a.get("defaultInterpolation") == "catmull-rom":
                return node
    return None


def rigged(shot: ET.Element) -> bool:
    return idle_of(shot) is not None


def keys(node: ET.Element, prop: str) -> list[tuple[float, float]]:
    a = next(a for a in node.findall("animate") if a.get("property") == prop)
    return [(float(k.get("time")), float(k.get("value"))) for k in a.findall("key")]


# -- asking for it -----------------------------------------------------------------------------------------------------
def test_a_character_with_no_rig_is_refused_by_name_before_anything_is_written(tmp_path):
    sk = Sketch("heads-test", "Heads test", SPEAKERS, LINES, (Beat(0.0, "cat", "", "half", "flat", "desk"),), 2.0)
    with pytest.raises(toon.ToonDataError, match="toon-cat version 1 has no head rig"):
        toon_sketch.build(tmp_path, staged(sk, heads=("cat",)), {"--init"})
    assert list(tmp_path.iterdir()) == []


def test_a_character_this_sketch_never_shows_is_refused_by_name(tmp_path):
    with pytest.raises(toon_sketch.StagingError, match="'hamster', who is not in this sketch"):
        toon_sketch.build(tmp_path, staged(heads=("hamster",)), {"--init"})


def test_no_heads_asks_for_nothing(tmp_path):
    assert toon_sketch.head_plans(tmp_path, SK, (), True, {}) == {}


def test_a_voiced_build_with_no_takes_on_file_says_to_record_again(tmp_path):
    with pytest.raises(toon_sketch.StagingError, match="record again"):
        toon_sketch.head_plans(tmp_path, SK, BOTH, True, {})


def test_takes_from_another_length_of_sketch_are_refused(tmp_path):
    recorded(tmp_path)
    path = tmp_path / "voiced" / "speech.json"
    data = json.loads(path.read_text())
    data["end"] += 1.0
    path.write_text(json.dumps(data))
    end = sketch.load_beats(tmp_path / "voiced" / "beats.json")[1]
    with pytest.raises(toon_sketch.StagingError, match="record again"):
        toon_sketch.head_plans(tmp_path, Sketch("h", "H", SPEAKERS, LINES, BEATS, end), BOTH, True, {})


# -- each its own plan -------------------------------------------------------------------------------------------------
def test_each_character_is_planned_from_its_own_lines_and_hears_the_others(tmp_path):
    recorded(tmp_path)
    beats, end = sketch.load_beats(tmp_path / "voiced" / "beats.json")
    takes, _ = sketch.load_speech(tmp_path / "voiced" / "speech.json")
    sk = Sketch("h", "H", SPEAKERS, LINES, tuple(beats), end)
    plans = toon_sketch.head_plans(tmp_path, sk, BOTH, True, {})
    sloth, goat = plans["sloth"][1], plans["goat"][1]
    assert plans["sloth"][0] is toon_rigs.rig_of("toon-sloth") and plans["goat"][0] is toon_rigs.rig_of("toon-goat")
    second = takes[1]
    during = [v for t, v in goat.nod.keys if second.at <= t <= second.at + second.kept]
    listening = [v for t, v in sloth.nod.keys if second.at <= t <= second.at + second.kept + 1.0]
    assert max(map(abs, during)) > max(map(abs, listening)) > 0.0  # the speaker nods, the listener barely
    assert not any(second.at <= t <= second.at + second.kept for t, _ in sloth.gaze)


def test_a_silent_build_plans_an_idle_head_for_each(tmp_path):
    plans = toon_sketch.head_plans(tmp_path, SK, BOTH, False, {})
    assert plans["sloth"][1].nod.keys == ((0.0, 0.0),) and plans["sloth"][1] != plans["goat"][1]
    assert len(plans["goat"][1].idle_roll.keys) > 2


def fox_sketch() -> Sketch:
    speaker = Speaker("bo", Voice(role="bo", id="a1", name="Roger"), VoiceSettings(0.5, 0.75, 0.3), "fox")
    beat = Beat(0.0, "fox", "The report is finished.", "half", "flat", "desk", 0, 0)
    return Sketch("heads-test", "Heads test", (speaker,), (Line("bo", "The report is finished."),), (beat,), 2.0)


def test_a_writer_names_the_fox_and_gets_the_rig_of_the_version_it_draws(tmp_path):
    plans = toon_sketch.head_plans(tmp_path, fox_sketch(), ("fox",), False, {})
    assert plans["fox"][0] is toon_rigs.RIGS["toon-fox@2"] is toon_inked.FOX_RIG
    plans = toon_sketch.head_plans(tmp_path, fox_sketch(), ("fox",), False, {"toon-fox": 2})
    assert plans["fox"][0] is toon_inked.FOX_RIG


def test_a_pin_to_a_version_with_no_rig_is_refused_by_name_before_anything_is_written(tmp_path):
    staging = staged(fox_sketch(), {"toon-fox": 1}, heads=("fox",))
    with pytest.raises(toon.ToonDataError, match=r"toon-fox version 1 has no head rig.*toon-fox@2"):
        toon_sketch.build(tmp_path, staging, {"--init"})
    assert list(tmp_path.iterdir()) == []


def test_the_same_pin_draws_flat_when_the_writer_does_not_ask_for_heads(tmp_path):
    assert toon_sketch.check_heads(fox_sketch(), (), {"toon-fox": 1}) is None


def test_a_pin_to_a_version_that_does_not_exist_is_refused(tmp_path):
    with pytest.raises(characters.CharacterError, match="toon-fox"):
        toon_sketch.head_plans(tmp_path, fox_sketch(), ("fox",), False, {"toon-fox": 9})


def test_every_rig_is_keyed_by_a_registered_drawing():
    for part in toon_rigs.RIGS:
        assert registry.get("character", part).name == part


# -- through the build -------------------------------------------------------------------------------------------------
def test_only_the_characters_named_move_and_the_rest_draw_flat(pinned_fonts, tmp_path):
    root = project(tmp_path / "p", pinned_fonts)
    xml = tree(toon_sketch.build(root, staged(heads=("sloth",)), set()))
    assert [rigged(shot) for shot in shots(xml)] == [True, False, True, False]
    xml = tree(toon_sketch.build(root, staged(heads=BOTH), set()))
    assert [rigged(shot) for shot in shots(xml)] == [True, True, True, True]
    xml = tree(toon_sketch.build(root, staged(), set()))
    assert not any(rigged(shot) for shot in shots(xml))


def test_the_record_of_what_was_drawn_names_a_moving_character_as_well(pinned_fonts, tmp_path):
    root = project(tmp_path / "p", pinned_fonts)
    toon_sketch.build(root, staged(heads=("sloth",)), set())
    assert characters.read_record(root) == {"toon-goat": 1, "toon-sloth": 1}


def test_the_fox_moves_through_the_build_at_the_version_it_is_named_by(pinned_fonts, tmp_path):
    root = tmp_path / "p"
    root.mkdir()
    shutil.copytree(pinned_fonts, root / "assets" / "fonts")
    toon_sketch.build(root, staged(fox_sketch()), {"--init"})
    xml = tree(toon_sketch.build(root, staged(fox_sketch(), heads=("fox",)), set()))
    assert rigged(shots(xml)[0])  # its one shot; the groups after it are the caption's
    assert characters.read_record(root) == {"toon-fox": 2}


def test_a_voiced_build_keeps_lips_shots_and_camera_on_a_moving_head(pinned_fonts, tmp_path):
    root = project(tmp_path / "p", pinned_fonts, voiced=True)
    seen = []

    def push(shot, node):
        seen.append(shot.app.who)
        camera.push_in(shot.cv, node, scale=[(shot.app.start, 1.0), (shot.app.start + 1.0, 1.05)])

    still = toon_sketch.build(root, staged(camera=push), {"--voice"})
    moving = toon_sketch.build(root, staged(camera=push, heads=BOTH), {"--voice"})
    assert craft.moves(moving.scene.to_bytes(layout="pretty")) == craft.moves(still.scene.to_bytes(layout="pretty"))
    assert seen == ["sloth", "goat", "sloth", "goat"] * 2
    xml = tree(moving)
    for shot in shots(xml):
        assert (shot.get("id") or "").startswith("shot-") and rigged(shot)
    for shot in shots(xml)[:2]:
        held = [g for g in shot.iter("group") if g.find("animate[@property='opacity']") is not None]
        assert len(held) >= 3  # the visemes and the blinks


def test_a_character_s_timeline_runs_on_through_the_cuts(pinned_fonts, tmp_path):
    root = project(tmp_path / "p", pinned_fonts, voiced=True)
    staging = staged(heads=BOTH)
    xml = tree(toon_sketch.build(root, staging, {"--voice"}))
    beats, end = sketch.load_beats(root / "voiced" / "beats.json")
    sk = Sketch("h", "H", SPEAKERS, LINES, tuple(beats), end)
    plan = toon_sketch.head_plans(root, sk, BOTH, True, {})["sloth"][1]
    apps = [a for a in sketch.appearances(sk.beats, sk.end) if a.who == "sloth"]
    assert len(apps) == 2
    sloth = [s for s in shots(xml) if rigged(s)][0], [s for s in shots(xml) if rigged(s)][2]
    for shot, app in zip(sloth, apps, strict=True):
        kept = keys(idle_of(shot), "rotation")
        whole = [(round(t, 6), round(v, 4)) for t, v in plan.idle_roll.keys]
        assert set(kept) <= set(whole) and len(kept) < len(whole)
        assert kept[0][0] <= app.start and kept[-1][0] >= min(app.end, whole[-1][0])


def test_the_rig_is_the_module_the_build_draws_with():
    assert toon_sketch.toon_head is toon_head
