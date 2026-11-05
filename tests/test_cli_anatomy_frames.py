"""The build command's frame checks (``srstudio build`` runs ``cli._anatomy_frames`` on the scene it wrote): an open
bust (ADR 0148) and a text too short to read (rule 8) fail the build, a project with nothing to measure passes, and a
check the engine cannot answer is said, not passed. Moved from the episodes repository (ADR 0225): it tests the
library's command and reads no reel.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from srstudio import anatomy_gate, anatomy_ledger, build_report, cli, figure_record, text_rules
from srstudio.anatomy_ledger import BUST_OPEN
from srstudio.errors import SrstudioError
from srstudio.figure_record import Figure
from srstudio.framegraph import Drawing, Frame, FrameGraphError, Node
from srstudio.layout import LayoutError
from srstudio.releases import Release
from srstudio.social import InstagramPost
from srstudio.text_rules import TEXT_SHORT

POST = InstagramPost(title="t", description="d")


# -- an open bust (the anatomy gate) ----------------------------------------------------------------------------------
FIGURE_PLACE = (1.0, 0.0, 0.0, 1.0, 0.0, 0.0)


def box(left: float, top: float, right: float, bottom: float) -> tuple[tuple[float, float], ...]:
    return ((left, top), (right, top), (right, bottom), (left, bottom))


def figure(*shapes: tuple[str, tuple]) -> tuple[Frame, dict[str, Drawing]]:
    nodes = tuple(Node(name, None, "shape", FIGURE_PLACE, 1.0, True) for name, _ in shapes)
    return Frame(1.0, 1080.0, 1920.0, nodes), {name: Drawing((outline,), True) for name, outline in shapes}


BUST = box(300, 841, 789, 1406)


@pytest.fixture
def built(tmp_path):
    release = Release("a-b", POST, video="The_Video")
    project = tmp_path / "ep" / "a-b"
    project.mkdir(parents=True)
    (project / release.scene_file).write_bytes(b'<scene><project fps="24" duration="1"/></scene>')
    return {"a-b": release}, tmp_path / "ep", project


def _open_scene(project: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    figure_record.write(project, [Figure("toon-cat", ("body",))])
    anatomy_ledger.write(project, [])
    shown, drawn = figure(("body", BUST))
    monkeypatch.setattr(anatomy_gate.framegraph, "evaluate", lambda *_: [shown])
    monkeypatch.setattr(anatomy_gate.framegraph, "drawings", lambda *_: drawn)
    monkeypatch.setattr(anatomy_gate, "_duration", lambda *_: 1.0)


def test_the_build_command_fails_on_an_open_bust(built, monkeypatch, capsys):
    _, _, project = built
    _open_scene(project, monkeypatch)
    monkeypatch.setattr(cli, "find_engine", lambda: Path("engine"))
    assert cli._anatomy_frames(project) == 1
    assert BUST_OPEN in capsys.readouterr().err


@pytest.mark.parametrize('missing', ['figures.json', 'anatomy.json'])
def test_missing_anatomy_provenance_is_skipped_and_cannot_satisfy_required_check(built, monkeypatch, missing):
    _, _, project = built
    _open_scene(project, monkeypatch)
    (project / missing).unlink()
    monkeypatch.setattr(text_rules, 'after_build', lambda *args: [])
    with build_report.capture() as report:
        cli._measured(project, next(project.glob('*.scene.xml')), Path('engine'))
    checks = report.to_dict()['checks']
    assert checks['anatomy']['status'] == 'skipped'
    assert missing in checks['anatomy']['results'][0]['reason']
    assert checks['text']['status'] == 'passed'
    with pytest.raises(SrstudioError, match='Required build checks'):
        report.require(['anatomy'])


def test_explicit_empty_anatomy_records_can_pass(built, monkeypatch):
    _, _, project = built
    _open_scene(project, monkeypatch)
    figure_record.write(project, [])
    assert anatomy_gate.after_build(project, 'empty', next(project.glob('*.scene.xml')), 'engine') == []


def test_the_build_command_says_when_it_could_not_measure(built, monkeypatch, capsys):
    _, _, project = built

    def nothing() -> Path:
        raise LayoutError("no scene-render")

    monkeypatch.setattr(cli, "find_engine", nothing)
    assert cli._anatomy_frames(project) == 0
    assert "not measured" in capsys.readouterr().err


def test_the_build_command_passes_a_covered_figure(built, monkeypatch):
    _, _, project = built
    figure_record.write(project, [Figure("toon-cat", ("body",))])
    anatomy_ledger.write(project, [])
    shown, drawn = figure(("body", BUST), ("counter", box(0, 1380, 1080, 1920)))
    monkeypatch.setattr(anatomy_gate.framegraph, "evaluate", lambda *_: [shown])
    monkeypatch.setattr(anatomy_gate.framegraph, "drawings", lambda *_: drawn)
    monkeypatch.setattr(anatomy_gate, "_duration", lambda *_: 1.0)
    monkeypatch.setattr(cli, "find_engine", lambda: Path("engine"))
    assert cli._anatomy_frames(project) == 0


def test_a_project_with_no_scene_has_nothing_to_measure(tmp_path):
    assert cli._anatomy_frames(tmp_path) == 0


# -- a text too short to read (rule 8) --------------------------------------------------------------------------------
PLACE = (1.0, 0.0, 0.0, 1.0, 100.0, 100.0)
BOX = Drawing((((0.0, 0.0), (300.0, 0.0), (300.0, 60.0), (0.0, 60.0)),), False)
DRAWN = {"a": BOX, "b": BOX, "card": Drawing((((0.0, 0.0), (1080.0, 0.0), (1080.0, 1920.0), (0.0, 1920.0)),), True)}
SHOWN = [i / 24 for i in range(5, 12)]  # 0.292 s of seven frames


def node(text: str = "HELLO", *, name: str = "a", opacity: float = 1.0, world=PLACE) -> Node:
    return Node(name, None, "layer", world, opacity, True, text)


def frame(time: float, *nodes: Node) -> Frame:
    return Frame(time, 1080.0, 1920.0, nodes)


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
