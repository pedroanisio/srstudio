"""Rules 7 and 8: a caption does not run across a sentence end, and a text is timed on the frame (ADR 0149, 0150)."""

from __future__ import annotations

import json
import os
import shutil
from pathlib import Path

import pytest

from srstudio import anatomy_ledger, cli, framegraph, native, text_rules
from srstudio.anatomy_ledger import Exemption, ExemptionError
from srstudio.episode import Episode, EpisodeSpec
from srstudio.frame_gates import FrameGateError, RunTogether, broken_off
from srstudio.framegraph import Drawing, Frame, FrameGraphError, Node
from srstudio.releases import Release
from srstudio.sample import SYSTEM_FONTS, Line, write_sample_project
from srstudio.social import InstagramPost
from srstudio.text_rules import CAPTION_RUN, MINIMUM, TEXT_SHORT, Run, TextRefusedError

LINES = ["Take it.", "Whatever you say."]
POST = InstagramPost(title="t", description="d")
ENGINE = os.environ.get("SRSTUDIO_ENGINE") or shutil.which("scene-render")


def scene(*windows: str) -> bytes:
    texts = "".join(f'<text id="t{i}" text="{w}"/><layer asset="t{i}"/>' for i, w in enumerate(windows))
    return f"<scene><composition>{texts}</composition></scene>".encode()


def project(tmp_path: Path, lines: list[str] = LINES) -> Path:
    (tmp_path / "voice-transcript.json").write_text(
        json.dumps({"lines": [{"expected": line} for line in lines]}), encoding="utf-8"
    )
    return tmp_path


def test_a_window_that_drops_the_stop_is_a_fault(tmp_path):
    [note] = text_rules.caption_notes(scene("Take it Whatever"), project(tmp_path))
    assert note.rule == CAPTION_RUN and note.part == "Take it Whatever"


def test_a_window_that_keeps_the_stop_and_breaks_off_is_a_fault(tmp_path):
    [note] = text_rules.caption_notes(scene("Take it. Whatever"), project(tmp_path))
    assert note.part == "Take it. Whatever"


def test_a_window_with_both_faults_is_noted_once(tmp_path):
    notes = text_rules.caption_notes(scene("Take it Whatever"), project(tmp_path))
    assert len(notes) == 1


def test_a_window_of_whole_sentences_is_not(tmp_path):
    assert text_rules.caption_notes(scene("Take it. Whatever you say."), project(tmp_path)) == []


def test_each_sentence_in_its_own_window_is_not(tmp_path):
    assert text_rules.caption_notes(scene("Take it.", "Whatever you say."), project(tmp_path)) == []


def test_a_silent_reel_has_nothing_to_compare(tmp_path):
    assert text_rules.caption_notes(scene("Take it Whatever"), tmp_path) == []


def test_a_transcript_that_is_not_one_stops_the_rule_with_its_error(tmp_path):
    (tmp_path / "voice-transcript.json").write_text("{}", encoding="utf-8")
    with pytest.raises(FrameGateError):
        text_rules.caption_notes(scene("Take it Whatever"), tmp_path)


def test_broken_off_names_the_last_sentence_end_it_crossed():
    lines = ["Meetings have been reduced to one.", "It is this one, and it does not end."]
    window = "Meetings have been reduced to one. It is"
    assert broken_off(scene(window), lines) == [RunTogether(window, "one.", "It")]


def test_a_stop_that_is_kept_and_a_last_word_that_trails_off_is_a_whole_window():
    assert broken_off(scene("Take it. Whatever..."), LINES) == []


@pytest.mark.parametrize(
    "window",
    [
        "Take it. Whatever",
        "Take it. Whatever you say.",
        "Take it.",
        "it. Whatever you",
        "Take it. Whatever you,",
        "Whatever you say.",
    ],
)
def test_the_cue_chooser_reads_rule_7_as_the_gate_does(window):
    words = [native.Word(w, float(i), float(i) + 0.5) for i, w in enumerate(window.split())]
    assert native._broken_off(words) is bool(broken_off(scene(window), LINES))


def test_a_window_stripped_of_its_last_stop_is_still_whole():
    assert broken_off(scene("Take it. Whatever you say"), LINES) == []


def test_a_window_with_no_sentence_end_in_it_is_not_broken_off():
    assert broken_off(scene("Whatever you"), LINES) == []


def test_a_new_reel_is_refused(tmp_path):
    with pytest.raises(TextRefusedError, match="caption-run on Take it Whatever"):
        text_rules.refuse_captions("a-new-reel", scene("Take it Whatever"), project(tmp_path))


def test_a_listed_window_of_its_reel_builds_and_no_other(tmp_path, monkeypatch):
    row = Exemption("old-reel", CAPTION_RUN, "Take it Whatever", "published with it")
    monkeypatch.setattr(text_rules, "exemptions", lambda: (row,))
    text_rules.refuse_captions("old-reel", scene("Take it Whatever"), project(tmp_path))
    with pytest.raises(TextRefusedError):
        text_rules.refuse_captions("other-reel", scene("Take it Whatever"), project(tmp_path))
    with pytest.raises(TextRefusedError):
        text_rules.refuse_captions("old-reel", scene("Take it Whatever", "Take it. Whatever"), project(tmp_path))


@pytest.fixture
def project_dir(tmp_path: Path) -> Path:
    root = tmp_path / "project"
    root.mkdir()
    write_sample_project(root, [Line("v", "Take it.", 1000)], angles=["wide"])
    return root


def _episode(root: Path, slug: str) -> Episode:
    episode = Episode(
        EpisodeSpec(slug=slug, title="t", description="t", root=root, seed=1, background="#D5DFDF", signature=False)
    )
    episode.cv.assets.add_text(id="said", text="Take it Whatever", width=200, height=80, size="40")
    episode.comp.add_layer(id="said-layer", asset="said", x=0, y=0)
    return episode


def test_the_build_refuses_before_it_writes_a_scene(project_dir, tmp_path):
    project(project_dir)
    out = tmp_path / "a-new-reel.scene.xml"
    with pytest.raises(TextRefusedError, match="a-new-reel"):
        _episode(project_dir, "a-new-reel").finish(out=out)
    assert not out.exists()


def test_a_published_reel_on_the_list_still_rebuilds(project_dir, tmp_path, monkeypatch):
    project(project_dir)
    row = Exemption("old-reel", CAPTION_RUN, "Take it Whatever", "published with it")
    monkeypatch.setattr(text_rules, "exemptions", lambda: (row,))
    assert _episode(project_dir, "old-reel").finish(out=tmp_path / "old-reel.scene.xml").is_file()


def test_a_first_delivery_answers_for_a_window_that_breaks_off(tmp_path):
    root = tmp_path / "a-b"
    root.mkdir()
    project(root)
    (root / "a-b.scene.xml").write_bytes(scene("Take it. Whatever"))
    release = Release("a-b", POST, video="The_Video")
    [drift] = text_rules.caption_defects({"a-b": release}, tmp_path, {"a-b": "The_Video"})
    assert drift.name == "The_Video" and "breaks off" in drift.reason


def test_a_first_delivery_lists_no_row_of_the_closed_list(tmp_path, monkeypatch):
    root = tmp_path / "a-b"
    root.mkdir()
    project(root)
    (root / "a-b.scene.xml").write_bytes(scene("Take it. Whatever"))
    row = Exemption("a-b", CAPTION_RUN, "Take it. Whatever", "published with it")
    monkeypatch.setattr(text_rules, "exemptions", lambda: (row,))
    assert text_rules.caption_defects({"a-b": Release("a-b", POST)}, tmp_path, {"a-b": "a-b"})


def test_a_project_with_no_scene_has_nothing_to_read(tmp_path):
    assert text_rules.caption_defects({"a-b": Release("a-b", POST)}, tmp_path, {"a-b": "a-b"}) == []


def test_the_delivery_gate_runs_the_rule():
    source = (Path(__file__).resolve().parent.parent / "episodes" / "instagram_posts.py").read_text(encoding="utf-8")
    assert "text_rules.caption_defects(chosen, _beside(renders), first)" in source
    assert "frame_gates.captions_run_together(chosen, _beside(renders), first)" in source


def test_the_list_is_closed_to_other_rules():
    text = json.dumps(
        {"schema": "1.0.0", "exemptions": [{"reel": "a", "rule": "hand-no-arm", "part": "p", "why": "w"}]}
    )
    with pytest.raises(ExemptionError):
        text_rules.parse(text)


def test_every_row_of_the_list_is_read():
    assert all(row.why.strip() for row in text_rules.exemptions())


def test_a_reel_pulled_from_the_queue_is_not_published_and_not_on_the_list():
    pulled = {"take-my-phone", "what-my-dad-does", "gloss-fewer-meetings"}
    assert not pulled & {row.reel for row in text_rules.exemptions()}


def test_the_anatomy_list_is_still_closed_to_these_rules():
    text = json.dumps({"schema": "1.0.0", "exemptions": [{"reel": "a", "rule": CAPTION_RUN, "part": "p", "why": "w"}]})
    with pytest.raises(ExemptionError):
        anatomy_ledger.parse_exemptions(text)


# -- rule 8: a text is timed on the frame -----------------------------------------------------------------------------
PLACE = (1.0, 0.0, 0.0, 1.0, 100.0, 100.0)
BOX = Drawing((((0.0, 0.0), (300.0, 0.0), (300.0, 60.0), (0.0, 60.0)),), False)
DRAWN = {"a": BOX, "b": BOX, "card": Drawing((((0.0, 0.0), (1080.0, 0.0), (1080.0, 1920.0), (0.0, 1920.0)),), True)}
SHOWN = [i / 24 for i in range(5, 12)]  # 0.292 s of seven frames


def node(text: str = "HELLO", *, name: str = "a", opacity: float = 1.0, world=PLACE) -> Node:
    return Node(name, None, "layer", world, opacity, True, text)


def frame(time: float, *nodes: Node) -> Frame:
    return Frame(time, 1080.0, 1920.0, nodes)


def shown(first: float, last: float, *, name: str = "a", text: str = "HELLO") -> list[Frame]:
    return [frame(first + i / 24, node(text, name=name)) for i in range(round((last - first) * 24) + 1)]


def test_a_text_is_timed_from_its_first_to_its_last_frame():
    [run] = text_rules.runs(shown(1.0, 2.0), DRAWN, 24.0)
    assert run == Run("HELLO", 1.0, pytest.approx(2.0))
    assert run.seconds(24.0) == pytest.approx(1.0 + 1 / 24)


def test_a_text_carried_across_a_cut_into_another_layer_is_one_run():
    """The engine's false finding: it times each layer, and the frames show one card."""
    frames = shown(1.0, 1.25, name="a") + shown(1.0 + 7 / 24, 3.0, name="b")
    [run] = text_rules.runs(frames, DRAWN, 24.0)
    assert (run.first, run.last) == (1.0, pytest.approx(3.0))


def test_a_flip_of_a_frame_or_two_does_not_end_a_run():
    frames = shown(1.0, 2.0) + [frame(2.0 + 1 / 24)] + shown(2.0 + 2 / 24, 3.0)
    assert len(text_rules.runs(frames, DRAWN, 24.0)) == 1


def test_the_same_words_after_a_gap_are_a_second_run():
    gap = [frame(2.0 + i / 24) for i in range(1, 12)]
    assert len(text_rules.runs(shown(1.0, 2.0) + gap + shown(2.5, 3.5), DRAWN, 24.0)) == 2


def test_case_and_spacing_do_not_make_another_text():
    frames = shown(1.0, 1.5, text="Hello  there") + shown(1.0 + 13 / 24, 2.0, text="HELLO THERE", name="b")
    assert [run.text for run in text_rules.runs(frames, DRAWN, 24.0)] == ["Hello there"]


def test_a_faded_text_is_not_on_the_frame():
    assert text_rules.runs([frame(1.0, node(opacity=0.2))], DRAWN, 24.0) == []


def test_a_text_off_the_frame_is_not_on_it():
    away = node(world=(1.0, 0.0, 0.0, 1.0, 5000.0, 100.0))
    assert text_rules.runs([frame(1.0, away)], DRAWN, 24.0) == []


def test_a_text_flat_in_a_flip_is_not_on_the_frame():
    flat = node(world=(0.0, 0.0, 0.0, 1.0, 100.0, 100.0))
    assert text_rules.runs([frame(1.0, flat)], DRAWN, 24.0) == []


def test_a_text_behind_something_solid_is_not_on_it():
    cover = Node("card", None, "shape", (1.0, 0.0, 0.0, 1.0, 0.0, 0.0), 1.0, True)
    assert text_rules.runs([frame(1.0, node(), cover)], DRAWN, 24.0) == []


def test_a_run_under_the_minimum_is_a_fault():
    [note] = text_rules.short_notes([Run("HELLO", 1.0, 1.5)], 24.0)
    assert note.rule == TEXT_SHORT and note.part == "HELLO" and "0.542" in note.detail


def test_a_run_at_the_minimum_is_not():
    assert text_rules.short_notes([Run("HELLO", 1.0, 1.0 + MINIMUM - 1 / 24)], 24.0) == []


def test_a_text_that_had_its_time_may_come_back_for_a_beat():
    assert text_rules.short_notes([Run("HELLO", 1.0, 3.0), Run("HELLO", 5.0, 5.2)], 24.0) == []


def test_the_frames_around_a_short_run_are_read_to_the_frame():
    times = text_rules.around([Run("HELLO", 1.0, 1.25)], 24.0, 0.25)
    assert 23 / 24 in times and 31 / 24 in times
    assert all(t == round(t * 24) / 24 for t in times)  # the engine's frame times, not rounded seconds
    assert min(times) >= 1.0 - 0.3 and max(times) <= 1.25 + 0.3


def test_a_long_run_is_not_read_again():
    assert text_rules.around([Run("HELLO", 1.0, 3.0)], 24.0, 0.25) == []


def test_the_engine_reports_a_text_on_its_nodes():
    printed = {
        "result": {
            "size": [1080, 1920],
            "time": 1.0,
            "nodes": [
                {"id": "a", "kind": "layer", "world": PLACE, "world_opacity": 1.0, "draw": True, "text": "HI"},
                {"id": "b", "kind": "shape", "world": PLACE, "world_opacity": 1.0, "draw": True},
            ],
        }
    }
    assert [n.text for n in framegraph.read_frame(json.dumps(printed)).nodes] == ["HI", ""]


def _scene(root: Path, body: str = "") -> Path:
    out = root / "a-b.scene.xml"
    out.write_text(
        f'<scene><project fps="24" duration="1"/><composition>{body}</composition></scene>', encoding="utf-8"
    )
    return out


def _engine(monkeypatch: pytest.MonkeyPatch, times: list[float], *, tracks: list[dict] | None = None) -> list[float]:
    """The engine's two answers, read from a seam at the subprocess: what a frame shows, and the caption pages."""
    asked: list[float] = []

    def evaluate(_engine, _scene, wanted):
        asked.extend(wanted)
        return [frame(t, *([node()] if any(abs(t - s) < 1e-3 for s in times) else [])) for t in wanted]

    monkeypatch.setattr(text_rules.framegraph, "evaluate", evaluate)
    monkeypatch.setattr(text_rules.framegraph, "drawings", lambda _: DRAWN)

    class Done:
        returncode, stderr = 0, ""
        stdout = json.dumps({"tracks": tracks or []})

    monkeypatch.setattr(text_rules.subprocess, "run", lambda *a, **kw: Done)
    return asked


def test_a_scene_is_read_on_its_frames_to_the_frame(tmp_path, monkeypatch):
    _engine(monkeypatch, SHOWN)
    [note] = text_rules.timing_notes(_scene(tmp_path), "engine")
    assert note.rule == TEXT_SHORT and "0.292" in note.detail


def test_the_frames_read_are_the_reel_s_own(tmp_path, monkeypatch):
    asked = _engine(monkeypatch, SHOWN)
    text_rules.timing_notes(_scene(tmp_path, '<group start="0.31" end="0.5"/>'), "engine")
    assert all(abs(t * 24 - round(t * 24)) < 1e-3 for t in asked)


def test_a_flash_between_two_frames_of_the_pass_is_found_at_its_start(tmp_path, monkeypatch):
    _engine(monkeypatch, [(9 + i) / 24 for i in range(1, 3)])
    scene = _scene(tmp_path, '<group start="0.375" end="0.5"/>')
    [note] = text_rules.timing_notes(scene, "engine")
    assert "0.083" in note.detail


def test_a_burned_page_is_timed_as_the_engine_pages_it(tmp_path, monkeypatch):
    tracks = [{"burn": True, "pages": [{"text": "Too\nquick", "start": 0.1, "end": 0.4}]}]
    _engine(monkeypatch, [], tracks=tracks)
    [note] = text_rules.timing_notes(_scene(tmp_path), "engine")
    assert note.part == "Too quick" and "0.300" in note.detail


def test_a_track_that_is_not_burned_is_not_on_the_frame(tmp_path, monkeypatch):
    tracks = [{"burn": False, "pages": [{"text": "Too quick", "start": 0.1, "end": 0.4}]}]
    _engine(monkeypatch, [], tracks=tracks)
    assert text_rules.timing_notes(_scene(tmp_path), "engine") == []


def test_captions_the_engine_cannot_page_stop_the_rule(tmp_path, monkeypatch):
    class Failed:
        returncode, stdout, stderr = 1, "", "no track"

    monkeypatch.setattr(text_rules.subprocess, "run", lambda *a, **kw: Failed)
    with pytest.raises(FrameGraphError, match="no track"):
        list(text_rules.pages("engine", _scene(tmp_path)))


def test_a_reply_that_is_not_pages_stops_the_rule(tmp_path, monkeypatch):
    class Odd:
        returncode, stdout, stderr = 0, '{"tracks": [{"pages": []}]}', ""

    monkeypatch.setattr(text_rules.subprocess, "run", lambda *a, **kw: Odd)
    with pytest.raises(FrameGraphError, match="captions"):
        list(text_rules.pages("engine", _scene(tmp_path)))


def test_a_first_delivery_answers_for_a_short_text(tmp_path, monkeypatch):
    root = tmp_path / "a-b"
    root.mkdir()
    _scene(root)
    _engine(monkeypatch, SHOWN)
    release = Release("a-b", POST, video="The_Video")
    [drift] = text_rules.timing_defects({"a-b": release}, tmp_path, {"a-b": "The_Video"}, "engine")
    assert drift.name == "The_Video" and TEXT_SHORT in drift.reason


def test_a_reel_with_no_scene_has_no_text_to_time(tmp_path):
    assert text_rules.timing_defects({"a-b": Release("a-b", POST)}, tmp_path, {"a-b": "a-b"}, "engine") == []


def test_an_engine_that_cannot_read_a_scene_refuses_the_delivery(tmp_path, monkeypatch):
    root = tmp_path / "a-b"
    root.mkdir()
    _scene(root)

    def broken(*_):
        raise FrameGraphError("no")

    monkeypatch.setattr(text_rules.framegraph, "evaluate", broken)
    with pytest.raises(FrameGateError, match="not timed"):
        text_rules.timing_defects({"a-b": Release("a-b", POST)}, tmp_path, {"a-b": "a-b"}, "engine")


def test_a_listed_text_of_a_published_reel_passes_after_its_build(tmp_path, monkeypatch):
    _engine(monkeypatch, SHOWN)
    row = Exemption("old-reel", TEXT_SHORT, "HELLO", "published with it")
    monkeypatch.setattr(text_rules, "exemptions", lambda: (row,))
    assert text_rules.after_build("old-reel", _scene(tmp_path), "engine") == []
    assert text_rules.after_build("other-reel", _scene(tmp_path), "engine") != []


def test_the_build_command_fails_on_a_short_text(tmp_path, monkeypatch, capsys):
    _scene(tmp_path)
    _engine(monkeypatch, SHOWN)
    monkeypatch.setattr(cli, "find_engine", lambda: Path("engine"))
    monkeypatch.setattr(cli.anatomy_gate, "after_build", lambda *_: [])
    assert cli._anatomy_frames(tmp_path) == 1
    assert TEXT_SHORT in capsys.readouterr().err


def test_the_build_command_measures_the_picture_not_the_sound_beside_it(tmp_path, monkeypatch):
    project = tmp_path / "a-b"
    project.mkdir()
    picture = _scene(project)
    (project / "a-b.audio.scene.xml").write_text("<scene/>", encoding="utf-8")
    seen: list[tuple[str, Path]] = []
    monkeypatch.setattr(cli, "find_engine", lambda: Path("engine"))
    monkeypatch.setattr(cli.anatomy_gate, "after_build", lambda _p, reel, scene, _e: seen.append((reel, scene)) or [])
    monkeypatch.setattr(cli.text_rules, "after_build", lambda reel, scene, _e: seen.append((reel, scene)) or [])
    assert cli._anatomy_frames(project) == 0
    assert seen == [("a-b", picture), ("a-b", picture)]


def test_the_build_command_says_when_it_measured_nothing(tmp_path, monkeypatch, capsys):
    _scene(tmp_path)

    def nothing() -> Path:
        raise cli.LayoutError("no scene-render")

    monkeypatch.setattr(cli, "find_engine", nothing)
    assert cli._anatomy_frames(tmp_path) == 0
    assert "not measured" in capsys.readouterr().err


def test_a_rule_the_engine_cannot_read_leaves_the_other_to_answer(tmp_path, monkeypatch, capsys):
    _scene(tmp_path)
    _engine(monkeypatch, SHOWN)
    monkeypatch.setattr(cli, "find_engine", lambda: Path("engine"))

    def broken(*_):
        raise FrameGraphError("no")

    monkeypatch.setattr(cli.anatomy_gate, "after_build", broken)
    assert cli._anatomy_frames(tmp_path) == 1
    said = capsys.readouterr().err
    assert "the anatomy frames were not measured" in said and TEXT_SHORT in said


def test_the_delivery_gate_runs_the_timing_rule():
    source = (Path(__file__).resolve().parent.parent / "episodes" / "instagram_posts.py").read_text(encoding="utf-8")
    assert "text_rules.timing_defects(chosen, _beside(renders), first, engine)" in source


@pytest.mark.skipif(ENGINE is None, reason="needs the engine")
@pytest.mark.parametrize(
    ("layers", "short"),
    [
        (['<group id="s" start="0" end="2"><layer id="l" asset="a"/></group>'], False),
        (
            [
                '<group id="s1" start="0" end="0.35"><layer id="l1" asset="a"/></group>',
                '<group id="s2" start="0.35" end="2"><layer id="l2" asset="b"/></group>',
            ],
            False,
        ),
        (['<group id="s" start="0.5" end="0.85"><layer id="l" asset="a"/></group>'], True),
    ],
    ids=["one layer", "carried across a cut", "a card that is short"],
)
def test_the_engine_bug_reproduction_reads_as_the_frames_do(tmp_path, layers, short):
    """The two scenes of docs/engine-bug-legibility-across-cuts.md, and a third that is short on any reading."""
    shutil.copyfile(next(font for font in SYSTEM_FONTS if font.is_file()), tmp_path / "font.ttf")
    card = 'text="SAME CARD" width="700" height="200" size="76" color="#000000" align="center" fontAsset="f"'
    scene = tmp_path / "card.scene.xml"
    scene.write_text(
        '<?xml version="1.0" encoding="UTF-8"?>\n<scene version="1.1">\n'
        '<project width="1080" height="1920" fps="24" duration="2" background="#ffffff"/>\n'
        '<metadata title="card"><accessibility description="A card."/></metadata>\n'
        f'<assets><font id="f" src="font.ttf" family="DejaVu Sans" weight="700"/><text id="a" {card}/>'
        f'<text id="b" {card}/></assets>\n'
        f"<composition>{''.join(layers)}</composition></scene>\n",
        encoding="utf-8",
    )
    notes = text_rules.timing_notes(scene, ENGINE)
    assert [note.part for note in notes] == (["SAME CARD"] if short else [])
